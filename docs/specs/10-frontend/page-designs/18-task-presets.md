# Task Presets｜任务模板资源

规范 ID：`PAGE-18` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

复用任务定义，查看所需机器人、观测、动作、成功条件与场景。

- 页面 ID：`PAGE-18`；导航归属：Resources / 辅助资源入口。
- 主要对象：Task Template Revision、能力要求、判据/阶段候选和默认配置。
- 增量路线：A/B 选择已有模板；复杂编辑后续。这是设计顺序，不是排期或启动实施。

## 图片参考

![Task Presets｜任务模板资源 原始概念图](../../../foreendAssets/%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BB%E5%8A%A1%E9%A2%84%E8%AE%BE%E6%8E%A7%E5%88%B6%E5%8F%B0.png)

主参考：`IMG-018`，PPT 第 18 页。覆盖程度：完整页面构图参考。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 左侧 | 机器人/任务家族/用途筛选。 |
| 主体 | 模板列表和明确可用状态。 |
| 右侧 | Overview、Success Criteria、Observation & Action、Variations。 |

## 关键操作与跳转

- Open in Scene Setup 引用固定模板修订并创建实验草案。
- 复制/编辑模板生成新修订，运行中的配置不受影响。
- 模板中的场景与机器人作为引用，不复制成另一套资产库。

## 状态、失败与恢复

- 可用、待适配、仅规划清楚区分。
- 阶段流程只作模板语义，允许子任务与双臂局部并行阶段。

## 相对原图的取舍

- Screw Assembly、Cloth、Outdoor 等卡片是远期素材，不全部纳入 V1。
- Human/Expert/Policy 是执行和动作来源，不把模板锁死为互斥三类数据。
- 卡片中的计数/受欢迎程度不作为实际资源统计。

关联冲突：[VIS-C01](../../90-governance/08-visual-design-conflicts.md#vis-c01)、[VIS-C11](../../90-governance/08-visual-design-conflicts.md#vis-c11)、[VIS-C17](../../90-governance/08-visual-design-conflicts.md#vis-c17)、[VIS-C22](../../90-governance/08-visual-design-conflicts.md#vis-c22)。

## 主责功能与后端支撑

- [任务模板目录与能力差异](../../00-overview/07-task-template-catalog.md)
- [任务模板选择与实验配置流程](../02-scene-setup/02-task-template-configuration.md)

后端/契约：[07-task-scene-experiment-config](../../30-contracts/07-task-scene-experiment-config.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 用于实验 | [PAGE-02](02-scene-setup.md) | Task Template Revision，创建草案 |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
