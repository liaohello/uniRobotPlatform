# Episode、录制接入、事件与标注契约

规范 ID：`CT-EPISODE` · 责任层：共享契约 · 版本：V0.6（2026-10-22）

状态：当前 mobileCar 接入的语义基线；原生行为已只读核对，平台适配与产品验收未执行。来源：[S16](../90-governance/sources/S16-mobile-first-spec-repair.md)；原始 S02/S03/S04/S05/S07 需求保留。

[配置快照](07-task-scene-experiment-config.md) · [时间/坐标](04-time-frames-units.md) · [当前阶段](../00-overview/10-first-task-closed-loop.md)

## 一套配置权威与原生身份

平台新采集的 Episode 必须绑定平台 Session 和一个 ValidatedSnapshot；它固定已解析 Scene/Robot/Task、实例初态覆盖、Execution、适用的观测/录制引用。Episode 不再平行维护一份 Task Profile 或可变 Experiment Config 作为第二配置权威。

| 信息 | 必需性与归属 |
|---|---|
| platformSessionId / validatedSnapshotRef | 新平台采集必需，可保存在平台 sidecar/index；不要求修改原生数据格式 |
| origin | sourceProject/adapter、原生 run/backend generation/episode ID、schema/reader 版本及原始存储引用；标识不能只靠显示名 |
| recording segment | 原生区间 ID、起止、序列/时间、终态、同 Episode 多段关系；保留 native 边界 |
| 配置索引投影 | 可缓存 scene/robot/task/Execution/Recording refs，但必须与快照一致；冲突报告并阻止作为配置一致数据使用，不静默覆盖原文 |
| 实际采集事实 | 实际 Owner/来源/操作者、动作/观测 schema、起始 actual snapshot、结束/失败与完整性；与预期配置分开 |
| 条件引用 | Route 仅路线任务；算法观测/模型仅实际使用算法/策略时；seed 按任务；实际 Operator View 及变化按人工界面追溯需要记录 |

历史原生 Episode 可只有原生配置/身份：索引明确 provenance=legacy/native、缺哪些平台引用及验证证据，不伪造 ValidatedSnapshot，不反写原始文件。是否可用于后续训练由用途资格另判，不能因能播放就补写为已验证配置。

## 分层数据

| 层 | 内容 |
|---|---|
| 原始记录 | 观测、本体、变换、实际发出的动作及源时间/身份 |
| 在线事件 | 请求/受理/拒绝/执行反馈，控制源切换、接管/干预、阶段、Reset/碰撞/失败 |
| 派生/清理 | FK/重采样、片段、变换/排除原因及版本，不覆盖原始文件 |
| 离线标注 | 区间、作者/修订、词表、候选/审核来源；评估真值、预测与人工结论独立 |
| 训练视图 | 固定成员、观测/动作映射、split、导出与资格报告，属于后续阶段 |

动作注明底盘/关节/TCP、绝对或增量、目标或实测、单位、顺序、周期和对应观测身份；请求被拒绝不能混作实际执行 action。Human/Expert/Policy 是实际来源，Demonstration/Intervention 是用途，任务结果、录制完整性、停车确认和训练资格分别表达。

## 采集生命周期：begin / append / end / failure

| 操作职责 | 接受和完成条件 | 持久化及失败规则 |
|---|---|---|
| begin | 校验所需来源/流和配置绑定；进入 STARTING，起始记录/actual snapshot 可靠写入后才确认 RECORDING | 返回原生 Episode/segment 身份和真实状态；失败不授予 recording-ready，不伪造数据 |
| append | 原生 recorder 追加源观测、动作链和事件；浏览器不承担逐帧持久化 | 按原生 seq/sample/control tick、measurement/arrival 等时间和媒体引用关联；重入/丢样按原生策略显式记录 |
| end | 接受停止后进入 DRAINING；排空队列、终态/索引/完整性写入完成才确认 COMPLETE | 停车确认与 recorder finalize 分开显示，不能以 COMPLETE 证明物理已经停稳 |
| failure | 状态 FAILED、完整性 INCOMPLETE，保留已写记录、媒体与诊断，停止/保持依原控制契约 | 存储故障不保证尾事件/完整索引仍能写入；缺失尾部不能推定成功，不自动删除原始证据 |
| list/read | 按 source/native identity 读取索引、事件、状态、媒体及质量信息 | ReplayReader 只读，不发送动作或推进物理；不完整内容仅按可解析部分展示并明示缺失 |

这些是能力职责，不冻结一套新的公共 HTTP begin/append API。适配器包装已有 Recorder/Reader；只在原协议缺少必要身份/完成回执时补适配，不并行建设第二录制器。

## mobileCar M1 的已核对映射

