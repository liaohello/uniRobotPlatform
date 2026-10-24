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

## 原生绑定协议（m1-binding-1）

状态：**平台侧已实现；原生侧候选补丁已实现并在服务器以 mock backend 验证，未部署到运行实例**（2026-10-24）。本轮 M1.2d 补齐生命周期互斥、prepared-only TTL 与单 Session 当前观测；实现与真实支持范围见 [M1.2d 交付记录](../../../backend-m1.2d.md)。

### 能力声明

`GET /api/v1/capabilities` 增加以下可选字段；缺省即“未声明”，平台按 `unsupported` 处理，不推断：

- `session_binding_protocol: "m1-binding-1"`
- `recording_begin_protocol: "m1-recording-1"`
- `config_manifest_sha256`：原生对实际读取的配置/extends 链/profile/arm_spec 字节与覆盖后有效配置的规范摘要
- `scene_manifest_sha256`：原生对自身 `/api/v1/scene` 编译场景 manifest 的规范摘要
- `runtime_python_version` / `runtime_package_versions`：原生运行环境自报，用于与依赖锁逐项核对

`config_manifest_sha256` 不覆盖源码 Git 提交与安装包；`scene_manifest_sha256` 不覆盖根 XML 文件摘要。三者与源码 pin、scene XML 摘要分别表述。

### 端点

| 方法 / 路径 | 请求 | 成功响应 |
|---|---|---|
| POST `/api/v1/session/prepare` | `contract_version, session_id, config_fingerprint, run_id, backend_generation, episode_id` | `accepted, binding_id, session_id, config_fingerprint, run_id, backend_generation, episode_id, state="prepared", motion_commands_accepted=false, expires_at_backend_monotonic_s, owner_state, recording_ready, motion_ready, motion_blockers` |
| GET `/api/v1/session/prepared/{binding_id}` | — | 与 prepare 相同字段的回读；`state ∈ prepared/started/expired/invalidated/released` |
| POST `/api/v1/session/start` | `binding_id, session_id, config_fingerprint` | `started, binding_id, session_id, run_id, backend_generation, episode_id, config_fingerprint, started_at_backend_monotonic_s, control_scope_granted, owner_state, owner_session_id, lease_expires_at_backend_monotonic_s, recording_required_for_motion, recording_begin_required, recording_ready, motion_ready, motion_blockers` |
| POST `/api/v1/session/release` | `binding_id` | `released` |
| POST `/api/v1/recording/begin` | `contract_version, binding_id, session_id, config_fingerprint, operator_id, operator_kind, view_source` | `accepted, binding_id, session_id, config_fingerprint, run_id, backend_generation, episode_id, recording_segment_id, recording_status="RECORDING", command_capture_ready=true, recording_start_event_seq>=1, initial_snapshot_sha256, durable_start_records=true` |

### 保证与拒绝

- prepare/start/release **不产生运动、不 RESET、不开始或结束录制、不改初态**；录制开始是独立操作，受 `recording.begin` 协议约束。
- `recording.begin` 复用既有 Recorder，读取当前 actual snapshot；只有 `recording_start`、`feedback_initial`、`initial_snapshot.json` 已持久化并 sync 后才返回 RECORDING。录制非 IDLE/COMPLETE 时拒绝，FAILED 时明确要求先处理；`m1-recording-1` 只覆盖 begin，stop/finalize 由下一节的 `m1-stop-1`/`m1-end-1` 定义。
- 任一身份字段与原生当前 runtime 不一致时拒绝（`accepted=false`/`started=false` + `reason`），不得静默改写。RESET 后所有 prepared/started binding 失效。
- `session_id` 由平台生成，原生必须原样回显；同一 run/generation/episode 同时最多一个有效 binding，重复 prepare 返回冲突而不是覆盖。
- `expires_at_backend_monotonic_s` 只约束 `prepared`；回读显式给出 `expires_scope="prepared"`。过期后 `start` 拒绝、回读返回 `expired`。`started` 不受准备 TTL 影响，只由 RESET、显式 release、身份变化或未来明确定义的 Session 结束事件失效；当前没有额外 Session close/end 事件，不以短租约替代持续 Session。
- 显式 Start 只建立 active Session 与执行器授权范围，**不获取 owner/lease**、不等于开始录制、也不等于已到位。`owner_state`/`lease_expires_at_backend_monotonic_s` 必须来自真实 owner 状态；没有 deadline 时返回 `null`，不得伪造。
- `recording_ready` 必须来自 Recorder 的真实 `RECORDING` + `command_capture_ready`，且绑定处于 started；`motion_ready` 只表示平台可运动条件（授权范围、录制要求、safety、冲突 owner），不是命令已获准执行。
- 重复 start 返回同一 binding；重复 begin 在已 RECORDING 时拒绝，平台对已 ready 的重复请求不再次调用 native。

