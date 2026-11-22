# Egern 原生规则

[配置模板](../templates/egern.yaml)包含完整的策略组、规则顺序和中文注释。[规则目录](rules/)可供已有配置单独订阅。

| 文件 | 用途 |
| --- | --- |
| `ads.yaml`、`ads-exceptions.yaml` | 同时检查拦截和例外，只有命中拦截且未命中例外时才进入广告策略。 |
| `lan.yaml`、`proxy-priority.yaml` | 本地网络直连，指定海外厂商优先代理。 |
| `cn-direct.yaml`、`foreign-proxy.yaml` | 国内与下载直连补充，以及海外游戏平台。 |
| `apple-direct.yaml`、`apple-proxy.yaml` | 优先匹配大陆服务的直连例外。六条 APNs IP 与端口组合写在模板的 `and` 规则中，与域名规则配套使用。 |
| `foreign-general.yaml`、`cn-general.yaml` | 从 XTLS GeoSite 快照展开的通用域名分类，放在专用规则之后。 |

规则使用 Egern 原生格式。精确域名、后缀、关键词与正则分别保留各自的匹配方式。广告构建与 Mihomo 共用输入，验证两端导出一致。地域分类的快照哈希和导出信息见[构建清单](BUILD-MANIFEST.json)。

[项目使用说明](../README.md) · [广告来源与许可](../mihomo/rules/ADS-SOURCES.md) · [Egern 规则语法](https://egernapp.com/docs/configuration/rules/)
