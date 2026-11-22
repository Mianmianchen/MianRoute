"""Import corroborated, uncovered advertising hosts from pinned public snapshots."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

import yaml


ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "mihomo/rules"
MANIFEST = RULES / "ADS-MANIFEST.json"
REVIEW = "2026-11-22"
ADGUARD = "https://raw.githubusercontent.com/AdguardTeam/AdguardFilters/5a5cbd637c00de45b6b7792ebc4363177bf03326/"
DNS = "https://raw.githubusercontent.com/AdguardTeam/AdGuardSDNSFilter/b2c6793a585132710ae3841c5c59cc6099ef8b7a/Filters/filter.txt"
HAGEZI = "https://raw.githubusercontent.com/hagezi/dns-blocklists/c15030cf263d495b4a2fa2ace43937a59b4ce1d2/wildcard/pro-onlydomains.txt"
SECTIONS = ["ChineseFilter/sections/adservers.txt", "MobileFilter/sections/adservers.txt"]
HOST = r"[a-z0-9-]+(?:\.[a-z0-9-]+)+"
AD = re.compile(r"\|\|(" + HOST + r")\^")


def read_source(url):
    with urlopen(url, timeout=90) as response:
        return response.read().decode("utf-8-sig").splitlines()


def parents(host):
    labels = host.split(".")
    return [".".join(labels[i:]) for i in range(len(labels) - 1)]


def dataset(path):
    return set(yaml.load(path.read_text(), Loader=yaml.CSafeLoader)["payload"])


manifest = json.loads(MANIFEST.read_text())
old_ads = dataset(RULES / "ads.yaml")
old_exceptions = dataset(RULES / "ads-exceptions.yaml")
baseline = dict(manifest["outputs"])
for filename, expected in baseline.items():
    if hashlib.sha256((RULES / filename).read_bytes()).hexdigest() != expected:
        raise ValueError("Published hash mismatch: " + filename)
# Check independently resolved Git blobs before adopting the two upstream releases.
pins = [(HAGEZI, "52f60be1d077bc3b3199ccaf36409e44b57ad88e"), (DNS, "5094df3850a4e7f1d40b34f701e5e37082828e15")]
for src, (url, expected_blob) in zip(manifest["sources"], pins, strict=True):
    with urlopen(url, timeout=90) as response:
        content = response.read()
    git_header = ("blob %d\0" % len(content)).encode()
    if hashlib.sha1(git_header + content).hexdigest() != expected_blob:
        raise ValueError("Upstream Git blob mismatch")
    cache = RULES / ".ads-source-cache" / src["snapshot_cache_name"]
    cache.parent.mkdir(exist_ok=True)
    cache.write_bytes(content)
    src.update(url=url, commit=url.split("/")[5], sha256=hashlib.sha256(content).hexdigest(),
               snapshot_size_bytes=len(content), git_blob=expected_blob)
manifest["snapshot_date_utc"] = REVIEW
manifest["build_script_sha256"] = hashlib.sha256((RULES / "build-ads.py").read_bytes()).hexdigest()
dns_lines = read_source(DNS)
dns_blocks = {match[1] for line in dns_lines if (match := AD.fullmatch(line))}
pro = set(read_source(HAGEZI))
section_by_host = {}
for section in SECTIONS:
    for line in read_source(ADGUARD + section):
        match = AD.fullmatch(line)
        if match:
            section_by_host[match[1]] = section

def allowed_patterns():
    for rule in old_exceptions:
        kind, value = rule.split(",", 1)
        if kind == "DOMAIN":
            yield re.compile("^" + re.escape(value) + "$")
        elif kind == "DOMAIN-SUFFIX":
            yield re.compile(r"(?:^|\.)" + re.escape(value) + "$")
        elif kind == "DOMAIN-REGEX":
            yield re.compile(value)
        else:
            raise ValueError("Unsupported existing exception " + kind)
    for line in dns_lines:
        if not line.startswith("@@"):
            continue
        # Treat scoped exceptions conservatively when their host is identifiable.
        body = line[2:].split("$", 1)[0].lstrip("|")
        for prefix in ("https://", "http://"):
            body = body.removeprefix(prefix)
        host = re.split(r"[\^/|]", body, maxsplit=1)[0]
        if host and re.fullmatch(r"[\w.*-]+", host):
            yield re.compile(r"(?:^|\.)" + re.escape(host).replace(r"\*", ".*") + "$", re.I)

exceptions = list(allowed_patterns())
restored = {row["domain"] for row in manifest["reviewed_removals"]}
added = []
for host, section in sorted(section_by_host.items()):
    ancestors = parents(host)
    if host not in dns_blocks or not pro.intersection(ancestors):
        continue
    if host in old_ads or any("+." + name in old_ads for name in ancestors):
        continue
    if restored.intersection(ancestors) or any(rule.search(host) for rule in exceptions):
        continue
    manifest["reviewed_additions"].append({
        "domain": host, "match": "exact", "review_date_utc": REVIEW,
        "reason": "Unconditional advertising host in the AdGuard section and current DNS filter, also covered by HaGeZi PRO. Import only this host.",
        "primary_sources": [ADGUARD + section, DNS, HAGEZI],
    })
    added.append(host)

# Two exact uncovered Chinese advertising hosts added in the same upstream case.
easylist_revision = "63761376e60234c6323169cea8877d8e7dbebea5"
easylist_url = f"https://raw.githubusercontent.com/easylist/easylistchina/{easylist_revision}/easylistchina.txt"
easylist = set(read_source(easylist_url))
for host in ("93cwt9hr8s.com", "dw3wytlo38.com"):
    assert f"||{host}^" in easylist
    assert host not in restored and not any(rule.search(host) for rule in exceptions)
    if not any(row["domain"] == host for row in manifest["reviewed_additions"]):
        manifest["reviewed_additions"].append({
            "domain":host, "match":"exact", "review_date_utc":REVIEW,
            "primary_sources":[easylist_url, f"https://github.com/easylist/easylistchina/commit/{easylist_revision}"],
            "reason":"Exact DNS host in the upstream Ads-Union change for a documented Chinese reading page; keep descendant behavior.",
        })
        added.append(host)

# Import reviewed missing hosts. The bidder source reference identifies its exact
# declaration in the upstream browser adapter. Mobile reports remain separate.
from endpoint_samples import browser_bidders

reviews = json.loads((ROOT / "maintenance/reviewed-ad-endpoints.json").read_text())
bidder_sources = browser_bidders()
adwars = read_source("https://raw.githubusercontent.com/jdlingyu/ad-wars/ac079e9d3c4c4dd38d5756b821c8e6b1abd00ee2/sha_ad_hosts")
anti_ad = set(read_source("https://raw.githubusercontent.com/privacy-protection-tools/anti-AD/c1d0a1ddb1a5d048f104e2a7eac991b43c3cca8f/anti-ad-adguard.txt"))
historical_hosts = {line.partition("#")[0].strip() for line in adwars}
verified = []
for row in reviews["browser_bidding"]:
    host = row["host"]
    if bidder_sources.get(host) != row["source"]:
        raise ValueError("Browser bidder source mismatch: " + host)
    verified.append((host, [row["source"]], "Exact browser bidding host verified in the adapter's request construction."))
for row in reviews["mobile_advertising"]:
    host = row["host"]
    if host not in historical_hosts or f"||{host}^" not in anti_ad:
        raise ValueError("Missing exact mobile advertising host: " + host)
    verified.append((host, row["sources"], row["reason"]))

known_hosts = {row["domain"]: row for row in manifest["reviewed_additions"]}
for host, sources, reason in verified:
    if restored.intersection(parents(host)) or any(pattern.search(host) for pattern in exceptions):
        raise ValueError("Advertising endpoint conflicts with a previous restoration or exception: " + host)
    if host in known_hosts:
        entry = known_hosts[host]
        if entry["match"] != "exact":
            raise ValueError("Reviewed endpoint has broader scope: " + host)
        entry.update(primary_sources=sources, reason=reason)
        continue
    entry = {"domain": host, "match": "exact", "review_date_utc": REVIEW,
             "primary_sources": sources, "reason": reason}
    manifest["reviewed_additions"].append(entry)
    known_hosts[host] = entry
    added.append(host)

def save():
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

save()
subprocess.run([sys.executable, str(RULES / "build-ads.py")], check=True)
new_ads = dataset(RULES / "ads.yaml")
new_exceptions = dataset(RULES / "ads-exceptions.yaml")
def blocked(host, rules):
    return host in rules or any("+." + name in rules for name in parents(host))
for row in manifest["reviewed_additions"]:
    if not blocked(row["domain"], new_ads):
        raise ValueError("Lost curated block: " + row["domain"])
for row in manifest["reviewed_exact_exceptions"]:
    if "DOMAIN," + row["domain"] not in new_exceptions:
        raise ValueError("Lost curated exception: " + row["domain"])
for host in restored:
    if blocked(host, new_ads):
        raise ValueError("Restored domain re-blocked: " + host)
for host in ["courier.push.apple.com", "apps.apple.com", "chatgpt.com", "api.openai.com",
             "gemini.google.com", "apple-pay-gateway.apple.com", "paypal.com", "dl.steam.clngaa.com"]:
    if not blocked(host, old_ads) and blocked(host, new_ads):
        raise ValueError("New block on functional host: " + host)
if "refresh_20261122" not in manifest and baseline != {k: hashlib.sha256((RULES / k).read_bytes()).hexdigest() for k in baseline}:
    manifest["refresh_20261122"] = {
        "previous_outputs": baseline, "source_revisions": [x["commit"] for x in manifest["sources"]],
        "blocking_rows_added": len(new_ads - old_ads), "blocking_rows_removed": len(old_ads - new_ads),
        "exception_rows_added": len(new_exceptions - old_exceptions),
        "exception_rows_removed": len(old_exceptions - new_exceptions),
        "note": "Row counts include upstream suffix compaction. All curated additions, removals and exact exceptions were checked.",
    }
for name in manifest["outputs"]:
    manifest["outputs"][name] = hashlib.sha256((RULES / name).read_bytes()).hexdigest()
manifest["mobile_cn_review_20261122"] = {
    "sources": [ADGUARD + name for name in SECTIONS] + [DNS, HAGEZI],
    "exact_hosts": sorted({row["domain"] for row in manifest["reviewed_additions"]
                           if row.get("review_date_utc") == REVIEW and DNS in row.get("primary_sources", [])}),
    "device_validation": False,
}
save()
print("New exact advertising hosts:", len(added))
