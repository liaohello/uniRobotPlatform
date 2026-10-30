# M1.5j 证据册｜新 Recorder 产物的平台历史 reader 重载

分类：**test-only**。真实 Recorder 落盘、真实 unirobot 应用、真实 HTTP；native backend 是 mock（无 MuJoCo、无渲染、无物理步进），媒体与事件输入是 synthetic（非真人、非真实传感器测量）。运行数据（`recordings/`、SQLite、日志原件）保留在服务器，证据册只保存可复核的报告与摘要。

- 新 run：`run_5f972f067e014b8596d38c20f5f6042c`
- 新 episode：`episode_7f432849f34940ad908513d15a2098ed`
- 隔离 root：`/home/liaozhengyan/Desktop/uniRobotPlatform/scratch/m1j-new-recording-20261030T1144Z`
- 生成器（未跟踪原件，未修改、未提交）：`backend/tools/new_recording_roundtrip.py`，SHA-256 `b1d5c08a6820438ce0c5391239a50bc390e4551a20e4554497761ba381be63f2`
- 冻结副本：`.../input/new_recording_roundtrip.py`，运行前后 SHA-256 均为 `b1d5c08a…`；无补丁
- 验收工具：`backend/tools/new_recording_readback_check.py`，SHA-256 `60d59c5e7205f5ee57a2b62ea455df7087093be620232602f3eb833df28ba084`
- native release：`m1h-20261024T152235Z-native`（未修改）
- 平台 reader 源码：冻结 `m1i-20261030T035643Z-platform`，50 文件聚合 `107f897ddfe2485fb116eba8c6bbdef32258c4c2ab483d80f27a01e1cf803d59`（与 18985 候选启动清单一致）

## 1. Recorder 实际写出

| 项 | 事实 |
|---|---|
| events | 18 条、9 类：`recording_start` 1、`feedback_initial` 1、`actuator_reference` 4、`feedback` 4、`rgbd_capture_timing` 2、`requested` 2、`approved` 2、`recording_stop` 1、`episode_terminal` 1 |
| samples | 2 个（`synthetic_frame_00/01`），RGB/depth 各 2 个媒体字节；persist 2 行 |
| media | `assets/rgb/synthetic_frame_00.png` SHA `dd9756d348f1…`、`synthetic_frame_01.png` `a1d7b2b8d7a9…`；depth `db57f174d2da…`、`72fefb1c2633…`（与注入字节逐字节相等） |
| transforms | 2 条，按 `sample_id` 覆盖两个 sample |
| persist | 2 行，含 `persist_sequence`、`capture_backend_monotonic_s`、`capture_sim_time_s`、`persist_backend_monotonic_s`、`rgb_uri`/`depth_uri` |
| 终态 | `episode_terminal` 1 条；`episode.json` `recording_status=COMPLETE`、`audit_status=COMPLETE`、`termination_reason=OPERATOR_FINISHED`；tail 与 end receipt 的 SHA 相符 |
| 生成器自检 | 13/13 通过；writer 进程已退出，native 端口 18980 关闭 |

写入文件：`manifest.json`、`episode.json`、`episode_complete.json`、`events.jsonl`、`control.jsonl`、`commands.jsonl`、`transforms.jsonl`、`observations/{index,rgb,depth,persist}.jsonl`、`assets/{rgb,depth}/*`、`initial_snapshot.json`、`quality_report.json`；另有 quality 管线的 `g2a/run_…/*.g2a_quality.json` 与 eligibility sidecar，均在隔离 root 内。

## 2. 当前平台 reader 回读

writer 停止后，以 test-only 历史来源（`source_id=testonly-new-recording-run_5f972f…`）和独立 SQLite 启动当前 reader，经真实 HTTP GET 读取：

- 列表、详情、流目录；
- 有界 events / persist / transforms records；
- frames（含 `include_time_quality` 与 `include_action_basis`）；
- RGB/depth 媒体资产；
- 缺媒体隔离副本诊断。

