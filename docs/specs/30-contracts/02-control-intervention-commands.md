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

客户端不能通过写一个 owner 字段自授控制权。旧动作过期与拒绝、重复请求、断连清理需要后端协议，具体机制尚未选择。

响应建议含 command_id、Accepted/Rejected、原因、执行阶段与完成/失败信息。TCP 规划结果和最终执行结果分开；Replay 不调用在线命令入口。

## 关联文档

- [控制权与受控人工接管](06-control-authority.md)
- [关节操控与监控](../10-frontend/07-viewport-tools/03-joint-manipulation.md)
- [TCP 操控与虚线运动轨迹](../10-frontend/07-viewport-tools/04-tcp-trajectories.md)
- [物理受力与临时工具](../10-frontend/07-viewport-tools/05-physical-force-tool.md)
- [时间、坐标系与命令生命周期](04-time-frames-units.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)
