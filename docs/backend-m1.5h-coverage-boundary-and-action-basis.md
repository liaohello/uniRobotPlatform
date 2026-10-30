# M1.5h｜时间资格覆盖边界修正与历史动作／事件读取依据

日期：2026-10-30（America/Los_Angeles）· 分支 `codex/backend-m1-services` · 基线 `a10b96b` · 候选 `m1h-20261030T002258Z-platform`
证据册：[docs/evidence/m1.5h-coverage-and-action-basis/](evidence/m1.5h-coverage-and-action-basis/README.md) · 治理来源 [S28](specs/90-governance/sources/S28-coverage-boundary-and-action-basis.md) / 决策 DEC-065

## 0. 一句话结论

覆盖边界收紧后，"这条 Episode 可以按记录时间调度"必须由普查自己证明——扫描到达文件末尾**且**每一行都被判定**且**可读锚点的时间满足条件，三者缺一不可；不可判定的行可能藏着锚点，排除它不等于解释它。同时，真实归档里动作／事件的种类、原始位置、时间字段、单位与关联键已逐项实测并作为 opt-in 摘要交付：Actual、记录 Target、命令意图、受理、下发、生命周期各自分类，`rejected` 与"执行完成"回执在这两条记录中不存在就写 `not_recorded`，不补零、不默认 Human、不把审批当执行。

## 1. 交付概览

| 项 | 结果 | 实测依据 |
|---|---|---|
| **A 追加顺序浏览** | 继续可用，且与"序列是否完整"分开表达 | 真实记录 `append_order_display.eligible=true`、`displayed_sequence_may_have_gaps=false`；隔离夹具含不可解析行时 A 仍合格、`displayed_sequence_may_have_gaps=true` 并给出该行位置 |
| **整 Episode 记录时间资格** | 由三个独立事实共同决定，不可判定的行会否决整集结论 | 基线同一夹具 `covers_whole_episode=true`/`any_base=true`/逐基 `blocking_reasons=[]`（缺陷复现）；修正后 `reached_end_of_file=true`、`every_line_of_the_anchor_file_is_decided=false`、`covers_whole_episode=false`、逐基 `1_lines_are_undecidable_and_could_hide_anchors` |
| **真实干净记录未被误伤** | 303 锚点、`undecidable_total=0`、两类良性行为 0，整集资格仍为真 | census 实测（候选 18983） |
| **窗口范围表述修正** | 时间窗只筛帧页，census 独立扫描锚点文件 | 真实请求：页返回 1 帧、`excluded_outside_time_window=302`，同一响应 census 仍 `anchors_in_this_scan=303`、`covers_whole_episode=true` |
| **动作／事件读取依据** | 现有 records 分页 + event_seq／命名时间过滤继续是读取面；语义元数据、逐帧关联与未记录类别以 opt-in `action_basis` 交付 | COMPLETE events 全量 12561 条 12 类、FAILED 224 条 11 类，逐类位置/时间字段/单位/键实测 |
| **跨流同步** | 仍未证明，且不由 A/B 推导 | `cross_stream_synchronized.eligible=false`、`not_derivable_from=["A","B"]` |

## 2. A：覆盖边界的三个事实

`time_quality.coverage` 现在分别表达（`playback_eligibility.recorded_interval_schedule.eligible_by_base.<base>` 同步给出同名三问）：

- `reached_end_of_file`：扫描是否读到文件末尾（触顶 `anchor_limit=4000` 即为 false，`stopped_at_line_index` 给出停下的行）；
- `line_accounting`：逐行是否被**判定**。`blank_lines_skipped` 与 `prefiltered_lines_skipped` 归为 `benign`（空行不含记录；原文不含该流 token 的行不可能是该流锚点——这是读取方自己的、可复核的规则）；`oversize_lines_skipped`、`unparseable_lines_skipped`、`non_object_lines_skipped` 归为 `undecidable`（内容从未被解析，无法排除它就是那条锚点），并给出 `undecidable_positions[]` 的 `line_index` 与 `record_position="observations/persist.jsonl#<n>"`。解析成功但被规则剔除的锚点计入 `parsed_records_rejected_by_rule`——它们是"已见的锚点被规则排除"，与"无法判断的行"不同类；
- `readable_anchor_timing_satisfies_schedule`：可读锚点自身的时间是否满足调度（逐基的缺失/非数值/回退），与上面两问分列在 `blocking_reason_scope.coverage` 与 `.timing`。

