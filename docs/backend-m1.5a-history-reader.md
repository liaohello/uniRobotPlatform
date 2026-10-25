# M1.5a｜真实历史 Episode/segment 只读 reader 首个切片

2026-10-25 · 范围：把服务器已有的真实历史录制以**只读**方式接入平台，固定一个明确来源，冻结最小历史读取契约与 OpenAPI，并保持原生身份、时间与动作语义不变。

**真实历史 reader 首个切片完成（61/61 服务器实测断言）；这不代表同步回放 UI、新采集闭环或正式 M1.5/M1 验收通过。** 原始数据全部留在服务器，不搬目录、不重写、不导出重算；`frontend/` 未改动。

**本轮边界违规与后果（不隐瞒）**：交付代码路径与 61 项检查只对 native 发 GET，但一次人工排障探测向 8792 发送了 `POST /api/v1/episodes/episode_27bfed5427684795b361cd2ec21e9aa7/validate`，违反了"仅 GET"边界。后果已实测限定为**该记录的一份派生文件**被 native 自己重写：`…/episode_27bfed54…/quality_report.json`，mtime 2026-10-25 12:20:38，摘要 `53314c847d17f38da6b32587aaaeb830660f495bc5f2df45b57d3759efa303bd`；该文件重写前的摘要未被快照，因此**不能声称内容不变**。经复核未变的是下列明确集合（不是整个归档）：`episode.json` `0dec88f47c9fa1dd…` 与 `episode_complete.json` `b2923d0f9587fe04…` 仍等于落地前基线，mtime 仍是 2026-10-18；全归档 696 个同名文件聚合摘要仍为 `60c0c6963bc9ae84…`（逐文件差异 0 项）；8792 运行时状态前后一致（`episode_43c22f95…`、`recording_status=IDLE`），未被停止/重启/替换。后续任何复现都不得对 native 发非 GET 请求；该约束在 M1.5b 已由构造保证（`tools/native_get_probe.py`），并纠正了本节原先超出证据的表述，见 [M1.5b 整改记录](backend-m1.5b-history-readonly-hardening.md)。

## 一、结论

| 项 | 状态 |
|---|---|
| 一个明确历史来源 + 实际 recording_root 已冻结 | `mobilecar-server-history-20261017` → `/home/liaozhengyan/Desktop/mobileCar/var/runs`（native `configs/g4a2_server.yaml` 的 `recording.root: ../../var/runs`，release `drvfix-20261019T044549Z-0a80415b2577`）；声明文件 `backend/config/mobilecar-history-source.json`，sha256 `fbfcc6a69edb9472…` |
| 平台历史读取 API（列表 / 轻量详情 / 可用流 / 分 records 页 / 媒体资产） | 5 个 GET 路径在同一 OpenAPI 中暴露，61/61 断言在服务器对**真实记录**通过 |
| 真实记录规模 | 348 条 Episode（272 个 run id / 磁盘 295 个 run 目录）；声明 342 COMPLETE + 6 FAILED（audit 342 COMPLETE + 6 INCOMPLETE）；全部记录 `complete_tail=true`；多段 Episode 0；跨 run 重复 episode_id 0 |
| 完整性分层 | 生命周期闭合状态、`complete_tail` 存在性、tail 声明校验和、本次读取实际重算结果分别表达；抽样 16 条真实记录的 tail 对自身 `episode.json` 声明均为**过期自校验**（`mismatch_present`），仍按声明保留生命周期状态，不改写、不称已验证 |
| 已覆盖集合复核未变（非整库证明） | 696 个 `episode.json` + `episode_complete.json` 聚合摘要在整轮读取前后一致：`60c0c6963bc9ae8442bc3d9c9e5f0c33c19973cee966994365313b57ae9d6664`；8792 health 前后完全一致（`run_9c88e3e3…/gen 1/episode_43c22f95…`、`recording_status=IDLE`）。其它文件（含被 native 重写的派生 `quality_report.json`）在该时点没有前置摘要，属未覆盖 |
| 新候选端口，不替换既有服务 | 历史候选常驻 `http://127.0.0.1:18960`，同一进程继续携带 geometry-2、Map/Route、Session/`current`、STOP/end 契约（原统一检查 27/27 在该候选上复跑通过）；18959/18949/18953/8792 未替换 |
| 发布身份小缺口已闭合 | `launch_unified_gateway.py` 的 `SOURCE_ROOTS` 增至 `("src/unirobot","config","tools")`，平台源码聚合摘要 `e86a709fb6e59f44…` 覆盖 42 个文件，其中包含启动器与本轮检查工具；native 完整清单 154 路径与生产 pin 的边界不变 |

## 二、冻结的来源与读取方式

