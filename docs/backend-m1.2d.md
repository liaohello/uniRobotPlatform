# M1.2d｜准备链路 P1 修复、当前状态刷新与真实 HTTP 协议集成

日期：2026-10-24。本轮修复 native 准备链路的两项 P1，补齐单 Session 的只读当前观测，并让**平台实际 `NativeBindingClient`**经真实 HTTP 与隔离的 native mock 候选完成 prepare/readback/start/begin/release 集成。**候选完成；8792 未部署、未重启，未执行真实物理验证、线上运动/录制或 M1 验收。** 证据索引：[evidence/m1.2d](evidence/m1.2d/m1e-20261024T090448Z-platform/README.md)。

## 一、两项 P1

### P1-1 录制生命周期竞态

原实现中，`Runtime.submit` 的 commands RESET 和 `Runtime.start_episode` 在取得 `backend.lock` 之前检查 `recording_state()`；新的 `recording/begin` 在 `backend.lock` 内执行 `recorder.start`。旧检查可以通过，随后 RESET 在录制已经开始后才提交。

修复：

- 在 `Runtime` 增加 `lifecycle_lock`；所有录制状态检查、RESET、legacy `episodes/start`、`recording/begin`、`stop_episode` 和 recorder 失败停止都经过该锁。
- 锁顺序固定为 **lifecycle → backend → recorder**；不从 recorder 回调、recording gate 或已持有 backend 锁的路径反向获取 lifecycle。
- RESET 的状态检查在 lifecycle 锁内完成，并在同一临界区提交 RESET 与失效 binding；legacy `episodes/start` 从状态检查、RESET、取得实际 snapshot 到 `recorder.start` 全程持有 lifecycle 锁。新 begin 同样在 lifecycle 锁内完成 binding/状态检查、初始快照和 durable start。
- `stop_episode` 持 lifecycle 锁完成 STOP、停车等待、drain 和 Recorder stop；`require_recording`、STOP latch、owner/lease 和既有安全门控未放宽。

确定性回归：native `mobileCar/tests/integration/test_lifecycle_race.py`（补丁与证据见 [native patch](evidence/m1.2d/m1e-20261024T090448Z-platform/native/native-m1e.patch)）用屏障阻塞第一个 `recorder.start`，再从其他线程发起 commands RESET 和 legacy `episodes/start`，断言二者等待、随后被拒绝、没有 RESET 命令穿透，且只发生一次 start。反向测试阻塞 legacy start，证明新 begin 不能插入。**同一测试在修复前 release 上 2 failed**，证据 `native/prefix-race/prefix-race.log`；修复后 57 项 native 聚焦测试全部通过。

### P1-2 binding TTL

原实现把 30 秒 prepared TTL 同时用于 started，导致 Start 后越过 TTL 的 binding 被标为 `expired`，无法 begin，也允许同 runtime 再次 prepare。

修复：

- `_evaluate` 只对 `prepared` 检查 `expires_at`；`started` 仅由 RESET、显式 release 或身份变化失效。当前没有额外 Session close/end 事件，文档明确不再凭空定义短租约。
- readback 增加 `expires_scope="prepared"`，避免客户端把 started 的过期字段误读为仍会过期。
- `release` 只允许 `prepared|started` 转为 `released`，不覆盖 expired/invalidated 证据。
- 可控时钟测试覆盖：prepared 超时拒绝；Start 后越过 TTL 仍可读回、重复 start 和 begin；started 仍阻止同 runtime 重复 prepare；release 后允许新 prepare；RESET 后 invalidated。

### 当前执行观测

`GET /api/v1/sessions/{id}` 现在返回存储的历史会话（含 `start_receipt`、`recording_begin_receipt`、attempts）+ `current` 只读实时观察。`current` 字段：

- `source="live_native_read_only"`、`observed_at`、`valid`、`status`、`error`、`blockers`；
- `runtime_identity` 与实际匹配、`binding{state,matches,readback_sha256,error}`；
- `snapshot_id`、`snapshot_eligible`、`recipe_fingerprint_matches`；
- `control_scope_granted`、`recording_required_for_motion`、`recording_begin_required`；
- `recording{status,episode_id,segment_id,command_capture_ready,error,ready}`；
- `owner{state,session_id,lease_expires_at_backend_monotonic_s,lease_exposed=false}`、`safety_latched`；
- `recording_ready`、`motion_ready`、`start_available`、`recording_begin_available`。

语义：

