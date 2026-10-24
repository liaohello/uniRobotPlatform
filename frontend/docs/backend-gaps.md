# 真实来源、平台配置接入与最小差距

此文件是前端交接记录，不定义第二套公共接口。权威语义仍在后端维护的 `docs/specs/30-contracts`，wire 以 backend 的 mobilecar / drafts / prepare 实现和实际 OpenAPI 为准。

## 已接入（M1.2c 候选 18944）

- `GET /api/v1/mobilecar/scene`（geometry-1 / geometry-2）、`capabilities`、`snapshot`、`scene/assets/{id}?sha256=…`、`kinematics`、`execution-recipe`、`preflight`。
- `GET /api/v1/experiment-drafts`、`POST /api/v1/experiment-drafts`、`GET/PUT /api/v1/experiment-drafts/{id}`、`POST /api/v1/experiment-drafts/{id}/validate`。
- `GET /api/v1/config-snapshots`、`GET /api/v1/config-snapshots/{id}`。
- `GET /api/v1/sessions`、`GET /api/v1/sessions/{id}`、`POST /api/v1/sessions`（创建 prepared）、`POST /api/v1/sessions/{id}/start`（显式 Start）。

同源代理按方法+路径白名单转发；保留真实 HTTP 状态、错误体、查询参数和 `Content-Type`。允许的写入为 Draft 创建/保存/validate 以及平台 Session 创建/Start。**不代理** 运动/停止/RESET、`recording/begin`/finalize、回放、媒体和任何 native 命令端点。代理放行不授予执行资格，资格仍由 18944 判定。

## 已消费的契约字段

| 能力 | 前端使用 | 边界 |
|---|---|---|
| geometry-2 内容/运行身份 | `geometry_binding.content_identity_sha256`、`exported/observed_runtime_identity`、`runtime_identity_matches`、`association`；`geometry_provenance` 的 bundle 与导出身份 | 运行身份变化保留网格/相机/布局，取消旧手势和本地目标；内容身份变化或绑定不一致则明确失效、重载。geometry-1 仍接受，但没有独立内容摘要 |
| 运动学元数据 | `profile.arm.joint_names/zero_model_rad/user_direction`、`tcp.site/parent_body/position_m/orientation_xyzw/orientation_status`、`camera_mount`、`gripper`、`consistency`、`digest`、`authority` | 与 execution-recipe 的 `expected.model_id/model_sha256/scene_id` 和 `kinematics.profile_id/digest` 交叉核对；缺失或不匹配时禁用本地 Joint/TCP 并显示原因，不猜映射、不回退冻结 profile |
| 配置 Draft | `draft_revision`、`execution_revision`、`fingerprint`、`recipe_fingerprint`、`validation.status/result`；保存只用 `base_revision` + `name/description` | 后端 `preset.recipe.editable_initial_state_fields=[]`；没有任意初态、场景编辑或机器人配置写入 |
| 校验结果 | `checks[].{key,status,phase,scope,detail}`、`blocking_reasons`、`execution_eligible`、`validated_snapshot_id`、`reused` | “通过几项”只作摘要；执行资格只看 `execution_eligible`，Session 资格只看后端 Session 状态 |
| 不可变快照 | `snapshot_id/snapshot_sha256/created_at`、checks、`validation_scope`、recipe、observation、kinematics | 快照只 INSERT；重复校验返回同一 id/sha；不把快照当执行许可 |
| Session 读取 | `state`、`execution_eligible`、`start_available`、`native_binding`、`execution{source,observed_at,control_scope_granted,owner,recording_*,motion_*}`、`blocking_reasons`、`start_attempts`、`start_receipt`、`recording_begin_*` | 空列表、failed、unsupported 都是正常可解释结果；`GET /sessions` 只读动作存档，不刷新 native；不把 health、Owner、本地目标或夹具成功当作 Ready |
| Session 创建 / Start | `POST /sessions` 使用 validated snapshot、execution_revision、fingerprint、幂等键；`POST /sessions/{id}/start` 无 body，前置回读 binding/身份/owner/recording/safety | 创建与 Start 分离；不自动创建、不自动 Start；超时显示结果未知并回读存档；409/失效/离线/拒绝原样显示；当前真实环境因快照不合格保持禁用 |
| 新鲜度 | `execution.source/observed_at` 仅在 prepare/start/recording-begin 更新；`GET /mobilecar/preflight` 提供 `checked_at` 当前 native 只读观测 | 存档刷新与 native 观测刷新分开；binding/身份失效取消旧手势与本地目标并禁用 Start，同内容网格/相机/布局保留 |

