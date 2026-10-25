# M1.5c 证据册｜run 身份边界最小修正与真实帧关联切片

绑定产物：`m1s-20261025T084308Z-platform`（`http://127.0.0.1:18966`，服务器 `~/Desktop/uniRobotPlatform/releases/…`，报告 `~/Desktop/uniRobotPlatform/var/reports/…`）。
说明文档见 [M1.5c 交付记录](../../backend-m1.5c-frame-linkage.md)。

## 一、冻结身份

| 项 | 值 |
|---|---|
| 启动清单 sha256 | `6872adad98dbc75fb253e18725c81309b53d0a4c40c03d573c72d4298404a9d4`（`history-startup.json`） |
| 源码聚合（46 文件，`src/unirobot`+`config`+`tools`） | `932582d19de263ab6a74cc8f5e85b77caf309edf0dc474b92b000a5727263a04` |
| 检查工具重算 | `platform_source.match=true`，recorded 与 recomputed 同上 |
| 进程登记 | PID `3668527`，本地启动 `Sun Oct 25 16:43:08 2026`，owner `liaozhengyan`，完整 argv 在 `launch-registry.json` |
| 数据库 | `frames-20261025T084308Z.sqlite3`，`existed_before=false`（未覆盖旧库；该运行期文件不入库） |
| 端口占用检查 | 18961/18962/18963 属于他人服务，未被使用或清理；18964/18960/18959/18953/18949/8792 全部保留 |

## 二、文件

| 文件 | 内容 |
|---|---|
| `history-check.json` | 86/86 读取与帧关联断言，含 `classification` 与 `not_covered` |
| `get-probe-log.jsonl` / `get-probe-log.json` | 本轮经 `GetProbe` 发出的 59 条请求，`methods=["GET"]`、`non_get=[]`，并带作用域说明 |
| `coverage-digests.json` | 事前记录、事后复核的 946 文件集合，`drift=[]`；同时保留归档 696 聚合前后值 |
| `unified-on-history-candidate.json` | 28/28 统一能力回归（geometry-2、Map/Route、Draft、Session/current、STOP/end、既有历史 GET） |
| `history-replay-facts.json` | 上一轮最小事实表的再生产（8 条 GET） |
| `frame-sample-complete.json` | 真实 COMPLETE 记录首页一帧：四主角色 matched、`age_ms=2.8854…`、`declared_reference_status=unresolved_reference` |
| `frame-sample-second-page.json` | `offset=1` 的第二帧，证明游标可续 |
| `frame-sample-incomplete.json` | 真实 FAILED/INCOMPLETE 记录 4 帧，主角色全 matched、引用 4/4 未解析 |
| `error-unsupported-time-base.json`、`error-invalid-sample-id.json` | 真实错误响应（冻结候选） |
| `openapi.json` | 六条历史路径，方法集合均为 `{"get"}` |
| `launch-registry.json` | 进程、端口、release、数据库与所有权登记 |

## 三、真实与隔离夹具必须分开读

1. **真实归档事实**：303 个持久帧；每个 `sample_id` 恰 2 个观测行；606 个 `asset_uri` 全部存在且带 `metadata.asset_sha256`（抽查 6/6 相等）；`sample_id→transforms` 303/303；`capture_control_tick_id→events.control_tick_id` 303/303；`feedback_sample_id` 仅 3/303 有对应观测行；状态记录早于采集 0.34–8.78 ms（首页帧 2.885 ms），采集→落盘约 100 ms。
2. **未证明的部分**：时钟同源性（只命名，不验证）、跨流/跨 Episode 游标、历史 3D 渲染、逐 body 位姿可否重建。响应内以 `clock_sameness.verified_by_reader=false`、`synchronized_across_streams=false`、`three_d_replay.*=false` 与 `not_proven` 明示。
3. **隔离夹具（`tmp_path` 副本，非真实归档）**：run 目录换成 root 内兄弟 run 的软链、同名 Episode 跨 run、媒体软链逃出 `assets/`、缺 `observations/persist.jsonl`、候选记录声明他人 Episode、无 capture tick 状态、不可用 `sample_id` token。这些只在 `backend/tests/test_frames.py` 内构造，真实归档未被写入。
4. **不变性口径**：只对事前记录摘要的 946 文件集合成立；`quality_report.json` 等派生文件仍只有现状，不声称历史未变。

## 四、被取代的同轮尝试

`m1q-20261025T084007Z-platform`（PID `3492357`，`http://127.0.0.1:18965`，聚合 `71e984c347416da3…`，清单 sha `fd62b390…`）保留为历史：其报告目录内没有 `history-check.json`，因为检查工具的一条帧断言把默认页大小写死导致中断；平台代码字节与 `m1s` 相同，差异仅在 `tools/`。未回填、未删除、进程未清理。一次变量替换失误产生的空 `m1r-…` 目录（无 backend，只有一份失败启动日志）已删除，无证据价值。

## 五、测试与失败基线

- 聚焦（在冻结 release 的隔离副本内）：`test_frames.py` 12 + `test_episodes.py` 19 = **31 passed**。
- 全量：**159 passed / 3 failed**，失败项名称与基线不变：`test_catalog::test_catalog_loads_real_tasks`、`test_catalog::test_every_task_has_existing_evidence`、`test_migrate::test_manifest_sources_exist`。链条 147/3 → 159/3（新增 12 项全部通过，未新增失败）。不使用"全绿"表述。
