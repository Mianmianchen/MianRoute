"""Validate both native exports and exercise their effective advertising decision."""
import hashlib
import http.client
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
BLOCK = set("""
googleads.g.doubleclick.net pagead2.googlesyndication.com www.google-analytics.com
ads.pubmatic.com adservice.sigmob.cn api-access.pangolin-sdk-toutiao.com
mobads.baidu.com tracker.adform.net sdk.adhuanxiao.com
""".split())
BLOCK.update(json.loads((ROOT / "maintenance/ad-endpoints.json").read_text())["exact"])
NORMAL = set("""
apps.apple.com
itunes.apple.com
courier.push.apple.com
gsp10-ssl-cn.ls.apple.com
icloud.com
icloud.com.cn
appleid.apple.com
account.apple.com
apple-pay-gateway.apple.com
www.paypal.com
www.paypalobjects.com
checkout.paypal.com
api-m.paypal.com
chatgpt.com
api.openai.com
auth.openai.com
oaistatic.com
files.oaiusercontent.com
gemini.google.com
generativelanguage.googleapis.com
dl.steam.clngaa.com
store.steampowered.com
login.microsoftonline.com
partner.microsoftonline-m.net.cn
www.kwai.com
kwai.com
www.taobao.com
trade.taobao.com
login.taobao.com
www.jd.com
passport.jd.com
a.klaviyo.com
static.addtoany.com
app.adjust.com
bdad.123pan.cn
api.bilibili.com
www.douyin.com
www.zhihu.com
open.weixin.qq.com
pay.weixin.qq.com
a0.app.xiaomi.com
vd6.l.qq.com
xp.apple.com
gdmf.apple.com
mesu.apple.com
swcdn.apple.com
init.push.apple.com
gateway.icloud.com
icloud-content.com
buy.itunes.apple.com
iosapps.itunes.apple.com
api.github.com
github.com
raw.githubusercontent.com
dl.google.com
play.googleapis.com
login.live.com
files.pythonhosted.org
api.steampowered.com
steamcommunity.com
www.ximalaya.com
mobile.ximalaya.com
www.bilibili.com
www.xiaohongshu.com
www.weixin.qq.com
alipay.com
www.alipay.com
www.123pan.com
www.microsoft.com
support.apple.com
""".split())

def load(path):
    return yaml.load(path.read_bytes(), Loader=yaml.CSafeLoader)

m = ROOT / "mihomo/rules"
e = ROOT / "egern/rules"
payload = load(m / "ads.yaml")["payload"]
domains = {s for s in payload if not s.startswith("+.")}
suffix = {s[2:] for s in payload if s.startswith("+.")}
eg = load(e / "ads.yaml")
assert set(eg) == {"domain_set", "domain_suffix_set"}
assert set(eg["domain_set"]) == domains and set(eg["domain_suffix_set"]) == suffix
assert len(domains) + len(suffix) == len(payload) == len(eg["domain_set"]) + len(eg["domain_suffix_set"])
mapping = {"DOMAIN":"domain_set", "DOMAIN-SUFFIX":"domain_suffix_set", "DOMAIN-REGEX":"domain_regex_set"}
ea = load(e / "ads-exceptions.yaml")
expected = {k:set() for k in mapping.values()}
for row in load(m / "ads-exceptions.yaml")["payload"]:
    kind, value = row.split(",", 1)
    expected[mapping[kind]].add(value)
assert {k:set(v) for k,v in ea.items()} == {k:v for k,v in expected.items() if v}
regex = [re.compile(p,re.I) for p in expected["domain_regex_set"]]
def blocked(host):
    parts = host.split(".")
    parents = {".".join(parts[i:]) for i in range(len(parts)-1)}
    allowed = host in expected["domain_set"] or parents & expected["domain_suffix_set"] or any(r.search(host) for r in regex)
    return bool((host in domains or parents & suffix) and not allowed)

failures = sorted(h for h in NORMAL if blocked(h)) + sorted(h for h in BLOCK if not blocked(h))
if failures:
    raise SystemExit("Unexpected advertising decisions: " + ", ".join(failures))
emeta = json.loads((e.parent/"BUILD-MANIFEST.json").read_text())
mmeta = json.loads((m/"ADS-MANIFEST.json").read_text())
for filename in ("ads.yaml","ads-exceptions.yaml"):
    assert hashlib.sha256((e/filename).read_bytes()).hexdigest() == emeta["output_sha256"][filename]
    assert hashlib.sha256((m/filename).read_bytes()).hexdigest() == mmeta["outputs"][filename] == emeta["source_files"][filename]

# Test both sides of the existing AND/NOT gate with an isolated core, on loopback.
with tempfile.TemporaryDirectory() as temp:
    root = pathlib.Path(temp)
    for f in ("ads.yaml","ads-exceptions.yaml"):
        shutil.copyfile(m/f,root/f)
    cases = {h:"daily-use" for h in NORMAL}
    cases.update(dict.fromkeys(BLOCK,"ad-test"))
    providers = {k:{"type":"file","path":"./"+k+".yaml","behavior":behavior,"format":"yaml"} for k,behavior in [("ads","domain"),("ads-exceptions","classical")]}
    profile = {"mixed-port":17890, "external-controller":"127.0.0.1:19090", "mode":"rule", "log-level":"debug",
        "hosts":dict.fromkeys(cases,"127.0.0.1"), "rule-providers":providers,
        "proxy-groups":[{"name":k,"type":"select","proxies":["REJECT"]} for k in ["daily-use","ad-test"]],
        "rules":["AND,((RULE-SET,ads),(NOT,((RULE-SET,ads-exceptions)))),ad-test","MATCH,daily-use"]}
    conf = root/"test.yaml"
    conf.write_text(yaml.safe_dump(profile))
    cmd = [sys.argv[1],"-d",temp,"-f",str(conf)]
    subprocess.run(cmd+["-t"],check=True)
    with (root/"log").open("w") as out:
        core = subprocess.Popen(cmd,stdout=out,stderr=subprocess.STDOUT)
        try:
            for _ in range(240):
                if core.poll() is not None:
                    raise RuntimeError("Mihomo exited before loading providers")
                try:
                    with urllib.request.urlopen("http://127.0.0.1:19090/providers/rules", timeout=1) as response:
                        ready = json.load(response).get("providers") or {}
                    if all((ready.get(p) or {}).get("ruleCount",0) > 0 for p in providers):
                        break
                except OSError:
                    pass
                time.sleep(.2)
            else:
                raise RuntimeError("Mihomo providers did not initialize")
            for host, policy in cases.items():
                conn = http.client.HTTPConnection("127.0.0.1",17890,timeout=2)
                try:
                    conn.request("CONNECT",host+":443",headers={"Host":host+":443"})
                    conn.getresponse().read(1)
                except (OSError,http.client.HTTPException):
                    pass
                finally:
                    conn.close()
                for _ in range(25):
                    if any(host+":443" in line and "using "+policy in line for line in (root/"log").read_text().splitlines()):
                        break
                    time.sleep(.1)
                else:
                    raise AssertionError("Core policy mismatch: "+host)
        finally:
            core.terminate()
            core.wait(timeout=10)
print(f"Core checks passed: {len(BLOCK)} advertising/tracking hosts, {len(NORMAL)} normal-service hosts. Egern exports match.")
