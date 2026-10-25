# M1.5d｜帧读取分页与角色完整性修正、时间语义分离与历史姿态准备

本轮完成三件正确性修正与一件资源准备：`has_more` 分页判定、角色完整性判定、时间语义命名，以及"历史机器人姿态映射 + 固定模型资源"准备切片。候选地址是联调用途，不是生产部署；使用前请以 `ss -ltnp sport = :18969` 确认存活。

## 冻结身份

| 项 | 值 |
| --- | --- |
| release | `m1v-20261025T161014Z-platform` |
| 地址 | `http://127.0.0.1:18969`（新端口，启动前空闲） |
| 进程 | pid `3923606`，独立会话，owner `liaozhengyan`（见 `launch-registry.json`） |
| 数据库 | `var/reports/m1v-20261025T161014Z-platform/frames-20261025T161014Z.sqlite3`（`existed_before=false`） |
| 源码聚合 | `d022239329c0518d19b4e8d84b14dda7bf740f2beec0a842eadd104fe0f7cba7`（47 文件，根 `src/unirobot + config + tools`） |
| 启动清单 sha256 | `8e32f91f6cf2a24f7786101bc0ec5189671b16d750c5204ed966b8959101ef91` |
| 历史来源 | `mobilecar-server-history-20261017` → `/home/liaozhengyan/Desktop/mobileCar/var/runs`（只读文件） |
| 保留未替换 | 18966（m1s）、18964（m1p）、18960、18959、18953、18949、8792 native；18967（m1t）与 18968（m1u）为本轮中断的检查工具版本，进程与目录保留、不回填 |

## 结果

- 读取断言 **102/102**（`history-check.json`，M1.5c 为 86）；本轮经 `GetProbe` 发出的 **64 条请求全为 GET**，`non_get=[]`。
- 覆盖集合 **946 文件**，事前记录、事后复核 **`drift=[]`**；报告重算源码摘要并断言等于冻结清单（`match: true`）。
- 统一能力回归 **28/28**（geometry-2、capabilities/snapshot/kinematics、Map/Route、Draft、Session/`current`、STOP/end schema 仍在同一进程内）。
- 平台测试：聚焦 `test_frames.py + test_episodes.py` **39 passed**；全量 **167 passed / 3 failed**，三项历史布局失败保留原名与基线：`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`。
- 历史只读面由 6 条 GET 扩为 **8 条**（新增 `robot-state` 与 `model/assets/{asset_id}`），OpenAPI 中全部只有 `get`，无 validate/assessment/eligibility 代理。

## 修正 1｜分页

真实代表帧（303 条持久帧）首页：`{"has_more": true, "next_offset": 1, "next_qualifying_anchor_line_index": 1, "post_page_records_examined": 1}`，行计数 `{"lines_read": 2, "blank_lines_skipped": 0, "oversize_lines_skipped": 0, "unparseable_lines_skipped": 0, "prefiltered_lines_skipped": 0}`。判定改为"整页装满后继续扫描，遇到下一条合格锚点即停"，越过文件末尾才声明没有下一页；隔离夹具覆盖首部/中间空行、坏行、超限行、时间窗口与 offset 组合（`test_frames.py::test_blank_and_unreadable_anchor_lines_are_counted_not_silently_last_page`），未触碰真实归档。

## 修正 2｜角色完整性

图像观测要求"必需 `sensor_kind` 各恰一条"：真实每帧 `matched_kinds=["depth","rgb"]`、`missing_kinds=[]`、`duplicate_kinds=[]`。新增状态 `ambiguous_kind`（同一必需 kind 多行）与 `ambiguous_candidates`（单记录角色多候选），并按公开优先级 `stream_absent > identity_mismatch > ambiguous_kind > ambiguous_candidates > partial > missing/unresolved_reference > matched` 判定。夹具证明"重复 rgb 且缺 depth"不得 `matched`、重复状态候选不得只取第一条（此时 `recorded_state=null`、`single_state_selected=false`、全部候选与冲突标记列出）。声明引用 `unresolved_reference` 与主角色完整性仍分开（真实记录 3/303 能解析 `feedback_sample_id`）。

## 修正 3｜时间语义

`times.quantities` 按"记录 + 字段 + 单位 + 符号 + 含义"命名每条差值；`times.age_of_state_relative_to_frame` 已随 `frame-link-1 → frame-link-2` 迁移移除，`version_migration` 字段说明原因与替代键。真实首帧三个不同量：

