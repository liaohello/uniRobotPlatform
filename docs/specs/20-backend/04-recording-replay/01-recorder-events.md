# 原始采集、Episode 与事件写入

规范 ID：`BE-DATA-RECORDER` · 责任层：后端

文档状态：V0.6（2026-10-22）mobileCar 采集适配职责；复用原生 Recorder，平台接入及运行验收未执行。

来源：[doc-009](../../../设计过程与Specification总册_20261021.md#doc-009)、[doc-011](../../../设计过程与Specification总册_20261021.md#doc-011)、[doc-033](../../../设计过程与Specification总册_20261021.md#doc-033)、[doc-036](../../../设计过程与Specification总册_20261021.md#doc-036)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-REC-001](../../indexes/05-requirements.md#req-rec-001)、[REQ-FORCE-004](../../indexes/05-requirements.md#req-force-004)

## 目标与责任边界

负责协议约定数据流、动作链、事件与元数据的持久化，以及录制生命周期。阶段和来源不是原始数据的替代物。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 身份与配置 | 新平台 Episode 绑定 Session 与唯一 ValidatedSnapshot；原生 run/generation/episode/segment 和存储引用保留，索引投影不能成为第二配置权威。 |
| 来源 | Human/Expert/Policy、演示/干预用途、阶段分别记录，自动化不能冒充真人。 |
| 动作与事件 | 保留拒绝、受理、执行与反馈的可追踪关系；外力与动作来源分别记录。 |
| 写入与收尾 | STARTING→RECORDING→DRAINING→COMPLETE，失败 FAILED/INCOMPLETE；起始持久化和 finalize 回执明确，停车状态独立；详见 CT-EPISODE。 |

## 未决与依赖

OQ-004/020/021/022 在 mobileCar M1 的必要部分按 [CT-EPISODE](../../30-contracts/03-episode-events-annotations.md) 收敛；其他机器人/用途保留其实际格式和时间策略，不以“尚未冻结所有格式”阻断 M1。

## mobileCar 接入职责

原生 start 含 RESET，不作为 Prepare Session 实现。只有起始内容写盘同步、返回 accepted/RECORDING 后确认录制 ready；RESET 请求受理与实际初态应用另核对。停止分别记录 STOP/停车反馈与 Recorder finalize；超时/失败保留实际结果，不能仅凭 COMPLETE 推断停稳。

begin/append/end/failure 是适配职责，不要求新增逐帧浏览器 API。复用原生 Recorder/ReplayReader；平台新增索引/sidecar 关联快照与原生记录，不重写原始 Episode。FAILED 或尾标记缺失不冒充完整；正常尾标记存在但状态 FAILED 仍显示不完整。Reset 后保留原生 Episode/generation/segment 映射，不能承诺跨 Reset 录制连续。

来源：[S16](../../90-governance/sources/S16-mobile-first-spec-repair.md)。对应 [TEST-MOBILE-001/002](../../40-verification/06-scene-setup-first-loop.md) 待执行；原生实现不等于平台已接通。

## 关联规范

- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)
- [任务、观测与数据配置](../../00-overview/03-task-and-observation-profiles.md)
- [时间、坐标系与命令生命周期](../../30-contracts/04-time-frames-units.md)
- [独立状态域与运行模型](../../00-overview/04-runtime-state-domains.md)
- [工作区、运行与记录验收](../../40-verification/02-workspace-runtime-acceptance.md)

## 验收入口

- [TEST-REC-001](../../40-verification/02-workspace-runtime-acceptance.md#test-rec-001)（现有草案，未执行；依赖的未决规则须先收敛）。
- [TEST-REC-004](../../40-verification/02-workspace-runtime-acceptance.md#test-rec-004)（现有草案，未执行；依赖的未决规则须先收敛）。
