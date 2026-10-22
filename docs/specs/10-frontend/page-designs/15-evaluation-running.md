# Evaluation Running｜评估运行监控

规范 ID：`PAGE-15` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

监控评估状态并进入统一 Simulation 或历史 Episode 诊断。

- 页面 ID：`PAGE-15`；导航归属：Models & Experiments / Evaluation。
- 主要对象：Evaluation Run、Episode Evidence、关联 Session。
- 增量路线：E：监控；并行调度后续另定。这是设计顺序，不是排期或启动实施。

## 图片参考

![Evaluation Running｜评估运行监控 原始概念图](../../../foreendAssets/%E6%9C%BA%E5%99%A8%E4%BA%BA%E8%AF%84%E4%BC%B0%E8%BF%90%E8%A1%8C%E7%9B%91%E6%8E%A7%E4%BB%AA%E8%A1%A8%E7%9B%98.png)

主参考：`IMG-015`，PPT 第 15 页。覆盖程度：完整页面构图参考。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 左侧 | 作业列表及后端上报的排队/运行状态。 |
| 中央 | 只读配置摘要、进度、当前 Episode 和只读实时画面。 |
| 右侧 | 有分母说明的暂定指标、阶段结果与资源摘要。 |

## 关键操作与跳转

- 在线预览默认只读；需接管时“在 Simulation 中打开”并指向同一 Session。
- Pause/Stop 明确针对评估作业，不复用全局含义不明的播放按钮。
- 结束的 Episode 进入 P05；Run 完成后进入 P16。

## 状态、失败与恢复

- 已完成数/计划数与当前执行数分别显示；未完成 Episode 不提前纳入结果分母。
- 实时预览与历史片段播放有独立标签和时钟。
- 人工干预按协议记录为辅助或评估有效性变化，不能静默继续计为纯自主。

## 相对原图的取舍

- 图中四个 Running 不作为 V1 多任务并行承诺。
- 底部播放进度仅控制历史片段，不倒退正在运行的物理仿真。
- 批量作业取消是调度行为，不能被前端关闭页面替代。

关联冲突：[VIS-C02](../../90-governance/08-visual-design-conflicts.md#vis-c02)、[VIS-C06](../../90-governance/08-visual-design-conflicts.md#vis-c06)、[VIS-C15](../../90-governance/08-visual-design-conflicts.md#vis-c15)、[VIS-C16](../../90-governance/08-visual-design-conflicts.md#vis-c16)、[VIS-C20](../../90-governance/08-visual-design-conflicts.md#vis-c20)。

## 主责功能与后端支撑

- [Evaluation｜评估概念](../06-training-evaluation/02-evaluation-workspace.md)

后端/契约：[02-evaluation-comparison](../../20-backend/06-training-evaluation/02-evaluation-comparison.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 需要在线交互 | [PAGE-03](03-simulation.md) | 同一 Session ID 与 Evaluation Run ID |
| 查看已完成轨迹 | [PAGE-05](05-episode-detail.md) | 具体 Episode ID |
| 查看报告 | [PAGE-16](16-evaluation-results.md) | 确定的 Run/Report ID |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
