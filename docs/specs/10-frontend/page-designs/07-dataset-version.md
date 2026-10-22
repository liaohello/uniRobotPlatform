# Dataset Version｜划分、质量与导出

规范 ID：`PAGE-07` · 责任层：前端页面设计 · 版本：V0.6（2026-10-22）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

检查一份确定的数据版本是否满足指定训练用途，并生成可追踪导出。

- 页面 ID：`PAGE-07`；导航归属：Data。
- 主要对象：Dataset Version、Split Manifest、Export Recipe、Export Report。
- 增量路线：E：数据版本与出口。这是设计顺序，不是排期或启动实施。

## 图片参考

![Dataset Version｜划分、质量与导出 原始概念图](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E6%95%B0%E6%8D%AE%E9%9B%86%E7%AE%A1%E7%90%86%E7%95%8C%E9%9D%A2.png)

主参考：`IMG-005`，PPT 第 5 页。覆盖程度：局部参考：右侧 Dataset Details 与底部 Statistics；导出向导尚无独立图。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 摘要 | 版本、成员数量、来源、标注修订、观测/动作 schema。 |
| 详情标签 | Episodes、Quality、Splits、Export History。 |
| 导出抽屉 | 目标版本/配方、字段映射、采样和单位校验、报告。 |

## 关键操作与跳转

- 选择任务用途和训练/导出配方，检查所需相机键、动作维度、频率和标签。
- 查看并固化 train/validation/test 划分；避免同源片段跨集合泄漏。
- 通过后提交导出，保留来源版本、转换规则及错误报告；从固定版本进入 Training Setup。

## 状态、失败与恢复

- 缺字段、映射未知、资格不满足和导出部分失败可定位到 Episode。
- 发布版本成员、清理/标注/转换/split 引用固定；如由 Collection 产生，记录其 revision 和解析清单，集合后续变化不修改该版本。此页属于后续数据阶段，不作为 M1 回放前置。

## 相对原图的取舍

- Download 不等于 LeRobot 导出；导出版本和 schema 尚未冻结。
- 不可仅按成功率决定训练资格，也不假设所有 ACT/BC 都要求语言或完整阶段标签。
- 此图未覆盖划分与导出完整流程，后续图稿需要补这些视图。

关联冲突：[VIS-C09](../../90-governance/08-visual-design-conflicts.md#vis-c09)、[VIS-C11](../../90-governance/08-visual-design-conflicts.md#vis-c11)、[VIS-C14](../../90-governance/08-visual-design-conflicts.md#vis-c14)。

## 主责功能与后端支撑

- [Dataset Management｜数据管理](../05-datasets/01-browser-quality-export.md)

后端/契约：[01-quality-versions-export](../../20-backend/05-dataset-export/01-quality-versions-export.md)、[05-dataset-model-lineage](../../30-contracts/05-dataset-model-lineage.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 检查问题轨迹 | [PAGE-05](05-episode-detail.md) | Episode ID 与问题时间区间 |
| 配置训练 | [PAGE-08](08-training-setup.md) | 固定 Dataset Version、Split 与配方引用 |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
