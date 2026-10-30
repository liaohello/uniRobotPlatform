# Specification 修订记录

规范 ID：`GOV-CHANGELOG` · 责任层：治理 · 版本：V0.9（2026-10-30）

状态：设计草案；S08/S09 是用户提供的分析文本，不自动视为所有细节已确认。Waypoint 范围以 S10 的用户明确选择为准。诊断/草案实现证据见独立交付记录，正式 M1/M2 与工作台验收未执行。

来源：[S08](sources/S08-frontend-ia-analysis.md)、[S09](sources/S09-unified-development-reuse-analysis.md)、[S10](sources/S10-waypoint-scope-confirmation.md)。

[上级目录](README.md) · [总索引](../README.md)

## V0.9｜2026-10-30

### 2026-10-30 M1.5h 时间资格覆盖边界修正与历史动作／事件读取依据

- 新增来源 S28（覆盖边界缺陷复现、修正要求与动作／事件实测依据的 Goal 原文）与决策 DEC-065（`covers_whole_episode` 需"到达 EOF"且"每行被判定"，逐基 `readable_anchor_timing_satisfies_schedule` 单列；不可判定行阻塞整集资格并给出 `record_position`，空行与确认无关行为良性；`scope_note` 更正为"窗只筛页、普查独立扫描锚点文件"；动作／事件十类按记录自身键分类与关联，`not_recorded`/`unknown` 不填充、不默认 Human、不把审批当执行；`include_action_basis` 为 opt-in、`frame-link-2` 不升版、不新增端点）。
- [Episode/事件/标注契约](../30-contracts/03-episode-events-annotations.md)：census 小节改写覆盖规则与理由串，播放语义小节把覆盖类与时间类阻塞分列，新增两条 M1.5h 条款（`line_accounting` 三事实与计数分类规则；`action_basis` 词表、present/null 关联键、逐帧候选、命令链、控制来源、独立事件轨与必需流 `unknown` 上限）。[时间与坐标契约](../30-contracts/04-time-frames-units.md)追加覆盖边界三事实与动作／事件分类约束；[回放与数据验收](../40-verification/03-replay-data-acceptance.md)标注 TEST-REPLAY-003 的"明确缺失"新增支撑并重申跨流未证明；[M1.5g 交付记录](../../backend-m1.5g-anchor-time-quality.md)追加"更正"一节，写明旧规则只看 EOF 的缺陷与旧 `scope_note` 的易误读处，不改写其历史实测数值。
- 实现：`backend/src/unirobot/frames.py`（`_stream_lines` 报告不可判定行、`LINE_ACCOUNTING` 分类规则、`_time_quality` 三事实与 `blocking_reason_scope`、`ACTION_CATEGORIES`/`ACTION_BASIS_RULES`/`_action_basis()` 有界 events 扫描、`recorded_target_event`/`command_dispatch_event` 可选角色与 `PAGE_ROLES` 覆盖统计、`_unit_of`/`_is_time_named` 按记录字段名定单位、`version_migration.corrections/additions`）、`backend/src/unirobot/api.py`（`include_action_basis` 参数透传）、新增 `backend/tools/anchor_coverage_repro.py`（基线与修正源码对照复现同一夹具）；`tools/episode_history_check.py` 断言 130 → **146**（本轮 16 项）；`tests/test_frames.py` 新增 9 项隔离用例并修正既有截断用例的理由串。
- 服务器验证：候选 `m1h-20261030T002258Z-platform`（`127.0.0.1:18983`，PID 3745241，启动前端口实测空闲，独立 SQLite `frames-20261030T002258Z.sqlite3`，源码聚合 `68f481b38843d2bc…` 50 文件与启动清单 MATCH、清单内 `frames.py` 摘要与运行目录全等，启动清单 sha256 `90b5234d6308860d…`）读取检查 **146/146**、统一回归 **28/28**、冻结树聚焦 **69 passed**、全量 **203 passed / 3 项历史布局失败**（`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`，按名保留、不称全绿）；75 条请求全为 GET、946 文件 `drift=[]`、`live_scene_reads=0`；18977（M1.5f）与 18979（M1.5g）常驻未替换。真实测量：COMPLETE 普查 303 锚点、`undecidable_total=0`、整集资格仍为真；窗口页 1 帧 + 302 窗外而 census 仍 303 锚点；events 全量 12561 条 12 类（FAILED 224 条 11 类），`feedback.command_id` 全 null、`requested.control_tick_id` 全 null、`dispatch` 两键均 present，逐帧候选 `actuator_reference={"1":200}`、`dispatch={"0":199,"1":1}`；`rejected`、执行完成回执与接管事件类型 `not_recorded`；`episode_terminal` 数值时钟为 null；控制来源只见于 payload 字段。合成对照：同一含不可解析行的档案在 `a10b96b` 源码上报 `covers_whole_episode=true`/`any_base=true`，在修正源码上报 `covers_whole_episode=false` 与逐基 `1_lines_are_undecidable_and_could_hide_anchors`，A 在两版中均合格。交付前先在运行同一棵 dev 树的 scratch 实例（18981）跑通 146/146 再冻结，未产生半途 release；scratch 按命令行身份核对后停止。
- 机器目录：补充来源 22 → 23 个，文档节点与 REQ 计数不变。三句结论仍分开表达："追加顺序播放可用""记录时间播放是否有资格（须逐基且逐覆盖）""跨流同步仍未证明"；本轮不做前端事件轨／倍速实现，不代表生产部署、正式 M1.5 或 M1 验收通过。

### 2026-10-30 M1.5i 拒绝回执分域与时间接近不提升同步