`covers_whole_episode` = 到达 EOF **且** 每行都被判定；`eligible_for_whole_episode` = 上述成立且该基时间合格。因此"其余锚点很干净"不再能替不可判定的内容背书。A 不受影响仍可按追加顺序浏览，但会声明 `displayed_sequence_may_have_gaps` 并保留定位诊断。

**行为影响与迁移**：`unirobot-mobilecar-frame-link-2` 不升版（无字段删除或改名；默认帧页逐键不变，实测键集合差恰为可选块），但 `covers_whole_episode`/`eligible_for_whole_episode` 的含义**收紧**，已写入 `version_migration.corrections`（记明旧行为"只看 EOF 即宣称整集"是本轮修正对象）与 `version_migration.additions`。旧可选参数名 `scan_truncated_at_anchor_limit` 由 `scan_stopped_at_anchor_limit_before_eof` 取代——这是 census 内可选块的理由串变更，消费方应读 `blocking_reason_scope` 而不是匹配旧串。真实 COMPLETE/FAILED 两条记录都是 `undecidable_total=0`，其资格结论未变（这本身就是回归保护）。

**实测（真实 COMPLETE，候选 18983）**：`lines_read=303`、`anchors_in_this_scan=303`、`unique_sample_ids=303`、`rejected_anchors` 三类均 0、`benign={blank:0, prefiltered:0}`、`undecidable={oversize:0, unparseable:0, non_object:0}`、`covers_whole_episode=true`、三基 `eligible_for_whole_episode=true`。

## 3. B：真实动作／事件读取依据（全量有界扫描，非抽样）

COMPLETE `run_0104613ff7364ae78cf2f3946bd45f7b / episode_27bfed5427684795b361cd2ec21e9aa7`（events 12561 条，63 页遍历到 EOF）与 FAILED `run_1f6fb34853f94130aadedb8fa486705b / episode_879cf70489064a3b83bb15b5395a8341`（224 条，2 页）实测：

| 类别 | 真实 type | 条数 C/F | 原始位置（首/末，events.jsonl#） | 关联键（present/null 实测） | 帧关联 |
|---|---|---|---|---|---|
| Actual 状态 | `feedback` | 6074 / 106 | 3 / 12555 | `control_tick_id` 6074/0；`command_id` **0/6074 全 null** | 由 capture tick 关联，每帧恰 1 条（既有 `state_feedback_event` 角色） |
| 记录 Target | `actuator_reference` | 6074 / 106 | 2 / 12554 | `control_tick_id` 6074/0；`command_id` 全 null | **本轮新增可选角色** `recorded_target_event`；200 帧页实测候选分布 `{"1": 200}` |
| 命令意图 | `requested` | 20 / 1 | 331 / 12556 | `command_id` 20/0；`control_tick_id` **0/20（全 null）** | 独立事件轨（只按 `command_id` 串链，不挂帧） |
| 受理回执 | `approved` | 20 / 1 | 332 / 12557 | 同上，tick 全 null | 独立事件轨；20 条 `decision.approved` 全为 true |
| 拒绝回执 | `rejected` | **0 / 0 → `not_recorded`** | — | — | 缺失如实声明，并说明"本扫描未发现"不等于"录制器永远不会写" |
| 下发 | `dispatch` | 20 / 1 | 333 / 12558 | `command_id` 20/0 且 `control_tick_id` 20/0 | 可选角色 `command_dispatch_event`；实测 200 帧页 `{"0": 199, "1": 1}` → 多数帧无下发记录，**不从相邻 tick 借用** |
| 执行结果 | 无该 type | — | — | — | `feedback` 的 `command_id` 全 null，故**不能**把某条 feedback 断言为某命令的执行结果；`not_proven` 明确列出 |
| 控制来源／接管 | 无 `takeover`/`control_source_change` type；来源只出现在 payload 内 | — | — | `payload.request.operator_id`/`operator_kind`、`payload.command.operator_id`、`payload.operator_id`、`payload.owner_session_id`、`payload.session_id` | `control_source.status="recorded_only_inside_payload_fields"`、`takeover_event_type_recorded=false`；`lease_heartbeat` 45/0、`lease_expired` 1/1 单列 |
| 生命周期 | `recording_start`/`recording_stop`/`episode_terminal` | 1/1/1 · 1/1/1 | 0 / 12559 / 12560 | tick 与 command 均 null；`episode_terminal` 的 `backend_monotonic_s`、`sim_time_s` **为 null**，只有 `wall_utc` | 独立事件轨；终态声明不进任何数值时间基，不得伪造时刻 |
| 采集计时 | `rgbd_capture_timing` | 303 / 4 | 40 / 12547 | `payload.sample_id`、`payload.feedback_sample_id`、`capture_control_tick_id` | 既有 `capture_timing_event` 角色 |

