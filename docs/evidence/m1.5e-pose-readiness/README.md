# M1.5e｜时间量来源、机械臂映射证据与按部件渲染就绪

契约唯一来源是 [Episode/事件/标注契约](../../specs/30-contracts/03-episode-events-annotations.md)；实现说明见 [M1.5e 交付记录](../../backend-m1.5e-pose-readiness-and-time-sources.md)；事实来源为 [S25](../../specs/90-governance/sources/S25-time-sources-and-pose-readiness.md)，决策为 [DEC-062](../../specs/90-governance/01-decisions.md#dec-062)。本册证据分三类：**真实归档实测**、**源码证据**、**隔离夹具**，不互相顶替。

## 冻结身份

| 项 | 值 |
| --- | --- |
| release | `m1x-20261026T065320Z-platform` |
| 前端唯一基址 | `http://127.0.0.1:18970`（新端口，启动前空闲；用前 `ss -ltnp sport = :18970` 确认存活） |
| 进程 | pid `3256687`，owner `liaozhengyan`，独立会话（`launch-registry.json`） |
| 数据库 | `var/reports/m1x-20261026T065320Z-platform/frames-20261026T065320Z.sqlite3`（`existed_before=false`） |
| 源码聚合 | `df124d886e652f03534ca146b7b261d19af318c45fd434c8f90cb8628cbcb063`（49 文件，根 `src/unirobot + config + tools`） |
| 启动清单 sha256 | `6209e493cc23443e739a3fcdedb959102d413ee184048f04eff4a4002b7802eb` |
| 模型资源 | 冻结 bundle `m1-geometry-20261023T192202Z-cdfc7472e5de/geometry`（provenance `bundle_sha256 275389464eee2f3d…`） |

## 结果

- 历史读取断言 **110/110**（M1.5c 86 → M1.5d 102 → 本轮 110）；`GetProbe` **64 条请求全为 GET**；覆盖集合 **946 文件 `drift=[]`**；报告重算源码摘要并断言等于冻结清单（`match: true`）。
- 统一能力回归 **28/28**（geometry-2、Map/Route、Draft、Session/`current`、STOP/end schema 仍在同一进程）。
- 平台测试：聚焦 **45 passed**（`test_frames.py` + `test_history_fk.py` + `test_episodes.py` 相关）；全量 **179 passed / 3 failed**，三项历史布局失败保留原名与基线。
- 历史只读面仍为 8 条 GET（`openapi.json`），全部只有 `get`，无 validate/assessment/eligibility 代理。

## 时间量来源（真实 + 夹具）

真实首帧 `rgbd_e3213e6cb64b4cd693c17d485d064d09`（`frame-sample-complete.json`）：

| 键 | 来源记录 | 字段 | 相对采集 |
| --- | --- | --- | --- |
| `state_event_write_minus_frame_capture` | 状态事件信封 | `backend_monotonic_s` | −2.885407 ms |
| `state_payload_feedback_time_minus_frame_capture` | 状态事件负载 | `feedback_time_monotonic` | −3.669841 ms |
| `recorder_declared_feedback_time_minus_frame_capture` | 计时事件负载 | `feedback_time_s` | −3.668296 ms |
| `state_sim_time_minus_frame_capture_sim_time` | 状态事件**负载** | `sim_time_s` | 0（负载与采集同为 0.14） |
| `state_event_envelope_sim_time_minus_frame_capture_sim_time` | 状态事件**信封** | `sim_time_s` | 0 |
| `persist_minus_capture` | 持久帧 | `persist_backend_monotonic_s` | 100.025438 ms |

`recorder_declared.fields.observation_age_ms = 33.45116903074086` 与 `recomputed_arrival_minus_capture_ms = 33.45116903074086` 一致（`agrees_with_recomputation: true`），并注明它是采集→到达的管线延迟、不是状态采样年龄。负载量不再由信封回退：夹具用例覆盖负载缺失、负载非数值字符串、负载与信封同存且不同值（`tests/test_frames.py::test_a_missing_payload_sim_time_is_never_filled_from_the_envelope`）。

## 机械臂映射证据（源码）

- `ARM_JOINTS = tuple(f"joint{i}" for i in range(1, 6))`（`backends/modelgen/model/arm.py:10`）；`ArmController.qpos = model.jnt_qposadr[[model.joint(name).id for name in ARM_JOINTS + (GRIPPER_DRIVE,)]]`（`control/arm.py:12-14`）；序列化 `self.data.qpos[self.arm.qpos[:5]]`（当前源码 `backends/mujoco/backend.py:3385`）→ 五值即 `joint1…joint5` 的模型弧度，夹爪驱动（索引 5）被切掉。
- 逐文件摘要亲自复核：本地 `a5cef52` 的 `arm.xml/chassis.xml/robot.xml/control/arm.py/modelgen-model arm.py/sensors/scene.py/arm_spec.json` 与 drvfix 冻结清单相等；`backends/mujoco/backend.py` 不等（`de7a889d…` vs `108dc2d5…`）。
- 同日冻结快照 `g2a-20261017T155919Z…`、`…T160655Z…`、`…T160903Z…`（该 run 创建于 `2026-10-17T16:09:20.027084Z`）含同一链（其 `backend.py:1386`）与同一 `arm.xml 794b0c38e0c69643…`、`robot.xml 3ca3d6d0a92a48bb…`。
- 边界：记录不带 release/构建/提交标识 → 写入者只收窄到该发布族；`drvfix-20261019T044549Z` 晚于归档且 `backend.py` 与检出不同，非写入者。响应 `version_binding.writer_identified = false`。

## 运动学对照（`history-fk-check.json`）

| 项 | 实测 |
| --- | --- |
| 抽样 | 152 / 303 帧（stride 2），跳过 0 |
| 主约定误差 | min 1.61145e-14、median 1.66139e-14、p95 1.66809e-14、**max 1.68974e-14 m** |
| 叠加 `base_link` 本体偏移的替代约定 | 误差恒 **0.0556000 m** → 排除 |
| 反序映射（诊断，非拟合目标） | 误差 median 0.20967 m → 顺序确受检 |
| bundle 臂序 vs 平台配置臂序 | `orders_equal: true` |
| 关节行程 rad | joint1 0.035345／joint2 0.002927／joint3 0.002214／joint4 0.001287／joint5 0.035077（`unexercised_joints: []`） |
| 底盘位移范围 m | x 0.051060／y 0.004595／z 0.000327 |

单帧端点侧（`robot-state-sample.json`）：`verdict = consistent`，`abs_error_m = 1.6454375138849238e-14`，替代假设 `inconsistent` 且误差 0.0556000…，`joints_left_at_zero = []`，链路 `base_link → link1…link5 → gripper_link → guide_rod_link`。结论只支持运动学一致性，不校准硬件、不证明写入构建、不证明渲染外观。

## 按部件就绪（`robot-state-sample.json`）

`part_readiness`：`fixed_model_reference_assembly = ready`；`arm_local_pose / base_pose_placement / tcp_position_marker = ready_with_caveats`；`gripper_visual_appearance = conditional`；`tcp_orientation_frame / camera_view_from_record / dynamic_scene_objects_from_record = blocked`；`wheel_pose_from_record = not_required`。每项带 `requires`、`pose_input_required`、`inputs_available`、`frontend_rule`、`gaps`。

`capability_summary`：`fixed_model_assembly_available = true`、`whole_robot_pose_rebuildable = false`、`escalation_forbidden`、`defaults_forbidden`、`kinematic_agreement = consistent`、`abs_tcp_error_m = 1.6454e-14`。

`mapping` 状态：`arm_joint_positions / base_position / base_orientation / tcp_site_position = verified`（附 `verified_basis`），`gripper_joints = unverified`，`tcp_site_orientation / camera_extrinsics / dynamic_scene_objects = missing`，`wheel_joint_velocities / base_twist = not_required_for_pose`；10 项目标 4 项已验证，`robot_state_can_be_rebuilt_without_assumptions = false`。

## 对 M1.5d 两项表述的更正

1. 平台配置 `arm.zero_model_rad[3]` 实为 `-1.5707963267948966`（精确 `-π/2`），M1.5d 所称"配置写成 `-1.5708` 四舍五入值"不成立（该字面量只出现在 M1.5d 文档自身）。
2. 夹爪并非"任何来源都没有换算规则"：平台配置声明了 `zero_width_m 0.025`、`width_per_drive_rad_m 0.023199`、`jaw_origin_correction_m 0.00052438637918234`、`source_gap_m 0.04895122724163532` 与四条 `mimic` 关系；缺的是 native 背书与逐值验证，故仍为 `unverified`。M1.5d 交付文档保留原文并附更正段，不倒填。

## 文件

`history-check.json`（110 项断言）、`history-fk-check.json`（离线运动学抽样统计）、`history-startup.json`、`launch-registry.json`、`coverage-digests.json`、`get-probe-log.{json,jsonl}`、`unified-on-history-candidate.json`、`history-replay-facts.json`、`openapi.json`；样例 `frame-sample-{complete,second-page,incomplete}.json`、`frame-page-{after-lookahead,two}.json`、`robot-state-{sample,by-sample,incomplete}.json`；错误面 `error-{unsupported-time-base,invalid-sample-id,unknown-model-asset}.json`。

## 边界

未启动新物理实例，未执行运动/RESET/录制/STOP-end/重启；未修改历史归档、tail、native、生产配方与 pin；未改 `frontend/`。保留 18969（m1v）、18966（m1s）、18964（m1p）、18965、18960、18959、18953、18949 与 18961/18962/18963（他人服务）、8792；本轮中断前的 scratch 实例已停止，未留下监听端口。历史归档未全量验证、跨流同步游标未定义、前端装配与姿态视觉核对未做、M1.5/M1 正式验收未通过。
