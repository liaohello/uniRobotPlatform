# 机器人控制与干预

功能包 ID：`PKG-BE-CONTROL` · 状态：基础组织稿；不表示包内全部需求已确认。

管理权限、关节/底盘/夹爪、TCP 求解规划、外力和主臂桥。

[上级大类](../README.md) · [总索引](../../README.md)

## 规范节点

| 节点 | 规范 ID | 内容 |
|---|---|---|
| [01-ownership-takeover.md](01-ownership-takeover.md) | `BE-CONTROL-AUTHORITY` | 控制源仲裁与受控接管执行 |
| [02-joint-base-gripper.md](02-joint-base-gripper.md) | `BE-CONTROL-ACTUATORS` | 关节、底盘与夹爪命令执行 |
| [03-ik-planning-execution.md](03-ik-planning-execution.md) | `BE-CONTROL-PLANNING` | TCP 求解、轨迹检查与执行 |
| [04-physical-intervention.md](04-physical-intervention.md) | `BE-CONTROL-FORCE` | 物理扰动与持续外力管理 |
| [05-leader-device-bridge.md](05-leader-device-bridge.md) | `BE-CONTROL-LEADER` | 实体主臂设备桥与关节映射 |

## 细化方式

每个编号文件是一个设计节点；文件内继续列正常流程、异常/取消、数据接口、未决项和验收。仅当节点能独立讨论和验收时再拆文件，不按每个按钮或前端代码组件建一份文档。
