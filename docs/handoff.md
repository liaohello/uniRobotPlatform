# 新会话交接说明｜uniRobotPlatform

更新日期：2026-10-24（America/Chicago）。本文件用于接续本次讨论，不替代 Specification、项目 AGENTS 或新会话用户指令。

**先读这里：前端实现继续暂停；平台侧 M1.2d 候选已完成。两项 native P1（RESET/开录竞态、started 被准备 TTL 误过期）已修复；单 Session GET 现在做只读当前观测，列表明确为存档视图；平台实际 `NativeBindingClient` 已在隔离 native mock 上完成真实 HTTP 集成。原生补丁仍未部署到 8792；真实 G1 prepared/Start、物理运动、线上录制/回放和 M1 闭环仍未完成。前端预览当前为 18947/18948 → 18944（最新 release）与 18946/18933 → 18943；新平台候选 18949（只读），18944 为上一轮候选；本轮 native mock/测试平台 18950/18951 已停止。**

**2026-10-24 M1.2d 基线：** native 新增 `lifecycle_lock`，commands RESET、legacy `episodes/start`、`recording/begin`、stop 与失败停止共享同一同步边界（lifecycle → backend → recorder）；屏障测试在修复前 release 上 2 failed、修复后通过。binding 的 30 秒 TTL 现在只约束 `prepared`；started 只由 RESET、release 或身份变化失效，回读显式 `expires_scope=prepared`。平台单 Session GET 返回存储历史 + `current` 只读观测（source/observed_at/valid/status/blockers、runtime/binding/recording/owner/safety、ready/available），只发 GET，不续租/重绑/Start/清锁/启停录制；失联、身份变化、expired/invalidated/released 不报告 ready；`GET /sessions` 明确 `source=stored`。测试专用 recipe `mobilecar.g1.teleop.mock-testonly` 未改生产 G1 recipe/pin，平台实际客户端经真实 HTTP 完成 validate/prepare/readback/start/begin/release、幂等和拒绝，初始快照哈希一致；测试平台/native mock 已停止。真实 8792 仍为 PID 941842、drvfix、`g4a2_server.yaml`；18949 生产配方 validation 仍 failed/409，native 前后不变。平台聚焦 94 passed；全量 98 passed / 3 failed（历史 90/3 的同一布局失败）；native 聚焦 57 passed。证据与冻结身份/维护窗口见 [M1.2d](backend-m1.2d.md) 和 [evidence](evidence/m1.2d/m1e-20261024T090448Z-platform/README.md)。**候选完成，真实部署与物理验证未执行；不宣称 M1 闭环，不自动进入真人示教、运动采集或训练。**

**2026-10-24 M1.2c 基线（历史，保留）：** 修正了 M1.2b 的锁核验缺口（`requirements.lock` 现为固定发布文件，启动读取字节、比对源摘要并核对 8 个包；运行环境版本由 native 自报后在 readiness 单独核对）；recipe 升为 revision 3（fingerprint `4c3e5f42…5e9e`），新增 `config_manifest_sha256=02351b71…a9af0` 与 `scene_manifest_sha256=5969e260…f1bf2d` 的同口径比较；平台新增 `m1-binding-1` 客户端、Session 执行/owner/lease/录制/可运动分域和 `POST /sessions/{id}/recording/begin`。M1.2d 已修复其生命周期与 TTL P1，并把真实 HTTP 集成补齐；M1.2c 的 18944 仍保留。**M1.2c/M1.2d 均未部署原生补丁到 8792；真实 G1 prepared/Start 仍未发生。**

