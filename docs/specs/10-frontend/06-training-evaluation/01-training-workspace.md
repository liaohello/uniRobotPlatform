# Model Training｜训练管理概念

规范 ID：`FE-TRAIN-WORKSPACE` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-019](../../../设计过程与Specification总册_20261021.md#doc-019) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.6（2026-10-22）｜更新日期：2026-10-22（America/Los_Angeles）；原始内容来源保留。

状态：模块需求存在；当前为概念设计

来源：S04、S05（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：[REQ-TRAIN-001](../../indexes/05-requirements.md#req-train-001)

## V0.5 当前最小范围

[S15](../../90-governance/sources/S15-scene-setup-first-loop.md) 保留数据→模型完整目标；[S16](../../90-governance/sources/S16-mobile-first-spec-repair.md) 明确当前先 mobileCar 采集/回放，再 bimanual 复用，训练/预测后续。本节最小 recipe/Job 详情在后续阶段适用，不作为 [M1/M2](../../00-overview/10-first-task-closed-loop.md) 完成条件；ACT 仍只是候选，规范不证明已接通。

模型列表只展示实际支持的方法；允许首版只有一个可选项。数据资格/兼容检查、queued/running/succeeded/failed/cancelled、错误/日志/指标、Checkpoint 和回到 Simulation 的入口必须可表达；后端不支持时不展示 Pause/Resume 为可用。真实模式无模型/后端时说明原因，Demo 的模拟进度与真实 Job 分开。

验收：[TEST-LOOP-003～005](../../40-verification/06-scene-setup-first-loop.md)。以下保留早期成熟度和能力概念背景，具体当前路线以上述 V0.5 为准。

## 历史成熟度

用户明确要求模型训练作为整体前端的独立部分；具体功能、模型列表、后端接口和 P2 排期来自助手建议，尚未冻结。

## 建议边界

前端管理独立训练后端上的作业，不在浏览器里实现 PyTorch 训练框架。主要流程：选数据版本及划分 → 选模型和配置 → 提交作业 → 监控指标/资源 → 管理 Checkpoint → 进入评估。

| 对象 | 最小关系草案 |
|---|---|
| Training Job | 指向数据版本、配置版本、后端运行与状态 |
| Metrics | 指标名、step、数值、时间与 Job |
| Checkpoint | 生成作业、训练 step、存储引用 |
| Model Version | Checkpoint、配置、数据版本及后续评估 |

BC、ACT、Diffusion Policy 为助手示例，不等于首版必须全部支持；VLA 模型的具体训练能力也不能从产品名称推导。

## 待讨论

本地 / 服务器作业接口、资源调度、停止语义、断点续训、日志持久化、配置校验、模型与动作 schema 适配、训练/验证划分规则。未决前先保留导航入口和对象关系即可，不应建立空页面来假装功能已完成。

## 关联文档

- [Dataset、Training、Checkpoint 与 Evaluation 关系](../../30-contracts/05-dataset-model-lineage.md)
- [Dataset Management｜数据管理](../05-datasets/01-browser-quality-export.md)
- [Evaluation｜评估概念](02-evaluation-workspace.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## V0.2 Prediction 回到 Simulation

Training 负责数据、作业、Loss/指标、资源、日志与 Checkpoint；Model Registry 负责版本/来源关系。选择模型后进入 [Simulation Policy Rollout](../03-simulation/05-execution-profiles-policy-rollout.md)，兼容检查后由用户启动，不在训练页复制实时机器人控制界面。周期性验证视频可以在训练页显示或链接独立 Run；Evaluation 管理判据、结果与比较。

## V0.3 配置、作业与模型页面

[Training Setup](../page-designs/08-training-setup.md) 编辑草案和提交；[Training Runs](../page-designs/09-training-runs.md) 监控已接受的配置快照。运行中修改不会更改当前 Job；Pause/Resume、参数和指标由适配器声明，未提供的 Loss 不显示假曲线。

[Model Catalog](../page-designs/11-model-catalog.md)、[My Models](../page-designs/12-my-models.md)、[Registry & Compare](../page-designs/13-model-registry-compare.md) 作为同一模型域的视图。导入、注册、适配与验证分开；按 action/observation、归一化、机器人/控制器检查后才能进入执行。图中模型名单、指标和硬件数值均非可用能力证明。

训练内验证称 Validation 并给出数据/方法来源；正式任务评估仍有独立协议与结果入口。图片中训练 Evaluation 重名入口不作为新增第二套评估系统。

## 页面图与设计归属（V0.3）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%A8%A1%E5%9E%8B%E8%AE%AD%E7%BB%83%E6%8E%A7%E5%88%B6%E5%8F%B0.png)

[PAGE-08 页面设计与修正](../page-designs/08-training-setup.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
