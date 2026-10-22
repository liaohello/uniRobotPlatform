# Home｜项目首页

规范 ID：`PAGE-01` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

从项目进入一条任务闭环，并找回最近配置、运行和数据。

- 页面 ID：`PAGE-01`；导航归属：Home。
- 主要对象：Project、最近 Runtime Session、Episode、Experiment Config。
- 增量路线：A：轻量入口。这是设计顺序，不是排期或启动实施。

## 图片参考

![Home｜项目首页 原始概念图](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E5%B9%B3%E5%8F%B0%E4%BB%AA%E8%A1%A8%E7%9B%98.png)

主参考：`IMG-001`，PPT 第 1 页。覆盖程度：完整页面构图参考。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 顶部 | 项目与连接摘要；运行告警仅显示后台 Session 摘要。 |
| 主体 | 继续最近任务、打开配置、查看最近 Episode；保留任务模板快捷入口。 |
| 辅助 | 六业务阶段流程缩为可折叠说明，首次使用时展示。 |

## 关键操作与跳转

- 选择任务快捷卡后进入 Scene Setup 草案，不直接启动机器人。
- 最近运行进入同一 Session 的 Simulation；最近 Episode 进入历史详情。
- 保留项目筛选及返回位置，项目、机器人和任务分别显示。

## 状态、失败与恢复

- 无项目/无数据时提供明确的创建配置入口。
- 断连时保留可访问历史数据，不显示虚构 Connected 或运行成功。

## 相对原图的取舍

- 移除图片中六项编号导航与第二套模型入口，使用统一导航映射。
- 大幅缩小欢迎横幅；把主要空间给正在进行的任务和最近结果。
- 卡片中的模型外形、时间和成功状态均为占位，不能视为真实工程数据。

关联冲突：[VIS-C01](../../90-governance/08-visual-design-conflicts.md#vis-c01)、[VIS-C02](../../90-governance/08-visual-design-conflicts.md#vis-c02)、[VIS-C17](../../90-governance/08-visual-design-conflicts.md#vis-c17)、[VIS-C21](../../90-governance/08-visual-design-conflicts.md#vis-c21)。

## 主责功能与后端支撑

- [全局信息架构与工作区](../01-shell/01-navigation-context.md)

后端/契约：[01-session-lifecycle](../../20-backend/01-session-scene/01-session-lifecycle.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 任务快捷卡 | [PAGE-02](02-scene-setup.md) | Task Template/Experiment Config 引用 |
| 最近运行 | [PAGE-03](03-simulation.md) | 现有 Session ID |
| 最近轨迹 | [PAGE-05](05-episode-detail.md) | Episode ID |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
