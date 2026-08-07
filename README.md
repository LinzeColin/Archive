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

---

## 云成本红线：对象存储必须零付费（Owner 硬指令 · 长期有效）

**云端账单必须恒为 $0.00。不允许任何 agent 触发收费行为。**

1. **禁止 `InfrequentAccess` 存储类** —— 建桶、写对象、生命周期转换，一律不许。
   R2 的免费额度（10GB 存储 / 100 万 Class A / 1000 万 Class B）**只覆盖 Standard**；
   IA 从第 1 次操作起计费，且**按整计费单位向上取整**。
   2026-08-07 实账单：**51 次 IA 操作 = $9.00**，同期 **301 万次 Standard 操作 = $0.00**。
   根因是建桶时默认存储类选了 IA，写入端不指定存储类就全部继承 —— 一次手滑，之后静默自动计费。
2. **禁止"整包下载来判断存在 / 做校验"的高频轮询。** 判断对象存在用 `HeadObject`
   （写入时把 sha256 放进对象 `Metadata`，Head 就读得到）；真要逐字节复核，
   **按天或按周跑，不许按分钟跑**。
   反例：memory-atlas reconcile 每 15 分钟把 2466 个对象整包拉一遍核 sha256，
   折合 71 万次 Class B/天、21.3M/月，直接打穿 10M/月免费额度。
3. **新增或改动任何周期性任务，先算月操作量**：
   `每轮操作数 × 每天轮数 × 31 < 免费额度 × 50%`。**算不出来就不上线。**
4. **存储优先级**：**GitHub Release 资产 > R2 > OVH 本地**。
   Release 资产不计仓库体积、没有操作计费，永远优先。

完整事故记录、账单逐行归因、免费额度速查表 → **`Private-Database` 仓 `OPS/AGENT_ONBOARDING.md` §9.7**。
机器守卫 → OVH `/usr/local/bin/linze-r2-free-tier-guard.py`（每 6 小时，非 Standard 桶自动熔断改回；
判定 `/srv/linze/apps/status/data/r2_free_tier_guard.json`）。
