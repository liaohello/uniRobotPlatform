# M1.2c｜原生无运动准备能力候选、可核对配方证明与无 RESET 开录

日期：2026-10-24。本轮修正 M1.2b 的锁核验缺口，完成 `m1-binding-1` / `m1-recording-1` 的原生**候选**实现，并让平台以同一口径核对部署配置、编译场景和运行时版本。**没有在 8792 上部署原生补丁，没有真实运动、RESET、在线录制或回放；不是 M1 闭环，也不是真人示教验收。**

证据索引：[docs/evidence/m1.2c](evidence/m1.2c/m1c-20261024T065943Z-platform/README.md)。历史 M1.2b 记录保留：[backend-m1.2b.md](backend-m1.2b.md)。

## 结论摘要

| 事项 | 本轮结果 | 可核验证据 |
|---|---|---|
| 依赖锁来源与核验 | `requirements.lock` 明确属于 native mobileCar `a5cef52`；平台在启动时读取固定发布副本并比对源摘要，同时逐行解析 `name==version` 与声明表比对；缺失/不符抛 `RecipeError` | `GET /api/v1/mobilecar/execution-recipe` 的 `dependencies.requirements_lock.verification` |
| 配方版本 | 升到 revision 3，fingerprint `4c3e5f42…5e9e`；新增原生配置/场景期望摘要 | recipe 文档、`focused.junit.xml` |
| 部署配置摘要 | native 计算 `mobilecar-config-manifest-1`：extends 链字节 + 覆盖后的有效配置 + 实际读取的 profile/arm_spec 字节；G1 期望 `02351b71…a9af0` | `native-identity.json`、`runtime-config-attribution.json` |
| 编译场景摘要 | native 对 `/api/v1/scene` 的规范 JSON 自行摘要，并与固定期望 `5969e260…f1bf2d` 同口径比较；不再用根 XML 摘要冒充 | `scene.json`、`attestation.json` |
| 运行时环境 | native 自报 Python 与 8 个包的版本，平台按锁逐项核对；未声明为 `unsupported`，不是 passed | 快照 readiness checks |
| 原生绑定 | 候选补丁实现 prepare/readback/start/release；无运动、无 owner、无 RESET、无录制；身份/配置指纹/过期/冲突/回读真实一致 | native 52 passed；真实 HTTP（mock backend）证据 |
| 无 RESET 开录 | 候选实现 `m1-recording-1`；复用 Recorder，持久化 `recording_start`/`feedback_initial`/`initial_snapshot.json` 后才返回 RECORDING | `recording-begin.json`、`events.jsonl`、初始快照哈希 |
| 平台对接 | 新增 `POST /sessions/{id}/recording/begin`；无声明即 unsupported；Session active、授权范围、owner/lease、录制 ready、可运动分开表达 | OpenAPI、平台 86 项聚焦测试 |
| 真实 8792 | **未替换、未重启、未发送任何写请求**；仍为 PID 941842 / drvfix release / `g4a2_server.yaml` | 前后健康与快照一致 |
| 真实 G1 prepared/Start | **仍未实现**：8792 未部署补丁且 profile 为 G4A2；平台候选对真实 native 仍返回 `validation_incomplete` | live `session-error.json` |

## 一、依赖锁：来源、覆盖范围和三层核验

配方文件名保留 `mobilecar-g1-recipe-v2.json`（避免路径迁移），内容 `schema_version=2`、`recipe_revision=3`；fingerprint 覆盖锁、协议与摘要期望。

M1.2b 的交付描述写了“加载时逐个核对文件摘要”，实际只读取了 preset pin 与 kinematics 两个文件；`requirements.lock` 只被声明。本轮修正如下。

