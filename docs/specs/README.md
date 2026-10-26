# uniRobotPlatform Specification 总索引

组织版本：V0.8 · 2026-10-25（America/Chicago）。状态：**Specification 文档体系；M1.3 地图/Route 资源切片与 M1.4 STOP/录制收尾候选已完成，分别不等于导航执行与真实停车；8792 未部署，M1 闭环验收未执行。** 未修改节点保留各自版本。

本文档树吸收设计总册，将现有规则落到可继续讨论的功能节点。保留需求确认程度、建议和未决项；产品验收尚未执行。前端目录按业务工作区＋共享交互组织，后端按能力域组织，另提供按界面区域和完整功能链查找的入口。

## 从哪里开始

**当前优先阅读：[mobileCar 最短闭环与 bimanual 复用](00-overview/10-first-task-closed-loop.md)。** 用户已确定 M1 场景→运行→录制→回放，M2 用 bimanual 验证共享组件；训练/预测后续。轻量专项工具可独立 HostApp，store 按草案注入，同一运行实体的控制权仍由后端统一裁决。

**最新前端方向：[统一 3D 工作台实施计划](00-overview/09-page-design-delivery-plan.md)。** 按 S11/S17 先统一主架构，再逐项接任务；下一个前端产物是对象树/视口/Inspector、相机与 Joint/TCP Target 可操作样板，继而接真实控制/采集/回放。诊断/元数据草案成果保留，不能代替主工作台。前端生产实现继续暂停。

| 阅读目的 | 入口 |
|---|---|
| 理解分类方法与维护粒度 | [阅读指南](indexes/01-reading-guide.md) |
| 先看完整产品边界 | [系统总览](00-overview/README.md) |
| 设计页面与交互 | [前端总索引](10-frontend/README.md) |
| 设计服务、控制与数据能力 | [后端总索引](20-backend/README.md) |
| 核对共同数据与协议 | [共享契约](30-contracts/README.md) |
| 看某个功能前后端如何对应 | [功能映射](indexes/06-feature-map.md) |
| 按画面区域找到功能 | [界面区域索引](indexes/03-ui-regions.md) |
| 按业务流程找到功能 | [工作区索引](indexes/02-workspaces.md) |
| 按机器人和任务配置查找 | [LanderPi / SO101 任务索引](indexes/08-robot-task-profiles.md) |
| 按问题、需求或来源查找 | [主题](indexes/04-topics.md) / [需求追踪矩阵](indexes/05-requirements.md) / [章节迁移](indexes/07-source-migration.md) |
| 查看决定与待讨论项 | [决策](90-governance/01-decisions.md) / [未决问题](90-governance/02-open-questions.md) |
| 直接开发当前最小范围 | [M1/M2 当前阶段](00-overview/10-first-task-closed-loop.md)、[任务字段](10-frontend/02-scene-setup/02-task-template-configuration.md)、[共享组件](10-frontend/02-scene-setup/05-shared-scene-components.md) |
| 查看开发任务、依赖与完成检查 | [M1 实施工作包](00-overview/09-page-design-delivery-plan.md) |

## 目录结构

```text
docs/specs/
├── README.md
├── 00-overview/              产品边界、Profile、状态域、机器人能力
├── 10-frontend/
│   ├── 01-shell/             全局导航、布局焦点、状态反馈
│   ├── 02-scene-setup/       场景布置与初态流程
│   ├── 03-simulation/        在线任务、运行录制、主臂面板
│   ├── 04-replay-annotation/ 同步回放与标注编辑
│   ├── 05-datasets/          数据查询、质量与导出预览
│   ├── 06-training-evaluation/ 训练/评估概念节点
│   ├── 07-viewport-tools/    共享 3D、选择、关节、TCP、物理受力
│   └── 08-observation-inspector/ 属性、传感器、时间轴
├── 20-backend/
│   ├── 01-session-scene/     会话、场景配置与初态
│   ├── 02-robot-control/     权限、执行、IK、外力、主臂桥
│   ├── 03-observation-algorithms/ 观测、专家、策略与任务
│   ├── 04-recording-replay/  原始采集、历史读取、标注存储
│   ├── 05-dataset-export/    质量、版本与训练出口
│   ├── 06-training-evaluation/ 作业、模型、结果
│   └── 07-existing-project-adapters/ 三个现有项目的接入
├── 30-contracts/             状态、命令、Episode、时间、来源、权限
├── 40-verification/          保留原 TEST 编号的待执行验收
├── 90-governance/            决策、未决、冲突、过程、维护与来源
├── references/               本地/开源资源登记与有限 PoC 计划
├── indexes/                  多入口导航与需求追踪
├── templates/                节点、功能包与决定模板
├── catalog.json              文档/功能包清单
└── traceability.json         需求→来源→主责规范→验收
```

