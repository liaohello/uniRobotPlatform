# 共用 3D Viewport

规范 ID：`FE-3D-VIEWPORT` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-026](../../../设计过程与Specification总册_20261021.md#doc-026) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.6｜更新日期：2026-10-22（America/Los_Angeles）

状态：组件草案

来源：S01、S03、S05（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：[REQ-VIEW-001](../../indexes/05-requirements.md#req-view-001)

## 组件职责草案

渲染机器人/场景、对象拾取、Hover/Selection、坐标系、Gizmo、Ghost、轨迹和外力反馈。Scene Setup、Simulation、Replay 共用呈现能力，使用不同数据上下文和可用操作。

| 使用方 | 数据来源 | 可写入对象 |
|---|---|---|
| Scene Setup | ExperimentDraft / 实例初态；显式资源编辑用 SceneDraft | 白名单内实例覆盖或指定资源草案，不反写运行态 |
| Simulation | 在线 Robot / World State | 通过网关提交控制或干预意图 |
| Replay | Episode Historical State | 标注层；不写在线状态 |

坐标系需支持显示、隐藏与大小调节，这是 S01 的直接需求。相机 Orbit / Zoom / Focus 与控制 Gizmo 的拾取区域、优先级需统一。渲染选择高亮不能修改物理材质或碰撞属性。

前端机器人姿态来自后端 Actual State；预览机器人作为独立 Ghost。对象稳定 ID 要能定位到 Arm / Joint / Link / Body，不以屏幕像素或显示名称作为唯一后端标识。

渲染帧率、状态订阅频率、传感器帧率、控制频率和录制频率分别定义；当前不填入未经测量的性能承诺。

## 关联文档

- [选择、相机与整臂框选](02-selection-camera.md)
- [TCP 操控与虚线运动轨迹](04-tcp-trajectories.md)
- [物理受力与临时工具](05-physical-force-tool.md)
- [Scene Setup｜场景布置](../02-scene-setup/01-workflow-initial-state.md)
- [Replay & Annotation｜同步回放与标注](../04-replay-annotation/01-synchronized-playback.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
