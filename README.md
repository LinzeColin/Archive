# Archive

LinzeColin 的冷归档仓：退役 / 参考项目的源码，以真实目录保存（非 submodule 索引）。

## 📦 数据落地政策（长期有效 · 自运行分仓治理）

**本仓只归档代码与内容，长期/业务/运行时数据不入本仓。** 任何需长期存储的数据一律写入私有仓
`LinzeColin/Private-Database` 对应数据区（其余项目数据 → `Private-MetaDatabase/`），用 `private_db_client.py`
免 clone 读写；Private-Database 禁止 `git clone`；派生/临时物走 `.gitignore`。
**一次分清、长期自运行，不再需要人工反复迁移。**

## 归档项目

| 目录 | 说明 |
| --- | --- |
| `COM1005` | 课程归档（内容归档） |
| `Linear-Regression-Live-Series` | 线性回归直播系列（内容归档） |
| `nab` | 从 `LinzeColin/CodexProject` 迁入的 Cloudflare L2 展示（内容归档） |
| `CodexTokenMonitor` | 退役的 token 用量监控工具（已双平面治理） |
| `EVA_OS` | 退役项目（已双平面治理） |
| `_codexproject_legacy` | 仓库拆分时从 CodexProject 迁出的遗留资产 |

## 规则

- 把本仓当作源码级归档中心：保持各归档目录可读、自包含。
- 冷归档默认不再开发；确需改动时，收尾同样遵循"合进 main、无遗留分支/PR"。
