# S25｜时间量来源、机械臂映射证据与按部件渲染就绪（2026-10-25）

## 来源类型

平台后端只读切片的事实来源（M1.5e）。分三类并列：**源码证据**（native 当前检出与冻结 release 快照）、**真实归档实测证据**（离线读取，只读文件）、**隔离夹具证据**（`tmp_path` 内构造，不触碰真实归档）。绑定候选 `m1x-20261026T065320Z-platform`（`http://127.0.0.1:18970`，源码聚合 `df124d886e652f03…`／49 文件，启动清单 sha256 `6209e493cc23443e…`）。

## 观察到的事实

### 时间量来源（真实归档 + 隔离夹具）

1. 旧实现允许 `payload.sim_time_s` 缺失或非数值时回退使用事件信封的 `sim_time_s`，同时把结果标为负载来源，等于用一条记录的字段填充另一条记录的量。
2. 现拆为 `state_sim_time_minus_frame_capture_sim_time`（仅取自状态反馈负载）与 `state_event_envelope_sim_time_minus_frame_capture_sim_time`（取自事件信封），负载缺值时前者**缺失**而非回退；`times.sim_time_quantity_keys` 列出两键，`version_migration.corrections` 记录该标注更正。
3. 真实代表记录 `run_0104613ff7364ae78cf2f3946bd45f7b / episode_27bfed5427684795b361cd2ec21e9aa7` 首帧 `rgbd_e3213e6cb64b4cd693c17d485d064d09`：负载与信封的 `sim_time_s` 均为 `0.14`，与 `capture_sim_time_s = 0.14` 相同 → 两个 sim 量都为 0，而 backend monotonic 侧三个量分别 −2.885407 ms（事件写入）、−3.669841 ms（负载采样戳）、−3.668296 ms（录制器声明）；`observation_age_ms = 33.45116903074086` 与 `arrival − capture` 逐位相等，属管线延迟。
4. 隔离夹具三种情形均通过：负载缺失（仅信封量存在）、负载为非数值字符串（仅信封量存在）、负载与信封都有且数值不同（两量并存、`source_record` 不同、值分别为 0 与 −10 ms）。

### 机械臂映射证据（源码证据）

5. `ARM_JOINTS = tuple(f"joint{i}" for i in range(1, 6))`（`backends/modelgen/model/arm.py:10`），`GRIPPER_DRIVE = "gripper_base_joint"`；`ArmController` 以名字解析 `model.joint(name).id` 再取 `model.jnt_qposadr`（`control/arm.py:12-14`）；反馈序列化 `"arm_model_qpos_rad": self.data.qpos[self.arm.qpos[:5]].tolist()`（当前源码 `backends/mujoco/backend.py:3385`）。顺序由名字列表决定，与 XML 或原始 qpos 布局无关；索引 5 的夹爪驱动被切掉，故五值即五个臂铰接。
6. 版本可绑定范围（本轮逐文件亲自复核）：本地检出 `a5cef52` 中 `arm.xml 794b0c38e0c69643…`、`chassis.xml 90c347efaf65a8ac…`、`robot.xml 3ca3d6d0a92a48bb…`、`control/arm.py dc5decac1dbfbd4a…`、`modelgen/model/arm.py fb3fd286a9103d8a…`、`sensors/scene.py efb2ccbed695d30d…`、`arm_spec.json 8d1dc917c7c76c58…` 与 drvfix 冻结清单（384 文件）相等，而 `backends/mujoco/backend.py` 不等（磁盘与 HEAD `de7a889da20598f0…` vs 清单 `108dc2d56d3918b8…`）；工作区脏文件为 `app.py`、`cli.py`、`config.py`、`contracts/models.py`、`data/recorder.py`。
7. 该记录 `created_wall_utc = 2026-10-17T16:09:20.027084Z`；服务器上录制当天三个更早的冻结快照 `g2a-20261017T155919Z-1bf2b553093a`、`g2a-20261017T160655Z-92c71ff8d582`、`g2a-20261017T160903Z-7e3afdbaff8f` 内均含同一条链（`ARM_JOINTS` 于 `modelgen/model/arm.py:10`、`model.jnt_qposadr` 于 `control/arm.py:14`、`arm_model_qpos_rad = data.qpos[self.arm.qpos[:5]]` 于该版本 `backend.py:1386`），且 `arm.xml`、`robot.xml` 摘要与记录声明的 `model_sha256` 一致。
8. 限制：记录的 run 清单只声明 `contract_version = mobilecar-1.0` 与 `software = {name: mobilecar, version: 0.1.0}`，无 release/构建/提交标识；`drvfix-20261019T044549Z` 晚于归档且其 `backend.py` 与当前检出不同，故不是这批记录的写入者。结论只能是"写入者收窄到 2026-10-17 的 g2a 发布族"，不能指认唯一构建，也不回溯编造提交身份。

