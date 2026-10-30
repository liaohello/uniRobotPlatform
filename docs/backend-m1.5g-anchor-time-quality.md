# M1.5g｜单 Episode 采集锚点的时间质量与播放资格切片（2026-10-29）

基线 `a64b522`（M1.5f），分支 `codex/backend-m1-services`。本轮只做一件事：把"采集锚点的时间到底能支撑哪种播放"变成**可实测、可复现、由后端定义字段**的契约，同时保持现有历史读取接口稳定。不扩展夹爪标定、相机外参、点云、训练或导航执行。

## 三个独立结论（不合并）

| 结论 | 判定 | 依据 |
|---|---|---|
| **追加顺序播放（A）可用** | 成立 | 真实 COMPLETE 记录 303 个锚点经 2 页（200+103）真实 HTTP 遍历：行号严格递增、无跳漏、无重复消费，末页 `has_more=false`、`next_offset=null`、`whole_file_scanned=true` |
| **记录时间播放（B）是否有资格** | 在实测范围内**有资格**，逐时间基判定 | 代表 COMPLETE 记录三个采集时间基各自 303/303 数值、0 缺失、0 非数值、0 回退、0 相等相邻、`covers_whole_episode=true`、`blocking_reasons=[]`；代表 FAILED 记录 4 个锚点同样干净（但其记录本身仍是 `FAILED`/不完整终态，见"边界"） |
| **跨流同步（C）** | **仍未证明** | `cross_stream_synchronized.eligible=false`、`not_derivable_from=["A","B"]`、同页 `same_clock_verified=false`；契约只允许"记录命名了同一时钟基"，不把它写成同源或同刻 |

## 前端联调基址

`http://127.0.0.1:18979`（候选 `m1w-20261029T155818Z-platform`，PID 2738345，独立 SQLite `frames-20261029T155818Z.sqlite3`，端口启动前实测空闲）。**M1.5f 的 18977 未被替换**，18970/18969/18966/18964/18960/18959/18953/18949/18944 与 8792 全部保留；本轮实测后端在监听号段见 [handoff](handoff.md)。核活方式：`GET /api/v1/episodes?limit=1`（本服务未注册 `/health`，404 不代表不可用）。

```text
GET /api/v1/episodes/{episode_id}/frames?run_id={run_id}                          # 默认帧页：不含 census（与上一轮逐键相同）
GET /api/v1/episodes/{episode_id}/frames?run_id={run_id}&include_time_quality=true # 新增可选有界 census
GET /api/v1/episodes/{episode_id}/robot-state?run_id={run_id}&sample_id={id}       # 重复 id 现在明确拒绝
```

Episode 只读面仍是**八条 GET**：本轮没有新增端点、没有通用查询框架、没有服务端播放 Session；只在既有 `frames` 路由上加一个可选布尔参数（默认 `false`，非布尔 422 `bool_parsing`），并给 `robot-state` 增加一条拒绝码。

## 1. 实测锚点时间质量（真实归档，只读）

代表 COMPLETE 记录 `run_0104613ff7364ae78cf2f3946bd45f7b / episode_27bfed5427684795b361cd2ec21e9aa7`：

