# M1.4｜受 Session/运行身份约束的机器人 STOP 与录制可靠结束候选

2026-10-24 · 范围：平台 Session 生命周期新增两个受身份约束的动作（机器人 STOP、录制结束）与 native 候选扩展协议 `m1-stop-1`/`m1-end-1`，并在服务器完成无物理隔离集成。

**候选实现与无物理集成验证已完成；8792 未部署、真实机器人停车未验证、M1 整体闭环未通过。** 本轮不启动第二个物理仿真实例、不替换 18953、不修改 `frontend/`，对 8792 只读取。

## 一、要解决的差距

M1.2c/M1.2d 已能准备 Session、显式 Start 并在无 RESET 的情况下开始录制，但结束侧仍缺可用契约：

- native 只有 legacy `POST /api/v1/episodes/stop`，请求体只带 `reason`，没有 Session/binding/run/generation/episode/segment 身份。平台"先 GET 校验再 POST"**不能**声称获得原子身份保护：校验与执行之间存在竞态，可能结束别的 Session 刚开的 segment。
- 平台此前只能用 `POST /api/v1/runs/{run_id}/stop`，那是**运行记录/进程管理**，不是机器人停止。
- "录制收尾有结论"缺乏可区分证据：命令是否下发、机器人是否真的停稳、Recorder 队列是否排空、尾记录是否写全、Episode 完整性如何，之前混在一个状态里。

## 二、契约与身份约束

两个动作都在既有 `m1-binding-1` 绑定与 runtime 身份之内执行，平台侧端点：

| 平台端点 | 请求 | 语义 |
|---|---|---|
| `POST /api/v1/sessions/{id}/stop` | `request_id`（1–128，幂等键）、`reason=OPERATOR_STOP`、`parking_timeout_s?`（0<v≤30） | latch 型机器人 STOP。不 RESET、不清安全锁、不结束录制、不获取 owner、不恢复运动 |
| `POST /api/v1/sessions/{id}/recording/end` | 同上，`reason=OPERATOR_FINISHED` | 先 STOP，再结束**本 Session 自己 begin 的 segment**并 finalize |

平台从存储的 Session 取 `binding_id`、`config_fingerprint`、`run_id/backend_generation/episode_id` 和 `recording_begin_receipt.recording_segment_id` 组装 native 请求；前端不传也不覆盖这些身份字段。native 在 lifecycle 临界区内**重新读取**当前 runtime 身份与 binding 后再执行，因此拒绝发生在副作用之前。

对应 native 端点 `POST /api/v1/session/stop`（协议 `m1-stop-1`）与 `POST /api/v1/recording/end`（协议 `m1-end-1`）。能力声明为 `capabilities.session_stop_protocol` / `recording_end_protocol`，缺省即未声明。`m1-recording-1` 只覆盖 begin，**不**被解释为包含 end。

## 三、回执分层：不把任何单一字段当"整机停稳且录制完整"

`StopReceipt` 与 `RecordingEndReceipt` 保留五个独立层次：

| 层 | 字段 | 只说明 |
|---|---|---|
| 请求受理 | `accepted`、`code`、`replayed` | 该 `request_id` 在此身份下被接受；不表示机器人已停 |
| STOP 下发 | `dispatch.dispatched`、`dispatch.command_id`、`dispatch.status` | 命令是否离开应用层（`DISPATCHED`/`submit_failed`/`not_sent`） |
| 实际停车 | `parking.confirmed`、`waited_ms`/`timeout_ms`、`base_stopped`、`arm_max_joint_velocity_rad_s`、`scope_coverage`、`observed_confirmed`、`coverage_complete`、`coverage_note` | 观测反馈是否证明停稳。`scope_coverage` 逐项 `confirmed/unconfirmed/not_observed`；无反馈的作用域标 `not_observed`，绝不推断。`coverage_complete=false` 时不得称"整机停稳"（首版 gripper 无独立反馈，恒为不完整） |
| Recorder 排空 | `drain.completed`、`recorder_queue_empty`、`queued_events`、`dropped_events`、`fanout_drained` | 录制器侧队列是否清空。`fanout_drained` 只报广播订阅滞后，不参与门控 |
| 落盘终态 | `finalize.completed`、`error`、`terminal_event_written`、`complete_tail`、`audit_status`、`recording_status`、`event_count`、`storage_ref`、`episode_complete_sha256`、`checksummed_artifacts`、`preserved_records`；`integrity ∈ complete / incomplete_terminal_recorded / finalize_failed_missing_tail / unknown` | 尾记录与摘要事实。`integrity` 是 Episode/segment 的最终判定；尾文件存在 ≠ 录制完整 |

