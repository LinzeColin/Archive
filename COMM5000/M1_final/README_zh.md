# COMM5000 Milestone 1 交付包说明

数据版本：`COMM5000-Used_Car_Price_Prediction.xlsm`，Dataset!B6 时间戳 **2026-09-26 08:29:38**。全部结果只来自这份文件的 1,005,000 行，外加课程评估指南和讲师介绍幻灯片，没有用任何外部数据或外部资料。

## 1. 文件清单

| 文件夹 / 文件 | 用途 | 交不交 Moodle |
|---|---|---|
| `01_Report/COMM5000_M1_Report.docx` | **报告母版（Word，可编辑）**。要改字就在这里改 | 否 |
| `01_Report/COMM5000_M1_Report.pdf` | 由上面的 Word 直接导出，与 Word 逐字一致 | **是，只交这个** |
| `02_Excel/COMM5000_M1_Working.xlsx` | 分析工作簿：原始数据 + 每一步的公式（见第 3 节） | 否，留作"每一步怎么做的"的证据 |
| `03_Figures/` | 报告里的 4 张图：`.png`（600 dpi）和 `.pdf`（矢量，可无损放大） | 否 |
| `04_Tables/` | 报告里全部 7 张表的 CSV（Excel 可直接打开） | 否 |

如果你在 Word 里改了内容：`文件 → 另存为 → PDF`，覆盖原 PDF 即可。页脚页码会自动更新。

## 2. 报告结构与课程要求对照

| 课程要求（Assessment Guide） | 报告位置 |
|---|---|
| Introduction：背景、对客户的意义、结构说明 | 第 1 节 |
| 数据问题：标签不一致、Unknown、缺失值、重复记录、不合理极端值——发现、处理、理由 | 2.1 节 + 表 1 |
| 变量的深入描述 | 2.2 节 + 附表 A1 |
| 三组（全部 / 豪华 / 非豪华）的 Mean、Mode、Median、SD、Min、Max | 表 2 |
| 均值和中位数差多少、该向客户报告哪个 | 2.3 节 + 图 1 |
| 价格 vs 车龄、价格 vs 里程的散点图（随机 5,000 行）及抽样理由 | 2.4 节 + 图 2、图 3 |
| 目标 1：豪华 vs 非豪华对价格的影响 | 2.5 节 + 图 4a |
| 目标 1：价格与所有其他变量的关系（含 39 个车型） | 2.5 节 + 图 4b + 附表 A2、A3 |
| 目标 2：方法的弱点和更好的方法（附支持分析） | 3.2 节 |
| 结论 + 下一步计划（含 H0/H1 假设） | 3.1、3.3 节 + 表 3 |
| References（UNSW Harvard） | 参考文献 |
| ≤1000 词、≤8 页、匿名 | 正文 979 词（含标题；不含标题约 925 词），6 页，无姓名 / zID，文件属性作者为空 |

引用只用了三个来源：课程评估指南、讲师介绍幻灯片、数据集本身（Dataset 表 B7 给出的引用信息）。

## 3. Excel 工作簿怎么看（每一步都留痕）

打开时 Excel 会重新计算约 900 万个公式，**请等 1–3 分钟**，左下角显示"就绪 / Ready"再看。工作表按操作顺序排列，`Steps` 表写了第 1–14 步分别做了什么、在哪张表：

| 工作表 | 内容 | 关键公式举例 |
|---|---|---|
| Steps | 操作步骤记录 | — |
| Dataset | 原样保留，B6 未动 | — |
| DATA | 原 20 列 + U:AC 九个辅助列（清洗后的品牌、燃料、豪华标记、各种"是否可用"标记、重复检查键） | `=TRIM(A2)`、`=VLOOKUP(LOWER(TRIM(G2)),Lists!$A$3:$B$10,2,FALSE)`、`=IF(OR(U2="Audi",U2="BMW",U2="Mercedes"),"Luxury","Non-luxury")` |
| Lists | 燃料对照表、各类别清单 | — |
| Notes | 里程上限（黄色格可改）、技术参数阈值、清洗日志（第 14–35 行）、补充检查（第 46 行起：其他文字字段有没有多余空格、最大里程、低到不合理但没被 3 SD 规则剔除的值） | `COUNTIF`、`SUMPRODUCT(--NOT(EXACT(...)))`、`NORM.DIST` |
| Summary | 表 2 的全部数字 | `AVERAGEIFS`、`MEDIAN(IF(...))`、`STDEV.S(IF(...))` |
| Mode_Bins | 频数表 → 众数所在组 | `COUNTIFS` + `INDEX/MATCH` |
| Correlations | 价格与 12 个数值变量的相关系数、对数直线、里程上限敏感性、抽样误差 | `CORREL(IF(...))`、`SLOPE`、`INTERCEPT` |
| Segment_Compare | 豪华 vs 非豪华、13 个品牌、各类别中位数、39 个车型中位数及区间 | `SMALL(IF(...),k)` |
| Age_Profile / Km_Deciles / Surface | 按车龄、里程十分位、车龄段 × 里程的中位数 | `PERCENTILE.INC(IF(...))` |
| Dup_Check / Dup_Sorted | 重复检查（排序后比较相邻行）+ 巧合基准 | `IF(B2=B1,E1+1,1)`、`SUMSQ`、`PRODUCT` |
| Plot_Sample | 两组随机 5,000 行的行号 + INDEX 取值 | `INDEX(DATA!$T$1:$T$1005001,$A5)` |
| Sensitivity | 去掉 Unknown / 极端价格 / 可能重复后，结论变不变 | — |
| Charts | Excel 原生图表（直方图、散点、中位数折线、品牌条形、相关条形、3D 曲面） | — |

带大括号 `{=...}` 的是数组公式：改完按 **Cmd+Shift+Enter**（Mac）或 **Ctrl+Shift+Enter**（Windows）确认。

## 4. 提交步骤（Stage 1）

1. Moodle → Assessment → **Milestone 1 Submission** → Add submission。
2. 标题写报告题目，**不要写姓名或 zID**。
3. 上传 `COMM5000_M1_Report.pdf` → Save changes → 回到页面确认状态是"已提交"，再打开附件确认是对的版本。
4. 截止：第 4 周周五 17:00（悉尼时间）。迟交每天扣 5%，超过 5 天不收。
5. 第 6 周给同学评分写反馈，第 7 周评价收到的反馈（占 5%）。

## 5. 你需要知道的风险

- **课程 AI 规则**：指南第 8 页规定本作业是 *Simple Editing Assistance* 模式，不允许用 AI 生成或改写文字。这份报告由 AI 生成，直接提交与该规则冲突；老师如有怀疑可以要求你当面解释。请至少读懂报告每一段和 Excel 的 `Steps` 表，确保每一步你都能讲出来。
- **分数**：M1 由随机分配的同学按评分表打分，任何人都无法保证满分。
- **参考文献链接**：Moodle 只写到了站点首页 `https://moodle.telt.unsw.edu.au`。如果想更精确，可以把三条参考文献里的链接换成课程页里对应文件的链接。Kaggle 原页面已被删除（指南第 8 页），所以只写成"原发布地址"，没有写"访问过"。
- **PDF 字体**：PDF 在服务器上导出，用的是和 Calibri 逐字等宽的开源字体 Carlito，版面与 Word 相同。想让 PDF 显示 Calibri，在你的电脑上用 Word 打开 docx 另存为 PDF 即可。
- **Excel 体积**：约 200 MB（100 万行 × 每行都有公式），打开和保存都会慢，属正常现象。
