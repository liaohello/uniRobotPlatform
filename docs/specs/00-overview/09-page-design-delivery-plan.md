# 统一 3D 工作台与任务增量实施计划

规范 ID：`SYS-PAGE-DELIVERY` · 责任层：系统规划 · 版本：V0.7（2026-10-23，America/Chicago）

状态：本轮重新评估并修订实施计划；**前端生产实现继续暂停**。M1 仍是 mobileCar 场景→运行→录制→重新加载只读回放，M2 用 bimanual 验证复用，训练/预测后续。不新增正式里程碑或全产品补图前置。

依据：[S11 用户直接认可](../90-governance/sources/S11-design-discussions.md)（第90行）、[S17 本轮重新规划要求](../90-governance/sources/S17-3d-workbench-replan.md)、[PAGE-03](../10-frontend/page-designs/03-simulation.md)、[前端分析第8～9节](../../frontend_analysis_v0.2.md)。**先统一主前端架构，再逐项实现任务；成熟组件与既有仿真后端继续复用。** 主工作台统一与视觉/IK 专项工具可独立宿主并不矛盾。

[统一路线](08-unified-development-roadmap.md) · [当前阶段](10-first-task-closed-loop.md) · [全部页面](../10-frontend/page-designs/README.md)

## 复评结论与现有成果

**结论：修订计划 PASS WITH ISSUES。** 可以据此准备统一工作台的交互样板；Joint 拖动映射、TCP 自由度/参考系、布局手感及性能阈值仍需样板核实，真实执行继续受 native 绑定与录制门控约束。本轮未实施或验收工作台。

| 发现 | 证据与实际影响 | 本轮最小修正 |
|---|---|---|
| FE-R1 / P1：原计划缺少主工作台架构与可操作 3D 门槛 | S11 第90行、PAGE-03 的 A–H 与 Joint/TCP；原 M1.2/1.3 只要求最小宿主/运行视图，诊断草案被当作主前端技术方向。无法据此验收持续遥操作体验 | 主架构采用下述 React/TS + Three.js 方向；M1.2 先交付可操作 3D 样板，M1.3 在同一骨架接真实控制 |
| FE-R2 / P1：诊断读取不等于工作台运行接口 | `backend/src/unirobot/mobilecar.py:18` 仅四个 native GET，`api.py:97` 起为 preflight/草案/拒绝 Session 创建；缺少持续状态、命令、控制权、录制及回放适配 | 按下面的工作台交互服务补最小边界；保存已有草案 API/SQLite 与接入证据 |
| FE-R3 / P1：可复用 renderer 尚不满足全部 3D 交互 | native `scene-view.js:183–222` 只拾取 TCP 球并沿屏幕平面拖动；`:450–493` 是末态 Ghost 与目标辅助线。不能据此宣称通用对象选择、Joint 工具或完整轨迹已完成 | 封装并扩展 SceneView；补选择/手势仲裁、Joint/TCP 目标工具和真实轨迹语义，避免重写整套 renderer |

已完成的接入诊断、源码/预设 pin、草案保存/冲突/过期反馈保留。[M1.1](../../m1.1-integration-check.md) 与 [M1.2 草案切片](../../m1.2-drafts.md) 的服务器证据有效：最新32项聚焦测试、11项浏览器检查及退出后重载，覆盖诊断和元数据草案。它们不证明 3D 工作台、prepared Session 或真实 M1 已完成。FastAPI 静态资源 + ES modules 的选择仅保留为该诊断工具的历史实现，不能继续约束主工作台架构。

## 主前端架构与复用决定

这是本轮工程执行建议，不冒称用户已逐项指定库及版本。实现前按目标环境固定锁文件，不以“最新版”作为兼容性结论。

