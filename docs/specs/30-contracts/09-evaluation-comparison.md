# 评估报告与比较证据契约

规范 ID：`CT-EVAL-COMPARISON` · 责任层：共享契约 · 版本：V0.3（2026-10-21）

状态：V0.3 接口语义草案，字段名与序列化尚未冻结。本契约约束页面口径，不声明服务已经实现。

[模型与数据来源](05-dataset-model-lineage.md) · [任务评定](../20-backend/03-observation-algorithms/04-task-assessment.md) · [后端职责](../20-backend/06-training-evaluation/02-evaluation-comparison.md)。

## 对象与身份

| 对象 | 必须可追溯的含义 |
|---|---|
| Evaluation Config Revision | 模型/Checkpoint、任务与判据、场景/机器人/环境版本、执行与人工辅助政策、种子或测试清单、记录配置 |
| Evaluation Run | 接受的配置快照、实际运行环境/适配器版本、执行清单和作业生命周期 |
| Episode Evidence | Episode、任务结果、终止原因、完整性、可评定性、干预/外力/辅助记录、指标原始依据 |
| Report Revision | 固定的输入证据集合、指标定义版本、聚合规则、生成时间和缺失项 |
| Comparison Manifest | 指向确定的 Report/Model Version，比较维度、差异、分组、可比较性与聚合方法 |

运行中修改阈值/场景生成新配置；历史报告不原地改判。允许补充后处理的新报告修订，但必须给出来源与改判理由。前端表格、摘要、图表和导出报告引用同一个 Report Revision。

## 比较维度

默认按任务/判据版本、机器人与动作观测语义、环境/场景版本、测试清单与随机化、辅助政策和指标定义检查共同条件。模型作为被比较变量可以不同；若实验本就研究随机化或数据配方差异，必须声明自变量与控制条件，不能称所有条件相同。

后端返回 `comparable`、`descriptive_only` 或 `insufficient_evidence` 的语义状态及具体差异；精确枚举待接口冻结。Same Eval Only 是查询过滤，不能由开关自行赋予可比较性。跨不同任务/环境的分数可陈列，默认不合成无依据的最佳排名。

## 分母与人工辅助

- 分别保留 planned、started、finalized、evaluable、invalid、assisted 的计数及排除理由；pending 不计为已失败。
- 任务成功、终止原因、人工辅助、外力扰动、完整性与评估有效性独立。Intervened 不是与 Success 互斥的任务结果。
- 候选自主指标：在符合协议的已启动自主尝试中，无人工接管完成的成功数为分子；人工接管后救回的尝试不得从分母中悄悄剔除来提高自主成功率。具体纳入/终止规则由协议修订确定。
- 另报辅助成功率和人工接管率，写清各自分母。若只统计“从未干预子集”，必须注明条件化筛选，不能替代主自主指标。
- 无法评定、故障中止和缺数据按协议报告，不写成 0 成功，也不把有效性问题隐藏在成功均值里。

## 统计定义

每个指标带名称、单位、统计单位（Episode/Run/Seed）、样本量、适用样本选择、定义/分母、聚合方法和缺失原因。阶段成功率说明分母是全部尝试还是进入该阶段的尝试；导航与操作阶段不共用未说明的口径。

单次成功率显示计数/分母。跨重复 Run/Seed 的 mean±std 仅在有相应重复证据且定义明确时提供；置信区间记录方法和假设，不能只从界面切换按钮编造。延迟等连续量的帧/Step 与 Episode 样本不能混用。无扰动实验时不生成鲁棒性雷达。

## 来源关系

P13 模型比较和 P17 批次比较都引用 Comparison Manifest；一个以模型版本为索引，一个以评估 Run/条件为索引。结果可回到原始 Episode、配置和模型来源，不凭文件名或图片上的标签建立关系。

关联需求：[REQ-EVAL-002](../indexes/05-requirements.md#req-eval-002)。验收：[TEST-EVAL-002](../40-verification/05-visual-page-consistency.md#test-eval-002)、[TEST-EVAL-003](../40-verification/05-visual-page-consistency.md#test-eval-003)。