| 层级 | 内容 | 本轮状态 |
|---|---|---|
| 配方声明 | `unirobot-execution-recipe-1` 声明 native 项目、commit、源文件路径、源摘要、固定版本表 | 已实现；参与 recipe fingerprint |
| 发布文件核验 | 平台读取 `backend/config/pins/mobilecar-a5cef52/requirements.lock` 的实际字节，SHA-256 必须等于 `c1cad889…8439`；随后解析每行并与声明的 8 个精确版本完全相等 | 已实现；缺失、摘要不符、包表不符都会在应用启动时抛 `RecipeError` |
| 运行环境版本核验 | 平台不检查自己的 gateway 环境，也不通过 HTTP 猜测 native 安装了什么；native 在 capabilities 中自报 Python 与包版本，平台在 readiness 中与锁核对 | 已实现；未声明为 `unsupported`，缺失/不符为 failed |

锁的权威来源是 native mobileCar 的 `requirements.lock`，不是平台自身的依赖。平台发布物中的副本是**固定发布输入**，不代表当前运行实例的 site-packages；后者只能由 native 自报，平台如实标注为自报而非平台侧环境检查。`pyproject.toml` 的 `>=` 依赖范围与锁的精确版本不是同一层，未把两者混为“已核验环境”。

## 二、部署配置与编译场景证明

### 配置摘要 `config_manifest_sha256`

native 计算并公开 `mobilecar-config-manifest-1`：

- `config_files`：YAML `extends` 链上每个实际读取文件的相对路径、SHA-256、大小；
- `effective_config`：应用 `backend_kind`/`require_recording`/`realtime` 覆盖后的有效配置；
- `runtime_files`：观察 profile、action profile（启用 G4A1 时）、navigation profile（启用时）、posture profile（配置时；缺失显式记 `present=false`）、arm_spec、quality/action profile 的实际字节；
- `launch_overrides`：显式覆盖项。

摘要覆盖的是**部署配置内容**，不覆盖源码 Git 提交，也不覆盖安装包；源码提交仍由本地 pin 声明，安装包由运行时自报单独核对。G1 期望摘要由 [native_recipe_identity.py](../backend/tools/native_recipe_identity.py) 在服务器上从 `configs/default.yaml --backend mujoco --require-recording` 生成，工具禁用 `MjData`/`mj_step`/`mj_forward`，`physics_state_calls=0`。

### 场景摘要 `scene_manifest_sha256`

native 对自身实际返回的 `/api/v1/scene` 规范 JSON 求 SHA-256；平台同时要求：

1. 声明值 == 本次实际响应的摘要（自洽，防止声明与响应不是同一份）；
2. 实际摘要 == recipe 固定的编译场景摘要（来源一致）；
3. `model_id` / `model_sha256` / `scene_id` 仍逐字段比较。

根 XML 摘要 `scene_file_sha256` 只作为文件声明保留，**不替代**编译场景摘要。G1 编译场景期望为 `5969e260…f1bf2d`；它恰好与当前 8792 的 live scene 摘要相同，说明场景几何相同，但**不能**说明当前部署配置就是 G1——配置摘要与 interface_profile 仍是不同值。

### 当前真实拒绝

8792 仍是 `g4a2_server.yaml`，live 快照为：

- `interface_profile`：`g4a1-1.0` vs G1 期望 `g2a-1.0`（configuration failed）；
- `deployed_config_attestation` / `scene_manifest_attestation` / 运行时环境 / 两个协议：旧 native 不声明，全部 `unsupported`；
- `native_recording_idle`：passed（当前 IDLE）。

因此 Snapshot 仍为 `failed` / `execution_eligible=false`，Session 创建仍 409。没有改标签、没有换 profile 重签。

## 三、原生绑定协议 `m1-binding-1`（候选）

候选补丁位于 [native-m1binding.patch](evidence/m1.2c/m1c-20261024T065943Z-platform/native/native-m1binding.patch)，基线 native commit `a5cef52`，SHA-256 `9f9a7b0c…ebe1`。应用补丁后的候选源码身份见 [native-candidate-manifest.json](evidence/m1.2c/m1c-20261024T065943Z-platform/native/var/reports/native-candidate-manifest.json)。

