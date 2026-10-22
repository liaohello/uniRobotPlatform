# Episode Detail｜回放、标注与审核

规范 ID：`PAGE-05` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

同步分析单条轨迹并保存独立标注修订，检查其训练用途资格。

- 页面 ID：`PAGE-05`；导航归属：Data。
- 主要对象：历史 Episode、Annotation Revision、Review Revision。
- 增量路线：B 同步只读回放，E 标注审核。这是设计顺序，不是排期或启动实施。

## 图片参考

![Episode Detail｜回放、标注与审核 原始概念图](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E5%9B%9E%E6%94%BE%E4%B8%8E%E6%A0%87%E6%B3%A8%E7%95%8C%E9%9D%A2.png)

主参考：`IMG-004`，PPT 第 4 页。覆盖程度：完整页面构图参考；图底 A/B 方案是备选说明。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 顶部 | Episode 身份、历史时间、机器人/观测配置与返回列表。 |
| 中央 | 3D 历史状态、存在的相机流、可折叠 View Controls。 |
| 底部 | 唯一回放时钟、关节/夹爪曲线、阶段、控制源和事件轨。 |
| 右侧 | 选中标注属性、作者/来源、审核及保存状态。 |

## 关键操作与跳转

- 播放、倍速、定位时间，缺帧显示明确；只查看被记录的观测。
- 阶段/结果/事件等标签分别编辑，保存为新修订；原始数据不改写。
- Split/Trim/Export Clip 产生片段引用或派生导出，不裁掉原始 Episode。
- 将“Open in Simulation”改为“以此配置新建运行”；只引用可恢复的场景/初态信息，不承诺任意帧物理续跑。

## 状态、失败与恢复

- Replay 时钟与后台 Session 明确隔离。
- 标注未保存、并发修订冲突、流缺失与模型版本缺失分别处理。
- 没有记录候选轨迹/接触数据时不推造历史证据。

## 相对原图的取舍

- 默认采用图 A 的简化观测工具；图 B 的集中 View Controls 作为可折叠高级面板。
- 移除图片下方的方案说明和红色标注框，它们属于设计说明。
- 把 Grasp 阶段、grasp_success 结果和接管事件分别存储及呈现。

关联冲突：[VIS-C09](../../90-governance/08-visual-design-conflicts.md#vis-c09)、[VIS-C11](../../90-governance/08-visual-design-conflicts.md#vis-c11)、[VIS-C12](../../90-governance/08-visual-design-conflicts.md#vis-c12)、[VIS-C21](../../90-governance/08-visual-design-conflicts.md#vis-c21)。

## 主责功能与后端支撑

- [Replay & Annotation｜同步回放与标注](../04-replay-annotation/01-synchronized-playback.md)
- [阶段、事件与标注编辑](../04-replay-annotation/02-annotation-editor.md)

后端/契约：[03-episode-events-annotations](../../30-contracts/03-episode-events-annotations.md)、[02-replay-annotation-store](../../20-backend/04-recording-replay/02-replay-annotation-store.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 返回轨迹列表 | [PAGE-04](04-episode-library.md) | 原筛选、排序和位置 |
| 加入集合 | [PAGE-06](06-dataset-collections.md) | Episode 与审核/标注修订引用 |
| 以配置新建运行 | [PAGE-03](03-simulation.md) | 可恢复配置引用，不承诺任意历史帧续跑 |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
