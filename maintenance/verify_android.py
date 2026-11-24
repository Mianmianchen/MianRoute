"""Exercise the imported v2rayNG rules through Xray SOCKS, with offline DNS and three inert outbounds."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import tempfile
import time

PROXY = ["www.tiktok.com", "www.paypal.cn", "apps.apple.com", "courier.push.apple.com", "api.openai.com",
         "gemini.google.com", "store.steampowered.com", "android-probe.example.org", "8.8.8.8",
         "cdn.us99.api.exponea.com", "api-v5.trbo.com", "api.ads.tvb.com", "www3.doubleclick.net"]
DIRECT = ["www.taobao.com", "www.jd.com", "www.meituan.com", "www.baidu.com", "www.qq.com",
          "dl.steam.clngaa.com", "gsp10-ssl-cn.ls.apple.com", "m1.ad.10010.com",
          "android-probe.example.cn", "android-cn-ip.example.org", "android-lan.local",
          "192.168.1.1", "223.5.5.5", "163.181.246.1", "47.251.90.1"]
BLOCK = ["mobads.baidu.com", "googleads.g.doubleclick.net", "www.google-analytics.com",
         "tracker.ads.tvb.com", "sibling.trbo.com", "sub.www3.doubleclick.net"]


def address(host):
    try:
        return b"\x01" + ipaddress.IPv4Address(host).packed
    except ipaddress.AddressValueError:
        encoded = host.encode()
        return b"\x03" + bytes([len(encoded)]) + encoded


def read_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise EOFError()
        data += chunk
    return data


def connect_socks(listener, host, port, udp):
    with socket.create_connection(("127.0.0.1", listener), timeout=3) as conn:
        conn.sendall(b"\x05\x01\x00")
        assert read_exact(conn, 2) == b"\x05\x00"
        target = address(host) + struct.pack("!H", port)
        command = b"\x03\x00" + address("0.0.0.0") + b"\0\0" if udp else b"\x01\x00" + target
        conn.sendall(b"\x05" + command)
        head = read_exact(conn, 4)
        assert head[:2] == b"\x05\x00" and head[3] == 1, head
        endpoint = socket.inet_ntoa(read_exact(conn, 4)), struct.unpack("!H", read_exact(conn, 2))[0]
        if udp:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(b"\0\0\0" + target + b"probe", endpoint)
                time.sleep(.06)
        else:
            conn.sendall(b"probe")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("xray", type=Path)
    p.add_argument("assets", type=Path)
    p.add_argument("--direct-ip", action="append", default=[], type=ipaddress.IPv4Address)
    args = p.parse_args()
    assets = args.assets.resolve()
    manifest = json.loads((assets / "manifest.json").read_bytes())
    for name, digest in manifest["output_sha256"].items():
        assert hashlib.sha256((assets / name).read_bytes()).hexdigest() == digest, name
    items = json.loads((assets / "routing.json").read_bytes())
    assert all(r["enabled"] and r["outboundTag"] in {"direct", "proxy", "block"} for r in items)
    rules = [{k:v for k,v in item.items() if k not in {"remarks", "enabled"}} for item in items]
    cases = [(h, 443, False, tag) for tag, hosts in [("proxy", PROXY), ("direct", DIRECT), ("block", BLOCK)]
             for h in hosts]
    cases += [(str(h), 443, True, "direct") for h in args.direct_ip]
    cases += [("163.181.246.1", 443, True, "direct"), ("47.251.90.1", 443, True, "direct"),
              ("17.249.1.1", 443, False, "proxy"), ("17.1.1.1", 5223, False, "proxy")]
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        access = work / "access"
        with socket.socket() as port_probe:
            port_probe.bind(("127.0.0.1", 0))
            listener = port_probe.getsockname()[1]
        hosts = {h: "192.0.2.1" for h in PROXY + DIRECT + BLOCK if not h[0].isdigit()}
        hosts.update({"android-cn-ip.example.org": "223.5.5.5", "android-probe.example.org": "47.251.90.1",
                      "www.tiktok.com": "47.251.90.1"})
        config = {"log": {"access": str(access), "loglevel": "warning"},
                  "dns": {"hosts": hosts, "servers": [{"address": "127.0.0.1", "port": 9}], "queryStrategy": "UseIPv4"},
                  "inbounds": [{"tag": "test", "protocol": "socks", "listen": "127.0.0.1", "port": listener,
                                "settings": {"udp": True, "ip": "127.0.0.1"}}],
                  "outbounds": [{"tag": tag, "protocol": "blackhole"} for tag in ["proxy", "direct", "block"]],
                  "routing": {"domainStrategy": "IPIfNonMatch", "rules": rules}}
        path = work / "core.json"
        path.write_text(json.dumps(config))
        cmd = [str(args.xray.resolve()), "run", "-config", str(path)]
        env = dict(os.environ, XRAY_LOCATION_ASSET=str(assets))
        subprocess.run([*cmd, "-test"], env=env, check=True)
        core = subprocess.Popen(cmd, env=env)
        try:
            for _ in range(120):
                try:
                    with socket.create_connection(("127.0.0.1", listener), timeout=.1):
                        break
                except OSError:
                    if core.poll() is not None:
                        raise RuntimeError("Xray did not start")
                    time.sleep(.1)
            for host, port, udp, expected in cases:
                offset = access.stat().st_size
                connect_socks(listener, host, port, udp)
                needle = f"{'udp' if udp else 'tcp'}:{host}:{port}"
                for _ in range(100):
                    with access.open("rb") as log:
                        log.seek(offset)
                        lines = log.read().decode().splitlines()
                    if any(needle in line and ("-> " + expected + "]" in line or
                           ">> " + expected + "]" in line) for line in lines):
                        break
                    time.sleep(.02)
                else:
                    raise AssertionError(f"{needle} expected {expected}: {lines}")
        finally:
            core.terminate()
            core.wait(timeout=10)
    print(f"{len(cases)} live routing checks passed")


if __name__ == "__main__":
    main()
