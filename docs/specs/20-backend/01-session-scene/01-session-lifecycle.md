# 仿真 Session 与运行生命周期

规范 ID：`BE-SESSION-LIFECYCLE` · 责任层：后端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-010](../../../设计过程与Specification总册_20261021.md#doc-010)、[doc-011](../../../设计过程与Specification总册_20261021.md#doc-011)、[doc-015](../../../设计过程与Specification总册_20261021.md#doc-015)、[doc-016](../../../设计过程与Specification总册_20261021.md#doc-016)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-STATE-001](../../indexes/05-requirements.md#req-state-001)、[REQ-STATE-002](../../indexes/05-requirements.md#req-state-002)

## 目标与责任边界

承载服务器仿真与任务会话。Workspace 属于前端导航；仿真、任务、录制、控制权各自有状态，不能合成一个由页面驱动的大状态机。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 会话身份 | 定义 Session、机器人、场景配置、运行代数和 Episode 之间的关系。 |
| 物理执行 | 由执行服务管理启动、暂停、单步、停止、Reset；规划与只读查询不成为另一个在线物理推进者。 |
| 状态发布 | 提供权威实际状态和状态转换原因，前端不凭页面可见性推断运行状态。 |
| 资源 | 并发上限、活动实例切换和设备分配尚未冻结，不因存在 Session 对象就支持多实验并行。 |

## 未决与依赖

关联 OQ-003、OQ-004、OQ-026。复用现有执行者的原则来自上一轮工程分析；精确方法名、超时与生命周期先核对各后端。

## 关联规范

- [独立状态域与运行模型](../../00-overview/04-runtime-state-domains.md)
- [全局信息架构与工作区](../../10-frontend/01-shell/01-navigation-context.md)
- [Robot / World State 契约草案](../../30-contracts/01-robot-world-state.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)
- [工作区、运行与记录验收](../../40-verification/02-workspace-runtime-acceptance.md)

## 验收入口

- [TEST-SCENE-002](../../40-verification/02-workspace-runtime-acceptance.md#test-scene-002)（现有草案，未执行；依赖的未决规则须先收敛）。

## V0.6 创建、开始与身份映射

Session 身份/状态域以 [SYS-STATE](../../00-overview/04-runtime-state-domains.md) 为准：prepared→显式 Start 成功后 active，active 内物理可 Running/Paused，显式结束并有录制终态后 closed，故障终止 failed；不把原生 RunRecord 或进程状态直接当相同枚举。适配器保留 platformSessionId 与 native run/generation/episode/segment 的映射，Reset 边界见 [CT-EPISODE](../../30-contracts/03-episode-events-annotations.md)。

Scene Setup 的创建请求只能消费 [ValidatedSnapshot](../../30-contracts/07-task-scene-experiment-config.md)，成功后处于 `prepared`，不因创建、导航或验证推进物理/启动任务/录制。显式 Start 时重查实时适配器、必需流与控制权，并返回真实状态。底层运行时若只能“创建即启动”，统一适配器在提供等价未开始状态前不得声称符合此创建契约。首版可顺序单实例运行；存在活动实例时明确冲突，不隐式停止旧 Session。HostApp 可有多个入口，物理推进和执行器授权按运行实体跨宿主统一裁决。mobileCar 原生 episodes/start 含 RESET/录制，禁止用来模拟 prepared；M1 对此能力的接入差距须明示，不能用只读 scene/snapshot 声称任意配置已应用。
