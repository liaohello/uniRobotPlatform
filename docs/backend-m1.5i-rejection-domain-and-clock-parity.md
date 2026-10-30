# M1.5i｜拒绝回执分域与"时间接近不提升同步"收口

日期：2026-10-30（America/Los_Angeles）· 分支 `codex/backend-m1-services` · 本轮起点 `c79d9d6`（A 段已交付）· 候选 `m1i-20261030T035643Z-platform`
证据册：[docs/evidence/m1.5i-rejection-domain-and-clock-parity/](evidence/m1.5i-rejection-domain-and-clock-parity/README.md) · 治理来源 [S29](specs/90-governance/sources/S29-rejection-domain-and-clock-parity.md) / 决策 DEC-066

## 0. 本轮做了什么（不重复 A）

A 段（不可判定行 → 整 Episode 时间资格）已在 `c79d9d6` 交付：`covers_whole_episode` 与逐基 `eligible_for_whole_episode` 现在要求"到达 EOF""每行被判定""可读锚点时间合格"三件事同真，不可判定行以 `n_lines_are_undecidable_and_could_hide_anchors` 阻塞并给出 `record_position`，空行/预筛行为良性，A 追加顺序仍可用并声明 `displayed_sequence_may_have_gaps`，`scope_note` 已更正为"窗只筛页、普查独立扫描锚点文件"。本轮在**新候选上复验**该结论（真实归档 148/148 中的 coverage 与窗口断言全部通过），不再重复实现，也不把旧计数当作本轮成果。

本轮新增的是 B 段两处未覆盖的收口：

1. **真实记录到的拒绝必须是回执，而不是被执行的动作**。此前只有"归档里没有 `rejected`"的 `not_recorded` 路径被验证；现在补齐"归档确实写了 `rejected`"的路径：它进入 `command_receipt_rejected`（`status=observed`），命令链显示该命令 `requested→rejected` 且**没有** `approved`/`dispatch`，并且**从不进入任何帧关联**——关联类型集合恒为 `actuator_reference`/`dispatch`/`feedback`/`feedback_initial`。
2. **时间数值接近不得提升任何关联或同步声明**。`frame_association.rules.clock_parity` 明写：数值接近甚至**相等**的时间戳都不提升链接，`synchronized_across_streams` 与 `same_clock_verified` 保持 false，只有记录中真实存在的键才建立关联。两个方向的证据：合成夹具把被拒回执的时间戳设为与第二个帧采集时刻**完全相等**且不带 tick → 仍不关联；真实归档实测命令意图/受理的时间戳与某帧采集时间只差 **15.8 ms** → 仍不关联、同步声明仍为 false。

## 1. A 段（复验结论）

| 事实 | 真实 COMPLETE（候选 18985） | 合成夹具（同一档案 + 一行不可解析内容） |
|---|---|---|
| `reached_end_of_file` | true | true |
| `every_line_of_the_anchor_file_is_decided` | true（`undecidable_total=0`，良性行 0/0） | **false**（`unparseable_lines_skipped=1`） |
| `readable_anchor_timing_satisfies_schedule`（逐基） | true | true（可读锚点本身干净） |
| `covers_whole_episode` / `eligible_for_whole_episode` | true | **false**，阻塞原因 `1_lines_are_undecidable_and_could_hide_anchors` |
| A 追加顺序 `eligible` / `displayed_sequence_may_have_gaps` | true / false | **true / true**（诊断 `record_position="observations/persist.jsonl#2"`） |
| 窗口页语义 | 页 1 帧 + 302 条窗外，census 仍 303 锚点、`covers_whole_episode=true` | — |

基线与修正源码的同一夹具对照见 M1.5h 证据册 `m1h_repro_baseline.json` / `m1h_repro_corrected.json`（基线报 `covers_whole_episode=true`，修正后报 false）。迁移说明仍在 `version_migration.corrections/additions`：`frame-link-2` 不升版、无字段改名，但 `covers_whole_episode` 语义收紧、旧理由串 `scan_truncated_at_anchor_limit` 停用为 `scan_stopped_at_anchor_limit_before_eof`。

## 2. B 段：真实支持范围（真实归档，非抽样）

