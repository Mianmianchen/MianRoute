# MianRoute

MianRoute 为 OpenWrt 上的 Nikki（Mihomo）和 Apple 设备上的 Egern 提供分流规则。默认拦截广告与追踪，局域网和中国大陆服务直连，海外服务和未匹配流量走代理。Apple 大陆服务有单独的直连例外，APNs 推送走代理。

## 开始使用

| 客户端 | 配置模板 | 设置方法 |
| --- | --- | --- |
| Nikki | [查看带注释的 YAML](templates/nikki.yaml) · [下载原文件](https://raw.githubusercontent.com/Mianmianchen/MianRoute/main/templates/nikki.yaml) | 下载并补入自己的节点，或为 `PROXY` 组绑定本地节点订阅。在 Nikki 选择这份配置，并核对混入设置中的 DNS 和透明代理接管。 |
| Egern | [查看带注释的 YAML](templates/egern.yaml) · [下载原文件](https://raw.githubusercontent.com/Mianmianchen/MianRoute/main/templates/egern.yaml) | 导入后添加自己的节点，在 `PROXY` 组中选中。模板只做网络层分流，无需安装证书。 |

两份模板沿用相同的七个策略组。首次设置时，把 `PROXY` 里的 `REJECT` 占位替换成自己的节点或订阅。配置完成前，国内直连仍可使用，需要代理的请求会被拒绝。节点、订阅凭据和设备设置只保存在自己的配置副本中。

## 规则怎样匹配

| 匹配顺序 | 默认结果 |
| --- | --- |
| 广告或追踪域名 | 命中拦截表且未命中例外时拒绝。命中例外则继续向下匹配。 |
| 局域网、明确的海外厂商入口 | 局域网直连；PayPal、Microsoft 等指定入口优先代理。 |
| 中国大陆直连补充、游戏平台 | 指定 Steam 下载主机直连，其余命中游戏平台规则的流量走代理。 |
| Apple 服务 | 先匹配大陆服务的直连例外，随后处理 APNs 和其他 Apple 服务。APNs 的 IP 规则限定 TCP 端口。 |
| 通用地域与兜底 | `.cn` 直连，`.tw` 走国外网站组；最后按域名分类、GeoIP 和兜底策略匹配。 |

模板从本仓库订阅[六份 Mihomo 规则](mihomo/rules/)或[十份 Egern 原生规则](egern/rules/)，每 24 小时检查更新。只需要广告拦截时，请同时引用 `ads.yaml` 和 `ads-exceptions.yaml`，组合方式见对应模板。域名层规则无法区分同一主机上的广告与正常内容。

## 来源和更新

- **广告与追踪**　GitHub Actions 每天计划构建两次。构建会锁定公开上游版本，用 Mihomo 核心验证代表性域名，并比对 Egern 导出。检查通过后才发布。[上游与许可](mihomo/rules/ADS-SOURCES.md) · [版本、哈希与规则数](maintenance/ad-sources.lock.json) · [构建记录](https://github.com/Mianmianchen/MianRoute/actions/workflows/refresh-ad-rules.yml)
- **地域数据**　Nikki 模板从 [XTLS 官方发布页](https://github.com/XTLS/Xray-rules-dat/releases/latest) 获取 GeoSite 和 GeoIP。Egern 的国家查询使用 [MetaCubeX 的 MMDB](https://github.com/MetaCubeX/meta-rules-dat/releases/tag/latest)，地域域名分类使用本仓库已展开的规则集。[Egern 构建清单](egern/BUILD-MANIFEST.json)
- **其他分流规则**　Apple、国内与海外补充规则随仓库提交更新。目前 `main` 没有定时重建 Egern 地域分类或刷新本仓库地域数据库 Release 的工作流。

反馈误拦或分流错误时，请提供客户端版本、公开域名、实际命中的策略和预期结果。提交前请移除节点资料、证书、个人订阅地址及访问记录。[反馈问题](https://github.com/Mianmianchen/MianRoute/issues) · [项目许可](LICENSE)