结果：**46/46 检查通过，22 次请求全部为 GET**（`phase2.json.requests`）。

关键逐值核对：

| 检查 | 结果 |
|---|---|
| 列表/详情身份 | run/episode 与目录名一致；`recording_root_resolved` 等于隔离 root |
| 事件 | 18 条，词表与 writer 的 9 类逐类相等；每条带原始 `line_index` |
| persist | 2 行，`sample_id`、`persist_sequence`、三个采集时间字段、`rgb_uri`/`depth_uri` 与 writer 行完全一致 |
| transforms | 2 条，`sample_id` 覆盖两个 sample |
| frames | 2 帧按追加顺序；image 2/2、camera_transform 1、capture_timing 1、state_feedback 1；`linkage_status=matched` |
| time_quality | 2 锚点、EOF、`every_line_of_the_anchor_file_is_decided=true`、`undecidable_total=0`、`covers_whole_episode=true`；三基各 2 个数值；A 合格、`displayed_sequence_may_have_gaps=false`；逐基 B 合格 |
| action_basis | 18 条事件全部计入：Actual `feedback` 4、Target `actuator_reference` 4、`feedback_initial` 1、capture timing 2、lifecycle 3、`requested` 2、`approved` 2；`rejected`/`dispatch` 未记录；`frame_association` 每帧 feedback/Target 各 1 候选；`dispatch` 0；`clock_parity`/`recorded_target`/`rejected_requests` 规则存在 |
| 媒体 | 4 个资产逐字节等于注入值；`X-Episode-Asset-Sha256` 相符；错误 `sha256` 返回 409 |
| 控制来源 | 只在 payload 内记录（`mobilecar_application`/`scripted`/`m1j-synthetic-driver`），无 takeover 事件，不默认 Human |
| 必需流 | writer 自报 7 个 sensor streams；测试期望仅 rgb/depth；run manifest 无 stream 声明 → `unknown` |

## 3. 独立与只读

- writer 停止后 native 端口 18980 关闭；reader 仍能返回列表、详情、frames、媒体与 time_quality/action_basis。
- reader 指向已停止的 native：`/api/v1/mobilecar/scene` 返回 503 `native_offline`，历史读取仍为 200。
- 未配置 geometry bundle：`robot-state` 返回 503 `history_model_bundle_not_configured`，没有用在线 geometry 或 live Actual 替代。
- 读取前后隔离 root 的 21 个文件摘要完全一致（`digest.equal=true`）；没有重写 `quality_report.json`、tail 或媒体。
- 缺媒体案例：在独立副本删除 `assets/depth/synthetic_frame_00.npy` 后，详情仍可读（200），该资产返回 404 `episode_asset_missing`，对应帧的 depth `availability=absent`；成功产物未被修改。

## 4. 保留并解释的异常

1. **tail 对 `episode.json` 的校验和不符**：tail 声明 `e89f6a2a…`，实际最终 `episode.json` 为 `e3bba06b…`；reader 以 `integrity.checksum_verification.verdict=mismatch_present` 报告，不重算改写、不把声明当已验证。原因是 Recorder 先写 tail 快照，随后才把 `recording_status/ended_wall_utc` 落到 `episode.json`；本轮**没有修改任何文件**来消除该差异。
2. **quality_report 与 episode.json 的声明分层**：`quality_report.json` 为 `audit_status=INCOMPLETE`、`passed=false`，错误为 `observation stream rgbd depth lacks an explicit valid mask`（合成输入未提供 valid mask）；`episode.json` 仍声明 `COMPLETE/COMPLETE`。两者分列，不互相覆盖，也不据此宣称录制质量合格。
3. **synthetic 时间戳的构造差异**：生成器把 `capture_backend_monotonic_s` 设为未来 0.1/0.3 s，但立即发布，故 persist 行出现负的 `capture_to_persist_ms`（−78.8 / −273.5 ms）。这是 synthetic 输入的构造结果，不是传感器测量；reader 原样保留，B 资格只按各时间基自身是否单调/数值完整判定，不据此声称采集与落盘顺序成立。
4. **模型身份缺失**：run manifest 的 `model_id/model_sha256/scene_id` 均为 null；`three_d_replay` 为 restricted/unknown，未套在线 geometry。
5. **命令事件**：`requested`/`approved` 是 test-only session 控制请求（payload 内 `command_type=stop`、`operator_kind=scripted`），`control_tick_id` 为 null，不挂帧；`dispatch`/`rejected` 未记录，不推断执行结果。

