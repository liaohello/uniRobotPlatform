# 按功能贯通前端、后端、契约与验收

同一业务功能横跨多个责任层，但每条规则只有一个主责位置。下表是交叉导航，不表示列出的能力全部已实现。

| 功能 | 前端主责 | 后端主责 | 共享契约/模型 | 待执行验收 |
|---|---|---|---|---|
| 场景加载与初态 | [Scene Setup｜场景布置](../10-frontend/02-scene-setup/01-workflow-initial-state.md) | [后端功能节点](../20-backend/01-session-scene/02-scene-config-versions.md) | [Robot / World State 契约草案](../30-contracts/01-robot-world-state.md)、[Episode、采集、事件与标注契约](../30-contracts/03-episode-events-annotations.md) | [TEST-SCENE-002](../40-verification/02-workspace-runtime-acceptance.md#test-scene-002)、[TEST-SCENE-003](../40-verification/02-workspace-runtime-acceptance.md#test-scene-003) |
| 运行/录制操作 | [Simulation｜在线仿真工作台](../10-frontend/03-simulation/01-workflow-task-panels.md) | [后端功能节点](../20-backend/01-session-scene/01-session-lifecycle.md) | [独立状态域与运行模型](../00-overview/04-runtime-state-domains.md)、[Episode、采集、事件与标注契约](../30-contracts/03-episode-events-annotations.md) | [TEST-REC-004](../40-verification/02-workspace-runtime-acceptance.md#test-rec-004) |
| 选择与整臂框选 | [选择、相机与整臂框选](../10-frontend/07-viewport-tools/02-selection-camera.md) | 纯观察选择无需下发运动命令；后端仅提供身份/状态 | [Robot / World State 契约草案](../30-contracts/01-robot-world-state.md)、[控制权与受控人工接管](../30-contracts/06-control-authority.md) | [TEST-SEL-002](../40-verification/01-interaction-acceptance.md#test-sel-002)、[TEST-SEL-006](../40-verification/01-interaction-acceptance.md#test-sel-006) |
| 关节控制与监控 | [关节操控与监控](../10-frontend/07-viewport-tools/03-joint-manipulation.md) | [后端功能节点](../20-backend/02-robot-control/02-joint-base-gripper.md) | [控制与干预命令契约草案](../30-contracts/02-control-intervention-commands.md)、[Robot / World State 契约草案](../30-contracts/01-robot-world-state.md) | [TEST-JOINT-001](../40-verification/01-interaction-acceptance.md#test-joint-001)、[TEST-JOINT-002](../40-verification/01-interaction-acceptance.md#test-joint-002) |
| TCP 与虚线轨迹 | [TCP 操控与虚线运动轨迹](../10-frontend/07-viewport-tools/04-tcp-trajectories.md) | [后端功能节点](../20-backend/02-robot-control/03-ik-planning-execution.md) | [控制与干预命令契约草案](../30-contracts/02-control-intervention-commands.md)、[时间、坐标系与命令生命周期](../30-contracts/04-time-frames-units.md) | [TEST-TCP-001](../40-verification/01-interaction-acceptance.md#test-tcp-001)、[TEST-TCP-002](../40-verification/01-interaction-acceptance.md#test-tcp-002)、[TEST-TCP-003](../40-verification/01-interaction-acceptance.md#test-tcp-003) |
| VLA 人工接管 | [接管与状态反馈](../10-frontend/01-shell/03-authority-status-feedback.md) | [后端功能节点](../20-backend/02-robot-control/01-ownership-takeover.md) | [控制权与受控人工接管](../30-contracts/06-control-authority.md)、[控制与干预命令契约草案](../30-contracts/02-control-intervention-commands.md) | [TEST-AUTH-002](../40-verification/01-interaction-acceptance.md#test-auth-002)、[TEST-AUTH-003](../40-verification/01-interaction-acceptance.md#test-auth-003) |
| 外力干预 | [物理受力与临时工具](../10-frontend/07-viewport-tools/05-physical-force-tool.md) | [后端功能节点](../20-backend/02-robot-control/04-physical-intervention.md) | [控制与干预命令契约草案](../30-contracts/02-control-intervention-commands.md)、[Episode、采集、事件与标注契约](../30-contracts/03-episode-events-annotations.md) | [TEST-FORCE-002](../40-verification/01-interaction-acceptance.md#test-force-002)、[TEST-REC-002](../40-verification/02-workspace-runtime-acceptance.md#test-rec-002) |
| 实体主臂 | [实体主臂与仿真从臂](../10-frontend/03-simulation/03-leader-follower-panel.md) | [后端功能节点](../20-backend/02-robot-control/05-leader-device-bridge.md) | [机器人能力与适配边界](../00-overview/06-robot-capabilities.md)、[控制与干预命令契约草案](../30-contracts/02-control-intervention-commands.md)、[Episode、采集、事件与标注契约](../30-contracts/03-episode-events-annotations.md) | [TEST-LEADER-002](../40-verification/02-workspace-runtime-acceptance.md#test-leader-002) |
| 观测与算法 | [传感器与算法观测面板](../10-frontend/08-observation-inspector/02-sensors-algorithms.md) | [后端功能节点](../20-backend/03-observation-algorithms/README.md) | [Robot / World State 契约草案](../30-contracts/01-robot-world-state.md)、[时间、坐标系与命令生命周期](../30-contracts/04-time-frames-units.md) | [TEST-PROFILE-001](../40-verification/02-workspace-runtime-acceptance.md#test-profile-001)、[TEST-REC-003](../40-verification/02-workspace-runtime-acceptance.md#test-rec-003) |
| 同步回放/标注 | [Replay & Annotation｜同步回放与标注](../10-frontend/04-replay-annotation/01-synchronized-playback.md) | [后端功能节点](../20-backend/04-recording-replay/02-replay-annotation-store.md) | [Episode、采集、事件与标注契约](../30-contracts/03-episode-events-annotations.md)、[时间、坐标系与命令生命周期](../30-contracts/04-time-frames-units.md) | [TEST-REPLAY-002](../40-verification/03-replay-data-acceptance.md#test-replay-002)、[TEST-ANN-001](../40-verification/03-replay-data-acceptance.md#test-ann-001) |
| 数据质量与导出 | [Dataset Management｜数据管理](../10-frontend/05-datasets/01-browser-quality-export.md) | [后端功能节点](../20-backend/05-dataset-export/01-quality-versions-export.md) | [Episode、采集、事件与标注契约](../30-contracts/03-episode-events-annotations.md)、[Dataset、Training、Checkpoint 与 Evaluation 关系](../30-contracts/05-dataset-model-lineage.md) | [TEST-DATA-001](../40-verification/03-replay-data-acceptance.md#test-data-001)、[TEST-EXPORT-001](../40-verification/03-replay-data-acceptance.md#test-export-001) |
| 训练与评估 | [Model Training｜训练管理概念](../10-frontend/06-training-evaluation/01-training-workspace.md) | [后端功能节点](../20-backend/06-training-evaluation/01-jobs-models-results.md) | [Dataset、Training、Checkpoint 与 Evaluation 关系](../30-contracts/05-dataset-model-lineage.md) | [TEST-TRACE-001](../40-verification/03-replay-data-acceptance.md#test-trace-001) |

## 如何讨论一个功能包

例如 TCP：先讨论前端目标/轨迹反馈，再核对后端到底提供终点 IK 还是 q(t)，共同补齐契约，最后冻结测试预期。不要在 Simulation、Viewport、后端与接口文档各写一套 TCP 规则。

## V0.2 新增功能链

| 功能 | 前端 | 后端 | 契约/全局 | 验收 |
|---|---|---|---|---|
| 任务模板与配置 | [配置流程](../10-frontend/02-scene-setup/02-task-template-configuration.md) | [场景构建](../20-backend/01-session-scene/03-scene-builder-assets.md) | [配置契约](../30-contracts/07-task-scene-experiment-config.md) | TEST-SCENE-004/006 |
| SO101 2D/3D | [摆放节点](../10-frontend/02-scene-setup/03-so101-tabletop-layout.md) | [场景构建](../20-backend/01-session-scene/03-scene-builder-assets.md) | 同一 ExperimentDraft 实例覆盖，固定 SceneVersion | TEST-SCENE-005 |
| Waypoint | [编辑器](../10-frontend/02-scene-setup/04-map-waypoint-editor.md) | [路线执行](../20-backend/03-observation-algorithms/03-map-waypoint-execution.md) | [路线契约](../30-contracts/08-navigation-map-route.md) | TEST-NAV-003～006 |
| 三执行配置/推理 | [Policy Rollout](../10-frontend/03-simulation/05-execution-profiles-policy-rollout.md) | [控制接管](../20-backend/02-robot-control/01-ownership-takeover.md) | [配置契约](../30-contracts/07-task-scene-experiment-config.md) | TEST-EXEC-001/IA-002 |
| 任务评定/辅助统计 | [评估视图](../10-frontend/06-training-evaluation/02-evaluation-workspace.md) | [任务评定](../20-backend/03-observation-algorithms/04-task-assessment.md) | Outcome/终止/有效性分开 | TEST-TASK-001 |
| 统一骨架与复用 | [开发路线](../00-overview/08-unified-development-roadmap.md) | [现有项目适配](../20-backend/07-existing-project-adapters/01-integration-boundaries.md) | [资源登记](../references/open-source-resource-registry.md) | TEST-ARCH-001；PoC 未执行 |

所有新 TEST 的预期见 [任务配置验收](../40-verification/04-task-config-workflow-acceptance.md)。

## 图片与新证据链（V0.3）

| 功能链 | 页面入口 | 后端/契约 |
|---|---|---|
| 页面图 → 功能规则 | [21 页面图](../10-frontend/page-designs/README.md) | 每页链接原功能包，不复制能力实现 |
| 资源 → 实验 → 运行 | [Task/Robot/Scenes](../10-frontend/page-designs/18-task-presets.md)、[Scene Setup](../10-frontend/page-designs/02-scene-setup.md) | [配置契约](../30-contracts/07-task-scene-experiment-config.md)与 Scene Builder |
| 模型 → 在线验证 | [My Models](../10-frontend/page-designs/12-my-models.md) → [Simulation](../10-frontend/page-designs/03-simulation.md) | [来源关系](../30-contracts/05-dataset-model-lineage.md)、Policy Adapter、统一 Ownership |
| 评估 → 报告 → 比较 | [四评估视图](../10-frontend/page-designs/14-evaluation-setup.md) | [评估比较契约](../30-contracts/09-evaluation-comparison.md)、[服务边界](../20-backend/06-training-evaluation/02-evaluation-comparison.md) |

## V0.5 当前开发入口

| 功能链 | 前端/页面 | 后端/契约 | 验收 |
|---|---|---|---|
| 三图共用 Setup | [PAGE-02](../10-frontend/page-designs/02-scene-setup.md)、[字段](../10-frontend/02-scene-setup/02-task-template-configuration.md)、[组件](../10-frontend/02-scene-setup/05-shared-scene-components.md) | [权限/版本/验证/快照](../30-contracts/07-task-scene-experiment-config.md)、[路线资源](../30-contracts/08-navigation-map-route.md) | TEST-CONFIG-001～007 |
| 数据到训练预测 | [M1/M2 与后续全流程](../00-overview/10-first-task-closed-loop.md) | [来源链](../30-contracts/05-dataset-model-lineage.md)、[数据出口](../20-backend/05-dataset-export/01-quality-versions-export.md)、[模型作业](../20-backend/06-training-evaluation/01-jobs-models-results.md) | TEST-LOOP-001～005 |

[本轮验收定义](../40-verification/06-scene-setup-first-loop.md) 均待执行；索引连通不代表真实任务跑通。

## V0.6 当前切片与作用域

| 功能 | 当前主责与映射 | 待执行验收 |
|---|---|---|
| mobileCar 四步闭环 | [阶段](../00-overview/10-first-task-closed-loop.md)、[Episode/native 接入](../30-contracts/03-episode-events-annotations.md)、[后端采集](../20-backend/04-recording-replay/01-recorder-events.md) | TEST-MOBILE-001/002 |
| 草案/资源/宿主隔离与复用 | [配置作用域](../30-contracts/07-task-scene-experiment-config.md)、[组件注入](../10-frontend/02-scene-setup/05-shared-scene-components.md)、[状态域](../00-overview/04-runtime-state-domains.md) | TEST-HOST-001 / TEST-CONFIG-008 |

完整数据/训练/预测行保留为后续能力，不作为当前 M1 回放前置；新增条目与原条目均未执行。
