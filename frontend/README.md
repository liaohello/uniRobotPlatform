# uniRobot 3D Workbench · M1.2c Session 准备与显式 Start

恢复前端实现的用户指令已解除本切片的暂停。此应用位于独立 worktree；主写者只写 `frontend/`，backend、公共契约、参考工程和根配置保持只读。现有诊断和草案实现保留。

本轮面向 M1.2c 候选 18944：3D 工作台消费 geometry-2 与版本化运动学；Session 抽屉可创建/列出/读取/保存真实 Draft，运行后端 validate，读取不可变配置快照、逐项检查、阻塞原因和空/失败 Session 状态；在满足后端资格时可显式创建 prepared Session 并独立 Start。真实 native 仍未部署 binding 补丁，所以真实界面准确显示阻塞，成功交互只在隔离的状态协议夹具中验证。

## 现在可以操作

- 实时只读或显式冻结来源的 mobile_pick 场景与 LanderPi 网格，旋转/平移/缩放；相机工具栏提供放大、缩小、适配模型（仅机器人）、恢复全景（机器人 + 可见场景对象，并恢复默认 3/4 俯视方向）、聚焦选中对象。
- 标准视角按车体轴命名：车头 = world_sim +X，车侧 = world_sim −Y，顶视 = world_sim +Z。只移动相机，不旋转模型根节点。
- 对象树、mesh 点击/悬停、Inspector 共用稳定 link ID；双击机械臂部件选整臂。选中不授予控制权。
- 显式 Joint 模式：单关节环或用户角数值/滑条编辑，其他已有目标保留；°/rad 仅改变显示。native 模型 joint4 零位偏移继续保留。
- TCP 模式：world_sim（m、Z-up）轴/平面拖动及数值联动。Ghost 是本地位置 IK 或 FK 候选，Actual 来自所选后端只读流或冻结样本；预览和取消不写 Actual。
- 布局：标准工作台 / 3D 专注预设；导航可收起；层级、Inspector、传感器、时间轴可折叠与恢复；分隔条可拖动；保存/恢复/重置布局不改变渲染器、相机、目标或运行状态。
- 3D 视口可应用内最大化（Dockview 最大化）或进入浏览器全屏（覆盖视口、来源/状态、目标操作与弹层）。全屏被环境拒绝时显示真实原因，应用内最大化仍可用。
- Session 准备抽屉请求真实平台 API：Draft 创建/列表/读取/保存（仅 `name`/`description`）、`validate`、不可变配置快照读取、configuration/readiness 逐项结果、证据来源、`blocking_reasons`、recipe fingerprint，以及 Session 列表中的空/失败/unsupported 状态。
- 合格快照可显式“创建 prepared Session”，之后独立点击“显式 Start”。创建使用 validated snapshot、execution_revision、fingerprint 和幂等键；不因 validate 自动创建，不因创建自动 Start。超时标记结果未知并优先通过 GET 存档回读恢复。
- Session 详情分别展示生命周期（配置合格 / prepared / 可 Start / active）、native binding 身份与状态、授权范围、Owner/lease、recording ready、motion ready/blockers、Start/recording 回执和 attempt。active 不表示取得 Owner、正在录制或允许运动。
- 新鲜度双通道：`GET /sessions` 明确标为“最近平台动作存档”，显式刷新只重读存档；`GET /mobilecar/preflight` 是当前 native 只读观测（`checked_at`），刷新它不会改变 Session 存档或资格。运行身份或 binding 失效会取消旧本地目标/手势并禁用 Start，保留同内容网格、相机和布局。
- 代理新增 `POST /sessions` 与 `POST /sessions/{id}/start`，仍不代理运动、STOP、RESET、recording begin/finalize 或 native 命令。代理白名单不放宽后端资格判定。
- geometry-2 区分内容身份与 run/generation/episode：运行身份变化时取消旧手势和本地目标，保留网格、相机与布局；内容身份变化时明确失效，不沿用旧资产。
- live 运动学来自 `GET /api/v1/mobilecar/kinematics`，并与 execution-recipe 的模型 pin、关节顺序、单位、TCP 父节点/site、相机父节点和一致性结果交叉核对；`orientation=null` 显示“未声明”，不伪造标定姿态。冻结样本保留独立参考 profile，不自动回退。
- 观察用相机、传感器区域与时间/事件区域统一装配。传感器媒体及连续 Episode 不在本单帧样本中，明确显示缺失，不放假视频或轨迹。