`EpisodeArchive` 直接按原生 Recorder 落盘布局读取（`runs/<run_id>/manifest.json` 与 `runs/<run_id>/episodes/<episode_id>/…`），不重新导出、不重算、不建索引库：本切片是纯读取服务，没有 SQLite，不覆盖也不迁移任何旧资源。之所以不代理 native HTTP 详情：`GET /api/v1/episodes/{id}` 对同一条记录返回 **20,946,833 字节**（整份 JSONL 入内存），而平台轻量详情只有 **21,031 字节**——把整份详情转给前端正是本切片要避免的。

`--episode-root` / `UNIROBOT_EPISODE_ROOT` 只用于隔离夹具与测试；真实候选的 root 由声明文件固定，`root_override` 记录为 `null`。

可用流（`stream_id` → 原生文件）：`events`→`events.jsonl`、`control`→`control.jsonl`、`commands`→`commands.jsonl`、`transforms`→`transforms.jsonl`、`observations-index`→`observations/index.jsonl`、`observations-persist`→`observations/persist.jsonl`、`initial-snapshot`→`initial_snapshot.json`、`episode`→`episode.json`、`tail`→`episode_complete.json`。原生 `ReplayReader` 的 HTTP 面没有暴露 commands/control/transforms/persist，也没有分页；平台按同一文件格式自行有界读取，未发明新存储格式。

## 三、最小历史读取契约（已实现并冻结）

| 方法与路径 | 作用 | 关键参数 |
|---|---|---|
| `GET /api/v1/episodes` | 有界分页列表 + 每条声明状态 | `limit`(默认 50，上限 200)、`offset`、`run_id`、`recording_status`、`episode_id` |
| `GET /api/v1/episodes/{episode_id}` | 轻量详情：身份、segment、可用流、完整性分层、时间与动作语义、记录内模型身份、媒体摘要 | `run_id`（歧义时必填） |
| `GET /api/v1/episodes/{episode_id}/streams` | 可用流目录：逐文件存在性、字节数、真实记录计数、超大行数 | `run_id` |
| `GET /api/v1/episodes/{episode_id}/streams/{stream_id}/records` | 按流有界读取；`event_seq` 区间或命名时间基过滤 | `run_id`、`limit`、`offset`、`event_seq_from/to`、`time_base`+`time_from/to` |
| `GET /api/v1/episodes/{episode_id}/assets/{asset_path}` | 媒体资产读取，限定该 Episode 的 `assets/` 子树 | `run_id`、可选 `sha256`（64 位十六进制） |

响应统一使用 `schema_version: "unirobot-mobilecar-episode-read-1"`、`read_only: true`，并携带 `source`（source_id/adapter/release/recording_root/声明规模/基线摘要）、`paging`、`cursor`、`integrity` 与 `capability_limits`。列表排序为 `run_id → episode_id`，与文件系统扫描顺序一致且可复现。

## 四、身份、时间与动作语义

- 身份保留 `source_id / adapter_id / run_id / episode_id / recording_segment_id / previous_recording_segment_id / native contract_version / episode 目录原始引用`；`backend_generation` 只出现在记录的命令 payload 里，因此以 `available / distinct_values / reason / scope` 单独表达，不假装它是每条记录的顶层字段。
- `episode_display_name_is_not_a_key: true`：同名 episode 出现在多个 run 下时返回 409 `episode_id_ambiguous` 并列出候选 run，必须带 `run_id` 才读，跨 run 不串读。
- 时间原义保留：`wall_utc`、`backend_monotonic_s`、`sim_time_s`、`measurement_time_s`、`arrival_time_s`、`clock_id`、`frame_id`、`persist_sequence` 等单位（s / ms / rad / m）逐字返回；`time_base` 只接受这些命名基，未知基（例如浏览器到达顺序）400 `time_base_unsupported`；游标声明 `line_index_is_not_a_clock` 与 `synchronized_across_streams: false`，本切片不建立跨流同步时钟。
- 动作分类按记录的事件类型分开：`recorded_target=actuator_reference`、`command_intent=requested/approved/rejected/dispatch/dispatched/expired/command_response`、`execution_feedback=feedback`、`recorded_state=feedback_initial`、`lifecycle=recording_start/recording_stop/episode_terminal`；读取器不把反馈当动作标签，也不把 Target 当 Actual。
- 无平台 sidecar 的 legacy 记录：`platform_association.known=false`、`validated_snapshot_ref=null`，原因 `legacy_native_record_without_platform_sidecar`；若记录目录内真的存在 `platform_session.json`，才按 sidecar 内容关联。

## 五、完整性分层（真实数据的关键发现）

