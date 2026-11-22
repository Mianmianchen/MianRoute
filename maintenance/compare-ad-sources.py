"""Compare DNS-representable host rules using public reference and control domains."""
from pathlib import Path
from urllib.request import Request, urlopen
import json
import ipaddress
import re

import yaml
from endpoint_samples import NEW_SOURCES, CN_BIDDERS, MOBILE_SDK_CASE, browser_bidders

SOURCES = {
    "HaGeZi PRO": [
        "suffix",
        "https://raw.githubusercontent.com/hagezi/dns-blocklists/c15030cf263d495b4a2fa2ace43937a59b4ce1d2/wildcard/pro-onlydomains.txt"
    ],
    "HaGeZi PRO++": [
        "suffix",
        "https://raw.githubusercontent.com/hagezi/dns-blocklists/c15030cf263d495b4a2fa2ace43937a59b4ce1d2/wildcard/pro.plus-onlydomains.txt"
    ],
    "AdGuard DNS": [
        "abp",
        "https://raw.githubusercontent.com/AdguardTeam/AdGuardSDNSFilter/b2c6793a585132710ae3841c5c59cc6099ef8b7a/Filters/filter.txt"
    ],
    "anti-AD": [
        "abp",
        "https://raw.githubusercontent.com/privacy-protection-tools/anti-AD/c1d0a1ddb1a5d048f104e2a7eac991b43c3cca8f/anti-ad-adguard.txt"
    ],
    "217heidai DNS": [
        "abp",
        "https://raw.githubusercontent.com/217heidai/adblockfilters/f35f33ccc4c61bb7b23173926bd4a92f070cf445/adblockdns.txt"
    ],
    "oisd big": [
        "abp",
        "https://raw.githubusercontent.com/sjhgvr/oisd/4fb1e35646895c2c3d330db9f623fe58067135be/abp_big.txt"
    ],
    "blackmatrix7 Advertising_All": [
        "clash",
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/0b6897dc17e0c513d25449c935a9694818e32f0c/rule/Surge/Advertising/Advertising_All.list"
    ]
}
EASYLIST = "https://raw.githubusercontent.com/easylist/easylistchina/63761376e60234c6323169cea8877d8e7dbebea5/easylistchina.txt"
# Public bidding/sync URLs in Prebid.js, revision 3b4911e0f41d39e6b7cca50dcc9c9988bc35c0f3.
PREBID = set("hbopenbid.pubmatic.com tlx.3lift.com eb2.3lift.com ssb.smartadserver.com btlr.sharethrough.com apex.go.sonobi.com htlb.casalemedia.com".split())
CONTROLS = set("""
apps.apple.com itunes.apple.com courier.push.apple.com gsp10-ssl-cn.ls.apple.com
icloud.com icloud.com.cn appleid.apple.com account.apple.com apple-pay-gateway.apple.com
www.paypal.com www.paypalobjects.com checkout.paypal.com api-m.paypal.com
chatgpt.com api.openai.com auth.openai.com oaistatic.com files.oaiusercontent.com
gemini.google.com generativelanguage.googleapis.com dl.steam.clngaa.com store.steampowered.com
login.microsoftonline.com partner.microsoftonline-m.net.cn www.kwai.com kwai.com
www.taobao.com trade.taobao.com login.taobao.com www.jd.com passport.jd.com
a.klaviyo.com static.addtoany.com app.adjust.com bdad.123pan.cn api.bilibili.com www.douyin.com www.zhihu.com open.weixin.qq.com pay.weixin.qq.com
""".split())
HOST = r"[a-z0-9_-]+(?:\.[a-z0-9_-]+)+"
SUFFIX = re.compile(r"\|\|(" + HOST + r")\^")
EXACT = re.compile(r"\|(" + HOST + r")\^")
def fetch(url):
    with urlopen(Request(url, headers={"User-Agent":"MianRoute-source-review"}),timeout=90) as response:
        return response.read().decode("utf-8-sig").splitlines()

class Rules:
    def __init__(self):
        self.suffix = set()
        self.exact = set()
        self.keyword = []
        self.allow = []
    def blocks(self, host):
        labels = host.split(".")
        hit = host in self.exact or any(".".join(labels[i:]) in self.suffix for i in range(len(labels)-1)) or any(k in host for k in self.keyword)
        return hit and not any(p.search(host) for p in self.allow)
    def exception(self, kind, value):
        if kind == "DOMAIN": value = "^" + re.escape(value) + "$"
        if kind == "DOMAIN-SUFFIX": value = r"(?:^|\.)" + re.escape(value) + "$"
        self.allow.append(re.compile(value, re.I))