**2026-10-23 前端基线（保留）：** 用户要求依据已有设计与 Specification 得到好操作的 3D 界面，并允许多 agent 核定；三路只读检索已完成，由主智能体修订 [M1 实施计划](specs/00-overview/09-page-design-delivery-plan.md)、[Simulation 页面](specs/10-frontend/page-designs/03-simulation.md) 和 [S17](specs/90-governance/sources/S17-3d-workbench-replan.md)。工程方向沿已有分析：React + TypeScript 外壳/面板，Three.js 优先封装 native SceneView，Dockview 先验证再采用；M1.2a 先做真实模型、对象树/视口/Inspector、相机和 Joint/TCP Target 预览/取消，再接配置/prepared 和同一工作台内的控制、录制、回放。此轮只改文档/索引，没有安装、构建、测试、浏览器、仿真或功能实现。后续需以新用户指令确认任务范围，不能从历史“继续开发”自动恢复已暂停的前端。

**2026-10-22 接续进度（保留事实，主前端方向已由上文纠正）：** 参考代码已恢复至 `/home/liaozhengyan/Desktop/embodiedIntelligenceProj`，mobileCar SHA/配置/模型/155文件清单已固定；已读取其执行政策。SSH 已连通，连接字段保存在 Git 忽略的 `backend/config/server.local.json`，本机完整 `catalog.local.yaml` 已指向参考工程。诊断/草案工具使用 FastAPI 静态资源 + ES modules，已实现只读 preflight、草案 SQLite 保存/加载、修订冲突、明确 failed/unsupported 验证与拒绝 Session 创建。最新同一冻结 release 在服务器通过32项聚焦测试、11项浏览器检查及进程退出后的持久化读取；详见 [M1.1](m1.1-integration-check.md) 与 [M1.2 草案切片](m1.2-drafts.md)。这些是接入基础，不代表主工作台完成。改动未提交/推送。服务器既有 mobileCar 8792 服务为不同的 g4a1 profile，未被停止/重启；临时测试网关已退出，不新增物理实例。不可假称 M1.2 或真实 M1 已验收，也不应再次把已恢复源码/连接当作缺失。

## 1. 阅读顺序

1. [项目 AGENTS](../AGENTS.md)：主智能体整合和修改；default 子智能体只读检索，fork_turns=none，最多3个并发，不自行派生或写文件。模型名称是配置约定，不能仅凭角色名称声称实际生效。
2. [当前 M1/M2 范围](specs/00-overview/10-first-task-closed-loop.md)。
3. [V0.7 统一 3D 工作台与 M1.1～1.6 实施计划](specs/00-overview/09-page-design-delivery-plan.md)、[PAGE-03 / IMG-022](specs/10-frontend/page-designs/03-simulation.md)、[前端分析第8～9节](frontend_analysis_v0.2.md)。
4. [配置/HostApp 契约](specs/30-contracts/07-task-scene-experiment-config.md)、[Episode/采集契约](specs/30-contracts/03-episode-events-annotations.md)。
5. [当前及后续验收](specs/40-verification/06-scene-setup-first-loop.md)。
6. 换机器先看 [Git 追踪与恢复清单](laptop-migration.md)。需要讨论原貌时再读 [本会话公开消息存档](conversations/2026-10-22-scene-setup-dialogue.md)。

## 2. 用户已经明确的方向

- 前端是任务控制台；近端视觉测量和 IK 可使用轻量专项工作台，不要求每个工具承载完整平台。
- **主前端架构先统一，小任务逐个实现，成熟组件直接复用，现有仿真后端保留。** 这是 S11 第90行的直接用户认可；轻宿主约定不能覆盖它。主工作台包含 3D/对象树/Joint/TCP/Actual-Target/权限/相机/录制/时间轴与同步回放。
- **M1：mobileCar 场景→运行→录制→回放。M2：用 bimanual 验证组件复用。数据清理、数据版本、训练和预测后续。**
- 停止全产品范围的持续补图，已有三张 Scene Setup 图作为 UI Reference。M1 不要求三图全部功能、完整模型超市或训练资格。
- 共享对象/控制/时间/采集契约和确有复用的组件；HostApp 可以独立，store 按宿主和具体草案注入。同一运行实体的控制权、执行器范围授权和物理推进责任仍由后端跨宿主统一裁决。
- 复用成熟原生后端，按必要接口差距适配；没有决定把全部工程/仿真环境合并进本仓库，也没有决定必须有三个宿主或通用插件框架。