| 项 | 实测 |
|---|---|
| 可读锚点 / 有效身份 | 303 个锚点，`unique_sample_ids=303`；`rejected_anchors` 三类各 0；读取行 303，空行/超限/坏行/非对象全 0 |
| 原始位置范围 | 首锚点 `line_index=0`，末锚点 `line_index=302`（文件顺序即追加顺序） |
| `capture_backend_monotonic_s`（unit s，clock `backend_monotonic`） | 首个 426494.351568496，末个 426554.824271964；min/max 与之相等（因本记录单调）；间隔 302 段：min 0.10000491904793307 / max 0.31082851998507977 / median 0.200073431013152 / mean 0.20024073996044547 / total 60.47270346805453 |
| `capture_sim_time_s`（clock `sim`） | 首个 0.1400000000000001，末个 60.609999999949444；间隔 min 0.09999999999994458 / max 0.3099999999998282 / median 0.19999999999988916 |
| `persist_backend_monotonic_s` | 首个 426494.451593934，末个 426554.935713941；间隔 min **0.04587684402940795**（落盘抖动小于采集间隔，如实呈现）/ max 0.3509999539819546 / median 0.20132345249294303 |
| 缺失 / 非数值 / 相等 / 回退 | 三个基各自 `missing_count=0`、`non_numeric_count=0`、`equal_adjacent_gaps=0`、`backwards_gaps=0` |
| sample_id 重复 | 0 组（该记录无重复）；若有，census 会列出每组的 `line_indexes` 与 `record_positions="observations/persist.jsonl#<n>"` |
| 首末 vs 最小最大 | 两者分别报告；本记录因单调而数值相等，契约禁止把"首个/末个"当作"最小/最大"（夹具中回退用例证明二者会分开） |
| 文件顺序 vs 时间顺序 | `file_order_matches_value_order=true`、`monotonic_non_decreasing_in_file_order=true`；读取面**不做任何自动排序** |
| 声明速率 | 锚点只有 `profile_id="g2a-rgbd-5hz-original"`，`anchor_fields_declaring_a_numeric_rate=[]`；由记录值推得 median 隐含速率 4.998164898438034 / 5.000000000002771 / 4.96713118922423 Hz，并明确标注"不是录制器声明的速率、不是播放保证" |

代表 FAILED 记录 `run_1f6fb34853f94130aadedb8fa486705b / episode_879cf70489064a3b83bb15b5395a8341`：4 个可读锚点，三基各 4/4 数值、0 缺失、0 非数值、0 相等、0 回退，`covers_whole_episode=true`，A 合格、逐基 B 合格、C 仍不合格。

**覆盖范围声明**：census 扫描该 Episode 的锚点文件全体（上限 4000，触顶时 `covers_whole_episode=false` 并把 `scan_truncated_at_anchor_limit` 列入阻塞原因）；它不是全归档扫描（本 Goal 未做、也不作为前置），且带时间窗的页仍会返回同一份 Episode 级 census（窗只筛页，不改 census）。

## 2. 冻结的最小播放语义（写入主责契约）

- **A 追加顺序逐帧展示**：锚点文件的自身顺序 + 现有分页规则；不要求时间基数值、不要求时钟同源、不要求 id 唯一。合格条件即"该 Episode 有可读锚点"。
- **B 按同一采集时间基的记录间隔调度**：**逐基判定**，且必须满足：本次扫描覆盖完整（未触顶）、该基在每个锚点上存在且为数值、按文件顺序不回退。异常规则：缺时/非数值 → 该基拒绝用于调度，帧仍按 A 显示且不补值；相等相邻 → 按并列呈现，不插值、不用零间隔除出速率；回退 → 该区间拒绝调度，因为记录本身不能证明一条连续时钟；时钟只被命名 → 不作为同源证据。A/B 成立也**不得**推出 C。
- **C 跨流同步**：本切片一律 `eligible=false`，理由随响应给出。
- 明确禁止：默认 30Hz（或任何名义速率）、按浏览器到达时间补时、跨 RESET 把多个段落连成一条时钟、通过自动排序改写锚点原始位置或关联身份。
- 具体调用缺口（如实登记，未预先建系统）：真实归档目前无重复 id，故未新增"按锚点位置选帧"的参数；若将来出现重复 id 需要精确定位，最小扩展是在 `robot-state` 增加按 `anchor_line_index` 选帧，而不是让调用方靠顺序猜。

## 3. census 字段（后端命名，写入契约）

