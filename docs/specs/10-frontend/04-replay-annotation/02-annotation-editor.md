# 阶段、事件与标注编辑

规范 ID：`FE-REPLAY-ANNOTATION` · 责任层：前端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-017](../../../设计过程与Specification总册_20261021.md#doc-017)、[doc-030](../../../设计过程与Specification总册_20261021.md#doc-030)、[doc-033](../../../设计过程与Specification总册_20261021.md#doc-033)、[doc-039](../../../设计过程与Specification总册_20261021.md#doc-039)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-ANN-001](../../indexes/05-requirements.md#req-ann-001)、[REQ-REPLAY-002](../../indexes/05-requirements.md#req-replay-002)

## 目标与责任边界

负责历史 Episode 的标签候选、区间选择、修订和确认界面。原始状态与动作保持只读，标注写入独立层；标签字典和区间规则仍待讨论。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 显示 | 原始事件、阶段标签、控制来源使用可辨识轨道；不把人工接管等同于新任务阶段。 |
| 编辑 | 选择时间区间、添加/修改标签、保存修订属于方案；边界、重叠及多臂作用域待定。 |
| 来源 | 区分在线事件、自动候选与人工确认，展示来源和修订关系。 |
| 结果 | 人工判断与自动任务结果不相互覆盖；具体审核流程待定。 |

## 未决与依赖

关联 OQ-021、OQ-023。当前不冻结导航、近场和双臂阶段字典，也不默认要求遥操作时逐动作手工打标。

## 关联规范

- [Replay & Annotation｜同步回放与标注](01-synchronized-playback.md)
- [统一时间轴与事件轨](../08-observation-inspector/03-timeline-event-tracks.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)
- [回放、标注与数据管理验收](../../40-verification/03-replay-data-acceptance.md)

## 验收入口

- [TEST-ANN-001](../../40-verification/03-replay-data-acceptance.md#test-ann-001)（现有草案，未执行；依赖的未决规则须先收敛）。

## V0.2 标注类型与训练用途

| 类别 | 内容 | 规划范围 |
|---|---|---|
| Task Metadata | 指令、任务/目标描述 | 优先基础能力 |
| Phase | 全局/部件语义区间 | 字典与区间边界继续讨论 |
| Outcome / Failure | 成功、滑脱、碰撞、超时等原因 | 自动结果与人工审核独立 |
| Perception | 框、类别、位姿、掩码 | 按感知用途扩展，不把完整图像标注工具塞入首版 |

训练所需标签由 Export/Training Profile 声明；不能因未来可能用 VLA 就要求所有 ACT/BC 类数据具备人工阶段或语言标签。自动仿真真值、模型预测、自动候选、人工审核分别带来源；原始控制源/事件不能被可编辑标签覆盖。缺失必需标签才影响对应用途资格，不把所有未标注 Episode 标成无效。

关联 [Episode 契约](../../30-contracts/03-episode-events-annotations.md)、[任务评定](../../20-backend/03-observation-algorithms/04-task-assessment.md)。

## 页面图与设计归属（V0.3）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E5%9B%9E%E6%94%BE%E4%B8%8E%E6%A0%87%E6%B3%A8%E7%95%8C%E9%9D%A2.png)

[PAGE-05 页面设计与修正](../page-designs/05-episode-detail.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