停车超时与 finalize 结果分别保留：`ended_parking_unconfirmed`（已停稳证据不足但收尾成功）与 `end_finalize_failed`（收尾失败，`integrity=finalize_failed_missing_tail`）是不同结论。`FAILED/INCOMPLETE`、有尾但失败、drain/finalize 失败缺尾在 `code`+`integrity`+`finalize.error` 上各自可诊断，历史失败不被后续成功清除。

## 四、幂等、未知结果与并发

- 同一 `request_id` 重复：平台命中存储回执返回 HTTP 200 + `replayed=true`；native 侧另有进程内回执（上限 64 条）。
- 结果未知（传输失败/超时）：只追加 `stop_attempts` / `recording_end_attempts` 条目，`result="result_unknown"`，不伪造回执、不写 `stop_receipt`。
- 并发结束：native 在 lifecycle 临界区内重检 segment；已 finalize 的 segment 由磁盘只读 `finalized_receipt()` 重放为 `end_already_finalized`（`dispatch.dispatched=false`），**不产生第二个 `episode_terminal`**，也不结束更新的 segment。
- 平台侧读取—改写—写回同一 Session 文档时持 `session_write_lock` 并在锁内重读最新文档再合并（`_commit_lifecycle`），使两个并发 accepted 回执各自保留，不发生丢更新。网络调用在锁外，慢 STOP 不阻塞其他 Session 写入。
- 已被平台守卫拒绝的请求不写回执：Session 关闭后再次结束返回 409 `session_not_stoppable`，不虚构成功。
- `current` 仍只读：只做 native GET 与本地读取，不 STOP、不 end、不续租、不 Start。

## 五、保留的既有规则

`lifecycle → backend → recorder` 锁序不变；`prepared`-only TTL、`require_recording`、租约与安全停止规则不变。安全 STOP **不以** `motion_ready`/`recording_ready` 为前置条件，也没有新增会挡住既有紧急停止的 owner/lease 门槛（native `stop_session` 只校验身份与 binding）。失联或反馈不足一律 `unconfirmed`/`unknown`，不静默改写。

## 六、native 补丁候选（未提交、未部署）

冻结 release `m1h-20261024T152235Z-native`；补丁 `native-m1h.patch`（10 个文件，sha256 `d182801df7381bc45717ff40b0d61df28b5437e92f6ee5528127bdf6d231a99f`）：

| 文件 | 内容 |
|---|---|
| `contracts/models.py` | `StopDispatchEvidence`、`ParkingEvidence`（含 `observed_confirmed`/`coverage_complete`/`scope_coverage`）、`RecordingDrainEvidence`、`RecordingFinalizeEvidence`、`RecordingIntegrity`、`SessionStopRequest/Response`、`RecordingEndRequest/Response`、两个 capability 字段 |
| `app.py` | `stop_session`/`end_recording` 及 lifecycle 临界区实现、`_dispatch_stop_locked`/`_wait_parking_locked`/`_parking_evidence`、回执 LRU、磁盘重放 `_end_receipt_from_disk`、两个 POST 路由、legacy `_stop_episode_locked` 重构复用 |
| `data/recorder.py` | 只读 `finalized_receipt()`：从磁盘取 audit/recording 状态、事件数、`storage_ref`、`episode_complete_sha256`；不改 recorder 状态 |
| `attestation.py`、`config.py`、`cli.py`、`session_binding.py` | 协议声明与配置/绑定配套 |
| `tests/integration/test_recording_end.py`（新）、`test_lifecycle_race.py`、`test_session_binding.py` | 身份、并发、覆盖与失败路径 |

