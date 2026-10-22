# 场景布置工作区

功能包 ID：`PKG-FE-SCENE` · 状态：基础组织稿；不表示包内全部需求已确认。

负责已有场景、机器人与初态的编辑流程；复用三维工具，修改的是配置草案。

[上级大类](../README.md) · [总索引](../../README.md)

## 规范节点

| 节点 | 规范 ID | 内容 |
|---|---|---|
| [01-workflow-initial-state.md](01-workflow-initial-state.md) | `FE-SCENE-WORKFLOW` | Scene Setup｜场景布置 |
| [02-task-template-configuration.md](02-task-template-configuration.md) | `FE-SCENE-TEMPLATES` | 任务模板选择与实验配置流程 |
| [03-so101-tabletop-layout.md](03-so101-tabletop-layout.md) | `FE-SCENE-BIMANUAL-LAYOUT` | SO101 桌面对象的 2D/3D 布置 |
| [04-map-waypoint-editor.md](04-map-waypoint-editor.md) | `FE-SCENE-WAYPOINTS` | 2D 地图与 Waypoint 路线编辑 |
| [05-shared-scene-components.md](05-shared-scene-components.md) | `FE-SCENE-COMPONENTS` | 三图共用组件、数据驱动变体与扩展边界 |

## 细化方式

每个编号文件是一个设计节点；文件内继续列正常流程、异常/取消、数据接口、未决项和验收。仅当节点能独立讨论和验收时再拆文件，不按每个按钮或前端代码组件建一份文档。

## 当前页面参考（V0.5）

[导航、近场抓取、双臂转运三图](../page-designs/02-scene-setup.md) 是同一页面的任务变体；新规则见任务字段与共享组件节点。以下为历史 V0.3 参考，旧图保留。

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E5%9C%BA%E6%99%AF%E9%85%8D%E7%BD%AE%E7%95%8C%E9%9D%A2.png)

[PAGE-02 页面设计与修正](../page-designs/02-scene-setup.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
