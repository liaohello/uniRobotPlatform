# M1.5j｜新 Recorder 产物的平台历史 reader 重载验收

日期：2026-10-30（America/Los_Angeles）· 分支 `codex/backend-m1-services` · 基线 `8850bca` · 阅读源码：冻结 `m1i-20261030T035643Z-platform`（18985）
证据册：[docs/evidence/m1.5j-new-recording-readback/](evidence/m1.5j-new-recording-readback/README.md)

## 0. 一句话结论

用未跟踪的 `new_recording_roundtrip.py` 冻结副本，在授权服务器上以 test-only recipe、mock backend、隔离 recording root 和独立 SQLite 生成了一个**全新的** Episode（`run_5f972f067e014b8596d38c20f5f6042c / episode_7f432849f34940ad908513d15a2098ed`），并由**当前平台 reader** 经真实 HTTP GET 重载：**46/46 检查通过，22 次 reader 请求全为 GET**。writer 停止后 reader 仍可读取；读取前后隔离 root 的 21 个文件摘要一致；缺媒体副本返回 `episode_asset_missing` 且帧侧报 `availability=absent`。**本轮没有修改平台 reader 源码**，只新增了 test-only 验收工具。

## 1. 生成器复用与冻结

- 原未跟踪文件：`backend/tools/new_recording_roundtrip.py`，审阅后 SHA-256 `b1d5c08a6820438ce0c5391239a50bc390e4551a20e4554497761ba381be63f2`。
- 复制到服务器隔离目录 `.../input/new_recording_roundtrip.py` 作为外部测试输入；复制前后、运行前后 SHA-256 均不变；**未修改、未删除、未加入提交**。
- 未另写采集器。为生成 test recipe，仅在隔离目录写了一个不记录任何内容的探针 native 启动脚本（SHA `5f41ca4a…`），并在 writer 启动前停止。
- 生成器实际参数按其 `--help`/源码契约使用：`--native-release m1h-20261024T152235Z-native --platform-url http://127.0.0.1:18981 --root <隔离 root> --port 18980 --out <隔离 root>/phase1.json`。未猜选项。

## 2. 新产物（真实 Recorder 落盘）

| 项 | 事实 |
|---|---|
| run / episode | `run_5f972f067e014b8596d38c20f5f6042c` / `episode_7f432849f34940ad908513d15a2098ed` |
| 事件 | 18 条、9 类；`feedback` 4、`actuator_reference` 4、`rgbd_capture_timing` 2、`recording_start`/`feedback_initial`/`recording_stop`/`episode_terminal` 各 1、`requested`/`approved` 各 2 |
| 观察 | 2 个 sample；RGB/depth 各 2 个文件；`observations/persist.jsonl` 2 行；`transforms.jsonl` 2 条 |
| 媒体 | 4 个资产逐字节等于注入的 PNG/NPY；persist 的 `rgb_uri`/`depth_uri` 指向 `assets/…` |
| 终态 | `episode_terminal` 1；`episode.json` 声明 `COMPLETE/COMPLETE`；tail 与 end receipt 的 SHA 相符 |
| 生成器自检 | 13/13；writer 进程退出；native 端口关闭 |

写入内容全部在隔离 root 的 `recordings/run_5f972f…/`；`g2a/run_5f972f…/*.g2a_quality.json` 是同一 Recorder 的 quality sidecar，不是第二个 Episode。

## 3. 平台 reader 重载

为隔离 root 建立 test-only 历史来源（`source_id=testonly-new-recording-run_5f972f…`），在 writer 停止后启动冻结平台源码的隔离副本（50 文件聚合 `107f897ddfe2485f…`，与 18985 启动清单一致），使用独立 SQLite，经真实 HTTP GET 读取列表、详情、流目录、有界 records、frames、媒体、`include_time_quality` 与 `include_action_basis`。

**46/46 检查通过**（`phase2.json`），逐值要点：

- 列表/详情：run/episode 与目录名一致；`recording_root_resolved` 等于隔离 root；`episode_json_readable`/`tail_json_readable` 为 true。
- 事件：18 条逐类与 writer 相等，每条带原始 `line_index`。
- persist：2 行逐键相等（`sample_id`、`persist_sequence`、三个采集时间字段、`rgb_uri`/`depth_uri`）。
- frames：2 帧追加顺序；image 2/2、camera_transform 1、capture_timing 1、state_feedback 1；`linkage_status=matched`；sample/tick 与 writer 一致。
- time_quality：本 Episode 只有 2 个锚点；`reached_end_of_file=true`、`every_line_of_the_anchor_file_is_decided=true`、`undecidable_total=0`、`covers_whole_episode=true`；三基各 2 个数值；A 合格且无 gap 声明；逐基 B 合格。
- action_basis：18 条全部计入；Actual/Target/意图/受理/lifecycle 分域；`rejected`/`dispatch` 未记录；每帧 feedback 与 Target 各 1 候选；`clock_parity`/`recorded_target`/`rejected_requests` 规则存在；控制来源只在 payload 内，不默认 Human。
- 媒体：4/4 资产 SHA 与注入值相等；错误 `sha256` 409。
- 必需流：writer 自报 7 个 sensor streams，测试期望 only rgb/depth，run manifest 无 stream 字段 → `unknown`；没有把测试期望写入 manifest。

