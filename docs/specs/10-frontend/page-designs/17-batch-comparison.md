# Batch Comparison｜评估批次比较

规范 ID：`PAGE-17` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

对照已有评估批次的模型、条件和结果，并保留可比较性说明。

- 页面 ID：`PAGE-17`；导航归属：Models & Experiments / Evaluation。
- 主要对象：Evaluation Run 集合、Comparison Manifest、聚合统计定义。
- 增量路线：后续比较方案；不要求先建设并行集群。这是设计顺序，不是排期或启动实施。

## 图片参考

![Batch Comparison｜评估批次比较 原始概念图](../../../foreendAssets/%E6%9C%BA%E5%99%A8%E4%BA%BA%E8%AF%84%E6%B5%8B%E6%89%B9%E6%AC%A1%E5%AF%B9%E6%AF%94%E4%BB%AA%E8%A1%A8%E6%9D%BF.png)

主参考：`IMG-017`，PPT 第 17 页。覆盖程度：完整页面构图参考。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 顶部 | 选择 Run，明确比较协议和分组。 |
| 主区 | 指标表、配置差异、来源与可比较性。 |
| 下方 | 有证据的失败分布和代表 Episode。 |

## 关键操作与跳转

- 选择已有报告后建立比较清单，先检查条件再计算排名。
- 条件不同保留对照和分层统计，默认不作公平总排名。
- 保存比较预设/导出报告；回到对应结果或 Episode。

## 状态、失败与恢复

- CI 方法、统计单位和重复数未知时显示不可用。
- 单 seed 单 Run 不自动产生跨 seed 标准差；百分比明示分母。
- 并排比较不等于同时运行；初期可比较串行得到的结果。

## 相对原图的取舍

- 图片四组协议、随机化与 seed 均不同，不宜直接给出“最好模型”结论。
- 鲁棒性雷达只对真实相应扰动实验显示；无数据不补曲线。
- 均值±标准差与 95% CI 不能只切换显示文案，必须有对应统计定义和证据。

关联冲突：[VIS-C16](../../90-governance/08-visual-design-conflicts.md#vis-c16)、[VIS-C17](../../90-governance/08-visual-design-conflicts.md#vis-c17)、[VIS-C20](../../90-governance/08-visual-design-conflicts.md#vis-c20)。

## 主责功能与后端支撑

- [Evaluation｜评估概念](../06-training-evaluation/02-evaluation-workspace.md)

后端/契约：[09-evaluation-comparison](../../30-contracts/09-evaluation-comparison.md)、[02-evaluation-comparison](../../20-backend/06-training-evaluation/02-evaluation-comparison.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 查看单批报告 | [PAGE-16](16-evaluation-results.md) | 选中 Report Revision ID |
| 分析代表轨迹 | [PAGE-05](05-episode-detail.md) | Episode ID 与证据区间 |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