| 端点 | 行为 |
|---|---|
| `POST /api/v1/session/prepare` | 校验 `run_id`/`backend_generation`/`episode_id` 与当前一致；同一 runtime 已有 prepared/started binding 时拒绝；生成 `bind_*` 与服务端单调过期时间；`motion_commands_accepted=false` |
| `GET /api/v1/session/prepared/{binding_id}` | 回读同一身份；身份变化 → `invalidated`，过期 → `expired`，主动释放 → `released`；未知 → 404 |
| `POST /api/v1/session/start` | 只把 binding 标记为 `started`，返回执行器授权范围、owner 状态、录制/可运动状态；重复 start 返回同一 binding |
| `POST /api/v1/session/release` | 释放 prepared/started binding；不停止录制、不释放物理 owner、不运动 |

保证与边界：

- prepare/start/release 不调用 `commands`、`episodes/*`、Recorder 或 `mj_step`；不写 owner/lease。
- `owner_state` 从 snapshot 的真实 owner 读取；start 只声明 `control_scope_granted=["base","arm","gripper"]`，`owner_state=not_acquired`，`lease_expires_at_backend_monotonic_s=null`（native 不暴露 lease deadline，不伪造）。
- `recording_ready` / `motion_ready` / `motion_blockers` 从真实 recorder 状态、safety latch 与 owner 计算；录制尚未开始时 `motion_blockers=["recording_not_ready"]`。
- RESET 会在 `Runtime.submit` 应用后立即失效所有 binding；即使绕过该路径，readback/start 也会因身份不同而 `invalidated`。prepare/start 与 RESET 在 backend 锁内串行。
- `config_fingerprint` 是平台快照 ID 的不透明回显，native 不重算；start/readback/begin 都要求逐字相等。

## 四、无 RESET 开录协议 `m1-recording-1`（候选）

| 项 | 语义 |
|---|---|
| 端点 | `POST /api/v1/recording/begin` |
| 前置 | binding 必须为 `started`；`session_id`/`config_fingerprint`/run/generation/episode 必须一致；录制必须为 IDLE/COMPLETE；FAILED 明确拒绝 |
| 初始状态 | 读取当前 `backend.snapshot()`；不 RESET、不发命令、不获取 owner |
| 持久化 | 复用既有 Recorder.start：写 `recording_start`（event_seq=1）、`feedback_initial`、原子 `initial_snapshot.json`；`writer.sync()` 后才置 `RECORDING`、`command_capture_ready=true` |
| 响应 | binding/session/config/identity、`recording_segment_id`、`recording_status=RECORDING`、`recording_start_event_seq`、`initial_snapshot_sha256`、`durable_start_records=true` |
| 重复 | 已 RECORDING 时拒绝第二次 begin；平台层已 ready 的重复请求返回已存 receipt，不再调用 native |
| 停止/收尾 | **本轮不实现**；不使用新 begin 路径调用 STOP/finalize，不声称停车已确认或数据完整 |

`require_recording` 与既有租约/安全停止门控保留；begin 只负责“可靠开始并确认 RECORDING”，不改变 owner、不停车、不 finalize。真实 HTTP（mock backend）证据显示：身份前后一致、owner 仍为空、`recording_start` seq=1、初始快照哈希与响应一致。

## 五、平台对接

新增/扩展：

