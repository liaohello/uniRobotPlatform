# 按机器人与任务配置查找

当前已确认 **mobileCar 场景→运行→录制→回放优先，再 bimanual 组件复用，训练后续**，范围和适用验收见 [当前开发基线](../00-overview/10-first-task-closed-loop.md)。SO101/ACT 的旧首发建议不再作为当前门槛。三图共用 [Scene Setup](../10-frontend/page-designs/02-scene-setup.md)；以下任务目录是能力范围导航，不表示首版同时接通所有任务。

索引 ID：`IDX-ROBOT-TASKS`。机器人任务差异已有用户来源；任务配置的字段、阶段词表和默认布局仍是草案。本索引不为两个机器人复制整套前后端规范。

| 任务线 | 前端重点 | 后端重点 | 当前边界 |
|---|---|---|---|
| LanderPi 导航 | [观测面板](../10-frontend/08-observation-inspector/02-sensors-algorithms.md)、[在线任务流程](../10-frontend/03-simulation/01-workflow-task-panels.md) | [专家与任务编排](../20-backend/03-observation-algorithms/02-experts-policies-task-phases.md)、[底盘控制](../20-backend/02-robot-control/02-joint-base-gripper.md) | Scene Setup 支持 Waypoint 编辑/保存，Simulation 展示进度；后端导航仍可生成专家数据 |
| LanderPi 近场操作 | [Joint](../10-frontend/07-viewport-tools/03-joint-manipulation.md)、[TCP/轨迹](../10-frontend/07-viewport-tools/04-tcp-trajectories.md)、[观测面板](../10-frontend/08-observation-inspector/02-sensors-algorithms.md) | [IK/轨迹执行](../20-backend/02-robot-control/03-ik-planning-execution.md)、[观测与变换](../20-backend/03-observation-algorithms/01-sensors-transforms.md) | 可达性、视觉伺服、路径检查和物理成功分别表达；不把单点 IK 当完整抓取专家 |
| SO101 双臂操作 | [选择与整臂框选](../10-frontend/07-viewport-tools/02-selection-camera.md)、[主臂面板](../10-frontend/03-simulation/03-leader-follower-panel.md)、[任务观测](../10-frontend/08-observation-inspector/02-sensors-algorithms.md) | [主臂桥](../20-backend/02-robot-control/05-leader-device-bridge.md)、[控制权](../20-backend/02-robot-control/01-ownership-takeover.md)、[专家编排](../20-backend/03-observation-algorithms/02-experts-policies-task-phases.md) | 多臂选择不自动联合控制；实体主臂无独立摄像头；任务三相机按实际配置提供 |

共用 [任务/观测/记录配置](../00-overview/03-task-and-observation-profiles.md)、[机器人能力](../00-overview/06-robot-capabilities.md)、[Episode 契约](../30-contracts/03-episode-events-annotations.md)、[回放与标注](../10-frontend/04-replay-annotation/README.md)。

不同任务的 UI、算法观测和原始记录配置分别定义；隐藏面板不改变算法输入或录制。语义阶段、控制来源和采集用途独立，阶段词表仍按未决问题继续讨论。

[总索引](../README.md) · [工作区索引](02-workspaces.md) · [功能映射](06-feature-map.md)

## V0.2 模板目录

导航三类、感知四类、固定/底盘辅助 IK 及双臂直接/台面/空中交接的差异统一在 [任务模板目录](../00-overview/07-task-template-catalog.md) 维护；拧螺丝为远期意图，不被模板清单升级为 V1 承诺。
