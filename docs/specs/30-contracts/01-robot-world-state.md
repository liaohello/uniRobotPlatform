# Robot / World State 契约草案

规范 ID：`CT-STATE` · 责任层：共享契约 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-031](../../设计过程与Specification总册_20261021.md#doc-031) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.1｜整理日期：2026-10-21（America/Los_Angeles）

状态：接口概念草案，不是已实现 API

来源：S02、S03、S05（详见[来源档案](../90-governance/06-sources.md)）

关联需求：[REQ-CONTRACT-001](../indexes/05-requirements.md#req-contract-001)

## 目的

使在线 3D、Inspector、传感器、录制和回放能引用同一机器人身份与时间，而不是各面板自行解释数组。

| 字段组 | 建议内容 |
|---|---|
| 身份 | schema_version、session_id、robot_id、arm_id、稳定 joint/link/body ID |
| 时间 | sim_time、source_time、sequence、状态有效性 |
| 本体 | joint actual position/velocity；其他状态按实际能力 |
| 目标 | 单独的 joint target / TCP target 与关联 command_id |
| 变换 | Frame ID、世界/机器人/相机变换、单位与约定 |
| 控制 | 每个控制范围的 owner、模式、接管状态 |
| 物体 | 可供 3D 与回放使用的世界实体位姿 |

Actual、Target、Preview 分开；是否记录接触、力矩和加速度由任务/记录配置决定。缺失或过期字段应有明确状态，而不是以零填补。

当前未选择 WebSocket/HTTP、序列化形式、字段拼写、压缩、广播频率，也未声明上表是可直接调用的 API。字段草案只有在与既有后端核对后才能冻结。

## 关联文档

- [机器人能力与适配边界](../00-overview/06-robot-capabilities.md)
- [时间、坐标系与命令生命周期](04-time-frames-units.md)
- [控制与干预命令契约草案](02-control-intervention-commands.md)
- [Episode、采集、事件与标注契约](03-episode-events-annotations.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)
