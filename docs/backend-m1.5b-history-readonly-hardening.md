# M1.5b｜历史 reader 只读整改、根目录隔离与可复现发布

2026-10-25 · 范围：把 M1.5a 历史只读切片整改成**执行上真的只读、路径上真的受限、发布上真的可复现**，并修正上一轮超出证据的表述。

**本轮完成的是 reader 整改与可复现交付；不表示历史归档已全部验证、同步回放或 M1 验收通过。** 未修改 `frontend/`；native 未提交、未部署、未重启；未修补任何历史 tail；未执行真实录制、运动、RESET 或训练。

## 一、结论

| 项 | 状态 |
|---|---|
| 只读执行入口收敛 | 新增 `backend/tools/native_get_probe.py`：只有 `get/json` 方法，没有 method/body/data 参数可用；`episode_history_check.py`/`history_replay_facts.py` 全部经它发请求，逐条写入 JSONL 日志。冻结候选实测 **51 次请求，methods 只含 `GET`，non_get 为空**（`get-probe-log.jsonl`/`get-probe-log.json`）；事实表提取另有 8 次 GET |
| 违规记录保留并纠正表述 | 上一轮人工误发的 `POST …/validate` 记录与 native 现有派生报告都**保留原样**（未覆盖、未删除、未猜测回滚）；所有“原始文件全部未变/全程仅 GET”式表述已按实测范围收窄（见第五节） |
| 覆盖集合先记录后复核 | 新增 `coverage-digests.json`：检查开始前先记录**本次实际会打开的 946 个文件**摘要（两条代表记录的 manifest/episode/tail/六个流/initial_snapshot/quality_report/assets 全集 + 全归档 696 个身份文件），跑完复核**同一集合**，`drift=[]`，并写明未覆盖范围；696 聚合值 `60c0c696…` 只被称作它所覆盖的两个文件名，不再当整库不变性证明 |
| 统一受限路径解析 | 一个最小公共检查（`_real` + `confined_within`）覆盖 root、run 目录、`episodes` 目录、Episode 目录、run manifest、episode/tail/sidecar/assessments、固定流与 `assets/`；索引阶段拒绝软链目录，读取阶段每次重新解析（缓存索引不能绕过），软链/越界分别返回 `history_path_escape`、`episode_path_escape`、`episode_asset_escape` |
| `event_seq` 过滤修复 | 启用区间过滤时，缺失、非整数与 bool 序号一律排除并计数（`filtering.event_seq_range.excluded_without_valid_event_seq` + `anomalies[]` 带 `line_index/reason/value_type`），不补造序号；合法数据的 `offset`/`next_offset`/`has_more`/原始顺序与身份语义不变 |
| 报告与冻结产物绑定 | 新增 `backend/tools/source_digest.py`（唯一实现）；启动清单记录 roots 与逐文件摘要，两个检查工具都用运行中的树**重算并断言相等**：`running tree equals the frozen startup manifest` 与 `candidate bytes equal the frozen startup manifest`；历史工具还断言来源配置字节摘要等于清单值 |
| 新候选不替换既有服务 | 冻结候选 `m1p-20261025T053030Z-platform` 常驻 `http://127.0.0.1:18964`，同进程继续提供 geometry-2、Map/Route、Session/`current`、STOP/end 契约（28/28 回归，含新的绑定断言）；18960（M1.5a）、18959（M1.4b）、18949、18953、8792 全部保留；独立新库 `history-053031.sqlite3`（`existed_before=false`） |
| 服务器验证 | 冻结发布内 19 项聚焦全通过；平台全量 **147 passed / 3 failed**（历史三项不变，链条 …→128/3 → 140/3 → 147/3）；真实记录读取检查 **69/69** |

## 二、冻结链与身份闭合（不倒填历史）

