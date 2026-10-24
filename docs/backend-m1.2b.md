# M1.2b｜无执行副作用的配置验证与 Session 准备链路

日期：2026-10-24（America/Los_Angeles）。本轮实现配置快照、prepared Session 与显式 Start 的**平台侧契约**，并显式证明 native 侧缺少无运动绑定能力。**本轮没有运动、RESET、录制、控制或回放调用；不是 M1 闭环、控制或录制验收。**

> **2026-10-24 更正（M1.2c）**：本文“加载时逐个核对文件摘要”只对 preset pin 与 kinematics profile 成立；`requirements.lock` 当时仅被声明，没有读取实际字节，也没有核对包表。另两处口径已在 M1.2c 修正：`deployed_config_attestation` 当时与 155 文件源清单摘要比较，属于错误 scope；`scene_manifest_attestation` 当时只做“声明==观测”，没有与固定编译场景期望比较。M1.2b 的 live 结果、PID 不变和 70 passed 等历史事实保留，但不要把上述锁/摘要描述当作已验证事实。当前实现与证据见 [M1.2c](backend-m1.2c.md)。

稳定版保持不变：[read-1](backend-m1-read.md) 仍在 18941，[geometry-1](backend-m1-geometry.md) 仍在 18942，前端预览 18933，native 8792 继续用同一个物理实例。本轮候选是新的 18943，只新增读取与平台侧准备，不改前端、不改原生源码、不新增物理循环。

## 结论摘要

| 事项 | 本轮结果 | 可核验证据 |
|---|---|---|
| 执行配方 | 新增 `mobilecar-g1-recipe-v2.json`，把 preset pin、依赖锁、所需协议、运动学 profile 合成一个带指纹的配方 | `GET /api/v1/mobilecar/execution-recipe`，fingerprint `78ec4bf1…342b26` |
| 配置快照 | 服务端生成不可变、可重现的 `unirobot-config-snapshot-1`；同一草案+同一证据得到同一 `snapshot_id` 与 `snapshot_sha256` | `cs-6f48f98f…9392b4`，`5833f65c…9cac97`，重复校验 `reused=true` |
| 配置验证结果 | 13 项 configuration 检查中 12 项通过，仅 `interface_profile` 失败；5 项 readiness 检查 4 项 unsupported、1 项通过 | 快照 `checks`（17 项）与 `blocking_reasons`（5 项） |
| ValidatedSnapshot | 本轮**不签发**：`validation_status=failed`、`execution_eligible=false`、`validated_snapshot_id=null` | `POST /api/v1/sessions` 返回 409 `validation_incomplete` |
| prepared Session | 契约与实现完成，仅在夹具（conformance fixture 声明 binding 协议）下走通；真实 native 不支持，故未创建 | 14 项 `test_prepare.py` 用例 |
| 显式 Start | 前置条件、成功回执、失败语义完整；真实环境不可达，返回明确拒绝而不是伪造成功 | 夹具 receipt；live `POST /sessions/missing/start` → 404 |
| 几何包身份 | geometry-2 把**内容身份**与 run/generation/episode 身份拆开；内容不符仍 409，身份漂移只记录 | `geometry_binding`，`association=content_matches_export_identity` |
| 运动学元数据 | 零位/方向/TCP/夹爪固定为带来源摘要的 profile，并与实时 native 限位交叉核对 | `max_user_limit_error_rad=0.0`，5 项一致性均 true |
| native 影响 | PID、run/generation/episode、录制状态、owner、safety 前后一致；没有非 GET 调用 | `report/live/live-check.json` |

## 一、执行配方与可验证来源

配方 `unirobot-execution-recipe-1` 是"允许签发什么"的唯一声明。它把三个文件固定成一条可核验链：