大类和功能包各有 README，包内 `01-...md` 是设计节点。例如一个 TCP 功能分到：前端手柄与轨迹呈现、后端求解与执行、共享命令/时间语义、对应验收，而不是把四种职责写进同一篇前端文件。

## 当前必须带入后续设计的修订

- 关节滑条主要承担监控；默认只读是建议细化，具体编辑入口待定。
- V1 在 Scene Setup 创建、编辑、保存 Waypoint，Simulation 展示执行进度；用户已明确确认，旧排除项已被取代。
- VLA 控制中使用显式受控接管，鼠标选择/拖动不隐式覆盖策略。
- TCP 移动时需要虚线轨迹；默认表示 TCP、关节中心或组合尚未冻结。
- 实体主臂无独立相机；保留状态、映射、标定与跟踪误差。
- 用户已允许浏览器绘制 3D；仿真、感知、规划在服务器。当前工程方向沿已有分析采用 React + TypeScript 外壳、Three.js SceneView 复用、Dockview 先验证；具体库版本与兼容性未因文档存在而验证。

## 使用方式

后续按一个功能包逐个细化节点，更新相关契约、未决项和 TEST。相同规则只在主责文档定义，工作区用链接复用；所有已确认/已实现/已验证声明都需要相应来源或证据。详见 [维护规则](90-governance/05-maintenance.md)。

[来源总册](../设计过程与Specification总册_20261021.md) 保留历史；[上一轮工程分析](../frontend_analysis_v0.2.md) 保留为参考，已被新需求覆盖的建议不作为当前基线。

## 新增规范与机器索引

[功能包模板](templates/feature-package.md) · [规范节点模板](templates/spec-node.md) · [决策模板](templates/decision.md)

[文档清单](catalog.json) · [需求追踪数据](traceability.json)。机器索引只用于导航，不是运行时 API 或功能验收证据。

## V0.2 历史阅读入口（当前以 V0.6/S16 为准）

| 本轮完善内容 | 主责入口 |
|---|---|
| 四组导航、Data 入口与跨页流程 | [全局 IA](10-frontend/01-shell/01-navigation-context.md) |
| 模板与任务差异 | [任务模板目录](00-overview/07-task-template-catalog.md)、[场景配置](10-frontend/02-scene-setup/02-task-template-configuration.md) |
| SO101 2D/3D 布置与地图编辑 | [桌面摆放](10-frontend/02-scene-setup/03-so101-tabletop-layout.md)、[Waypoint](10-frontend/02-scene-setup/04-map-waypoint-editor.md) |
| A–H 布局与执行来源 | [布局预设](10-frontend/03-simulation/04-ah-layout-presets.md)、[Execution Profile](10-frontend/03-simulation/05-execution-profiles-policy-rollout.md) |
| 统一骨架下逐任务接入 | [开发路线](00-overview/08-unified-development-roadmap.md) |
| 开源与本地资源复用 | [参考索引](references/README.md)、[资源登记](references/open-source-resource-registry.md) |
| 修订、来源与用户确认 | [变更记录](90-governance/07-change-log.md)、[来源登记](90-governance/06-sources.md) |

四导航组和多数细化交互仍为设计方案；Waypoint 的 V1 范围已经确认。产品实现、PoC、任务验收均未因本次文档更新而启动。

## V0.3 图片化页面设计入口

本轮纳入 20 页 PPT 与素材目录 21 张独特图，建立 **21 个页面/视图节点，每页都有图片参考**。前端的八个功能包继续负责规则，新增页面设计层负责区域、操作、跳转和图片取舍，不另造业务后端。

- [先看页面图与导航映射](10-frontend/page-designs/README.md)
- [现有图片的 22 项冲突与收敛建议](90-governance/08-visual-design-conflicts.md)
- [统一导航、上下文和视觉规则](10-frontend/01-shell/04-visual-design-rules.md)
- [原图片与 PPT 页码对应](references/04-visual-asset-catalog.md)
- [页面细化与增量计划](00-overview/09-page-design-delivery-plan.md)

部分页面仍用原图局部作为参考，已标明图稿缺口；Real Robot/Offline Inference/大规模批量能力等保留为后续候选。原图、PPT 和总册均未改写。此次是文档完善，不宣称图中所有功能已确认、已实现或已验证。