COMPLETE `run_0104613ff7364ae78cf2f3946bd45f7b / episode_27bfed5427684795b361cd2ec21e9aa7`（events 12561 条 12 类）、FAILED `run_1f6fb34853f94130aadedb8fa486705b / episode_879cf70489064a3b83bb15b5395a8341`（224 条 11 类）：

| 分域 | 真实 type | 关联键（present/null 实测） | 与帧的关系 | 状态 |
|---|---|---|---|---|
| Actual | `feedback` 6074/106 | `control_tick_id` 全 present；`command_id` **全 null** | 按 capture tick 关联，每帧恰 1 | observed；**不是**任何命令的执行结果 |
| 记录 Target | `actuator_reference` 6074/106 | `control_tick_id` 全 present，`command_id` null | 可选角色，200 帧页候选 `{"1": 200}` | observed；**不是** Actual |
| 命令意图 | `requested` 20/1 | `command_id` 全 present；`control_tick_id` **全 null** | 不挂帧，独立事件轨 | observed |
| 受理 | `approved` 20/1 | 同上 | 不挂帧 | observed（20 条 `decision.approved=true`） |
| 拒绝 | `rejected` **0/0** | — | — | **`not_recorded_in_this_scan`**（不等于不可能；合成夹具已覆盖"真的写了"的路径） |
| 下发 | `dispatch` 20/1 | 两键均 present | 可选角色；实测仅 1/303 命中自身 tick，`{"0": 199, "1": 1}`，缺失不借用 | observed |
| 执行结果 | 无该 type；`feedback` 不携 `command_id` | — | — | **not_recorded**；不得把审批/下发读成执行成功 |
| 控制来源／接管 | 无 `takeover`/`control_source_change` 类型；来源只在 payload | `payload.operator_id`/`operator_kind`/`view_source`/`session_id`/`owner_session_id` | 不挂帧 | `recorded_only_inside_payload_fields`；**不默认 Human** |
| 租约 | `lease_heartbeat` 45/0、`lease_expired` 1/1 | `session_id`/`owner_session_id`/`channel` | 不挂帧 | observed，单列 |
| 生命周期 | `recording_start`/`recording_stop`/`episode_terminal` 各 1 | tick、command 均 null；`episode_terminal` 的两个数值时钟为 **null** | 不挂帧 | observed；终态声明不进数值时间基 |
| 采集计时 | `rgbd_capture_timing` 303/4 | `payload.sample_id`、`feedback_sample_id`、`capture_control_tick_id` | 既有角色 | observed |

单位取自记录自身字段名后缀（`*_s`→second、`*_ms`→millisecond、`wall_utc`→iso8601_utc）；`payload.wheel_target_rad_s` 按名推得 rad/s 故不列为时间字段；无后缀字段 `unknown_from_field_name`。

**时间接近不提升（本轮新增的实测）**：`requested`/`approved` 的 `backend_monotonic_s` 与 `observations-persist` 第 7 行锚点的 `capture_backend_monotonic_s` 只差 **0.015817145991604775 s**；两个时间戳都没有进入任何帧关联，`same_clock_verified=false`、`synchronized_across_streams=false`、`verified_by_reader=false`，`clock_parity` 规则逐字写明不得升级。合成侧更极端：时间戳**完全相等**且无 tick → 仍不关联。

## 3. 前端交接

1. **现存可调用请求**（八条 GET 不变；语义块均为 opt-in）：

```
GET /api/v1/episodes/{episode_id}/frames?run_id={run_id}&limit=1&include_time_quality=true
GET /api/v1/episodes/{episode_id}/frames?run_id={run_id}&limit=1&time_base=capture_sim_time_s&time_from=0.2&time_to=0.6&include_time_quality=true
GET /api/v1/episodes/{episode_id}/frames?run_id={run_id}&limit=200&include_action_basis=true
GET /api/v1/episodes/{episode_id}/streams/events/records?run_id={run_id}&limit=5&event_seq_from=332&event_seq_to=334
```

实际载荷见证据册 `action-basis-complete.json`、`rejected-category.json`、`events-records-command-window-real.json`、`proximity-command-to-anchor.json`。