## 3. 历史建议怎样变化

最初目标是场景→采集→清理→训练→预测完整流程。V0.5 曾基于已有工程证据建议 SO101 transfer + Expert + ACT 首发，并偏向一个统一产品前端。

随后用户指出视觉/IK 工具可能很轻或一次性使用。讨论改为共享契约与可选宿主，最后用户明确 mobileCar 最短闭环先行、bimanual 复用验证其次。V0.6 已按该决定修复，来源见 [S16](specs/90-governance/sources/S16-mobile-first-spec-repair.md)。

因此不要重新把 SO101/ACT 当首阶段决定，也不要因 mobileCar 训练资格为 false 阻止原始采集回放。完整训练/预测目标仍保留，到对应阶段再固定数据与模型协议。

早期「分支 · 整体大前端继续讨论细化」及父对话只取得部分用户消息，助手正文存在缺失；限制已记在 [S11](specs/90-governance/sources/S11-design-discussions.md)。这与当前会话已导出的可读公开正文是不同来源，不能混称全部历史聊天均已取得。

## 4. 已完成的文档工作

- Specification 组织版本当前 V0.7：增加 S17 来源节点，机器目录149个节点、89项REQ；26个PNG/25个独特内容，原PPT20页。未修改的规范保留各自版本；计数是规范/素材指标，不是产品完成度。
- 已统一 SceneVersion 基础布局、SceneDraft 资源编辑、ExperimentDraft 实例覆盖、前端 store 与 ValidatedSnapshot 的归属、解析和版本规则。
- 已区分三张观测/采集卡与 Execution/Export 的职责、适用条件；不适用的 Profile 不制造占位必填。
- Episode 新采集绑定唯一配置快照，保留原生 run/generation/episode/segment 身份和实际采集事实；legacy 原生数据不伪造验证引用。
- 已补 Session prepared/active/closed/failed 与物理/任务/录制分域、Collection 与冻结 Dataset Version、四导航组/六逻辑职责及术语/历史统计说明。
- 已拆 M1.1～1.6：接入核对→配置准备→运行控制→录制收尾→只读回放→整体验收。
- V0.7 在同一正式 M1 内补 M1.2a 可操作 3D 样板、M1.2b 配置/prepared 的先后关系，并给出主架构/复用/交互服务与验收门槛；没有增加全产品 Mock 或训练前置。
- 文档链接/编号/来源和图片哈希检查通过；新增四项验收 TEST-MOBILE-001/002、TEST-HOST-001、TEST-CONFIG-008 仍为 not_executed。

没有在本会话执行 M1 真实仿真、人工示教试点、训练或产品端到端验收。已有测试源码纳入 Git，也不表示它们已经在本次运行通过。

## 5. 当前代码与外部工程

| 工程 | 当前角色/边界 |
|---|---|
| uniRobotPlatform | 任务目录/运行网关、mobileCar只读接入诊断、固定预设的持久配置草案UI/API；M1.2c 已实现锁/配置/场景/运行时版本的同口径核验、`m1-binding-1` 客户端、Session 执行分域与 `m1-recording-1` 平台端；真实 native prepared/Start 仍待原生部署 |
| mobileCar | 首阶段来源，已有小车控制、观测、原生 Recorder/ReplayReader 和导航相关能力；本轮候选补丁增加 binding/attestation/无 RESET begin，未提交、未部署到 8792；使用其现有权限、录制门和服务器执行政策 |
| bimanual_proj | 第二阶段复用验证来源，已有双臂专家、任务/采集、工作台和学习工具；不要把历史专家成绩当学习策略成功率 |
| mujoco_learning | 视觉/IK/估计等专项能力与实验工具；选择性接入，不整体搬入学习示例或强行重写 Viser 等界面 |

