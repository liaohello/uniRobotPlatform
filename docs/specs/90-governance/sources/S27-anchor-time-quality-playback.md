# S27｜单 Episode 采集锚点时间质量与播放资格实测（2026-10-29）

## 来源类型

平台后端只读切片的事实来源（M1.5g）。分三类并列：**真实归档实测证据**（同一候选进程上的平台 GET 与只读文件读取）、**冻结身份核对**（release 清单与本地工作树逐文件聚合）、**隔离夹具证据**（`tmp_path` 构造的异常锚点集，不触碰真实归档）。绑定候选 `m1w-20261029T155818Z-platform`（`http://127.0.0.1:18979`，PID 2738345，源码聚合 `707843426524d406…`／49 文件，启动清单 sha256 `064a5bf0192798fa046dd065d0139c461fdef74ebe2f41ce3a5d48a19138573b`）。用户 Goal：完成单 Episode 采集锚点的时间质量与播放资格切片，为记录时间播放提供真实依据，同时保持现有历史读取接口稳定。

## 观察到的事实

### 可读锚点与身份（真实归档）

1. 代表 COMPLETE 记录 `run_0104613ff7364ae78cf2f3946bd45f7b / episode_27bfed5427684795b361cd2ec21e9aa7`：census 扫得 **303 个可读锚点、303 个不同 `sample_id`**；`rejected_anchors = {excluded_identity_mismatch: 0, excluded_stream_mismatch: 0, excluded_without_sample_id: 0}`；`anchor_lines = {lines_read: 303, blank/oversize/unparseable/non_object/prefiltered: 0}`；首锚点 `line_index=0`，末锚点 `line_index=302`；`covers_whole_episode=true`（上限 4000 未触及）。
2. 代表 FAILED 记录 `run_1f6fb34853f94130aadedb8fa486705b / episode_879cf70489064a3b83bb15b5395a8341`：**4 个可读锚点**，同样零缺失、零非数值、零相等、零回退，`covers_whole_episode=true`。该记录的 `FAILED`/不完整终态属另一层（integrity 层）事实，census 不认证录制完整性。

### 时间基、单位与 clock 来源（真实归档）

3. 三个可选时间基在两个记录上都**逐锚点存在且为数值**：`capture_backend_monotonic_s`（unit `s`，clock `backend_monotonic`）、`capture_sim_time_s`（`s`，`sim`）、`persist_backend_monotonic_s`（`s`，`backend_monotonic`）；`missing_count=0`、`non_numeric_count=0` 于三基、两条记录。
4. COMPLETE 记录实测（文件顺序）：capture monotonic 首个 426494.351568496、末个 426554.824271964，间隔 302 段 min 0.10000491904793307 / max 0.31082851998507977 / median 0.200073431013152 / mean 0.20024073996044547 / total 60.47270346805453；sim 首个 0.1400000000000001、末个 60.609999999949444，间隔 min 0.09999999999994458 / max 0.3099999999998282 / median 0.19999999999988916；persist 首个 426494.451593934、末个 426554.935713941，间隔 min **0.04587684402940795**（落盘抖动可小于采集间隔）/ max 0.3509999539819546 / median 0.20132345249294303。
5. 相等与回退计数均为 0，`monotonic_non_decreasing_in_file_order=true`、`file_order_matches_value_order=true`；`recorder_counters.persist_sequence_backwards_steps_in_file_order=0`。因该记录单调，"首个/末个"与"最小/最大"数值相等，但响应把它们作为**不同键**分别给出（夹具中的回退用例证明二者会分叉）。
6. 速率没有被声明也没有被假设：锚点携带 `profile_id="g2a-rgbd-5hz-original"`，`anchor_fields_declaring_a_numeric_rate=[]`；由记录值推得的隐含速率 median 分别是 4.998164898438034 / 5.000000000002771 / 4.96713118922423 Hz，响应内注明"derived from the recorded values … not a rate the recorder declared and not a playback guarantee"；`never_assumed = {default_rate_hz_applied: false, browser_arrival_time_used: false, clock_stitched_across_reset: false}`。
7. 记录未把 segment/RESET 身份挂到锚点上：census 的 `not_proven` 含 "RESET or segment boundaries on anchors"，因此响应不能把跨段值连成一条时钟（实测两条记录各自单调，但这只说明"未见回退"，不说明"无跨段"）。

### 分页与筛选语义（真实 HTTP）

8. 以 `limit=200` 从 `offset=0` 依 `next_offset` 推进：2 页（200 + 103）覆盖 303 锚点，行号序列 `== sorted(set(...))`，首末与 census 一致；末页 `has_more=false`、`next_offset=null`、`post_page_records_examined=0`、`scan.whole_file_scanned=true`。无跳漏、无重复消费。
9. 窗口是筛选而非排序：`time_base=capture_sim_time_s&time_from=0.2&time_to=0.6&limit=2` 实测返回 **1 帧**、`excluded_outside_time_window=302`、`records_missing_selected_time_base=0`，返回帧仍按 `line_index` 升序；同页 `time_quality.coverage.anchors_in_this_scan` 仍是 303（census 覆盖该 Episode 的锚点，不止本页），且 `page_filter_context` 回显窗与分页参数。
10. 带 census 的请求不改变分页/过滤：与不带 census 的同一请求相比，`excluded_*`、`records_missing_selected_time_base`、`next_offset`、`has_more` 计数一致；`time_quality` 是唯一新增顶层键（实测键集合差恰为该单键，其余键除 `retrieved_at` 逐值相等）。census 体积 8,733 B；同一请求 200 帧本体 5,181,012 B；带窗小页 43,841 B。响应头仅 `cache-control: no-store` 等，**无 `ETag`**。
11. census 与页遍历期间发出的请求全部指向平台自身：本轮 `GetProbe` 日志 71 条、methods 仅 `GET`，`live_scene_reads_in_this_run=0`（不含 `/api/v1/scene` 读取）。