## 仍然阻塞的能力

| 能力 | 现状 | 前端行为 |
|---|---|---|
| 真实 Prepared Session 创建 / 显式 Start | 平台 18944 已实现创建/Start 与 `m1-binding-1` 校验，但运行中的 8792 未部署 native 补丁且 profile 为 G4A2；真实快照仍 `execution_eligible=false` | 创建按钮只在 validated+eligible 快照上启用；真实环境保持禁用。Start 仅在 prepared + `start_available` + binding verified + 身份新鲜时启用；本轮没有对真实环境发送创建/Start |
| 真实校验通过 | 当前 native 为 `g4a1-1.0`，G1 recipe 期望 `g2a-1.0`；configuration 失败，readiness 多项 unsupported | 显示真实 `failed`、`execution_eligible=false`、`validated_snapshot_id=null`、`blocking_reasons` 和逐项检查；不重签、不伪造 Passed |
| 运动学标定 / 原生 attestation | `orientation_xyzw=null`、`orientation_status=not_specified_in_source`；authority 为 `platform_reference_not_native_attested`；零位是用户照片位姿、未标定 | 明确显示“未声明/未标定”；位置 IK 仅本地预览，不代表姿态、碰撞、动力学或执行许可 |
| 控制权 / 命令回执 | 尚无平台认可的 owner/lease、目标版本、命令受理/执行终态和 STOP | 不把原生 Owner 观察值当授权；提交执行、接管、停止保持禁用 |
| 录制 / 回放 / 媒体 | 无 begin-without-RESET、可靠收尾、媒体 reader、连续 Episode | 录制、RESET、播放、媒体下载保持禁用；时间条只显示单帧/只读快照 |
| 部署内容核验 | pin 的场景 XML 摘要和部署配置无法经 native HTTP 独立核验 | 快照的 unsupported 项按原义显示；不把 `resource_matches_pin` 或 health 在线提升为 Passed |

## 当前真实环境结果（18944 / 2026-10-24 服务器验证）

- 后端候选 `m1c-20261024T065943Z-platform`（recipe revision 3，fingerprint `4c3e5f42…5e9e`）运行在 18944；前端通过 18947 预览代理访问该候选，`geometry-2` + `unirobot-mobilecar-kinematics-1` + `preflight`。
- 真实运行身份 `run_9c88e3e...` / generation 1 / `episode_43c22f...` 前后一致；几何内容身份 `cb789964...18a7cc`。运行身份漂移、内容变化、延迟创建/刷新和 binding 失效路径由自动浏览器夹具验证，没有为制造漂移而 RESET 真实实例。
- `GET /api/v1/sessions` 返回空数组；没有 prepared/active/failed Session。
- `GET /api/v1/mobilecar/preflight` 返回真实的当前 native 只读观测：`read_contract_compatible=false`、`session_ready=false`，`interface_profile` 失败；界面显示 `checked_at`，并明确它不是 Session 存档刷新。
- `POST /experiment-drafts/{id}/validate` 返回 `validation.status=failed`、`execution_eligible=false`、`validated_snapshot_id=null`。实测快照 19 项检查，`validation_scope=motion_free_configuration_and_declared_protocol_only`；具体 snapshot id/sha、逐项检查与 6 条 blocking reasons（含 `interface_profile`、配置/场景 attestation、运行时版本、`session_binding_protocol`）见本轮 `config/browser.json` 和 `integration-summary.json`。
- 真实环境不满足创建条件，创建 prepared Session 按钮保持禁用；没有发送真实 `POST /sessions` 或 `/start`。同 release 的真实配置请求只包含读取与 Draft create/save/validate；没有运动、RESET、录制或 native 命令。
- Session 成功交互（创建、幂等重试、独立 Start、拒绝、超时回读、409、binding 失效）只在本轮 `browser-session.py` 的**有状态合成夹具**中验证，不写真实 Session，也不证明 native 部署。