**兼容性范围（不是"加字段"就算完）**：本轮只在 **opt-in** 块 `action_basis.frame_association.rules` 内新增两个说明键（`clock_parity`、`recorded_target`），并让"归档确实写了 `rejected`"的情形返回 `status=observed` 而不是 `not_recorded_in_this_scan`——后者是**取值变化**，不是新增字段。没有任何字段被删除或改名，`schema_version`（`unirobot-mobilecar-frame-link-2`）与默认帧页逐键均不变，八条 GET 不变，因此**不需要版本迁移**；但两条消费约束必须遵守：①不得把 `rules` 当作封闭键集（新增键是允许的，未知键应忽略而非报错）；②不得把 `categories.*.status` 缓存为永久值——同一类别在不同 Episode 上可在 `observed` 与 `not_recorded_in_this_scan` 之间变化，跨 Episode 复用须按响应重判。A 段（`covers_whole_episode` 语义收紧与旧理由串停用）的迁移说明仍以 M1.5h/DEC-065 与 `version_migration.corrections/additions` 为准。

2. **可精确关联帧的事件**：只有真实携带 `control_tick_id` 且等于帧锚点 `capture_control_tick_id` 的 `feedback`/`feedback_initial`（Actual）与 `actuator_reference`（Target）——以及**有时**的 `dispatch`（实测 1/303）；`rgbd_capture_timing` 按 `payload.sample_id` 关联。
3. **只能独立浏览**：`requested`、`approved`、`rejected`、`lease_heartbeat`、`lease_expired`、`recording_start`、`recording_stop`、`episode_terminal`（按 `event_seq` 或命名时间基定位）。**根本未记录**：`rejected`（本条归档）、任何"执行完成/失败"回执、`takeover`/控制源切换事件、按 Episode 的必需流声明。
4. **错误／歧义／缺失状态**：`matched` / `missing` / `ambiguous_candidates`（全部候选列出）/ `stream_absent` / `unresolved_reference`；类别层 `observed` / `not_recorded_in_this_scan`；`sample_id` 命中多个锚点时 `robot-state?sample_id=` 返回 409 `frame_sample_id_ambiguous`。
5. **对"状态、动作及声明必需流可重载"的验收差距**：状态与动作的读取/关联依据已按记录给出；**必需流仍 `unknown`**——真实 Episode 与 run 清单都没有按 Episode 声明的必需流集合（平台侧 `declared_streams` 只核对在线能力通告），故只引用已有声明、无声明即 unknown，不编造训练数据要求、不补零动作。统一历史游标、倍速、区间循环与对齐误差阈值仍未定义。

## 4. 验证与候选身份

候选 `m1i-20261030T035643Z-platform`：**`http://127.0.0.1:18985`**，PID 1659550，独立 SQLite `frames-20261030T035643Z.sqlite3`，启动前 `ss -ltn` 实测空闲，核活 `GET /api/v1/episodes?limit=1`=200。

- 真实归档读取检查 **148/148**（M1.5h 的 146 → 本轮 +2：时间接近不提升、拒绝回执分域）；
- 统一候选能力回归 **28/28**；冻结树聚焦 **71 passed**；冻结树全量 **205 passed / 3 failed**，三项历史布局失败按名保留（`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`），不称全绿；
- 隔离夹具新增 2 项：`test_a_recorded_rejection_is_a_receipt_and_never_an_executed_action`、`test_an_equal_stamp_without_a_shared_key_never_creates_a_link_or_a_sync_claim`；连同既有用例覆盖坏行、超限、缺时、非数值、回退、重复 ID、事件缺失、多候选、截断；
- 身份：树聚合 `107f897ddfe2485f…`／50 文件与启动清单 MATCH，清单内 `frames.py`=`9ae98b126e42760a…` 与运行目录全等，启动清单 sha256 `7338d2779ecf55fb…`；
- 边界：77 条请求全为 GET、`live_scene_reads=0`、946 文件 `drift=[]`；18977/18979/18983 常驻未替换；只改 `backend/` 与 `docs/`。

## 5. 剩余正式 M1 门槛

状态/动作：读取、分域、精确关联、缺失与歧义已有可复现依据。仍然缺：按 Episode 的必需流声明（→ `unknown`）；真实归档中的拒绝/执行回执与控制源切换样本（→ `not_recorded`，不得推定）；统一历史游标与跨流同步（→ 未证明）；回放执行本身（倍速、区间循环、逐帧步进、误差阈值）。本 Goal 不代表生产部署、跨流同步或 M1 验收通过。
