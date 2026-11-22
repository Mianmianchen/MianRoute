"""Exercise public rule providers with the official Mihomo core and loopback-only traffic."""
import http.client
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import yaml


providers = ["ads", "ads-exceptions", "ai-proxy", "cn-direct", "apple-direct", "apple-proxy"]
cases = {
    "f7jxqt8z3.com": "ad-test",
    "www.kwai.com": "cn-test",
    "apps.apple.com": "apple-test",
    "courier.push.apple.com": "apple-test",
    "gs-loc-cn.apple.com": "region-test",
    "api.openai.com": "ai-test",
    "gemini.google.com": "ai-test",
    "dl.steam.clngaa.com": "cn-test",
}
with tempfile.TemporaryDirectory() as folder:
    root = pathlib.Path(folder)
    for name in providers:
        shutil.copyfile("mihomo/rules/" + name + ".yaml", root / (name + ".yaml"))
    fixture = {
        "mixed-port": 17890, "external-controller": "127.0.0.1:19090", "mode": "rule", "log-level": "debug",
        "hosts": {name: "127.0.0.1" for name in cases},
        "rule-providers": {name: {"type": "file", "path": "./" + name + ".yaml", "format": "yaml",
                                  "behavior": "domain" if name == "ads" else "classical"} for name in providers},
        "proxy-groups": [{"name": name, "type": "select", "proxies": ["REJECT"]} for name in sorted(set(cases.values()))],
        "rules": ["AND,((RULE-SET,ads),(NOT,((RULE-SET,ads-exceptions)))),ad-test", "RULE-SET,ai-proxy,ai-test",
                  "RULE-SET,cn-direct,cn-test", "RULE-SET,apple-direct,region-test", "RULE-SET,apple-proxy,apple-test", "MATCH,REJECT"],
    }
    config = root / "fixture.yaml"
    config.write_text(yaml.safe_dump(fixture))
    cmd = [sys.argv[1], "-d", folder, "-f", str(config)]
    subprocess.run(cmd + ["-t"], check=True)
    logfile = root / "mihomo.log"
    with logfile.open("w") as log:
        core = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(150):
                if core.poll() is not None:
                    raise RuntimeError(logfile.read_text()[-3500:])
                try:
                    with urllib.request.urlopen("http://127.0.0.1:19090/providers/rules", timeout=1) as response:
                        loaded = json.load(response)["providers"]
                    if all(loaded.get(p, {}).get("ruleCount", 0) > 0 for p in providers):
                        break
                except OSError:
                    pass
                time.sleep(.2)
            else:
                raise RuntimeError("Rule providers failed to load")
            for host, policy in cases.items():
                client = http.client.HTTPConnection("127.0.0.1", 17890, timeout=2)
                try:
                    client.request("CONNECT", host + ":443", headers={"Host": host + ":443"})
                    client.getresponse().read(1)
                except (OSError, http.client.HTTPException):
                    pass
                finally:
                    client.close()
                for _ in range(30):
                    if any(host + ":443" in line and ("using " + policy) in line for line in logfile.read_text().splitlines()):
                        break
                    time.sleep(.1)
                else:
                    raise RuntimeError("Missing policy for " + host + "\n" + logfile.read_text()[-3500:])
                print(host, policy)
        finally:
            core.terminate()
            core.wait(timeout=10)
