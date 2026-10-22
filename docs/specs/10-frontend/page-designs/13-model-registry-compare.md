# Registry & Compare｜模型版本比较

规范 ID：`PAGE-13` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

比较模型来源、配置及可比较的评估证据，记录有依据的版本选择。

- 页面 ID：`PAGE-13`；导航归属：Models & Experiments / Models。
- 主要对象：Model Version 集合、Comparison Manifest、Evaluation 证据。
- 增量路线：E 或后续比较能力。这是设计顺序，不是排期或启动实施。

## 图片参考

![Registry & Compare｜模型版本比较 原始概念图](../../../foreendAssets/RoboLab%E6%A8%A1%E5%9E%8B%E5%BA%93%E5%AF%B9%E6%AF%94%E4%B8%8E%E6%B3%A8%E5%86%8C%E4%BB%AA%E8%A1%A8%E6%9D%BF.png)

主参考：`IMG-013`，PPT 第 13 页。覆盖程度：完整页面构图参考。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 左侧 | 模型版本选择与评估协议筛选。 |
| 中央 | 模型/训练配置事实表与评估结果，缺失或不匹配分栏。 |
| 右侧 | 比较预设、指标选择与注册/推荐动作。 |

## 关键操作与跳转

- 选择版本后由后端计算比较维度，展示协议/任务/环境/种子和辅助控制差异。
- 仅可比较的同条件指标可参与排名；不匹配时保留描述性对照。
- Open Eval Report 跳 P16；Run in Simulation 只传配置引用。

## 状态、失败与恢复

- Same Eval Only 是筛选条件，实际比较依据来自报告和版本身份。
- 无共同指标、评估缺失或协议不同显示原因及降级表格。

## 相对原图的取舍

- LanderPi 与 SO101 标签混用时不能因为开关开启就视为同一评估。
- 不复用 P17 的批次统计计算实现；两页都使用同一 Comparison Manifest。
- Preferred/Registered/Validated 有不同依据，不通过点击标签自动获得验证事实。

关联冲突：[VIS-C14](../../90-governance/08-visual-design-conflicts.md#vis-c14)、[VIS-C19](../../90-governance/08-visual-design-conflicts.md#vis-c19)、[VIS-C20](../../90-governance/08-visual-design-conflicts.md#vis-c20)。

## 主责功能与后端支撑

- [Evaluation｜评估概念](../06-training-evaluation/02-evaluation-workspace.md)

后端/契约：[09-evaluation-comparison](../../30-contracts/09-evaluation-comparison.md)、[02-evaluation-comparison](../../20-backend/06-training-evaluation/02-evaluation-comparison.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 查看评估证据 | [PAGE-16](16-evaluation-results.md) | 确定的 Report Revision ID |
| 仿真验证版本 | [PAGE-03](03-simulation.md) | 明确单个 Model Version，重新校验 |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
