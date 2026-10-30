# M1.5i 证据册｜拒绝回执分域与时间接近不提升同步

日期：2026-10-30 · 候选：`m1i-20261030T035643Z-platform` · 交付说明：[../../backend-m1.5i-rejection-domain-and-clock-parity.md](../../backend-m1.5i-rejection-domain-and-clock-parity.md)

## 0. 运行中的候选与身份

| 项 | 值 |
|---|---|
| 实际运行地址 | `http://127.0.0.1:18985`（`GET /api/v1/episodes?limit=1` 实测 200；本服务未注册 `/health`） |
| PID / 端口核活 | 1659550；启动前 `ss -ltn` 实测 18985 空闲；18977（M1.5f）、18979（M1.5g）、18983（M1.5h）常驻未替换 |
| 独立 SQLite | `var/reports/m1i-20261030T035643Z-platform/frames-20261030T035643Z.sqlite3` |
| 冻结源码聚合 | `107f897ddfe2485fb116eba8c6bbdef32258c4c2ab483d80f27a01e1cf803d59`／50 文件，重算 ↔ 启动清单 **MATCH** |
| 启动清单 sha256 | `7338d2779ecf55fbb6b285b087b3e0d996a31f7d45c3222247c2abd648d5830f` |
| 关键源文件 | `src/unirobot/frames.py` = `9ae98b126e42760aa54ef99ab3c74bfc4b445b70605a39e30a0fdd3b4903f06f`（清单值与运行目录逐字节相同） |

## 1. 真实归档证据

| 文件 | 内容 |
|---|---|
| `history-check.json` | 读取检查 **148/148**（本轮 +2：`a command stamp numerically close to a frame buys no link and no clock claim`、`a rejection is a receipt category, and this archive records none to promote`） |
| `unified-on-history-candidate.json` | 统一候选能力回归 **28/28** |
| `get-probe-log.jsonl` | 77 条请求，全为 GET，无 `/api/v1/scene` |
| `coverage-digests.json` | 946 个归档文件，检查前后 `drift=[]` |
| `history-startup.json` / `launch-registry.json` | 冻结清单与启动登记（端口、PID、启动时刻、argv） |
| `action-basis-complete.json` | 真实 COMPLETE 的 `action_basis`（200 帧页、events 全量词表、逐帧候选） |
| `action-basis-rules-and-not-proven.json` | 关联规则（含本轮新增 `clock_parity`）、`independent_tracks` 与 `not_proven` |
| `rejected-category.json` | 拒绝类别的实测状态 `not_recorded_in_this_scan` 与"不等于不可能"声明；受理/下发计数对照 |
| `proximity-command-to-anchor.json` | **实测 15.8 ms**：命令时间戳与第 7 行锚点采集时刻只差 `0.015817145991604775 s`，却不在任何关联类型里，`same_clock_verified`/`synchronized_across_streams`/`verified_by_reader` 全 false |
| `events-records-command-window-real.json` | 既有 records 路由按 `event_seq` 窗口返回的原始记录（保留原始事件值） |
| `pytest-rejection-parity-and-coverage.txt` | 冻结树内针对本轮主题的 11 项合成用例输出 |

## 2. 合成夹具证据（与真实归档分列）

冻结树 `tests/test_frames.py` 新增两项，均由服务器执行：

- `test_a_recorded_rejection_is_a_receipt_and_never_an_executed_action`：夹具**真的写了**一条 `rejected`（`decision.approved=false`、`reason=outside_declared_workspace`、`control_tick_id=null`）。断言拒绝类别 `status=observed`、`counts={rejected:1}`；该命令链只有 `requested→rejected`，无 `approved`/`dispatch`；已批准命令仍是唯一被下发者；`rejected` **不出现在任何帧关联**（关联类型集合恒为 `actuator_reference`/`dispatch`/`feedback`/`feedback_initial`）；`independent_tracks` 含 `command_receipt_rejected`/`command_receipt_accepted`；`not_proven` 仍否认"任何命令已被物理执行"。
- `test_an_equal_stamp_without_a_shared_key_never_creates_a_link_or_a_sync_claim`：把被拒回执的 `backend_monotonic_s` 设为与第二个帧采集时刻**完全相等**且不带 tick；断言读者不建立任何角色（`requested`/`rejected` 从不进入 `by_event_type`）、`clock_parity` 规则生效、页面 `same_clock_verified=false`、`clock_sameness.verified_by_reader=false`、`synchronized_across_streams=false`；同一记录的原始负载仍能经 `streams/events/records` 逐字读回（`reason=outside_declared_workspace`、时间戳等于 `CAPTURE_2`）。

A 段（不可判定行覆盖边界）的基线与修正对照仍在 M1.5h 证据册（`m1h_repro_baseline.json` / `m1h_repro_corrected.json`）；本轮只复验、不重复实现，复验结果见 `history-check.json` 中的 coverage 与窗口断言。

冻结树全量测试：**205 passed / 3 failed**，三项历史布局失败按名保留（`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`），不称全绿。冻结树聚焦 71 passed。