空白左键拖动 Orbit，右键平移，滚轮缩放；手柄拖动期间不 Orbit。视口内 F 聚焦、Esc 取消本地目标（全屏中 Esc 交给浏览器，不清目标），文本输入优先。失焦、指针取消或布局尺寸真实变化会结束当前手势并保留最后本地草案；没有在线速度/力输入服务。

## 来源与限制

`public/sample/scene.json` 来自既有 native 服务的只读 SceneManifest；`snapshot.json` 是一次真实运行采样，**不是初始化状态、Episode 回放或实时状态**。23 个 STL 由本地参考资产复制并与 native 清单哈希核对。原生服务的 g4a1 来源不证明平台选定 G1 recipe 的集成已通过。身份、源时钟、模型摘要、捕获方式见 `public/sample/provenance.json`。

TCP 本地 DLS 仅尝试位置约束；没有姿态规划、碰撞检查、动力学验证、服务端 plan_id 或执行许可。不可达目标保留标记并隐藏 Ghost。虚线只作目标辅助线，不是已规划轨迹。Ghost 只显示机械臂，避免把重复底盘误认为实际运动。

默认来源为真实只读监控；可用 `?source=frozen` 显式打开冻结来源。平台写入仅限 Draft 创建/保存/validate；Start、接管、执行、RESET、录制与回放按钮保持禁用，后端已有 Target 和 Owner 仅供观察，不代表本方提交或授权。断连保留最后 Actual 并标陈旧，连续3次失败后暂停自动重试；geometry-2 运行身份变化取消旧手势与本地目标但保留网格/相机/布局，内容身份变化明确失效并重载。只有用户显式选择才切到冻结样本。所有数据读取集中于 `src/adapters/`，端点变更不散落到面板。[后端最小缺口与样例](docs/backend-gaps.md) 是交接建议，公共 wire 契约继续由后端对话维护。

## 代码边界

React/TypeScript 负责外壳、状态及面板；Three.js SceneView 采用参考模块的前端自有副本，并补齐生命周期和交互。没有导入 native main.js、R3F 或浏览器物理。依赖和锁文件仅位于本目录，主智能体为唯一写入者。

源码复用与资产来源见 [provenance](docs/provenance.md)。在原生服务器政策下执行构建、测试与浏览器；本地只读写源码/清单和传输。

## 运行和验证

以下 npm 命令**仅在授权服务器**、Node >=20.19 的独立环境中运行：

```bash
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm test -- --maxWorkers=2
python3 tests/browser-usability.py http://127.0.0.1:18934 /tmp/usability --release <release_id>
python3 tests/browser-config.py http://127.0.0.1:18934 /tmp/config
python3 tests/browser-session.py http://127.0.0.1:18934 /tmp/session
python3 tests/browser-history.py http://127.0.0.1:18947 /tmp/history --mode real        # 真实历史记录：预览上游必须是 episode-read-1 候选（本轮为 18964）
python3 tests/browser-history.py http://127.0.0.1:18947 /tmp/history-synth --mode synthetic # 隔离故障夹具（page.route），不触碰归档
python3 tools/serve-readonly.py --directory dist --port 18947 --upstream http://127.0.0.1:18964
```

