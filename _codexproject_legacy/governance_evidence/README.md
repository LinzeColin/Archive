# CodexProject 治理证据归档（已迁出项目部分）

原存于 `LinzeColin/CodexProject` 的 `governance/run_manifests/` 与 `governance/stage_gates/`，
属**已迁出项目**的历史运行证据与阶段门记录。2026-07-20 经 Owner 授权迁入本仓。

| 来源目录 | 数量 | 说明 |
|---|---|---|
| `run_manifests/` | 480 | 非 `TSK-` 前缀的遗留运行清单，属 ADP / arxiv / OpenAIDatabase / EEI / PFI / Alpha / FIFA / QBVS / Serenity-Alipay / whkmSalary / KM_IDSystem 等已迁出项目 |
| `stage_gates/` | 16 | 同上项目的阶段门记录 |

**为什么迁出**：这些项目已随仓库拆分迁往 KMOS / MetaDatabase / AgentDatabase，
其证据留在 CodexProject 只是占位，与该仓现有职责（基建/运维）无关。

**CodexProject 侧保留了什么**：本仓自身的 96 条遗留清单、72 条 `TSK-` 新证据、48 条阶段门，
均未迁出——它们记录的是 root 级治理工作，仍属该仓。

**授权与锁**：这批文件原受 `artifact_policy.json` 的 `retained_legacy_collections` 防篡改锁保护
（`mutable: false`，锁定数量与 sha256），条款为 `read_only_until_owner_authorized_migration`。
Owner 于 2026-07-20 明确授权本次迁移，CodexProject 侧已按迁出后的真实内容重新锚定基线。

本目录为只读历史记录，不参与任何 CI 门禁。
