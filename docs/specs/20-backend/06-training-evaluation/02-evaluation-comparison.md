# 评估编排、报告与比较服务边界

规范 ID：`BE-EVAL-COMPARISON` · 责任层：后端能力域 · 版本：V0.3（2026-10-21）

状态：职责设计草案。复用既有仿真与任务后端，未实现/部署新的评估服务。

[共享评估契约](../../30-contracts/09-evaluation-comparison.md) · [共享任务判据](../03-observation-algorithms/04-task-assessment.md) · [评估页面](../../10-frontend/page-designs/14-evaluation-setup.md)。

| 子功能 | 后端责任 | 前端边界 |
|---|---|---|
| 接受配置 | 校验模型、场景、任务、种子和支持的随机化；固定快照 | 编辑草案并展示反馈 |
| 编排运行 | 调用现有 Session/控制源/录制器，绑定 Run 与 Episode | 监控；在线交互跳同一 Simulation |
| 生命周期 | 作业排队/启动/终止和取消，反馈实际状态 | 不以切页、关闭预览或本地按钮状态替代 |
| 辅助记录 | 从 Ownership/事件取得接管区间、恢复、外力与任务结果 | 不自行推断自主成功 |
| 报告 | 按固定证据和版本化规则输出指标、计数和缺失原因 | 摘要/表格/导出用同一修订 |
| 比较 | 检查共同条件、差异与统计依据，生成 Comparison Manifest | 展示可比较性，关闭无依据排名 |

Evaluation Running 的画面只读订阅同一 Session。用户需要接管时定位到统一 Simulation；数据和评估记录真实控制变化。不得为评估页另建不经过统一 Ownership 的速度/关节指令通道。

批次可以串行执行；并行环境数量、资源调度和优先级尚未确定。界面多行 Running 只显示后端实际支持的状态，不构成并行集群实现要求。

Run 失败时保留已生成证据及明确终止原因；当前 Episode 封口由原采集系统负责。重试生成新的 Run/Attempt 身份并保留关联，不静默覆盖旧结果。采集丢帧不自动等于任务失败，反之亦然。

现有项目接入依赖 [适配边界](../07-existing-project-adapters/01-integration-boundaries.md)；精确端点/传输/调度实现待选定任务切片时核对。