预览进程只由 `tools/preview-registry.py` 管理：`free-port` 先报告既未被监听又未被台账占用的端口（只读，不杀任何东西），`check-release.py --preview-registry … --preview-round …` 在启动预览后立刻登记完整身份（pid、端口、release、上游、cmdline、内核 start tick、uid），`verify` 复核，`stop --pid … --round …` 只有在这些身份全部吻合时才终止那一个 pid。**不要用端口正则或进程名批量停止**，端口号本身不构成所有权证明。

`tests/browser-session.py` is an explicitly synthetic, stateful protocol fixture; it does not create a real Session or prove native prepared/Start.

本地可运行 `python3 frontend/tools/release-source.py` 制作文件白名单、哈希和归档；上传后使用服务器 `tools/check-release.py` 核对输入、构建、测试并运行生产构建的 Chromium 检查。禁止用本机测试替代服务器执行。报告绑定同一 release，旧失败迭代不拼成最终通过。具体交付结果另见本方 [开发记录](docs/development.md)。

## 真实来源与平台配置

`PlatformService` 只读 scene / capabilities / snapshot / kinematics / execution-recipe，资产使用 scene 提供的 URI 与 sha256 查询参数，经同源代理读取。默认请求完成后等待1秒，可选择2/5秒；不叠加请求，10秒超时，切源取消迟到结果。普通快照只更新 Actual，不重建renderer、覆盖本地 Target 或重置相机。世界物体只显示编译初态，没有实时物体真值。`PlatformConfigApi` 仅使用同源代理的白名单路径：Draft 创建/列表/读取/保存/validate、配置快照读取、Session 读取。历史 Episode 走独立的 `PlatformEpisodeApi`（episode-read-1 五条精确 GET：列表、详情、流目录、单流 records、assets 字节），只在“历史 Episode”视图内使用：该视图不挂载 3D、不订阅 live 轮询、没有可执行 Target/Ghost，只做单流分页浏览与按界面节奏的播放；跨流同步、历史 3D 回放与任何录制写入仍未接入。

live Joint/TCP 候选使用 `GET /api/v1/mobilecar/kinematics` 的版本化元数据，并要求 execution-recipe 的模型 pin 与 profile digest 匹配；同时检查关节顺序、单位、TCP 父节点/site、相机父节点和 5 项实时一致性。元数据缺失或不匹配时禁用本地候选并显示具体原因，不自动回退。`orientation_xyzw=null` 只表示源未声明姿态。冻结样本使用自身独立参考 profile，并明确标注不是 live 元数据。见 [来源](docs/provenance.md) 和 [最小后端差距](docs/backend-gaps.md)。

## 车体渲染坐标约定

修正版本的实时源接受 `unirobot-mobilecar-geometry-1` 和 `unirobot-mobilecar-geometry-2`（capabilities/snapshot 仍为 read-1），资产声明 `coordinate_space=mujoco_compiled_mesh`、`units=m`、`mesh_preprocessing_applied=true`，并保留原STL摘要/mesh名称及几何 provenance。geometry-2 还必须提供 `content_matches=true`、观测/导出的内容与运行身份一致。顶点使用MuJoCo编译网格，前端只应用既有 geom/body/joint 变换，不再应用 mesh_scale/mesh_pos/mesh_quat；网格SHA对应本次编译STL字节。未声明完整约定的 live scene 明确拒绝，不以原STL猜补偿。

alpha=0 的几何不构造渲染对象；半透明 Actual 启用透明混合且不写不透明深度。判断显隐不使用 collision/group，也不按零件名过滤。基础可见几何保留，未增加碰撞调试层、点云或可达性点层。TCP/Joint手柄、模型/用户角、Actual/Target/Ghost与只读轮询保持原有路径。

旧 `public/sample` 原始资产保留为历史交互夹具，数据源明确标为“冻结旧样板 · 网格坐标未修正”；不作为本轮装配正确的证据。新截图只针对独立几何候选源与明确标识的新前端release。