| 键 | 字段 | 相对采集 |
| --- | --- | --- |
| `state_event_write_minus_frame_capture` | 事件信封 `backend_monotonic_s` | −2.885407 ms |
| `state_payload_feedback_time_minus_frame_capture` | 状态负载 `feedback_time_monotonic` | −3.669841 ms |
| `recorder_declared_feedback_time_minus_frame_capture` | 计时负载 `feedback_time_s` | −3.668296 ms |

另给出 `state_payload_feedback_time_minus_state_event_write` = −0.784434 ms、`sim` 基差值 0（`sim_time_s` 与 `capture_sim_time_s` 同为 0.14，不同基不折算）、`persist_minus_capture` = 100.025438 ms；`recorder_declared` 原样复制录制器自己的 `observation_age_ms = 33.451169`、`capture_to_render_complete_ms`、`capture_to_publish_complete_ms` 等，并附重算的 `arrival − capture = 33.451169 ms` 与一致性判定——它是管线延迟，不是状态采样年龄。`clock_sameness` 现同时给出记录里命名同钟的字段清单、写入版本绑定范围（`contract_version`、`software {name, version: 0.1.0}`、`profile_sha256 9473171d7460ba96…`；不含 native release/构建/提交）与 `synchronized_upgraded_by_numeric_closeness: false`。

## 准备切片｜历史姿态与固定模型

`GET /api/v1/episodes/{episode_id}/robot-state?run_id=&sample_id=`（schema `unirobot-mobilecar-history-pose-1`）复用同一关联规则取该帧状态，并给出：

- 模型身份比对：run 清单 `contract_version/model_id/model_sha256/scene_id` 与冻结 bundle `resource_identity` 四项全等（`status: "match"`）；bundle `bundle.json` 文件摘要 `a5f4a90ca5988ba0…`、provenance `bundle_sha256 275389464eee2f3d…`、71 links、23 个逐文件校验过的 mesh 资产、`tcp_site=grasp_tcp`、`camera_ids=[rgbd]`。导出时的 `runtime_identity` 属于另一次运行，已在响应中区分标注。
- 映射状态（9 项目标，1 项达 `partially_verified`）：`arm_joint_positions` `partially_verified`（5 值 ↔ `joint1…joint5`，逐位凭证只到索引 3：记录 model/user 恰在索引 3 差 `−π/2`，平台配置该处写为四舍五入的 `−1.5708`）；`base_position`、`base_orientation`、`gripper_joints`、`tcp_site_position` `unverified`；`camera_extrinsics`、`dynamic_scene_objects` `missing`；`wheel_joint_velocities`、`base_twist` `not_required_for_pose`。所有条目 `no_default_applied: true` 且带精确 `gap`；`pose_readiness.robot_state_can_be_rebuilt_without_assumptions = false`。
- `GET /api/v1/episodes/{episode_id}/model/assets/{asset_id}` 只从冻结 bundle 出字节（逐请求重算摘要、ETag、`X-UniRobot-Model-Source: frozen_compiled_geometry_bundle`），并在服务前要求该 Episode 的模型身份与 bundle 相符；不调用当前 `/mobilecar/scene`、snapshot 或 Actual。动态世界物体（如 `target_cube`）无历史位姿记录，响应明确 `render_from_record: false`，不伪造。
- `rendering.verified = false`、`frontend_assembly_done = false`：资源就绪与身份/映射校验通过不等于历史渲染通过，装配与姿态正确性留给下一轮前端。

## 文件

- `history-check.json` 102 项断言明细；`history-startup.json` 冻结启动清单；`launch-registry.json` 进程身份与所有权；`coverage-digests.json` 946 文件事前/事后摘要；`get-probe-log.json` / `get-probe-log.jsonl` 64 条 GET 证据。
- `unified-on-history-candidate.json` 28 项既有能力回归；`history-replay-facts.json` 流与记录事实。
- `frame-sample-complete.json`、`frame-sample-second-page.json`、`frame-page-after-lookahead.json`、`frame-sample-incomplete.json` 真实帧页样例；`robot-state-sample.json`、`robot-state-by-sample.json`、`robot-state-incomplete.json` 姿态准备样例；`error-unsupported-time-base.json`、`error-invalid-sample-id.json`、`error-unknown-model-asset.json` 错误面样例；`openapi.json` 8 条历史 GET 路径。

## 边界

未执行录制、运动、RESET、STOP/end、重启或新物理实例；未修改归档或历史 tail；未改 native 与前端；18966/18964/其他后端与前端预览未被替换。历史归档未全量验证、跨流同步游标未定义、同步回放与 M1/M1.5 正式验收未通过。
