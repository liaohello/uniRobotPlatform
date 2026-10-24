# 真实来源、平台配置接入与最小差距

此文件是前端交接记录，不定义第二套公共接口。权威语义仍在后端维护的 `docs/specs/30-contracts`，wire 以 backend 的 mobilecar / drafts / prepare 实现和实际 OpenAPI 为准。

## 已接入（M1.3 候选 18953 · 真实地图与路线资源）

- `GET /api/v1/maps` → `{schema_version:"unirobot-map-catalog-1", source:"local_map_packages", live:false, supported, reason, maps:MapVersionView[]}`；Room A/B 为 `g3b_historical_offline` 固定版本，`live=false`、`test_only=false`、`assets_verified=true`、`compatibility.g1_recipe_status=failed`、`navigation_eligible=false`、`current_runtime_status=not_checked`。
- `GET /api/v1/maps/{map_id}/versions/{version}?frame=map`；`GET /api/v1/maps/{map_id}/versions/{version}/image?sha256=<64hex>` 返回 `image/x-portable-graymap` 字节（实测 Room A 为 P5、59×47、maxval 255、2786 B、sha256 `01dcdb38…069d71`）；摘要不符 409 `map_asset_revision_changed`，缺图 404 `map_image_missing`。
- `POST /api/v1/route-drafts`、`GET/PUT /api/v1/route-drafts/{route_id}`（PUT 需 `base_revision`）、`POST /api/v1/route-drafts/{route_id}/publish`（body 仅 `base_revision`）、`GET /api/v1/routes/{route_id}/versions`、`GET /api/v1/routes/{route_id}/versions/{version}`。**没有路线目录/列表 GET**，因此前端只提供按 `route_id` 显式打开的入口。
- 实测响应形状：versions 列表是 `{route_id, versions[]}` 信封；无已发布版本时 404 `route_version_not_found`（前端按空列表处理）；publish 返回 `{route_version, reused}`；保存冲突 409 `{code:"route_draft_revision_conflict", message, current_revision}`；缺 `yaw_rad`/显式 null 为 422；越界/占用为 422 `waypoint_out_of_bounds|waypoint_occupied`；错误帧 409 `map_frame_mismatch`。
- DTO 为 snake_case（`map_ref.map_id`、`x_m/y_m/yaw_rad`、`draft_revision`、`content_digest`、`coordinate_convention.*`、`compatibility.*`、`assets_verified`、`manifest_sha256`）；前端在 `src/adapters/platform-navigation.ts` 单向转换为 camelCase ViewModel，版本 `v1/v2` 字符串与 `content_digest` 全部以后端为准，本地不再生成任何摘要或数字版本。
- 代理白名单只新增上述真实存在的路径（maps 集合/固定版本/image、route-drafts 集合 POST 与单资源 GET/PUT/publish、routes versions 与固定版本 GET）；`GET /api/v1/route-drafts` 这类不存在的集合读方法被显式拒绝，运动、STOP/RESET、`recording/*`、`/runs/{id}/stop`、commands/episodes 与 native 透传继续不代理。

## 候选之间的读取契约差异（本轮实测）

18953 的 `GET /api/v1/mobilecar/scene` 仍是 `unirobot-mobilecar-read-1`（`data_source=live_native_http`，无 `geometry_binding`/`geometry_provenance`），而 18949 已是 `unirobot-mobilecar-geometry-2`。前端严格判定因此拒绝在 18953 上挂载 3D 工作台，并显示“3D 数据源不可用 / 使用冻结原生样本”。地图与路线资源不依赖机器人场景，所以 Scene Setup 已与该门控解耦；3D、Session 与可用性回归改在 18949 上游执行，两者共用同一冻结 dist。

## 已接入（M1.2d 候选 18949）