### 并发边界

状态检查、RESET、legacy `episodes/start`、`recording/begin`、stop 和 recorder 失败停止必须使用同一 lifecycle 同步边界；锁顺序固定为 lifecycle → backend → recorder。RESET 的状态检查和 binding 失效在同一临界区完成；活动录制期间 commands RESET 与 legacy start 必须被重新检查并拒绝，不能凭锁外旧状态穿透。不得从 recorder 回调或已持有 backend 锁的路径反向获取 lifecycle。

### 平台核验规则

prepare 与回读必须使 `session_id`、`config_fingerprint`、`run_id`、`backend_generation`、`episode_id` 全部相等，且 `state=prepared`、`motion_commands_accepted=false`；start 还必须回显同一 `binding_id`、`state=started`、`started=true`，并给出 owner/录制/可运动字段。start 前置回读允许 `started`（用于丢失响应后的幂等恢复），但不得接受 `expired/invalidated/released`。`recording.begin` 还必须回显同一 binding/session/config 与 RECORDING、capture ready、durable start record、初始快照摘要；任一不符即 `native_recording_begin_failed`，不更新 recording-ready。

平台只允许访问上述五个路径加下一节 STOP/录制结束的两个 native 路径（共七个），不猜测其他端点。

## STOP 与录制结束协议（m1-stop-1 / m1-end-1）

状态：**平台侧已实现；native 侧候选补丁已在服务器以明确标注的 mock backend 完成真实 HTTP + 真实 Recorder 文件集成，未部署到任何运行实例，真实停车未验证**（2026-10-24）。实现、错误码分层与证据见 [M1.4 交付记录](../../../backend-m1.4.md) 与 [M1.4 证据册](../../../evidence/m1.4-stop-end/README.md)。

### 能力声明

`GET /api/v1/capabilities` 增加两个可选字段；缺省即"未声明"，平台按 unsupported 处理，不从 `m1-recording-1` 推断 end：

- `session_stop_protocol: "m1-stop-1"`
- `recording_end_protocol: "m1-end-1"`

### 端点

| 方法 / 路径 | 请求 | 关键响应 |
|---|---|---|
| POST `/api/v1/session/stop` | `contract_version, request_id, run_id, backend_generation, episode_id, binding_id?, session_id?, config_fingerprint?, reason, parking_timeout_s?` | `accepted, code, protocol="m1-stop-1", replayed, 身份回显, dispatch{dispatched,command_id,status,status_detail}, parking{confirmed,waited_ms,timeout_ms,base_stopped,base_stop_latched,base_velocity_m_s,arm_max_joint_velocity_rad_s,control_tick_id,observed_at_backend_monotonic_s,scope_coverage,observed_confirmed,coverage_complete,coverage_note}, owner_cleared_after_stop, safety_latched, recording_status, recording_segment_id, recording_touched=false, motion_restored=false` |
| POST `/api/v1/recording/end` | 同上，另必须携带 `binding_id, session_id, config_fingerprint, recording_segment_id` | 上述分层之外再加 `active_segment_id, binding_state, drain{completed,fanout_drained,recorder_queue_empty,queued_events,dropped_events}, finalize{completed,error,terminal_event_written,complete_tail,recording_status,audit_status,event_count,storage_ref,episode_complete_sha256,checksummed_artifacts,preserved_records}, integrity ∈ complete/incomplete_terminal_recorded/finalize_failed_missing_tail/unknown, reset_issued=false, safety_cleared=false, owner_acquired=false` |

平台侧对应 `POST /api/v1/sessions/{id}/stop` 与 `POST /api/v1/sessions/{id}/recording/end`，请求体只有 `request_id`、`reason`、`parking_timeout_s`；身份字段一律由平台存储的 Session 提供，前端不传。首次成功 201，幂等重放 200 + `replayed=true`。

### 保证与拒绝