单位取自记录自身字段名：`wall_utc`→iso8601_utc、`*_s`→second、`*_ms`→millisecond；`payload.wheel_target_rad_s` 虽以 `_s` 结尾但按名推得 rad/s，**不**列为时间字段；`payload.feedback_time_monotonic`、`base_twist` 等无单位后缀的字段一律 `unknown_from_field_name`。

**调用缺口与最小扩展**：要回答"这条 Episode 有哪些事件类别、各自能和帧按什么键关联"，前端原本必须遍历 63 页 12561 条记录并自行分辨 `null` 与"存在"。因此沿用 M1.5g 的 opt-in 模式，在**同一** `frames` 路由上新增可选布尔 `include_action_basis`（默认 `false`），返回一个 `action_basis` 块：`scope`（扫描条数、是否到 EOF、`record_limit=20000`）、`categories`（上表十类，含 `not_recorded_in_this_scan` 与 `absent_event_types`）、`vocabulary`（逐 type 计数、首末行号、有界位置、逐键 present/null、时间字段与单位）、`frame_association`（本页每帧 tick 的候选计数、全部候选位置、`matched/missing/ambiguous_candidates` 与规则）、`command_chain`（按 `command_id` 分组，不推执行结果）、`control_source`、`independent_tracks`、`rules`、`not_proven`。默认帧页逐键不变；历史只读面仍是八条 GET；未新增端点、通用查询框架、服务端播放 Session 或时钟对齐系统。

代价如实声明：`action_basis` 需要整趟 events 扫描，200 帧页上实测约 148 KB（默认页约 39 KB、census 约 12 KB）。它属于"每 Episode 一次"的建轨信息，不应逐帧携带；逐帧只需 tick 相等判断的场合用 `limit` 小页取。

## 4. 前端可直接复现的请求

```
GET /api/v1/episodes/{episode_id}/frames?run_id={run_id}&limit=1&include_time_quality=true
GET /api/v1/episodes/{episode_id}/frames?run_id={run_id}&limit=1&time_base=capture_sim_time_s&time_from=0.2&time_to=0.6&include_time_quality=true
    # 页 1 帧 + 302 条窗外，census 仍 303 锚点、covers_whole_episode=true（窗不缩普查）
GET /api/v1/episodes/{episode_id}/frames?run_id={run_id}&limit=200&include_action_basis=true
    # 首次建轨：类别词表 + 逐帧候选 + 未记录类别
GET /api/v1/episodes/{episode_id}/streams/events/records?run_id={run_id}&limit=5&event_seq_from=332&event_seq_to=336
    # 事件轨本身：仍是既有分页 + event_seq／命名时间过滤，返回原始记录与 line_index
```

