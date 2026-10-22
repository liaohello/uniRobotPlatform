# My Models｜模型版本与 Checkpoint

规范 ID：`PAGE-12` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

管理实际导入或训练产出的模型版本，检查运行兼容性与验证依据。

- 页面 ID：`PAGE-12`；导航归属：Models & Experiments / Models。
- 主要对象：Model Version、Checkpoint、来源关系、Evaluation 引用。
- 增量路线：E：模型版本。这是设计顺序，不是排期或启动实施。

## 图片参考

![My Models｜模型版本与 Checkpoint 原始概念图](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E6%A8%A1%E5%9E%8B%E5%9B%AD%E6%B7%B1%E8%89%B2%E4%BB%AA%E8%A1%A8%E7%9B%98.png)

主参考：`IMG-012`，PPT 第 12 页。覆盖程度：完整页面构图参考。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 主体 | 本地/已导入模型列表，版本、方法和适配状态。 |
| 右侧 | 数据/训练/权重来源、IO Schema、Checkpoints 与协议化指标。 |
| 操作区 | 配置训练、离线诊断、进入 Simulation、配置评估。 |

## 关键操作与跳转

- 固定选择 Model Version 与 Checkpoint，显示 action/observation 和归一化配置。
- Open Inference 进入 P10；Run in Simulation 进入 P03；Evaluate 进入 P14。
- 登记/推荐/验证三种标记分开；推荐只是有理由的人工选择。

## 状态、失败与恢复

- 已注册不等于可运行；权重缺失、适配未知与测试失败分别显示。
- 历史评估分数显示协议、样本量与人工辅助情况。

## 相对原图的取舍

- 下方重复模型比较区缩为选中摘要，完整比较进入 P13。
- “Best Success Rate”不作为跨任务全局排名；指标有条件和来源。
- SO101 的 RGB+D/50Hz、硬件资源及所有数值均须由实际模型配置提供。

关联冲突：[VIS-C02](../../90-governance/08-visual-design-conflicts.md#vis-c02)、[VIS-C08](../../90-governance/08-visual-design-conflicts.md#vis-c08)、[VIS-C14](../../90-governance/08-visual-design-conflicts.md#vis-c14)、[VIS-C17](../../90-governance/08-visual-design-conflicts.md#vis-c17)、[VIS-C19](../../90-governance/08-visual-design-conflicts.md#vis-c19)。

## 主责功能与后端支撑

- [Model Training｜训练管理概念](../06-training-evaluation/01-training-workspace.md)

后端/契约：[05-dataset-model-lineage](../../30-contracts/05-dataset-model-lineage.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 离线诊断 | [PAGE-10](10-offline-inference.md) | 固定模型/预处理引用 |
| 进入仿真 | [PAGE-03](03-simulation.md) | 固定模型/任务配置，显式启动 |
| 配置评估 | [PAGE-14](14-evaluation-setup.md) | Model Version ID |
| 比较版本 | [PAGE-13](13-model-registry-compare.md) | 已选模型版本引用 |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