- 新增来源 S29（本轮 Goal 原文：A 段覆盖边界 + B 段动作/事件最小证据面，并明确"被拒请求不当作已执行 action""不因事件时间接近提升 synchronized/same_clock_verified"）与决策 DEC-066（记录到的拒绝保持回执身份、不进入帧关联、命令链不补出审批/下发；`clock_parity` 规则把"数值接近甚至相等都不建立链接"写进 API；`recorded_target` 规则拒绝把 Target 报告为 Actual；原始事件值不改写）。
- [Episode/事件/标注契约](../30-contracts/03-episode-events-annotations.md)追加回执分域与 `clock_parity` 条款；A 段覆盖边界的实现与迁移说明保持 M1.5h 原样（`frame-link-2` 不升版），本轮只复验并在新候选上重测。
- 实现：`backend/src/unirobot/frames.py`（`ACTION_BASIS_RULES` 新增 `clock_parity`、`recorded_target`）；`tests/test_frames.py` 新增夹具开关 `record_rejected_receipt` 与两项用例（真实记录的拒绝、完全相等时间戳且无共享键）；`tools/episode_history_check.py` 断言 146 → **148**（时间接近不提升、拒绝回执分域）。
- 服务器验证：候选 `m1i-20261030T035643Z-platform`（`127.0.0.1:18985`，PID 1659550，启动前端口实测空闲，独立 SQLite `frames-20261030T035643Z.sqlite3`，源码聚合 `107f897ddfe2485f…` 50 文件与启动清单 MATCH、清单内 `frames.py`=`9ae98b126e42760a…` 与运行目录全等，启动清单 sha256 `7338d2779ecf55fb…`）读取检查 **148/148**、统一回归 **28/28**、冻结树聚焦 **71 passed**、全量 **205 passed / 3 项历史布局失败**（三项按名保留）、77 条请求全为 GET、946 文件 `drift=[]`、`live_scene_reads=0`；18977/18979/18983 常驻未替换。真实实测：命令意图/受理时间戳与第 7 行锚点采集时刻仅差 `0.015817145991604775 s` 却不建立任何关联、同步声明全为 false；`rejected` 在本归档 `not_recorded_in_this_scan`；合成夹具补写的 `rejected` 为 `observed` 且不进帧关联、命令链无 `approved`/`dispatch`。交付前先在运行同一棵 dev 树的 scratch 实例（18981）跑通 148/148 再冻结，未产生半途 release。
- 机器目录：补充来源 23 → 24 个，文档节点与 REQ 计数不变。三句结论仍是分开的；本轮不打开跨流同步、不实现前端回放，也不代表生产部署或 M1 验收通过。

## V0.8｜2026-10-29

### 2026-10-29 M1.5g 采集锚点时间质量与播放资格（记录时间播放的真实依据）

- 新增来源 S27（单 Episode 采集锚点时间质量与播放资格实测）与决策 DEC-064（播放资格逐时间基、逐覆盖范围判定；A/B/C 三件事不可互推；缺时/非数值/相等/回退/截断各自的允许与拒绝；禁止默认帧率、浏览器补时与跨 RESET 连时钟；census 为 opt-in 且 `frame-link-2` 不升版；重复锚点 id 改为明确拒绝而非静默取第一条）。
- [Episode/事件/标注契约](../30-contracts/03-episode-events-annotations.md)：帧关联小节新增 `include_time_quality` 与 `time_quality` 块字段定义（`coverage`/逐基 `time_bases`（含"首个-末个"与"最小-最大"分列、间隔统计、相等与回退计数、文件顺序是否等于值顺序）/`identity.duplicates[]` 的 `record_positions`/`recorder_counters`/`profile`/`playback_eligibility`/`not_proven`）与页级 `summary.anchors_with_repeated_sample_id_on_this_page`，写明"时间窗与 `sample_id` 只是筛选、页内 `line_index` 恒升序、census 不因窗口缩小范围"；新增 A/B/C 播放语义与异常规则、`implied_rate_hz_from_median_recorded_gap` 非声明速率声明，以及 `robot-state` 的 409 `frame_sample_id_ambiguous` **行为收紧**与迁移方式。[时间与坐标契约](../30-contracts/04-time-frames-units.md)追加同义约束段（禁止名义帧率/浏览器补时/跨 RESET 拼接，profile 名含 `5hz` 不算声明速率）；[回放与数据验收](../40-verification/03-replay-data-acceptance.md)标注 TEST-REPLAY-001 的"逐帧/追加顺序"部分已有真实遍历证据、"按约定时间同步"仍未证明，TEST-REPLAY-003 的"明确缺失"由 census 与拒绝语义支撑。
- 实现：`backend/src/unirobot/frames.py`（`TIME_QUALITY_*` 常量、`_base_statistics()` 逐基统计、`_time_quality()` 有界普查与三模式资格、页级重复 id 计数、`include_time_quality` 参数）、`backend/src/unirobot/api.py`（帧路由参数透传）、`backend/src/unirobot/history_pose.py`（重复锚点 id 的 `frame_sample_id_ambiguous` 拒绝）；`tools/episode_history_check.py` 断言由 118 增至 130（本轮 12 项，含真实两页遍历 303 锚点无跳漏与"census 不改分页语义"）；`tests/test_frames.py` 新增 8 项隔离用例（opt-in/逐基测量/回退/相等/缺失/非数值/重复 id/截断）。
- 服务器验证：候选 `m1w-20261029T155818Z-platform`（`127.0.0.1:18979`，PID 2738345，启动前端口实测空闲，独立 SQLite `frames-20261029T155818Z.sqlite3`，源码聚合 `707843426524d406…` 49 文件且与本地工作树全等，启动清单 sha256 `064a5bf0192798fa…`，重算↔清单 MATCH）读取检查 **130/130**、统一回归 **28/28**、冻结内聚焦 **63 passed**、全量 **191 passed / 3 项历史布局失败**（名称与基线同前）；71 条请求全为 GET、946 文件 `drift=[]`、`live_scene_reads_in_this_run=0`。真实 COMPLETE 记录 303 锚点/303 唯一 id/三基零缺失零非数值零相等零回退、A 与三基 B 合格、隐含 4.998/5.000/4.967 Hz 且锚点无声明速率字段；FAILED 记录 4 锚点同法测量（记录完整性属另一层）；census 8,733 B 对 200 帧页体 5,181,012 B。交付前先在运行同一棵 dev 树的 scratch 实例（18978）跑通 130/130，未产生半途 release；scratch 按命令行身份核对后停止。**18977 与其他既有服务保留未替换。**
- 机器目录：补充来源 21 → 22 个，文档节点与 REQ 计数不变。"追加顺序播放可用""记录时间播放是否有资格（逐基、逐覆盖范围）""跨流同步仍未证明"是三句分开的话；本轮不做前端倍速/区间实现，不代表生产部署、正式 M1.5 或 M1 验收通过。