| 组成 | 内容 | 摘要 |
|---|---|---|
| preset pin | argv/env/config、7 条命令、7 条流、model/scene 期望 | 文件 `146d331f…d9768` |
| 依赖锁 | Python `>=3.10,<3.13`；mujoco 3.1.6、pydantic 2.13.5 等 8 个精确版本 | `c1cad889…fc8439` |
| 运动学 profile | 5 关节零位/方向、夹爪换算、TCP 安装、来源与限制 | 文件 `6e2d3d08…3fd5`，内容摘要 `7238f521…81bc0` |
| 所需协议 | `session_binding=m1-binding-1`、`recording_begin=m1-recording-1` | 参与 recipe fingerprint |

加载时逐个核对文件摘要，任一不符即启动失败（`RecipeError`），不会带着过期声明运行。`recipe_fingerprint` 覆盖上述全部内容；草案、快照、prepared Session 都用它判断依赖是否变化。

> **更正（2026-10-24）**：以上“逐个核对”在 M1.2b 实际只覆盖 preset pin 与 kinematics；锁文件未被读取。M1.2c 已把锁固定为发布文件并在启动时读取字节、比对源摘要与包表；运行环境版本另由 native 自报后在 readiness 核对。详见 [M1.2c 第一节](backend-m1.2c.md#一依赖锁来源覆盖范围和三层核验)。

**可核验层级必须分清**，这也是不能凭"根 XML 摘要 + health 在线"签发 Passed 的原因：

| 层级 | 例子 | 能否由本平台独立核验 |
|---|---|---|
| 原生自报 | `interface_profile`、`recording_required_for_motion`、`supported_commands` | 只能作为声明读取，不能证明部署内容 |
| 逐字节可核验 | mesh 资产字节、bundle 摘要、recipe 源文件 | 是 |
| 编译产物可核验 | compiled scene 与 live scene manifest 完整相等 | 是（geometry 候选） |
| **不可通过 HTTP 核验** | 部署源码/配置清单、scene XML 文件本身 | 否。pin 的 `scene_file_sha256=f94c2c19…204a` 是**场景 XML 文件摘要**，原生 HTTP 既不提供该文件也不提供 manifest 摘要 |
| 观测值 | live scene manifest 摘要 `5969e260…f1bf2d` | 只记录为证据，未与 pin 绑定，因此是 `unsupported` 而不是 `passed` |

## 二、当前 native profile 与固定 G1 配方的关系

实际运行的 native 是 `configs/g4a2_server.yaml`（PID 941842），不是 G1 配方：

| 维度 | G1 配方期望 | 当前实际 | 结论 |
|---|---|---|---|
| 部署配置 | `configs/default.yaml` + `--require-recording` | `configs/g4a2_server.yaml`（extends g4a1） | 不同执行面 |
| 自报 interface_profile | `g2a-1.0` | `g4a1-1.0` | **不一致**，configuration 检查失败 |
| 真实 profile id | — | 配置里声明 `g4a2-1.0`，但 health 从不读取该字段 | health 的 profile 是由 `g4a1.enabled`/`navigation.enabled` 推导的字面量，不是部署证明 |
| model/scene | landerpi…3ca3d6d0 / mobile_pick | 相同 | 资源身份一致（仅这三字段） |
| 命令集 | 7 条 | 13 条超集 | 子集检查通过 ≠ 同一执行面 |
| recording/action profile | g2a_rgbd_5hz / g2a_action_teleop_v1 | g4a2_human_sixdim_v1 / g4a1_action_v1 | 不同采集口径 |
| 运行状态 | — | `recording=IDLE`、无 owner、`safety_latched=true` | 即使 profile 匹配也不具备运动条件 |

因此本轮**不做**"换 profile 重签"：既不能停既有 native，也不能再开第二个物理实例。`interface_profile` 失败是真实差异，不是配置疏忽。

## 三、配置快照与 prepared 契约

状态推进（每步只做声明的事）：

```text
draft(unvalidated) --validate--> configuration snapshot(failed|passed)
                                        |
                     execution_eligible=true（含 readiness）
                                        v
                             ValidatedSnapshot（本轮未签发）
                                        |
                             POST /sessions（幂等/冲突）
                                        v
                              prepared Session
                                        |
                             POST /sessions/{id}/start（显式）
                                        v
                                  active（带回执）
```

- **不可变性**：快照只 INSERT，重复请求返回已存文档，`snapshot_sha256` 不会因重算而改变。
- **可重现性**：`snapshot_id = "cs-" + sha256(payload 去掉 snapshot_id/snapshot_sha256/created_at)`。同一草案、同一证据重复校验得到同一 id 与同一 sha（实测 `reused=true`）。换草案（`draft_id` 不同）或 native 状态变化则产生新 id，这是预期行为。
- **两段判定**：`configuration` 决定 `validation_status`；`readiness` 决定 `execution_eligible`；只有两者都通过才有 `validated_snapshot_id`。合同要求"必需项 unsupported/not_checked 阻止全局 passed"，这里通过"readiness 未通过则不给 ValidatedSnapshot"落实，而不是把 unsupported 伪装成 passed。
- **创建无副作用**：一次校验只发 5 个 GET（health、capabilities、scene、snapshot、health）；prepared 创建额外只调用协议声明的 `session/prepare` 与 `session/prepared/{id}` 回读。**不调用** `/api/v1/commands`、`/api/v1/episodes/*`，不 RESET、不录制、不推进物理。
- **既有运行不被替换**：同一 `run/generation/episode` 只允许一个 prepared/active Session，第二个返回 409 `session_conflict` 并带上现有 `session_id`；native 有非 IDLE 录制时 readiness 直接失败（`native_recording_idle`）。任何路径都不调用 stop。

真实请求与响应（服务器执行）：

```bash
curl -s -X POST http://127.0.0.1:18943/api/v1/experiment-drafts \
  -H 'Content-Type: application/json' -d '{"name":"M1.2b live check"}'
curl -s -X POST http://127.0.0.1:18943/api/v1/experiment-drafts/<draft_id>/validate \
  -H 'Content-Type: application/json' -d '{"execution_revision":1,"fingerprint":"<64 hex>"}'
curl -s http://127.0.0.1:18943/api/v1/config-snapshots/cs-6f48f98fff1b427eb10a5fae647a8ffee49392b4
```

```json
{
  "schema_version": "unirobot-config-snapshot-1",
  "snapshot_id": "cs-6f48f98fff1b427eb10a5fae647a8ffee49392b4",
  "snapshot_sha256": "5833f65cd929dcc1447ece59ea1fe2c57c0fb14a6b603c568fe7e8517d9cac97",
  "validation_status": "failed",
  "execution_eligible": false,
  "validated_snapshot_id": null,
  "validation_scope": "motion_free_configuration_and_declared_protocol_only"
}
```

创建 Session 的真实拒绝（节选）：

```json
{"detail": {"code": "validation_incomplete", "message": "Snapshot is not execution eligible",
  "blocking_reasons": [
    {"key": "interface_profile", "scope": "configuration",
     "message": "native /api/v1/health self-report: observed g4a1-1.0; recipe expects g2a-1.0; this value is derived from config flags, not attested"},
    {"key": "session_binding_protocol", "scope": "readiness",
     "message": "native declared session binding protocol: Native declares no motion-free Session binding; required m1-binding-1. episodes/start performs RESET and recording"}
  ]}}
```

## 四、显式 Start 的前置条件、结果与失败语义

`POST /api/v1/sessions/{id}/start` 先做只读复核，再决定是否请求 native；**不把"后台物理循环在线"当作 Session 已 Start**。

| 前置条件 | 失败 key | 作用域 |
|---|---|---|
| Session 处于 prepared | `session_not_startable` | platform |
| 快照仍存在且 `execution_eligible` | `snapshot_not_eligible` / `snapshot_not_found` | platform |
| recipe fingerprint 未变 | `recipe_changed` | platform |
| live run/generation/episode 与 Session 一致 | `runtime_identity_changed` | native |
| native 录制为 IDLE | `native_recording_active` | recording |
| base/arm 无其他 owner | `control_owner_present` | native |
| native 安全停止未锁存 | `native_safety_stop_latched` | native |
| binding 已核实且回读仍一致 | `native_binding_unverified` | native |

- 任一不满足：409 `start_preconditions_unmet`，响应带 `blocking_reasons`（key/scope/message），Session 状态不变，仅追加一条 `start_attempts` 记录（`result=refused`）。
- native 拒绝或传输失败：502/409 `native_start_failed`，同样记录 `failed`，不写 `active`。
- 成功：返回 `state=active` 与 `start_receipt`（binding_id、native_session_id、run/generation/episode、config_fingerprint、`started_at_backend_monotonic_s`、`control_scope_granted`）。重复调用返回同一 active Session，不重复启动。
- 本轮真实环境没有任何 Session，`/sessions/missing/start` 返回 404 `session_not_found`；成功路径只在夹具中验证，不对外宣称已可启动。

## 五、native 绑定保证与最小协议

事实（只读核对原生源码与实时响应）：

- 没有"注册/准备 Session"的端点；`session_id` 只是调用方自选字符串，不登记、不校验 owner 匹配。
- owner 只在运动/规划命令里由 `_acquire` 写入，租约 0.5 s 后过期；`/api/v1/lease/renew` 只续已有通道，不创建。
- `episodes/start` 会先提交一条 RESET 命令再开始录制，响应不回读实际应用的 episode/初态；`require_recording` 只在启动配置里生效。
- health 不提供 session、config 或 scene manifest 摘要。

因此平台**不能**用内存标志把缺失能力包装成真实 Session。本轮做法：

1. 在 `CapabilitiesWithAttestation` 中读取四个可选声明：`config_manifest_sha256`、`scene_manifest_sha256`、`session_binding_protocol`、`recording_begin_protocol`。缺失即 `unsupported`，不猜测、不回退。
2. 只有声明 `session_binding_protocol=m1-binding-1` 时才调用绑定端点；客户端路径白名单仅 `/api/v1/session/prepare|start|release` 与 `/api/v1/session/prepared/{id}`。
3. `prepare` 必须回显平台生成的 `session_id`、`config_fingerprint`、run/generation/episode，并给出 `state=prepared`、`motion_commands_accepted=false`；再 GET 回读并逐字段比对，任一处不符即 `native_binding_unverified`。
4. 协议文本见 [Session 生命周期 §原生绑定协议](specs/20-backend/01-session-scene/01-session-lifecycle.md#原生绑定协议m1-binding-1)。**原生侧尚未实现，本轮未修改原生源码**，所以真实环境永远走到 `session_binding_protocol=unsupported`。

夹具证明的是平台客户端与判定逻辑正确（包含 prepare/readback/start/release 全流程），不是原生能力已经存在。

## 六、几何包生命周期：内容身份与运行身份

geometry-1 把 `runtime_identity`（run/generation/episode）当作服务前置条件，导致正常开录 RESET 后场景永久 409。geometry-2 改为：

| 判断 | 依据 | 结果 |
|---|---|---|
| 内容是否仍是同一份几何 | `resource_identity`（contract/model_id/model_sha256/scene_id）+ live scene 摘要 == `native_scene_sha256` | 不符 → 409 `geometry_source_changed`，绝不返回旧网格 |
| 内容身份摘要 | 上述四项 + model_inputs/compiled_scene 摘要 | `content_identity_sha256=cb789964…18a7cc` |
| 运行身份是否与导出时相同 | 导出时记录的 run/generation/episode vs 本次 health | 不同 → 仍返回 200，但 `runtime_identity_matches=false`、`association=content_reverified_after_runtime_identity_change`，并同时给出 `exported_runtime_identity` 与 `observed_runtime_identity` |

每次 GET scene 都重新读取 live health 与 scene 并复核内容，因此"身份变化后的重新核验"不需要额外状态或后台任务；`geometry_provenance.runtime_identity` 永远保留导出时刻的原值，不被改写。

前端处理约定：`content_matches=true` 但 `runtime_identity_matches=false` 时，只刷新 Actual/Target 与身份，不重载网格、不清空模型；只有 `geometry_source_changed` 才提示重建 bundle。

真实 native 的 episode 未变化，所以线上只观察到 `content_matches_export_identity`；身份漂移路径由夹具覆盖（`test_episode_change_keeps_verified_content_and_reports_the_new_identity`），**没有为了制造漂移去 RESET 真实实例**。

## 七、运动学元数据

`landerpi.kinematics.v1` 固定了此前只散落在源文件里的常量：

- 5 关节 `zero_model_rad=[0,0,0,-1.5707963267948966,0]`、`user_direction=[1,1,1,1,1]`、`q_model = zero + direction·q_user`。
- 夹爪 `min/max=0.012000038000000005/0.05 m`、`zero_width=0.025`、`width_per_drive_rad_m=0.023199`、mimic 系数。
- `grasp_tcp` 在 `guide_rod_link` 上的平移；**姿态在源文件里不存在**，明确 `orientation_xyzw=null`、`orientation_status=not_specified_in_source`。
- 相机挂 `link4`，`status=source_topology_not_rigid_to_tcp`。
- 权威级别 `platform_reference_not_native_attested`，并列出四条限制（照片零位非硬件 500、未标定、无独立符号位、原生不暴露常量）。

`GET /api/v1/mobilecar/kinematics` 会实时交叉核对：用 profile 的零位/方向把 native `model_limits_rad` 变换成用户限位，与 native `arm_user_limits_rad` 比较；同时核对关节顺序、TCP 父 body/site、相机父 body、夹爪宽度限位。实测 5 项全部 true，最大误差 `0.0 rad`。

能证明的只是"这份元数据与当前 native 声明一致"，**不能证明**关节轴符号、TCP 姿态或真实标定；前端可以据此逐步去掉写死的参考 profile，但不能把它当运动学校准结果。

## 八、接口、版本与入口

| 入口 | 版本 / 状态 | 内容 |
|---|---|---|
| `127.0.0.1:18941` | read-1，冻结 | 场景/能力/快照/资产，语义与字节不变 |
| `127.0.0.1:18942` | geometry-1，冻结 | 编译网格候选，前端已集成 |
| `127.0.0.1:18943` | **M1.2b 候选** | read-1 三个读取 + geometry-2 scene + 下列新端点 |
| `127.0.0.1:18933` | 前端预览（只读） | 代理 18942，不改动 |

新增/扩展端点（全部只读或平台侧准备，不开放运动）：

| 方法 / 路径 | 行为 | 支持状态 |
|---|---|---|
| GET `/api/v1/mobilecar/execution-recipe` | 配方、来源摘要、所需协议、声明限制 | 已开放 |
| GET `/api/v1/mobilecar/kinematics` | 运动学 profile + 实时一致性 | 已开放 |
| POST `/api/v1/experiment-drafts/{id}/validate` | 生成配置快照；响应新增 `snapshot_id`、`snapshot_sha256`、`execution_eligible`、`blocking_reasons`、`recipe_fingerprint` | 已开放（结果 failed） |
| GET `/api/v1/config-snapshots` / `{id}` | 读取不可变快照 | 已开放 |
| POST `/api/v1/sessions` | 由合格快照创建 prepared Session | **真实环境 409**；夹具可用 |
| GET `/api/v1/sessions` / `{id}` | 读取 prepared/active 与绑定、阻塞项、Start 尝试 | 已开放（当前为空） |
| POST `/api/v1/sessions/{id}/start` | 显式 Start | **真实环境 404**（无 Session）；夹具可用 |

错误码：`snapshot_not_found` 404、`stale_execution_reference`/`recipe_changed`/`validation_incomplete`/`idempotency_conflict`/`session_conflict`/`native_binding_unverified`/`start_preconditions_unmet` 409、`native_offline` 503、`native_start_failed` 502/409。全部返回 `detail.code`，不以空值或旧状态顶替。

## 九、验证范围

| 检查 | 结果 |
|---|---|
| 聚焦回归（服务器，gateway-py314） | **70 passed**：prepare/drafts/geometry/read/api/mobilecar |
| 全量 backend | **74 passed，3 failed**；3 项为 `test_catalog`/`test_migrate`，依赖 sibling 源码检出（`../mobileCar` 需为源码而非服务器运行根）与 `docs/acceptance_report.md`；用**同一基线 8848603** 在相同布局复现同样 3 项失败，非本轮回归 |
| 快照可重现 | 同草案重复校验：同一 `snapshot_id`/`snapshot_sha256`，`reused=true` |
| 真实读取 | recipe/kinematics/validate/snapshot/scene/capabilities/snapshot 全部 200；sessions 409；缺失 Session start 404 |
| 几何候选 | `geometry-2` 200，`content_identity_sha256` 稳定，23 个资产仍按摘要返回（复用既有 bundle，未重导出） |
| native 影响 | PID 941842、run `run_9c88…`、generation 1、episode `episode_43c2…`、`recording=IDLE`、无 owner、`safety_latched=true` 前后一致 |
| 调用形态 | 校验/读取全部 GET；prepared 路径只允许协议声明的两条 POST；夹具断言不存在 `/commands` 与 `/episodes/*` |
| 未验证 | 真实 prepared/Start、RESET 实际生效、录制 begin/停稳/finalize、owner/lease、前端集成、多实例与并发压力 |

## 十、未开放与后续依赖

以下接口边界需与后续阶段一起定义，本轮只保证"不用错误方式绕过"：Owner/lease 与接管、命令 ID/目标版本/TTL、受理态与执行终态、STOP、RESET 实际应用确认、可靠开录（begin without RESET）、停车与 finalize、`require_recording` 的真实门控。`episodes/start` 仍**不能**充当 Prepare 或普通 Start。

本轮交付以"无执行副作用的准备链路及其真实支持范围"为准：**不宣称控制、录制或 M1 闭环完成。**

## 十一、复现

服务器上（候选网关已运行时不要重复启动，也不停止 18941/18942/native）：

```bash
R=~/Desktop/uniRobotPlatform/releases/m12b-20261024T034103Z-4be0d6c86d7b
cd "$R"
UNIROBOT_REPO_ROOT="$R" UNIROBOT_CATALOG="$R/report/catalog.live.yaml" \
  UNIROBOT_DRAFT_DB="$R/report/live-prepare.sqlite3" UNIROBOT_ALLOW_LAUNCH=0 \
  UNIROBOT_PROBE_TIMEOUT=3 \
  UNIROBOT_GEOMETRY_BUNDLE=~/Desktop/uniRobotPlatform/releases/m1-geometry-20261023T192202Z-cdfc7472e5de/geometry \
  PYTHONPATH=backend/src \
  ~/Desktop/uniRobotPlatform/envs/gateway-py314/bin/python -m uvicorn unirobot.api:app --host 127.0.0.1 --port 18943
```

```bash
curl -s http://127.0.0.1:18943/api/v1/mobilecar/execution-recipe
curl -s http://127.0.0.1:18943/api/v1/mobilecar/kinematics
curl -s http://127.0.0.1:18943/api/v1/mobilecar/scene
```

源码 release：`backend/` 42 个输入文件（`src`、`tests`、`config`、`pyproject.toml`、`migration_manifest.json`），聚合 SHA-256 `0905b667de09f3a3d8afe22afb6f8efabb27fd3efe9698aa24037cad0c68f4e3`，上传后逐文件核对。交付文档在测后补写，单独列在服务器 `report/docs-manifest.txt`，不参与源码聚合。真实响应、OpenAPI 与进程记录在服务器 `report/live/` 与 `report/gateway-job.json`，精简副本在 [本目录 evidence](evidence/m1.2b/m12b-20261024T034103Z-4be0d6c86d7b/)；补写文档不改变已验证源码身份。
