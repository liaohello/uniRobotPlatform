# M1.5e｜时间量来源修正、机械臂映射证据与按部件历史渲染就绪（2026-10-25）

状态：候选实现完成并在服务器验证；不等于历史整车渲染可用、跨流同步回放可用，或 M1.5/M1 验收通过。

契约唯一权威来源是 [Episode/事件/标注契约](specs/30-contracts/03-episode-events-annotations.md)。本文件记录实现取舍与实测证据；事实来源登记为 [S25](specs/90-governance/sources/S25-time-sources-and-pose-readiness.md)，决策为 [DEC-062](specs/90-governance/01-decisions.md#dec-062)，明细见 [M1.5e 证据册](evidence/m1.5e-pose-readiness/README.md)。

## 前端使用基址

唯一基址：`http://127.0.0.1:18970`（候选 `m1x-20261026T065320Z-platform`，用前 `ss -ltnp sport = :18970` 确认存活）。

- `GET /api/v1/episodes/{episode_id}/frames?run_id=&limit=&offset=&time_base=&time_from=&time_to=&sample_id=` → `unirobot-mobilecar-frame-link-2`
- `GET /api/v1/episodes/{episode_id}/robot-state?run_id=&sample_id=` → `unirobot-mobilecar-history-pose-1`
- `GET /api/v1/episodes/{episode_id}/model/assets/{asset_id}?sha256=` → 冻结 bundle 网格字节（ETag = `"sha256:<digest>"`，`X-UniRobot-Model-Source: frozen_compiled_geometry_bundle`）

装配规则：先按 `model_resource.status == "match"` 与 `part_readiness[*].status` 决定画什么；`frontend_rule` 是每项能力的使用约束；`capability_summary.whole_robot_pose_rebuildable == false` 只限制整车重建，不限制固定模型装配。

## 1. sim 时间量来源修正

`frames.py` 此前在 `payload.sim_time_s` 缺失或非数值时回退取事件信封的 `sim_time_s`，却仍把该值标为负载来源。现拆成两个各自命名的量（`SIM_TIME_QUANTITIES`）：

- `state_sim_time_minus_frame_capture_sim_time` ← 状态反馈**负载** `sim_time_s`；负载无该字段或非数值时**该量直接缺失**，不回退。
- `state_event_envelope_sim_time_minus_frame_capture_sim_time` ← 状态反馈**事件信封** `sim_time_s`。

每条都带 `source_record/field/unit/clock/meaning/other_value/capture_value/value/abs_ms/direction/line_index`。`version_migration` 新增 `corrections` 记录这次标注更正（frame-link-2 内不改 schema，因为"负载量=负载字段"的语义未变，只是此前可能被别的记录填充）；响应 `times.sim_time_quantity_keys` 列出两个键。真实记录首帧实测两个量都是 0（负载与信封的 `sim_time_s` 均为 0.14，等于 `capture_sim_time_s`），且 `source_record` 不同。隔离夹具覆盖三种情形：负载缺失、负载为非数值字符串、负载与信封同时存在且数值不同。

## 2. 机械臂映射证据链（源码证据）

`arm_model_qpos_rad` 的五值顺序不再是推测：native 源码按**名字**取 qpos。

- `src/mobilecar/backends/modelgen/model/arm.py:10` `ARM_JOINTS = tuple(f"joint{i}" for i in range(1, 6))`；`GRIPPER_DRIVE = "gripper_base_joint"`
- `src/mobilecar/control/arm.py:12-14` `names = ARM_JOINTS + (GRIPPER_DRIVE,)`；`joints = [model.joint(n).id …]`；`qpos = model.jnt_qposadr[self.joints]`
- `src/mobilecar/backends/mujoco/backend.py:3385` `"arm_model_qpos_rad": self.data.qpos[self.arm.qpos[:5]].tolist()`（索引 5 是夹爪驱动，被切掉）
- `assets/landerpi/model/arm.xml` 中 `joint1…joint5` 文档顺序与之一致（巧合，不起决定作用）

版本可绑定范围（本轮亲自复核，不采信二手结论）：本地 native 检出 `a5cef52`（工作区脏：app.py、cli.py、config.py、contracts/models.py、data/recorder.py 被改），其中 `arm.xml`、`control/arm.py`、`modelgen/model/arm.py`、`sensors/scene.py`、`arm_spec.json`、`chassis.xml`、`robot.xml` 与 drvfix 冻结清单逐文件摘要相等，而 `backends/mujoco/backend.py` **不等**（磁盘/HEAD `de7a889d…` vs 清单 `108dc2d5…`）。录制当天的三个冻结快照 `g2a-20261017T155919Z…`、`…T160655Z…`、`…T160903Z…`（该 run 的 `created_wall_utc = 2026-10-17T16:09:20.027084Z`）都含同一链：`ARM_JOINTS`（modelgen/model/arm.py:10）、`model.jnt_qposadr`（control/arm.py:14）、`arm_model_qpos_rad = data.qpos[self.arm.qpos[:5]]`（该版本 backend.py:1386），且 `arm.xml 794b0c38e0c69643…`、`robot.xml 3ca3d6d0a92a48bb…` 与记录里的 `model_sha256` 相等。限制保留：记录本身不带 release/构建/提交标识，因此只能把写入者**收窄**到该发布族，不能指认唯一构建；`drvfix-20261019T044549Z` 晚于归档且其 `backend.py` 与当前检出不同，不是这批记录的写入者。不编造旧提交或构建身份。

## 3. 模型角与用户角分离

`arm_joint_positions` 明确 `draw_source = "model radians, applied directly to the hinge joints"`、`requires_user_angle_conversion = false`；新增 `model_vs_user_angles` 块把用户坐标公式与零位单独报告：`conversion_is_required_for_drawing = false`，`user_angle_formula.used_for = "user-facing display and limit comparison only"`，零位权威为 `zero_status = "user_defined_photo_pose_not_hardware_500"`、`calibration_session = "uncalibrated"`、`authority = "platform_reference_not_native_attested"`。配置 `arm.joint_names` 与 bundle 臂铰接名逐项相等（`config_joint_names_equal_bundle_arm_hinges = true`）。历史值不修改，用户照片零位不称为硬件标定。

**对 M1.5d 两处表述的更正**（原交付文档保留原文并附更正段）：

1. M1.5d 写"平台配置该处写为 `-1.5708` 四舍五入值"——不成立。`backend/config/mobilecar-landerpi-kinematics-v1.json` 的 `arm.zero_model_rad[3]` 实为 `-1.5707963267948966`（精确 `-π/2`），与记录中 model/user 数组在索引 3 的差值逐位相符；仓库里 `-1.5708` 只出现在 M1.5d 那份文档自身。
2. M1.5d 写"任何来源都不存在把宽度换算成夹爪关节值的规则"——过头了。平台配置声明了 `gripper.zero_width_m / width_per_drive_rad_m / jaw_origin_correction_m / source_gap_m` 与四条 `mimic` 关系（附 `parameters.yaml`、`arm_spec.json`、`landerpi_nominal.yaml` 摘要）；缺的是 native 侧背书与逐值验证，因此该映射仍是 `unverified`（不是"无规则"），也不作为绘制必经步骤。

## 4. 按部件划分的就绪

`robot-state` 新增 `part_readiness`（9 项能力）、`part_status_meaning`、`capability_summary`，`mapping` 状态改为**由证据决定**。真实首帧实测：

| 能力 | 状态 | 前端规则要点 |
| --- | --- | --- |
| `fixed_model_reference_assembly` | `ready` | 身份匹配即可装配固定模型，不需要任何 pose 输入 |
| `arm_local_pose` | `ready_with_caveats` | 五个模型弧度直接驱动 `joint1…joint5`，不经过用户角；样本未动的轴不得声称已验证 |
| `base_pose_placement` | `ready_with_caveats` | 底盘位姿可用，但须并列展示"写入版本仅收窄到发布族"这一限制 |
| `gripper_visual_appearance` | `conditional` | 只有接受平台声明常量（非 native 背书）才可依宽度摆位 |
| `tcp_position_marker` | `ready_with_caveats` | 只画点标记；无朝向记录 |
| `tcp_orientation_frame` | `blocked` | 不得合成朝向框架 |
| `camera_view_from_record` | `blocked` | 无标定；声明的安装体不刚性等同 TCP |
| `dynamic_scene_objects_from_record` | `blocked` | 世界物体保持 bundle 初始布局并标注非历史状态 |
| `wheel_pose_from_record` | `not_required` | 静态摆位不需要轮角 |

`capability_summary`：`usable_now = [fixed_model_reference_assembly, arm_local_pose, base_pose_placement, tcp_position_marker]`，`usable_only_with_the_named_caveat = [gripper_visual_appearance]`，`blocked = [tcp_orientation_frame, camera_view_from_record, dynamic_scene_objects_from_record]`，`fixed_model_assembly_available = true`，`whole_robot_pose_rebuildable = false`，`escalation_forbidden`、`defaults_forbidden`。映射状态实测：`arm_joint_positions / base_position / base_orientation / tcp_site_position = verified`，`gripper_joints = unverified`，`tcp_site_orientation / camera_extrinsics / dynamic_scene_objects = missing`，轮速与 twist `not_required_for_pose`（10 项目标中 4 项已验证）。

## 5. 可证明映射的独立运动学检查

新增纯运动学模块 `backend/src/unirobot/history_fk.py`（不依赖 MuJoCo/numpy/native，约定取自 native 场景导出器的字段含义：link 的 `local_transform` 是 MuJoCo `body_pos/body_quat`（父体参考系，wxyz→xyzw），`joint_axis` 是子体参考系下的 `jnt_axis`），并在 `robot-state` 内对**本帧**给出 `tcp_kinematic_cross_check`；离线工具 `backend/tools/history_fk_check.py` 直接读归档与冻结 bundle，对**整条记录**做抽样统计。两种根坐标约定同时检验，不预设其一：

- 真实结果：抽样 152/303 帧，`kinematic_consistency_holds`，误差 max `1.6897430535684736e-14 m`（median `1.6614e-14`），逐轴差 ~1e-14；
- 另一约定（再加一次 `base_link` 本体偏移 0.0556）误差恒为 `0.05560000…m` → 被明确排除；
- 反序映射误差 median `0.20967 m` → 顺序确受检验；bundle 文档序与配置序 `orders_equal = true`；
- 五个关节行程范围 joint1 0.035345、joint2 0.002927、joint3 0.002214、joint4 0.001287、joint5 0.035077 rad（`unexercised_joints = []`），底盘位移范围 x 0.05106、y 0.004595、z 0.000327 m；
- 单帧端点侧：`verdict = consistent`，`abs_error_m = 1.6454e-14`，`joints_left_at_zero = []`。

这只支持运动学一致性：不校准硬件、不证明渲染外观、不指认写入构建；未动过的轴不被宣布验证过（本轮无未动轴）。缺证据的底盘/夹爪/相机只限制各自能力，不要求一次解决全部目标，缺口以最小形式列出。

## 契约与兼容

`frame-link-2` 与 `history-pose-1` 均**未升版**：新增键（`sim_time_quantity_keys`、`arm_mapping_chain`、`version_binding`、`model_vs_user_angles`、`tcp_kinematic_cross_check`、`part_readiness`、`part_status_meaning`、`capability_summary`、映射条目 `verified_basis/draw_source/requires_user_angle_conversion`）为附加式变更；唯一标注语义修正在 `version_migration.corrections` 内说明并给出替代键。`robot-state` 端点新增一次纯算术 FK（无额外 IO），身份不符时仍返回 `not_computable`。

## 服务器验证

- 候选 `m1x-20261026T065320Z-platform`（`127.0.0.1:18970`，PID 3256687，独立 SQLite `frames-20261026T065320Z.sqlite3`，源码聚合 `df124d886e652f03…`／49 文件，清单 sha256 `6209e493cc23443e…`，报告重算断言 MATCH）。
- 历史读取断言 **110/110**（M1.5d 为 102）；`GetProbe` 64 条请求全为 GET；946 文件覆盖集合 `drift=[]`。
- 统一能力回归 **28/28**；聚焦 **45 passed**；全量 **179 passed / 3 failed**，三项历史布局失败保留名称与基线。
- 未启动新物理实例，未执行运动/RESET/录制/STOP-end/重启；未修改归档、tail、native、生产配方或 pin；未改 `frontend/`；18969/18966/18964/18960/18959/18953/18949/8792 与 18961/18962/18963（他人服务）全部未替换。
- 过程记录：新增断言先在**同源码 scratch 实例**（临时端口、临时 SQLite，验证后停止）跑绿，再冻结 `m1x`，避免把工具缺陷留在不可变 release 上；此前 18969 上跑出的两次失败均为断言针对旧版行为（新键不存在），未产生错误证据。

## 下一步（不属本 Goal）

前端固定模型装配与姿态视觉核对、夹爪与相机所需凭证来源、跨流同步游标、归档全量验证与 M1.5/M1 正式验收。
