# Model Catalog｜模型来源目录

规范 ID：`PAGE-11` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

登记可参考或可导入的模型来源，并说明实际接入状态。

- 页面 ID：`PAGE-11`；导航归属：Models & Experiments / Models。
- 主要对象：外部 Model Reference、Import Job、兼容性声明。
- 增量路线：E 或后续；先登记实际接入模型。这是设计顺序，不是排期或启动实施。

## 图片参考

![Model Catalog｜模型来源目录 原始概念图](../../../foreendAssets/RoboLab%20%E6%A8%A1%E5%9E%8B%E5%8A%A8%E7%89%A9%E5%9B%AD%E4%BB%AA%E8%A1%A8%E7%9B%98.png)

主参考：`IMG-011`，PPT 第 11 页。覆盖程度：完整页面构图参考。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 左侧 | 来源、方法、任务和声明的输入筛选。 |
| 主体 | 来源条目与版本/许可证/导入状态。 |
| 右侧 | 说明、输入输出要求、适配证据与后续动作。 |

## 关键操作与跳转

- 从官方或本地引用创建导入计划，由服务器处理权重和依赖。
- 导入完成进入 My Models；经过适配/验证后才允许申请 Simulation 加载。
- Fine-tune 进入 P08 配置，不直接启动训练。

## 状态、失败与恢复

- 仅参考、未导入、导入失败、已导入、待适配、可验证分别显示。
- 兼容性未知保留未知，不能凭机器人标签判定。

## 相对原图的取舍

- ALOHA 等条目不能仅凭名称与 ACT/VLA 当相同类型模型；条目类型由实际接入定义。
- 图片中的参数量、许可证、性能和 star 数未核实，不能写入真实产品数据。
- Run Inference 进入诊断工具；Run in Simulation 进入统一工作台，均不自动发动作。

关联冲突：[VIS-C02](../../90-governance/08-visual-design-conflicts.md#vis-c02)、[VIS-C14](../../90-governance/08-visual-design-conflicts.md#vis-c14)、[VIS-C17](../../90-governance/08-visual-design-conflicts.md#vis-c17)、[VIS-C19](../../90-governance/08-visual-design-conflicts.md#vis-c19)。

## 主责功能与后端支撑

- [Model Training｜训练管理概念](../06-training-evaluation/01-training-workspace.md)

后端/契约：[01-jobs-models-results](../../20-backend/06-training-evaluation/01-jobs-models-results.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 查看导入结果 | [PAGE-12](12-my-models.md) | Import Job/Model Version ID |
| 配置微调 | [PAGE-08](08-training-setup.md) | 模型版本与支持的训练方法 |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