复用而非重写：仍走既有 `CommandType.STOP`（`payload={"latch": true}`）与既有 Recorder 的 `stop()`/`_finalize_episode()`；`recording/end` 内部调用同一收尾链。未把 `/runs/{id}/stop` 当机器人停止。

native 工作树保持未提交、未推送，既有未提交补丁原样保留，本轮不产出也不复用新的生产 source pin；候选源码摘要记录为 `native-candidate-pins.json`：pin `c550a4e495680c8895ca28e92b6aac7de22727086aa351cbad8f42a1618549de`（生产 recipe 白名单 155 路径中该 release 副本内实际存在的 152 个；缺的 3 个是 native `docs/*.md`，非代码）。它与生产 pin `a01098040d953608004a34b3c76519d7884eaa4b2c95e36822bd4e7d283b911c`（`a5cef52` base）不可互换。

**候选身份范围更正（2026-10-25）**：上述 `c550a4e4…` 只是生产 recipe 旧白名单 155 路径中该 release 副本内实际存在的 152 个路径的子集摘要，**不覆盖**补丁新增的执行模块 `src/mobilecar/attestation.py` 与 `src/mobilecar/session_binding.py`，因此**不能当完整 release pin**，也不表示 “drvfix + m1h 已组装验证”。该 release 经实测是 drvfix 内容叠加 m1h 补丁（`backends/mujoco/backend.py`、`ui/static/g4a2.html`、`ui/static/app.js`、`assets/landerpi/source_description/urdf/mecanum.xacro` 与 drvfix 一致而与 `a5cef52` 工作树不同），且从未作为该组合启动或验证过。完整、缺项必失败的发布身份见 [M1.4b](backend-m1.4b-unified-candidate.md) 第四、五节：`41b9c80c5d03eb11a2ff5551407430559514353d1d8bee324f4ad9111a5e038a`（154 个必需路径全部存在）。原 198 行清单与本节历史事实保持未改写。

## 七、服务器验证结果

所有测试、构建与集成在服务器执行；本地未运行任何测试或构建。

| 检查 | 结果 |
|---|---|
| 平台聚焦（`test_stop_end.py` + `test_prepare.py` + `test_drafts.py`） | 66 passed |
| 平台全量 | 123 passed / 3 failed（共 126） |
| 历史失败基线（未跳过、未算全绿） | `test_catalog::test_catalog_loads_real_tasks`、`test_catalog::test_every_task_has_existing_evidence`、`test_migrate::test_manifest_sources_exist`；与 m1.2b→m1.3 同一失败链（74/3 → 90/3 → 98/3 → 108/3 → 123/3），均为文档布局断言，与本轮 STOP/end 无关 |
| 本轮新增回归 | 并发结束丢回执一项：先失败（两个并发结束只留一个回执），加 `session_write_lock` + 锁内重读合并后修复；连续 10 次重复通过，两种竞态顺序均由独立 HTTP 运行覆盖 |
| native 聚焦（新集成测试 + 相关套件） | 31 passed / 0 failed |
| native 适用全量 | 122 testcases：120 passed / 2 failed，历史项 `tests.integration.test_provenance::test_provenance_manifest_targets_and_hashes_are_complete`、`tests.g3b_cases.test_scene_and_envelope::test_nav2_internal_yaw_goal_is_tighter_than_acceptance`，与 STOP/end 无关 |
| 隔离 cross-HTTP 集成 | 39/39 断言通过（另一次运行同样 39/39，覆盖相反竞态顺序） |
| OpenAPI | 由 FastAPI 自动生成，两个端点与 `StopSession/EndRecording/StopReceipt/RecordingEndReceipt/SessionCurrent` 视图字段齐备 |

JUnit、cross 结果与 Recorder 落盘文件（含逐文件 sha256 与本地副本核对）见 [证据册](evidence/m1.4-stop-end/README.md)。

## 八、隔离 cross-HTTP 集成（无物理）

真实平台客户端 → 真实 native HTTP → 真实 Recorder 文件系统，backend 为明确标注的 mock（`backend.kind: mock`，profile `m1i-cross-http-testonly-mock-no-physics`），独立记录目录、独立 SQLite、检查后确认空闲的回环端口 18954（native）与 18956（平台）。

