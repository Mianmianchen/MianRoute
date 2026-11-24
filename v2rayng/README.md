# Android · v2rayNG

适用版本为 v2rayNG 2.3.15（Xray 26.10.31）。使用普通节点或节点订阅。开启安卓 VPN 后，交给 v2rayNG 的应用流量按 MianRoute 的公开规则分流。自定义完整 Xray 配置使用其自身的路由。

## 首次设置

1. 打开侧边栏的「资源文件」，点右上角添加资源 → 添加 URL。按下表分别添加两项。**备注须完整填写文件名**，v2rayNG 会用备注作为磁盘文件名。保存后点下载图标，确认两份文件均已下载。
2. 打开 [routing.json 原文](https://raw.githubusercontent.com/Mianmianchen/MianRoute/v2rayng-data/routing.json)，全选并复制从 `[` 到 `]` 的完整内容。进入「路由设置」→ 右上角菜单 →「从剪贴板导入规则集」。已有自定义路由可以先「导出规则集至剪贴板」备份。导入会替换未锁定的路由，锁定项保留在最前。个人例外可在本地置于广告和局域网规则之后。
3. 将「域名策略」设为 `IPIfNonMatch`。在设置中使用 VPN 模式，开启「启用流量探测 (Sniffing)」和「启用 routeOnly」，关闭「启用 IPv6」与「IPv6 优先」。希望所有应用使用同一套规则时，关闭「分应用代理」。选择自己的节点，重启 v2rayNG 服务。

| 资源备注 | 资源 URL |
| --- | --- |
| `mianroute-site.dat` | https://raw.githubusercontent.com/Mianmianchen/MianRoute/v2rayng-data/mianroute-site.dat |
| `mianroute-ip.dat` | https://raw.githubusercontent.com/Mianmianchen/MianRoute/v2rayng-data/mianroute-ip.dat |

## 分流和更新

- 广告库在构建时扣除例外。精确例外只豁免该主机，后缀和通配例外遵循上游范围。放行的域名继续判断直连或代理。
- 局域网、大陆服务及指定 Steam 下载默认直连。海外厂商的指定大陆入口、Apple 推送和商店、游戏平台、TikTok 等按公共模板分流。Apple 大陆服务例外优先直连。
- 未分类域名解析到大陆 IP 时直连。对没有域名的连接，收录企业在境外宣告的 IPv4 网段也走直连，覆盖 TCP 与 UDP。已识别的海外域名优先按域名处理。共享云网段仅能识别网络归属。
- 地域库使用 XTLS 的 CN 数据。企业网段按公开 ASN 从 [ipverse](https://github.com/ipverse/as-ip-blocks) 的 BGP 数据生成，当期没有 IPv4 前缀的 ASN 会在[构建清单](https://raw.githubusercontent.com/Mianmianchen/MianRoute/v2rayng-data/manifest.json)中记为 0。
- GitHub 在公共规则变动和定时构建后发布通过 Xray 实测的资源。手机端在「资源文件」点下载、重启服务即可使用更新的域名和 IP。规则顺序或引用名称变动时，还要重新导入 `routing.json`。更新节点订阅仅更新节点。
- 家庭 Wi-Fi 已由 Nikki 接管时，手机端可以关闭 v2rayNG，避免两层分流。公共配置仅包含公开规则，个人例外及节点由设备本地维护。

[构建与测试记录](https://github.com/Mianmianchen/MianRoute/actions/workflows/android-rules.yml) · [v2rayNG 对应版本](https://github.com/2dust/v2rayNG/releases/tag/2.3.15)
