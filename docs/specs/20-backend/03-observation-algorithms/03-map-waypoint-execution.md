# 地图与 Waypoint 校验、授权和执行

规范 ID：`BE-NAV-ROUTES` · 责任层：后端 · 版本：V0.2（2026-10-21）

状态：设计草案；S08/S09 是用户提供的分析文本，不自动视为所有细节已确认。Waypoint 范围以 S10 的用户明确选择为准。实现及产品验收均未执行。

来源：[S09](../../90-governance/sources/S09-unified-development-reuse-analysis.md)、[S10](../../90-governance/sources/S10-waypoint-scope-confirmation.md)。

[上级目录](README.md) · [总索引](../../README.md)

关联需求：[REQ-NAV-004](../../indexes/05-requirements.md#req-nav-004)

## 职责

接受 Scene Setup 保存的路线版本，提供地图兼容、点位预检、导航授权、执行状态与结果；复用既有导航服务，不让网页编辑器直连速度话题。

1. 保存/导入时核对地图、Frame、单位、顺序和点位条件。
2. 启动时核对当前定位、地图/场景身份、控制权、记录门与已有导航任务状态。
3. 把冻结 Route Snapshot 适配到选定导航接口，建立外部路线/Waypoint ID 到内部目标的追踪。
4. 发布当前点、完成/失败点和原因；取消、接管、健康失效或 Reset 使旧输出失效。
5. 草案新修订不改变已授权任务；在线换路线若以后开放，须定义终止屏障、重规划和新授权。

Nav2 Humble Waypoint Follower 官方说明提供有序点数组、当前索引反馈和未完成点列表，可作为适配参考；不代表现有小车接口已经提供所有功能。[官方源码说明](https://github.com/ros-navigation/navigation2/blob/humble/nav2_waypoint_follower/README.md)

Route Following 与离散 Waypoint 到点不是完全相同的评估任务。连续路线偏差、每点朝向、失败继续/终止策略需模板声明，不能从后端默认参数猜测。

契约：[地图与路线](../../30-contracts/08-navigation-map-route.md)。验收：[TEST-NAV-005](../../40-verification/04-task-config-workflow-acceptance.md#test-nav-005)、[TEST-NAV-006](../../40-verification/04-task-config-workflow-acceptance.md#test-nav-006)。
