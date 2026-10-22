# TCP 操控与虚线运动轨迹

规范 ID：`FE-3D-TCP` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-023](../../../设计过程与Specification总册_20261021.md#doc-023) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.4｜更新日期：2026-10-22（America/Los_Angeles）

状态：虚线可视化已要求；显示语义与规划能力待定义

来源：S03、S04、S05（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：[REQ-TCP-001](../../indexes/05-requirements.md#req-tcp-001), [REQ-TCP-002](../../indexes/05-requirements.md#req-tcp-002), [REQ-TCP-003](../../indexes/05-requirements.md#req-tcp-003), [REQ-TCP-004](../../indexes/05-requirements.md#req-tcp-004)

## 用户要求

设置末端操控状态后，TCP 朝目标移动时，需要用虚线展现关节的运动轨迹。该需求不能在整理时悄悄缩减成“只有 TCP 一条线”。默认具体显示哪些轨迹仍需原型确定。

## 需要区分的四种对象

| 对象 | 真实含义 | 助手建议显示 |
|---|---|---|
| Candidate TCP Path | 某一候选 q(t) 经 FK 得到的末端空间轨迹 | 虚线，标记候选 / 检查状态 |
| Joint Trajectory q(t) | 各关节角/位置随时间的序列 | 时间曲线、Ghost Robot |
| Joint Position Trails | 移动关节中心在世界或指定 Frame 中的轨迹 | 可选虚线，便于满足“关节运动轨迹”原意 |
| Actual TCP Trail | 根据实际历史状态计算的末端轨迹 | 实线 |

“默认 TCP，关节中心按需显示”是助手建议，尚未得到用户对显示语义的最终确认。Ghost Robot 是姿态预览，不等于运动轨迹本身。

## 操作流程草案

选择 Arm → 开启 TCP Tool → 选择目标参考系 / 自由度约束 → 拖动 Gizmo 形成目标 → 后端 IK / 必要轨迹生成与检查 → 显示候选 → 按 Live 或 Preview-Confirm 提交 → 对比实际运动。

只有 IK 终点 q_target 时只能证明得到一个候选配置，无法直接给出整条 q(t)。可以显示目标 Ghost 和起终点；如绘制仅作目标连接的辅助线，必须标记为未规划提示，不能称其为已验证可执行路径。

获得 q(t) 后，可通过 FK 得到 TCP 或某个关节中心位置。插值/规划方法、碰撞检查级别、轨迹时长和执行器跟踪约束尚未冻结；不能保证拖动即完成无碰规划。

## 显示契约草案

轨迹绑定 robot/arm、trajectory_id、目标版本、Frame、时间区间、候选来源、检查状态。新目标导致旧候选失效时需明确标记；不能把过期路径继续显示成当前已接受命令。预览不会写 Actual State。

待定：姿态轴拖动、局部/世界轴、受限自由度、Joint Trails 默认开关、轨迹颜色与虚线、Ghost 密度、Live 下是否显示全程候选。沿用 INT-TCP-TRAJECTORY-001、TEST-TCP-001。

## 关联文档

- [控制权与受控人工接管](../../30-contracts/06-control-authority.md)
- [控制与干预命令契约草案](../../30-contracts/02-control-intervention-commands.md)
- [共用 3D Viewport](01-viewport-contexts.md)
- [时间、坐标系与命令生命周期](../../30-contracts/04-time-frames-units.md)
- [交互验收清单](../../40-verification/01-interaction-acceptance.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
