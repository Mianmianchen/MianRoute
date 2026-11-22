# Advertising and privacy rules

Nikki/Mihomo uses `mihomo/rules/ads.yaml` with `mihomo/rules/ads-exceptions.yaml`. Egern uses the corresponding files in `egern/rules`. Both are generated from one domain policy. An exception skips the advertising rejection and continues ordinary routing. Existing clients can retain their rule-set URLs, groups and ordering.

## Inputs

| Input | Use |
| --- | --- |
| [AdGuard DNS filter](https://github.com/AdguardTeam/AdGuardSDNSFilter) and the [current Multi PRO domain feed](https://github.com/hagezi/dns-blocklists) | Updated baseline, including unconditional DNS exceptions and the repository's existing reviewed restorations |
| [AdGuard Chinese and Mobile filters](https://github.com/AdguardTeam/AdguardFilters) | Dedicated advertising hosts from the two regional/mobile ad-server sections |
| [EasyList and EasyPrivacy](https://github.com/easylist/easylist) | Dedicated international advertising and tracking hosts, with allowlist checks |
| [AdGuard CNAME trackers](https://github.com/AdguardTeam/cname-trackers) | Disguised advertising hostnames and purpose-specific analytics, telemetry and email open/pixel aliases |
| [Reviewed endpoints](../../maintenance/ad-endpoints.json) | Exact browser auction and mobile advertising endpoints with their public source |
| [Public Suffix List](https://publicsuffix.org/) | Guard against blocking a public suffix or shared hosting suffix |

Supplemental entries match exact hostnames. Browser path restrictions and page element rules stay with the browser. Known exceptions, removed domains, and user-reviewed additions are recorded in ADS-MANIFEST.json. The 2020 ad-wars entries and the public Prebid.js adapter URLs identify previously reviewed hosts. The workflow downloads only public rule sources.

Source credits: AdGuard and its contributors, HaGeZi and contributors, EasyList and EasyPrivacy authors and contributors (GPL-3.0 option), and the maintainers named by the reviewed sources. See [GPL text](ADS-LICENSE-GPL-3.0.txt), [AdGuard CNAME MIT notice](ADS-LICENSE-CNAME-MIT.txt), and the [EasyList licensing page](https://easylist.to/pages/licence.html). The Public Suffix List is fetched for validation and remains available from its MPL-2.0 project.

## Advertising exceptions

The build publishes an exact, suffix or DNS wildcard exception only when it overlaps the current blocklist. Full upstream and locally reviewed exceptions are reconsidered at every build. The China Unicom exception is limited to the exact host `m1.ad.10010.com` for [app icons](https://github.com/TG-Twilight/AWAvenue-Ads-Rule/issues/201). The repository omits the exceptions for `www.googleadservices.com` and `pagead.l.doubleclick.net`. Blocking these hosts can prevent [Google sponsored links](https://github.com/AdguardTeam/AdGuardSDNSFilter/issues/289) from opening.

## Updates

After merge the workflow runs at 02:17 and 14:17 UTC. It resolves each upstream to an immutable Git commit, builds both exports and tests the advertising decision against the official Mihomo core. A failed download, unexpected source shrinkage, failed control case or conflicting branch update leaves the previous published snapshot in place. The source lock records the Git revisions, SHA-256 values and resulting counts. To reproduce the current snapshot, install PyYAML 6.0.3 and run `python maintenance/build_ads.py`; to resolve newer public inputs, add `--refresh`. Egern checks validate the native encoding and agreement with the tested domain policy.