## 4. 独立与只读

- writer 停止后 native 端口关闭；reader 仍返回 200。reader 指向已停止 native 时 `/mobilecar/scene` 为 503 `native_offline`，历史读取不受影响。
- 无 geometry bundle：`robot-state` 为 503 `history_model_bundle_not_configured`；不套在线 geometry/live Actual。
- 读取前后隔离 root **21 个文件摘要一致**（`digest.equal=true`），没有自动 validate/assessment 或重写。
- 缺媒体副本：删除 `assets/depth/synthetic_frame_00.npy` 后，详情 200、资产 404 `episode_asset_missing`、帧 depth `availability=absent`；成功产物未被修改。

## 5. 保留并解释的异常

1. **tail 对 `episode.json` 的校验和不符**：tail 声明 `e89f6a2a…`，最终 `episode.json` 为 `e3bba06b…`；reader 报 `integrity.checksum_verification.verdict=mismatch_present`，没有改写文件或把声明当已验证。原因是 Recorder 先写 tail 快照、随后才落最终 `recording_status/ended_wall_utc`。
2. **quality_report 与 episode.json 分层**：`quality_report.json` 为 `audit_status=INCOMPLETE`、`passed=false`（`depth lacks an explicit valid mask`，合成输入未提供 valid mask）；`episode.json` 仍声明 `COMPLETE/COMPLETE`。两者分列，不据此宣称录制质量合格。
3. **synthetic 时间戳构造**：生成器把 `capture_backend_monotonic_s` 放在未来 0.1/0.3 s 后立即发布，persist 行出现负的 `capture_to_persist_ms`（−78.8/−273.5 ms）。这是 synthetic 输入构造，不是传感器测量；reader 原样保留，B 资格只按各时间基自身是否单调/数值完整判定，不据此声明采集与落盘顺序成立。
4. **模型身份缺失**：manifest `model_id/model_sha256/scene_id` 为 null；`three_d_replay` restricted/unknown；未套在线 geometry。
5. **命令事件**：`requested`/`approved` 是 test-only session 控制请求（`command_type=stop`、`operator_kind=scripted`），`control_tick_id` null，不挂帧；`dispatch`/`rejected` 未记录，不推断执行结果。

## 6. 验证

- 聚焦：`test_frames.py` + `test_episodes.py` → **71 passed**。
- 全量：**205 passed / 3 failed**，三项历史布局失败具名保留：`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`。不称全绿。
- 全部测试在服务器上对冻结 release 的隔离 `/tmp` 副本执行；未写 release 或真实归档。

## 7. 前端交接与状态

- **前端限定游标／倍速已实现**（前端侧交付；本后端工作树不含该前端代码与运行证据，不能用本轮 reader 证据替代）。
- **动作界面尚待接线**；本轮只提供 reader 的 `action_basis` 分域、逐帧候选、独立事件轨与缺失/歧义状态。
- **跨流同步和真实 M1 尚未验收**。
- **区间循环与旧档案没有发生的 `rejected` 事件不再作为全局前置**：它们不是本轮 reader 重载的门槛，也不应从旧归档缺失推断为不可能。

## 8. 记账与边界

- 测试写请求：生成器对 test-only 执行网关（18981）发出 1 次 GET + 7 次 POST（draft/validate/session/start/begin/stop/end）；均为测试生命周期，不经生产网关。
- reader 读取：22 次 GET（18987/18988）；**本轮未向 8792 发请求**，8792 未被写入、RESET、STOP、begin/end、重启或替换。
- 18985/18983/18979/18977 与前端预览保留；未改 `frontend/`、原 native 工作树、生产 pin、recipe 或真实归档；未进入点云、标定、导航或训练。
- 测试端口 18980/18981/18987/18988 已关闭，无残留测试进程；运行数据不入 Git。
- 只新增 `backend/tools/new_recording_readback_check.py`（test-only）；未提交未跟踪生成器；没有新平台候选，18985 仍是最新历史读取候选。

## 9. 不主张

本轮只证明"无物理的新 Recorder 产物已通过当前平台 reader 重载验证"。不代表生产部署、真人采集、真实传感器测量、录制质量合格、跨流同步、统一历史游标、动作界面接线或正式 M1 验收。