覆盖：能力声明 → 校验/创建/Start → `recording/begin` → STOP（下发/停车/覆盖分层，`recording_touched=false`）→ 同请求重放 → 错误 runtime 身份（`stop_runtime_identity_mismatch`，不下发）→ 两个并发 `recording/end` → 磁盘核对 → 重试回读 → 未知 segment（`end_segment_mismatch`）→ 结束后再 begin 新 segment 并用旧 segment 结束（`end_already_finalized`，尾事件仍为 1）→ 外来 binding（`end_binding_not_found`）→ 新 segment 正常结束（尾事件累加为 2）→ 终态与身份不变性 → OpenAPI 暴露。

磁盘事实：一次结束只写一个 `episode_terminal`；`episode_complete.json` 的 sha256 与回执 `finalize.episode_complete_sha256` 一致；`audit_status=COMPLETE`、`event_count` 与尾记录一致、5 个校验和产物；`parking.coverage_complete=false`（gripper `not_observed`）仍被如实报告；run/generation/episode 全程未变。

test-only recipe（`mobilecar.g1.teleop.mock-testonly`，`recipe_revision: 2`，四个 required protocol）只存在于 `tools/mock_native_protocol_app.py`；生产 recipe `backend/config/mobilecar-g1-source.json` 未修改，其 `required_protocols` 仍只有 `session_binding`/`recording_begin`，因此生产配置下 STOP/end 被拒绝为 unsupported。

## 九、前端接线（本仓库不实现前端）

样例见 `docs/evidence/m1.4-stop-end/m1i-…-platform/api-samples/stop-end-openapi-and-refusals.json`。三类结论分开：

1. **真实生产拒绝**：8792 的 `GET /api/v1/capabilities`（只读）不含任何 `*_protocol` 字段；生产 recipe 下 `POST …/stop` → 409 `stop_unsupported`，`POST …/recording/end` → 409 `recording_end_unsupported`，`current.stop_available=false`、`recording_end_available=false`。前端必须据此灰化按钮并显示"当前运行实例不支持该动作"。
2. **mock 成功**：`code=stopped` 且 `parking.coverage_complete=false`；`code=ended`、`integrity=complete`、`drain.completed=true`。这只证明契约与状态机在合成后端上按分层工作。
3. **尚未执行**：真实 MuJoCo 停车、真机 STOP、`parking.confirmed=true` 的真机语义、8792 部署后行为，本轮均未验证，不得由 UI 文案宣称"机器人已停止"，除非 `parking.confirmed=true` 且 UI 明确 `coverage_note` 的覆盖范围。

前端接线要点：`request_id` 由前端为每次点击生成并复用（重试同 id → 200 replay，不重复下发）；按钮可用性读 `current.stop_available`/`recording_end_available`，二者由协议声明 + Session 状态 + 身份匹配决定；结果文案按 `code` 分支，`accepted=true` 只表示被受理；`ended_parking_unconfirmed`、`end_finalize_failed`、`ended_incomplete_terminal` 与 `end_already_finalized` 必须显示不同提示；409 `session_not_stoppable` 表示 Session 已关闭。导航、owner 获取、运动遥操作、训练与回放 UI 不在本轮范围。

## 十、候选与端口

| 端口 | 身份 | 本轮处理 |
|---|---|---|
| 8792 | 真实 8792：PID 941842、`drvfix` release、`configs/g4a2_server.yaml`、`backend_kind=mujoco`、`interface_profile=g4a1-1.0` | **仅 GET** `capabilities`/`health`。未 STOP、未 RESET、未 begin/end、未重启、未替换 |
| 18953 | Map/Route 资源候选 `m1g-20261024T113913Z-platform` | 保留，未替换、未停止 |
| 18949 / 18944 / 18943 | 既有前端预览与后端候选 | 保留，未触碰 |
| 18951 → 18949、18950 → 18944、18946 → 18943 | 最新前端预览代理链（18951 为当前前端端口，代理到 18949） | 只作现状记录，本轮未启动也未停止前端 |
| 18954、18956 | 本轮 test-only mock native 与 test-only 平台 | 启动前确认空闲，集成检查结束后已停止两个测试服务 |

## 十一、真实 M1 部署矩阵（本轮未执行任何步骤）

