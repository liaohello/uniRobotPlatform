# 专家、学习策略与任务编排

规范 ID：`BE-ALGORITHM-RUNNERS` · 责任层：后端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-007](../../../设计过程与Specification总册_20261021.md#doc-007)、[doc-009](../../../设计过程与Specification总册_20261021.md#doc-009)、[doc-013](../../../设计过程与Specification总册_20261021.md#doc-013)、[doc-020](../../../设计过程与Specification总册_20261021.md#doc-020)、[doc-033](../../../设计过程与Specification总册_20261021.md#doc-033)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-OBS-004](../../indexes/05-requirements.md#req-obs-004)、[REQ-NAV-002](../../indexes/05-requirements.md#req-nav-002)、[REQ-REC-001](../../indexes/05-requirements.md#req-rec-001)

## 目标与责任边界

接入导航/SLAM、视觉伺服、IK/动作规划与后续学习策略，发布运行状态、阶段、来源和任务结果。界面显示算法过程，计算在服务器完成。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 经典专家 | 小车导航与近场操作、双臂动作规划分别适配；IK 终点不能独自构成完整专家演示。 |
| Policy | 输出通过共同控制边界，受控接管时停止对应范围输出。 |
| 任务阶段 | 全局与部件阶段、事件和成功判据需要任务专属定义，词表不在本轮冻结。 |
| 导航边界 | 后端可产生专家目标，也接收 Scene Setup 的保存路线；Simulation 展示执行状态，活动路线新授权规则见 [路线执行](03-map-waypoint-execution.md)。 |

## 未决与依赖

关联 OQ-012、OQ-018、OQ-023、OQ-028。完整 VLN/VLA、通用专家和成功率不能从界面入口推断为已完成。

## 关联规范

- [任务、观测与数据配置](../../00-overview/03-task-and-observation-profiles.md)
- [控制权与受控人工接管](../../30-contracts/06-control-authority.md)
- [Evaluation｜评估概念](../../10-frontend/06-training-evaluation/02-evaluation-workspace.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)
- [范围与建议分期](../../00-overview/02-scope-and-staging.md)

## 验收入口

- [TEST-REC-001](../../40-verification/02-workspace-runtime-acceptance.md#test-rec-001)（现有草案，未执行；依赖的未决规则须先收敛）。
