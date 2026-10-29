# M1.5g 证据册｜采集锚点时间质量与播放资格（候选 `m1w-20261029T155818Z-platform`）

权威语义在 `docs/backend-m1.5g-anchor-time-quality.md`；本册登记实测字节、请求与逐项断言。真实归档、冻结身份核对与隔离夹具三类证据分列。

## 冻结身份与实际进程

| 项 | 值 |
|---|---|
| 实际运行地址 | `http://127.0.0.1:18979`（`GET /api/v1/episodes?limit=1` 实测 200；服务未注册 `/health`） |
| release / PID | `m1w-20261029T155818Z-platform` / PID 2738345（`launch-registry.json`；`listen.was_free_before_start=true`） |
| 独立 SQLite | `var/reports/m1w-20261029T155818Z-platform/frames-20261029T155818Z.sqlite3`（启动前不存在） |
| 源码聚合 | `707843426524d4065f922743cb0a27bc383e4555ead46373f0188f35dd0f5e9c`，49 文件（`src/unirobot + config + tools`），与本地工作树**全等** |
| 启动清单 | sha256 `064a5bf0192798fa046dd065d0139c461fdef74ebe2f41ce3a5d48a19138573b`；检查工具重算 ↔ 清单 **MATCH** |
| 覆盖不变性 | 事前记录、事后复核的 946 文件集合 `drift=[]`（其余文件该时点无前置摘要，属未覆盖） |
| 请求 | `GetProbe` 71 条，methods 仅 `GET`；`live_scene_reads_in_this_run=0` |

## 实测结果一览

| 项 | COMPLETE 记录 | FAILED 记录 |
|---|---|---|
| 可读锚点 / 唯一 id | 303 / 303 | 4 / 4 |
| 拒绝锚点（身份/流/无 id） | 0 / 0 / 0 | 0 / 0 / 0 |
| 行号范围 | 0 … 302 | 见样本 |
| 三基数值 / 缺失 / 非数值 | 303 / 0 / 0（每基） | 4 / 0 / 0（每基） |
| 相等相邻 / 回退 | 0 / 0（每基） | 0 / 0（每基） |
| `covers_whole_episode` | true | true |
| A 追加顺序展示 | eligible | eligible |
| B 逐基 `eligible_for_whole_episode` | 三基均 true（`blocking_reasons=[]`） | 三基均 true |
| C 跨流同步 | **not eligible** | **not eligible** |
| 隐含速率（median 间隔倒数） | 4.998164898438034 / 5.000000000002771 / 4.96713118922423 Hz | 见样本 |

完整数值（首末、min/max、间隔 min/max/median/mean/total、profile、`not_proven`）在 `frames-census-complete.json` 与 `frames-census-incomplete.json` 原样可见。

## 页遍历与筛选语义（真实 HTTP）

- `frames-page-without-census.json` / `frames-page-with-census.json`：同一 `limit=2` 请求，键集合差恰为主观测块 `time_quality`（顶层 `set(with) - set(without)` 在 130 项检查里以整页 200 帧验证）。
- `frames-census-windowed.json`：`time_base=capture_sim_time_s&time_from=0.2&time_to=0.6&limit=2` → 返回 1 帧、`excluded_outside_time_window=302`、`records_missing_selected_time_base=0`，帧仍按 `line_index` 升序；`time_quality.coverage.page_filter_context` 回显窗与分页参数，而 `anchors_in_this_scan` 仍为 303（窗筛页、不改 census）。响应头 `etag_present=false`，`content-length=43841`。
- 遍历（检查项 `walking the pages consumes every anchor once…`）：2 页（200 + 103）＝303 锚点，行号 `== sorted(set(...))`，末页 `has_more=false`、`next_offset=null`、`post_page_records_examined=0`、`whole_file_scanned=true`。
- 体积：census 8,733 B；同请求 200 帧本体 5,181,012 B。

## 本轮 12 条新断言（`history-check.json` 原名）

- the default page stays light and the census is opt-in only
- the census counts readable anchors and their valid identity, and says what it covered
- each capture base is reported with its field, unit, clock and per-base counts
- first/last in file order is separated from min/max in value order for every base
- recorded time advances in append order, so no anomaly had to be explained away
- no rate is assumed: the numbers come from the recorded values, never from a default
- append-order display, recorded-interval scheduling and cross-stream sync stay three claims
- anchor identity is unique here, and the census would name every position if it were not
- walking the pages consumes every anchor once, in append order, with no gap or repeat
- asking for the census leaves paging and both filters exactly as they were
- the incomplete real record is measured with the same vocabulary and the same honesty
- the census and the page walk ask the platform only, never the live native scene

## synthetic 异常样例（隔离夹具，非归档事实）

`synthetic-backwards-census.json`（该基被拒、其余基仍单独判定、锚点顺序未改）、`synthetic-equal-tie-census.json`（并列存在、`implied_rate…=null` 不做零除）、`synthetic-missing-time-base-census.json`（缺失计数、剩余值未被填充）、`synthetic-truncated-census.json`（`covers_whole_episode=false` + `scan_truncated_at_anchor_limit`）、`synthetic-duplicate-anchor-refusal.json`（重复 id 的 `robot-state` 409 `frame_sample_id_ambiguous`，含两个匹配位置）。全部在 `tmp_path` 内的合成 Episode 上产生，未触碰真实归档，**未**通过断开 8792 取证。

## 测试

冻结 release 内聚焦 **63 passed**（`test_frames.py` + `test_history_fk.py` + `test_episodes.py`）；同一棵树全量 **191 passed / 3 failed**，三项历史布局失败保留名称与基线（`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`；成因见 M1.2 证据册：`../bimanual_proj`、`../mujoco_learning` 不在本服务器 release 布局中），不使用"全绿"表述。统一能力回归 **28/28**。

## 过程记录

交付前先以运行同一棵 dev 树的 scratch 实例（`127.0.0.1:18978`）跑通 130/130 与夹具用例，之后才冻结 `m1w-…`；scratch 进程按命令行身份核对后停止，其报告目录 `var/reports/scratch-m1w-pre-155714` 保留为过程记录。18977（M1.5f）与其他既有服务未被替换或清理。

## 不主张

跨流同步、采样同刻、声明速率、历史整车渲染、前端装配完成、全归档覆盖、生产部署与正式 M1.5/M1 验收；FAILED 记录的锚点时间"干净"不等于该记录完整或训练合格。