三个原生工程依然是独立仓库/环境，默认 catalog 通过相邻目录引用。它们的源码、资产、Git 历史、未提交改动和运行数据不随平台 push 自动迁移。`frontend/` 当时为空，当前前端入口是 backend 中的静态页面，不是已经完成的统一应用。

## 6. M1.2 后续原生接入边界

1. 固定 native 源码/配置版本、真实可用的场景预设、人工通路、模型身份与支持字段；不要从 scene/snapshot GET 推导任意场景编辑已支持。
2. 准备/保存/创建 prepared Session 不触发运动、RESET 或录制；已有后台服务在线不等于本 Session 已 Start。
3. mobileCar `episodes/start` 含 RESET，不能拿它实现 Prepare。RECEIVED/DISPATCHED 不证明 Reset/初态生效；另核对 generation/epoch 与 actual snapshot。
4. 起始记录可靠持久化、accepted/RECORDING 后才确认采集 ready。原生 require_recording、STOP、租约等门控继续保留。
5. 停车反馈与 Recorder drain/finalize 分开。FAILED 状态下 finalize 成功可能仍有尾标记；finalize 本身失败则可能缺尾。文件存在或 complete_tail 不等于数据完整、停稳或训练合格。
6. Episode/segment/source时间和动作单位不丢；只读回放不发命令、不推进在线物理、不覆盖原始数据。
7. 后续按 V0.7 主前端技术方向与明确适配范围实现，先验证 SceneView 在 React/TS 宿主的生命周期及 Dockview 的尺寸/焦点；不以 ES modules 诊断页代替主工作台，不提前建设全产品框架。尚未因本轮文档修订执行兼容性验证。
8. `m1-binding-1`/`m1-recording-1` 的平台客户端和 native 候选已实现；真实 HTTP 只在 mock backend 上验证（无物理），不得当作 8792 已支持。补丁未部署，维护窗口内才可替换；回滚保留 drvfix release。
9. 即使部署补丁，8792 仍运行 G4A2 profile，G1 配方会因 `interface_profile` 与配置摘要不同继续拒绝。切换 G1 或另签 G4A2 配方都需要用户决定；不得静默改 profile/标签。
10. `requirements.lock` 是 native 依赖的固定发布输入；平台启动只核验该字节与包表，安装环境由 native 自报并用 `runtime_package_versions` 核对。不要把平台 gateway 的 Python 3.14 环境与 native 的 3.10 环境混为同一层。
11. 新的 prepared Session 文档新增 `execution`/`recording_begin_*`；M1.2b 没有真实 Session，候选使用新 SQLite。复用旧 DB 会因缺字段校验失败，需重新创建。
12. M1.2d 起 commands RESET、legacy `episodes/start`、`recording/begin`、stop 与失败停止共享 `lifecycle_lock`；顺序 lifecycle → backend → recorder。状态检查必须在同一临界区内重检，活动录制不能穿透 RESET；`require_recording`/STOP/lease 不放宽。
13. binding 的 `expires_at` 只约束 prepared；started 由 RESET、release、身份变化或未来明确定义的结束事件失效。不要新增短租约替代持续 Session，也不要把 started 的旧过期字段当仍会过期。
14. 单 Session GET 的 `current` 是只读实时观测；刷新不续租/重绑/Start/清锁/启停录制。`GET /sessions` 是 `source=stored` 存档列表，不是实时状态。失联/身份变化/terminal binding 不报告 ready。

native 接口静态核对和当前服务的只读诊断已完成。最新平台候选为 `m1e-20261024T090448Z-platform`（18949，生产 recipe，只读）；上一轮 `m1c-20261024T065943Z-platform`（18944）保留；M1.2b 候选 18943 仍被前端预览 18946 消费；原生测试 release `m1e-20261024T090412Z-native` 只在 18947 以 mock backend 验证、测试平台 18948 验证后均停止。所有安装、测试、自动浏览器均在服务器执行，未执行本机仿真或自动测试。