下表是原项目实际入口的静态证据，不意味着统一平台已完成调用或验证。

| 平台含义 | mobileCar 现有入口/行为 | 平台必须保留的边界 |
|---|---|---|
| 读当前资源/状态 | GET `/api/v1/scene`、`/api/v1/snapshot`；manifest 含 model_id/model_sha256/scene_id | 只读当前编译场景/actual state，不证明任意编辑/切场景或预设初态应用 |
| 开始录制 | POST `/api/v1/episodes/start`，含 operator_id/operator_kind/view_source 等；先请求 RESET 再 Recorder.start | 明示 RESET 边界，不能用于 Prepare Session；accepted=true 且 recording_status=RECORDING 才确认起始记录持久化；RESET RECEIVED/DISPATCHED 不等于实际初态已应用，另核对生效 generation/epoch 与 actual snapshot |
| 停止录制 | legacy POST `/api/v1/episodes/stop` 只有 `reason`，无 Session/binding/segment 身份；身份绑定的结束走下方 M1.4 的 `recording/end` | accepted=true 且状态 COMPLETE 才标录制完成；仍单独显示停车反馈/超时；FAILED 不冒充完整。平台不得用"先 GET 校验再 POST legacy"声称获得原子身份保护 |
| 列表/历史/媒体 | GET `/api/v1/episodes`、`/api/v1/episodes/{episode_id}` 及 assets 子资源 | 保留 read_only、recording_status、segment_count、complete_tail；有尾标记也须结合终态/质量判断 |

原生身份与边界规则：Episode 由实际 backend snapshot 中的 episode_id 标识，RESET 可改变 Episode/generation；Recording Segment 是录制区间，不能假设每次重开只换 segment 或每次都只换 Episode。以实际响应/事件报告原生身份，平台 Session 与 origin 组合索引；同一 Episode 的多个 segment 不展平成互不相关的数据。

M1 在停止/Reset 发生时必须给当前 segment 的终态和身份切换结论：由原生服务按顺序 finalize 旧记录、确认新 epoch，再启用新采集/命令上下文。若原生不支持“录制中任意 Reset”，界面禁用该路径，先显式 end；不能承诺连续跨 Reset 同一 Episode。旧命令/lease/epoch 按既有后端规则失效，不由宿主自行重放。

mobileCar 的 native start 会写 recording_start、feedback_initial、initial_snapshot 并 sync；正常 stop 排空后写 terminal/checksums/episode_complete。FAILED 状态下若 finalize 成功，可能写出尾标记但仍为 FAILED/INCOMPLETE；若 drain/finalize 本身失败，尾标记可能缺失。complete_tail 是尾部存在性信息，不等于录制完整性结论。队列溢出/写盘故障沿用原生失败和停车机制；平台不静默掉流来保持绿色。

## M1.2c 无 RESET 开录候选（m1-recording-1）

M1.2c 在原生候选中增加独立的 `POST /api/v1/recording/begin`，复用既有 Recorder，不经过 `episodes/start` 的 RESET：

- 请求必须绑定已 start 的 `m1-binding-1` binding、平台 `session_id`、`config_fingerprint` 与当前 run/generation/episode；任一不符拒绝。
- 读取当前 actual snapshot 作为起始状态；写入 `recording_start`（segment 内 event_seq 从 1 开始）、`feedback_initial` 与原子 `initial_snapshot.json`，`writer.sync()` 后才返回 `RECORDING` 与 `command_capture_ready=true`；响应给出 segment、起始事件序号与 initial snapshot SHA-256。
- 不 RESET、不发运动命令、不获取 owner/lease、不停止录制；录制为 STARTING/RECORDING/DRAINING 时拒绝，FAILED 时要求先按既有路径处置。
- 该轮只定义 begin，不含 stop/finalize、停车确认、回放与跨 RESET 连续采集；stop/finalize 现由下方 M1.4 的 `m1-stop-1`/`m1-end-1` 定义，其余仍走既有 `episodes/stop` 与后续工作包。`require_recording`、租约与安全停止门控不变。
- 平台侧仅在 native 声明 `recording_begin_protocol=m1-recording-1` 时调用；未声明即 `unsupported`。真实 8792 未部署候选，平台 live 仍不会调用该端点。

