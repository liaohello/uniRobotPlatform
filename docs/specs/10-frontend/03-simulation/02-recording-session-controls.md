# 运行与录制操作区

规范 ID：`FE-SIM-RECORDING` · 责任层：前端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-011](../../../设计过程与Specification总册_20261021.md#doc-011)、[doc-016](../../../设计过程与Specification总册_20261021.md#doc-016)、[doc-033](../../../设计过程与Specification总册_20261021.md#doc-033)、[doc-036](../../../设计过程与Specification总册_20261021.md#doc-036)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-STATE-003](../../indexes/05-requirements.md#req-state-003)、[REQ-REC-001](../../indexes/05-requirements.md#req-rec-001)

## 目标与责任边界

负责在线工作台的运行、任务、录制与结束反馈。界面只请求状态变化，不自行决定 Recorder 已保存或 Episode 已完成。停止运动、暂停物理、结束录制和 Reset 的边界需要分别设计。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 准备 | 展示当前 Session、任务、观测与录制 Profile 及可用流。 |
| 开始与收尾 | 展示后端报告的开始、录制、Finalize 和失败；精确状态表未冻结。 |
| 控制操作 | 运行/暂停/停止/结束保存/Reset 的控件和后果要明确，避免一个按钮承载全部行为。 |
| 跨页 | 页面切换不隐式结束录制属于现有建议；持续驾驶输入需单独撤销。 |

## 未决与依赖

关联 OQ-003、OQ-004、OQ-022。暂停录制、失败保留和 Reset 边界由契约与后端收敛后再固化交互。

## 关联规范

- [独立状态域与运行模型](../../00-overview/04-runtime-state-domains.md)
- [Simulation｜在线仿真工作台](01-workflow-task-panels.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)
- [工作区、运行与记录验收](../../40-verification/02-workspace-runtime-acceptance.md)

## 验收入口

- [TEST-REC-004](../../40-verification/02-workspace-runtime-acceptance.md#test-rec-004)（现有草案，未执行；依赖的未决规则须先收敛）。

## V0.2 执行与录制独立

选择 Human/Expert/Policy 执行配置不等于开始录制。接管仅在连续有效录制且没有 Reset/终止时保留同一 Episode；显示来源切换事件。具体见 [执行配置](05-execution-profiles-policy-rollout.md)。

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。

## V0.4 三组状态栏

当前图分别显示 Simulation 的 Start/Pause/Resume/Reset、Task 的 Begin/End 与 Recording 的时长/停止录制。按钮显示应按后端实际状态约束：Running 不重复 Start/Resume，任务运行不重复 Begin，Recorder 收尾显示 Finalizing/失败而非立即成功。未录制时需有开始录制入口。

End Task 不自动表示成功；Reset 和 End Task 是否封口当前 Episode/录制继续等精确边界仍在 OQ-004，不能仅凭三个独立视觉区域推断已决定全部转换。暂停物理、终止任务和录制启停的后果分别明确。

## V0.8 STOP 与结束录制的可接线契约（后端候选，前端未实现）

M1.4 为这两个动作提供了身份绑定的候选契约：`POST /api/v1/sessions/{id}/stop` 与 `POST /api/v1/sessions/{id}/recording/end`，请求只需 `request_id`（每次点击生成并在重试时复用）、`reason` 与可选 `parking_timeout_s`；Session/binding/run/generation/episode/segment 由平台补齐，界面不能指定别人的 segment。

按钮可用性与文案必须按分层判据分开：

- `current.stop_available` / `current.recording_end_available` 决定是否可点，来源是协议声明 + Session 状态 + 身份匹配，不是"已经停稳"。生产 recipe 下二者为 false，需显示"当前运行实例不支持"而不是隐藏或假装成功。
- 受理后先显示"停止请求已受理"；`dispatch.dispatched=false` 时说"命令未下发"；`parking.coverage_complete=false` 时按 `scope_coverage` 列出 `confirmed/unconfirmed/not_observed`，不得写"整机已停稳"（首版夹爪恒无独立反馈）。
- 收尾显示 Finalizing；`ended_parking_unconfirmed`、`ended_incomplete_terminal`、`end_finalize_failed` 与 `end_already_finalized` 必须是不同提示，失败与缺尾不得被后续成功覆盖。
- `code=stopped/ended` 之外的 409 `session_not_stoppable` 表示 Session 已关闭；同一 `request_id` 重放返回 200 `replayed=true`，界面不重复提示"已发送"。
- STOP 不 Reset、不清安全锁、不结束录制，也不获取控制权；`runs/{run_id}/stop` 不能作为这两个按钮的后端。

契约细节见 [Session 生命周期 §STOP 与录制结束协议](../../20-backend/01-session-scene/01-session-lifecycle.md#stop-与录制结束协议m1-stop-1--m1-end-1) 与 [M1.4 交付记录](../../../backend-m1.4.md)（含 OpenAPI/错误样例）。真实停车与部署验证尚未执行，OQ-004 关于 Reset/End Task 是否封口 Episode 的边界仍待决定；本轮没有修改前端代码。