| release | 状态 | 启动清单聚合 | 报告 |
|---|---|---|---|
| `m1k-20261025T040435Z-platform` | M1.5a 首片（保留原样） | 清单内 `58a7373422…`；交付文档当时误引 `e86a709f…`（该值来自修复前的一次启动，未与冻结树闭合） | 61/61 与 27/27 报告保留，只描述该版本 |
| `m1l-20261025T052446Z-platform` | 整改期测试构建（未作为交付候选，不跑交付报告） | 未生成候选清单 | — |
| `m1m-20261025T052644Z-platform` | 中间冻结（发现 `history_replay_facts.py` 缺 `import hashlib` 后弃用） | `bc33483d7f24e45e…`（45 文件） | 69/69、28/28 留在服务器报告目录，不引用为本轮结论 |
| `m1n-20261025T052747Z-platform` | 中间冻结（事实提取媒体样本选择缺陷后弃用） | `bb84b1ef070694b0…`（45 文件） | 同上，保留不删 |
| **`m1p-20261025T053030Z-platform`** | **本轮交付候选，常驻 18964** | **`4090935b4c45c900ec9b2eed62372bfc02ad5b0464f21fcf9da6c76c9fa89715`**（45 文件，roots `src/unirobot`+`config`+`tools`）；启动清单 sha256 `832bf518274600a9c64b6a2dd55b83c70246d6ecb6c79c48042e80e965629f85` | 本报告所有数字来自这一代产物；清单、运行字节、工具、报告与提交互相对应 |

来源配置 `backend/config/mobilecar-history-source.json` 字节摘要 `fbfcc6a69edb9472…`，由启动清单记录、由历史检查工具重算断言。旧 `58a737…`/`e86a709f…` 值不倒填、不改写。

## 三、只读执行规则（现在由构造保证）

1. 历史验证只允许两类动作：平台 GET，以及归档文件的只读打开。需要 native 状态时用 `native_get_probe.GetProbe`（无 method/body 形参），人工排障同样只能用它；真实 native 的 `validate`/`assessment` POST 与临时写探测一律禁止。
2. 需要重算派生结论时只在隔离副本上做：本轮的损坏/缺文件/软链/重复 ID 案例全部由 `tmp_path` 夹具构造（`tests/test_episodes.py`），未改真实归档、未为造案例启动录制。
3. `episode_history_check.py` 每次运行写 GET 日志与摘要，报告内含 `requests.methods == ["GET"]` 与 `non_get == []` 断言；日志本身就是"只读执行记录"交付物。

## 四、路径边界与分页语义

解析规则（`episodes.py`）：`_real()` 取完整解析路径，`confined_within(boundary_real, target)` 要求解析结果落在边界内；`EpisodeLocation.checked()` 是**唯一**取文件的方式，边界为 Episode 解析目录（`assets/` 子树再收紧到 assets）；`EpisodeLocation.__init__` 拒绝软链或越界的 Episode 目录（`history_path_escape`），`_run_manifest` 拒绝软链 manifest，索引只接受非软链且被包含的 run/`episodes`/Episode 目录。缓存索引不保存绝对路径，`location()` 每次调用重新解析，因此"索引之后再动目录"无法绕过读取时检查（回归覆盖）。媒体清单在 `assets/` 目录本身是软链时按 `episode_asset_escape` 拒绝，并逐文件排除并计数（`symlink_or_escape_excluded`/`excluded_count`）。

分页与游标：`offset` 仍是行序号（native 追加顺序），`next_offset = 最后一条返回行的 line_index + 1`，`has_more` 依据实际扫描行数；`cursor.line_index_is_not_a_clock` 与 `time.synchronized_across_streams=false` 不变。区间过滤启用时才做 `event_seq` 合格性判定，`bool` 因是 `int` 子类被显式拒；`observations-index`/`observations-persist` 合法地没有 `event_seq`（原生 `SensorObservation` 无该字段，persist 用 `persist_sequence`），因此对它们设区间会得到空页 + 明确计数，而不是被当成损坏数据。`wall_utc` 是日历字符串：数值边界直接 400 `time_base_not_numeric`，不再拿字符串比较；未知基仍 400 `time_base_unsupported`。`limit` 上限 200（实测 422）。

## 五、对上一轮表述的更正

1. **不再说**"所有原始文件未变""全程仅 GET"。事实是：native 自身因那次误发的 `POST …/validate` 重写了该记录派生的 `quality_report.json`（mtime 2026-10-25 12:20:38，摘要 `53314c847d17f38d…`；其重写前摘要从未快照，**不能声称内容未变，也不猜测回滚**）；被逐文件证明未变的是 696 个 `episode.json`/`episode_complete.json`（聚合 `60c0c696…`）与本轮额外覆盖的 946 文件集合（`drift=[]`）。其余文件（其他 Episode 的流文件、资产等）在违规时点没有前置摘要，属**未覆盖**。
2. **更正 `transforms.jsonl` 语义**：M1.5a 记录把 transforms 说成"记录内唯一的位姿来源"。实测该流的记录字段是 `sample_id/stream_id/sensor_kind/clock_id/frame_id/measurement_time_s/arrival_time_s/source/metadata`，即带 frame/时钟标记的变换观测，**不是逐 body 位姿序列**；因此"模型身份相等"也不等于可复原历史姿态。3D 状态维持 `identity_verified_rendering_unverified` 时也必须按此理解。
3. 上一轮 61/61 与 27/27 报告保留为 **m1k 版本证据**，不与本轮 69/69、28/28 拼接成"一直全绿"。