### 2026-10-29 M1.5f 历史完整静态模型树（解除前端逐 link 装配数据的外部依赖）

- 新增来源 S26（历史完整静态模型树实测）与决策 DEC-063（逐 link 装配数据由既有 `robot-state` 的可选 `include_model_tree` 给出、默认兼容不升版、树复用 bundle 的 `Link`/`Geom` 序列化而非 `_link_view` 摘要、身份不符只拒给不替代、内容键取一次、动态响应不带内容 ETag、world 链是编译初态不是记录位姿）。
- [Episode/事件/标注契约](../30-contracts/03-episode-events-annotations.md)：历史姿态小节新增 `include_model_tree` 参数与 `model_resource.model_tree` 字段规则（逐 link `parent_name/joint/local_transform/geoms` 与逐 geom 类型/尺寸/变换/颜色/`mesh_asset_id`/碰撞过滤、`counts`、沿用四摘要的 `content_identity`、`caching` 取一次与 ETag 分工、`semantics` 的 `compiled_initial_layout_not_live_object_state` 与 `world_links_are_not_recorded_object_positions`、`mesh_bytes` 只走 Episode 资产路由），并写明八条 GET 不变、`history-pose-1` 不升版、身份不符时 `included=false` 且不返回替代树。
- 实现：`backend/src/unirobot/api.py`（`include_model_tree: bool = Query(False)` 透传）、`backend/src/unirobot/history_pose.py`（`_model_tree()`：状态不符与未配置 bundle 时只给拒绝说明；命中时整棵 `links/world_links` + 元数据；摘要视图原位保留）；`tools/episode_history_check.py` 断言由 110 增至 118（本轮 8 项，含"树与直接加载的 bundle 逐元素相等"与"取树不发 live scene 读"）；`tests/test_frames.py` 新增 4 条隔离用例（默认兼容、整树相等、身份不符拒给、native 指向不可达地址时场景读 503 而历史树完整）。
- 服务器验证：候选 `m1z-20261029T075630Z-platform`（`127.0.0.1:18977`，PID 272431，独立 SQLite `frames-20261029T075630Z.sqlite3`，源码聚合 `5cb9a562a1190c11…` 49 文件，启动清单 sha256 `5503bb07f703fe6a…`，重算↔清单 MATCH，且与本地工作树聚合全等）读取检查 **118/118**、统一回归 **28/28**、冻结 release 内聚焦 **55 passed**、dev 树全量 **183 passed / 3 项历史布局失败**（名称与基线同前）；本轮 66 条请求全为 GET、946 文件覆盖 `drift=[]`；真实树 `71 links / 2 world_links / 100 geoms / 22 mesh_geoms`，带树响应 `content-length 107835` 且无 `ETag`，换帧树逐字节相同，`live_scene_reads_in_this_run=0`。同轮 `m1y-20261029T075301Z-platform`（18976）交付前因补 `world_links` 非记录位姿声明而重冻结，其 release 与报告目录保留为历史未回填，进程为本轮注册且身份核对后停止；18970 与其他既有服务未替换未清理。
- 机器目录：补充来源 20 → 21 个，文档节点与 REQ 计数不变。前端 #34 的"缺逐 link 位姿表"外部依赖已由本切片解除；这不等于前端装配已验证、历史整车渲染可用、坐标与标定语义已获凭证，也不等于 M1.5/M1 验收通过。

## V0.8｜2026-10-25

### 2026-10-26 M1.5e `sim` 时间量来源拆分、机械臂映射证据与分部姿态就绪

