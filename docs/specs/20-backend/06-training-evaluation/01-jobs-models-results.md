# 训练作业、模型版本与评估结果

规范 ID：`BE-MODEL-JOBS` · 责任层：后端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-019](../../../设计过程与Specification总册_20261021.md#doc-019)、[doc-020](../../../设计过程与Specification总册_20261021.md#doc-020)、[doc-034](../../../设计过程与Specification总册_20261021.md#doc-034)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-TRAIN-001](../../indexes/05-requirements.md#req-train-001)、[REQ-TRAIN-002](../../indexes/05-requirements.md#req-train-002)、[REQ-EVAL-001](../../indexes/05-requirements.md#req-eval-001)

## 目标与责任边界

作为后续服务边界管理训练/评估作业和模型来源关系，不在浏览器内训练。当前只整理概念，不规定支持的全部算法与资源调度实现。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 训练 | 绑定数据/划分/配置版本，输出作业状态、指标、日志与 Checkpoint。 |
| 模型 | 模型版本关联权重、推理配置与动作/观测兼容性。 |
| 评估 | 绑定模型、任务、场景/种子与 Episode，按任务判据给出结果。 |
| 追踪 | 从评估回到模型、训练数据与原始轨迹，结果来源不凭文件名判断。 |

## 未决与依赖

关联 OQ-027、OQ-028。六工作区、模型列表与分期仍为建议；作业接口、停止/续训和资源策略待设计。

## 关联规范

- [Model Training｜训练管理概念](../../10-frontend/06-training-evaluation/01-training-workspace.md)
- [Evaluation｜评估概念](../../10-frontend/06-training-evaluation/02-evaluation-workspace.md)
- [Dataset、Training、Checkpoint 与 Evaluation 关系](../../30-contracts/05-dataset-model-lineage.md)
- [Dataset Management｜数据管理](../../10-frontend/05-datasets/01-browser-quality-export.md)

## 验收入口

- [TEST-TRACE-001](../../40-verification/03-replay-data-acceptance.md#test-trace-001)（现有草案，未执行；依赖的未决规则须先收敛）。

## V0.3 对界面状态的供给

训练适配器声明可用方法、参数、指标和 Job 控制；只有实际支持才提供 Pause/Resume。接受配置后保存不可变作业快照。模型权重导入、版本注册、IO/动作/归一化适配和运行验证分别记录，未知能力不给虚构 Ready。

评估编排与比较拆见 [评估报告与比较服务](02-evaluation-comparison.md)，复用原 Session/Ownership/Recording；页面呈现多个 Run 不等于后端已支持并行调度。

## V0.5 首条闭环职责

V0.5 曾建议将一个训练 recipe 前移；[V0.6 当前基线](../../00-overview/10-first-task-closed-loop.md) 已由用户明确改为 mobileCar 四步闭环优先、bimanual 复用其次、训练/预测后续。本节训练职责在对应阶段适用，不作为 M1 前置。最小服务接受固定数据版本/split/配置，返回真实 Job 状态、错误、日志/指标和可加载 Checkpoint。建议复用既有 bimanual ACT，但实际可用参数/IO/环境需接入核验；目录中存在一个命令不表示本服务已实现。

模型适配必须核对相机键/预处理、机器人、动作维度/顺序/单位/绝对或增量语义/周期和归一化；加载成功后仍须通过 Simulation 的显式启动和真实 rollout。训练失败、取消或策略零成功率如实记录；本轮不追加任何策略成功保证。完整来源字段见 [CT-LINEAGE](../../30-contracts/05-dataset-model-lineage.md)，验收 [TEST-LOOP-004/005](../../40-verification/06-scene-setup-first-loop.md)。
