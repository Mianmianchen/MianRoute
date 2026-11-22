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

def save():
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

save()
subprocess.run([sys.executable, str(RULES / "build-ads.py")], check=True)
new_ads = dataset(RULES / "ads.yaml")
if new_ads - old_ads != set(added) or old_ads - new_ads or dataset(RULES / "ads-exceptions.yaml") != old_exceptions:
    raise RuntimeError("Unrelated ad rules or exceptions changed")
for name in manifest["outputs"]:
    manifest["outputs"][name] = hashlib.sha256((RULES / name).read_bytes()).hexdigest()
manifest["mobile_cn_review_20261122"] = {
    "sources": [ADGUARD + name for name in SECTIONS] + [DNS, HAGEZI],
    "exact_hosts": sorted({row["domain"] for row in manifest["reviewed_additions"]
                           if row.get("review_date_utc") == REVIEW and DNS in row.get("primary_sources", [])}),
    "base_domains_removed": 0, "device_validation": False,
}
save()
print("New exact advertising hosts:", len(added))
