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

The generated rules, license notice, build script (build-ads.py), and manifest (ADS-MANIFEST.json) are published in this directory. Exact retained input hashes are listed below; these identify captured bytes, not immutable download URLs. Fresh downloads may change and must not be silently accepted as the audited snapshot. Preserve these notices and source-license files when redistributing. No node, subscription, credential or private configuration is included.

Loyalsoldier was used only as an old-list comparison input, not as a generation source. Source overlap or limited media-domain tests do not prove that every endpoint has been semantically audited. No guarantee of zero false positives, complete old-rule equivalence, or complete coverage of advertising.

## Exception behavior

The main advertising rule must test blacklist AND NOT exception list. An exception skips only the advertising rejection decision and then continues normal route selection; it does not mean DIRECT.

Required routing expression: `AND,((RULE-SET,ads),(NOT,((RULE-SET,ads-exceptions)))),REJECT`. Provider `ads` uses behavior `domain`, `ads-exceptions` uses `classical`, both YAML.

## Reproducibility status

- HaGeZi retained input: `5c00cbf3cf228e53717ef51a16150b488487ec91e8266a14ca48ebbbe2135b15` (4,466,245 bytes).
- AdGuard retained input: `3503aa3a16795a5856a921d829daf74c0d56a07ebed56446e19a961ede9f9144` (4,674,006 bytes).
- Both retained input files match these SHA256 values. Rebuilding in a separate local directory with Python 3 and PyYAML 6.0.3 reproduces both published-rule output hashes.
- No immutable upstream revision or public archive containing these exact input bytes has been verified. The original upstream URLs can change. If they no longer return the recorded hashes, the build must stop; updating hashes requires a new review rather than bypassing the check.
- This establishes cached-input reproducibility, not guaranteed clean network reproducibility or complete semantic/compatibility verification of every rule.
