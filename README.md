# MianRoute

MianRoute 为 OpenWrt 上的 Nikki（Mihomo）、Apple 设备上的 Egern 和 Android 上的 v2rayNG 提供分流规则。公共模板拦截广告与追踪，优先按域名分流。域名规则未命中时，收录企业的裸 IP 和大陆 IP 默认直连，其余流量默认走代理。

## 使用模板

| 客户端 | 配置文件 | 首次设置 |
| --- | --- | --- |
| Nikki | [带注释的 YAML](templates/nikki.yaml) · [下载](https://raw.githubusercontent.com/Mianmianchen/MianRoute/main/templates/nikki.yaml) | 在本地副本填入节点，并将 `PROXY` 的 `REJECT` 换成节点名。使用订阅时按模板注释配置 `proxy-providers` 和 `use`。在 Nikki 选用该文件后，核对 DNS 混入和透明代理接管范围。 |
| Egern | [带注释的 YAML](templates/egern.yaml) · [下载](https://raw.githubusercontent.com/Mianmianchen/MianRoute/main/templates/egern.yaml) | 在本地副本或 App 中添加节点或订阅，再在 `PROXY` 组选中实际节点。模板仅使用网络分流，无需安装证书或插件。 |
| v2rayNG | [Android 导入说明和订阅地址](v2rayng/) | 添加域名与 IP 资源，导入路由 JSON，选择自己的节点。 |

两个 YAML 模板的代理出口初始设为 `REJECT`。首次启用前先选好节点，否则需要代理的连接会被拒绝。

## 默认分流

| 流量 | 默认处理 |
| --- | --- |
| 广告与追踪 | 命中拦截表且未命中例外时拒绝。例外继续按下方规则分流。 |
| 局域网、大陆服务 | 局域网、指定 Steam 下载主机、`.cn` 和大陆域名分类直连。PayPal、Microsoft 等指定厂商的大陆入口优先代理。 |
| Apple | 明确的大陆服务例外直连。APNs、App Store 及其余命中 Apple 规则的连接走 Apple 代理组。Egern 已启用 APNs 接管。 |
| 游戏平台 | Steam 等游戏平台走代理，指定大陆下载主机优先直连。 |
| 未命中域名规则的连接 | 收录企业的裸 IP（含海外 CDN 和云节点）及大陆 IP 走中国大陆组，默认直连。其余走兜底代理。 |

个人域名和 IP 可加在模板标出的本地例外位置。Nikki 的设备白名单和专用 BT 下载设备的绕过在路由器的 LAN 访问控制中设置。同一设备混合使用浏览器与 BT 时，需要单独区分流量。模板关闭客户端 IPv6。要在全网停用 IPv6，还需在路由器核对 WAN6、RA 和 DHCPv6。DNS 上游由本地配置决定。

## 单独订阅规则

已有配置可从 [Mihomo 目录](mihomo/rules/) 或 [Egern 目录](egern/rules/) 选取所需文件。公共直连补充使用 `cn-services.yaml`。旧订阅 `cn-direct.yaml` 内容相同，任选一份。Nikki 在这份订阅中仅对未识别到域名的连接匹配企业 ASN。Egern 将同一份 ASN 名单放在 `cn-general.yaml`，沿用模板中的海外域名优先级。云厂商的共享 IP 也会匹配，规则无法从裸 IP 区分云租户。广告拦截须配对使用 `ads.yaml` 和 `ads-exceptions.yaml`，组合写法见模板。规则按顺序匹配，Steam 下载和 Apple 大陆直连例外分别放在各自的代理规则前。

广告表按域名拦截广告和追踪。与正常内容共用域名的广告、依赖网页路径或页面元素的广告，无法靠这份域名表完整区分。[上游与例外说明](mihomo/rules/ADS-SOURCES.md)

模板每 24 小时检查规则订阅。Nikki 的地域库取自 [XTLS](https://github.com/XTLS/Xray-rules-dat/releases/latest)，Egern 的域名分类来自[构建清单](egern/BUILD-MANIFEST.json)记录的快照。广告与追踪规则的输入、许可和更新时间见[来源说明](mihomo/rules/ADS-SOURCES.md)和[构建记录](https://github.com/Mianmianchen/MianRoute/actions/workflows/refresh-ad-rules.yml)。

[反馈分流或误拦问题](https://github.com/Mianmianchen/MianRoute/issues)时，请提供客户端版本、公开域名、实际策略和预期结果。节点、私有订阅、证书和完整访问日志请留在本地。[项目许可](LICENSE)