- 新增来源 S25（时间量来源与姿态就绪实测）与决策 DEC-062（`sim` 基时间量按来源记录拆分且不回退、机械臂映射以源码链+冻结快照+摘要一致+运动学复现为证据上限且不证明写者版本、模型角绘制不依赖用户角转换、就绪条件按部件划分、夹爪宽度表述更正）。
- 更正上一轮两处超出证据的表述并显式记账，不回填原文：`zero_model_rad` 实为精确 `-π/2`（不是"舍入为 -1.5708"），平台运动学配置已声明夹爪宽度与 mimic 常数（不是"任何地方都不存在规则"），缺的是这些常数与历史写者版本绑定的凭证；见 [M1.5d 交付记录](../backend-m1.5d-frame-reading-and-pose-preparation.md) 追加的"更正"小节。
- [Episode/事件/标注契约](../30-contracts/03-episode-events-annotations.md)：帧时间小节把 `sim` 基差值拆为 `state_sim_time_minus_frame_capture_sim_time`（只取状态负载 `payload.sim_time_s`）与 `state_event_envelope_sim_time_minus_frame_capture_sim_time`（只取事件信封 `sim_time_s`），缺数值时对应量缺席、不回退、`times.sim_time_quantity_keys` 列出两者，迁移说明补 `version_migration.corrections`；姿态小节新增 `arm_mapping_chain`、`version_binding`（`writer_identified=false` 与可绑定范围上限）、`model_vs_user_angles`（`render_source`/`conversion_is_required_for_drawing=false`，用户角公式与照片零位权威单独列出）、`tcp_kinematic_cross_check`（两条根坐标假设、`supported_hypotheses`、逐轴差值、`tolerance_authority`、`supports`/`does_not_prove`）与九项 `part_readiness`（状态词汇 `ready`/`ready_with_caveats`/`conditional`/`blocked`/`not_required`，每项带 `requires`/`pose_input_required`/`inputs_available`/`frontend_rule`/`evidence`/`gaps`）＋`capability_summary`（`fixed_model_assembly_available=true` 与 `whole_robot_pose_rebuildable=false` 并存，`escalation_forbidden`/`defaults_forbidden`），映射状态改为按证据判定（`verified` 需复现成立）、未证项仍不补默认值；`frame-link-2` 与 `history-pose-1` 版本不变（纯字段新增，向后兼容）。
- 实现：`backend/src/unirobot/frames.py`（`SIM_TIME_QUANTITIES` 两条独立量与 `_delta` 来源标注）、`backend/src/unirobot/history_pose.py`（映射链证据、版本绑定上限、模型角/用户角分离、TCP 运动学对照、分部就绪与能力汇总）、新增 `backend/src/unirobot/history_fk.py`（纯运动学：冻结 bundle 体树、`body_poses`/`site_world_position`/`tcp_from_recorded_state`，不依赖 MuJoCo/numpy/native）、新增 `backend/tools/history_fk_check.py`（离线全归档聚合对照，产出 `unirobot-mobilecar-history-fk-check-1`）；`tools/episode_history_check.py` 断言由 102 增至 110（本轮 8 项），新增 `backend/tests/test_history_fk.py`（7 项手算期望）与 `test_frames.py` 的来源/映射/分部用例。
- 服务器验证：候选 `m1x-20261026T065320Z-platform`（`127.0.0.1:18970`，PID 3256687，独立 SQLite `frames-20261026T065320Z.sqlite3`，源码聚合 `df124d886e652f03…` 49 文件，清单 sha256 `6209e493cc23443e…`）读取检查 110/110、统一能力回归 28/28、聚焦 45 passed、全量 179 passed / 3 项历史布局失败（名称与基线同前：`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`）；本轮经 `GetProbe` 发出的 64 条请求全为 GET，946 文件覆盖集合 `drift=[]`，历史归档、native 8792、生产配方与 pin 未改动，未启动新的 native 实例。离线运动学对照：真实 Episode 152/303 帧可比，`error_primary_m` 最大 1.68974e-14 m，五轴均有位移（joint2/joint3 幅度仅 0.0029/0.0022 rad），竞争根坐标约定分离 0.0556000 m、关节序反转分离 0.20967 m；容差 0.005 m 由本检查自述，非标定上限。
- 机器目录：补充来源 19 → 20 个，文档节点与 REQ 计数不变。固定模型资源准备完成、前端装配验证、历史姿态局部验证与正式 M1.5/M1 验收是四件不同的事：本轮只交付前三者的契约与证据基础，历史整车渲染、跨流同步与统一历史游标仍未验证。


### 2026-10-25 M1.5d 帧读取分页/角色完整性修正、时间语义分离与历史姿态准备

- 新增来源 S24（帧读取修正与历史姿态准备实测）与决策 DEC-061（分页由下一条合格锚点决定、角色完整性按必需 sensor_kind 与逐角色基数判定、三个时间量分离且版本迁移显式、同钟命名与写入版本绑定分开、姿态映射逐项可判定且不补默认值、资源就绪与渲染验证分离）。
- [Episode/事件/标注契约](../30-contracts/03-episode-events-annotations.md)：帧关联小节改写为 `unirobot-mobilecar-frame-link-2` 的分页、角色完整性与时间语义规则（新增 `ambiguous_kind`/`ambiguous_candidates`、公开状态优先级、`anchor_lines`/`scan` 行计数、`times.quantities` 与 `times.recorder_declared`、移除 `age_of_state_relative_to_frame` 并说明迁移）；新增"历史机器人姿态与固定模型资源准备"小节，冻结两条新只读 GET（`robot-state` schema `unirobot-mobilecar-history-pose-1`、`model/assets/{asset_id}`）及其身份校验、映射状态词汇与不伪造规则；历史只读面由六条扩为八条 GET。
- 实现：`backend/src/unirobot/frames.py`（分页 lookahead、`ROLE_REQUIREMENTS`、歧义状态与候选诊断、命名时间量与 `clock_sameness` 证据分层、schema 升版）、新增 `backend/src/unirobot/history_pose.py`（姿态映射与冻结 bundle 资产读取）、`backend/src/unirobot/episodes.py`（`run_identity()` 公共读取入口）、`backend/src/unirobot/api.py`（两条 GET）；`tools/episode_history_check.py` 断言由 86 增至 102。
- 服务器验证：候选 `m1v-20261025T161014Z-platform`（`127.0.0.1:18969`，PID 3923606，源码聚合 `d022239329c0518d…` 47 文件，清单 sha256 `8e32f91f6cf2a24f…`）读取检查 102/102、统一能力回归 28/28、聚焦 39 passed、全量 167 passed / 3 项历史布局失败（`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`）；本轮经 `GetProbe` 发出的 64 条请求全为 GET，946 文件覆盖集合 `drift=[]`。同轮 `m1t-…`（18967）与 `m1u-…`（18968）因检查工具自身缺陷中断，保留为历史未回填。
- 机器目录：补充来源 18 → 19 个，文档节点与 REQ 计数不变。切片完成不等于历史渲染通过、坐标与标定语义已获凭证、统一历史游标可用或 M1.5/M1 验收通过。


### 2026-10-25 M1.5c 真实帧关联切片与 run 身份边界

