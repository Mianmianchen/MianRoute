"""Rebuild MianRoute advertising rules for Mihomo and Egern from the same host sets."""
import argparse
from bisect import bisect_left
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "mihomo/rules"
E = ROOT / "egern/rules"
LOCK = ROOT / "maintenance/ad-sources.lock.json"
# Each tuple is a file and the semantics we can preserve in both clients.
INPUTS = {
    "hagezi/dns-blocklists": ("main", {"wildcard/pro-onlydomains.txt": "base"}),
    "AdguardTeam/AdGuardSDNSFilter": ("gh-pages", {"Filters/filter.txt": "dns"}),
    "easylist/easylist": ("master", {
        "easylist/easylist_adservers.txt": "abp", "easylist/easylist_adservers_popup.txt": "abp",
        "easyprivacy/easyprivacy_trackingservers.txt": "abp",
        "easyprivacy/easyprivacy_trackingservers_international.txt": "abp",
        "easylist/easylist_allowlist.txt": "veto", "easyprivacy/easyprivacy_allowlist.txt": "veto",
        "easyprivacy/easyprivacy_allowlist_international.txt": "veto",
    }),
    "AdguardTeam/AdguardFilters": ("master", {
        "ChineseFilter/sections/adservers.txt": "abp", "MobileFilter/sections/adservers.txt": "abp",
        "ChineseFilter/sections/allowlist.txt": "veto",
    }),
    "AdguardTeam/cname-trackers": ("master", {
        "data/combined_disguised_ads_justdomains.txt": "cname_ads",
        "data/combined_disguised_trackers_justdomains.txt": "cname_trackers",
        "data/combined_disguised_mail_trackers_justdomains.txt": "cname_mail",
    }),
    "publicsuffix/list": ("main", {"public_suffix_list.dat": "psl"}),
}
LABEL = r"[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?"
HOST = re.compile(rf"{LABEL}(?:\.{LABEL})+")
ABP = re.compile(r"\|\|([a-z0-9_.-]+)\^", re.I)
LEGACY = {"adukwai.com","adkwai.com","open.e.kuaishou.cn","open.e.kuaishou.com","open.kuaishouzt.com","open.kwaizt.com"}
PURPOSE = re.compile(r"^(?:analytics|telemetry|metrics|tracking|tracker|pixel|beacon|collect)(?:[0-9]*|[-_][a-z0-9_-]+)$")
REPLACED_EXCEPTIONS = {"ad.10010.com", "www.googleadservices.com", "pagead.l.doubleclick.net"}
MAIL = re.compile(r"^(?:opens?|pixels?|beacon)(?:[0-9]*|[-_][a-z0-9_-]+)$")

def valid(host):
    return (len(host) <= 253 and HOST.fullmatch(host) and not host.rsplit(".", 1)[1].isdigit()
            and not host.endswith((".localhost", ".local", ".invalid", ".test", ".example")))

def suffixes(host):
    labels = host.split(".")
    return (".".join(labels[i:]) for i in range(len(labels)-1))

def digest(data):
    return hashlib.sha256(data).hexdigest()

def fetch(url, api=False):
    headers = {"User-Agent":"MianRoute-public-ad-rules"}
    if api and os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=headers), timeout=90) as response:
                return response.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

def inputs(refresh, old):
    for repo, (branch, files) in INPUTS.items():
        if refresh:
            api = "https://api.github.com/repos/" + repo + "/commits/" + branch
            rev = json.loads(fetch(api, api=True))["sha"]
        for path, kind in files.items():
            key = repo + "/" + path
            previous = old.get(key, {})
            pin = rev if refresh else previous["revision"]
            if not re.fullmatch("[a-f0-9]{40}", pin):
                raise ValueError("Invalid source revision: " + key)
            url = "https://raw.githubusercontent.com/" + repo + "/" + pin + "/" + quote(path)
            print('Reading', key, pin, flush=True)
            data = fetch(url)
            sha = digest(data)
            if not refresh and previous["sha256"] != sha:
                raise ValueError("Pinned input digest mismatch: " + key)
            if not data.strip() or (previous and len(data) < 0.6 * previous["bytes"]):
                raise ValueError("Empty or unusually reduced input: " + key)
            record = {"revision":pin, "sha256":sha, "bytes":len(data), "url":url}
            if previous.get("sha256") == sha:
                record = previous
            yield key, kind, record, data.decode("utf-8-sig").splitlines()

