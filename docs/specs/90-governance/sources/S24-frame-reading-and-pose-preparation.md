# S24｜帧读取分页与角色完整性修正、时间语义分离与历史姿态准备（2026-10-25）

## 来源类型

平台后端只读切片的实测证据与契约修正来源（M1.5d）。绑定候选 `m1v-20261025T161014Z-platform`（`http://127.0.0.1:18969`，源码聚合 `d022239329c0518d…`，启动清单 sha256 `8e32f91f6cf2a24f…`）。

## 观察到的事实

1. 旧分页把 `_stream_lines` 预过滤后的记录数与原始文件行号混用，`has_more` 会把"过滤后计数不大于末页行号"当成没有下一页，也会用整份文件的行数误报还有下一页；行被跳过、坏行或超限时不作任何说明。真实锚点文件（303 行持久帧）里没有空行或坏行，但这一事实此前并未被报告，只是恰好没暴露。
2. 角色完整性此前由"候选条数是否等于 2"判定，不看 `sensor_kind`：重复 rgb 行加缺失 depth 行仍会被当作完整的图像观测；同一键出现多个状态、变换或计时候选时，实现会取文件里的第一条来出状态与时间，且响应不说明发生过选择。
3. 首页第一帧 `rgbd_e3213e6cb64b4cd693c17d485d064d09` 实测三个不同的时间戳：采集 `capture_backend_monotonic_s = 426494.351568496`；状态事件信封 `backend_monotonic_s = 426494.348683089`（早 2.885407 ms）；状态负载 `feedback_time_monotonic = 426494.347898655`（早 3.669841 ms，比事件信封还早 0.784434 ms）；计时事件负载 `feedback_time_s = 426494.3479002`（早 3.668296 ms，与负载自述相差 1.545 µs）。旧实现把事件信封那一个差值单独称作"状态相对帧采集的年龄"。
4. 同帧 `sim_time_s = capture_sim_time_s = 0.14`，即仿真时间差为 0；毫秒级差值只存在于 backend monotonic 侧。计时事件还把 `observation_age_ms = 33.45116903074086` 记为自己的采集→到达延迟，与 `arrival_backend_monotonic_s − capture_backend_monotonic_s = 33.451169 ms` 相等；另有 `capture_to_render_complete_ms = 5.867805`、`capture_to_publish_complete_ms = 62.209262`、`capture_to_persist_ms = 100.025438`、`arrival_to_persist_ms = 66.574269`。这些是管线延迟，不是状态采样年龄。
5. 时钟命名证据在记录内部：`clock_id = backend_monotonic`、计时负载 `feedback_clock = "backend_monotonic"`、`capture_clocks = {sim, backend_monotonic, wall_utc}`，两侧同名但不构成同源证明。写入版本绑定只能到 run 清单声明的 `contract_version = mobilecar-1.0` 与 `software = {name: mobilecar, version: 0.1.0}`，以及帧上的 `interface_profile = g2a-1.0`、`profile_id = g2a-rgbd-5hz-original`、`profile_sha256 = 9473171d7460ba96…`；`episode.json` 与 run 清单都不含 native release、构建号或提交号，因此"当前源码怎么写"不能自动证明这批 2026-10-17 的记录由同一写入版本产生。
6. 代表记录的键空间：观测索引 `rgb 303 / depth 303 / joint_feedback 608 / lidar 608 / imu 608 / encoders 608`；事件 `feedback 6074 / actuator_reference 6074 / rgbd_capture_timing 303 / feedback_initial 1 / requested=approved=dispatch=20 / lease_heartbeat 45 / lease_expired 1`。每个持久帧的 rgb+depth 恰各一条，`control_tick_id` 状态关联每帧恰一条候选。
7. 姿态与固定模型：run 清单声明的 `model_id / model_sha256 / scene_id / contract_version` 与既有不可变 geometry bundle 的 `resource_identity` 四项全等；bundle `bundle.json` 文件摘要 `a5f4a90ca5988ba0…`、provenance `bundle_sha256 275389464eee2f3d…`，含 71 条 link、23 个 mesh 资产（加载时逐文件摘要校验）、`tcp_site = grasp_tcp`、`camera_ids = [rgbd]`，导出时的 `runtime_identity` 属于另一次运行。机器人链提供 `base_free`（free）、`joint1…joint5`（hinge）、夹爪 `left_jaw_joint/right_jaw_joint`（slide，轴 `[0,-1,0]`）与相机链 `depth_cam_link ← camera_connect_link ← link4`。
8. 记录的姿态字段足以覆盖五自由度臂：`arm_model_qpos_rad` 5 值，臂铰接 5 条，名称与顺序可由 bundle 与平台运动学配置对上。关节顺序的直接证据只有一条：同一记录 `joint_feedback` 行的 `model_joint_positions_rad[3] = −1.5713109306099213` 与 `user_joint_positions_rad[3] = −0.0005146038150247723` 只差恰好 `−π/2`，其余四个索引 model 与 user 相等，说明偏移位于索引 3（joint4），而平台配置把 `zero_model_rad[3]` 写成四舍五入的 `−1.5708`。其余索引的按位对应仍无逐位凭证。
9. 底盘、夹爪与 TCP 的语义没有被任何来源证实：`base_position_world_sim_m` 未声明指哪个 body 原点（记录 z ≈ 0.05354 与 bundle `base_link` free 关节局部 z 0.0556 不是同一量）；`base_quaternion_xyzw` 的 `xyzw` 标签与 bundle `orientation_xyzw` 标签一致，但旋转的是哪个 body、在哪个参考系未证；`gripper_width_m = 0.025` 到两条 slide 关节的映射规则（半宽、符号、是否驱动 `gripper_base_joint/gripper_left_join/gripper_right_joint`）在记录、bundle 与平台配置里都不存在；`tcp_position_world_m` 只有 3 个位置分量、无朝向，且 `grasp_tcp` 在 bundle 里是 site 名而非 link；观测 `frame_id = rgbd_optical` 没有配套标定；world 侧 `target_cube` 等动态物体没有历史位姿记录。
10. 本轮经 `GetProbe` 发出的 64 条请求全为 GET；946 文件覆盖集合事前记录、事后复核 `drift=[]`；读取断言 102/102、统一能力回归 28/28、平台聚焦 39 passed、全量 167 passed / 3 项历史布局失败（`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`，基线不变）。
11. 过程记录：`m1t-…`（18967）与 `m1u-…`（18968）两次冻结因检查工具自身的缺陷中断（一次对整数取 `len()`，一次把工具外层变量 `body` 重新绑定为字节），其服务与报告目录保留为历史、未回填；因 `tools/` 在摘要根内，工具修正只能随新的不可变 release 生效，最终交付候选为 `m1v-…`（18969）。

