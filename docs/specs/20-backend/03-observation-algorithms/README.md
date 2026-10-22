# 观测、算法与任务编排

功能包 ID：`PKG-BE-OBS` · 状态：基础组织稿；不表示包内全部需求已确认。

提供传感器与变换，接入专家和学习策略，发布任务阶段与结果。

[上级大类](../README.md) · [总索引](../../README.md)

## 规范节点

| 节点 | 规范 ID | 内容 |
|---|---|---|
| [01-sensors-transforms.md](01-sensors-transforms.md) | `BE-OBSERVATION-STREAMS` | 传感器、状态与时刻变换 |
| [02-experts-policies-task-phases.md](02-experts-policies-task-phases.md) | `BE-ALGORITHM-RUNNERS` | 专家、学习策略与任务编排 |
| [03-map-waypoint-execution.md](03-map-waypoint-execution.md) | `BE-NAV-ROUTES` | 地图与 Waypoint 校验、授权和执行 |
| [04-task-assessment.md](04-task-assessment.md) | `BE-TASK-ASSESSMENT` | 任务判据、终止原因与人工辅助统计 |

## 细化方式

每个编号文件是一个设计节点；文件内继续列正常流程、异常/取消、数据接口、未决项和验收。仅当节点能独立讨论和验收时再拆文件，不按每个按钮或前端代码组件建一份文档。
