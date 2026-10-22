# 共享三维视口与交互工具

功能包 ID：`PKG-FE-3D` · 状态：基础组织稿；不表示包内全部需求已确认。

统一定义 Viewport、Selection、Joint、TCP 和外力工具；工作区只引用，不复制规则。

[上级大类](../README.md) · [总索引](../../README.md)

## 规范节点

| 节点 | 规范 ID | 内容 |
|---|---|---|
| [01-viewport-contexts.md](01-viewport-contexts.md) | `FE-3D-VIEWPORT` | 共用 3D Viewport |
| [02-selection-camera.md](02-selection-camera.md) | `FE-3D-SELECTION` | 选择、相机与整臂框选 |
| [03-joint-manipulation.md](03-joint-manipulation.md) | `FE-3D-JOINT` | 关节操控与监控 |
| [04-tcp-trajectories.md](04-tcp-trajectories.md) | `FE-3D-TCP` | TCP 操控与虚线运动轨迹 |
| [05-physical-force-tool.md](05-physical-force-tool.md) | `FE-3D-FORCE` | 物理受力与临时工具 |

## 细化方式

每个编号文件是一个设计节点；文件内继续列正常流程、异常/取消、数据接口、未决项和验收。仅当节点能独立讨论和验收时再拆文件，不按每个按钮或前端代码组件建一份文档。

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