`time_quality`（8 个键）：`requested`、`coverage`（含 `anchors_in_this_scan/unique_sample_ids/rejected_anchors/anchor_lines/first_anchor_line_index/last_anchor_line_index/whole_anchor_file_scanned/anchor_limit/stopped_at_line_index/covers_whole_episode/not_a_whole_archive_sweep/scope_note/page_filter_context`）、`time_bases`（逐基 `field/unit/clock/source_record/numeric_count/missing_count(+行号)/non_numeric_count(+值类型)/first_in_file_order/last_in_file_order/min_recorded_value/max_recorded_value/first_minus_last_s/recorded_gaps{count,min_s,max_s,median_s,mean_s,total_s}/equal_adjacent_gaps{count,line_index_pairs}/backwards_gaps{count,steps}/monotonic_non_decreasing_in_file_order/file_order_matches_value_order/description`）、`identity`（`duplicate_sample_id_groups/duplicates[]（sample_id/occurrences/line_indexes/record_positions）/every_anchor_position_is_reported/effect_on_this_route/effect_on_robot_state`）、`recorder_counters`、`profile`、`playback_eligibility`（三模式 + `rules_when_unqualified` + `never_assumed` + 逐基 `eligible_for_whole_episode/eligible_within_this_scan/blocking_reasons/zero_interval_ties_present/implied_rate_hz_from_median_recorded_gap/implied_rate_note`）、`not_proven`。
页级新增 `summary.anchors_with_repeated_sample_id_on_this_page`。census 体积 8,733 B，同页 200 帧本体 5,181,012 B → census 只应一次取，不逐帧携带。

## 4. 兼容性与错误码

- `unirobot-mobilecar-frame-link-2` **不升版**：默认响应逐键与上一轮相同，请求 census 时只多 `time_quality` 一个顶层键（实测键集合差恰为该键，其余键逐值相等，除 `retrieved_at`）。
- 新增可选参数 `include_time_quality`（默认 `false`）；非法布尔沿用 FastAPI 422 `bool_parsing`。
- **行为收紧（不是纯兼容新增，如实声明）**：`GET /api/v1/episodes/{id}/robot-state?sample_id=` 此前在该 id 命中多个锚点时会静默取第一条，现返回 **409 `frame_sample_id_ambiguous`**，detail 含 `first_matching_anchor_line_index`、`next_matching_anchor_line_index`、`no_first_match_was_assumed=true`、`state_is_not_taken_from_either_candidate=true` 与 `how_to_inspect`。schema 版本号不变（无字段删除或改名），但调用方若曾依赖"总能拿到一条"需按该码分支处理；迁移方式：改用唯一 `sample_id`，或按 census 列出的位置消歧，且不以任何"时间最近/文件第一条"替代。
- census 与分页/过滤共用同一身份与流判定规则，因此不改变 `excluded_*`、`records_missing_selected_time_base`、`next_offset`、`has_more` 的语义（实测：带 census 的窗口页与不带 census 时计数一致）。

## 5. 可复现的播放检查（真实 HTTP）

- 遍历：`limit=200` 从 `offset=0` 按 `next_offset` 推进直至 `has_more=false`，2 页 303 锚点，行号序列 `== sorted(set(...))`，首末等于 census 首末，末页 `next_offset=null`、`post_page_records_examined=0`、`whole_file_scanned=true`。
- 筛选语义不变：`time_base=capture_sim_time_s&time_from=0.2&time_to=0.6` 实测返回 1 帧、`excluded_outside_time_window=302`、`records_missing_selected_time_base=0`（窗是筛选不是排序，页仍按文件顺序）；`sample_id=` 过滤计数分列。
- 独立于在线 native：census 与页遍历期间只发出平台 GET，`live_scene_reads_in_this_run=0`；取树与历史资产接口继续读冻结 bundle。
- 隔离夹具（`tmp_path`，不触碰真实归档）覆盖：缺时、非数值、相等（并列不除零）、回退（该基被拒而其余基仍判）、重复 id（列出全部位置 + robot-state 409 + 两锚点仍按原序可见）、以及触顶截断（`covers_whole_episode=false` 且各基阻塞含 `scan_truncated_at_anchor_limit`）。

## 6. 验证结果