- `GET /api/v1/sessions` 返回 M1.2d envelope `{source:"stored", live:false, retrieved_at, sessions[]}`；前端解包 `.sessions` 并显示存档来源。
- `GET /api/v1/sessions/{id}` 在存档文档之外新增只读 `current` 观测：`source=live_native_read_only`、`observed_at`、`valid`、`status`、`error`、`runtime_identity(_matches)`、`binding{binding_id,state,matches,readback_sha256,error}`、`snapshot_id/snapshot_eligible/recipe_fingerprint_matches`、`control_scope_granted`、`recording_*`、`owner{state,session_id,lease_expires_at_backend_monotonic_s,lease_exposed}`、`safety_latched`、`recording_ready/motion_ready/start_available/recording_begin_available`、`blockers[]`。
- Session 资格判断只取 `current`；`preflight` 保留为全局 native 诊断。`current.status` 由后端区分 prepared / started / expired / invalidated / released / offline / identity_changed / snapshot_ineligible / unverified，前端不按浏览器时钟推断 backend 单调到期时间。
- 18949 的 `/openapi.json` 路径清单实测不含 map / route / waypoint 端点，因此代理未新增任何路线转发，前端也没有自造 wire（浏览器测试断言无 `/maps|/route|/waypoint` 请求）。

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
| 地图来源（live SLAM / 导航栅格） | 18953 提供 G3B **历史离线**地图（`live=false`），没有 live SLAM 地图端点 | 只读取与显示固定历史版本；界面写明历史包不等于 live SLAM，摘要或尺寸不符即失败，不静默回退离线夹具 |
| Route Draft / Route Version / 采用 | 草案与不可变版本 API 已可用；仍没有“采用此版本到配置”的端点，也没有路线目录列表 | 创建/读取/条件保存/发布/固定版本读取全部走后端；采用按钮禁用并说明原因；路线只能凭 `route_id` 打开 |
| 本地存储冒充服务端 | 上一轮的 `local_session_only` 存储与 `local-` 摘要已删除 | 版本 `vN` 与 `content_digest` 只来自后端；冲突文案改为显示真实 `code` 与 `current_revision` |
| 导航执行 / 目标下发 / 热重规划 | 无 owner/lease、目标代数、规划与安全校验；后端 validation 固定 `execution_supported=false` | 点间连线标为“编辑连线，非规划安全路径”；执行按钮禁用；运行中改目标、重规划、速度发布与导航执行未实现 |

## 当前真实环境结果（18944 / 2026-10-24 服务器验证）

- 后端候选 `m1c-20261024T065943Z-platform`（recipe revision 3，fingerprint `4c3e5f42…5e9e`）运行在 18944；前端通过 18947 预览代理访问该候选，`geometry-2` + `unirobot-mobilecar-kinematics-1` + `preflight`。
- 真实运行身份 `run_9c88e3e...` / generation 1 / `episode_43c22f...` 前后一致；几何内容身份 `cb789964...18a7cc`。运行身份漂移、内容变化、延迟创建/刷新和 binding 失效路径由自动浏览器夹具验证，没有为制造漂移而 RESET 真实实例。
- `GET /api/v1/sessions` 返回空数组；没有 prepared/active/failed Session。
- `GET /api/v1/mobilecar/preflight` 返回真实的当前 native 只读观测：`read_contract_compatible=false`、`session_ready=false`，`interface_profile` 失败；界面显示 `checked_at`，并明确它不是 Session 存档刷新。
- `POST /experiment-drafts/{id}/validate` 返回 `validation.status=failed`、`execution_eligible=false`、`validated_snapshot_id=null`。实测快照 19 项检查，`validation_scope=motion_free_configuration_and_declared_protocol_only`；具体 snapshot id/sha、逐项检查与 6 条 blocking reasons（含 `interface_profile`、配置/场景 attestation、运行时版本、`session_binding_protocol`）见本轮 `config/browser.json` 和 `integration-summary.json`。
- 真实环境不满足创建条件，创建 prepared Session 按钮保持禁用；没有发送真实 `POST /sessions` 或 `/start`。同 release 的真实配置请求只包含读取与 Draft create/save/validate；没有运动、RESET、录制或 native 命令。
- Session 成功交互（创建、幂等重试、独立 Start、拒绝、超时回读、409、binding 失效）只在本轮 `browser-session.py` 的**有状态合成夹具**中验证，不写真实 Session，也不证明 native 部署。
