# 控制与干预命令契约草案

规范 ID：`CT-COMMAND` · 责任层：共享契约 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-032](../../设计过程与Specification总册_20261021.md#doc-032) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.1｜整理日期：2026-10-21（America/Los_Angeles）

状态：接口概念草案，不是已实现 API

来源：S03、S04、S05（详见[来源档案](../90-governance/06-sources.md)）

关联需求：见需求追踪矩阵中的引用与相关主责规范

## 共用信封建议

command_id、session_id、robot/control_scope、source、authority 引用、issued_time/sequence、目标/坐标系/单位、有效期及请求类型。

| 意图 | 主要载荷草案 | 接收后语义 |
|---|---|---|
| Joint Target | 关节 ID 与目标、Live/Preview | 只控制对应目标变量 |
| TCP Target | Frame、目标位姿、约束、目标版本 | IK / 必要轨迹检查；反馈受理与实际执行 |
| Base Velocity | 底盘速度、有效期 | 持续输入需超时失效 |
| Gripper | 机器人定义的开度/目标 | 语义与单位需能力描述 |
| Takeover / Resume | 指定控制范围、请求 ID | 后端确认后移交 |
| External Force | Body、作用点/Frame、力向量、有效期 | 干预权限；不改变关节目标 |
| STOP（latch） | `request_id`（幂等键）、`reason`、可选 `parking_timeout_s`（0<v≤30）；身份由平台 Session 提供 | 只下发 latch 型停止：不 RESET、不清安全锁、不结束录制、不获取 owner、不恢复运动；不以 `motion_ready`/`recording_ready`/owner/lease 为前置条件 |

客户端不能通过写一个 owner 字段自授控制权。旧动作过期与拒绝、重复请求、断连清理需要后端协议，具体机制尚未选择。

响应建议含 command_id、Accepted/Rejected、原因、执行阶段与完成/失败信息。TCP 规划结果和最终执行结果分开；Replay 不调用在线命令入口。

## STOP 回执分层（M1.4 候选）

上表其余意图仍是概念草案；STOP 已有平台侧实现与 native 候选补丁（`m1-stop-1`，见 [Session 生命周期](../20-backend/01-session-scene/01-session-lifecycle.md#stop-与录制结束协议m1-stop-1--m1-end-1) 与 [M1.4 交付记录](../../backend-m1.4.md)）。其响应必须分层给出，供 UI 分别判断：

| 层 | 字段 | UI 允许的说法 |
|---|---|---|
| 受理 | `accepted`、`code`、`replayed` | "停止请求已受理"，不得说"已停止" |
| 下发 | `dispatch.dispatched`、`command_id`、`status` | "停止命令已下发/未下发" |
| 停稳 | `parking.confirmed`、`scope_coverage`、`coverage_complete`、`coverage_note` | 只有 `coverage_complete=true` 才能说"整机停稳"；否则按作用域列 `confirmed/unconfirmed/not_observed` |
| 安全态 | `safety_latched`、`owner_cleared_after_stop` | 说明 STOP 后是否仍处安全锁定、owner 是否被清；不推断恢复 |

`POST /api/v1/runs/{run_id}/stop` 是运行记录/进程管理，不是机器人 STOP，UI 不得用它作为停止按钮的后端。真实停车确认尚未执行（未部署、未做物理验证）。

## 关联文档

- [控制权与受控人工接管](06-control-authority.md)
- [关节操控与监控](../10-frontend/07-viewport-tools/03-joint-manipulation.md)
- [TCP 操控与虚线运动轨迹](../10-frontend/07-viewport-tools/04-tcp-trajectories.md)
- [物理受力与临时工具](../10-frontend/07-viewport-tools/05-physical-force-tool.md)
- [时间、坐标系与命令生命周期](04-time-frames-units.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)
