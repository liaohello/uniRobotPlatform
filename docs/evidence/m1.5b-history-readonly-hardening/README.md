# M1.5b 证据册｜历史 reader 只读整改、根目录隔离与可复现发布

目录：`m1p-20261025T053030Z-platform/`（服务器 release `releases/m1p-20261025T053030Z-platform`，冻结候选 `http://127.0.0.1:18964`）。全部测试与读取验证在服务器执行；本地未运行测试或构建。中间 release `m1l/m1m/m1n` 保留在服务器且未被改写，只作为整改过程证据，不作为本轮结论来源。

## 一、冻结身份

| 项目 | 值 |
|---|---|
| release | `m1p-20261025T053030Z-platform`（由整改后的 `m1l` 测试构建整体复制生成，冻结后未再原地修改源码或工具） |
| 启动清单 sha256 | `832bf518274600a9c64b6a2dd55b83c70246d6ecb6c79c48042e80e965629f85` |
| 平台源码聚合 | `4090935b4c45c900ec9b2eed62372bfc02ad5b0464f21fcf9da6c76c9fa89715`，45 文件，roots `src/unirobot` + `config` + `tools`（含启动器与三个检查/提取工具） |
| 清单与运行字节一致性 | `history-check.json` 断言 `recorded_aggregate == recomputed_aggregate` 且文件数相等；`unified-on-history-candidate.json` 同样断言（`matches_running_bytes: true`） |
| 历史来源声明 | `backend/config/mobilecar-history-source.json`，sha256 `fbfcc6a69edb9472007e9076c39e9677b2797b4a7e7bb2e4b8eac432fde9c394`（由清单记录、由工具重算断言） |
| 数据库 | 独立 `report/history-053031.sqlite3`，`existed_before=false`；未读取或覆盖任何更早候选的库 |
| 只读执行记录 | `get-probe-log.jsonl`（51 行，全部 `"method":"GET"`）与 `get-probe-log.json`（`methods:["GET"]`、`non_get:[]`）；`history-replay-facts.json` 另有 8 次 GET |
| 覆盖集合 | `coverage-digests.json`：946 个文件的 before/after 摘要与 `drift=[]`；`archive_baseline_before == archive_baseline_after == 60c0c696…`（仅覆盖 696 个 `episode.json`/`episode_complete.json`） |

## 二、文件

| 文件 | 内容 |
|---|---|
| `history-startup.json` | 冻结启动清单（端口/native/geometry/maps/recipe/独立库 + `history` 块 + `platform_source.roots`/逐文件摘要） |
| `history-check.json` | 69/69 断言：上一轮 61 项全部保留 + 8 项新增（清单/字节绑定、来源配置字节绑定、解析根与边界规则、真实归档无软链排除、无 `event_seq` 流在区间下被排除并计数、日历时间基拒绝数值边界、覆盖集合前后一致、本次请求全为 GET） |
| `unified-on-history-candidate.json` | 28/28：M1.4b 的 27 项能力回归 + 1 项源码绑定断言 |
| `coverage-digests.json` | 覆盖集合 before/after、逐文件摘要、`drift`、显式未覆盖清单 |
| `get-probe-log.jsonl`、`get-probe-log.json` | 每一次 GET 的 URL/状态/字节数与摘要（只读执行记录） |
| `history-replay-facts.json` | 由 `tools/history_replay_facts.py` 提取的最小事实表：逐流字段/时间基/序列/单位/frame、媒体 URI 关联、历史模型身份、`proven_by_this_run` 与 `not_proven` |

## 三、必须分开读的事实

1. **整改后的读取面**：真实 COMPLETE 与 FAILED/incomplete 记录均可分页读取，事件顺序与身份保持原生值；平台轻量详情 21 KB 级对 native 整条 20.9 MB；真实归档 `media_summary.excluded_count == 0`（没有软链需要排除），`source.recording_root_resolved` 与 `path_boundary` 一并对外可见。
2. **完整性与违规的当前状态**：`episode.json` 的 tail 自校验在抽样 16/16 条真实记录上过期（`mismatch_present`），生命周期声明值不被改写；`quality_report.json` 因上一轮误发请求被 native 重写，其**重写前摘要从未快照**，本册不作任何"内容未变"表述；被证明未变的是 696 聚合集合与本轮 946 文件覆盖集合。
3. **未做**：其他文件在违规时点之前的前置摘要；同步回放与统一游标；逐 body 位姿重建；native 任何写请求；8792 变更；物理运动/录制/RESET/训练；M1.5/M1 验收。

## 四、隔离夹具覆盖（服务器 19 passed）

`backend/tests/test_episodes.py` 新增：run/`episodes`/Episode 目录级软链不进索引（404 `episode_not_found`）、`episode.json` 文件级软链 409 `episode_path_escape`、run `manifest.json` 软链 409 `history_path_escape`、`assets/` 目录软链 409 `episode_asset_escape`、索引缓存后替换目录为软链仍被读取时拒绝、`event_seq` 缺失/字符串/bool 在区间下被排除并计数且不补造、`wall_utc` 数值边界 400 `time_base_not_numeric`。夹具全部在 `tmp_path` 副本上构造，未修改真实归档、未启动录制。

## 五、历史失败与基线

平台全量：147 passed / 3 failed，失败项仍是 `test_catalog::test_catalog_loads_real_tasks`、`test_catalog::test_every_task_has_existing_evidence`、`test_migrate::test_manifest_sources_exist`（断言读取仓库文档/外部工程布局，服务器 release 副本内不成立）。链条：74/3 → 90/3 → 98/3 → 108/3 → 123/3 → 128/3 → 140/3 → 本轮 147/3（新增 7 项聚焦测试全通过，未新增失败）。不使用"全绿"表述。

## 六、冻结后复跑（2026-10-25，不生成新绑定产物）

冻结之后在服务器做了一次独立复跑，输出只写入 `/tmp/m1p-verify-<ts>/` 并在验证后删除，`releases/` 与 `var/reports/` 中已提交的本册产物未被改写，因此本节不构成新的绑定报告，只证明上一节的数字可再现：

- 副本聚焦测试 `tests/test_episodes.py`：19 passed。副本全量：147 passed / 3 failed，失败项与本册第五节完全同名同因（历史仓库布局断言）。
- 对存活候选 `127.0.0.1:18964` 重跑 `tools/episode_history_check.py`：69/69，`requests.methods=["GET"]`、`total=51`、`platform_source.match=true`（recorded 与 recomputed 均为 `4090935b4c45c900…`）、946 文件覆盖集合 `drift=[]`。
- 独立重算归档 696 个身份文件聚合摘要：`60c0c6963bc9ae84…`，与 `m1p-…/coverage-digests.json` 的 before/after 一致。
- native 排障一律走 `tools/native_get_probe.GetProbe`（无 method/body 形参）：`/api/v1/health` 200，`run_9c88e3e3…/gen 1/episode_43c22f95…` 未变，`non_get=[]`。
- 文档修复提交 `1f7f88e` 只触及 `docs/specs/`，不在清单摘要根（`src/unirobot`/`config`/`tools`）内，`4090935b…` 与 `832bf518…` 继续有效。
