# Evaluation｜评估概念

规范 ID：`FE-EVAL-WORKSPACE` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-020](../../../设计过程与Specification总册_20261021.md#doc-020) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.3｜更新日期：2026-10-21（America/Los_Angeles）；原始内容来源保留。

状态：助手建议；未逐项确认

来源：S05（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：[REQ-EVAL-001](../../indexes/05-requirements.md#req-eval-001)

## 当前成熟度

独立评估工作区、P1/P2 分期、批量评估均为助手提出的扩展方案。其定位是把模型、任务、配置、种子、运行证据与结果关联，便于复现实验。

## 建议流程

选择 Model Version / Checkpoint → 选择任务和场景配置版本 → 指定种子或测试集合 → 启动评估 → 在 Simulation 观察 → 从结果进入 Replay → 聚合比较。

| 指标层 | 可能内容；非冻结标准 |
|---|---|
| 任务 | 导航、停靠、可达性、抓取、保持、传递等阶段结果 |
| 控制与干预 | 接管次数、人工区间、外力扰动 |
| 数据与运行 | 记录完整性、异常、超时 |
| 对比 | 模型、配置、场景/种子及样本数量 |

成功条件必须引用对应任务的正式规范，不能在前端用一个阈值替代整个任务成功判定。导航到达不必然代表移动操作成功；干预后的结果应标明是否含人工控制或物理扰动。

自动汇总、基础运行管理与批量鲁棒性实验可分层开发，具体优先级待定。当前不从过去某个机器人实验的数值直接冻结本平台通用评估标准。

## 关联文档

- [Dataset、Training、Checkpoint 与 Evaluation 关系](../../30-contracts/05-dataset-model-lineage.md)
- [Simulation｜在线仿真工作台](../03-simulation/01-workflow-task-panels.md)
- [Replay & Annotation｜同步回放与标注](../04-replay-annotation/01-synchronized-playback.md)
- [Dataset Management｜数据管理](../05-datasets/01-browser-quality-export.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## V0.2 自主与辅助结果分组

统计自主成功率时明确样本数、分母、人工接管和外力扰动分组。Timeout/Aborted/Invalid Run 不替代完整性和训练资格；判据由 [任务评定](../../20-backend/03-observation-algorithms/04-task-assessment.md) 提供，在线执行复用 Simulation。

## V0.3 评估视图分工与比较

[Setup](../page-designs/14-evaluation-setup.md) 只配置/校验；[Running](../page-designs/15-evaluation-running.md) 管作业进度与只读在线预览；[Results](../page-designs/16-evaluation-results.md) 管固定报告与 Episode 证据；[Comparison](../page-designs/17-batch-comparison.md) 管已有批次对照。运动接管仍跳统一 Simulation。完成报告上的 Edit 应复制为新评估草案。

[比较契约](../../30-contracts/09-evaluation-comparison.md) 统一模型与批次比较的证据、分母、统计单位及可比较性。图片中的多行 Running、不同协议排名和统计曲线不自动纳入 V1；批次可以串行产生，缺证据不造 mean±std/CI 或雷达。

## 页面图与设计归属（V0.3）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E8%AF%84%E4%BC%B0%E6%8E%A7%E5%88%B6%E5%8F%B0.png)

[PAGE-14 页面设计与修正](../page-designs/14-evaluation-setup.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
