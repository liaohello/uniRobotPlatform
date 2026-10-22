# 前端 Specification

主目录按业务工作区组织；跨工作区复用的三维交互和观察面板独立成包。按顶部/左栏/中央/右栏/底部查找请使用界面区域索引，它是阅读入口，不是永久的实现分层。

当前 V0.6 从 [M1 mobileCar / M2 bimanual](../00-overview/10-first-task-closed-loop.md) 开始；复用 [三图参考](page-designs/02-scene-setup.md)、[任务字段](02-scene-setup/02-task-template-configuration.md) 和 [共享组件](02-scene-setup/05-shared-scene-components.md)。轻宿主可按需使用组件/契约，不共享全局可写 store，不要求先实现三图或全产品菜单。

[总索引](../README.md) · [前后端功能映射](../indexes/06-feature-map.md)

## 功能包

- [全局外壳与操作上下文](01-shell/README.md) — `PKG-FE-SHELL`
- [场景布置工作区](02-scene-setup/README.md) — `PKG-FE-SCENE`
- [在线仿真工作台](03-simulation/README.md) — `PKG-FE-SIM`
- [回放与标注工作区](04-replay-annotation/README.md) — `PKG-FE-REPLAY`
- [数据管理工作区](05-datasets/README.md) — `PKG-FE-DATA`
- [训练与评估工作区](06-training-evaluation/README.md) — `PKG-FE-MODELS`
- [共享三维视口与交互工具](07-viewport-tools/README.md) — `PKG-FE-3D`
- [共享观察、属性与时间面板](08-observation-inspector/README.md) — `PKG-FE-PANELS`

## 当前交互修订

- 滑条以监控为主；默认只读仍是详细实现建议。
- V1 在 Scene Setup 创建、编辑与保存 Waypoint；Simulation 展示执行进度。运行中修改路线暂留后续。
- VLA 控制中使用显式受控接管；选择或拖动本身不抢占控制。
- TCP 虚线需要表达运动轨迹；具体 TCP/关节中心/Ghost 组合尚未冻结。
- 主臂无独立相机；任务中央/腕部相机仍按 Profile 提供。

## 页面设计层（V0.3）

[21 个页面/视图及参考图](page-designs/README.md) · [统一视觉与页面规则](01-shell/04-visual-design-rules.md) · [图片冲突分析](../90-governance/08-visual-design-conflicts.md)

功能规范按原八个功能包维护；页面设计节点将其组成可见视图。每个页面有图、覆盖程度、对象、操作、跳转、异常和修正。Resources 是辅助资源入口建议，模型标签与评估状态页不再各自成为独立在线控制台。

## V0.4 Simulation 参考图

[PAGE-03](page-designs/03-simulation.md) 使用用户更新的 IMG-022；[逐项对照与建议](03-simulation/06-simulation-v2-review.md) 说明实际删除/替换及功能缺口，旧主图保留为历史。