def dns_exception(line):
    m = re.fullmatch(r"@@(\|\||\|)?([a-z0-9_.*-]+)\^\|?", line, re.I)
    if not m:
        return None
    anchor, pat = m.groups()
    pat = pat.lower()
    if "*" not in pat and anchor in ("||","|"):
        return ("DOMAIN-SUFFIX" if anchor == "||" else "DOMAIN", pat), pat
    expression = ("(?:^|\\.)" if anchor == "||" else "^" if anchor else "") + re.escape(pat).replace(r"\*", ".*") + "$"
    return ("DOMAIN-REGEX", expression), pat

def effective_exceptions(candidates, exact, suffix):
    """Retain only rules whose domain sets intersect this build's blocklist."""
    # A child's reversed name starts with its reversed parent and a label separator.
    reversed_hosts = sorted(host[::-1] for host in exact | suffix)
    active = []
    for rule, pattern in candidates.items():
        kind, value = rule
        if kind == "DOMAIN-REGEX":
            # dns_exception emits only end-anchored literal/glob patterns here.
            # '*' spans dots. A matching name under a blocked suffix must end in
            # both the glob's final literal and the blocked domain (at a label boundary).
            tail = pattern.rsplit("*", 1)[-1]
            intersects = any(host.endswith(tail) or tail.endswith("." + host) for host in suffix)
            if not intersects:
                matches = re.compile(value).search
                intersects = any(matches(host) for host in exact)
        else:
            intersects = value in exact or any(parent in suffix for parent in suffixes(value))
            if not intersects and kind == "DOMAIN-SUFFIX":
                prefix = value[::-1] + "."
                i = bisect_left(reversed_hosts, prefix)
                intersects = i < len(reversed_hosts) and reversed_hosts[i].startswith(prefix)
        if intersects:
            active.append(rule)
    return active

