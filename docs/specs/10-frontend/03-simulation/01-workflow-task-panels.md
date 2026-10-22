# Simulation｜在线仿真工作台

规范 ID：`FE-SIM-WORKFLOW` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-016](../../../设计过程与Specification总册_20261021.md#doc-016) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.6｜更新日期：2026-10-22（America/Los_Angeles）；原始内容来源保留。

状态：功能边界明确；布局与录制流程为草案

来源：S01–S05（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：见需求追踪矩阵中的引用与相关主责规范

## 核心任务

运行 / 暂停 / 重置 MuJoCo，观察算法、人工控制、受控接管、物理干预、录制 Episode。按当前 HostApp 的 Task Template/能力和 Layout Preset 选择默认面板；3D 组件可复用，运行状态和控制权限仍由后端裁决。

## 面板职责建议

| 区域 | 内容 |
|---|---|
| 全局状态 | Project、Robot、Scene、Session、仿真/录制/连接状态 |
| 中央 Viewport | 模型、选择、高亮、坐标系、Joint / TCP 工具、轨迹 |
| Hierarchy / Inspector | 对象树、Arm、关节实测/目标/限位、TCP、控制来源 |
| 任务传感器区 | 小车地图/RGB-D，或双臂中央/左右腕相机 |
| 控制与事件区 | 当前控制源、人工接管、运行反馈、事件、录制入口 |
| 可折叠分析区 | 关节曲线、实时数据、可选历史轨迹 |

面板位置仅为职责分类，不能据此认定左中右布局已由用户确认。用户在操作中，任务阶段变化只建议切换布局，不强制重新排列。

## 操作流程

选定 Session → 检查状态和控制源 → 观察或选择对象 → 按工具生成目标 → Live / Preview-Confirm → 后端反馈 → 观察实际执行 → 录制与事件关联。

VLA Active 下鼠标仍可选中观察，但运动操作需先走受控接管；是否允许未授权时编辑纯预览目标待确定。外力以独立干预权限判定，不视作 TCP 控制。

## 与其他规范的关系

本页负责工作流，不重新定义快捷键、TCP 路径含义或接管协议。具体引用 Selection、Joint、TCP、Physics、Leader-Follower、Control Authority。

## 待细化

录制开始/结束与任务状态关系、暂停录制、重置后 Episode 边界、连接恢复、快捷控制区位置、手动夹爪输入、接管目标范围。

## 关联文档

- [控制权与受控人工接管](../../30-contracts/06-control-authority.md)
- [任务、观测与数据配置](../../00-overview/03-task-and-observation-profiles.md)
- [选择、相机与整臂框选](../07-viewport-tools/02-selection-camera.md)
- [关节操控与监控](../07-viewport-tools/03-joint-manipulation.md)
- [TCP 操控与虚线运动轨迹](../07-viewport-tools/04-tcp-trajectories.md)
- [物理受力与临时工具](../07-viewport-tools/05-physical-force-tool.md)
- [实体主臂与仿真从臂](03-leader-follower-panel.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## V0.2 布局与执行配置

详细区域见 [A–H 布局与预设](04-ah-layout-presets.md)；运行来源见 [执行配置与模型推理](05-execution-profiles-policy-rollout.md)。Simulation 展示 Scene Setup 保存的路线及当前点，不把地图点击直接转换成在线换目标。

运行中物体扰动需要受控外力或独立、可追踪的测试输入通道；不能把 Scene Setup 的位置修改方法直接用于正在录制的物理世界。扰动方法尚待 OQ-037 收敛。

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
