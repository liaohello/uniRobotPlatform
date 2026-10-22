# Offline Inference｜离线预测诊断

规范 ID：`PAGE-10` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

检查模型在指定输入上的输出形状、映射与预测可视化。

- 页面 ID：`PAGE-10`；导航归属：Models & Experiments / 模型详情工具。
- 主要对象：Model Version、固定 Observation Sample、Prediction Artifact。
- 增量路线：后续候选诊断工具，非首条闭环必做。这是设计顺序，不是排期或启动实施。

## 图片参考

![Offline Inference｜离线预测诊断 原始概念图](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E6%8E%A8%E7%90%86%E4%B8%8E%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0.png)

主参考：`IMG-008`，PPT 第 8 页。覆盖程度：局部参考：模型、输入和预测区；运行控制区不采用。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 左侧 | 模型版本/Checkpoint、推理参数。 |
| 中央 | 来自 Dataset 的固定时间样本，或明确冻结的输入快照。 |
| 右侧 | 预测动作、时间跨度、Frame/单位、推理耗时与候选 Ghost。 |

## 关键操作与跳转

- 选择可完整提供模型输入的样本，并记录预处理和输入版本。
- 预测只生成诊断结果，不向执行器发送动作。
- 上传图片只供支持该输入的方法使用；所需本体/历史缺失时阻止完整动作预测。
- “在仿真中验证”携带引用进入 P03，经校验和显式启动；此处不保留 Play Rollout。

## 状态、失败与恢复

- 输入键/历史长度缺失、动作解码不支持或不兼容明确显示。
- 候选输出不标记为已执行；样本结果绑定模型与输入。

## 相对原图的取舍

- 删除图中 Simulation Rollout 和第二套在线录制/Reset 控件。
- SO101 输入按当前三路 RGB 和本体配置，不默认加入深度。
- 不将 Offline/Simulation/Real Robot 三个标签当同一执行状态切换。

关联冲突：[VIS-C02](../../90-governance/08-visual-design-conflicts.md#vis-c02)、[VIS-C05](../../90-governance/08-visual-design-conflicts.md#vis-c05)、[VIS-C08](../../90-governance/08-visual-design-conflicts.md#vis-c08)、[VIS-C14](../../90-governance/08-visual-design-conflicts.md#vis-c14)、[VIS-C18](../../90-governance/08-visual-design-conflicts.md#vis-c18)。

## 主责功能与后端支撑

- [执行配置与模型推理入口](../03-simulation/05-execution-profiles-policy-rollout.md)
- [Model Training｜训练管理概念](../06-training-evaluation/01-training-workspace.md)

后端/契约：[02-experts-policies-task-phases](../../20-backend/03-observation-algorithms/02-experts-policies-task-phases.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 查看模型详情 | [PAGE-12](12-my-models.md) | Model Version ID |
| 在仿真验证 | [PAGE-03](03-simulation.md) | 模型/输入/推理配置引用，重新校验后显式启动 |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
