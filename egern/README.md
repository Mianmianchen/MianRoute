# Egern 原生规则

[配置模板](../templates/egern.yaml)包含完整的策略组、规则顺序和中文注释。[规则目录](rules/)可供已有配置单独订阅。

| 文件 | 用途 |
| --- | --- |
| `ads.yaml`、`ads-exceptions.yaml` | 同时检查拦截和例外，只有命中拦截且未命中例外时才进入广告策略。 |
| `lan.yaml`、`proxy-priority.yaml` | 本地网络直连，指定海外厂商优先代理。 |
| `cn-services.yaml`、`foreign-proxy.yaml` | 公共大陆服务和指定 Steam 下载主机直连，海外游戏平台走代理。 |
| `apple-direct.yaml`、`apple-proxy.yaml` | 优先匹配大陆服务的直连例外。六条 APNs IP 与端口组合写在模板的 `and` 规则中，与域名规则配套使用。 |
| `foreign-general.yaml`、`cn-general.yaml` | 从 XTLS GeoSite 快照展开的通用域名分类。`cn-general.yaml` 另含企业 ASN，只使用已有目的 IP。海外分类应排在它前面。 |

规则使用 Egern 原生格式。精确域名、后缀、关键词与正则分别保留各自的匹配方式。广告构建与 Mihomo 共用输入，验证两端导出一致。地域分类的快照哈希和导出信息见[构建清单](BUILD-MANIFEST.json)。

重建到临时目录时，用 `python egern/build-rules.py --mihomo-dir mihomo/rules --geosite <GeoSite文件> --output <目录>/rules`。企业 ASN 在 `mihomo/rules/cn-services.yaml` 末尾维护。修改后在同一构建命令加 `--sync-cn-alias`，并将 `--output` 设为 `egern/rules`，同步旧订阅并生成新的 Egern 规则和清单。要记录新快照的出处，可同时传入 `--geosite-source <固定版本URL>`。

[项目使用说明](../README.md) · [广告来源与许可](../mihomo/rules/ADS-SOURCES.md) · [Egern 规则语法](https://egernapp.com/docs/configuration/rules/)
