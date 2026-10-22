# Training Runs｜作业列表与详情

规范 ID：`PAGE-09` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

查看训练作业实际状态、配置快照、指标和输出权重。

- 页面 ID：`PAGE-09`；导航归属：Models & Experiments。
- 主要对象：Training Job、Metrics、Logs、Checkpoint。
- 增量路线：E：训练监控。这是设计顺序，不是排期或启动实施。

## 图片参考

![Training Runs｜作业列表与详情 原始概念图](../../../foreendAssets/RoboLab%E6%A8%A1%E5%9E%8B%E8%AE%AD%E7%BB%83%E7%9B%91%E6%8E%A7%E4%BB%AA%E8%A1%A8%E6%9D%BF.png)

主参考：`IMG-007`，PPT 第 7 页。覆盖程度：完整页面构图参考。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 左侧 | 作业筛选列表，详情选中与批量勾选分开。 |
| 中央 | 选中 Job 状态、只读配置快照、曲线、资源和日志。 |
| 右侧 | Checkpoint、Artifacts、数据配方引用及模型注册。 |

## 关键操作与跳转

- 新建/复制进入 P08 新草案；停止/取消针对明确 Job。
- Pause/Resume 仅在适配器支持并确认后显示成功。
- 选择 Checkpoint 注册/进入 My Models；从模型进入 Simulation 前执行兼容检查。
- 验证视频为有来源的预览；正式评估跳 P14。

## 状态、失败与恢复

- 排队、启动中、运行、暂停、取消、失败和完成由后端上报。
- 指标缺失显示未上报；ETA 为估计；历史资源曲线注明采样时间。

## 相对原图的取舍

- 图中固定 Loss 列表改成按方法提供的指标 Schema。
- 不因多行显示 Running 就推断已具备多 GPU 并行调度能力。
- 不同任务或 Loss 定义不能直接以最小数值评选全平台最佳模型。

关联冲突：[VIS-C13](../../90-governance/08-visual-design-conflicts.md#vis-c13)、[VIS-C14](../../90-governance/08-visual-design-conflicts.md#vis-c14)、[VIS-C16](../../90-governance/08-visual-design-conflicts.md#vis-c16)、[VIS-C17](../../90-governance/08-visual-design-conflicts.md#vis-c17)。

## 主责功能与后端支撑

- [Model Training｜训练管理概念](../06-training-evaluation/01-training-workspace.md)

后端/契约：[01-jobs-models-results](../../20-backend/06-training-evaluation/01-jobs-models-results.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 复制为新训练 | [PAGE-08](08-training-setup.md) | 旧 Job Config 引用，新草案身份 |
| 查看模型输出 | [PAGE-12](12-my-models.md) | Checkpoint/Model Version 引用 |
| 配置正式评估 | [PAGE-14](14-evaluation-setup.md) | 固定模型与协议引用 |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