## V0.4 历史更新：Simulation V2

[当前 Simulation 页面与新主图](10-frontend/page-designs/03-simulation.md) · [删除/替换清单与后续意见](10-frontend/03-simulation/06-simulation-v2-review.md)。仅更新该工作台及其共享规则，其他页面保留 V0.3 设计状态。旧图和 PPT 不删除；图片状态与产品验收继续区分。

## V0.5 历史更新：三图共用配置与完整目标

本节的 SO101/ACT 首发与训练前置建议现由 V0.6/S16 取代；原图与来源保留。

- [三张 Scene Setup UI Reference](10-frontend/page-designs/02-scene-setup.md)：导航、近场抓取、双臂转运，原样归档，旧图/PPT 保留。
- [Task Configuration 字段规范](10-frontend/02-scene-setup/02-task-template-configuration.md)：五类任务的字段、条件、建议默认和能力校验。
- [公共配置契约](30-contracts/07-task-scene-experiment-config.md) / [Route 资源版本](30-contracts/08-navigation-map-route.md)：Profile 唯一编辑、对象权限、Stale、已验证快照与创建门控。
- [共享组件清单](10-frontend/02-scene-setup/05-shared-scene-components.md)：共用一次、任务差异、后续能力，以及三图冲突修正。
- [F0 样板 / R1 真实任务](00-overview/10-first-task-closed-loop.md) / [验收](40-verification/06-scene-setup-first-loop.md)：最小训练/预测前移，Mock 与真实链路分别验收。

本轮更新文档、索引和参考素材；未运行仿真、采集、训练或预测。图片与目录里的能力标签不作为已接通证据。

## V0.6 更新：审核修复与 mobileCar 优先

- 当前阶段改为 [M1 mobileCar 四步闭环 / M2 bimanual 组件复用](00-overview/10-first-task-closed-loop.md)，完整数据/训练/预测保留后续；三图不是全部功能前置。
- [配置契约](30-contracts/07-task-scene-experiment-config.md) 明确 SceneVersion/SceneDraft/ExperimentDraft、覆盖解析、HostApp/store 作用域与分层唯一性；三张 Profile 卡与 Execution/Export 分开适用。
- [Episode/采集契约](30-contracts/03-episode-events-annotations.md) 合并旧引用集合，以固定快照为配置权威；收敛原生 start/RESET、finalize、失败保留、索引与只读回放。原生能力不自动等于平台适配已完成。
- [状态域](00-overview/04-runtime-state-domains.md) 补 Session lifecycle；[Collection/版本](30-contracts/05-dataset-model-lineage.md) 明确可编辑选择和不可变成员清单；[术语表](00-overview/05-glossary.md) 区分导航、工作区、页面和组件。
- 当前 **89 项 REQ、26 PNG/25 独特内容**；旧数字保留历史标签。[新增四项验收](40-verification/06-scene-setup-first-loop.md) 与既有条目均未执行。本轮仅修改文档/机器索引，不修改产品代码、原生工程或图片。

## V0.8 当前更新：身份绑定 STOP 与可靠录制结束候选（M1.4）