- 新增来源 S23（真实帧关联切片与 run 目录身份边界实测）与决策 DEC-060（run 身份每次读取校验、关联只依据记录键、年龄不等于同步、切片不解锁历史 3D）。
- [Episode/事件/标注契约](../30-contracts/03-episode-events-annotations.md)：历史只读面由五条 GET 扩为六条（新增 `GET /api/v1/episodes/{episode_id}/frames`，schema `unirobot-mobilecar-frame-link-1`）；路径受限条款补入 run 目录身份校验（缓存索引建立后不得用指向兄弟 run 的软链以原身份读取）；新增"图像—机器人状态帧关联切片"小节，固定角色与关联键、六种关联状态、显式选样规则（不插值、不状态保持、不按时间相近或行号）、差值只作为记录字段相减的年龄、`clock_sameness.verified_by_reader=false` 与媒体摘要仍属声明。
- 实现：`backend/src/unirobot/episodes.py`（`require_run_directory`）、新增 `backend/src/unirobot/frames.py`、`backend/src/unirobot/api.py`（帧路由）；`tools/episode_history_check.py` 增加 17 项帧关联断言（总数 69→86）；新增 `backend/tests/test_frames.py`（12 项，含 run 目录替换夹具）。
- 服务器验证：候选 `m1s-20261025T084308Z-platform`（`127.0.0.1:18966`，源码聚合 `932582d19de263ab…`，清单 sha256 `6872adad98dbc75f…`）读取检查 86/86、统一能力回归 28/28、聚焦 31 passed、全量 159 passed / 3 项历史失败；本轮经 `GetProbe` 发出的 59 条请求全为 GET；946 文件覆盖集合 `drift=[]`。同轮 `m1q-…`（18965）因检查工具断言写死页大小而中断，作为历史保留未回填。
- 机器目录：补充来源 17 → 18 个，文档节点仍 150 个，REQ 仍 89 项。切片完成不等于统一历史游标可用、历史归档全量验证或 M1.5/M1 验收通过。

### 2026-10-25 M1.5b 历史 reader 只读整改、根目录隔离与可复现发布
- 按 S22/DEC-059 把只读改成由构造保证：新增 `backend/tools/native_get_probe.py`（只有 GET 方法、无 method/body 形参、逐条写 JSONL 日志），历史检查与事实提取都经它发请求；冻结候选实测 51 次请求 methods 仅 `GET`、`non_get=[]`，另有 8 次 GET 用于事实提取；重算派生结论只允许在隔离副本上进行。
- 统一受限路径解析（`episodes.py` 内 `_real` + `confined_within` 单一检查）：root/run/`episodes`/Episode 目录/run manifest/episode/tail/sidecar/assessments/固定流/`assets/` 的解析结果都必须位于对应边界；索引拒绝软链目录，读取时每次重新解析，缓存索引不能绕过；新增 `history_path_escape`、`episode_path_escape`，软链 assets 与越界资产返回 `episode_asset_escape`，媒体清单逐文件排除并计数。
- `event_seq` 区间过滤修复：缺失、非整数与 bool 序号被排除且计数（`filtering.event_seq_range.anomalies[]` 带 `line_index/reason/value_type`），不补造序号；`observations-index/persist` 合法无 `event_seq` 时返回空页 + 计数；合法数据的 `offset/next_offset/has_more`、原生追加顺序与身份语义不变；`wall_utc` 拒绝数值边界（400 `time_base_not_numeric`），未知基仍 400 `time_base_unsupported`。
- 表述纠正：撤回超出证据的"所有原始文件未变/全程仅 GET"写法。保留上一轮违规记录与 native 现有派生 `quality_report.json`（摘要 `53314c84…`，前置摘要未快照，不声称内容未变、不回滚）；不变性只对事前记录并事后复核的同一集合成立（696 个 `episode.json`/`episode_complete.json` 聚合 `60c0c696…`，本轮另覆盖 946 文件集合 `drift=[]`）。同时更正 `transforms.jsonl` 语义：实测为带 frame/时钟标记的变换观测，不是逐 body 位姿，故模型摘要相等仍不等于历史 3D 渲染可用。
- 发布身份闭合：新增 `backend/tools/source_digest.py`（唯一实现，roots `src/unirobot`+`config`+`tools`），启动器写清单、两个检查工具重算并断言与清单相等；新不可变 release `m1p-20261025T053030Z-platform`（清单 sha256 `832bf518274600a9…`，源码聚合 `4090935b4c45c900…`，45 文件）常驻 `http://127.0.0.1:18964`，独立新 SQLite；旧 `m1k` 的 61/61 与 27/27 报告及 `58a737…`/`e86a709f…` 记录保留为原版本证据，不倒填。
- 服务器验证：新候选读取检查 69/69（含 8 项新断言）与既有能力回归 28/28；冻结发布内聚焦 19 passed；平台全量 147 passed / 3 failed（同历史三项，链条 140/3 → 147/3）。机器目录新增 S22，现为 150 个文档节点、17 个补充来源；REQ 仍 89 项。本轮不是同步回放、不是归档全量验证，也不是正式 M1.5/M1 验收。

