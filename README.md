# MianRoute

**项目简介**

MianRoute 是一个面向家庭网络的规则整理与配置实践项目：把分散的规则归类成可订阅文件，让分流、广告拦截和后续维护更清楚。

项目在Mihomo内核的Nikki和及iOS端的Egern中进行了广泛测试，理论上适用于Loon、Surge及其他主流客户端。

> 当前发布的是规则集与维护材料，不是一份可直接导入所有设备的通用完整配置。请自行配置节点、策略组、DNS 和本地网络接管方式。

## 为什么做 MianRoute

现阶段众多通用配置，采用了过于冗余的DNS、分流规则和广告规则，额外开销大，且过分的追求大而全，反而容易出现各种各样的问题。规则来源太多、重复越来越多、例外顺序难以理解。

MianRoute 希望把这些问题拆开处理：

- **规则与配置分离**：规则放在仓库中订阅，节点和凭据保留在使用者自己的配置里。可根据项目中提供的模板结合AI做一个属于自己的配置。
- **优化分流策略组**：众多规则使用了过于冗杂的分流策略，甚至每个应用堆一个策略组，但实际使用中，相当一部分的用户只需要区分国内和国外，因此，本配置只区分【苹果直连】、【苹果代理】、【国内直连】、【海外代理】、【广告拦截】几个大项，如有需求请自行添加。
- **按真实用途区分**：例如 Steam 下载 CDN 与平台服务分开考虑，苹果大陆入口与全球服务分开考虑，有相关需求的可以分别配置代理和直连。
- **不强追求大而全**：本项目不会为了“更多规则”，而照搬上游的错误拦截。
- **来源改动可检查**：提供广告来源说明、输入哈希与构建脚本，遇到上游变更先核对，而不是静默接受。

本项目不以政治或宗教立场作为拦截依据。因各方面的因素，本项目尽量不使用 Loyalsoldier 和 anti-AD 规则，有相关需求的用户需要注意。同时，聚合来源的完整传递依赖并不都能逐条追溯，有限测试也不能证明绝无误拦。


## 规则目录

mihomo 规则位于 [`mihomo/rules/`](mihomo/rules/)：

| 文件 | Mihomo behavior | 用途 |
| --- | --- | --- |
| [`apple-direct.yaml`](mihomo/rules/apple-direct.yaml) | `classical` | 明确的大陆区域入口等直连例外，放在苹果代理规则之前 |
| [`apple-proxy.yaml`](mihomo/rules/apple-proxy.yaml) | `classical` | 苹果代理补充，含 APNs 与相关服务规则 |
| [`cn-direct.yaml`](mihomo/rules/cn-direct.yaml) | `classical` | 国内直连补充、部分 Steam 下载 CDN 等例外 |
| [`foreign-proxy.yaml`](mihomo/rules/foreign-proxy.yaml) | `classical` | 世纪互联 Microsoft 365 的两个域名后缀，以及 Steam、Ubisoft、EA、PlayStation、Nintendo、Epic Games 的 GEOSITE 分类引用 |
| [`ads.yaml`](mihomo/rules/ads.yaml) | `domain` | 合并后的广告、追踪及部分安全威胁域名规则 |
| [`ads-exceptions.yaml`](mihomo/rules/ads-exceptions.yaml) | `classical` | 广告规则的域名例外，**必须与 ads 配套使用** |
| [`ads-custom.yaml`](mihomo/rules/ads-custom.yaml) | `classical` | 已核实的少量定制广告规则；内容已并入 ads，无需重复加载 |

这些都是补充规则，不是完整国家/地区数据库。`foreign-proxy.yaml` 还需要使用者的 GEOSITE 数据包含对应分类；仅订阅此文件不会自动下载或配置全部地理数据。

## 订阅方式

原始文件地址格式：

```text
https://raw.githubusercontent.com/Mianmianchen/MianRoute/main/mihomo/rules/文件名.yaml
```

以广告规则为例，下面是需要合入现有 Mihomo 配置的**片段**，不是完整配置：

