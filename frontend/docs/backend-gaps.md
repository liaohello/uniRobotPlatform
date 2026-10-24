# 真实来源、平台配置接入与最小差距

此文件是前端交接记录，不定义第二套公共接口。权威语义仍在后端维护的 `docs/specs/30-contracts`，wire 以 backend 的 mobilecar / drafts / prepare 实现和实际 OpenAPI 为准。

## 已接入（M1.2b 候选 18943）

- `GET /api/v1/mobilecar/scene`（geometry-1 / geometry-2）、`capabilities`、`snapshot`、`scene/assets/{id}?sha256=…`、`kinematics`、`execution-recipe`。
- `GET /api/v1/experiment-drafts`、`POST /api/v1/experiment-drafts`、`GET/PUT /api/v1/experiment-drafts/{id}`、`POST /api/v1/experiment-drafts/{id}/validate`。
- `GET /api/v1/config-snapshots`、`GET /api/v1/config-snapshots/{id}`。
- `GET /api/v1/sessions`、`GET /api/v1/sessions/{id}`。

同源代理按方法+路径白名单转发；保留真实 HTTP 状态、错误体、查询参数和 `Content-Type`。允许的写入仅为 Draft 创建/保存/validate。**不代理** `POST /api/v1/sessions`、`POST /sessions/{id}/start`、运动/停止/RESET/录制/回放、媒体和任何 native 命令端点。

## 已消费的契约字段

| 能力 | 前端使用 | 边界 |
|---|---|---|
| geometry-2 内容/运行身份 | `geometry_binding.content_identity_sha256`、`exported/observed_runtime_identity`、`runtime_identity_matches`、`association`；`geometry_provenance` 的 bundle 与导出身份 | 运行身份变化保留网格/相机/布局，取消旧手势和本地目标；内容身份变化或绑定不一致则明确失效、重载。geometry-1 仍接受，但没有独立内容摘要 |
| 运动学元数据 | `profile.arm.joint_names/zero_model_rad/user_direction`、`tcp.site/parent_body/position_m/orientation_xyzw/orientation_status`、`camera_mount`、`gripper`、`consistency`、`digest`、`authority` | 与 execution-recipe 的 `expected.model_id/model_sha256/scene_id` 和 `kinematics.profile_id/digest` 交叉核对；缺失或不匹配时禁用本地 Joint/TCP 并显示原因，不猜映射、不回退冻结 profile |
| 配置 Draft | `draft_revision`、`execution_revision`、`fingerprint`、`recipe_fingerprint`、`validation.status/result`；保存只用 `base_revision` + `name/description` | 后端 `preset.recipe.editable_initial_state_fields=[]`；没有任意初态、场景编辑或机器人配置写入 |
| 校验结果 | `checks[].{key,status,phase,scope,detail}`、`blocking_reasons`、`execution_eligible`、`validated_snapshot_id`、`reused` | “通过几项”只作摘要；执行资格只看 `execution_eligible`，Session 资格只看后端 Session 状态 |
| 不可变快照 | `snapshot_id/snapshot_sha256/created_at`、checks、`validation_scope`、recipe、observation、kinematics | 快照只 INSERT；重复校验返回同一 id/sha；不把快照当执行许可 |
| Session 读取 | `state`、`execution_eligible`、`start_available`、`native_binding`、`blocking_reasons`、`start_attempts` | 空列表、failed、unsupported 都是正常可解释结果；不把 health、Owner、本地目标或夹具成功当作 Ready |

## 仍然阻塞的能力

| 能力 | 现状 | 前端行为 |
|---|---|---|
| Prepared Session 创建 / 显式 Start | 真实 native 没有无运动绑定协议；平台只对声明 `session_binding_protocol=m1-binding-1` 的 Profile 调用绑定端点。当前真实环境无 Session | 抽屉读取 `GET /sessions` 并显示空/失败原因；本轮未代理 `POST /sessions` 和 start，Start 始终禁用，不显示 Ready |
| 真实校验通过 | 当前 native 为 `g4a1-1.0`，G1 recipe 期望 `g2a-1.0`；configuration 失败，readiness 多项 unsupported | 显示真实 `failed`、`execution_eligible=false`、`validated_snapshot_id=null`、`blocking_reasons` 和逐项检查；不重签、不伪造 Passed |
| 运动学标定 / 原生 attestation | `orientation_xyzw=null`、`orientation_status=not_specified_in_source`；authority 为 `platform_reference_not_native_attested`；零位是用户照片位姿、未标定 | 明确显示“未声明/未标定”；位置 IK 仅本地预览，不代表姿态、碰撞、动力学或执行许可 |
| 控制权 / 命令回执 | 尚无平台认可的 owner/lease、目标版本、命令受理/执行终态和 STOP | 不把原生 Owner 观察值当授权；提交执行、接管、停止保持禁用 |
| 录制 / 回放 / 媒体 | 无 begin-without-RESET、可靠收尾、媒体 reader、连续 Episode | 录制、RESET、播放、媒体下载保持禁用；时间条只显示单帧/只读快照 |
| 部署内容核验 | pin 的场景 XML 摘要和部署配置无法经 native HTTP 独立核验 | 快照的 unsupported 项按原义显示；不把 `resource_matches_pin` 或 health 在线提升为 Passed |

## 当前真实环境结果（2026-10-24 服务器验证）

- 后端候选 `m12b-20261024T034103Z-4be0d6c86d7b`（提交 `4be0d6c`）运行在服务器 18943；前端通过同源代理访问该候选，`geometry-2` + `unirobot-mobilecar-kinematics-1`。
- 真实运行身份 `run_9c88e3e...` / generation 1 / `episode_43c22f...` 前后一致；几何内容身份 `cb789964...18a7cc`，geometry-2 当前 `runtime_identity_matches=true`。运行身份漂移与内容变化路径由自动浏览器夹具验证，没有为制造漂移而 RESET 真实实例。
- `GET /api/v1/sessions` 返回空数组；没有 prepared/active/failed Session。
- `POST /experiment-drafts/{id}/validate` 返回 `validation.status=failed`、`execution_eligible=false`、`validated_snapshot_id=null`。实测快照 17 项检查（12 通过、1 failed、4 unsupported），`validation_scope=motion_free_configuration_and_declared_protocol_only`；具体 snapshot id/sha 与逐项证据见本轮 `config/browser.json` 和 `integration-summary.json`。
- 5 条真实 `blocking_reasons`：`interface_profile`（configuration）；`deployed_config_attestation`、`scene_manifest_attestation`、`session_binding_protocol`、`recording_begin_protocol`（readiness）。界面逐项显示，不用“通过 12/17”替代执行资格。
- 同 release 的代理请求只包含读取与少量平台写入；写请求仅为 Draft create、save、validate（本轮 3 POST / 3 PUT）。没有 Session 创建/start、运动、RESET、录制或 native 命令。