### 2026-10-25 M1.5a 真实历史 Episode/segment 只读 reader 首个切片
- 按 S21/DEC-058 新增平台受限只读历史面：`backend/src/unirobot/episodes.py` 与五条 GET（列表 / 轻量详情 / 可用流 / 按流有界记录页 / Episode `assets/` 内媒体资产），统一 `unirobot-mobilecar-episode-read-1` 与 `read_only=true`；来源固定在 `backend/config/mobilecar-history-source.json`（`mobilecar-server-history-20261017` → `/home/liaozhengyan/Desktop/mobileCar/var/runs`，native `drvfix-20261019T044549Z-0a80415b2577`）。原始数据留在服务器，不搬运、不重写、不重算导出，不修改或重启 8792。
- 完整性分四层：记录声明状态、`complete_tail` 存在性、tail 声明校验和条目、本次读取实际重算结果。实测发现 native tail 对自身 `episode.json` 的声明是**过期自校验**（抽样 16/16 条真实记录 `mismatch_present`，COMPLETE 记录声明 924 条摘要），平台如实报告且不改写生命周期状态；`FAILED`/`audit_status=INCOMPLETE` 记录标为 `incomplete_terminal_recorded` 且仍可读；`training_qualified=false` 不阻止原始读取。
- 身份与时间动作语义逐字保留：source/adapter+run+episode+segment+contract 版本+目录原始引用；同名跨 run 409 `episode_id_ambiguous`；`backend_generation` 只按记录 payload 如实标注；`wall/backend_monotonic/sim/measurement/arrival` 时间与单位不转换，游标声明"文件顺序不是时钟、不跨流同步"，Actual/记录 Target/命令意图/执行反馈分类不合并；legacy 无 sidecar 时关联明确未知，不伪造 ValidatedSnapshot。
- 3D 身份取自记录内 `manifest.json` 与 `transforms.jsonl`：与生产 pin 可比对时 `identity_verified_rendering_unverified`，否则 `restricted`；禁止套用在线 geometry/Actual。路径受限并复用既有保护：`..`/绝对路径/软链越界/非 `assets/` 目标/摘要不符/不支持后缀/超大小分别定位，不代理 validate、控制、RESET、录制或步进。
- 服务器验证：历史候选 release `m1k-20261025T040435Z-platform` 常驻 `127.0.0.1:18960`，`tools/episode_history_check.py` 61/61 通过（348 条与 native 列表一致；events 12561 条实际计数；303 张 rgb/depth/masks 资产摘要核验；平台详情 21,031 字节对 native 整条 20,946,833 字节；归档聚合摘要 `60c0c696…` 读取前后不变；8792 前后一致且仍无 stop/end 协议）；同一候选统一能力回归 27/27；聚焦 12 passed；平台全量 140 passed / 3 failed（同一历史三项，链条 128/3 → 140/3，未新增失败）。见 [M1.5a 交付记录](../../backend-m1.5a-history-reader.md) 与 [证据册](../../evidence/m1.5a-history/README.md)。
- 顺带闭合发布身份缺口：`launch_unified_gateway.py` 的平台源码摘要现覆盖 `src/unirobot + config + tools`（42 文件，`e86a709fb6e59f44…`），启动器与检查工具不再落在身份之外；native 完整清单与生产 pin 的边界不变。
- 机器目录新增 S21，现为 150 个文档节点、16 个补充来源；REQ 仍 89 项。本切片不是同步回放 UI、不是新采集闭环，也不是正式 M1.5/M1 验收。

### 2026-10-25 M1.4b 统一可联调候选与部署前发布身份

- 统一候选 release `m1j-20261025T020857Z-platform`：`tools/launch_unified_gateway.py` 用一份启动清单在一个进程内同时提供 geometry-2 scene 与 23 资产、capabilities/snapshot/kinematics、Map/Route 资源、Draft/validate、Session/`current` 与 STOP/end schema；`tools/unified_candidate_check.py` 27/27 通过，正向生命周期 39/39。候选以 `http://127.0.0.1:18959` 常驻保留为前端联调基址（独立 SQLite、对真实 native 仅 GET），在该存活地址重跑同一套检查 27/27；18954/18956 两个 test-only 服务检查后已停止；18949/18953 未替换。
- 几何读取兼容与执行资格分开记录：生产 recipe + 真实 8792 下 validate 真实失败、capabilities 不声明 stop/end 协议，prepared/Start/begin/STOP/end 继续按真实原因被拒；未换标签、未放宽 pin、未改生产 recipe/pin；`runs/{run_id}/stop` 仍与机器人 STOP 分离。
- 候选身份澄清并更正 M1.4 文档：`c550a4e4…` 为旧白名单 155 中存在的 152 子集摘要，不覆盖 `attestation.py`/`session_binding.py`，不等于完整 release pin，也不表示 drvfix+m1h 已组装验证；198 行历史清单未改写。
- 新增 `tools/release_identity.py` + `config/release-identity.native-m1h.json` + 回归 `tests/test_release_identity.py`：必需路径缺失即失败且不发布摘要，`extends` 闭包覆盖执行配置，受监视源码根的未列入文件被报告；m1h 副本 154/154、摘要 `41b9c80c…`，纯 drvfix 副本按预期失败，verify 复算匹配。
- 维护流程顺序修正：先冻结 release/完整 pin/recipe/protocol/config/scene/lock 并核验，再进入已获授权窗口；生产 pin 更新不再排在 begin/STOP/end 成功之后。G1/G4A2、a5/drvfix 与新 pin 仍待用户决定，推荐不等于授权。
- 服务器验证：平台全量 128 passed / 3 failed（同 `test_catalog_loads_real_tasks`、`test_every_task_has_existing_evidence`、`test_manifest_sources_exist` 历史布局失败，链条 74/3 → 90/3 → 98/3 → 108/3 → 123/3 → 128/3，均为读取仓库文档布局/外部工程资产的断言，在不含 `docs/` 的服务器 release 副本上必然失败）；机器目录新增 S20，补充来源 15 个、文档节点 150、REQ 仍 89。本轮不是部署、不是物理验证。

## V0.8｜2026-10-24

- 按 S18 将 PointGoal/waypoint 朝向改为必填，明确 m/rad、map +X/+Y、yaw 正方向与归一化、地图 origin 为图像左下角、图像列 +X/行 -Y；未给 yaw 报错，显式 0 合法。
- 新增版本化地图读取与 Route Draft/Version 资源切片；地图来源区分 G3B 历史离线包与 live SLAM，未证明兼容的运行时不授予导航资格。
- Route 保存只写资源，不发导航/机器人命令；点位、footprint、整条路径可达、动态执行分别表达，未实现检查为 unsupported。
- M1.3 候选 `m1g-20261024T113913Z-platform` 在服务器 18953 完成真实 Room A/B 读取、Route v1/v2、409 与固定版本不可变验证；平台全量 108 passed / 3 failed，三项仍为既有外部工程/native docs 布局失败。OpenAPI、真实地图资产、route evidence 与 native before/after 见 [M1.3 交付记录](../../backend-m1.3.md)。
- 机器目录新增 S18，现为 150 个文档节点、13 个补充来源；REQ 仍 89 项。本切片不是导航执行、部署或真实 M1 验收。

### 2026-10-24 M1.4 身份绑定 STOP 与可靠录制结束候选