| 部分 | 执行方向 | 复用与约束 |
|---|---|---|
| 应用外壳、配置、面板与状态 | React + TypeScript；同一平台内 Setup / Simulation / Replay 共用导航、上下文及面板职责 | 复用已有草案/验证契约；布局、选中和相机按视图持有，草案按 draftId/revision 注入，运行状态按 Session 注入 |
| 三维视口 | Three.js，优先封装 mobileCar 的 SceneView，补 TS 边界与生命周期 | 保留场景资产、坐标变换、关节链和 Actual/Ghost 映射；不整页导入耦合 DOM 的 native `main.js`；不先为 R3F 重写场景 |
| 面板布局 | Dockview 为首选候选；先用固定 A–H 默认布局验证 | 先核对 React/Three 尺寸变化、焦点、面板隐藏/重挂载与资源释放，再决定采用；不把浮窗/跨窗口/复杂布局编辑作为首个样板前置 |
| 相机、拾取与目标手柄 | 复用 OrbitControls；Raycaster 选择；评估 TransformControls 操作 TCP 目标标记 | Joint Ring 按机器人关节轴/限位适配；通用手柄不直接改 Actual mesh，不代替 IK、规划、权限或安全检查 |
| 状态与传输 | 面板订阅状态与 Three 渲染更新分开；先用 React 自身状态/必要的外部状态订阅桥 | 不预装多套全局 store。HTTP/既有轮询可继续用；实测频率/带宽后再决定 WS/SSE。渲染和面板频率不决定 Recorder 采样频率 |
| 部署与后端 | 前端构建产物仍可由 FastAPI 静态托管；native 继续负责仿真、控制、相机及 Recorder/Reader | 静态资源部署可以承载实时工作台；浏览器不增加第二物理循环，也不用第三人称画面冒充训练 RGB |

已有 native 根目录为 `/home/liaozhengyan/Desktop/embodiedIntelligenceProj/mobileCar`，固定 HEAD 见 M1.1。`package.json:5–13` 将 `src/mobilecar/ui/web/main.js` 构建为被忽略的 `ui/static/app.js`；后者未生成不表示渲染源码缺失。当前锁定 Three.js 0.180.0、esbuild 0.25.10 是复用兼容性输入，不自动成为新主前端的升级要求。

| 可复用边界 | 已核对源码 / 必须补齐的内容 |
|---|---|
| SceneView 生命周期与渲染 | `src/mobilecar/ui/web/scene-view.js:34–117,243–438,533–634`：容器/回调注入、Orbit、模型/关节/快照映射、ResizeObserver/渲染/销毁。封装时核验卸载后的监听器、RAF、计时器和异步资产释放，不据静态阅读宣称兼容 React 已通过 |
| TCP/Joint 交互经验 | `web/main.js:377–413,952–1055`：真实限位、目标编辑不被 Actual 覆盖、目标变化作废旧 plan、按 plan_id 执行。移植这些语义到面板/目标状态，不连同整页工作流直接搬入 |
| 数据边界 | `web/api.js` 与 native SceneManifest / RobotSnapshot / PlanPreview：复用身份、单位及回执；原生录制/回放和底盘门控继续保留 |

建议新主应用位于 `frontend/`，最小按 `app`（装配/上下文）、`workbench`（布局/面板）、`viewport`（renderer/工具）、`features`（Setup/Run/Replay）、`adapters`（服务/类型映射）组织；这是待实施目录，不声称已经存在。面板不各自维护另一套 fetch/控制权。轻量 IK/视觉工具可只复用契约，不要求重写原界面或建设通用插件平台。