## 六、面向后续回放的最小事实表（真实记录，实测）

代表记录 `run_0104613ff7364ae78cf2f3946bd45f7b / episode_27bfed5427684795b361cd2ec21e9aa7`（COMPLETE/COMPLETE，tail 声明 924 条摘要）：

| 流（文件） | 实测时间基与序列 | 单位 / frame | 身份与关联 |
|---|---|---|---|
| `events.jsonl` | `wall_utc`（ISO Z）、`backend_monotonic_s`、`sim_time_s`、`event_seq`（1 起）、`control_tick_id`、`command_id`、`plan_id`、`task_phase` | s；无 frame 字段 | `run_id/episode_id/contract_version` 每条都有；Actual 用 `feedback_initial`/`feedback`，Target 用 `actuator_reference`，意图用 `requested/…` |
| `control.jsonl` | 同上（首条含 `event_seq=3/4/5`、`control_tick_id`） | s | `command_id` 在这批为 `null`，如实返回 |
| `commands.jsonl` | `event_seq` | — | 命令派发记录 |
| `transforms.jsonl` | `measurement_time_s`/`arrival_time_s` + `clock_id=backend_monotonic` | `frame_id=rgbd_optical` | `sample_id/stream_id/source`；**不是 body 位姿序列**（第五节第 2 条） |
| `observations/index.jsonl` | `measurement_time_s`、`arrival_time_s`、可选 `capture_sim_time_s/capture_backend_monotonic_s/capture_control_tick_id`、`clock_id` | `frame_id=base_link`（lidar）等；`quality=simulated_nominal/simulated_raycast`；`source=mujoco_mj_ray/mujoco_sensor` | `stream_id/sample_id/sensor_kind/feedback_sample_id/value`，`metadata` 携带 `angular_frame_note/publish_period_s/source_sample_period_s/interface_profile` 等 |
| `observations/persist.jsonl` | `persist_sequence`、`persist_backend_monotonic_s`、`arrival_to_persist_ms`、`capture_to_persist_ms`、`capture_sim_time_s/capture_backend_monotonic_s/capture_control_tick_id` | ms/s 混用（按字段名）；`interface_profile=g2a-1.0` | **媒体路径关联实测在此**：`sample_id=rgbd_e3213e6c…`，`rgb_uri=assets/rgb/rgbd_e3213e6c…_rgb.png`、`depth_uri=assets/depth/…_depth_m.npy`、`valid_mask_uri=assets/masks/…_valid.png`，`feedback_sample_id=joint_feedback_000006551`、`capture_control_tick_id=tick_000006551`、`profile_id=g2a-rgbd-5hz-original`、`profile_sha256=9473171d7460…`、`kinds=[rgb,depth]` |

历史模型身份（run manifest，实测）：`model_id=landerpi_mecanum_dynamic_5dof_3ca3d6d0a92a`、`model_sha256=3ca3d6d0a92a48bb…`、`scene_id=mobile_pick`、`map_mode=unavailable`、`clocks=[sim, backend_monotonic, device, wall_utc]`、`truth_access=GT_DEBUG_SEPARATE_FROM_DEFAULT_OBSERVATION`；与生产 pin 相等 → `three_d_replay.model_match=match`、`status=identity_verified_rendering_unverified`，且 `live_geometry_or_actual_may_be_applied=false`。

**仍未证明**：跨流时间对齐与统一回放游标；measurement/arrival 数值接近不等于同一时刻；模型摘要相等不等于 3D 渲染通过；逐 body 位姿可否从现有流恢复；本轮也不做同步引擎与回放 UI。

## 七、错误样例（冻结候选实测）

| 情况 | 状态与 code |
|---|---|
| 缺失 / 字符串 / bool `event_seq` 且启用区间 | 只返回合法整数序号；`filtering.event_seq_range.excluded_without_valid_event_seq=3`，`anomalies[].value_type ∈ {NoneType,str,bool}` |
| `time_base=wall_utc` + 数值边界 | 400 `time_base_not_numeric`（附 `numeric_bases`） |
| 未知时间基 | 400 `time_base_unsupported` |
| `limit=1000` | 422 |
| `episode.json`/`manifest.json` 为软链、Episode 目录为软链 | 409 `episode_path_escape` / `history_path_escape` |
| `assets/` 目录软链或文件软链指向别处 | 409 `episode_asset_escape` |
| 流不存在 / 流名不支持 / 资产缺失 / 后缀不支持 / 摘要不符 | 404 `episode_stream_unavailable`、404 `episode_stream_unsupported`、404 `episode_asset_missing`、415 `episode_asset_type_unsupported`、409 `episode_asset_digest_mismatch` |

