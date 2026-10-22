# Results & Reports｜评估结果

规范 ID：`PAGE-16` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

说明一个确定评估 Run 的结果、失败原因和证据。

- 页面 ID：`PAGE-16`；导航归属：Models & Experiments / Evaluation。
- 主要对象：Evaluation Report Revision、Episode 结果、任务判据版本。
- 增量路线：E：评估结果与回放证据。这是设计顺序，不是排期或启动实施。

## 图片参考

![Results & Reports｜评估结果 原始概念图](../../../foreendAssets/RoboLab%20%E6%9C%BA%E5%99%A8%E4%BA%BA%E8%AF%84%E4%BC%B0%E7%BB%93%E6%9E%9C%E4%BB%AA%E8%A1%A8%E6%9D%BF.png)

主参考：`IMG-016`，PPT 第 16 页。覆盖程度：完整页面构图参考。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 顶部 | 只读模型/场景/任务/协议/种子快照及运行完成状态。 |
| 摘要 | 成功率、样本量、有效性与自主/辅助分组。 |
| 主体 | Episode 表、阶段结果、失败分类和回放入口。 |

## 关键操作与跳转

- 点击结果进入 P05 的历史 Episode，保留当前筛选与时间点。
- Edit Configuration 改为“复制配置新建评估”，不改历史 Run。
- 报告导出固定版本；Compare Runs 进入 P17。

## 状态、失败与恢复

- 结果、终止原因、人工干预、数据完整性各自筛选。
- 不可评定/缺记录保留未知或无效；单次 Run 无重复统计时不展示伪造 mean±std。

## 相对原图的取舍

- 顶部去掉 Simulation 播放控件，展示 Completed/Failed 等作业状态。
- Intervened 是控制辅助维度，不与 Success/Failure 互斥。
- 图片中 Timeout 总计 0 与失败分布 1 不一致；实际摘要和细节必须来自同一报告。

关联冲突：[VIS-C06](../../90-governance/08-visual-design-conflicts.md#vis-c06)、[VIS-C15](../../90-governance/08-visual-design-conflicts.md#vis-c15)、[VIS-C17](../../90-governance/08-visual-design-conflicts.md#vis-c17)、[VIS-C20](../../90-governance/08-visual-design-conflicts.md#vis-c20)。

## 主责功能与后端支撑

- [Evaluation｜评估概念](../06-training-evaluation/02-evaluation-workspace.md)

后端/契约：[04-task-assessment](../../20-backend/03-observation-algorithms/04-task-assessment.md)、[09-evaluation-comparison](../../30-contracts/09-evaluation-comparison.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 分析结果轨迹 | [PAGE-05](05-episode-detail.md) | Episode ID 与时间点 |
| 复制配置新建评估 | [PAGE-14](14-evaluation-setup.md) | 历史配置引用，新草案身份 |
| 比较批次 | [PAGE-17](17-batch-comparison.md) | Report Revision ID |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
