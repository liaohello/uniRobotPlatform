# 统一时间轴与事件轨

规范 ID：`FE-PANEL-TIMELINE` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-030](../../../设计过程与Specification总册_20261021.md#doc-030) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.4｜更新日期：2026-10-22（America/Los_Angeles）

状态：回放时间轴需求明确；多轨实现为草案

来源：S01、S02、S03、S05（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：见需求追踪矩阵中的引用与相关主责规范

## 建议轨道

Simulation / Episode 主时间、相机帧、关节曲线、TCP 轨迹、任务阶段、控制源区间、接管事件、物理扰动与离线标注。轨道来源与版本需可辨识。

## 在线与回放

在线时间轴关注最新状态和事件，可查看历史缓存但不因此回退物理世界。Replay 游标驱动历史显示，支持用户需要的播放、倍速；暂停、逐帧、定位、区间循环为建议。

不同流采样率不必相同；对齐与插值应遵守数据契约。缺帧区域、未知标签、时钟异常不能被一条连续曲线掩盖。区间端点语义和帧索引映射待定义。

离线标注与在线检测事件独立；修改标注不覆盖原始事件，也不修改动作。控制来源时间段可辅助区分纯 Policy、人工接管、纯人工示教和专家算法轨迹。

## 关联文档

- [时间、坐标系与命令生命周期](../../30-contracts/04-time-frames-units.md)
- [Replay & Annotation｜同步回放与标注](../04-replay-annotation/01-synchronized-playback.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。

## V0.4 实时轨的一致性

新图增加系统事件轨。实际 Live 轨只显示已发生事件；未来计划以独立计划轨/线型呈现。当前阶段摘要与阶段轨引用同一时刻；录制时长与 Session/任务时钟说明起点。

混合 Base Expert/Arm Human 应展开按部件的来源轨，或明确当前行的范围；用户“添加事件”产生带作者/来源的标记，不覆盖后端系统事件。详见 [V2 图稿问题与建议](../03-simulation/06-simulation-v2-review.md)。
