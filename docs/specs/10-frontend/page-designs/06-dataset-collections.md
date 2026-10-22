# Dataset Collections｜数据集合

规范 ID：`PAGE-06` · 责任层：前端页面设计 · 版本：V0.6（2026-10-22）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

将多个 Episode 组织为可版本化、可追踪的训练或分析集合。

- 页面 ID：`PAGE-06`；导航归属：Data。
- 主要对象：Collection、筛选快照、Dataset Version。
- 增量路线：E：数据组织。这是设计顺序，不是排期或启动实施。

## 图片参考

![Dataset Collections｜数据集合 原始概念图](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E6%95%B0%E6%8D%AE%E9%9B%86%E7%AE%A1%E7%90%86%E7%95%8C%E9%9D%A2.png)

主参考：`IMG-005`，PPT 第 5 页。覆盖程度：完整页面构图参考；底部分析区缩为摘要。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 左侧 | 任务/机器人、来源、时间、标签和资格筛选。 |
| 主体 | 集合列表或卡片，展示 Episode 数量、版本和数据规模。 |
| 右侧 | 选中集合的摘要、最新版本和打开详情动作。 |

## 关键操作与跳转

- 由筛选结果或选择的 Episode 创建可编辑 Collection，membershipMode 明确为 query 或 explicit，保存其修订；查询预览不是冻结数据版本。
- 按 [集合/版本契约](../../30-contracts/05-dataset-model-lineage.md) 冻结当前选择后打开 P07；M1 只读 Episode 回放无需先创建 Collection。
- 点击单条轨迹预览时进入 P05，避免在此重复完整标注工具。

## 状态、失败与恢复

- 未发布草案、已发布版本、导出中和不兼容分别显示。
- 同一 Episode 的控制来源可混合，集合不强制按 Human/Expert/Policy 互斥分库。

## 相对原图的取舍

- Experiences/Expert Data/Generated 等图片标签改为筛选视图，保留统一 Episode 底座。
- 移除顶部 Replay 播放控件和默认完整传感器/标注编辑区。
- 从 Collection 的确定修订解析成员并创建不可变 Dataset Version；集合后续变化不修改已发布成员。解析/发布失败不产生可训练的半版本；删除原始数据不是本页默认快捷操作。

关联冲突：[VIS-C01](../../90-governance/08-visual-design-conflicts.md#vis-c01)、[VIS-C09](../../90-governance/08-visual-design-conflicts.md#vis-c09)、[VIS-C11](../../90-governance/08-visual-design-conflicts.md#vis-c11)。

## 主责功能与后端支撑

- [Dataset Management｜数据管理](../05-datasets/01-browser-quality-export.md)

后端/契约：[01-quality-versions-export](../../20-backend/05-dataset-export/01-quality-versions-export.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 打开集合固定版本 | [PAGE-07](07-dataset-version.md) | Collection/Dataset Version ID |
| 完整轨迹预览 | [PAGE-05](05-episode-detail.md) | 具体 Episode ID |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
