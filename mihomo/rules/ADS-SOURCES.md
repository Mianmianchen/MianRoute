# Advertising rule sources

This generated candidate combines domain-level rules from:

1. HaGeZi Multi PRO, fixed snapshot from https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/pro-onlydomains.txt
   - Source project: https://github.com/hagezi/dns-blocklists
   - Copyright/credit: HaGeZi and upstream contributors.
   - Published under GPL-3.0; license copy in ADS-LICENSE-GPL-3.0.txt.
   - Scope includes ads, tracking, telemetry and security threats. Not an advertising-only inventory.
2. AdGuard DNS filter, fixed snapshot from https://adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt
   - Source project: https://github.com/AdguardTeam/AdGuardSDNSFilter
   - Copyright/credit: AdGuard and upstream filter authors.
   - Published under GPL-3.0; license copy in ADS-LICENSE-GPL-3.0.txt.
   - Only unconditional domain blocking rules are converted. Domain exceptions are preserved as a separate classical provider.
   - Regex/path/other blocking rules that cannot safely be represented at domain level are excluded and recorded in audit reports, not broadened to entire domains.
3. Six Kuaishou domain custom rules, corroborated by AdGuard Mobile Ads source:
   https://raw.githubusercontent.com/AdguardTeam/AdguardFilters/master/MobileFilter/sections/adservers.txt
   - GPL-3.0 license copy in ADS-LICENSE-GPL-3.0.txt.

The transformation scripts and source hashes are provided alongside the generated files. Preserve these notices and source-license files when redistributing. No node, subscription, credential or private configuration is included.

Loyalsoldier was used only as an old-list comparison input, not as a generation source. Source overlap or limited media-domain tests do not prove that every endpoint has been semantically audited. No guarantee of zero false positives, complete old-rule equivalence, or complete coverage of advertising.

## Exception behavior

The main advertising rule must test blacklist AND NOT exception list. An exception skips only the advertising rejection decision and then continues normal route selection; it does not mean DIRECT.

Required routing expression: `AND,((RULE-SET,ads),(NOT,((RULE-SET,ads-exceptions)))),REJECT`. Provider `ads` uses behavior `domain`, `ads-exceptions` uses `classical`, both YAML.