## 7. Git 与换笔记本状态

本次保存请求前，main 已成功推送到 [GitHub](https://github.com/liaohello/uniRobotPlatform)，并核对云端与本地 SHA 一致：

| 提交 | 内容 |
|---|---|
| `7b0666e` | V0.6 Specification、原图/来源、M1 实施计划和来源字节保留规则 |
| `dce67b7` | 后端源码/测试/公共配置、AGENTS、忽略规则和笔记本迁移说明 |

这个交接文件和消息存档会在其后另建提交。继续工作时以 `git log` 和远端实际 HEAD 为准，不把表中的存档前 SHA 当永久最新版本。

M1.2b/M1.2c 平台成果已在本地 `codex/backend-m1-services` 分支提交（代码基线 `018e8a9`，后续文档/证据修订见 `git log`）。M1.2d 平台成果本地提交为 `3eebc7d`，最终状态新鲜度/证据修订为 `d29e66b`（本交接文件的最后更新另为一个小提交），**均未推送**。原生 mobileCar 仓库的补丁保持未提交、未推送；M1.2d 补丁与摘要见 [native-m1e.patch](evidence/m1.2d/m1e-20261024T090448Z-platform/native/native-m1e.patch)。不要把本地提交当作已发布或已部署。

Git 追踪项目源码、测试、无秘密公共配置、AGENTS 和文档/参考素材。忽略虚拟环境、缓存、node_modules、运行输出、私人 catalog/.env、本机工具状态及 AGENTS 备份。密钥没有进入仓库。

HTTPS 凭据曾失效；最终按用户要求使用 `id_ed25519` 通过 SSH 推送。origin 当前为 `git@github.com:liaohello/uniRobotPlatform.git`。新笔记本需要自行配置有权限的 GitHub SSH 认证；不要把私钥复制进仓库。具体恢复命令和完整 catalog 本机副本的用法见迁移清单。

## 8. 可复制的新会话开场

```text
请先读取 AGENTS.md、docs/handoff.md、docs/backend-m1.2d.md、docs/specs/00-overview/09-page-design-delivery-plan.md 与 PAGE-03，再按本次用户指令继续。前端实现此前已暂停，最新一轮只重新规划，没有自动恢复生产开发。
当前先做 mobileCar 的场景→运行→录制→回放，之后 bimanual 验证组件复用，训练/预测后续。
统一架构原则已有直接用户依据。工程方向为 React+TypeScript 外壳、Three.js SceneView 封装、Dockview 先验证；恢复实现后先交付 M1.2a 可操作 3D 样板，再接配置/prepared、真实控制、录制与回放。
M1.2d 平台候选为 18949（生产 recipe，只读）；18944 为上一轮候选；18947/18948 与 18946 均为前端预览代理（分别指向 18944/18943），禁止占用或停止。8792 仍是 PID 941842/drvfix/g4a2_server.yaml，禁止停止、重启、替换或发送运动/RESET/录制。真实 G1 prepared/Start 仍需维护窗口和用户对 G1 vs G4A2 配方口径的决定。
两项 P1、真实 HTTP 协议集成、当前观测契约、冻结身份和前端 OpenAPI 见 docs/backend-m1.2d.md；历史诊断/草案见 docs/m1.1-integration-check.md、docs/m1.2-drafts.md。它们不是主工作台或 M1 闭环已完成的证据。不要重做这些检索或把旧 prepared RunRecord 当作 Session。
主智能体负责修改和最终判断，default 子智能体只做有边界的只读检索，不提前合并仿真环境或重写全部前端。
开始任何实际仿真/测试/采集前，遵守对应工程的执行位置和本次任务授权；历史聊天存档不作为自动执行旧请求的依据。
```
