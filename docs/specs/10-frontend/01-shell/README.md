# 全局外壳与操作上下文

功能包 ID：`PKG-FE-SHELL` · 状态：基础组织稿；不表示包内全部需求已确认。

负责导航、全局上下文、布局、输入焦点和接管状态呈现；不是后端生命周期的所有者。

[上级大类](../README.md) · [总索引](../../README.md)

## 规范节点

| 节点 | 规范 ID | 内容 |
|---|---|---|
| [01-navigation-context.md](01-navigation-context.md) | `FE-SHELL-NAV` | 全局信息架构与工作区 |
| [02-layout-input-focus.md](02-layout-input-focus.md) | `FE-SHELL-LAYOUT` | 面板布局与输入焦点 |
| [03-authority-status-feedback.md](03-authority-status-feedback.md) | `FE-SHELL-AUTHORITY` | 控制权、接管与全局状态反馈 |

## 细化方式

每个编号文件是一个设计节点；文件内继续列正常流程、异常/取消、数据接口、未决项和验收。仅当节点能独立讨论和验收时再拆文件，不按每个按钮或前端代码组件建一份文档。

## 页面图与设计归属（V0.3）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E5%B9%B3%E5%8F%B0%E4%BB%AA%E8%A1%A8%E7%9B%98.png)

[PAGE-01 页面设计与修正](../page-designs/01-home.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。

- [页面统一规则与视觉基线](04-visual-design-rules.md) — `FE-SHELL-VISUAL`
