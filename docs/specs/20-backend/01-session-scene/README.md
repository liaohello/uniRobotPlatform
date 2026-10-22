# 会话、场景与配置

功能包 ID：`PKG-BE-SESSION` · 状态：基础组织稿；不表示包内全部需求已确认。

管理仿真会话和场景配置的执行边界，与页面导航分离。

[上级大类](../README.md) · [总索引](../../README.md)

## 规范节点

| 节点 | 规范 ID | 内容 |
|---|---|---|
| [01-session-lifecycle.md](01-session-lifecycle.md) | `BE-SESSION-LIFECYCLE` | 仿真 Session 与运行生命周期 |
| [02-scene-config-versions.md](02-scene-config-versions.md) | `BE-SCENE-CONFIG` | 场景配置、初态检查与版本 |
| [03-scene-builder-assets.md](03-scene-builder-assets.md) | `BE-SCENE-BUILDER` | 受限对象配置与 MuJoCo 场景构建 |

## 细化方式

每个编号文件是一个设计节点；文件内继续列正常流程、异常/取消、数据接口、未决项和验收。仅当节点能独立讨论和验收时再拆文件，不按每个按钮或前端代码组件建一份文档。