- `POST /api/v1/sessions/{session_id}/recording/begin`（body：`operator_id`、`view_source`），仅在 active Session 且 native 声明 `m1-recording-1` 时调用；无声明 → 409 `recording_begin_unsupported`；native 拒绝/传输失败 → 409/503 `native_recording_begin_failed`，不更新 ready。
- `PreparedSession.execution`：`control_scope_granted`、`owner{state,session_id,lease_expires_at…}`、`recording_required_for_motion`、`recording_begin_required`、`recording_ready`、`motion_ready`、`motion_blockers`、`source`、`observed_at`。
- `StartReceipt` 增加 owner/lease/录制/可运动字段；`recording_begin_receipt` 与 `recording_begin_attempts` 保留真实回执和失败尝试。
- 快照 readiness 新增：同口径配置摘要、场景声明/实际/期望三方比较、Python 范围、8 个包精确版本；缺省即 `unsupported`。
- 客户端只允许 `/api/v1/session/prepare|start|release`、`/api/v1/session/prepared/{id}` 与 `/api/v1/recording/begin`；没有猜测端点。

**状态新鲜度**：`PreparedSession.execution` 在 prepare/start/recording begin 时更新；`GET /sessions` 返回最近一次平台动作的已存视图，不主动轮询 native。native 侧后续变化需要再次调用对应动作或重新验证，不能把旧视图当作持续实时状态。

**迁移说明**：本轮 `unirobot-prepared-session-1` 文档新增 `execution`、`recording_begin_*` 字段。M1.2b 没有真实创建过 Session（live 为空），新候选使用新的 SQLite 文件；若复用旧 DB，旧文档在读取时会因缺字段校验失败，需重新创建而不是补造状态。

## 六、验证范围

| 验证 | 结果 | 性质 |
|---|---|---|
| 平台聚焦（gateway-py314） | **86 passed**：prepare/drafts/geometry/read/mobilecar/api | 合成 native 替身 |
| 平台全量 | **93 total，90 passed，3 failed**；3 项仍是 catalog/migrate 依赖 sibling 源码与 native docs 的布局失败，与历史 74/3 同类；未跳过 | 环境布局事实 |
| 原生聚焦 | **52 passed**：新增 binding/attestation + app_mock + recorder + contracts | 真实 native 代码、真实 Recorder、mock backend |
| 原生受影响 | **44 passed** | 同上 |
| 原生真实 HTTP | prepare/readback/conflict/start/重复 start/begin/重复 begin/release 全部按预期；文件哈希与响应一致 | 真实 HTTP + mock backend，无物理 |
| live 平台 | 18944 对 8792：validation failed、Session 409、缺失 Session 404；native 前后一致 | 只读，未部署补丁 |
| 未验证 | 真实 G1 native prepared/Start、真实录制 begin、停车/finalize、owner/lease 获取、回放、并发压力 | 仍未执行 |

## 七、原生部署与维护窗口

当前 8792：

- PID 941842，release `drvfix-20261019T044549Z-0a80415b2577`，`configs/g4a2_server.yaml`；
- 本轮结束后仍为同一 PID、run/generation/episode、`recording=IDLE`、无 owner、`safety_latched=true`；
- 未停止、未重启、未替换、未发送 RESET/命令/录制请求。

候选补丁与部署物：

- 补丁基线 `a5cef52`；在服务器用 `drvfix` 内容 + 补丁组装了隔离 release `m1binding-20261024T065822Z-native`，只在 18946 以 **mock backend** 运行验证，已停止；
- 补丁不修改 `backends/mujoco/backend.py`；该文件恰好是 `drvfix` 与 `a5cef52` 之间唯一不同的已检查源文件。补丁可同时应用于两者；
- 若从 `a5cef52` 构建部署物，会顺带包含该 backend.py 的 G4A-2 UI/驾驶安全差异，需要单独评审；若从 `drvfix` 构建，则当前 pin 的 source manifest 不再精确对应，需要重新固定而不是静默沿用；
- 回滚：保留 `drvfix` release 与 `g4a2_server.yaml`，新 release 失败时按原命令重启旧 release；binding 是内存状态，重启后自然消失；新录制写到独立目录，不迁移旧数据。

**维护窗口前的真实决策**：即使换上新 native 代码，8792 仍运行 G4A2 profile，G1 配方仍会因 `interface_profile` 和配置摘要不同而拒绝。要得到真实 G1 prepared/Start，必须二选一：

