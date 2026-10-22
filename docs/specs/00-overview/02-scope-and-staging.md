# 范围与建议分期

规范 ID：`SYS-SCOPE` · 责任层：系统 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-008](../../设计过程与Specification总册_20261021.md#doc-008) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.6（2026-10-22）｜更新日期：2026-10-22（America/Los_Angeles）；原始内容来源保留。

状态：分期为建议；V1 Waypoint 范围已由用户在 S10 明确扩展

来源：S03、S04、S05（详见[来源档案](../90-governance/06-sources.md)）

关联需求：[REQ-PRD-005](../indexes/05-requirements.md#req-prd-005)、[REQ-NAV-003](../indexes/05-requirements.md#req-nav-003)、[REQ-NAV-004](../indexes/05-requirements.md#req-nav-004)。历史排除：[REQ-NAV-001](../indexes/05-requirements.md#req-nav-001)。

## 已明确的范围边界

当前 V1 在 Scene Setup 支持地图 Waypoint 创建、编辑和保存，Simulation 展示执行进度；来源为 [S10 用户确认](../90-governance/sources/S10-waypoint-scope-confirmation.md)。旧排除项 REQ-NAV-001 / DEC-016 已被 REQ-NAV-003 / DEC-027 取代。运行中修改活动路线暂留后续扩展，不因配置编辑开放而自动支持热重规划。其他核心交互仍包括 3D 关节/TCP、键盘底盘、主臂、受控接管与录制。

## V0.6 当前阶段

[S16](../90-governance/sources/S16-mobile-first-spec-repair.md) 明确先 mobileCar 场景→运行→录制→回放，再 bimanual 组件复用；数据清理/版本/训练/预测为后续阶段。共享契约不要求一个 HostApp/全局 store；轻量视觉/IK 可独立存在。M1 的录制完整性与只读回放不因训练资格 false 被阻断，训练门控本身继续保留。

## V0.5 历史建议（首发顺序由 S16 取代）

[S15](../90-governance/sources/S15-scene-setup-first-loop.md) 保留采集到模型预测的完整目标；V0.5 曾建议 SO101/ACT 和训练前移。S16 现明确 mobileCar 采集回放优先，再 bimanual 复用；旧建议不作当前门槛。

## 从上一轮保留的分期建议（历史，不作为当前阻断条件）

| 阶段 | 建议内容 | 不能误读为 |
|---|---|---|
| P0 | Scene Setup、Simulation、Replay、基础 Dataset；基础交互与数据链路 | 用户已批准的工期或完整 V1 冻结清单 |
| P1 | 数据检查、人工干预实验、基础评估管理 | 已完整训练平台 |
| P2（历史完整平台阶段） | 完整训练管理、多模型版本、批量评估；S16 仅将模型阶段排在 M1/M2 之后，不冻结为必须等待完整 P2 | 不要求浏览器内训练，也不规定最小训练必须等待完整平台全部完成 |

原回复的优先级存在粗细粒度差异：总体“基础 Dataset”为 P0，而专题表的“Dataset Management”为 P1；Evaluation 既有 P1 管理又有 P2 批量能力。整理时采用“基础/完整”“基础/批量”的解释消除表面冲突，但仍需正式排期时确认。

Push / Grab、联合双臂 IK、精确关节直接拖动映射、完整训练框架暂不作为已冻结核心能力。该描述保留了助手建议，不替用户新增永久排除项。

## 进入实现前的最小收敛

先冻结页面与 Session 关系、Scene Setup 与运行态边界、接管流程、TCP 虚线语义和原始记录契约；再细化布局和原型。阶段标签字典不应在未经讨论时冻结为训练真值。

## 关联文档

- [产品目标与边界](01-product-boundaries.md)
- [Dataset Management｜数据管理](../10-frontend/05-datasets/01-browser-quality-export.md)
- [Model Training｜训练管理概念](../10-frontend/06-training-evaluation/01-training-workspace.md)
- [Evaluation｜评估概念](../10-frontend/06-training-evaluation/02-evaluation-workspace.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)

## V0.2 设计深度与开发路径

历史 S08/S09 和 V0.5 的阶段建议保留来源；当前执行顺序以 S16/M1/M2 为准。具体路径见 [增量路线](08-unified-development-roadmap.md)，范围变化不表示已实现。