- 真实归档读取检查 **130/130**（M1.5f 118 → 本轮 +12 项）；统一能力回归 **28/28**；冻结 release 内聚焦 **63 passed**；同一棵树全量 **191 passed / 3 failed**（M1.5f 的 183+8 项新用例；三项历史布局失败名称与基线不变：`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`，不使用"全绿"表述）。
- 服务器实测 **71 条请求全为 GET**；946 文件覆盖集合事前记录、事后复核 **`drift=[]`**；源码聚合 `707843426524d406…`（49 文件）在冻结 release 与本地工作树**全等**；启动清单 sha256 `064a5bf0192798fa046dd065d0139c461fdef74ebe2f41ce3a5d48a19138573b`，报告重算与清单 MATCH。
- 边界遵守：未启动新 native、未运动、未 RESET、未录制、未 STOP/end、未重启 8792（8792 仅经 `GetProbe` 发 GET）；历史归档/tail/原始媒体/生产 recipe 与 pin/native 工作树未改；`frontend/` 未修改；只改 `backend/` 与必要 `docs/`。
- 过程记录：本轮先在 scratch 实例（18978，运行同一棵 dev 树）跑通 130/130 与全部夹具测试，之后才冻结交付候选，未产生半途 release；scratch 进程经命令行身份核对（`--draft-db` 指向 `var/reports/scratch-m1w-pre-155714/frames.sqlite3`）后停止，其报告目录保留为过程记录。

见 [证据册](evidence/m1.5g-anchor-time-quality/README.md)（真实 census / 真实受限 / synthetic 异常样例与请求日志）与契约 [Episode、事件、标注契约](specs/30-contracts/03-episode-events-annotations.md)。

## 7. 不主张

生产部署、正式 M1.5 或 M1 验收；历史整车渲染与前端装配完成；跨流同步、统一历史游标、采样同刻、声明速率、全归档覆盖。FAILED 记录的锚点虽然时间上"干净"，但该记录本身仍是不完整终态：census 只说明可读锚点的时间质量，不认证录制的完整性或训练资格。

---

## 8. 更正（2026-10-30，M1.5h/S28/DEC-065）

本节是本记录的最后一处改动，此后不再编辑本文件。

- **覆盖规则收紧**：本文第 3 节的 `covers_whole_episode` 当时只由"扫描是否触顶"得出。该规则允许"锚点文件里存在超限或无法解析的行时，仍由其余干净锚点宣称整条 Episode 的 B 资格"。M1.5h 起 `covers_whole_episode` 同时要求扫描到达 EOF 且每一行都被判定；不可判定行（oversize／unparseable／non_object）以 `n_lines_are_undecidable_and_could_hide_anchors` 阻塞整集结论并给出 `record_position`，空行与"确认无关"的行仍判为良性、不阻塞。旧可选串 `scan_truncated_at_anchor_limit` 由 `scan_stopped_at_anchor_limit_before_eof` 取代。
- **窗口范围表述更正**：本文第 44 行"带时间窗的页仍会返回同一份 Episode 级 census（窗只筛页，不改 census）"的结论正确，但当时的 `scope_note` 把"窗口页"与"截断扫描"并列为不支持整集声明的原因，容易被读成"页面带时间窗就降为窗口资格"。现行 `scope_note` 明确：窗只筛帧页，整集资格只看普查自身的覆盖与内容。真实复现请求：`...&time_base=capture_sim_time_s&time_from=0.2&time_to=0.6&include_time_quality=true` 返回 1 帧（302 条窗外），同一响应 census 仍 303 锚点、`covers_whole_episode=true`。
- 上述缺陷在 `a10b96b` 上的复现与修正后对照见 [M1.5h 证据册](evidence/m1.5h-coverage-and-action-basis/README.md)（`m1h_repro_baseline.json`／`m1h_repro_corrected.json`）。本文其余实测数值（130/130、303 锚点、4.998/5.000/4.967 Hz、census 8,733 B 等）是当时候选 18979 的真实测量，保持不变。
