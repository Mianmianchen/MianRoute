"""Export the public Egern rule order and shared datasets to v2rayNG/Xray."""
import argparse
import concurrent.futures
import gzip
import hashlib
import ipaddress
import json
import os
import pathlib
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml
from android_ads import effective_ads

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "egern/rules"
SITE, IP = "mianroute-site.dat", "mianroute-ip.dat"
KINDS = {"domain_keyword_set": 0, "domain_regex_set": 1, "domain_suffix_set": 2, "domain_set": 3}
POLICY = {"中国大陆": "direct", "DIRECT": "direct", "Apple直连": "direct", "PROXY": "proxy",
          "Apple代理": "proxy", "国外网站": "proxy", "兜底": "proxy", "广告": "block"}


def fetch(url, missing=False):
    request = Request(url, headers={"User-Agent": "MianRoute-public-builder"})
    token = os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        request.add_unredirected_header("Authorization", "Bearer " + token)

    for attempt in range(3):
        delay = 2 ** attempt
        try:
            with urlopen(request, timeout=45) as r:
                return r.read()
        except HTTPError as e:
            with e:
                if missing and e.code == 404:
                    return None
                remaining = e.headers.get("X-RateLimit-Remaining")
                retry_after = e.headers.get("Retry-After", "")
                limited = e.code == 429 or (e.code == 403 and (
                    remaining == "0" or retry_after or b"rate limit" in e.read(4096).lower()
                    or "rate limit" in str(e.reason).lower()
                ))
                if attempt == 2 or (e.code < 500 and not limited):
                    raise
                if limited:
                    reset = e.headers.get("X-RateLimit-Reset", "")
                    if retry_after.isdigit():
                        delay = max(1, int(retry_after))
                    elif remaining == "0" and reset.isdigit():
                        delay = max(1, int(reset) - int(time.time()) + 1)
                    else:
                        delay = 60 * 2 ** attempt
        except (TimeoutError, URLError):
            if attempt == 2:
                raise
        time.sleep(delay)


def read_yaml(path):
    return yaml.load(path.read_bytes(), Loader=yaml.CSafeLoader)


def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def varint(n):
    octets = bytearray()
    while n >= 128:
        octets.append((n & 127) | 128)
        n >>= 7
    octets.append(n)
    return bytes(octets)


def field(number, value):
    if isinstance(value, int):
        return varint(number * 8) + varint(value)
    if isinstance(value, str):
        value = value.encode()
    return varint(number * 8 + 2) + varint(len(value)) + value


def entry(name, items):
    return field(1, field(1, name.upper()) + b"".join(field(2, item) for item in items))


def country_entry(data):
    def number(offset):
        value = 0
        for shift in range(0, 64, 7):
            n = data[offset]
            offset += 1
            value |= (n & 127) << shift
            if n < 128:
                return value, offset
        raise ValueError("Malformed GeoIP varint")
    offset = 0
    while offset < len(data):
        start = offset
        tag, offset = number(offset)
        size, offset = number(offset)
        end = offset + size
        if tag != 10 or end > len(data):
            raise ValueError("Malformed GeoIP list")
        # Each GeoIP code is field 1, followed by its CIDRs.
        if data[offset:offset + 4] == b"\x0a\x02CN" and data[offset + 4] == 18:
            return data[start:end]
        offset = end
    raise ValueError("No CN networks in upstream GeoIP")


