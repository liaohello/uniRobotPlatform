# Episode Library｜轨迹列表

规范 ID：`PAGE-04` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

按任务、来源、结果和数据质量查找轨迹，并进入单条详情。

- 页面 ID：`PAGE-04`；导航归属：Data。
- 主要对象：Episode 摘要与筛选结果。
- 增量路线：B 最小列表，E 完整检索。这是设计顺序，不是排期或启动实施。

## 图片参考

![Episode Library｜轨迹列表 原始概念图](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E5%9B%9E%E6%94%BE%E4%B8%8E%E6%A0%87%E6%B3%A8%E7%95%8C%E9%9D%A2.png)

主参考：`IMG-004`，PPT 第 4 页。覆盖程度：局部参考：仅使用图左侧 Episode List；尚无独立完整列表设计图。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 顶部 | 项目/机器人/任务筛选、时间范围与搜索。 |
| 主体 | 可排序分页列表，显示时间、时长、来源组成、结果、完整性和标注状态。 |
| 辅助 | 选中摘要和加入集合入口；不在列表嵌完整回放器。 |

## 关键操作与跳转

- 打开一条 Episode 进入 P05；返回时保持筛选、排序和滚动。
- 来源筛选支持包含 Human/Expert/Policy 的混合轨迹。
- 多选后创建/加入 Dataset Collection，资格检查针对指定用途。

## 状态、失败与恢复

- 无结果与尚无录制分开；缺失/封口中记录可见但说明限制。
- 任务失败、完整性差、用途不合格分列，未知不强制写失败。

## 相对原图的取舍

- 参考图左侧小列表扩展为正式数据列表，P05 只保留可收起的上一条/下一条导航。
- 本页不显示 Mode Replay、倍速或全局播放按钮。
- 图片只提供局部视觉参考，列表密度、空态和批量操作仍需后续专门出图。

关联冲突：[VIS-C01](../../90-governance/08-visual-design-conflicts.md#vis-c01)、[VIS-C09](../../90-governance/08-visual-design-conflicts.md#vis-c09)、[VIS-C11](../../90-governance/08-visual-design-conflicts.md#vis-c11)。

## 主责功能与后端支撑

- [Dataset Management｜数据管理](../05-datasets/01-browser-quality-export.md)

后端/契约：[02-replay-annotation-store](../../20-backend/04-recording-replay/02-replay-annotation-store.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 打开轨迹 | [PAGE-05](05-episode-detail.md) | Episode ID、列表筛选与返回位置 |
| 创建/加入集合 | [PAGE-06](06-dataset-collections.md) | 选中的 Episode 引用 |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
