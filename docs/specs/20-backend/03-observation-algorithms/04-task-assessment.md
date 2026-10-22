# 任务判据、终止原因与人工辅助统计

规范 ID：`BE-TASK-ASSESSMENT` · 责任层：后端 · 版本：V0.2（2026-10-21）

状态：设计草案；S08/S09 是用户提供的分析文本，不自动视为所有细节已确认。Waypoint 范围以 S10 的用户明确选择为准。实现及产品验收均未执行。

来源：[S08](../../90-governance/sources/S08-frontend-ia-analysis.md)。

[上级目录](README.md) · [总索引](../../README.md)

关联需求：[REQ-TASK-002](../../indexes/05-requirements.md#req-task-002)

## 判据随任务版本绑定

| 任务族 | 判据方向，数值均待标定 |
|---|---|
| PointGoal/Route | 位置/可选朝向、路线进度/偏差、超时与失败点 |
| ObjectNav | 正确语义目标、观测发现、接近/停靠完成 |
| 感知/伺服 | 同语义参考点的方向/位置误差、时效、稳定性、扰动后恢复 |
| IK/底盘辅助 | 受约束末端误差、关节限位/碰撞、停靠与后续操作可行性 |
| 移动抓取 | 离开支撑、抬升、稳定保持与抓持反馈 |
| 双臂 | 抓取、台面中转或空中交接的独立协议、释放与最终放置 |

不能把可达空间画成规则圆就宣称可导航/可抓取；台面中转和手递手分别定义任务和接触证据。

## 结果轴

Task Outcome、Termination Reason、Recording Integrity、指定用途 Training Eligibility 分别保存。S08 的 Success/Failure/Timeout/Aborted/Invalid Run 作为报表分类建议；Timeout/Aborted 是结束原因，Invalid Run 是评估有效性，不压成一个替代所有原始字段的大枚举。Unknown/未评估保留，不补写成功或失败。

同时记录人工接管、外力扰动及其作用范围/区间。自主成功率的样本集合和分母明确排除或单独分组人工辅助完成的运行；允许失败轨迹数据完整且有分析用途。

评分引用任务版本、观测/真值权限与证据；自动评分、模型预测和人工审核独立。具体判据见各 Task Template，前端只展示服务结果。

验收：[TEST-TASK-001](../../40-verification/04-task-config-workflow-acceptance.md#test-task-001)。