def compile_routes():
    sites, cidrs, asns, rules = {}, {}, [], []
    snapshot = {}
    template = read_yaml(ROOT / "templates/egern.yaml")["rules"]

    def rule(label, policy, **kwargs):
        rules.append(dict(remarks=label, outboundTag=POLICY[policy], enabled=True, **kwargs))

    def site_ref(name):
        return f"ext:{SITE}:{name}"

    def ip_ref(name):
        return f"ext:{IP}:{name}"

    def source(name):
        path = SOURCE / (name + ".yaml")
        snapshot[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return read_yaml(path)

    for obj in template:
        kind, row = next(iter(obj.items()))
        policy = row["policy"]
        if kind == "and" and policy == "广告":
            expected = ["ads.yaml", "ads-exceptions.yaml"]
            pos, neg = row["match"]
            pair = [pos["rule_set"], neg["not"]["match"]["rule_set"]]
            if [r["match"].rsplit("/", 1)[-1] for r in pair] != expected:
                raise ValueError("Unrecognized ad expression")
            sites["ads"] = effective_ads(source("ads"), source("ads-exceptions"))
            rule("广告与追踪（已扣除例外）", policy, domain=[site_ref("ads")])
        elif kind == "rule_set":
            name = pathlib.PurePosixPath(row["match"]).stem
            data = source(name)
            for key in data:
                if key not in KINDS and (name, key) not in {
                    ("lan", "ip_cidr_set"), ("cn-general", "asn_set"), ("cn-general", "no_resolve")
                }:
                    raise ValueError(f"Unsupported field {name}/{key}")
            sites[name] = [(t, value) for k, t in KINDS.items() for value in data.get(k, ())]
            rule(name, policy, domain=[site_ref(name)])
            if "ip_cidr_set" in data:
                cidrs[name] = [ipaddress.ip_network(n) for n in data["ip_cidr_set"]]
                rule(name + " IP", policy, ip=[ip_ref(name)])
            if "asn_set" in data:
                if data.get("no_resolve") is not True:
                    raise ValueError("Expected a no-resolve enterprise ASN list")
                asns = [int(re.fullmatch(r"AS([1-9][0-9]*)", a)[1]) for a in data["asn_set"]]
        elif kind == "and":
            parts = {k: v for term in row["match"] for k, v in term.items()}
            if set(parts) != {"protocol", "dest_port", "ip_cidr"} or not parts["ip_cidr"].get("no_resolve"):
                raise ValueError("Unrecognized port/IP expression")
            rule("APNs " + parts["ip_cidr"]["match"], policy, network=parts["protocol"]["match"],
                 port=parts["dest_port"]["match"], ip=[parts["ip_cidr"]["match"]])
        elif kind == "domain_suffix":
            rule("." + row["match"], policy, domain=["domain:" + row["match"]])
        elif kind == "geoip" and row["match"] == "CN":
            rule("大陆 IP", policy, ip=[ip_ref("cn")])
            # This domain + IP combination only succeeds once an address is available.
            # Keep named foreign cloud tenants ahead of the enterprise bare-IP fallback.
            rule("未分类域名 · 其他 IPv4", "PROXY", domain=["regexp:.+"], ip=["0.0.0.0/0"])
            rule("企业 ASN · 裸 IP", policy, ip=[ip_ref("enterprise")])
        elif kind == "default" and POLICY[policy] == "proxy" and obj == template[-1]:
            # An IP catch-all also sends raw IPs to the selected v2rayNG policy group.
            # A network-only catch-all would suppress IPIfNonMatch's second pass.
            rule("兜底代理", policy, ip=["0.0.0.0/0", "::/0"])
        else:
            raise ValueError(f"Unsupported routing clause {obj!r}")
    if not sites or not asns:
        raise ValueError("Missing public rules")
    return sites, cidrs, asns, rules, snapshot


def upstream(asns, lock):
    rev = lock.get("asn_revision") or json.loads(fetch(
        "https://api.github.com/repos/ipverse/as-ip-blocks/commits/master"))["sha"]
    if not re.fullmatch("[0-9a-f]{40}", rev):
        raise ValueError("Invalid ASN snapshot")
    def get_asn(n):
        raw = fetch(f"https://raw.githubusercontent.com/ipverse/as-ip-blocks/{rev}/as/{n}/aggregated.json", missing=True)
        if raw is None:
            return n, []
        obj = json.loads(raw)
        if obj["asn"] != n:
            raise ValueError(f"ASN mismatch AS{n}")
        return n, [ipaddress.IPv4Network(p) for p in obj["prefixes"]["ipv4"]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        by_asn = dict(pool.map(get_asn, asns))
    if not all(by_asn.get(n) for n in (24429, 45102)):
        raise ValueError("Missing expected Alibaba/Taobao BGP announcements")
    prefixes = list(ipaddress.collapse_addresses(p for group in by_asn.values() for p in group))
    if any(n.prefixlen == 0 for n in prefixes):
        raise ValueError("Unexpected default route")

    asset = lock.get("geoip_asset")
    if asset is None:
        assets = json.loads(fetch("https://api.github.com/repos/XTLS/Xray-rules-dat/releases/latest"))["assets"]
        chosen = next(a for a in assets if a["name"] == "geoip-full.dat.gz")
        asset = {"url": chosen["browser_download_url"], "digest": chosen["digest"]}
    raw = fetch(asset["url"])
    if "sha256:" + hashlib.sha256(raw).hexdigest() != asset["digest"]:
        raise ValueError("GeoIP digest mismatch")
    return prefixes, country_entry(gzip.decompress(raw)), {
        "asn_revision": rev, "asn_source": "https://github.com/ipverse/as-ip-blocks",
        "announced_ipv4_prefix_counts": {str(n): len(ps) for n, ps in by_asn.items()},
        "merged_enterprise_ipv4_prefixes": len(prefixes), "geoip_asset": asset}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument("--lock", type=pathlib.Path, help="rebuild using a published manifest's external inputs")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sites, cidrs, asns, rules, inputs = compile_routes()
    cidrs["enterprise"], china, manifest = upstream(asns, json.loads(args.lock.read_bytes()) if args.lock else {})
    site_data = b"".join(entry(name, (field(1, k) + field(2, val) for k, val in rows))
                         for name, rows in sites.items())
    ip_data = china + b"".join(entry(name, (field(1, n.network_address.packed) + field(2, n.prefixlen)
                                          for n in rows)) for name, rows in cidrs.items())
    outputs = {SITE: site_data, IP: ip_data, "routing.json": dump(rules)}
    manifest.update(public_rule_sha256=inputs, output_sha256={k: hashlib.sha256(v).hexdigest() for k,v in outputs.items()})
    for name, data in {**outputs, "manifest.json": dump(manifest)}.items():
        (args.output / name).write_bytes(data)


if __name__ == "__main__":
    main()