- 只执行 native GET（health/capabilities/scene/snapshot/health + binding readback）；不续租、不重绑、不 Start、不清安全锁、不启停录制，不写平台存储。
- 失联返回 HTTP 200 + `status=offline`、`valid=false`，所有 ready/available 为 false；不会用旧 ready 冒充当前状态。
- 身份变化、snapshot/recipe 失效、binding `expired/invalidated/released`、绑定字段不一致、native 录制未 ready、safety latch、owner 冲突都会给出具体 blocker，ready/available 为 false。
- `GET /api/v1/sessions` 改为明确存档视图：`{"source":"stored","live":false,"retrieved_at", "sessions":[...]}`，不触发 native 读取，items 的 `current=null`。
- 历史回执不重写；GET 只返回观察副本。刷新不改变 start/begin 的幂等结果；重复 start/begin 仍由既有状态与 native 幂等保证，不新增第二次 native 调用。

契约同步见 [Session 生命周期](specs/20-backend/01-session-scene/01-session-lifecycle.md) 与 [Episode 契约](specs/30-contracts/03-episode-events-annotations.md)。

## 二、真实 HTTP 协议集成

在服务器启动隔离 native 候选（mock backend，端口 18950）和测试平台（端口 18951）：

- native 使用真实 FastAPI、真实 Recorder、隔离 `runs/`；不创建 MuJoCo 物理实例，不推进物理。
- 测试平台使用**测试专用 recipe** `mobilecar.g1.teleop.mock-testonly`，期望值来自该 mock 的真实 capabilities/attestation；`backend_kind=mock`、mock model_id、mock config/scene digest、测试 kinematics，**没有**为了让生产 G1 通过而伪造字段，生产 recipe/pin/fingerprint 未改。
- 平台实际 `NativeBindingClient` 经真实 HTTP 完成：draft/validate（19 项检查通过、`execution_eligible=true`）→ create Session（binding verified）→ 单 Session GET prepared → Start → 单 Session GET started → 重复 Start（native 幂等）→ begin（RECORDING）→ 单 Session GET recording ready/motion ready → 重复 begin（replayed，事件数不增）→ release → 单 Session GET 立即 released/invalid，ready=false。
- 拒绝：同 runtime 重复 prepare（native `binding_conflict`）、错误 episode 身份 prepare（native 拒绝）、重复 start 不重复启动、重复 begin 不新增 segment。
- 文件证据：`initial_snapshot.json` SHA-256 与 begin 回执一致；`events.jsonl` 首两项为 `recording_start` seq=1、`feedback_initial` seq=2；release 后 owner 仍为空。
- 结果：[cross-http.json](evidence/m1.2d/m1e-20261024T090448Z-platform/native/http/cross-http.json)。这是 **mock 协议集成通过**，不是生产 G1 验证通过。

## 三、Live 生产候选

新平台候选 `18949` 使用生产 recipe revision 3，对真实 8792 只读运行：

- Validation snapshot `cs-15113e6f9b76458ec57b847a53f74d91a395ba88`，`failed`、`execution_eligible=false`；
- `interface_profile`（configuration）和 `deployed_config_attestation`、`scene_manifest_attestation`、`runtime_python_version`、`runtime_package_versions`、`session_binding_protocol`、`recording_begin_protocol`（readiness，均 `unsupported`）阻塞；
- Session 创建 409 `validation_incomplete`；`GET /sessions` 为 `source=stored` 空列表；缺失 Session/begin 404；
- 8792 前后 run/generation/episode、`recording=IDLE`、owner、`safety_latched=true` 全部不变；PID 941842 未停止或重启。

端口/进程：

| 端口 | 实际 |
|---|---|
| 8792 | 既有 native，PID 941842，drvfix release，`g4a2_server.yaml` |
| 18941/18942/18943 | 既有服务，未改 |
| 18944 | 上一轮 M1.2c 平台候选 |
| 18946 | 前端预览代理 → 18943；本轮未占用 |
| 18933 | 较早前端预览代理 |
| 18947/18948 | 前端预览代理 → 18944（最新 release，未改动） |
| 18949 | 本轮 M1.2d 生产配方平台候选，只读运行中 |

## 四、冻结身份与部署决策

平台：

- release `m1e-20261024T090448Z-platform`；`backend` 46 个非缓存文件；源码清单 SHA-256 `c1ce0339…2946`；与工作树一致。
- Python 3.14.6；fastapi 0.161.1、pydantic 2.14.1、uvicorn 0.54.0、PyYAML 6.0.3、pytest 9.1.1。详见 `platform/dependency-versions.json`。

Native：