## 八、前端迁移说明（不改前端代码）

- 新历史基址 `http://127.0.0.1:18964`；`http://127.0.0.1:18960`（M1.5a 候选）与 `http://127.0.0.1:18959`（M1.4b 统一候选）继续存活，不做互换或"新地址即旧地址"的推断。用前用 `ss -ltnp sport = :<端口>` 确认存活。
- 分页语义未变：`offset` 是行序号，`next_offset` 可继续传；新增 `filtering.event_seq_range`（区间过滤时被排除/计数）与 `time.numeric_time_bases`。区间过滤下空页要按"该流合法地没有 event_seq"处理，不是加载失败。
- `time_base=wall_utc` 不再接受数值边界：请改用 `backend_monotonic_s`/`sim_time_s`/`measurement_time_s`/`arrival_time_s`，或自行做日历解析。
- 媒体关联以记录内字段为准：`observations-persist` 的 `rgb_uri/depth_uri/valid_mask_uri` 与 `sample_id/feedback_sample_id/capture_*`；index 记录的 `asset_uri` 可能为 `null`，此时不要猜测文件名。
- `integrity.checksum_verification.verdict=mismatch_present` 的展示文案是"记录器自校验过期"，不得渲染成数据损坏，也不得渲染成已验证；`not_verified` 列表要如实呈现。
- 3D：`transforms.jsonl` 不是逐 body 位姿；在没有额外证明之前，历史姿态回放不得用在线 Actual/geometry 顶替。

## 九、复现

```bash
REL=$HOME/Desktop/uniRobotPlatform/releases/m1p-20261025T053030Z-platform
R=$HOME/Desktop/uniRobotPlatform/var/reports/m1p-20261025T053030Z-platform
cd $REL/backend && PYTHONPATH=$REL/backend/src setsid $PY tools/launch_unified_gateway.py --port 18964 \
  --native-url http://127.0.0.1:8792 --geometry-bundle <已核验 geometry 目录> \
  --map-catalog $REL/backend/config/maps.catalog.json --maps-root $HOME/Desktop/mobileCar/var/maps \
  --history-source $REL/backend/config/mobilecar-history-source.json \
  --draft-db $REL/report/history-<ts>.sqlite3 --out-manifest $R/history-startup.json
PYTHONPATH=src $PY tools/episode_history_check.py --platform-url http://127.0.0.1:18964 \
  --native-url http://127.0.0.1:8792 --source-config config/mobilecar-history-source.json \
  --startup-manifest $R/history-startup.json --probe-log $R/get-probe-log.jsonl \
  --coverage-out $R/coverage-digests.json --complete-episode <run:episode> --failed-episode <run:episode> \
  --out $R/history-check.json
PYTHONPATH=src $PY tools/unified_candidate_check.py --platform-url http://127.0.0.1:18964 ... --startup-manifest $R/history-startup.json
PYTHONPATH=src $PY tools/history_replay_facts.py --platform-url http://127.0.0.1:18964 ... --startup-manifest $R/history-startup.json
PYTHONPATH=src $PY -m pytest tests/test_episodes.py -q
```

## 十、边界与未覆盖

- 未覆盖：其他 Episode 在违规时点之前没有前置摘要，因此"未变"只对已记录集合成立；同步回放与统一游标；逐 body 位姿可否重建；`quality_report.json` 重写前内容比对；归档全量逐记录校验；训练资格。
- 未做：任何 native 写、8792 变更、物理运动/录制/RESET/训练、`frontend/` 改动、native 提交/推送、生产 pin 变更（`a0109804…911c` 与 `mobilecar.g1.teleop` rev 3 未动）。
- 服务器实测的 native 状态：`run_9c88e3e3…/gen 1/episode_43c22f95…`、`recording_status=IDLE`、capabilities 仍不声明 stop/end 协议，检查前后一致。
- 本轮完成只表示 reader 整改与可复现交付完成；不表示历史归档已全部验证、同步回放可用或 M1.5/M1 验收通过。