1. 在维护窗口把实例切到 G1 `configs/default.yaml --backend mujoco --require-recording`（会改变当前 G4A2 人工采集界面/配置口径），再部署候选并重验；
2. 保留 G4A2 部署，另行形成 G4A2 的配方、采集口径和场景/配置摘要，再签发新目标（不是本轮 G1 配方）。

两种都需要用户决定；本轮没有静默改标签、改 profile 或重签。维护窗口未申请、未执行。

## 八、前端交付

- OpenAPI（含新端点与 schema）：[openapi.json](evidence/m1.2c/m1c-20261024T065943Z-platform/platform/report/live/openapi.json)。
- 真实失败样例：live `validation.json`、`session-error.json`、`start-missing.json`、`recording-begin-missing.json`。
- 成功夹具：`focused.junit.xml` 覆盖的 prepare/Start/begin 路径，明确标注为**合成 native 替身**；不得当作 live 成功。
- 真实 native（mock backend）成功：`native/http/*.json`，明确标注无物理、无部署。
- `GET /api/v1/mobilecar/execution-recipe` 现在同时给出锁核验层级、配置/场景期望摘要和协议要求，前端可显示“为什么不可执行”的具体 scope。
- 前端仍消费 18943；本轮未修改前端文件。18944 是新的只读平台候选，供独立对话核对。

## 九、复现

服务器上（不要重启 18941/18942/18943/8792）：

```bash
R=~/Desktop/uniRobotPlatform/releases/m1c-20261024T065943Z-platform
cd "$R"
UNIROBOT_REPO_ROOT="$R" UNIROBOT_CATALOG="$R/report/catalog.live.yaml" \
  UNIROBOT_DRAFT_DB="$R/report/live-prepare-m1c-2.sqlite3" UNIROBOT_ALLOW_LAUNCH=0 \
  UNIROBOT_PROBE_TIMEOUT=3 \
  UNIROBOT_GEOMETRY_BUNDLE=~/Desktop/uniRobotPlatform/releases/m1-geometry-20261023T192202Z-cdfc7472e5de/geometry \
  PYTHONPATH=backend/src \
  ~/Desktop/uniRobotPlatform/envs/gateway-py314/bin/python -m uvicorn unirobot.api:app --host 127.0.0.1 --port 18944
```

原生候选（隔离 release，mock backend，无物理）：

```bash
N=~/Desktop/mobileCar/releases/m1binding-20261024T065822Z-native
cd "$N"
PYTHONPATH=src MUJOCO_GL=egl ~/Desktop/mobileCar/envs/g2a-py310-mujoco316/bin/python \
  -m mobilecar --config configs/default.yaml --backend mock --require-recording \
  --host 127.0.0.1 --port 18946
```

原生摘要生成（只编译，不创建 MjData、不步进）：

```bash
cd "$N"
PYTHONPATH=src ~/Desktop/mobileCar/envs/g2a-py310-mujoco316/bin/python \
  ~/Desktop/uniRobotPlatform/releases/m1c-tools-20261024/native_recipe_identity.py \
  --config configs/default.yaml --backend-kind mujoco --require-recording \
  --out var/reports/native-identity.json
```

源码身份：平台 `backend` 44 个非缓存文件，清单 SHA-256 `d07d6410…a85b`（按 release 根相对路径）；原生冻结清单见 `native/var/reports/frozen-source-listing.txt`，清单摘要 `6e67d96e…120d`。这些是测试 release 身份，不是已部署生产身份。

## 十、仍未完成

真实 G1 native 部署与维护窗口、真实 prepared/Start、真实录制 begin（线上）、owner/lease 获取、STOP/停车确认/finalize、回放、并发和多实例、真人示教与训练。**本轮不宣称 M1 闭环完成，也不自动进入下一阶段。**
