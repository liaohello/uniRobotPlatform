# 前端页面设计与图片索引

规范 ID：`FE-PAGE-DESIGNS` · 责任层：前端页面设计 · 版本：V0.6（2026-10-22）

每个页面设计文件都嵌入至少一张原始参考图，并描述入口、对象、区域、操作、反馈、异常和修正。功能规则仍由原来的八个功能包负责，本目录负责“这些能力如何组成一个可读、可操作的页面”。

本目录共有 21 个逻辑视图，包含列表/详情、标签视图及后续候选页；不等于 21 个顶级菜单、独立系统或全部 V1 开发承诺。功能包不因新增页面而重复拆建。

[Specification 总索引](../../README.md) · [统一设计规则](../01-shell/04-visual-design-rules.md) · [22 项图片冲突与取舍](../../90-governance/08-visual-design-conflicts.md) · [素材/PPT 对照](../../references/04-visual-asset-catalog.md)

## 页面覆盖

| 页面与设计节点 | 导航归属 | 主图片 | 覆盖程度 | 增量位置 |
|---|---|---|---|---|
| [PAGE-01 Home｜项目首页](01-home.md) | Home | IMG-001 | 完整页面构图参考 | A：轻量入口 |
| [PAGE-02 Scene Setup｜实验配置与场景布置](02-scene-setup.md) | Prepare | IMG-023/024/025 | 导航、近场抓取、双臂转运三变体共用页面；旧 IMG-002 保留 | M1 已支持预设 / M2 复用；其余按任务切片 |
| [PAGE-03 Simulation｜统一在线任务工作台](03-simulation.md) | Run | IMG-022 | 用户更新的 V2 主图；原图保留对照，状态语义待收敛 | A/B 首条闭环，C/D 增量 |
| [PAGE-04 Episode Library｜轨迹列表](04-episode-library.md) | Data | IMG-004 | 局部参考：仅使用图左侧 Episode List；尚无独立完整列表设计图 | B 最小列表，E 完整检索 |
| [PAGE-05 Episode Detail｜回放、标注与审核](05-episode-detail.md) | Data | IMG-004 | 完整页面构图参考；图底 A/B 方案是备选说明 | B 同步只读回放，E 标注审核 |
| [PAGE-06 Dataset Collections｜数据集合](06-dataset-collections.md) | Data | IMG-005 | 完整页面构图参考；底部分析区缩为摘要 | E：数据组织 |
| [PAGE-07 Dataset Version｜划分、质量与导出](07-dataset-version.md) | Data | IMG-005 | 局部参考：右侧 Dataset Details 与底部 Statistics；导出向导尚无独立图 | E：数据版本与出口 |
| [PAGE-08 Training Setup｜训练配置](08-training-setup.md) | Models & Experiments | IMG-006 | 局部采用图 6 左侧配置；完整图混有运行监控 | E：模型训练规划 |
| [PAGE-09 Training Runs｜作业列表与详情](09-training-runs.md) | Models & Experiments | IMG-007 | 完整页面构图参考 | E：训练监控 |
| [PAGE-10 Offline Inference｜离线预测诊断](10-offline-inference.md) | Models & Experiments / 模型详情工具 | IMG-008 | 局部参考：模型、输入和预测区；运行控制区不采用 | 后续候选诊断工具，非首条闭环必做 |
| [PAGE-11 Model Catalog｜模型来源目录](11-model-catalog.md) | Models & Experiments / Models | IMG-011 | 完整页面构图参考 | E 或后续；先登记实际接入模型 |
| [PAGE-12 My Models｜模型版本与 Checkpoint](12-my-models.md) | Models & Experiments / Models | IMG-012 | 完整页面构图参考 | E：模型版本 |
| [PAGE-13 Registry & Compare｜模型版本比较](13-model-registry-compare.md) | Models & Experiments / Models | IMG-013 | 完整页面构图参考 | E 或后续比较能力 |
| [PAGE-14 Evaluation Setup｜评估协议配置](14-evaluation-setup.md) | Models & Experiments / Evaluation | IMG-014 | 局部采用左侧配置；图中实时/结果面板分给 P15/P16 | E：先单次评估；批量参数后续 |
| [PAGE-15 Evaluation Running｜评估运行监控](15-evaluation-running.md) | Models & Experiments / Evaluation | IMG-015 | 完整页面构图参考 | E：监控；并行调度后续另定 |
| [PAGE-16 Results & Reports｜评估结果](16-evaluation-results.md) | Models & Experiments / Evaluation | IMG-016 | 完整页面构图参考 | E：评估结果与回放证据 |
| [PAGE-17 Batch Comparison｜评估批次比较](17-batch-comparison.md) | Models & Experiments / Evaluation | IMG-017 | 完整页面构图参考 | 后续比较方案；不要求先建设并行集群 |
| [PAGE-18 Task Presets｜任务模板资源](18-task-presets.md) | Resources / 辅助资源入口 | IMG-018 | 完整页面构图参考 | A/B 选择已有模板；复杂编辑后续 |
| [PAGE-19 Robot Platform｜机器人能力资源](19-robot-platform.md) | Resources / 辅助资源入口 | IMG-019 | 完整页面构图参考；硬件事实与外形须全部替换为工程来源 | A/B 只读能力登记；D 主臂与双臂 |
| [PAGE-20 Scenes｜场景资源库](20-scenes.md) | Resources / 辅助资源入口 | IMG-020 | 完整页面构图参考 | A/B 已有场景选择；C 受限对象资产 |
| [PAGE-21 Real Robot Deployment｜真机部署后续参考](21-real-robot-future.md) | 后续环境能力；不加入当前活动 V1 导航 | IMG-010 | 完整候选构图参考；执行与安全语义尚未定义 | 后续，不因存在图片纳入当前 V1 |

所有页面均有图片参考。PAGE-04 Episode Library、PAGE-07 Dataset Version、PAGE-08 Training Setup、PAGE-10 Offline Inference、PAGE-14 Evaluation Setup 目前主要依赖原图局部，不视为已经具备完整专用定稿。PAGE-02 的双臂 2D 摆放、PAGE-03 的导航/双臂专属预设也仍需补专门图稿；保留已有图和明确的图文约束，不虚构新图已生成。

## 推荐阅读顺序

当前先看 [M1/M2 基线](../../00-overview/10-first-task-closed-loop.md)：M1 走 PAGE-02 → PAGE-03 → PAGE-04/05，取得真实记录并重载回放；M2 用 bimanual 验证组件/宿主复用。最小数据版本/训练/预测是后续阶段，表中 A–E 为历史标记。资源页可仅提供真实已有预设，轻宿主不必有全部页面。

图片中红色框、中文引导箭头、A/B 对比和未知硬件外形保留为原始参考，不属于产品界面。图片样式的取舍不改变控制权、数据或执行契约。

## 2026-10-22 Simulation 更新

PAGE-03 主图改为 IMG-022；旧 IMG-003/009 仅作对照，未修改其他页面主图。[删除/替换清单及后续意见](../03-simulation/06-simulation-v2-review.md) 单独维护，PPT 第 3 页仍为旧图。

## 2026-10-22 Scene Setup 更新

PAGE-02 当前采用 IMG-023/024/025 的三任务变体；旧 IMG-002/PPT 第 2 页保留。Task Params 与任务工具由 schema/capability 驱动，公共交互和版本由 [共享组件](../02-scene-setup/05-shared-scene-components.md) 与 [配置契约](../../30-contracts/07-task-scene-experiment-config.md) 主责。完成三图归档后停止大范围绘图，后续按真实任务补局部交互。