- 补丁 `native-m1e.patch`，SHA-256 `df7e6e96…d7e6`，基线 `a5cef52`；在 detached worktree 应用后逐文件哈希一致；未提交/推送 native 仓库。
- 最终测试 release `m1e-20261024T090412Z-native`；source listing `ff27bb5e…b1cb`；config digest `02351b71…a9af0`、scene digest `5969e260…f1bf2d`、`physics_state_calls=0`。
- **旧 source pin `a0109804…911c` 只等于 a5cef52 base**。补丁候选：
  - a5cef52 + patch：`c325a2b3…6efd`
  - drvfix + patch：`dd24d1c8…f7da`
- 两候选在 pin 范围内的实际差异见 [native-deploy-identity.json](evidence/m1.2d/m1e-20261024T090448Z-platform/native/reports/native-deploy-identity.json)：相对 drvfix base，a5 base 差异为 `AGENTS.md`、`assets/.../mecanum.xacro`、`modelgen/model/{__init__,source}.py`、`backends/mujoco/backend.py`、`g4a2.html`、`g4a2.js`；a5+patch 还会带入三份 docs 的更新。我们的 P1 补丁不修改这些文件；a5+patch 会额外包含 G4A2 UI/驾驶安全与 modelgen 变化，drvfix+patch 保留已部署行为但必须重新签发 source pin。

**部署步骤（维护窗口，本轮不执行）**：

1. 决定 G1 或 G4A2：若继续 G1 配方，native 必须以 `configs/default.yaml --backend mujoco --require-recording` 运行；若保留当前 G4A2 采集，则必须另签 G4A2 recipe/采集口径，不能沿用 G1 pin/摘要。
2. 选择 a5cef52+patch 或 drvfix+patch，生成并冻结**新的** source manifest/aggregate、patch sha、依赖锁和 config/scene digest；不要沿用 a010…。
3. 在独立 release 安装/测试；先验证 native health/capabilities/attestation、binding/start/begin；再启动平台候选，验证 G1（或新 G4A2）validation passed 和 prepared → active → RECORDING。
4. 停止旧 8792 前记录 PID/run/episode/owner/recording；替换为新 release 和选定 profile；失败则按 drvfix release + `g4a2_server.yaml` 原命令回滚。旧 binding 是内存状态，重启自然消失；新录制写独立目录，不迁移旧数据。
5. 成功判据：完整 current 观测有效；identity/config/binding 一致；begin 返回 durable RECORDING；记录文件哈希与回执一致；没有 RESET/owner/second start；safety/lease 门控未放宽。真实物理运动、停车/finalize、回放仍另测。

本轮没有维护窗口，也没有部署。

## 五、验证结果

| 检查 | 结果 |
|---|---|
| 平台聚焦（gateway-py314） | **94 passed**：prepare/drafts/geometry/read/mobilecar/api |
| 平台全量 | **98 passed / 3 failed**；3 项仍是 catalog/migrate 的 sibling 源码与 native docs 布局失败，历史 **90 passed / 3 failed** 事实保留，未跳过或改绿 |
| Native 聚焦 | **57 passed**：生命周期竞态 + TTL + app_mock + recorder + contracts |
| 修复前对照 | 新竞态测试在旧 release **2 failed** |
| 跨 HTTP | 测试 recipe validation passed、prepared/active/RECORDING、重复幂等、release 失效、文件哈希一致 |
| Live 生产 | 仍 failed/409；8792 不变 |

## 六、前端交付与未完成

- OpenAPI：[openapi.json](evidence/m1.2d/m1e-20261024T090448Z-platform/platform/live-m1e/openapi.json)。前端迁移：`GET /sessions` 从数组改为 `{source:"stored",live:false,sessions:[...]}`，必须读取 `sessions` 且不要把列表当实时状态；`GET /sessions/{id}` 的历史回执字段不变，新增 `current`，实时显示/按钮可用性应使用 `current.valid`、`current.status`、`current.blockers`、`current.recording_ready`、`current.motion_ready` 和各 available 字段。`POST /sessions/{id}/start` 与 `POST /sessions/{id}/recording/begin` 路径不变。
- 当前状态/新鲜度约定与错误样例见上面第三节和 [evidence README](evidence/m1.2d/m1e-20261024T090448Z-platform/README.md)；成功样例明确标注 native mock 无物理。
- 前端预览当前为 18947/18948 → 18944（最新 release）以及 18946/18933 → 18943；均未改动。18949 是本轮生产配方平台候选。前端文件未修改。
- 未完成：8792 部署、真实 G1 prepared/Start、真实物理运动、线上录制 begin、停车/finalize、回放、owner/lease 获取、并发压力、M1 闭环；不自动进入真人示教、采集或训练。
