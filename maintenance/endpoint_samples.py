"""Independent advertising endpoint samples. Fetch source text without running it."""
import re
import tarfile
from urllib.request import urlopen

RAW = "https://raw.githubusercontent.com/"
PREBID_REV = "3b4911e0f41d39e6b7cca50dcc9c9988bc35c0f3"
NEW_SOURCES = {
    "Cats-Team AdRules DNS": ("abp", RAW + "Cats-Team/AdRules/192049177992ba6d14cbc2e823bd15f7499a4590/dns.txt"),
    "1Hosts Xtra": ("abp", RAW + "badmojr/1Hosts/7a4588e87bcf7e86e0b8169d391b8422bd3c5d36/Xtra/adblock.txt"),
    "StevenBlack unified": ("hosts", RAW + "StevenBlack/hosts/ce25ce24d6dca08fa484612091a822bc93587086/hosts"),
}

# Server bidding is reported separately from browser-side bidding.
CN_BIDDERS = {
    "mobads.baidu.com": "https://union.baidu.com/docs/sdk/S2SBidding.html",
    "api-access.pangolin-sdk-toutiao.com": "https://www.csjplatform.com/en/blog/27710",
}
# Match literal declarations in live browser bid adapters; ignore templated hosts,
# documentation, user-sync, analytics and CDN URLs. Dynamic endpoints are outside the sample.
ENDPOINT = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+"
    r"(?:ENDPOINT|BID_ENDPOINT|BIDDER_ENDPOINT|BIDDING_ENDPOINT|BID_URL|BIDDER_URL|AUCTION_URL|AUCTION_ENDPOINT|ENDPOINT_URL)"
    r"\s*=\s*['\x22\x60](?:https?:)?//([a-z0-9-]+(?:\.[a-z0-9-]+)+)(?=[:/?'\x22\x60])",
    re.I | re.M,
)

def browser_bidders():
    archive = "https://codeload.github.com/Prebid/Prebid.js/tar.gz/" + PREBID_REV
    records = {}
    with urlopen(archive, timeout=90) as response, tarfile.open(fileobj=response, mode="r|gz") as tar:
        for entry in tar:
            if not entry.isfile() or not re.fullmatch(r"[^/]+/modules/[^/]+BidAdapter\.js", entry.name):
                continue
            path = entry.name.split("/", 1)[1]
            script = tar.extractfile(entry).read().decode("utf-8")
            for match in ENDPOINT.finditer(script):
                host = match[1].lower()
                if host not in records:
                    line = script.count("\n", 0, match.start(1)) + 1
                    records[host] = f"https://github.com/Prebid/Prebid.js/blob/{PREBID_REV}/{path}#L{line}"
    if len(records) < 40:
        raise ValueError("Too few literal browser bidder endpoints; inspect the pinned source")
    return records

# Customer-reported SDK traffic on the 123pan Android app. The report links
# each host to its purpose; exclude a telemetry-only host and an SDK log host.
# https://github.com/TG-Twilight/AWAvenue-Ads-Rule/issues/216
MOBILE_SDK_CASE = set("""
sdk.adhuanxiao.com mpcfg.fancydsp.com jp.ad.gameley.com de.ad.gameley.com
sdk.zhangyuyidong.cn adm.zhangyuyidong.cn api.shanghailingye.cn sdk.hzzfcm.com
xadsmartget.adgain.cn adsmartget.datads.cn
""".split())