- 按 S19 新增 `m1-stop-1`（`POST /api/v1/session/stop`）与 `m1-end-1`（`POST /api/v1/recording/end`）候选协议与平台侧 `sessions/{id}/stop`、`sessions/{id}/recording/end`；能力必须显式声明，`m1-recording-1` 不解释为含 end。
- 回执分层为受理/STOP 下发/停车证据与覆盖/Recorder 排空/落盘终态与完整性；`parking.coverage_complete` 与 `integrity` 共同决定"整机停稳且录制完整"，`accepted`、`base.stopped`、`complete_tail` 或尾文件存在都不再是单独判据。
- 明确拒绝规则：身份不符在副作用前拒绝；已 finalize 的 segment 走磁盘重放 `end_already_finalized`，不产生第二个 `episode_terminal`，不结束更新的 segment；同一 `request_id` 重放返回同一回执；结果未知只记 attempt。安全 STOP 不以 `motion_ready`/`recording_ready`/owner/lease 为前置条件。
- legacy `episodes/stop` 只有 reason，平台"先 GET 校验再 POST"不再被描述为原子身份保护；`POST /api/v1/runs/{run_id}/stop` 明确为进程/记录管理，不是机器人停止。
- native 候选补丁 `native-m1h.patch`（10 文件，sha256 `d182801d…a99f`）与冻结 release `m1h-20261024T152235Z-native` 记录候选源码摘要 `c550a4e4…49de`（生产 recipe 白名单中该 release 内存在的 152 路径），生产 pin `a0109804…911c` 未修改也未复用；native 保持未提交、未部署。
- 服务器验证：平台聚焦 66 passed，全量 123 passed / 3 failed（历史布局失败不变，未跳过、不称全绿）；native 聚焦 31 passed，适用全量 122 testcases（120 passed / 2 项历史失败）；隔离 cross-HTTP 集成 39/39 断言通过并核对 Recorder 落盘文件与摘要。
- 机器目录新增 S19，现为 150 个文档节点、14 个补充来源；REQ 仍 89 项。本轮不是部署、不是真机停车验证，也不改变正式 M1 验收状态。

## V0.7｜2026-10-23

### 2026-10-24 M1.2d 准备链路 P1 与状态 freshness

- 修复 native 录制生命周期竞态：commands RESET、legacy `episodes/start`、`recording/begin`、stop 与失败停止共享 lifecycle 锁，锁序 lifecycle → backend → recorder；状态检查与 RESET/开录在同一临界区重检，活动录制不能穿透。增加屏障回归，修复前对照 2 failed。
- binding 准备 TTL 只约束 prepared；started 由 RESET、release、身份变化或未来明确定义的结束事件失效。回读显式 `expires_scope=prepared`，不以短租约替代持续 Session。
- 单 Session GET 增加只读 `current`（source/observed_at/valid/status/blockers、runtime/binding/recording/owner/safety、ready/available）；`GET /sessions` 明确为 `source=stored`，刷新不续租/重绑/Start/清锁/启停录制，失联/身份变化/terminal binding 不报告 ready。
- 平台实际 `NativeBindingClient` 与隔离 native mock 完成真实 HTTP prepare/readback/start/begin/release、幂等和拒绝；测试 recipe 明示 mock，不改生产 G1 recipe/pin。生产 8792 未部署，真实 G1 与物理验证未执行。
- 平台聚焦 93 passed；全量 97 passed / 3 failed（历史 90/3 的同三项布局失败）；native 聚焦 57 passed。候选冻结身份与维护窗口决策见 M1.2d 交付记录。


### 2026-10-24 M1.2c 实现澄清（不改变 V0.7 范围）

- 修正 M1.2b “逐文件核验”的不准确描述：`requirements.lock` 现为 native `a5cef52` 的固定发布输入，启动读取字节、比对源摘要并核对 8 个精确版本；配方声明、发布文件核验、native 自报运行环境版本分开表述。
- 固定 `config_manifest_sha256`（extends 链/有效配置/profile/arm_spec）与 `scene_manifest_sha256`（编译场景规范 JSON）的覆盖范围；平台要求声明、实际响应和固定期望同口径一致，不以根 XML 摘要或 155 文件源清单替代；缺省即 unsupported。
- 补全 `m1-binding-1` 的 readback 状态、start 的 owner/lease/recording-ready/motion-ready 字段、RESET 失效和无 owner 获取；新增 `m1-recording-1` 无 RESET begin 的最小语义、持久化确认和 out-of-scope（stop/finalize/停车/回放）。
- 原生候选补丁与平台候选已在服务器隔离验证；8792 未部署、未重启，真实 G1 prepared/Start 和在线录制 begin 仍未发生。产品验收状态不因本轮实现或测试上升为通过。

- 按 S17 复评前端计划，恢复 S11/DEC-036 的统一架构原则与 PAGE-03 的可操作 3D 工作台交付形态；不改变 M1 mobileCar / M2 bimanual 和训练后续次序。
- 纠正把诊断页/元数据草案的 FastAPI 静态 ES modules 选择当作主前端架构的偏差。工程方向沿既有分析采用 React + TypeScript、Three.js SceneView 封装，Dockview 先验证再采用；不重写整套 native renderer 或迁移仿真后端。
- M1.2 内先交付对象树/视口/Inspector、相机与 Joint/TCP Target 预览/取消样板，再完成配置验证/prepared；M1.3～1.5 在同一骨架接控制/录制/历史。补焦点、Actual/Ghost/轨迹、权限/命令回执及来源/时间验收边界，复用现有 TEST 编号。
- 同步 PAGE-03、路线、交接与交付记录的取代说明；新增 S17、DEC-052～054 并登记机器索引。历史原文、素材、运行证据和产品代码不变，不把已有32项聚焦测试/11项浏览器检查上升为工作台或真实 M1 验收。
- 本轮只做文档与索引核对，前端生产实现继续暂停；兼容性、手势/参考系、性能及真实闭环仍待对应样板/集成验证。

本轮定向文档核对通过：149个目录节点的路径/编号、89项需求的主责/TEST映射、来源和原总册字节哈希，以及14份相关 Markdown 的569个本地链接目标。`git diff --check` 通过；backend 文件与本轮修订前的哈希清单一致。两路追加只读复核确认暂停/进度说明及关键交互契约一致。以上均为文档核对，不是产品测试、库兼容性或 M1 验收。