- [S19](90-governance/sources/S19-session-stop-recording-end.md) 明确本轮 Goal：STOP 与录制结束必须受 Session/运行身份约束，回执分层，且候选实现不等于部署或真实停车验证。
- [Session 生命周期](20-backend/01-session-scene/01-session-lifecycle.md#stop-与录制结束协议m1-stop-1--m1-end-1) 增加 `m1-stop-1`/`m1-end-1` 端点、拒绝与并发规则，允许访问的 native 路径由五个改为七个。
- [Episode 采集契约](30-contracts/03-episode-events-annotations.md#m14-身份绑定-stop-与可靠录制结束候选m1-stop-1--m1-end-1) 与 [控制命令契约](30-contracts/02-control-intervention-commands.md#stop-回执分层m14-候选) 固定"受理 / STOP 下发 / 停车证据与覆盖 / Recorder 排空 / 落盘终态与完整性"五层；`coverage_complete` + `integrity` 才是"整机停稳且录制完整"。
- [控制权契约](30-contracts/06-control-authority.md#stop-与控制权m14-候选) 明确安全 STOP 不是接管流程，也不得被新增 owner/lease 门槛挡住。
- 机器目录新增 S23 与 DEC-060，补充来源 18 个、文档节点 150 个、REQ 仍 89 项。M1.5c 真实帧关联只读切片与 run 身份边界修正（候选 `m1s-20261025T084308Z-platform`，`127.0.0.1:18966`）：run 目录身份改为每次构造读取位置时校验（索引缓存建立后换成 root 内兄弟 run 的软链不再以原身份读出，沿用 `history_path_escape`），历史只读面增为六条 GET（新增 `/api/v1/episodes/{episode_id}/frames`，schema `unirobot-mobilecar-frame-link-1`），帧关联只依据记录键并区分 `matched/partial/missing/unresolved_reference/identity_mismatch/stream_absent`，实测 303 帧四类键全命中而 `feedback_sample_id` 仅 3/303 有目标行、状态早于采集 0.34–8.78 ms 只作年龄呈现；86/86 与 28/28、聚焦 31 passed、全量 159 passed / 3 项历史失败，覆盖 946 文件 `drift=[]`。统一历史游标、同步 3D 与 M1.5/M1 验收仍未完成。见 [M1.5c 交付记录](../backend-m1.5c-frame-linkage.md) 与 [证据册](../evidence/m1.5c-frame-linkage/README.md)。
- 机器目录新增 S24 与 DEC-061，补充来源 19 个、文档节点 150 个、REQ 仍 89 项。M1.5d 帧读取分页/角色完整性修正、时间语义分离与历史姿态准备（候选 `m1v-20261025T161014Z-platform`，`127.0.0.1:18969`）：分页 `has_more` 只由"整页装满后是否还存在下一条合格锚点"决定且 `next_offset` 保持原始行号语义（空行/超限/坏行分别计数，越过末尾才声明无下一页）；角色完整性按必需 `sensor_kind` 与逐角色基数判定，重复候选返回 `ambiguous_kind`/`ambiguous_candidates` 并全部列出、不再默认取文件第一条；时间差按记录+字段+单位+符号+含义具名（真实首帧 2.885407/3.669841/3.668296 ms 三个不同量，`sim` 基差为 0，`observation_age_ms` 属管线延迟），schema 升为 `unirobot-mobilecar-frame-link-2` 并显式说明 `age_of_state_relative_to_frame` 的移除；历史只读面增为八条 GET（新增 `/api/v1/episodes/{episode_id}/robot-state` 与 `/api/v1/episodes/{episode_id}/model/assets/{asset_id}`，schema `unirobot-mobilecar-history-pose-1`），只读冻结 geometry bundle 且不代理当前 scene/snapshot/Actual；实测 102/102 与 28/28、聚焦 39 passed、全量 167 passed / 3 项历史失败，覆盖 946 文件 `drift=[]`，run 清单身份与 bundle 四项全等、23 资产逐文件校验、9 项映射 1 项 `partially_verified`（关节顺序凭证只到索引 3），底盘/四元数/夹爪/TCP/相机语义保持未证且不填默认值。统一历史游标、历史渲染验证与 M1.5/M1 验收仍未完成。见 [M1.5d 交付记录](../backend-m1.5d-frame-reading-and-pose-preparation.md) 与 [证据册](../evidence/m1.5d-frame-reading-and-pose/README.md)。
- 机器目录新增 S25 与 DEC-062，补充来源 20 个、文档节点 150 个、REQ 仍 89 项。M1.5e `sim` 时间量来源拆分、机械臂映射证据与按部件姿态就绪（候选 `m1x-20261026T065320Z-platform`，`127.0.0.1:18970`）：`state_sim_time_minus_frame_capture_sim_time` 只取状态负载 `sim_time_s`，事件信封值单列为 `state_event_envelope_sim_time_minus_frame_capture_sim_time`，缺值即缺席、不回退、修正记入 `version_migration.corrections`；机械臂顺序给出逐环源码链（`ARM_JOINTS` → `model.jnt_qposadr` → `self.arm.qpos[:5]`，第 6 项夹爪驱动被切片排除）及其在录制时段三个冻结快照中的存在与摘要一致，`writer_identified=false` 不编造旧构建身份；`render_source` 直接用模型弧度绘制、`conversion_is_required_for_drawing=false`，用户角公式与照片零位（`uncalibrated`）单列，`zero_model_rad` 更正为精确 `-π/2`；九项 `part_readiness` + `capability_summary` 分开固定模型装配（`available=true`）与整车重建（`false`），`escalation_forbidden`/`defaults_forbidden`；新增纯运动学模块与离线检查，同负载 TCP 复现 152/303 帧最大误差 1.69e-14 m、竞争根约定分离 0.0556 m、序反转 0.20967 m，底盘位置/四元数/TCP 位置升为 `verified`（映射 10 项中 4 项），夹爪 `unverified`、TCP 朝向与相机外参 `missing`，只支持运动学一致性不代表标定。同时显式更正 M1.5d 记录的两处超出证据表述（`-1.5708` 舍入、"平台配置不存在夹爪规则"），追加不回填。服务器实测 110/110、28/28、聚焦 45 passed、全量 179 passed / 3 项历史失败、64 次请求全为 GET、946 文件 `drift=[]`。资源准备、前端装配验证、历史姿态局部验证与正式 M1 验收分别表述。见 [M1.5e 交付记录](../backend-m1.5e-pose-readiness-and-time-sources.md) 与 [证据册](../evidence/m1.5e-pose-readiness/README.md)。
- 机器目录新增 S22 与 DEC-059，补充来源 17 个、文档节点 150 个、REQ 仍 89 项。历史 reader 只读整改与可复现发布（候选 `m1p-20261025T053030Z-platform`，`127.0.0.1:18964`）：只读由构造保证（51 次请求全为 GET）、路径解析覆盖索引与读取两侧、`event_seq` 区间过滤排除并计数非法序号、报告重算并绑定冻结摘要 `4090935b4c45c900…`；69/69 与 28/28、全量 147 passed / 3 项历史失败，并撤回超出证据的"全部原始文件未变"表述、更正 `transforms.jsonl` 非逐 body 位姿。见 [M1.5b 交付记录](../backend-m1.5b-history-readonly-hardening.md) 与 [证据册](../evidence/m1.5b-history-readonly-hardening/README.md)。
- 机器目录新增 S21 与 DEC-058，补充来源 16 个、文档节点 150 个、REQ 仍 89 项。真实历史 Episode/segment 只读 reader 首个切片（候选 `m1k-20261025T040435Z-platform`，`127.0.0.1:18960`）以五条受限 GET 读取 348 条真实录制，服务器 61/61 断言、已覆盖的 696 个身份文件摘要前后不变（其余文件无前置摘要，属未覆盖；一次人工 native validate 重写 1 个派生文件）；同步回放与新采集闭环未做。实现与证据见 [M1.5a 交付记录](../backend-m1.5a-history-reader.md) 与 [M1.5a 证据册](../evidence/m1.5a-history/README.md)，契约条款并入 [Episode/采集契约](30-contracts/03-episode-events-annotations.md)。
- 机器目录新增 S19，补充来源 14 个、文档节点 150 个、REQ 仍 89 项。实现与无物理集成证据见 [M1.4 交付记录](../backend-m1.4.md)。

## V0.8 当前更新：版本化地图与带朝向 Route 切片

- [S18](90-governance/sources/S18-navigation-map-route-slice.md) 补充本次明确需求：PointGoal 与每个 Waypoint 必须显式 `x/y/yaw`，缺失或 `null` 报错，显式 `0.0` 合法。S10 原文保留，不改写历史范围确认。
- [地图/Route 契约](30-contracts/08-navigation-map-route.md)、[任务模板](10-frontend/02-scene-setup/02-task-template-configuration.md)、[Waypoint 编辑器](10-frontend/02-scene-setup/04-map-waypoint-editor.md) 与 [后端执行边界](20-backend/03-observation-algorithms/03-map-waypoint-execution.md) 固定 m/rad、map +X/+Y、yaw 正方向、`[-π,π)` 归一化、origin 图像左下角、图像列 +X/行 -Y。
- 地图来源区分 G3B 历史离线与 live SLAM；Route Draft、不可变 Route Version、固定版本引用和 baseRevision 冲突进入主责契约。保存仅创建资源/显示数据，不执行导航、运动、RESET 或录制。
- 机器目录新增 S18 至 150 个文档节点、13 个补充来源；需求仍 89 项，图片不变。M1.3 后端候选已完成，产品端到端验收仍未执行。

## V0.7 更新：统一 3D 工作台计划复评

- [S17](90-governance/sources/S17-3d-workbench-replan.md) 重申统一主架构和好操作的 3D 界面；补 DEC-052～054，保留 M1/M2、专项轻宿主及既有后端。
- [实施计划](00-overview/09-page-design-delivery-plan.md) 增加架构/复用决定、A–H 工作台形态、交互服务与 M1.2a 样板门槛；[PAGE-03](10-frontend/page-designs/03-simulation.md) 同步。无新增产品需求或 TEST 编号。
- 机器目录新增一个来源节点至149，需求仍89项，图片不变；产品验收状态不变。本轮只修改文档/索引，前端实现继续暂停，详细兼容性与真实闭环尚待验证。