- STOP 只下发 latch 型停止命令：不 RESET、不清安全锁、不结束录制、不获取 owner、不恢复运动；`recording_touched`/`motion_restored` 恒为 false。
- 安全 STOP **不以** `motion_ready`、`recording_ready`、owner 或租约为前置条件；这些门槛不得挡住紧急停止。结束录制仍要求本 Session 有效 binding 与已 begin 的 segment。
- 身份（run/generation/episode、binding、config_fingerprint、segment）在 lifecycle 临界区内重检；不符即拒绝且 `dispatch.dispatched=false`，不产生副作用。legacy `episodes/stop` 只有 reason，平台"先 GET 校验再 POST"不构成原子身份保护，不得据此声称能安全结束他人或更新的 segment。
- `accepted=true` 只表示该 `request_id` 在此身份下被受理；`parking.confirmed=true` 只表示已观测作用域得到停稳反馈；`finalize.complete_tail=true` 只表示尾记录写全。整机停稳且录制完整的唯一判据是 `parking.coverage_complete=true` 且 `integrity=complete`，缺任何一项都必须显示为部分/未确认/失败，不得合并成一个"成功"。
- 无反馈的作用域标 `not_observed`，失联或超时标 `unconfirmed`；不推断、不伪造。首版 gripper 无独立反馈，因此 `coverage_complete` 恒为 false。
- 同一 `request_id` 重试返回同一回执（native 进程内另有上限 64 条的回执缓存）；传输失败或结果未知只追加 attempt（`result_unknown`），不写回执。
- 并发结束：已 finalize 的 segment 由磁盘只读证据重放为 `end_already_finalized`（不下发第二个 STOP、不写第二个 `episode_terminal`、不结束更新的 segment）；平台对同一 Session 文档的读—改—写在锁内重读后合并，两个并发 accepted 回执各自保留；Session 关闭后的重复结束返回 409 `session_not_stoppable`，不虚构回执。
- `FAILED`/`INCOMPLETE`、有尾但审计失败、drain 或 finalize 失败缺尾分别由 `code` + `integrity` + `finalize.error` 表达，后续成功不清除历史失败记录。
- `parking_timeout_s`（0<v≤30，缺省用运行配置）只约束停车等待；超时与 finalize 结果是两个独立结论，不互相覆盖。

### 单 Session 当前观测增补

`current` 在 M1.2d 字段之外必须给出 `stop_available`、`recording_end_available`、`session_stop_protocol`、`recording_end_protocol`、`last_stop_code`、`last_end_code`、`recording_integrity`。可用性只由协议声明、Session 状态与身份匹配决定，不代表已经停稳；`current` 仍只读，不得触发 STOP、end、Start、续租或清安全锁，也不得写存储。

### 平台核验规则

STOP/end 的回执必须逐项回显同一 `run_id/backend_generation/episode_id`；`recording/end` 还必须回显请求的 `recording_segment_id` 与当时的 `active_segment_id`。平台只在 `accepted=true` 时强制身份一致，拒绝回执按原样保留以便诊断。`accepted=true` 但 `finalize.completed=false` 视为契约违背，不得当作收尾成功存储。


### 单 Session 当前观测（M1.2d）

`GET /api/v1/sessions/{id}` 返回存储的历史 Session（start/begin 回执、attempts 等）+ `current` 只读实时观测。`current` 必须给出：

- `source="live_native_read_only"`、`observed_at`、`valid`、`status`、`error`、`blockers`；
- 当前 runtime 与身份匹配、binding 状态/字段匹配/回读摘要；
- snapshot/recipe 有效性、authorization scope、录制要求；
- 当前 recording 状态/segment/capture/error、owner/lease 暴露情况、safety；
- `recording_ready`、`motion_ready`、`start_available`、`recording_begin_available`。

刷新只允许 native GET 与本地存储读取；不得续租、重绑、Start、清安全锁或启停录制，不得写存储。失联时 HTTP 200 + `status=offline`、`valid=false`，所有 ready/available 为 false。身份变化、snapshot/recipe 失效、binding `expired/invalidated/released`/不一致、录制未 ready、safety latch、owner 冲突都必须阻止 ready/available，并给出具体 blocker。历史回执保持原样；重复 GET 不改变 start/begin 的幂等结果。

`GET /api/v1/sessions` 是明确的存档视图：`{"source":"stored","live":false,"retrieved_at","sessions":[...]}`，不触发 native 读取，`current=null`。前端必须用单 Session GET 的 `current` 表示当前状态，不能把列表当实时状态。

### 当前差距

运行中的固定 native（8792，PID 941842，`drvfix` release，`configs/g4a2_server.yaml`）没有这些端点，且其 interface_profile/配置与 G1 配方不同。M1.2d 的候选补丁（含生命周期互斥与 prepared-only TTL）已在隔离 release 以 mock backend 完成真实 HTTP 集成；M1.4 的 STOP/end 补丁同样只在隔离 release 验证。两者都未部署、未重启 8792（其 capabilities 不含任何 `*_protocol` 字段）。真实 G1 prepared/Start、真实停车确认与 STOP/end 部署仍需维护窗口与 G1 vs G4A2 配方口径决定。
