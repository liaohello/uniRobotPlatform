# 时间、坐标系与命令生命周期

规范 ID：`CT-TIME-FRAMES` · 责任层：共享契约 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-014](../../设计过程与Specification总册_20261021.md#doc-014) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.1｜整理日期：2026-10-21（America/Los_Angeles）

状态：跨工作区接口设计草案

来源：S02、S03、S05（详见[来源档案](../90-governance/06-sources.md)）

关联需求：[REQ-CONTRACT-002](../indexes/05-requirements.md#req-contract-002)

## 建议区分的时间

| 时间 | 用途 |
|---|---|
| Simulation Time | 仿真状态、动作、接触、事件的物理时间 |
| Sensor / Source Time | 各观测产生时间 |
| Host Time | 进程、连接、训练作业诊断 |
| Receive / Render Time | 前端显示与链路延迟分析 |
| Replay Cursor | 历史 Episode 的查看位置 |

时间轴同步应依照记录的时间契约，不能以浏览器收包顺序替代采样时序。暂停、重置、时间回退后的 Session / Episode 标识和单调序列需定义。各源时钟是否同源、采样对齐、插值规则、允许时差均未冻结。

## 坐标系与单位

状态、目标、轨迹和外力必须带 Frame ID 与单位。界面可用 degree 显示，传输单位不得只靠控件猜测。RGB-D 相机随机械臂刚性运动时，需用对应时刻变换处理，不应把相机位姿固定为起始外参在世界中的姿态。

## 命令状态建议

Draft → Submitted → Accepted / Rejected → Executing → Completed / Failed / Cancelled / Expired。

“目标已设置”“后端已接受”“物理状态已到达”分别显示。Accepted 不等于执行成功，IK Success 不等于到达，碰撞检查通过也不等于动力学执行必定成功。

取消未提交草案、撤销尚未执行命令、停止正在执行运动应使用不同反馈。动作维度、绝对 / 增量、关节 / TCP、目标 / 实测的语义在导出时继续保留。

## 关联文档

- [Robot / World State 契约草案](01-robot-world-state.md)
- [控制与干预命令契约草案](02-control-intervention-commands.md)
- [Episode、采集、事件与标注契约](03-episode-events-annotations.md)
- [统一时间轴与事件轨](../10-frontend/08-observation-inspector/03-timeline-event-tracks.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)