## V0.6｜2026-10-22

- 按 S16 用户直接决定，当前阶段改为 mobileCar 场景→运行→录制→回放，再 bimanual 验证组件复用；取代 V0.5 SO101/ACT 首发和训练前置建议，长期完整流程保留。
- 分开 SceneVersion 基础布局、SceneDraft 资源编辑、ExperimentDraft 实例覆盖和前端 store，明确解析与快照权威；不把四种称呼当同一持久化对象。
- 统一三种观测/采集摘要与 Execution/Export 的用途、旧名和适用条件；合并 Episode 当前引用集合，历史 native 数据不伪造已验证快照。
- 定义 HostApp/草案/资源/运行实体作用域；独立轻量工具可复用协议或组件，同一运行实体的后端授权/物理推进不按宿主复制。
- 补 Session prepared/active/closed/failed 与物理/任务/录制分域；收敛 mobileCar start 含 RESET、起始持久化、停车/finalize 分离、失败保留及只读 reader 的静态接口映射。
- 明确 Collection 可编辑、Dataset Version 冻结成员；四导航组与六业务职责属于分层关系，旧计数标历史并补当前统计。
- 新增2项需求和4项待执行验收，其他ID保留并按阶段引用；同步目录、追踪和参考登记。仅执行文档一致性验证，不运行产品/仿真/训练测试。

本轮文档验证：148 个目录节点、89 项需求的主责/TEST 映射、来源哈希、25 项图片哈希与尺寸、2,440 个本地链接/显式编号锚点检查通过；当前图片仍为26文件/25独特内容。3个只读子代理定点复核后，主代理修正旧版本提示、日期和 FAILED/finalize 措辞。新增4项产品验收全部保持 not_executed；文档验证不代表平台适配或真实采集回放已通过。

后续用户要求开始规划并提交 Git 基线：在 SYS-PAGE-DELIVERY 内补 M1.1～1.6 工作包、依赖、产物/完成检查和服务器验证边界；这是已批准 M1 范围的实施拆分，未增加需求编号或启动产品开发。Git 基线纳入 README、docs 和 .gitattributes 的证据字节保留规则，已有后端和本地代理配置/备份另行保留。计划补充后复核148节点、89需求、2,443条本地链接及来源/图片哈希通过，产品验收仍待执行。

## V0.5｜2026-10-22

- 原样归档三张 Scene Setup 图 IMG-023/024/025，PAGE-02 改为共用页面的任务变体，旧 IMG-002/PPT 保留。
- 细化五类任务字段/默认/条件/能力校验，Profile 唯一编辑来源、对象权限、Route 版本、Stale 和已验证快照；示意 schema 不冒充现存 API。
- 新建共享组件清单，收敛重复保存、步骤状态、顶栏/摘要和真实能力门控，未实现项明确后续扩展。
- 将当前路线改为 F0 前端样板 + R1 采集→清理→训练→预测完整任务；建议 SO101 台面转运/Expert/ACT，保留其历史训练表现与来源缺口，首任务选择非用户强制指定。
- 同步消费节点、来源/决策/未决、9 项新增需求与 12 项待执行验收，更新机器索引/图片登记；只执行文档一致性核查，不启动产品运行或训练。

本轮已执行的文档核查：147 个目录文档、87 项需求的主责/TEST 引用、25 项图片内容哈希、来源归档哈希，以及 2,411 个本地链接路径检查通过。修复文档入口指向不存在的 `foreEndDes.md` 的历史链接，改指已有来源摘录。新增 12 项产品验收均保留 `not_executed`；以上结果不代表 UI、仿真或模型验收。

## V0.4｜2026-10-22

- 原样归档用户提交 Simulation V2 图 IMG-022，PAGE-03 与相关工作台图引用切换；旧图/PPT 原件保留。
- 增加逐项删除/替换清单，区分已在图中体现的修改与未冻结交互。
- 细化 Profile/部件 Owner、三组运行状态、夹爪入口、实时轴、单位与命令反馈的剩余问题。
- 更新图片登记、来源、决策、未决与主责规范；不新增产品功能实现，不执行仿真或产品验收。

## V0.3｜2026-10-21

- 读取指定分支及父对话可读用户消息，保留助手正文不可取得的证据限制；直接用户认可补强统一前端/增量开发原则。
- 核对 22 PNG（21 独特内容）与 20 页 PPT，原件不改；新增图片/PPT/页面映射。
- 新建 21 个页面/视图节点，全部嵌图，标明完整/局部参考和后续候选；所有前端功能节点可找到所在页面图。
- 分析 22 项设计冲突，细化唯一在线控制台、Data 三层、资源/实验草案、模型状态、训练与评估视图。
- 增加共享评估比较契约、后端职责与页面细化路线，保留 V1 Waypoint 和其他既定边界。
- 新增 6 项需求和 8 项未来原型/产品验收；只执行文档检查，不修改产品代码、不执行 PoC 或任务仿真。

## V0.2｜2026-10-21

- 归档 S08/S09 与 S10 范围确认；总册保持不改。
- Waypoint 改为 V1 Scene Setup 编辑保存、Simulation 展示进度；退役旧排除断言，保留旧 REQ/DEC/TEST ID。
- 导航细化为 Prepare / Run / Data / Models & Experiments 四组；补 Data 详情流程与模型回 Run 推理。
- 增加任务模板目录、SO101 2D/3D 场景、A–H 布局、执行配置和模型输入/操作者视图区别。
- 补场景构建、地图路线、任务评定契约/后端节点；标签按训练用途选择，结果多轴表达。
- 增加统一骨架/任务切片路线、资源登记和三项 PoC 计划；仅有部分官方资料只读核对，未运行 PoC。
- 扩充需求、决策、未决、验收及多入口索引。文档检查与产品功能验收分开。

## V0.1｜2026-10-21

从设计总册建立前端、后端、共享契约、验收与治理体系；保留最初 56 项需求、39 个 TEST、26 项决策及 29 项未决问题。