### 身份歧义与拒绝（真实 + 夹具）

12. 两条真实记录均无重复 `sample_id`（`duplicate_sample_id_groups=0`）。
13. 隔离夹具（两个锚点共享同一 `sample_id`，位于 `observations/persist.jsonl#0` 与 `#2`）实测：census 列出该组 `occurrences=2`、`line_indexes=[0,2]`、`record_positions=["observations/persist.jsonl#0","observations/persist.jsonl#2"]`；`summary.anchors_with_repeated_sample_id_on_this_page=1`；`frames` 页仍返回全部三个锚点且顺序不变（不去重、不取第一条）。
14. 同一夹具下 `GET …/robot-state?sample_id=<重复 id>` 返回 **409 `frame_sample_id_ambiguous`**，detail 含 `first_matching_anchor_line_index=0`、`next_matching_anchor_line_index=2`、`no_first_match_was_assumed=true`、`state_is_not_taken_from_either_candidate=true`；用未重复的 id 选择仍返回 200。这是**行为收紧**：上一版本会静默取第一条。
15. 夹具异常集实测：缺失（一锚点无 `capture_sim_time_s`）→ `missing_count=1` 且该基 `eligible_for_whole_episode=false`、阻塞含 `time_base_absent_on_1_anchors`，剩余值不被填充（首末同为该唯一值、间隔计数 0）；非数值（字符串）→ `non_numeric_samples=[{line_index:1,value_type:"str"}]`、阻塞含 `non_numeric`；相等 → `equal_adjacent_gaps.count=1`、median 0 → `implied_rate_hz…=null`（不做零除）；回退 → `backwards_gaps.count=1`、该基阻塞 `clock_steps_backwards_1_times_in_file_order`，而 `persist_backend_monotonic_s` 仍 `eligible_for_whole_episode=true`（逐基判定），A 仍合格且锚点顺序未被改写；触顶（limit=1）→ `covers_whole_episode=false`、各基阻塞含 `scan_truncated_at_anchor_limit`。

### 兼容性与执行

16. `unirobot-mobilecar-frame-link-2` 未升版；`schema_version` 与既有键保持不变（census 为可选附加块）。非布尔 `include_time_quality` 值返回 422 `bool_parsing`。
17. 本轮服务器测试：真实读取断言 **130/130**（上一轮 118 → +12）；统一能力回归 **28/28**；冻结 release 内聚焦 **63 passed**；同一棵树全量 **191 passed / 3 项历史布局失败**（`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`，基线不变，不称全绿）；946 文件覆盖集合事前记录、事后复核 `drift=[]`；未启动新 native、未运动、未 RESET、未录制、未 STOP/end、未重启 8792；历史归档/tail/原始媒体/生产 recipe/pin/native 工作树未改；`frontend/` 未修改。
18. 交付前流程：先在运行同一棵 dev 树的 scratch 实例（18978）上跑通 130/130 与夹具测试，再冻结 `m1w-…`（18979，启动前实测端口空闲），未产生半途 release；scratch 进程按命令行身份核对后停止，报告目录保留。

## 对设计的影响

- 播放资格必须**逐时间基**判定，并且必须携带覆盖范围：同一 Episode 内一个基可以合格而另一个不合格（夹具的回退用例即如此），整页合格是假命题。
- 隐含速率是"记录值之差的倒数"，与"录制器声明的速率"是两种事实；契约必须并存展示而不互相冒充，且禁止名义 30Hz、浏览器补时与跨 RESET 连续时钟。
- census 属重量级分析，只有 opt-in 才付得出代价（8.7 KB 对 5.2 MB 的页体）；逐帧请求携带 census 是把一次性分析摊到每帧的错误用法。
- 身份唯一性属于选帧正确性而非显示细节：当 `sample_id` 不唯一时，宁可拒绝并要求调用方消歧，也不把姿态绑到"碰巧先读到的那条"。

## 效力

本来源为"追加顺序播放可用（A）"、"记录间隔调度按逐基、按覆盖范围给出资格与阻塞原因（B）"、"跨流同步仍未证明且不得由 A/B 推导（C）"、"重复锚点 id 的定位影响与明确拒绝"、"census 为可选附加块且 `frame-link-2` 未升版"提供依据。实现与证据见 [M1.5g 交付记录](../../../backend-m1.5g-anchor-time-quality.md) 与 [M1.5g 证据册](../../../evidence/m1.5g-anchor-time-quality/README.md)。