### 运动学对照（真实归档 + 隔离夹具）

9. 约定取自 native 场景导出器：link 的 `local_transform` 是 `model.body_pos/body_quat`（父体参考系，wxyz→xyzw），`joint_axis` 是子体参考系下的 `jnt_axis`。TCP site `grasp_tcp` 的父体为 `guide_rod_link`，偏移只存在于平台运动学参考配置（`authority = platform_reference_not_native_attested`，`orientation_status = not_specified_in_source`）。
10. 抽样 152/303 帧：以记录底盘位姿 + 五个模型弧度重算 site 位置，与同一负载记录的 `tcp_position_world_m` 比较，误差 min `1.61145e-14`、median `1.66139e-14`、p95 `1.66809e-14`、max `1.68974e-14` m，逐轴差 ~1e-14 m。
11. 对照假设（再叠加 `base_link` 本体偏移 0.0556）误差恒为 `0.0556000…` m，被排除；反序映射误差 median `0.20967` m，说明顺序确实受检；bundle 臂铰接文档序与配置序逐项相等。
12. 关节行程：joint1 0.035345、joint2 0.002927、joint3 0.002214、joint4 0.001287、joint5 0.035077 rad（无零行程轴）；底盘位移范围 x 0.051060、y 0.004595、z 0.000327 m。
13. 夹爪：`gripper_width_m` 由 native 侧计算为两个手指 site 位置之差（`_snapshot_gripper_width`），不是关节值；臂切片排除了 `gripper_base_joint`，故帧内没有夹爪关节值；平台配置声明了 `zero_width_m 0.025`、`width_per_drive_rad_m 0.023199`、`jaw_origin_correction_m 0.000524386…`、`source_gap_m 0.0489512…` 与四条 `mimic` 关系，但缺 native 背书 → 仍为 `unverified`。
14. 更正先前的两项表述：平台配置 `arm.zero_model_rad[3]` 是精确 `-1.5707963267948966`（不是 `-1.5708` 舍入值，仓库内 `-1.5708` 只出现在 M1.5d 文档自身）；夹爪宽度换算并非"任何来源都没有规则"，而是"存在平台声明规则但未经 native 背书与逐值验证"。

### 执行与覆盖

15. 本轮经 `GetProbe` 发出的 64 条请求全为 GET；946 文件覆盖集合事前记录、事后复核 `drift=[]`；历史读取断言 110/110、统一能力回归 28/28、聚焦 45 passed、全量 179 passed / 3 项历史布局失败（`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`）。新增断言先在同源码 scratch 实例（临时端口、临时 SQLite，验证后停止）跑绿再冻结，避免把工具缺陷带入不可变 release。

## 对设计的影响

- 时间量的**来源记录**是契约的一部分：一条记录的字段不得替代另一条记录的字段，缺失就报缺失。
- 机械臂角度顺序的证据来自"按名字取 qpos"的源码链，加上按名字绑定的 bundle 关节与运动学复算；这类证据强于按数组下标推测，但仍不等于指认写入构建。
- 运动学一致性检查可以同时排除错误的根约定与错误的关节顺序，因此"未证映射"应当被积极检验而不是无限期搁置；检查只支持一致性，不升级为标定或渲染证明。
- 按部件就绪是前端真正需要的形状：固定模型装配与局部姿态可用性与整车重建是三件事，必须分别表述，且不得用默认值填充未证字段或伪造动态物体位姿。

## 效力

本来源为"sim 量按来源记录拆分并保留标注更正说明""`arm_model_qpos_rad` 的顺序由名字寻址的源码链决定并可绑定到 2026-10-17 发布族（不指认唯一构建）""两种根约定与关节顺序可由纯运动学复算区分""按部件就绪与整车/渲染/同步表述分离"提供依据。实现与证据见 [M1.5e 交付记录](../../../backend-m1.5e-pose-readiness-and-time-sources.md) 与 [M1.5e 证据册](../../../evidence/m1.5e-pose-readiness/README.md)。
