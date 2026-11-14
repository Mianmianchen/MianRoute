# MianRoute · Egern 原生规则

本目录将 MianRoute 的已整理规则转换为 Egern 原生 rule-set，而不是直接引用 Mihomo 的 `payload` 文件。节点、订阅地址、MITM 私钥/证书和用户私有模块均不在此目录。

## 分组与顺序

用户配置采用与 Nikki 相同的 7 个策略组：PROXY、广告、国外网站、中国大陆、兜底、Apple代理、Apple直连。规则按顺序匹配：广告（排除例外）、LAN、明确海外厂商优先、明确中国直连/Steam下载、海外游戏平台、Apple直连、Apple代理、cn/tw后缀、海外域名、中国域名、GeoIP CN、代理兜底。

`ads.yaml` 与 `ads-exceptions.yaml` 必须共同使用 AND(广告, NOT(例外))。例外不是强制直连，而是继续后续分流。广告域名使用 suffix 匹配，原有精确域名与正则例外保持原语义。模块中的广告规则独立生效，主规则例外不能保证覆盖模块的拦截行为。

`apple-proxy.yaml` 包含 APNs 域名；6 条受 TCP/端口约束的 Apple 地址范围采用官方文档已明确的主配置 `and` 语法，避免猜测未示例的 `and_set` 嵌套形式。不要把这些范围变成所有端口的宽泛代理。`cn-direct.yaml` 包含明确的自定义直连与狭窄 Steam 下载主机；没有使用“所有游戏 UDP 直连”这类不可控规则。

## 来源和许可

- Apple、中国直连与广告规则：同仓库 `mihomo/rules/` 对应文件的格式转换。
- 广告来源、许可、筛选及限制沿用 [ADS-SOURCES.md](../mihomo/rules/ADS-SOURCES.md) 和 [GPL-3.0 许可](../mihomo/rules/ADS-LICENSE-GPL-3.0.txt)。
- GEOSITE 展开：XTLS/Xray-rules-dat 的 `geosite.dat`，记录所用快照 SHA-256 于 `BUILD-MANIFEST.json`；按原始 DomainType 保留精确、后缀、关键词及正则匹配。这里只展开已有分类，不创建地域/政治立场广告黑名单。
- `lan.yaml` 为 private 域名类别与常见本地 IPv4 范围。

构建清单记录此次内容，不代表上游最新内容永远不变。周度维护应从同一批输入重新生成 Nikki 与 Egern 两套规则并做差异审计；不要独立手改生成文件造成分叉。

## 验证范围

进行了 YAML 解析、允许字段检查、策略引用检查、329114 条广告后缀和 215 条例外等价检查、代表性域名及 6 个 APNs TCP/端口路由测试、公开文件秘密扫描。测试器不是 Egern 内核；实际导入、模块合并顺序、设备 DNS 路径、推送和流媒体仍须实机验证。此目录不承诺完整拦截所有广告、零误杀或所有游戏会话自动直连。

Egern 官方参考：[规则](https://egernapp.com/docs/configuration/rules/)、[DNS](https://egernapp.com/docs/configuration/dns/)、[策略组](https://egernapp.com/docs/configuration/policy_groups/)。

## 重建

`python3 build-rules.py --mihomo-dir /path/to/mihomo/rules --geosite /path/to/geosite.dat --output /path/to/egern/rules`

只接受公开规则与公开 geosite 输入，不读取用户配置或凭据。主配置里的 6 条 APNs 端口条件应同步核对 apple-proxy 上游，不在此脚本输出中。
