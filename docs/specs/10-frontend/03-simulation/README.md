# 在线仿真工作台

功能包 ID：`PKG-FE-SIM` · 状态：基础组织稿；不表示包内全部需求已确认。

负责在线任务流程、运行与录制操作、主从臂监控和任务专属面板组合。

[上级大类](../README.md) · [总索引](../../README.md)

## 规范节点

| 节点 | 规范 ID | 内容 |
|---|---|---|
| [01-workflow-task-panels.md](01-workflow-task-panels.md) | `FE-SIM-WORKFLOW` | Simulation｜在线仿真工作台 |
| [02-recording-session-controls.md](02-recording-session-controls.md) | `FE-SIM-RECORDING` | 运行与录制操作区 |
| [03-leader-follower-panel.md](03-leader-follower-panel.md) | `FE-SIM-LEADER` | 实体主臂与仿真从臂 |
| [04-ah-layout-presets.md](04-ah-layout-presets.md) | `FE-SIM-LAYOUT-AH` | Simulation A–H 功能区域与任务布局 |
| [05-execution-profiles-policy-rollout.md](05-execution-profiles-policy-rollout.md) | `FE-SIM-EXECUTION` | 执行配置与模型推理入口 |

## 细化方式

每个编号文件是一个设计节点；文件内继续列正常流程、异常/取消、数据接口、未决项和验收。仅当节点能独立讨论和验收时再拆文件，不按每个按钮或前端代码组件建一份文档。

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。

- [Simulation V2｜删除、替换与待修正项](06-simulation-v2-review.md) — `FE-SIM-V2-REVIEW`，当前主图 IMG-022。
