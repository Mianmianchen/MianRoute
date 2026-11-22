# Advertising rule sources

This generated ruleset combines domain-level rules from:

1. HaGeZi Multi PRO, captured input from the mutable upstream URL https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/pro-onlydomains.txt
   - Source project: https://github.com/hagezi/dns-blocklists
   - Copyright/credit: HaGeZi and upstream contributors.
   - Published under GPL-3.0; license copy in ADS-LICENSE-GPL-3.0.txt.
   - Scope includes ads, tracking, telemetry and security threats. Not an advertising-only inventory.
2. AdGuard DNS filter, captured input from the mutable upstream URL https://adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt
   - Source project: https://github.com/AdguardTeam/AdGuardSDNSFilter
   - Copyright/credit: AdGuard and upstream filter authors.
   - Published under GPL-3.0; license copy in ADS-LICENSE-GPL-3.0.txt.
   - Only unconditional domain blocking rules are converted. Domain exceptions are preserved as a separate classical provider.
   - Regex/path/other blocking rules that cannot safely be represented at domain level are excluded and recorded in audit reports, not broadened to entire domains.
3. Six Kuaishou domain custom rules, corroborated by AdGuard Mobile Ads source:
   https://raw.githubusercontent.com/AdguardTeam/AdguardFilters/master/MobileFilter/sections/adservers.txt
   - GPL-3.0 license copy in ADS-LICENSE-GPL-3.0.txt.

The generated rules, license notice, build script (build-ads.py), and manifest (ADS-MANIFEST.json) are published in this directory. The build manifest records immutable Git revisions and SHA-256 for both retained November 13 inputs. Verify fresh downloads against those hashes before building. Preserve these notices and source-license files when redistributing. No node, subscription, credential or private configuration is included.

Loyalsoldier was used only as an old-list comparison input, not as a generation source. Source overlap or limited media-domain tests do not prove that every endpoint has been semantically audited. No guarantee of zero false positives, complete old-rule equivalence, or complete coverage of advertising.

## Exception behavior

The main advertising rule must test blacklist AND NOT exception list. An exception skips only the advertising rejection decision and then continues normal route selection; it does not mean DIRECT.

Required routing expression: `AND,((RULE-SET,ads),(NOT,((RULE-SET,ads-exceptions)))),REJECT`. Provider `ads` uses behavior `domain`, `ads-exceptions` uses `classical`, both YAML.

## Reproducibility status

- HaGeZi retained input: `5c00cbf3cf228e53717ef51a16150b488487ec91e8266a14ca48ebbbe2135b15` (4,466,245 bytes).
- AdGuard retained input: `3503aa3a16795a5856a921d829daf74c0d56a07ebed56446e19a961ede9f9144` (4,674,006 bytes).
- Both retained input files match these SHA256 values. Rebuilding in a separate local directory with Python 3 and PyYAML 6.0.3 reproduces both published-rule output hashes.
- Both immutable Git revisions in ADS-MANIFEST.json were retrieved and verified. If a pinned download fails or does not match its SHA-256, stop the build. Updating source pins and hashes requires a new review.
- This establishes reproducibility when the immutable source objects are available, not complete semantic or device compatibility verification of every rule.


## 2026-11-21 narrow false-positive backport

Retains both verified 2026-11-13 immutable inputs in ADS-MANIFEST.json. The generator removes only `memcyco.com` from their union, following [AdGuard incorrect-block issue #246585](https://github.com/AdguardTeam/AdguardFilters/issues/246585) and its [upstream fix](https://github.com/AdguardTeam/AdGuardSDNSFilter/pull/2138/files). The domain no longer rejects at the ad gate; it follows the remaining routing rules. No exception changed and the full upstream delta was not imported.

### 2026-11-21 user-requested PureIP service block

Blocks `pureip.io` and its subdomains, plus exact hosts `stats.proxypurity.com`, `v4.mypublicipnow.com` and `v6.mypublicipnow.com`. The [PureIP site](https://pureip.io/) links the application bundle that names both probe hosts and the separate [analytics script](https://stats.proxypurity.com/script.js). No parent-wide block of the two other domains and no shared CDN or unrelated IP-diagnostic services added. Pinned ad-list and exception inputs are unchanged.

## 2026-11-22 upstream refresh

The current source revisions, Git blob IDs and SHA-256 hashes are in ADS-MANIFEST.json. Earlier dated sections describe their original snapshots. The review compares both HaGeZi Multi PRO and AdGuard DNS with the prior release, checks all curated blocks, restorations and exact exceptions, and cross-checks the AdGuard Chinese and Mobile advertising sections for additional exact hosts. Browser-only path and third-party conditions stay out of the domain rules. AdGuard filter section provenance: https://github.com/AdguardTeam/AdguardFilters/tree/5a5cbd637c00de45b6b7792ebc4363177bf03326 (AdGuard and contributors). The implementation is in maintenance/review-mobile-ads.py.

## Browser auctions and mobile advertising hosts

The November 22 endpoint review used the [Prebid.js browser bid adapters](https://github.com/Prebid/Prebid.js/tree/3b4911e0f41d39e6b7cca50dcc9c9988bc35c0f3/modules) and the [AWAvenue exact mobile advertising host source](https://github.com/TG-Twilight/AWAvenue-Ads-Rule/blob/376c201ec74baa65b3b9f3f34f2705da89f440ac/rule/domain.txt). Each adopted host is listed in `maintenance/reviewed-ad-endpoints.json` with its evidence, and is emitted as an exact match. AWAvenue is credited to its contributors under GPL-3.0, with the license text in ADS-LICENSE-GPL-3.0.txt. Prebid adapter source code is inspected at its pinned revision. The rules contain hostname facts and links to the relevant adapters.

The [before-change comparison](https://github.com/Mianmianchen/MianRoute/actions/runs/44979353031) includes four additional sources: AWAvenue Only.Ads, Cats-Team AdRules DNS, 1Hosts Xtra and StevenBlack unified. Source pins and sample selection are in `maintenance/endpoint_samples.py`. The benchmark reads literal browser bidding endpoints from vendor adapters and checks two platform-documented Chinese server-side endpoints separately. The AWAvenue domain cohort measures overlap with that particular source. Some lists aggregate other candidates. A match count or agreement between lists does not establish a measured reduction in ads on a device. Candidate lists are fetched for comparison; only the reviewed exact hosts are merged into the existing outputs.
