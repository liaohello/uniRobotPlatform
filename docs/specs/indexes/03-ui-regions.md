# 按前端功能区域查找

这是“看见一个区域后去哪找规则”的辅助索引。区域位置和宽度尚未冻结；同一组件可在不同工作区移动，主责规范不随面板位置变化。

| 界面区域 / 目的 | 主要功能 | 主责节点 |
|---|---|---|
| 全局顶部/导航 | 项目、机器人、场景、工作区、在线 Session | [全局信息架构与工作区](../10-frontend/01-shell/01-navigation-context.md)、[独立状态域与运行模型](../00-overview/04-runtime-state-domains.md) |
| 全局状态/控制区 | 控制源、接管、运行、录制与原因反馈 | [控制权与受控人工接管](../30-contracts/06-control-authority.md)、[Simulation｜在线仿真工作台](../10-frontend/03-simulation/01-workflow-task-panels.md) |
| 层级树 | Link/Joint/Arm、物体选择与定位 | [选择、相机与整臂框选](../10-frontend/07-viewport-tools/02-selection-camera.md)、[Inspector 与层级联动](../10-frontend/08-observation-inspector/01-hierarchy-inspector.md) |
| 中央 3D 视口 | 观察、选择、坐标系、工具、目标与实际 | [共用 3D Viewport](../10-frontend/07-viewport-tools/01-viewport-contexts.md)、[选择、相机与整臂框选](../10-frontend/07-viewport-tools/02-selection-camera.md)、[关节操控与监控](../10-frontend/07-viewport-tools/03-joint-manipulation.md)、[TCP 操控与虚线运动轨迹](../10-frontend/07-viewport-tools/04-tcp-trajectories.md)、[物理受力与临时工具](../10-frontend/07-viewport-tools/05-physical-force-tool.md) |
| 属性/监控区 | Actual/Target、限位、TCP、夹爪、控制源 | [Inspector 与层级联动](../10-frontend/08-observation-inspector/01-hierarchy-inspector.md)、[关节操控与监控](../10-frontend/07-viewport-tools/03-joint-manipulation.md) |
| 传感器/算法区 | 相机、RGB-D、SLAM/路径、点云等能力视图 | [传感器与算法观测面板](../10-frontend/08-observation-inspector/02-sensors-algorithms.md)、[任务、观测与数据配置](../00-overview/03-task-and-observation-profiles.md) |
| 时间轴/分析区 | 曲线、事件、控制来源与阶段 | [统一时间轴与事件轨](../10-frontend/08-observation-inspector/03-timeline-event-tracks.md)、[Replay & Annotation｜同步回放与标注](../10-frontend/04-replay-annotation/01-synchronized-playback.md) |
| 主臂设备区 | 连接、标定、映射与跟踪误差，无独立主臂相机 | [实体主臂与仿真从臂](../10-frontend/03-simulation/03-leader-follower-panel.md) |
| 场景编辑流程 | 初态、任务配置、检查和保存 | [Scene Setup｜场景布置](../10-frontend/02-scene-setup/01-workflow-initial-state.md) |
| 数据列表/详情 | Episode、结果、完整性和用途资格 | [Dataset Management｜数据管理](../10-frontend/05-datasets/01-browser-quality-export.md) |
| 训练/评估页面 | 作业、指标、模型与结果关系 | [Model Training｜训练管理概念](../10-frontend/06-training-evaluation/01-training-workspace.md)、[Evaluation｜评估概念](../10-frontend/06-training-evaluation/02-evaluation-workspace.md)、[Dataset、Training、Checkpoint 与 Evaluation 关系](../30-contracts/05-dataset-model-lineage.md) |
| 折叠/拖动/快捷键 | 布局、输入焦点和持续输入清理 | [面板布局与输入焦点](../10-frontend/01-shell/02-layout-input-focus.md) |

[前端目录](../10-frontend/README.md) · [前后端功能映射](06-feature-map.md)

## A–H 与新增场景工具

Simulation 区域对应 A Header、B Runtime、C Authority、D Hierarchy、E Viewport、F Inspector、G Sensors、H Timeline，详见 [布局节点](../10-frontend/03-simulation/04-ah-layout-presets.md)。准备阶段另见 [模板配置](../10-frontend/02-scene-setup/02-task-template-configuration.md)、[SO101 俯视摆放](../10-frontend/02-scene-setup/03-so101-tabletop-layout.md)、[地图 Waypoint 编辑](../10-frontend/02-scene-setup/04-map-waypoint-editor.md)。

## 图示入口

每个业务页面的区域表及原图见 [页面设计索引](../10-frontend/page-designs/README.md)。Simulation A–H 只用于在线工作台，其他页面按对象重新安排；资源/数据/结果页不复制在线运行栏。