| 方案 | 运行时口径 | 身份影响 | 可观察效果 | 主要风险/维护 | 回滚判据 |
|---|---|---|---|---|---|
| G1 + `a5cef52`+patch | 现有生产 pin 所在 base | 生产 recipe 不变 | STOP/end 仍 unsupported | 补丁基线漂移 | 维持现状即回滚完成 |
| 独立 G4A2 recipe + `a5cef52`+patch | 与 8792 当前配方同族 | 需新 recipe 与 scene 摘要 | 候选协议可声明 | G1↔G4A2 口径未定 | 撤下 recipe，回到旧 pin |
| **推荐（待决定）：独立 G4A2 recipe + `drvfix`+m1h patch** | 8792 现运行 `drvfix`，叠加 `native-m1h.patch` | 候选摘要 `c550a4e4…`（旧白名单子集，非完整 pin）+ 完整发布身份 `41b9c80c…`，需与新的部署 recipe 一并冻结 | STOP/end 可用，停车覆盖仍不完整 | 需维护窗口、需真实停车确认、需重算生产 pin | 保留 `drvfix` release 与 `g4a2_server.yaml`，重启回旧实例 |

**推荐方案不是部署授权。** 仍待用户决定：① 部署配方口径（G1 还是独立 G4A2 recipe）；② 部署基线（是否以 `drvfix` 为底）；③ 新生产 source pin（须在维护窗口内对最终运行的 release 重新计算，本轮记录的是候选摘要，不替代它）。

维护窗口顺序（2026-10-25 修正，本轮未执行；推导见 [M1.4b](backend-m1.4b-unified-candidate.md) 第六节）：① 窗口前先冻结最终 native release，用 `tools/release_identity.py` 生成并核验完整发布身份，确定 recipe/protocol 与 config/scene/lock 摘要，把新 pin 与 recipe 一并固化；② 第①步全部可复算后才进入已获授权的维护窗口；③ 停 8792 前确认无活动录制 → 部署 → 只读核对 `capabilities` 协议声明 → 单次 begin/STOP/end 物理确认（记录 `parking.coverage_complete`、`integrity` 与作用域覆盖）；④ 运行成功后只补记 pin 与运行 release 一致的核对结论，**不在成功之后才重算 pin**；⑤ 任一步失败按回滚判据恢复原 release。

## 十二、真实闭环仍缺

1. 真实 MuJoCo/真机停车确认，尤其是 gripper 覆盖（现在恒 `not_observed`）。
2. 8792 或新实例上的候选协议部署与只读能力核对。
3. 端到端"录制完整"验收：把 `integrity`、`event_count`、摘要与数据集/回放侧核对串起来。
4. 停车未确认与 finalize 失败缺尾在真实运动/磁盘故障注入下的行为（当前只在合成/注入路径覆盖）。
5. 前端 STOP/end 控件接线与可用性文案（本轮只提供契约与样例）。

## 十三、冻结状态与边界

- 平台改动：`backend/src/unirobot/prepare.py`、`backend/src/unirobot/api.py`、`backend/tests/native_fixtures.py`、`backend/tests/test_stop_end.py`（新）、`backend/tools/mock_native_protocol_app.py`、`backend/tools/cross_http_stop_end_check.py`（新）；服务器冻结 release `m1i-20261024T163746Z-platform`，源码清单 42 文件、sha256 `789e8072e07337e98982f366acefa7c729172e783af51e8e74a53767ee5af81e`。本轮交付已在平台仓库本地提交 `ddc56a3`（分支 `codex/backend-m1-services`），**不推送**。
- native：补丁保持未提交、未推送、未部署；既有未提交补丁与 git 索引未改动；不产出新生产 pin。
- 规范更新：Session 生命周期（`m1-stop-1`/`m1-end-1` 端点与"七个路径"白名单、可用性字段）、Episode 采集生命周期（end/finalize 分层替换 legacy 描述）、控制命令契约（STOP 意图行与回执分层）、运行状态域（`closed` 判据）、决策与变更日志。
- 本 Goal 完成只代表"停止与录制收尾候选"完成：不代表 8792 已部署、不代表真实停车已验证、不代表 M1 闭环通过。