`declared` 与 `integrity` 分开：`integrity.status` 只描述录制生命周期闭合（`complete` / `incomplete_terminal_recorded` / `finalize_failed_missing_tail` / `unknown`，沿用 CT-EPISODE 的 `integrity` 词表），`integrity.checksum_verification` 单独报告 tail 声明条数、本次重算文件、matched/mismatched 明细与 verdict，`integrity.not_verified` 明说未覆盖范围。

实测：所选 COMPLETE 记录 tail 声明 924 条校验和，本次重算的 `episode.json` **与声明不符**（记录器先写 tail 再定稿 `episode.json`，因此 tail 里存的是定稿前的摘要）；抽样 16 条真实记录全部呈现同一 `mismatch_present`，而生命周期状态仍为 `complete`。FAILED 记录 `recording_status=FAILED / audit_status=INCOMPLETE / termination_reason=RECORDING_FAILED`、tail 存在 → `incomplete_terminal_recorded`，仍然可读。两条都不被改写成"已验证完整"；`training_qualified=false` 也不阻止合格原始读取（`training_qualification.blocks_raw_read=false`）。因此"全 Episode 已验证完整"这一说法在本切片不成立，也未被使用。

## 六、面向未来 3D 回放的记录内身份

`recorded_model_identity` 取自该 run 的 `manifest.json`（`model_id/model_sha256/scene_id/map_mode/truth_access/clocks`）。与生产 pin 比对后：所选记录 model 与 scene 均 `match`（`3ca3d6d0a92a…`），状态为 `identity_verified_rendering_unverified`；不匹配或不可证时状态为 `restricted` 并给出具体原因。两种状态都带 `live_geometry_or_actual_may_be_applied: false`，即绝不把当前在线 geometry 或 Actual 套到历史 Episode。本节初稿曾把 `transforms.jsonl` 写成"记录内唯一的位姿来源"，该说法已在 M1.5b 更正：实测该流携带 `sample_id/stream_id/sensor_kind/clock_id/frame_id/measurement_time_s/arrival_time_s/source/metadata`，是带 frame/时钟标记的变换观测，不是逐 body 位姿序列，因此模型摘要相等仍不足以复原历史姿态。仍可提供真实元数据、事件与可用媒体。

## 七、受限读取与安全边界

路径先做 token 校验，再解析并强制落在该 Episode 的 `assets/` 子树内：绝对路径与含 `..` 的相对路径 400 `episode_asset_path_invalid`；软链指向别处 409 `episode_asset_escape`；`assets/` 之外不可达（`events.jsonl` 这类只能走 streams）；缺失 404 `episode_asset_missing`；未知后缀 415 `episode_asset_type_unsupported`；请求 `sha256` 不符在返回字节之前 409 拒绝；单文件上限 32 MiB。OpenAPI 中 5 条历史路径全部只有 `get`，没有代理 native 的 `POST /episodes/{id}/validate`、assessment、控制、RESET、录制、物理步进或任何重执行；`POST /api/v1/runs/{run_id}/stop` 仍是进程/记录管理，不是机器人 STOP。

## 八、服务器验证（全部在服务器执行）

| 检查 | 结果 |
|---|---|
| 历史切片 61 项断言（真实归档、一个候选进程、native 仅 GET） | 61/61 通过：来源身份、348 条与 native 列表一致、分页不重叠、`limit=1000` 422、FAILED 6 条、COMPLETE/FAILED 记录分层、events 12561 条实际计数、`event_seq` 与命名时间基窗口、control/transforms/persist/initial-snapshot 可读、超大观测行按实报告、303 张 rgb/depth/masks、资产摘要与 header、越界与摘要不符拒绝、legacy 关联未知、3D 状态跟随记录身份、平台详情 21 KB 对 native 20.9 MB、native 前后一致、归档聚合摘要前后不变 |
| 同一候选上的原统一能力回归 | `unified_candidate_check` 27/27 通过（geometry-2 + 23 资产、Map/Route、Session/`current`、STOP/end schema 与 availability 仍在） |
| 聚焦单测（隔离夹具/副本，不改原始 Episode） | 12 passed：COMPLETE/FAILED/缺 tail/坏行/缺流/跨 run 同名歧义/越界与软链/摘要不符/未知 sidecar/3D 两态/分页与时间基/OpenAPI 只读面 |
| 平台全量 | 140 passed / 3 failed |
| 历史失败基线（未跳过、不称全绿） | `test_catalog::test_catalog_loads_real_tasks`、`test_catalog::test_every_task_has_existing_evidence`、`test_migrate::test_manifest_sources_exist`；可核对链条 74/3 → 90/3 → 98/3 → 108/3 → 123/3 → 128/3 → 本轮 140/3，本轮新增 12 项全通过，未新增失败项 |
| 8792 | 检查工具与平台代码只发 GET；`capabilities` 仍不声明 stop/end 协议，health 前后完全一致。人工排障期间误发过一次 `POST …/validate`（后果与复核见开头说明），不属于交付代码路径 |
| 端口与服务 | 历史候选 18960（本轮新起，独立 SQLite `report/history-<ts>.sqlite3`，`existed_before=false`）；18959 统一候选、18949、18953、8792 全部保留；18954/18956 空闲 |

