# M1.5h 证据册｜时间资格覆盖边界修正与历史动作／事件读取依据

日期：2026-10-30 · 候选：`m1h-20261030T002258Z-platform` · 交付说明：[../../backend-m1.5h-coverage-boundary-and-action-basis.md](../../backend-m1.5h-coverage-boundary-and-action-basis.md)

## 0. 运行中的候选与身份核对

| 项 | 值 |
|---|---|
| 实际运行地址 | `http://127.0.0.1:18983`（`GET /api/v1/episodes?limit=1` 实测 200；本服务未注册 `/health`，404 不代表不可用） |
| PID / 启动时刻 | 3745241（见 `launch-registry.json`） |
| 端口核活 | 启动前 `ss -ltn` 实测 18983 空闲；18977（M1.5f）与 18979（M1.5g）常驻未替换 |
| 独立 SQLite | `var/reports/m1h-20261030T002258Z-platform/frames-20261030T002258Z.sqlite3` |
| 冻结源码聚合 | `68f481b38843d2bc4109c0bebbeccde819253aaf317409b66e3d1b6db7d86f45`／50 文件，重算 ↔ 启动清单 **MATCH** |
| 启动清单 sha256 | `90b5234d6308860d9d6b040ccc2b8b385704a8521aaea62d66d154f03b2aca73` |
| 关键源文件 | `src/unirobot/frames.py` = `f4b4187fc5b4e0cfcc0e6c11cc00993981985f48533accef5eb1251b93ced202`（清单值与运行目录逐字节相同） |

## 1. 真实归档证据（不是合成）

| 文件 | 内容 |
|---|---|
| `history-check.json` | 读取检查 **146/146**（本轮新增 16 项，每项带实测 detail） |
| `unified-on-history-candidate.json` | 统一候选能力回归 **28/28** |
| `get-probe-log.jsonl` / `.json` | 本轮全部 75 条请求，全为 GET，无 `/api/v1/scene` 读取 |
| `coverage-digests.json` | 覆盖 946 个归档文件，检查前后 `drift=[]`（未修改归档） |
| `history-startup.json` | 冻结清单（含逐文件摘要、监听号段与启动前空闲标记） |
| `frames-census-complete.json` | 真实 COMPLETE 的 `time_quality` 整块（303 锚点、三基、`line_accounting`） |
| `frames-page-default-no-basis.json` | 默认帧页（无 `time_quality`、无 `action_basis`，39,211 B） |
| `frames-window-page-census-full.json` | **窗口页 1 帧 + 302 窗外，census 仍 303 锚点、`covers_whole_episode=true`**（范围表述修正的真实证据） |
| `frames-census-and-basis-together.json` | 两个 opt-in 同时开启时的共存形状 |
| `action-basis-complete.json` | 真实 COMPLETE 的 `action_basis`（events 全量 12561 条、12 个 type、逐帧候选） |
| `action-basis-failed.json` | 真实 FAILED 的 `action_basis`（224 条、11 个 type、`lease_heartbeat` 缺席） |
| `events-records-command-window-real.json` | 既有 records 分页 + `event_seq_from/to` 的真实命令链记录 |
| `openapi-frames-include-parameters.json` | OpenAPI 中帧路由的两个可选参数（`include_time_quality`、`include_action_basis`） |
| `evidence-summary.json` | 上述关键测量值的汇总（供交接文档核对） |

真实代表记录：COMPLETE `run_0104613ff7364ae78cf2f3946bd45f7b / episode_27bfed5427684795b361cd2ec21e9aa7`；FAILED `run_1f6fb34853f94130aadedb8fa486705b / episode_879cf70489064a3b83bb15b5395a8341`。

## 2. A 段缺陷复现（基线源码 vs 修正源码，同一隔离夹具）

| 文件 | 内容 |
|---|---|
| `m1h_repro_baseline.json` | 以 `a10b96b` 冻结源码直读同一夹具：`covers_whole_episode=true`、`any_base_eligible_for_whole_episode=true`、逐基 `blocking_reasons=[]`，且该夹具含一行无法解析的锚点文件内容 → **旧错误确实成立** |
| `m1h_repro_corrected.json` | 以本轮源码读同一夹具：`reached_end_of_file=true`、`every_line_of_the_anchor_file_is_decided=false`、`covers_whole_episode=false`、`any_base=false`、逐基 `1_lines_are_undecidable_and_could_hide_anchors`、A 仍 `eligible=true` |

复现脚本：`backend/tools/anchor_coverage_repro.py`（只读隔离夹具，不接触真实 recording_root）。

合成夹具（`backend/tests/test_frames.py`，服务器执行）另覆盖：`oversize`／`unparseable`／`non_object` 三类不可判定行各自否决整集结论；`blank_lines` 与"确认无关"行不否决；扫描触顶自报；无 events 流时逐项 `missing`；`action_basis` 重复候选的 `ambiguous_candidates` 与全部位置。真实归档与合成证据分列，不用旧套件计数代替新增行为。

冻结树全量测试：203 passed / 3 failed，三项历史布局失败按名保留（`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`），不称全绿。
