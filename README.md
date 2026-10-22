# uniRobotPlatform
A MuJoCo-based embodied AI simulation and 3D interaction data collection platform with LiDAR/SLAM navigation, RGB-D perception, robotic arm manipulation, teleoperation data recording, and policy evaluation for BC, ACT, Diffusion Policy, VLA, and hierarchical VLN.

换笔记本继续开发先看 [Git 追踪与恢复清单](docs/laptop-migration.md)：本仓库包含规范、参考素材、项目规则和网关源码；三个原生工程仍需分别恢复，虚拟环境/私人配置/运行数据不随 Git 搬迁。

设计与需求从 [Specification 总索引](docs/specs/README.md) 开始；按 [前端](docs/specs/10-frontend/README.md)、[后端](docs/specs/20-backend/README.md) 和 [共享契约](docs/specs/30-contracts/README.md) 分层，提供 [功能映射](docs/specs/indexes/06-feature-map.md) 与 [需求追踪](docs/specs/indexes/05-requirements.md)。历史材料见 [文档入口](docs/README.md)。

### V0.3 前端图片与页面 Specification

[页面与图片索引](docs/specs/10-frontend/page-designs/README.md) · [设计冲突分析](docs/specs/90-governance/08-visual-design-conflicts.md) · [图片/PPT 对照](docs/specs/references/04-visual-asset-catalog.md)。原素材保留，页面设计与功能/后端规范交叉索引。

### V0.5 历史范围（当前阶段见 V0.6）

[一个前端样板与一条完整任务](docs/specs/00-overview/10-first-task-closed-loop.md)：三张 Scene Setup 共用组件和任务配置；真实流程覆盖场景→人工/专家采集→清理→数据版本→模型训练→预测运行。[任务字段](docs/specs/10-frontend/02-scene-setup/02-task-template-configuration.md) · [公共契约](docs/specs/30-contracts/07-task-scene-experiment-config.md) · [共享组件](docs/specs/10-frontend/02-scene-setup/05-shared-scene-components.md)。本轮为规范整理，首任务 SO101 台面转运/ACT 是建议。

### V0.6 当前开发范围

[mobileCar 四步闭环与 bimanual 复用](docs/specs/00-overview/10-first-task-closed-loop.md)：先场景→运行→录制→回放，再验证共享组件的宿主隔离与适配。训练/预测后续；[配置/宿主契约](docs/specs/30-contracts/07-task-scene-experiment-config.md)、[采集/回放契约](docs/specs/30-contracts/03-episode-events-annotations.md) 为当前主责。本轮仅修复规范，未改变后端和原生项目。