该能力与 [Session 生命周期](../20-backend/01-session-scene/01-session-lifecycle.md#原生绑定协议m1-binding-1) 的 start 分开：Start 只建立 active Session 与授权范围，begin 才建立录制 ready；三者（active、owner/lease、recording ready、可运动）必须分别表达。

### 并发边界（M1.2d）

commands RESET、legacy `episodes/start`（含其 RESET）、`recording/begin`、stop 与 recorder 失败停止必须共享同一 lifecycle 同步边界，锁顺序为 lifecycle → backend → recorder。录制状态检查与 RESET/开录在同一临界区重检，活动录制期间不得凭锁外旧状态提交 RESET；binding 失效也在 RESET 应用的同一临界区完成。该约束不改变 `require_recording`、STOP、停车等待、lease 或 Recorder 的既有安全语义，也不把 stop/finalize 纳入 m1-recording-1。

## M1.4 身份绑定 STOP 与可靠录制结束候选（m1-stop-1 / m1-end-1）

平台在既有 binding 身份内新增两个动作，端点与保证见 [Session 生命周期](../20-backend/01-session-scene/01-session-lifecycle.md#stop-与录制结束协议m1-stop-1--m1-end-1)。从采集侧看，回执必须让下面五层各自可判断，不得压缩成单个"成功"：

| 层 | 判据字段 | 不能替代 |
|---|---|---|
| 请求受理 | `accepted` + `code` + `replayed` | 不代表命令已下发，也不代表已停稳 |
| STOP 下发 | `dispatch.dispatched`、`command_id`、`status` | 下发成功不等于机器人停 |
| 实际停车 | `parking.confirmed`、`scope_coverage`、`observed_confirmed`、`coverage_complete`、`coverage_note` | 只有 `coverage_complete=true` 才称整机停稳；无反馈作用域为 `not_observed`，失联/超时为 `unconfirmed` |
| Recorder 排空 | `drain.completed`、`recorder_queue_empty`、`queued_events`、`dropped_events`；`fanout_drained` 只报订阅滞后不参与门控 | 队列空不等于尾记录写全 |
| 落盘终态与完整性 | `finalize.*` 与 `integrity ∈ complete / incomplete_terminal_recorded / finalize_failed_missing_tail / unknown` | `complete_tail=true` 或尾文件存在都不等于录制完整 |

采集终态规则：

- `integrity` 是本 segment 的完整性结论，直接取自磁盘证据（audit 状态、`event_count`、`episode_complete_sha256`、`storage_ref`、校验和产物数），不来自页面推断。
- 停车超时与 finalize 结果分别保留：`ended_parking_unconfirmed` 表示收尾完成但停稳证据不足；`end_finalize_failed` 表示收尾失败并按 `finalize.error` 诊断；`ended_incomplete_terminal` 表示有尾但审计 INCOMPLETE。三者都不能显示为"录制完整"。
- 结束只作用于请求携带且经 native 在 lifecycle 临界区内重检确认的 segment：身份不符 → `end_runtime_identity_mismatch`/`end_binding_not_found`/`end_binding_mismatch`/`end_binding_<state>`/`end_segment_mismatch`，且 `dispatch.dispatched=false`；已 finalize → `end_already_finalized`（磁盘重放，不写第二个 `episode_terminal`，不影响更新的 segment）。
- 同一 `request_id` 重试返回同一回执；传输失败/结果未知只记 attempt。`require_recording`、lease、RESET 与 recorder 的既有语义不变；STOP 不 RESET、不清安全锁、不获取 owner、不恢复运动，也不以 `motion_ready`/`recording_ready` 为前置条件。
- 平台 `current` 只读增加 `stop_available`、`recording_end_available`、`last_stop_code`、`last_end_code`、`recording_integrity`；可用性来自协议声明与身份匹配，不是停稳证明。

状态：**平台侧已实现；native 侧候选补丁已在服务器以明确标注的 mock backend + 真实 Recorder 文件系统完成隔离集成，未部署、真机停车未验证**（2026-10-24）。实现、验证与边界见 [M1.4 交付记录](../../backend-m1.4.md)，HTTP 与磁盘证据见 [M1.4 证据册](../../evidence/m1.4-stop-end/README.md)。

## 原始存储与读取适配

索引记录 sourceProject/adapter/native IDs、原始位置、format/schema/reader 版本、媒体/事件引用、完整性与可用流。原始文件继续由各工程保存，平台只维护映射/sidecar，不为统一前端强制搬目录或重写格式。使用原始 source time 和记录的变换，不能按浏览器收包顺序对齐。

M1 只要求其已声明必需流能重载和只读回放；缺失流、损坏或不支持 reader 给出定位原因。动力学重执行、离线重算和任意帧续跑是额外能力，不能从只读播放推导。

源码依据：[原生契约](../../../../mobileCar/docs/interface_contract_v1.md)、[API/运行入口](../../../../mobileCar/src/mobilecar/app.py)、[Recorder](../../../../mobileCar/src/mobilecar/data/recorder.py)、[ReplayReader](../../../../mobileCar/src/mobilecar/data/replay.py)。这些路径为本地调查证据，正式接入还需固定对应源码版本与实际运行结果。

验收：[TEST-MOBILE-001/002](../40-verification/06-scene-setup-first-loop.md)，保留 [TEST-REC-001/004](../40-verification/02-workspace-runtime-acceptance.md) 的来源/Reset 测试；训练与集合不作为 M1 前置。

## 平台历史只读 API（M1.5a 首个切片，S21/DEC-058）

来源固定为一个明确声明（source_id、adapter、native release、实际 recording_root、声明规模与归档聚合基线），原始数据留在服务器，平台代码不搬运、不重写、不重算导出，也不为此修改或重启任何 native 实例。只读由构造保证而非约定：验证工具只能通过一个不接受 method/body 参数的 GET-only 入口访问 native，逐条留下请求日志；重算派生结论只允许在隔离副本上进行（M1.5b）。

- 读取面只有八条 GET：Episode 列表（`limit` 上限 200、`offset`、`run_id`/`recording_status`/`episode_id` 过滤）、轻量详情、可用流目录、按流的有界记录页、该 Episode `assets/` 子树内的媒体资产、单 Episode 帧关联页（`GET /api/v1/episodes/{episode_id}/frames`），以及 M1.5d 的历史姿态准备页（`GET /api/v1/episodes/{episode_id}/robot-state`）与冻结模型资产页（`GET /api/v1/episodes/{episode_id}/model/assets/{asset_id}`）。列表/详情/流/记录/媒体统一 `schema_version: unirobot-mobilecar-episode-read-1`，帧关联页使用 `unirobot-mobilecar-frame-link-2`，姿态页使用 `unirobot-mobilecar-history-pose-1`，全部带 `read_only: true`；详情必须保持轻量，不把整份 JSONL 交给前端，也不建设通用数据查询框架。
- 复合身份保留 `source/adapter + run_id + episode_id + recording_segment_id(+previous) + native contract_version + episode 目录原始引用`；episode 显示名不是全局键，同名跨 run 必须带 `run_id`，否则 409 `episode_id_ambiguous`。`backend_generation` 若只存在于记录 payload，则按 payload 如实标注，不伪装成顶层字段。
- 时间与动作保持原义：`wall_utc / backend_monotonic_s / sim_time_s / measurement_time_s / arrival_time_s / clock_id / frame_id / event_seq / persist_sequence` 与单位逐字返回；游标声明"文件顺序不是时钟"与"不跨流同步"；时间过滤只接受命名时间基，未知基（含浏览器到达顺序）拒绝。Actual（`feedback_initial`/`feedback`）、记录 Target（`actuator_reference`）、命令意图（`requested` 等）与执行反馈分类不合并。
- 完整性分四层表达：记录声明的 `recording_status/audit_status/termination_reason`、`complete_tail` 文件存在性、tail 内声明校验和条目、以及本次读取实际重算/解析的结果。未做全量核验不得声称"全 Episode 已验证完整"；tail 对自身 `episode.json` 的过期自校验按 `mismatch_present` 报告，不改写生命周期状态，也不据此宣布数据损坏。缺流、坏行、缺媒体、未知时钟与不支持格式各自定位（`episode_stream_unavailable`、`integrity.corrupt_lines` 行号、`episode_asset_missing`、`time_base_unsupported`、`episode_asset_type_unsupported`），不静默丢弃、不制造默认帧。`training_qualified=false` 不阻止合格原始读取。
- 3D 回放身份只取记录内 `manifest.json` 的 `model_id/model_sha256/scene_id/map_mode/truth_access/clocks` 与 `transforms.jsonl`；与当前 pin 可比对时标 `identity_verified_rendering_unverified`，无法证明时标 `restricted`。任何情况都不得把当前在线 geometry 或 Actual 自动套到历史 Episode。legacy 记录无平台 sidecar 时 `platform_association.known=false`，不伪造 ValidatedSnapshot/Session 关联。
- 历史 API 不代理 native 的 `POST /episodes/{id}/validate`、assessment/eligibility 写操作、控制、RESET、录制、物理步进或任何重执行；`POST /api/v1/runs/{run_id}/stop` 仍不是机器人 STOP。资产路径拒绝绝对路径与 `..`，解析后必须落在该 Episode 的 `assets/` 子树内，软链越界与摘要不符分别 409。

- 路径受限覆盖索引与读取两侧：run 目录、`episodes` 目录、Episode 目录、run `manifest.json`、episode/tail/sidecar、固定流文件与 `assets/` 的解析结果都必须落在对应边界内；目录级与文件级软链都不允许成为越界通道，缓存索引不得绕过读取时检查；越界分别报告 `history_path_escape`、`episode_path_escape`、`episode_asset_escape`，媒体清单逐文件排除并给出计数。run 目录身份必须在每次构造读取位置时校验：目录本身不得是软链且解析结果仍等于 `root/run_id`，否则沿用 `history_path_escape`（409）——缓存索引只存名字，若索引建立后把 `root/runA` 替换为指向 `root/runB` 的软链，同名 Episode 不得再以 `runA` 身份被读出；拒绝信息不回显软链目标。只做最小公共路径检查，不搭建通用文件系统沙箱。
- `event_seq` 区间过滤必须是合格性判定：区间启用时，缺失、非整数或 bool（bool 是 `int` 子类）序号一律排除并计数，绝不补造序号，也不得用行号替代；合法数据的分页、`next_offset`、原生追加顺序与身份语义不受影响。`observations-index`/`persist` 原生就不带 `event_seq`（后者用 `persist_sequence`），对它们设区间得到空页加计数属正常结果。数值时间边界只接受命名数值时间基，日历字符串基（`wall_utc`）返回 `time_base_not_numeric`。
- 不变性声明的作用域：只有"事前记录摘要、事后复核同一集合"的文件才能称未变，且必须同时列出未覆盖范围；`episode.json`/`episode_complete.json` 的 696 文件聚合作为该集合的标识，不得扩写为整个归档不变。派生文件（如 native 自身 `validate` 重写的 `quality_report.json`）若缺少前置摘要，只报告现状，不声称内容未变、不猜测回滚。

### 图像—机器人状态帧关联切片（M1.5c 首切片，M1.5d/M1.5e 修正；schema `unirobot-mobilecar-frame-link-2`）

- 锚点是 `observations/persist.jsonl` 的一条记录（一个持久图像帧）。关联只能建立在记录里真实存在的键上，角色与键固定：`image_observation`=`sample_id`、`camera_transform`=`sample_id`、`capture_timing_event`=`payload.sample_id`、`state_feedback_event`=`control_tick_id`（等于帧的 `capture_control_tick_id`）、`feedback_observation_row`=观测行自身 `sample_id` 等于帧声明的 `feedback_sample_id`。
- 完整性由角色语义决定，不由候选条数决定：`image_observation` 要求响应中声明的必需 `sensor_kind` 集合（`rgb`、`depth`）**每个恰好一条**；单记录角色（transform、计时事件、状态事件、声明引用行）要求**恰好一条**。因此"两条同为 rgb 且缺 depth"不得返回 `matched`。角色状态为 `matched / partial / missing / unresolved_reference / identity_mismatch / stream_absent / ambiguous_kind / ambiguous_candidates`，含义与判定优先级随响应公开（`status_meaning`、`status_precedence`），诊断字段给出 `required_kinds/matched_kinds/missing_kinds/duplicate_kinds/unexpected_kinds/kind_inventory/candidate_line_indexes/ambiguous_records`。重复候选必须全部列出并标注是否与首个候选冲突，不得无说明地选择文件中的第一条；候选不唯一时不输出单一状态记录（`recorded_state=null`、`single_state_selected=false`）。主角色完整性与声明引用状态保持分开：声明了引用而归档无目标行时返回 `unresolved_reference` 并给出被查找的键值。
- 选样规则固定：不插值、不做状态保持（`carried_over_from_another_frame=false`）、不按时间取最近（数值相近不等于同一记录关系）、不用行号或浏览器到达顺序。每条关联给出可回溯位置 `record_position="<相对路径>#<line_index>"` 与身份核对；声明他人身份的候选被剔除并计数。
- 分页：`has_more` 只由"整页装满之后是否还存在下一条合格锚点"决定，越过锚点文件末尾才表示没有下一页；`next_offset` 保持锚点文件原始行号语义（最后一个已返回锚点的下一行），并另给 `next_qualifying_anchor_line_index`。扫描统计必须区分已读行与未读行（`scan.whole_file_scanned`、`post_page_records_examined`）并逐类计数被跳过的行（`anchor_lines.lines_read/blank_lines_skipped/oversize_lines_skipped/unparseable_lines_skipped/non_object_lines_skipped/prefiltered_lines_skipped`）；坏行与超限行如实表达，不得静默制造末页或声称覆盖整份文件。空页、`sample_id` 过滤与时间窗口过滤各自计数分列。
- 时间：只允许锚点记录上确实存在的时间基（`capture_backend_monotonic_s`/`capture_sim_time_s`/`persist_backend_monotonic_s`），未知基返回 `time_base_unsupported`。差值以 `times.quantities` 逐条给出，每条必须命名其两条来源记录、字段、单位、时钟、符号方向与含义；事件信封 `backend_monotonic_s`（写入时刻）、状态负载 `feedback_time_monotonic`（负载自述采样时刻）、计时负载 `feedback_time_s`（录制器声明）与锚点 `capture_backend_monotonic_s`、观测 `measurement_time_s`/`arrival_time_s`、`persist_backend_monotonic_s`、`sim` 基字段是互不折算的量。`sim` 基差值单列，不得折进 backend monotonic 差值，且**按来源记录再拆两层**（M1.5e/S25/DEC-062）：`state_sim_time_minus_frame_capture_sim_time` 只取状态负载的 `payload.sim_time_s`，`state_event_envelope_sim_time_minus_frame_capture_sim_time` 只取事件信封的 `sim_time_s`，各自命名自己的两条来源记录；负载值缺失或非数值时该负载量缺席，不得用信封值回退填充（此前"取信封值却标为负载来源"的行为是本轮修正对象，修正记入 `version_migration.corrections`），信封值缺失时同理。两个键在 `times.sim_time_quantity_keys` 中列出，缺席即是信息，不得静默合并。`times.recorder_declared` 原样复制录制器自己的时延字段（如 `observation_age_ms`、`capture_to_persist_ms`），并可并列给出读取方重算的 `arrival − capture`；它是管线延迟，不得称为状态采样年龄。旧的单一 `times.age_of_state_relative_to_frame` 已在 `frame-link-2` 中移除，`version_migration` 说明原因、替代键与兼容性（消费方必须读 `schema_version`）。同一时钟基的命名不等于同源：`clock_sameness` 必须分别说明记录命名了什么、读取方能否验证、写入版本可绑定到哪一层（`contract_version`、run 清单 `software` 名/版本、观测 `profile_sha256`；不含 native release/构建/提交），并保持 `verified_by_reader=false`、`synchronized_across_streams=false`、`synchronized_upgraded_by_numeric_closeness=false`。不得把带年龄的状态表述为采集时刻的场景状态。
- 媒体：uri 原样复制自帧记录与观测行，`availability` 取 `present/absent/refused/not_recorded_on_this_frame`；某 kind 有多个候选行时列出全部候选行号、给出 `observation_row_candidates` 与 `observation_rows_conflict`，`agrees_with_observation_row` 表示"存在候选声明了该 uri"。观测行 `metadata.asset_sha256` 作为声明值返回，不宣称已验证；字节仍只由媒体端点在真正服务该文件时重算。像素负载不进入本端点。
- 本切片不得被解释为历史 3D 能力已就绪：`transforms.jsonl` 只提供该帧记录的相机外参与伴随值，响应固定 `this_slice_does_not_enable_3d_replay=true`、`live_geometry_or_actual_may_be_applied=false`、`transforms_are_full_per_body_pose_sequences=false`，并指向姿态准备端点；跨 Episode 游标与统一回放时钟仍未定义。

### 历史机器人姿态与固定模型资源准备（M1.5d 首切片，M1.5e 补证据与分部就绪；schema `unirobot-mobilecar-history-pose-1`）

- 新增两条只读 GET：`GET /api/v1/episodes/{episode_id}/robot-state?run_id=&sample_id=`（schema `unirobot-mobilecar-history-pose-1`）与 `GET /api/v1/episodes/{episode_id}/model/assets/{asset_id}`。历史面由六条扩为八条 GET，仍全部只读、不代理 native 写操作。`sample_id` 缺省时取该 Episode 第一个合格持久帧；帧与状态的关联规则完全复用上一节，不另建一套选样逻辑，也不要求原始数据存在逐 body 矩阵。
- 模型资源固定：只使用运维选定的不可变 compiled geometry bundle，服务前比对 run 清单声明的 `contract_version/model_id/model_sha256/scene_id` 与 bundle `resource_identity`；四项全等才给 `status:"match"`，否则姿态映射视为不适用且资产请求返回 409 `history_model_identity_mismatch`。mesh 字节只从冻结 bundle 出，逐请求重算摘要，ETag 携带摘要，`X-UniRobot-Model-Source: frozen_compiled_geometry_bundle`；摘要不符返回 409 `history_asset_revision_changed`，不在 bundle 内返回 404 `history_model_asset_unavailable`。未配置 bundle 时返回 503 `history_model_bundle_not_configured`。历史端点不得代理当前 `/mobilecar/scene`、snapshot 或当前 Actual，也不得把在线几何或 Actual 套到历史帧上。
- 映射必须逐项可判定：每个目标给出 `recorded_field`、单位、记录长度、映射目标、`status ∈ {verified, partially_verified, unverified, missing, not_required_for_pose}`、`evidence`、`verified_basis`、`no_default_applied=true` 与精确 `gap`。状态由证据判定而非人工声明：`consistent`（运动学复现成立）与 `exercised`（样本确实驱动该轴）同时满足才升到 `verified`，未满足就停留在原名并给出缺口。当前已证实范围：`arm_model_qpos_rad` 五值对应 bundle 的 `joint1…joint5`（名称与数量一致，且逐位顺序由"按名称寻址的源码链 + 冻结模型树内的同一条链 + 同一负载内 TCP 位置复现"共同支持；索引 3 另有记录自身的 model/user 关节对相差 `−π/2` 这一独立凭证）；`base_position_world_sim_m`、`base_quaternion_xyzw` 与 `tcp_position_world_m` 在同一条反馈负载的纯运动学复现下升级为 `verified`，其 `gap` 改为说明该复现的权威来源（平台参考配置而非 native 认证）与不覆盖的语义。仍未证项保持未证且不得补默认值：夹爪宽度到 jaw/drive 关节值的换算（平台配置**已声明** `zero_width_m`、`zero_model_rad`、`width_per_drive_rad_m`、`jaw_origin_correction_m`、`source_gap_m` 与 mimic 常数，缺的是把这些常数绑定到写该记录的历史版本所需的逐帧 jaw 值与指令凭证——此处更正 M1.5d 的"不存在任何规则"表述）、TCP 朝向（记录只有 3 个位置分量，参考配置 `orientation_xyzw=null`、`orientation_status="not_specified_in_source"`，`grasp_tcp` 在 bundle 中是 site 名而非 link）、相机外参标定（仅有 `frame_id=rgbd_optical` 与固定相机链 `depth_cam_link ← camera_connect_link ← link4`，且平台声明相机安装体 `source_topology_not_rigid_to_tcp`）。
- 机械臂顺序的证据链与版本上限分开（`arm_mapping_chain`、`version_binding`）：链本身逐环给出可定位来源——`ARM_JOINTS = tuple(f"joint{i}" for i in range(1, 6))`、`ArmController` 用 `model.joint(name).id` 与 `model.jnt_qposadr` 按名称构造、反馈序列化为 `self.data.qpos[self.arm.qpos[:5]].tolist()`、第 6 个元素是 `GRIPPER_DRIVE` 且被切片排除，因此顺序跟随名称列表而非 XML 文档顺序或原始 qpos 布局；`version_binding` 给出该链在录制时段三个冻结 release 快照（`g2a-20261017T155919Z/160655Z/160903Z`）中的同一位置、快照内 `arm.xml`/`robot.xml` 摘要与记录 `model_sha256` 相等、以及"当前参考源码是工作树提交 `a5cef52`（含未提交改动）"这一事实；结论固定为"该链把写者收窄到同一 release 家族，但不指向单个构建"，并记录 `drvfix-20261019T044549Z` 晚于本归档且 `backend.py` 摘要与当前检出不同、故不是这些记录的写者。记录不带 release/构建/提交身份，`writer_identified=false`，可绑定上限只到 `contract_version`、run 清单 `software` 名/版本与 `model_id/model_sha256/scene_id`。不得为证明顺序而逐轴运动或要求硬件标定，也不得反向编造旧提交或构建身份。
- 模型角与用户角分离（`model_vs_user_angles`）：`render_source` 是把 `arm_model_qpos_rad` 直接按模型弧度施加到 bundle 铰链关节，`conversion_is_required_for_drawing=false`——先转用户角不是绘制的前置门槛。用户角公式 `q_user = (q_model − zero_model_rad) / user_direction` 与反变换只为用户侧显示与限位比较单列给出；`zero_model_rad` 的实际值是精确的 `-1.5707963267948966`（`-π/2`，此前"四舍五入为 -1.5708"的说法是本轮更正之一），其权威是 `zero_status="user_defined_photo_pose_not_hardware_500"` 与 `calibration_session="uncalibrated"`：用户照片零位不称为硬件标定，历史记录值不因该零位被改写。
- 有依据的局部姿态验证走 `tcp_kinematic_cross_check`：用冻结 bundle 的体树（body 偏移后在子 body 系内做关节运动，根 free joint 位姿取记录底盘位姿）计算 `grasp_tcp` site 的世界位置，与**同一条反馈负载**里的 `tcp_position_world_m` 逐轴相减，给出 `hypotheses`（两种根坐标约定：底盘位置即根 body 原点；底盘位置再加根 body 的局部偏移）、`supported_hypotheses`、`consistency_tolerance_m`、`tolerance_authority`（容差由本检查自述，不是标定上限）、`joints_on_chain/movable_joints_on_chain/joints_left_at_zero` 与 `supports`/`does_not_prove`。真实首帧误差 1.6454e-14 m（152/303 帧离线聚合最大 1.6897e-14 m，见交付记录），竞争约定分离 0.0556 m、关节序反转分离 0.20967 m。这只支持运动学一致性，不证明硬件或传感器标定，也不覆盖样本未驱动的轴。
- 就绪条件按部件给出（`part_readiness`，九项能力各一条）：`fixed_model_reference_assembly`、`arm_local_pose`、`base_pose_placement`、`gripper_visual_appearance`、`tcp_position_marker`、`tcp_orientation_frame`、`camera_view_from_record`、`dynamic_scene_objects_from_record`、`wheel_pose_from_record`。每项含 `requires`、`pose_input_required`、`inputs_available`、`frontend_rule`（前端可直接执行的单句规则）、`evidence` 与 `gaps`；状态词汇 `ready / ready_with_caveats / conditional / blocked / not_required` 的含义随 `part_status_meaning` 公开。`capability_summary` 汇总为 `usable_now / usable_only_with_the_named_caveat / blocked` 三档并固定 `fixed_model_assembly_available`、`whole_robot_pose_rebuildable`、`escalation_forbidden`（局部可用永不升级为整车重建、渲染或同步回放）与 `defaults_forbidden`。整车 `pose_readiness=false` 只表示"不作假设就不能整体重建"，不得被解读为冻结模型资源不可装配。
- 只准备有证据的机器人状态渲染资源：动态场景对象（如 `target_cube`）没有历史位姿记录时返回 `missing` 且 `render_from_record=false`，不得推断或摆位。轮速与底盘 twist 标注为姿态渲染不需要且缺少逐轮/分量标识。
- 准备成功与渲染验证分离：响应固定 `rendering.verified=false`、`frontend_assembly_done=false`，`pose_readiness.robot_state_can_be_rebuilt_without_assumptions=false` 并列出 `blocking_fields`；身份匹配、资产摘要与关节长度校验通过都不得表述为历史渲染或同步回放已通过，装配与姿态正确性由后续前端轮次验证。
- 时间语义在姿态端点沿用同一套命名量，`time.clock_sameness` 与 `same_clock_verified=false` 随响应返回；写入版本绑定范围同上，不因数值相近升级同步性。

实现与真实数据证据见 [M1.5a 交付记录](../../backend-m1.5a-history-reader.md)、[M1.5b 整改记录](../../backend-m1.5b-history-readonly-hardening.md)、[M1.5c 帧关联记录](../../backend-m1.5c-frame-linkage.md)、[M1.5d 修正与姿态准备记录](../../backend-m1.5d-frame-reading-and-pose-preparation.md) 与 [M1.5a 证据册](../../evidence/m1.5a-history/README.md)、[M1.5b 证据册](../../evidence/m1.5b-history-readonly-hardening/README.md)、[M1.5c 证据册](../../evidence/m1.5c-frame-linkage/README.md)、[M1.5d 证据册](../../evidence/m1.5d-frame-reading-and-pose/README.md)、[M1.5e 交付记录](../../backend-m1.5e-pose-readiness-and-time-sources.md) 与 [M1.5e 证据册](../../evidence/m1.5e-pose-readiness/README.md)：348 条记录索引与 native 列表一致、COMPLETE 与 FAILED/不完整记录分别读取、平台轻量详情 21 KB 对 native 整条 20.9 MB；946 文件覆盖集合在同一次读取前后一致（其余文件在该时点没有前置摘要，属未覆盖）；真实代表记录 303 个持久帧的 `sample_id` 关联 rgb/depth 每帧各一条、`control_tick_id` 状态关联每帧恰一条候选，而 `feedback_sample_id` 仅 3/303 有对应观测行；首帧实测状态事件写入早于采集 2.885407 ms、状态负载采样戳早于采集 3.669841 ms、录制器声明反馈时间早于采集 3.668296 ms、`sim` 基差值为 0，`observation_age_ms = 33.451169` 与 `arrival − capture` 相等；姿态准备中 run 清单身份与冻结 bundle 四项全等、23 个 mesh 资产逐文件校验、映射目标 10 项中 4 项达 `verified`（机械臂关节顺序、底盘位置、底盘四元数、TCP 位置）、夹爪为 `unverified`、TCP 朝向/相机外参/动态对象为 `missing`。M1.5e 另在候选 `m1x-20261026T065320Z-platform`（`127.0.0.1:18970`）上实测读取检查 110/110、统一回归 28/28、聚焦 45 passed、全量 179 passed / 3 项历史布局失败、64 条请求全为 GET、946 文件 `drift=[]`，离线运动学对照覆盖 152/303 帧且五轴均有位移（joint2/joint3 幅度仅 0.0029/0.0022 rad，故不据此宣称全部轴充分验证）。本节只冻结"受限只读切片与准备契约"；跨流同步游标对齐、标定权威凭证、渲染正确性、前端装配验证与新采集闭环仍未完成。
