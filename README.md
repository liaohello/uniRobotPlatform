# uniRobotPlatform
A MuJoCo-based embodied AI simulation and 3D interaction data collection platform with LiDAR/SLAM navigation, RGB-D perception, robotic arm manipulation, teleoperation data recording, and policy evaluation for BC, ACT, Diffusion Policy, VLA, and hierarchical VLN.

换笔记本继续开发先看 [Git 追踪与恢复清单](docs/laptop-migration.md)：本仓库包含规范、参考素材、项目规则和网关源码；三个原生工程仍需分别恢复，虚拟环境/私人配置/运行数据不随 Git 搬迁。

另开会话继续工作先读 [交接说明](docs/handoff.md)，需要讨论原貌时查看 [本次会话公开消息存档](docs/conversations/2026-10-22-scene-setup-dialogue.md)。

设计与需求从 [Specification 总索引](docs/specs/README.md) 开始；按 [前端](docs/specs/10-frontend/README.md)、[后端](docs/specs/20-backend/README.md) 和 [共享契约](docs/specs/30-contracts/README.md) 分层，提供 [功能映射](docs/specs/indexes/06-feature-map.md) 与 [需求追踪](docs/specs/indexes/05-requirements.md)。历史材料见 [文档入口](docs/README.md)。

### V0.3 前端图片与页面 Specification

[页面与图片索引](docs/specs/10-frontend/page-designs/README.md) · [设计冲突分析](docs/specs/90-governance/08-visual-design-conflicts.md) · [图片/PPT 对照](docs/specs/references/04-visual-asset-catalog.md)。原素材保留，页面设计与功能/后端规范交叉索引。

### V0.5 历史范围（当前阶段见 V0.6）

[一个前端样板与一条完整任务](docs/specs/00-overview/10-first-task-closed-loop.md)：三张 Scene Setup 共用组件和任务配置；真实流程覆盖场景→人工/专家采集→清理→数据版本→模型训练→预测运行。[任务字段](docs/specs/10-frontend/02-scene-setup/02-task-template-configuration.md) · [公共契约](docs/specs/30-contracts/07-task-scene-experiment-config.md) · [共享组件](docs/specs/10-frontend/02-scene-setup/05-shared-scene-components.md)。本轮为规范整理，首任务 SO101 台面转运/ACT 是建议。

### V0.6 当前开发范围

[mobileCar 四步闭环与 bimanual 复用](docs/specs/00-overview/10-first-task-closed-loop.md)：先场景→运行→录制→回放，再验证共享组件的宿主隔离与适配。训练/预测后续；[配置/宿主契约](docs/specs/30-contracts/07-task-scene-experiment-config.md)、[采集/回放契约](docs/specs/30-contracts/03-episode-events-annotations.md) 为当前主责。本轮仅修复规范，未改变后端和原生项目。

### V0.7 统一 3D 工作台计划复评

[最新前端实施计划](docs/specs/00-overview/09-page-design-delivery-plan.md)：先统一 React/TS 外壳、Three.js SceneView 复用边界，再逐项接通 mobileCar；下一份前端产物为对象树/视口/Inspector、相机与 Joint/TCP Target 可操作样板，继而接控制、录制和只读回放。诊断/元数据草案只代表接入基础。M1/M2 范围不变，前端实现继续暂停，本轮仅修订设计和计划。

### M1.2c 后端候选（2026-10-24）

[M1.2c 交付记录](docs/backend-m1.2c.md)：修正依赖锁核验，固定原生配置/编译场景摘要与运行时版本核对；平台候选 18944 增加 `m1-binding-1` 客户端、Session 执行分域和 `m1-recording-1` begin。原生候选补丁已在服务器以 mock backend 验证，但未部署到 8792；真实 G1 prepared/Start、在线录制、回放和 M1 闭环仍未完成。

### M1.2d 后端候选（2026-10-24）

[M1.2d 交付记录](docs/backend-m1.2d.md)：修复 native RESET/开录生命周期竞态与 started 被准备 TTL 误过期；单 Session GET 增加只读 `current`，列表明确为存档视图；平台实际 `NativeBindingClient` 已与隔离 native mock 完成真实 HTTP prepare/readback/start/begin/release 集成。候选完成，原生补丁仍未部署到 8792，真实物理验证未执行。

### M1.3 后端候选（2026-10-24）

[M1.3 交付记录](docs/backend-m1.3.md)：接入真实 G3B 历史离线地图的固定版本读取，交付 PointGoal/Waypoint 必填 `x/y/yaw`、m/rad 与旋转坐标约定，以及 Route Draft baseRevision 保存和不可变 Route Version 发布。平台候选 18953 已验证地图、PGM、冲突和版本不可变；保存不触发 native、Nav2、cmd_vel、RESET、运动或录制，当前 G1 仍无导航执行资格。8792 未部署，M1 闭环未验收。