def parse(kind, lines):
    r = Rules()
    for line in lines:
        line=line.strip().lower()
        if kind=="hosts":
            parts = line.partition("#")[0].split()
            if len(parts) >= 2 and parts[0] in {"0.0.0.0", "127.0.0.1"}:
                r.exact.update(parts[1:])
        if kind=="suffix" and re.fullmatch(HOST,line): r.suffix.add(line)
        if kind=="clash" and line.startswith("domain"):
            key,_,val=line.partition(",")
            if key=="domain-suffix": r.suffix.add(val)
            if key=="domain": r.exact.add(val)
            if key=="domain-keyword": r.keyword.append(val)
        if kind=="abp":
            allowed=line.startswith("@@")
            rule=line[2:] if allowed else line
            m=SUFFIX.fullmatch(rule) or EXACT.fullmatch(rule.rstrip('|'))
            if m:
                suffix=rule.startswith("||")
                if allowed: r.exception("DOMAIN-SUFFIX" if suffix else "DOMAIN",m[1])
                else: (r.suffix if suffix else r.exact).add(m[1])
            elif allowed and re.fullmatch(r"@@\|\|[\w.*-]+\^",line):
                r.exception("DOMAIN-REGEX",r"(?:^|\.)"+re.escape(line[4:-1]).replace(r"\*",".*")+"$")
    assert len(r.suffix)+len(r.exact)>500, (kind, len(r.suffix), len(r.exact))
    return r

root=Path("mihomo/rules")
def load(name):
    return yaml.load((root/name).read_bytes(),Loader=yaml.CSafeLoader)["payload"]
current=Rules()
for entry in load("ads.yaml"):
    if entry.startswith("+."): current.suffix.add(entry[2:])
    else: current.exact.add(entry)
for entry in load("ads-exceptions.yaml"): current.exception(*entry.split(",",1))
def hostname(s):
    if not re.fullmatch(HOST,s): return False
    try: ipaddress.ip_address(s)
    except ValueError: return True
    return False

china=set()
section=False
for line in fetch(EASYLIST):
    if line.startswith("!----"):
        section = "Ads-Union" in line
    match=SUFFIX.fullmatch(line.strip().lower())
    if section and match and hostname(match[1]): china.add(match[1])
directory=json.loads("\n".join(fetch("https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/7a9e2be53189b8273f6929977ec92e0f5ae993b6/services.json")))
global_ads=set()
for entity in directory["categories"]["Advertising"]:
    for sites in entity.values():
        for domains in sites.values():
            if isinstance(domains,list):
                global_ads.update(d for d in domains if isinstance(d,str) and hostname(d))
assert len(china)>100
cohorts=[china,global_ads,PREBID,CONTROLS]
base=[{d for d in hosts if current.blocks(d)} for hosts in cohorts]
print("COHORTS",*(len(x) for x in cohorts))
print("CN-MISSES",sorted(china-base[0]))
print("CURRENT",*(len(x) for x in base),sorted(base[-1]))
misses={}
bidders = browser_bidders()
samples = {"browser-bidders": set(bidders), "cn-s2s": set(CN_BIDDERS), "123pan-mobile-sdk": MOBILE_SDK_CASE}
print("ENDPOINT-SAMPLES", {k:len(v) for k,v in samples.items()})
print("ENDPOINT-BASE", {k:sum(current.blocks(h) for h in v) for k,v in samples.items()})
gaps = {h:[] for h in bidders if not current.blocks(h)}
for name,(kind,url) in (SOURCES | NEW_SOURCES).items():
    rules=parse(kind, fetch(url))
    print("ENDPOINT-TEST", name, {k:sum(rules.blocks(h) for h in v) for k,v in samples.items()})
    for host, voters in gaps.items():
        if rules.blocks(host):
            voters.append(name)
    results=[{d for d in hosts if rules.blocks(d)} for hosts in cohorts]
    extra=sorted(results[0]-base[0])
    print("SOURCE",name,json.dumps([len(x) for x in results]),"EXTRA",len(extra),"CONTROL",sorted(results[-1]),"EXAMPLES",extra[:8])
    if name=="HaGeZi PRO++":
        existing_allow=current.allow
        def combined(host):
            return current.blocks(host) or (rules.blocks(host) and not any(p.search(host) for p in existing_allow))
        probe=[{d for d in hosts if combined(d)} for hosts in cohorts]
        print("OVERLAY", [len(d) for d in probe], "CONTROL", sorted(probe[-1]))
    misses[name]=set(extra)
    gextra=sorted(results[1]-base[1]); print("GLOBAL-EXTRA",name,len(gextra),gextra[:20])
    misses["G:"+name]=set(gextra)
print("CONSENSUS", sorted(misses["217heidai DNS"] & (misses["HaGeZi PRO++"] | misses["oisd big"] | misses["anti-AD"]))[:60])
print("GLOBAL-AGREE", sorted(misses["G:217heidai DNS"] & (misses["G:HaGeZi PRO++"] | misses["G:oisd big"] | misses["G:anti-AD"]))[:80])

for host, voters in sorted(gaps.items()):
    print("BROWSER-GAP", host, bidders[host], json.dumps(voters))

# Check shared functions using the effective advertising rule and its exceptions.
# These domains have specific upstream reports of breakage.
for protected in ("bdad.123pan.cn", "vd6.l.qq.com", "a0.app.xiaomi.com"):
    if current.blocks(protected):
        raise ValueError("Functional host blocked: " + protected)
if base[-1]:
    raise ValueError("Functional control hosts blocked: " + str(sorted(base[-1])))