def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def dump(path, obj):
    header = "# MianRoute public advertising rules. Generated from maintenance/ad-sources.lock.json.\n"
    path.write_text(header + yaml.dump(obj, Dumper=yaml.CSafeDumper, allow_unicode=True, sort_keys=False, width=150), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    refresh = parser.parse_args().refresh
    manifest_path = M / "ADS-MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    previous = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    if not refresh and not previous:
        parser.error("Initial build requires --refresh")
    suffix = set(LEGACY)
    exact = set()
    supplement = set()
    sole_host = set()
    veto = set()
    allow = {}
    public, wild, psl_exceptions = set(), set(), set()
    lock, stats = {}, {}
    for key, kind, record, lines in inputs(refresh, previous.get("files", {})):
        lock[key] = record
        for raw in lines:
            line = raw.strip().lower()
            if kind == "psl":
                if not line or line.startswith("//"):
                    continue
                target = psl_exceptions if line.startswith("!") else wild if line.startswith("*.") else public
                target.add(line.lstrip("!*."))
            elif kind == "base":
                if valid(line):
                    suffix.add(line)
            elif kind in ("abp", "dns", "veto"):
                if line.startswith("@@"):
                    # A site- or path-scoped exception vetoes supplemental additions for that host.
                    # Only unconditional DNS exceptions become routing exceptions.
                    exception = dns_exception(line) if kind == "dns" else None
                    if exception:
                        rule, pattern = exception
                        if rule[0] in ("DOMAIN", "DOMAIN-SUFFIX") and rule[1] in REPLACED_EXCEPTIONS:
                            continue  # This unconditional exception must not veto future supplemental blocks.
                        allow[rule] = pattern
                    match = re.match(r"@@(?:\|\||\|?https?://)([a-z0-9_.-]+)(?=[/\^:$|]|$)", line)
                    if match and valid(match[1]):
                        veto.add(match[1])
                elif kind != "veto":
                    match = ABP.fullmatch(line)
                    if match and valid(match[1]):
                        (suffix if kind == "dns" else supplement).add(match[1])
            elif valid(line):
                label = line.split(".", 1)[0]
                if kind == "cname_ads" or (kind == "cname_trackers" and PURPOSE.fullmatch(label)) or (kind == "cname_mail" and MAIL.fullmatch(label)):
                    sole_host.add(line)
        if kind in ("base", "dns"):
            group = 0 if kind == "base" else 1
            manifest["sources"][group].update(url=record["url"], commit=record["revision"], sha256=record["sha256"], snapshot_size_bytes=record["bytes"])
            manifest["sources"][group].pop("git_blob", None)

    if len(public) < 1000 or len(suffix) < 30000 or len(supplement) < 1000 or len(sole_host) < 1000 or len(allow) < 25:
        raise ValueError("Incomplete input family")
    restored = {item["domain"] for item in manifest.get("reviewed_removals", [])}
    suffix.difference_update(restored)
    for item in manifest["reviewed_additions"]:
        (exact if item["match"] == "exact" else suffix).add(item["domain"])
    for item in manifest["reviewed_exact_exceptions"]:
        allow[("DOMAIN", item["domain"])] = None

    allow[("DOMAIN", "m1.ad.10010.com")] = None

    def unsafe_scope(h):
        return h in public or (h not in psl_exceptions and h.partition(".")[2] in wild)
    suffix = {h for h in suffix if valid(h) and not unsafe_scope(h)}
    # Supplementary hosts are exact even when an upstream can match descendants.
    # Shared parent domains, path rules, wildcard aliases and engagement links keep normal routing.
    curated = json.loads((ROOT / "maintenance/ad-endpoints.json").read_text())["exact"]
    if not all(valid(h) and not unsafe_scope(h) for h in curated):
        raise ValueError("Invalid curated hostname")
    exact.update(curated)
    blocked_before = set(exact)
    for h in supplement | sole_host:
        if unsafe_scope(h) or any(p in veto or p in restored for p in suffixes(h)):
            continue
        if not any(p in suffix for p in suffixes(h)):
            exact.add(h)
    minimal = sorted(h for h in suffix if not any(p in suffix for p in list(suffixes(h))[1:]))
    fixed = sorted(exact)
    if any((h in exact or any(p in suffix for p in suffixes(h))) for h in restored):
        raise ValueError("Previously restored hostname reblocked")
    allow = effective_exceptions(allow, exact, suffix)
    stats.update(suffix=len(minimal), exact=len(fixed), exceptions=len(allow), supplemental_exact=len(exact - blocked_before))
    old_count = sum(previous.get("counts", {}).get(k, 0) for k in ("exact","suffix"))
    if old_count and not 0.80 * old_count <= len(fixed)+len(minimal) <= 1.25 * old_count:
        raise ValueError("Unusual total rule count; keep last good release and review upstream changes")
    for h in fixed:
        if any(p in restored for p in suffixes(h)) and h not in blocked_before:
            raise ValueError("Unexpected exception conflict")
    ads = ["+."+h for h in minimal] + fixed
    exceptions = [kind + "," + value for kind, value in allow]
    dump(M/"ads.yaml", {"payload":ads})
    dump(M/"ads-exceptions.yaml", {"payload":exceptions})
    dump(E/"ads.yaml", {"domain_suffix_set":minimal, "domain_set":fixed})
    native = {}
    kinds = {"DOMAIN":"domain_set", "DOMAIN-SUFFIX":"domain_suffix_set", "DOMAIN-REGEX":"domain_regex_set"}
    for kind, value in allow:
        native.setdefault(kinds[kind], []).append(value)
    dump(E/"ads-exceptions.yaml", native)
    lock_obj = {"files":lock, "counts":stats}
    save_json(LOCK, lock_obj)
    if lock_obj != previous:
        manifest["snapshot_date_utc"] = datetime.now(timezone.utc).date().isoformat()
    manifest["outputs"] = {filename:digest((M/filename).read_bytes()) for filename in ("ads.yaml","ads-exceptions.yaml")}
    manifest["build_script_sha256"] = digest(Path(__file__).read_bytes())
    save_json(manifest_path, manifest)
    epath = E.parent / "BUILD-MANIFEST.json"
    emeta = json.loads(epath.read_text())
    emeta["files"].update({"ads":{"domain_suffix_set":len(minimal),"domain_set":len(fixed)}, "ads-exceptions":{k:len(v) for k,v in native.items()}})
    for filename in manifest["outputs"]:
        emeta["source_files"][filename] = manifest["outputs"][filename]
        emeta["output_sha256"][filename] = digest((E/filename).read_bytes())
    save_json(epath, emeta)
    print("Advertising build:", json.dumps(stats))

if __name__ == "__main__":
    main()
