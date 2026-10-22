# Evaluation Setup｜评估协议配置

规范 ID：`PAGE-14` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

固定模型、任务判据、测试条件和记录规则，提交可复现评估。

- 页面 ID：`PAGE-14`；导航归属：Models & Experiments / Evaluation。
- 主要对象：Evaluation Config Draft、Protocol Revision、测试场景/种子清单。
- 增量路线：E：先单次评估；批量参数后续。这是设计顺序，不是排期或启动实施。

## 图片参考

![Evaluation Setup｜评估协议配置 原始概念图](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E8%AF%84%E4%BC%B0%E6%8E%A7%E5%88%B6%E5%8F%B0.png)

主参考：`IMG-014`，PPT 第 14 页。覆盖程度：局部采用左侧配置；图中实时/结果面板分给 P15/P16。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 主体 | 模型版本/任务、场景版本、种子集、成功/终止规则。 |
| 辅助 | 实际支持的随机化项、记录字段、兼容检查及资源请求。 |
| 操作区 | 保存评估草案、校验、提交。 |

## 关键操作与跳转

- 判据引用任务协议；自定义阈值生成新修订。
- 启动时冻结评估清单与允许人工干预政策，跳 P15。
- 编辑 Scene/Task 转相应草案页，返回后重新校验。

## 状态、失败与恢复

- 提交前不展示伪造 Running 或成功率。
- 不支持 Real/Mixed、随机化项或多环境时说明能力未接入。

## 相对原图的取舍

- 移出 Live Evaluation View、进度格和结果表，避免配置与运行状态互相覆盖。
- Simulation 为当前执行环境；Real/Mixed 不由参考图自动纳入 V1。
- Episode 数量和阈值都是任务配置，不硬编码图片示例 50 或 50mm。

关联冲突：[VIS-C02](../../90-governance/08-visual-design-conflicts.md#vis-c02)、[VIS-C08](../../90-governance/08-visual-design-conflicts.md#vis-c08)、[VIS-C10](../../90-governance/08-visual-design-conflicts.md#vis-c10)、[VIS-C15](../../90-governance/08-visual-design-conflicts.md#vis-c15)、[VIS-C16](../../90-governance/08-visual-design-conflicts.md#vis-c16)、[VIS-C18](../../90-governance/08-visual-design-conflicts.md#vis-c18)。

## 主责功能与后端支撑

- [Evaluation｜评估概念](../06-training-evaluation/02-evaluation-workspace.md)

后端/契约：[04-task-assessment](../../20-backend/03-observation-algorithms/04-task-assessment.md)、[09-evaluation-comparison](../../30-contracts/09-evaluation-comparison.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 编辑实验场景草案 | [PAGE-02](02-scene-setup.md) | 当前配置引用与返回来源 |
| 提交评估成功 | [PAGE-15](15-evaluation-running.md) | 已接受 Evaluation Run ID |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