消费规则：①画帧轨用 `frames.linkage` 的既有角色；Target／dispatch 用 `action_basis.frame_association.by_event_type`，`ambiguous_candidates` 时展示全部候选、`missing` 时留空**不得**沿用上一 tick；②命令链按 `command_chain` 的 `command_id` 分组独立成轨，`requested`/`approved` 不得投影到任何帧；③`recording_stop`/`episode_terminal`/`lease_*` 走 `independent_tracks`，按 `event_seq` 或命名时间基定位，不按"时间最近"归属；④`status=not_recorded_in_this_scan` 只说明本次扫描未发现该类别；⑤`action_basis.scope.reached_end_of_file=false` 时不得宣称词表覆盖整条 Episode；⑥整集播放资格只看 `coverage.reached_end_of_file` + `line_accounting.every_line_of_the_anchor_file_is_decided` + 逐基 `readable_anchor_timing_satisfies_schedule`，与页面是否有时间窗无关；⑦A 与 B 成立都不推出跨流同步。

M1 的"重新加载状态／动作／所声明必需流"剩余差距：状态与动作的读取与关联依据已按记录给出；**所声明必需流仍为 unknown**——真实 Episode 与 run 清单都不含按 Episode 的必需流声明（平台侧 `declared_streams` 检查只核对在线能力通告，见 `backend/src/unirobot/mobilecar.py` 的 `checks advertised stream support only`），因此只引用已有声明、无声明即 unknown，不自行编造要求；缺流／不完整可见性与只读不控制已由现有面支撑；统一历史游标、倍速与对齐误差阈值仍未定义。

## 5. 服务器验证（全部在授权服务器执行）

候选 `m1h-20261030T002258Z-platform`：**`http://127.0.0.1:18983`**，PID 3745241，独立 SQLite `frames-20261030T002258Z.sqlite3`，端口启动前 `ss -ltn` 实测空闲，核活方式 `GET /api/v1/episodes?limit=1` → 200（本服务未注册 `/health`）。源码树聚合摘要 `68f481b38843d2bc…`／50 文件与启动清单逐字节 **MATCH**，清单内 `src/unirobot/frames.py` = `f4b4187fc5b4e0cf…` 与运行目录同文件全等——覆盖摘要、冻结源码与实际进程为同一候选。

- 真实归档读取检查 **146/146**（M1.5g 的 130 → 本轮新增 16 项，覆盖 A 的三事实、计数分类规则、A 与序列完整性、窗口范围语义，以及 B 的 opt-in 隔离、词表合计等于声明条数、类别分离、未记录声明、null 键不当关联键、逐帧候选、命令链、单位、控制来源、独立轨、FAILED 记录同法测量）；
- 统一候选能力回归 **28/28**；
- 冻结树聚焦 **69 passed**（`tests/test_frames.py` + `tests/test_episodes.py`）；冻结树全量 **203 passed / 3 failed**，三项历史布局失败按名保留：`tests/test_catalog.py::test_catalog_loads_real_tasks`、`tests/test_catalog.py::test_every_task_has_existing_evidence`、`tests/test_migrate.py::test_manifest_sources_exist`（与基线同因，本轮未无关扩修、不称全绿）；
- 隔离夹具新增 9 个用例：不可解析／超限／非对象行分别否决整集结论、空行与"确认无关"行不否决、窗口页不缩普查、`action_basis` opt-in 与默认页不变、词表与 present/null 键、逐帧候选与重复候选歧义、命令链不推执行、控制来源不默认、扫描触顶自报、无 events 流时逐项 `missing`；
- 缺陷复现证据：同一夹具分别以 `a10b96b` 冻结源码与本候选源码直读，基线 `covers_whole_episode=true`/`any_base=true`/逐基空阻塞，修正后逐基给出 `1_lines_are_undecidable_and_could_hide_anchors`（`m1h_repro_baseline.json` / `m1h_repro_corrected.json`）；
- 边界保持：75 条 GetProbe 记录全为 GET、`live_scene_reads=0`、946 个归档文件 `drift=[]`（未修改归档／tail／原始媒体）；18977（M1.5f）与 18979（M1.5g）常驻未替换，其他既有预览保留。

## 6. 不主张

本轮不主张：跨流同步、统一历史游标、采样同刻、录制器声明的数值速率、全归档覆盖、任何命令已被物理执行、`rejected`／执行回执不存在即不可能、按 Episode 的必需流集合、倍速与误差阈值、生产部署、正式 M1.5 或 M1 验收通过。