选型资料：[React 外部系统生命周期](https://react.dev/reference/react/useEffect)、[Three.js TransformControls](https://threejs.org/docs/pages/TransformControls.html)、[OrbitControls](https://threejs.org/docs/pages/OrbitControls.html)、[Dockview 官方仓库](https://github.com/dockview/dockview)。这些库提供 UI/交互机制，机器人控制契约仍由项目负责。

## 可操作 3D 界面的交付形态

沿用 IMG-022 的区域和 [A–H 主责规范](../10-frontend/03-simulation/04-ah-layout-presets.md)，3D 占主区；高级配置/诊断折叠，保持操作时布局稳定。下图表示区域关系，不冻结像素尺寸。

```text
A  项目 / Robot / Scene / Session / 连接与数据源
B  仿真 / 任务 / 录制操作        C  部件 Owner / 申请接管 / 回执
┌────────────────┬────────────────────────────────┬────────────────────┐
│ D 对象树       │ E 3D 主视口                    │ F Inspector        │
│ 搜索/显隐/选中 │ Select / Joint / TCP / Layers │ Actual / Target    │
│ 与视口联动     │ 标准视角 / 聚焦 / 目标与轨迹  │ 夹爪 / 命令反馈    │
│                ├────────────────────────────────┤                    │
│                │ G RGB-D / 实际可用相机与流状态│                    │
└────────────────┴────────────────────────────────┴────────────────────┘
H  时间轴：阶段 / 部件来源 / 命令与接管事件 / 录制边界
```

Human / Expert / Policy 使用同一工作台；M1 先接实际 Human 通路，其他来源按真实能力显示原因，M2/后续接入时不另建一套页面。机器人自由度、相机数量与执行器组取真实能力，不能照搬图中的 6-DoF、腕相机或虚构独立夹爪 Owner。

| 操作 | 必须可见的行为与边界 | 既有验收依据 |
|---|---|---|
| 观察与选择 | 旋转/平移/缩放、标准视角/聚焦；对象树、mesh 高亮和 Inspector 联动。选择、Active Arm 与 Owner 分开；相机操作不发运动 | TEST-SEL-001～006 中当前单臂适用部分 |
| 手势与输入焦点 | pointerdown 锁定本次语义；手柄命中、对象拾取、空白相机拖动分别处理；拖手柄时禁 Orbit。框选/修饰键与相机默认绑定需显式仲裁；输入框不触发驾驶 | TEST-INPUT-001/002，TEST-SEL 的边界规则 |
| Joint | 默认监控只读；显式 Joint 模式出现对应轴/环，形成所选关节 Target，与数值编辑同源。关节类型/轴/限位/单位取能力；native 要求全臂向量时保留其他目标，不用 Actual 无故覆盖 | TEST-JOINT-001/002 |
| TCP 与轨迹 | 轴/平面拖动与数值框共用一个目标及版本、Frame、单位；显示 Actual / Target / Ghost 与残差。目标连线、末态 Ghost、候选 q(t) / 关节中心轨迹、Actual Trail 明确区分；不能只留一条 TCP 线替代原关节轨迹要求 | TEST-TCP-001～003；轨迹主责规范 |
| 提交、取消与连续操作 | 第一轮先验证 Preview-Confirm，预览/取消不改 Actual；目标变化使旧计划失效。Live 能力按已支持通路显式开放，保留整体需求；连续底盘输入单独门控。ESC 取消未提交目标，不能回滚已受理运动；STOP 是独立控制 | 命令/权限契约；TEST-INPUT-003、TEST-AUTH |
| 控制权与反馈 | 先申请再控制；Pending 禁止发人工动作，确认/拒绝可定位。受理、IK、规划/检查、执行和到位分开；旧来源队列失效与显式恢复由后端裁决，UI 不自授权限 | TEST-AUTH-001～003 |
| 观测、录制与回放 | 状态/相机带 source 时间与陈旧/缺失提示；仿真/任务/录制三域独立。录制看后端确认和 finalizing；Replay 用历史来源与统一游标，无执行命令服务 | TEST-REC、TEST-REPLAY、TEST-MOBILE-001/002 |

## 工作台所需的最小服务边界

沿用 [状态](../30-contracts/01-robot-world-state.md)、[命令](../30-contracts/02-control-intervention-commands.md)、[权限](../30-contracts/06-control-authority.md)、[时间/单位](../30-contracts/04-time-frames-units.md)、[配置](../30-contracts/07-task-scene-experiment-config.md) 和 [Episode](../30-contracts/03-episode-events-annotations.md) 契约；以下是待适配职责，不是已提供的新 HTTP 路由。

| 工作台需要 | 最小适配内容 |
|---|---|
| 加载/观察 | Scene/资产与稳定对象 ID、能力/限位/坐标变换；带 native 身份和时间的 Actual/传感器状态，明确 offline/history/live |
| 编辑/准备 | 现有 Draft API 与服务端解析/验证；固定 ValidatedSnapshot、无执行副作用的 prepared 绑定与显式 Start，不以探活替代 Ready |
| 人工控制 | 每执行器组 Owner/lease、Target/plan revision、命令 ID/来源/TTL、回执/终态/拒绝、STOP；TCP/Joint 与底盘适配共用权限权威 |
| 录制/历史 | RESET 应用确认、录制起始持久化、停车与 finalize 独立回执；run/episode/segment/config 映射及只读状态/媒体/事件 reader |

公共类型在适配边界与真实后端字段对齐，不先设计全平台事件总线或任意机器人通用 API。Replay 复用渲染与面板，注入只读历史数据源；不能只把在线控制按钮变灰而仍注入执行服务。订阅/渲染卸载不等于停止 Session 或录制；持续输入必须清理。

## M1 实施工作包与新顺序

M1.1～1.6 仍是同一个正式 M1 内部工作包。M1.2 内的 a/b 为实施顺序，不新增里程碑；当前只完成诊断/元数据草案子集。

| 工作包 / 依赖 | 可交付产物与复用范围 | 完成门槛 / 当前状态 |
|---|---|---|
| M1.1 接入核对与技术基线 / 无 | 保留 native 版本/资产清单、接口/身份/能力/缺口映射；主前端技术方向由本轮纠正 | 接口核对已有证据；原“最小 ES modules 即主前端”结论不沿用。React/SceneView/Dockview 兼容性须在 M1.2a 实测 |
| M1.2a 统一外壳与可操作 3D / 1.1 | **下一份前端可检查产物**：React/TS 外壳、固定真实模型/场景、对象树/Inspector/相机联动、Joint/TCP 目标预览、Actual/Ghost 区分；观测/时间轴有统一区域和来源语义 | 优先证明可观察、可选中、可编辑目标、可取消；验证 resize/焦点/卸载和布局手感。无绑定时用明确标记的固定/历史/合成数据，不假造 live/Session Ready 或执行成功；相机/轨迹缺失明确显示。当前未实施 |
| M1.2b 配置与准备 / 1.1；复用 1.2a 的外壳 | 将已保存草案/验证界面纳入 Scene Setup；实现后端验证、ValidatedSnapshot 与 native prepared 绑定 | TEST-CONFIG-003/004/005/007/008 的已开放部分；保存/准备不触发运动、RESET 或录制。native 绑定可独立适配，但进入真实 Run 前必须完成；当前只有元数据草案 |
| M1.3 同一工作台内运行与人工操作基础 / 1.2a+b | 显式 Start、实时 3D/Actual、实际相机、受门控的 Joint/TCP/夹爪/底盘操作、命令回执、权限与停止 | 适用 TEST-SEL/JOINT/TCP/INPUT/AUTH；后端确认 runtime/Session 绑定。受理不等于到位，目标不改 Actual；失焦/切页清持续输入。require_recording 仍门控，实际运动检查须等 1.4 录制 ready，不为工作包顺序绕过保护 |
| M1.4 在同一工作台录制与收尾 / 1.3 的运行/状态基础 | 包装原生 episodes/Recorder，显示 RESET、实际初态/epoch/segment、录制状态、配置 sidecar、停车与收尾 | 开录含 RESET 须确认实际生效；起始内容持久化后才确认 RECORDING。停车、drain/finalize、任务结果/完整性独立；失败/缺尾保留。与 1.3 联调真实驾驶；TEST-MOBILE-002 |
| M1.5 同组件只读回放 / 1.4；reader 可提前独立适配 | Episode 列表/详情，复用 3D、相机、状态/曲线、来源/事件时间轴，注入历史 reader 与统一游标 | 结束后重载仍可回放，不发控制/RESET/物理步进、不改原始数据；保留 native 复合身份，缺流/损坏可见，training_qualified=false 不阻止合格原始读取 |
| M1.6 整体验收 / 1.2～1.5 | 真实操作者完成配置→运行→持续遥操作观察→录制结束→重载同步回放；记录冻结输入、运行/数据身份和限制 | TEST-MOBILE-001/002、适用配置及上述交互/工作区验收；同时检查失败/Reset。接口测试与截图不能替代用户可操作闭环；通过后结束 M1，再进入 M2 |

**样板门槛不能被后端进度替代。** 后续获得实现授权时，首先交付 M1.2a 的可操作 3D 样板，再扩大页面与 native 集成；不再把新增诊断卡/表单作为主前端完成依据。样板可先使用带来源标识的数据，不等同于真实控制已接通。

性能验收先测目标客户端/服务器链路及典型模型：渲染帧率、拖动到本地 Target 反馈、状态/图像年龄、命令往返与回放同步偏差。再在相关实现前固定可复现门槛；本轮不凭空承诺帧率/延迟。手柄的本地目标反馈不应逐次等待网络，Actual 仍只由后端状态更新。

主智能体负责设计、修改、验证与整合；只读子代理可并行定位来源/接口和核验证据，不运行写入型验证。本轮三路检索均已完成。具体实现中的文件保持单一写入者。

所有涉及 mobileCar 的安装、构建、lint/typecheck、测试、仿真、渲染、自动浏览器与数据导出继续遵守 native 服务器执行政策；连接信息不入 Git。当前占用的 native 物理实例不能自行停止或并行再开；这不阻止只读来源分析及获授权后在服务器验证不启动物理的前端样板。本轮只修改文档和索引。

## 尚待样板核实与后续范围

无需用户重新确认已认可的统一架构原则；下列为工程核实项，尚未执行：

- Joint Ring 的角度映射/视角退化、TCP 的可用姿态自由度和 Frame 映射，按能力形成明确样例，避免 UI 承诺 5-DoF 机器人不能完成的 6-DoF 目标。
- 单击/双击/框选与 Orbit/手柄的优先级、输入焦点/松键/失焦，以及 Draft 与 Target 取消的反馈；采用主责交互规范，不另造第二套语义。
- Dockview 的尺寸/焦点/生命周期、默认面板比例与典型操作测量；若候选不满足要求，记录具体证据后局部更换布局实现，不重选整套架构。
- 真实控制接入前对齐 Owner/lease/旧队列失效/失败恢复和每种命令终态；保留物理暂停、Reset/End Task 对活动 Episode 的既有未决转换，在相关操作开放前明确。真实回放前固定 source 时钟映射、缺流显示和同步阈值。

M2 用 bimanual 注入不同能力、关节/相机/单位、控制与历史服务，验证同一外壳/视口/Inspector/时间轴复用及 TEST-HOST-001；不以强制重写旧 Viser 等工具证明统一。Force/复杂多臂交互等按既有相关阶段开放，不在 M1 虚构可用。Waypoint V1 编辑保存范围保留，热重规划不因此开放。

后续 Collection/Dataset Version、训练/预测到相应阶段固定资格、模型 IO 和真实产物；本轮架构为其保留导航/上下文和共用面板边界，不提前实现。验收定义见 [QA-SCENE-FIRST-LOOP](../40-verification/06-scene-setup-first-loop.md)，正式 M1/M2 仍待执行。

## 原 V0.3 图稿缺口登记（不再是开发前置）

| 待补图 | 当前可用参考 | 需要解决的问题 |
|---|---|---|
| 完整 Episode Library | IMG-004 的左侧列表 | 表格/筛选、混合来源、完整性/结果/用途独立列与返回状态 |
| Dataset Version/Export | IMG-005 的右栏与 Statistics | 固定版本、划分、字段映射、资格错误与导出报告 |
| 导航编辑与执行 | IMG-002 路线局部、IMG-003 通用运行 | 地图坐标/朝向、草案与活动路线、进度/失败定位 |
| SO101 2D 布置/在线三相机 | IMG-002 的 2D 入口、IMG-009/019 布局 | 真实模型与工作范围、三路 RGB、左右臂控制来源和阶段 |
| Offline Inference | IMG-008 的模型/输入/输出 | 删除第二套运行器，输入完整性与预测不可执行的区别 |
| Training Setup / Eval Setup | IMG-006/014 的配置区域 | 把草案与监控拆清、固定版本与后端校验反馈 |

这些缺口保留历史上下文，不要求逐项补完整图才能开发。导航 Setup 与双臂 3D 已新增 IMG-023/025，其他可用局部参考加规范完成样板；首任务出现实际可用性问题再补图。原附件保持不变，本轮未生成或改绘图片。

## Specification 的迭代时点

开始任务前细化相关页面、功能、契约与验收；实现中发现能力不匹配立即更新对应主责条款并记来源；完成后记录真实结果和与图的差异，再开始下一条任务。不要每次重写整套总册，也不要等子任务全部结束才改规范。

页面、共享组件、后端/契约和证据分别维护。每个任务结束只更新受影响节点、图片映射、决策和测试状态；历史原图与来源不被覆盖为新事实。