## 九、前端接线（本轮不改前端代码）

- 历史基址：`http://127.0.0.1:18960`（同一进程也提供既有能力；18959 保持不变，两者不互相替换）。
- 先列表再详情再按流分页：`GET /api/v1/episodes?limit=50&offset=0` → `GET /api/v1/episodes/{id}?run_id=…` → `…/streams/{stream}/records?offset=…`；不要用详情拉整条记录，也不要按数组下标当时间轴。
- 时间轴游标：以所选 `time_base`（如 `backend_monotonic_s`/`sim_time_s`）与 `event_seq` 为准；`cursor.line_index_is_not_a_clock` 与 `synchronized_across_streams=false` 必须显式呈现为"未同步"。
- 状态文案分开：`declared.*`（记录声明）、`integrity.status`（生命周期闭合）、`integrity.checksum_verification.verdict`（本切片重算结论）、`integrity.not_verified`。出现 `mismatch_present` 时说明"记录器自校验过期"，不得据此说数据损坏，也不得据此说已验证。
- 媒体：只用 `assets/{kind}/{file}`；带 `?sha256=` 可让服务端在返回前核验；`X-Episode-Asset-Sha256`/`X-Episode-Run-Id` 为响应头。
- 3D：`three_d_replay.status` 为 `restricted` 时不得挂在线 geometry/Actual 复原历史姿态；即便 `identity_verified_rendering_unverified`，也只表示模型身份可复用，渲染正确性未验证。
- 仍不存在的能力（前端不要假设）：跨流同步游标对齐、footprint/路径可达与动态执行资格、导航执行、新采集闭环、STOP/end 的真机可用性。

## 十、启动与复现

```bash
REL=$HOME/Desktop/uniRobotPlatform/releases/m1k-20261025T040435Z-platform
PYTHONPATH=$REL/backend/src setsid $PY tools/launch_unified_gateway.py --port 18960 \
  --native-url http://127.0.0.1:8792 --geometry-bundle $GEOM/geometry \
  --map-catalog $REL/backend/config/maps.catalog.json --maps-root $HOME/Desktop/mobileCar/var/maps \
  --history-source $REL/backend/config/mobilecar-history-source.json \
  --draft-db $REL/report/history-<ts>.sqlite3 --out-manifest $REPORT/history-startup.json
PYTHONPATH=$REL/backend/src $PY tools/episode_history_check.py --platform-url http://127.0.0.1:18960 \
  --native-url http://127.0.0.1:8792 --source-config $REL/backend/config/mobilecar-history-source.json \
  --complete-episode run_0104613ff7364ae78cf2f3946bd45f7b:episode_27bfed5427684795b361cd2ec21e9aa7 \
  --failed-episode run_1f6fb34853f94130aadedb8fa486705b:episode_879cf70489064a3b83bb15b5395a8341 \
  --out $REPORT/history-check.json
```

## 十一、冻结状态与边界

- 平台本轮新增/修改：`backend/src/unirobot/episodes.py`、`backend/config/mobilecar-history-source.json`、`backend/src/unirobot/api.py`（5 条 GET 路由与错误/缓存中间件）、`backend/src/unirobot/settings.py`（`UNIROBOT_HISTORY_SOURCE`、`UNIROBOT_EPISODE_ROOT`）、`backend/tools/launch_unified_gateway.py`（`--history-source`/`--episode-root` + 启动清单 history 块 + `tools` 纳入源码摘要）、`backend/tools/episode_history_check.py`、`backend/tests/test_episodes.py`。平台改动本地提交、**不推送**。
- native：未提交、未部署、未重启；`ReplayReader`/Recorder 格式只被读取和引用。逐文件复核只覆盖 696 个 `episode.json`/`episode_complete.json`（以及 M1.5b 追加的覆盖集合），本节初稿提到的 `events.jsonl` 等并未事前快照，不属证明范围。一次人工误发的 `POST …/validate` 让 native 自己重写了一条记录的派生 `quality_report.json`，事实与复核范围见开头说明。
- 未验证：同步 3D 回放渲染、真机停车与录制闭环、新采集链路、G1/G4A2 与 a5/drvfix 选择、正式 M1.5/M1 验收。本 Goal 完成只表示真实历史 reader 首个切片可用。