## 5. 回归

- 聚焦：`backend/tests/test_frames.py` + `test_episodes.py` → **71 passed**。
- 全量：**205 passed / 3 failed**，三项历史布局失败具名保留：`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`。不称全绿。
- 测试在服务器上对冻结 release 的隔离 `/tmp` 副本执行，未写入 release 或真实归档。

## 6. 记账与边界

- **测试写请求**：生成器对 test-only 执行网关（18981）发出 1 次 GET + 7 次 POST（draft/validate/session/start/begin/stop/end），全部是测试生命周期，不经生产网关，不触达 8792。
- **reader 读取**：22 次 GET，全部指向 test-only reader（18987/18988）。
- **生产只读探测**：本轮未向 8792 发请求；8792 未被写入、RESET、STOP、begin/end、重启或替换。
- 18985/18983/18979/18977 与前端预览保留；未修改 `frontend/`、原 native 工作树、生产 pin、recipe 或真实归档；未进入点云、标定、导航或训练。
- 测试端口 18980/18981/18987/18988 均已关闭；无 probe/generator/reader 残留进程。

## 7. 文件

- `phase1.json`：生成器证据（writer 检查、samples、persist、事件计数、tail/manifest/quality、inventory）
- `phase2.json`：reader 证据（46 项检查、22 次 GET、逐帧/时间/动作/媒体、digest、缺媒体诊断）
- `execution-gateway.json`、`reader-gateway.json`、`missing-reader-gateway.json`：test-only 网关启动清单
- `test-recipe-summary.json`、`frozen-inputs.json`：test recipe 与冻结输入的来源、SHA、无补丁
- `pytest-focused.txt`、`pytest-full.txt`、`generator.log`、`verify.log`

## 8. 复现要点（服务器）

1. 冻结生成器与工具：把 `backend/tools/new_recording_roundtrip.py` 复制到隔离 `input/`，记录前后 SHA；把 `backend/tools/new_recording_readback_check.py` 放到隔离 `harness/`。不要修改或提交原未跟踪生成器。
2. 平台源码使用冻结 release 的**副本**（含 `src`、`config`、`tools`），并在环境设置 `UNIROBOT_REPO_ROOT=<隔离平台根>`；否则 `unirobot.settings` 会因副本缺少 `docs/specs/catalog.json` 回退到 cwd。
3. 探针 native（仅用于构建 test recipe）用 native release 解释器启动 18980；`build-recipe` 需要同时设置 `UNIROBOT_MOCK_NATIVE_URL=http://127.0.0.1:18980` 和 `UNIROBOT_MOCK_TEST_DB=<隔离 db>`，因为 `mock_native_protocol_app` 导入时会构建默认 app。构建后立即停探针。
4. 用 `serve` 在 18981 启动 test-only 执行网关（test recipe、隔离历史来源、隔离 root、独立 SQLite），再运行冻结生成器；writer 停止后停网关。
5. writer 停止后运行 `verify`（18987 reader、18988 缺媒体 reader、独立 SQLite），检查 `phase2.json` 的 46 项与 22 次 GET；结束后确认四个测试端口关闭、18985/18983/18979/18977 仍在监听。

## 9. 不主张

本轮只证明：**无物理的新 Recorder 产物可以通过当前平台 reader 重载读取**。不证明生产部署、真人采集、真实传感器测量、录制质量合格、跨流同步、统一历史游标、动作界面接线或正式 M1 验收。