```yaml
rule-providers:
  ads:
    type: http
    behavior: domain
    format: yaml
    url: https://raw.githubusercontent.com/Mianmianchen/MianRoute/main/mihomo/rules/ads.yaml
    path: ./ruleset/mianroute-ads.yaml
    interval: 86400

  ads-exceptions:
    type: http
    behavior: classical
    format: yaml
    url: https://raw.githubusercontent.com/Mianmianchen/MianRoute/main/mihomo/rules/ads-exceptions.yaml
    path: ./ruleset/mianroute-ads-exceptions.yaml
    interval: 86400

rules:
  - AND,((RULE-SET,ads),(NOT,((RULE-SET,ads-exceptions)))),REJECT
  # 后面继续保留自己的正常分流规则。
```

**不要只加载 ads 然后直接整表 REJECT。** 配套例外用于避免把上游已放行的功能重新拦住。`interval` 只是客户端检查订阅的间隔，不代表仓库按该频率发布。

其他规则按 `classical`、`yaml` 加载，指向自己的策略组。需要处理优先级：苹果直连例外应先于苹果代理；下载 CDN 的直连例外应先于游戏平台代理；明确需要代理的海外厂商 CN 域名应先于通用 CN 直连。

## 广告规则来源

（待建设）

不是将浏览器过滤语法逐行改成域名封锁。无法可靠转换的路径、正则或条件规则不会被随意扩大成整个域名的拒绝；域名例外单独保留。

请查看：

- [来源、语义与复现限制](mihomo/rules/ADS-SOURCES.md)
- [来源哈希清单](mihomo/rules/ADS-MANIFEST.json)
- [构建脚本](mihomo/rules/build-ads.py)
- [广告来源许可证](mihomo/rules/ADS-LICENSE-GPL-3.0.txt)

构建脚本依赖 Python 3 和 PyYAML。输入下载地址会变化；如果内容不再匹配清单中的哈希，脚本会停止。**不要通过删除哈希检查来“修好”构建。** 当前已验证保留输入的重建结果，但未验证这些输入存在长期可用的公开不可变快照，因此不承诺在任意时间全新下载都能复现同一版本。

## 维护原则

计划按周检查上游变化，重点复核新增、删除、例外冲突和异常扩大范围的规则。未完成核验时保留上一份有效版本，不以更新时间代替质量判断。

- 不直接复制无法解释用途的旧拒绝项。
- 不把诊断、风控、正常深链等端点仅凭名字判为广告。
- 不把广告例外强制设成 DIRECT。
- 保留来源署名和许可证；不能用项目名称覆盖上游权利声明。
- 更新规则不等于自动修改使用者设备或网络设置。

## 使用前需要知道

- **域名和广告拦截可能出错。** 同一域名同时承载广告和正常功能时，网络层规则可能无法细分。不承诺完整保留其所有拒绝项、覆盖所有广告或零误拦。
- **游戏相关覆盖不完全。** 游戏商店、登录、下载、语音和实际对局可能共享域名或使用动态 IP；不能保证所有游戏会话自动直连。
- **QUIC 不等于 UDP 443。** 全封 UDP 443 可能影响其他 UDP，也不能精确阻止所有端口的 QUIC。
- **Fake-IP 例外不等于直连。** DNS、路由和客户端接管是不同层次，需要一起验证。
- **Nikki 的混入设置可能覆盖 YAML。** 本地域名交给 dnsmasq 时，应确认 local-only 行为，避免未知域名又转回 Mihomo 造成循环。
- **加密 DNS 不等于绝对无泄漏。** 查询路径、应用自带 DNS、IPv6、接管范围和本地环境都可能影响结果。

## 反馈与贡献

欢迎通过 Issue 提交可复现问题或 PR 提出修正。为了更快定位，请提供：

- 客户端和核心版本；
- 出问题的公开域名、预期策略与实际命中规则；
- 最小复现步骤，以及已经做过的对比测试。

**请先脱敏。** 不要提交节点地址、订阅链接、UUID、密码、密钥、令牌或含私人访问记录的完整日志。

如果 MianRoute 帮你把配置理得更清楚，欢迎点一个 Star。更欢迎带证据的修正，让规则长期值得信任。

## 致谢与许可

感谢 [Mihomo](https://github.com/MetaCubeX/mihomo)、[Nikki](https://github.com/nikkinikki-org/OpenWrt-nikki)、[HaGeZi](https://github.com/hagezi/dns-blocklists)、[AdGuard](https://github.com/AdguardTeam/AdGuardSDNSFilter) 及其他上游贡献者。

仓库提供 [GPL-3.0 许可证](LICENSE)。聚合规则仍需遵守各来源的许可证、署名和分发要求，详见对应来源说明。