## 对设计的影响

- 分页必须由"下一条合格锚点"决定 `has_more`，`next_offset` 保持锚点文件原始行号语义；扫描统计区分"读过的行"与"未读的行"，空行、超限行与坏行必须计数，不得静默给出末页。
- 角色完整性必须由角色自身语义决定：图像观测要求"每个必需的 `sensor_kind` 恰好一条"，重复或缺失分别给出 `ambiguous_kind`、`partial`、`missing`，单记录角色的多候选给 `ambiguous_candidates` 并列出全部候选与冲突标记；状态与时间不得从多候选里悄悄取第一条。主角色完整性与声明引用（`unresolved_reference`）继续分开，不按时间相近补造状态。
- 时间必须按"哪条记录的哪个字段减哪条记录的哪个字段"命名，单位、符号、方向和含义随值返回；事件写入戳、状态负载采样戳、录制器声明的反馈时间与观测/落盘时延是不同量，`observation_age_ms` 属于管线延迟。`sim` 基与 backend monotonic 基不得互相折算。
- 同钟命名与写入版本绑定必须分开表述：记录能证明"双方都叫 backend_monotonic"和"清单声明了 contract_version/software 版本"，不能证明同源同时刻，也不能把当前源码行为回溯为旧记录的写入行为；数值相近不得升级为 `synchronized=true`。
- 历史 3D 的最小准备是"身份可核、资源可读、映射有状态"：模型/场景身份与资产摘要可比对并通过，臂映射按已证实的范围标 `partially_verified`，底盘原点语义、四元数参考系、夹爪宽度到关节值规则、TCP 朝向与相机标定一律标 `unverified/missing` 且不得填默认值；动态场景对象不伪造历史位姿。资源就绪不等于渲染通过，装配与姿态正确性交下一轮前端验证。
- 历史端点不得代理当前 `/mobilecar/scene` 或 snapshot，也不得使用当前 Actual；固定 mesh 由冻结 bundle 直接提供，避免历史读取路径依赖在线 native。

## 效力

本来源为"分页由下一条合格锚点决定""角色完整性按必需 sensor_kind 与逐角色基数判定""事件写入戳、状态采样戳与录制器声明时间是三个不同量""写入版本无法从记录绑定到 native 构建""历史姿态映射的已证实范围与精确缺口"提供依据，并构成 `frame-link-1 → frame-link-2` 版本迁移的原因说明。实现与证据见 [M1.5d 交付记录](../../../backend-m1.5d-frame-reading-and-pose-preparation.md) 与 [M1.5d 证据册](../../../evidence/m1.5d-frame-reading-and-pose/README.md)。
