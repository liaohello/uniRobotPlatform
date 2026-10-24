# M1.3 3D 视口与布局可用性交付

2026-10-23。保存点 `596c0d7`（真实只读联调 + 车体修正，含 63 个未提交证据文件）之后开始本轮；只写 `frontend/`，未改 backend、公共契约、native 或公共锁文件，未推送。本轮目标是把 3D 工作台做成真正可操作，并在同一外壳准备 Session 界面。下方原车体渲染记录按历史保留。

## 本轮行为

| 能力 | 实现 | 边界 |
|---|---|---|
| 聚焦选中对象 | `focusSelection`：选中 `arm` 时框住整臂，选中 link 时框住该 link；保持视角方向。视口内 `F` 同义 | 只改相机 pivot/距离，不改选中、Target 或控制权 |
| 适配模型 | `fitModel`：只框机器人可见几何（排除 pending、隐藏 geom、地面 plane），保持方向 | 不含场景物件 |
| 恢复全景 | `fitScene`：机器人 + 可见场景对象，并恢复默认 3/4 俯视方向 | 不旋转模型根节点 |
| 应用内最大化 | 锁定版 Dockview 公开 API：`maximizeGroup` / `exitMaximizedGroup` / `hasMaximizedGroup` / `onDidMaximizedGroupChange` | 未升级 Dockview、未重写布局框架 |
| 浏览器全屏 | `main` 元素全屏，覆盖数据源、状态、布局条、视口（含 HUD 与取消目标）、Inspector、传感器、时间轴、状态栏与弹层 | 被环境拒绝时显示 `NotAllowedError` 等真实原因，应用内最大化仍可用，不显示假成功 |
| 相机缩放 | 滚轮/触控板沿用 OrbitControls；工具栏 ＋/− 用相机 dolly，受 `minDistance/maxDistance` 限制 | 不缩放 mesh、不拉伸 Canvas |
| 面板缩放 | 分隔条加可见描边 + `::after` 命中扩展；左右栏、传感器、时间轴可拖动、折叠、恢复 | 折叠/恢复时重新分配垂直空间，不重建视口 |
| 布局预设 | 标准工作台 / 3D 专注（收起传感器与时间轴、收起导航、最大化视口） | 预设切换不改变 Target、Actual 或控制权 |
| 顶部压缩 | 原 runtime 63 + authority 39 + monitor 30 合并为 42px 控制条 + 可展开详情 | 只读、陈旧、Owner、重新加载仍可达 |
| Session 准备 | Draft / 校验 / prepared Session 三段抽屉，读取真实 envelope 标志 | 不出现 Ready；Start/运动/RESET/录制仍禁用 |

## 修掉的实际缺陷

1. `cancelGesture()` 只清 `gizmo.dragging`，不释放 `interacting`，一次失焦即可让工具、布局、数据源全部卡死；现在统一释放并清 `gizmo.axis`。
2. Dockview 布局事件与 `disableDnd` 属性抖动会在拖动中触发取消；`resize()` 现在只在宿主尺寸真变时返回 true，取消只在真实重排时发生，DnD 改为常量关闭。用新增的 gesture trace 定位（`cancel:layout`）。
3. 继承相机位于 pivot 下方，被 `maxPolarAngle` 夹成近乎水平视角；改为显式 3/4 俯视，默认取景框机器人。
4. `fitView` 把 4 m 地面当主体，相机被推到 5.5 m 上限；取景排除 plane。
5. 折叠传感器时 Dockview 把空间给时间轴、视口反而缩小；新增结构化 rebalance，折叠后视口变大、恢复后对称。
6. 布局“重置”用 `key` 重建整个 Dockview，会销毁 renderer 与相机；改为结构化重置，同一 renderer/相机/目标保持不变。
7. 1366×768 下固定条带 270px、视口仅约 140px 高；现在固定条带 150px，视口画布 319px（1920×1080 为 518px）。
8. 125% 页面缩放下 `.application{min-height:640px}` 造成页面溢出、状态栏被裁；已移除，并让短视口默认进入 3D 专注。
9. 分隔条颜色与背景几乎同色；改为可见描边与 hover 高亮。
10. Inspector 单一滚动会把“取消目标/提交执行”滚出屏幕；改为局部滚动 + 固定动作栏 + `<details>` 诊断。
11. 相机“前/侧”与车体方向相反（旧“前”为 world_sim −Y）；按车轴重命名为车头(+X)/车侧(−Y)/顶视(+Z)，只改相机。

## 同一冻结版本的实际验证

release `m1-front-geometry-20261024T041729Z-254ee2318a57`（65 个输入，aggregate `254ee2318a574695643a02fc72e64bf94090da737789de116a6d8e03d588ad64`），全部在服务器 cec-sim 的同一份解包产物上执行：Node 20.20.2 / npm 10.8.2，Chromium ANGLE SwiftShader，代理上游为几何候选 18942。

| 验证 | 结果 |
|---|---|
| 类型检查与生产构建 | `tsc --noEmit && vite build` 通过；保留既有大 chunk 提示 |
| 单元 | 23 passed：含 envelope 能力标志不升级为就绪、声称 ready 的 envelope 被拒绝、编译网格不二次 scale、Joint4 零位 |
| 真实只读 | 30 passed：三接口、23 资产摘要、Actual 持续更新、慢响应不重叠、断连/身份跳变/坏字节夹具 |
| 冻结交互回归 | 29 passed：Joint 环、TCP 轴、数值、取消、焦点、Orbit、布局、切源 |
| 装配/几何 | 23 passed：23 网格装配、TCP 对齐误差、前/侧/顶视图、跨 Actual 刷新的持续拖动 |
| 可用性（新增） | 99 passed：滚轮/按钮缩放、适配/全景/聚焦、分隔条双向拖动、最大化、全屏进入退出、布局预设、面板折叠、布局保存恢复、Esc 全屏、TCP 持续拖动、1366×768 / 1920×1080 / 125% |
| 只读边界 | 全部浏览器请求仅 GET；无运动/RESET/录制端点；native run/generation/episode 前后一致 |

关键数值（同一 release）：1366×768 画布 678×319、固定条带 150px、页面不滚动；1920×1080 画布 1048×518；125%（CSS 1093×614、DPR 1.25）画布 472×170，状态栏仍在视口内；滚轮 0.969→0.782→0.969 m；最大化 618×319→1202×541，同一 renderer、相机与目标；TCP 持续拖动跨 12 次快照、Actual 位移 5.5e-16 m、相机不动、面板尺寸不变。

证据：[源码清单](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/source-manifest.json)、[构建](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/build.log)、[23 项单元](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/unit.json)、[30 项只读](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/browser/browser.json)、[29 项冻结交互](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/frozen-browser/browser.json)、[23 项装配/几何](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/geometry/geometry.json)、[99 项可用性](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/usability/usability.json)、[原生只读前后](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/native-read-only.json)、[preview](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/preview.json)、[release 摘要](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/release.json)。

可用性截图为同一 release：[1366×768](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/usability/usability-1366.png)、[1920×1080](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/usability/usability-1920.png)、[3D 专注](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/usability/usability-focus3d.png)、[125% 缩放](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/usability/usability-125.png)、[Session 准备](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/usability/usability-session.png)。

## 预览与版本

- 候选预览：服务器回环 18935，代理 18942；SSH 隧道提供 http://127.0.0.1:18935/ 。已验证的 18933（`m1-front-geometry-20261023T192903Z-58a156740be8`）与 18931/18932 保持原状，未重启或停止。
- 本轮不进入 prepared Session 的真实 Start/接管/录制；Session 抽屉只呈现后端已返回的 false 标志与阻塞原因。
- 遗留：运动学仍是本地固定参考 profile（按模型摘要匹配），等待后端版本化元数据；媒体与连续 Episode 仍未接入；浏览器全屏在嵌入环境可能被拒绝，此时只有应用内最大化可用；软件渲染下会触发像素比降至 1.0 的自适应提示。

---

# LanderPi 车体渲染修正交付

2026-10-23。本轮按用户要求只修车体几何与材质；现有 TCP 手柄、拖动、数值编辑、取消、Joint、Actual/Target/Ghost 与实时只读监控保留。没有改为Viser、加入点云/可达性层、逐件位移/旋转补偿、移动模型根节点、改关节零位或伪造Actual。下方原只读联调记录按历史保留。

## 前端已修复

- `native-scene-view.js` 的 `_buildGeom` 在构造/拾取前跳过 authored alpha<=0；可见primitive和mesh都保留，不使用collision/group或零件名字删外观。半透明Actual实际启用混合并关闭opaque深度写入；Ghost保持既有蓝色候选样式并乘源alpha。
- 服务适配层消费 `unirobot-mobilecar-geometry-1` / verified compiled geometry scene。compiled STL的scale、居中与主轴预处理已烘焙，前端仅应用既有geom→body→joint→world_sim显示链，不二次scale。新增资产坐标、单位、source身份和geometry_provenance穿过内部类型/适配层；新增contype/conaffinity保留原义。无编译坐标约定的live scene拒绝，不能把旧raw STL组合标为已修正。
- 真实源继续按关节名使用model_joint_positions_rad；joint4用户0→模型−π/2未改。TCP实际标记不依赖本地目标，编译网格不会改变关节链或真实TCP。`geometry_source_changed`作身份失效处理，清旧预览并重载/明确不可用。
- 旧冻结资产与交互夹具保留，显式标为“冻结旧样板 · 网格坐标未修正”；不作为本轮装配证据。23个新compiled STL留在后端服务器，经API加载，未拉回平台模型目录。
- 检查模式只增加只读的geom局部AABB、变换局部AABB得到的world_sim范围、矩阵及TCP误差；这些是可视几何诊断，不是在线接触真值。页面header显示本次release摘要。

## 后端已补齐及仍有边界

用户明确授权与后端对齐后，向“Continue M1.1(后端)”发出坐标契约与原生导出字段修复请求。后端选择编译网格方案，独立提供18942；主智能体只写frontend，未修改backend、公共契约或原生工程。

后端交付记录：[backend-m1-geometry.md](/home/liaozhengyan/.codex/worktrees/backend-m1-read/uniRobotPlatform/docs/backend-m1-geometry.md)。geometry-1的scene、每资产coordinate_space/units/preprocessing/source_sha256/source_mesh_name、新字节SHA/URI、真实group/contype/conaffinity与来源摘要均已补齐；capabilities/snapshot仍为read-1。`chassis_collision`实际group3/contype2/conaffinity1/alpha0，`base_link_visual`仍是可见外观；collision只表示过滤参与。

当前必要几何信息已足够完成本切片。候选绑定本次native运行和静态编译来源，换run/模型/场景后需后端重新生成验证包，不承诺通用热切换；18941保持旧版兼容服务。验证范围为static compilation匹配live manifest，不是读取在线C内存/接触，也不授予执行资格。用户角/TCP本地运动学仍采用已有固定参考profile，版本化元数据和Session/控制/录制/媒体/回放仍按既有缺口保留，未在本轮扩展。

## 当前预览与版本

- 请查看 [http://127.0.0.1:18933/](http://127.0.0.1:18933/)，它代理服务器18942；18931/18932仍是旧预览。新预览PID800217，SSH仅作本地回环转发；页面header摘要为 `58a156740be8`。
- 前端release `m1-front-geometry-20261023T192903Z-58a156740be8`，63个输入；aggregate SHA256 `58a156740be83a2879e5a1d2145f77d552d51f6682b1e3d318d6a2b048044276`。
- 后端候选 `m1-geometry-20261023T192202Z-cdfc7472e5de`（后端提交42cdd6a），geometry bundle `275389464eee2f3de0c2ddf96ae85acbedfd382c496a589ec41a3662ee31d171`。接口 `geometry-1 + read-1`，native profile `g4a1-1.0`。
- 既有native8792/PID941842、read网关18941/PID1155600、几何候选18942/PID397182、旧18931/PID2614787和18932/PID293264均保留。只停止了本方核对PID/argv后的失败18933候选，未触及其他服务。

## 实际验证与截图

全部在服务器 cec-sim 的同一冻结前端release执行，Node20.20.2/npm10.8.2/原锁文件；Chromium ANGLE SwiftShader。没有以GPU性能或真人体验验收作扩张声明。

| 验证 | 实际结果 |
|---|---|
| 输入、类型检查、生产构建 | 63文件上传逐项SHA一致，`tsc --noEmit && vite build`通过；仍保留既有大chunk提示 |
| 单元 | 21 passed：旧FK/IK/零位、只读投影隔离，加alpha0/半透明/基础几何保留、编译网格不二次scale与缺失坐标约定拒绝 |
| 只读浏览器 | 30 checks passed；三接口、23网格新摘要、身份/断连/迟到/坏资产夹具及相机/目标稳定 |
| 旧交互回归 | 29 checks passed；TCP/Joint手柄、数值、取消、焦点/失焦、选择、Orbit、布局与源切换 |
| 新装配与TCP | 23 checks passed；Ghost关闭、无本地目标、所有可见geom保留、不可见碰撞不构造；四轮前后/左右分离、薄轴沿Y、支撑高度一致、底盘水平、两壳体/臂基座/两夹爪完整；TCP拖拽跨两次Actual刷新不丢目标或相机 |
| 几何数值 | 四轮中心与AABB、底盘范围/可见网格矩阵存于geometry.json；最终渲染关节链到真实TCP标记误差 `1.694362330178007e-14 m`；未改Actual或机器人模型来满足断言 |
| 三视图人工复核 | 主智能体查看了本版前/侧/斜视截图，车体水平、轮组及壳体装配完整，机械臂/夹爪与既有TCP链一致。截图Ghost关闭、无Target，并关闭场景物体层防止方块遮挡；grid仍为观察辅助 |
| 原生与网络 | 所有浏览器与代理API记录仅GET；native运行/Episode/recording与PID前后相同，无运动/RESET/录制，无新物理实例 |
| 回传 | 约1.40MB，25个证据文件按索引核对SHA，原始大网格留服务器；63个运行输入在交付前再次核对一致。本页/报告排除自引用hash |

沿用既有观察相机按钮的命名：UI“前”为Three +Z，即world_sim −Y（车侧）；UI“侧”为Three +X，即world_sim +X（车头）；斜视为原全景相机方向。没有为截图改根节点或旋转机器人。前、侧使用相同相机距离/观察中心，具体相机与tick记录在geometry.json。以机器人方向命名的截图：

- [车头视图（world_sim +X）](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/geometry/side-viewport.png)
- [侧视图（world_sim −Y）](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/geometry/front-viewport.png)
- [斜视图](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/geometry/oblique-viewport.png)
- [TCP本地预览](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/geometry/tcp-local-preview.png)

证据：[源码清单](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/source-manifest.json)、[21项单元](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/unit.json)、[30项只读](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/browser/browser.json)、[29项交互](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/frozen-browser/browser.json)、[23项装配/几何/交互](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/geometry/geometry.json)、[真实geometry scene](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/geometry/scene.json)、[进程/身份/网络摘要](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/integration-summary.json)、[完整产物索引](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/server-artifact-index.json)。

首轮同代码候选已通过装配15项与两组既有浏览器回归，后续测试将已显示的0再次fill为0而未触发React change，导致错误地等待一个未创建Target；修正为先编辑1再回0，完整冻结新版本重跑，未拼接旧候选结果。只读子代理关于Ghost transparent的担心经主智能体核对：Ghost材质构造时已保证transparent=true；实际补齐的是后续蓝色样式opacity继续乘源alpha。所有子代理只读，未运行验证或修改。

本轮切片可检查；未声明真实M1控制、录制或回放闭环通过。前端新改动/报告留在本方worktree，未提交或推送，原M1.2a保存提交e73624e及上一轮成果均保留。

---

# 第一轮真实只读联调交付记录

2026-10-23。最新记录优先；下方原 M1.2a 样板记录作为历史证据保留。前端恢复、只读接入及服务器验证均由用户明确授权，本轮已完成可检查切片，**不代表真实 M1 控制/录制/回放闭环通过**。

## 保存与修改边界

- 先将原 M1.2a 与验证证据保存为本地提交 `e73624e`；共同基线仍为 `2f7ff9b091c060034e55d2f387dbb6e130aaada3`，当前分支 `codex/m12a-workbench`。
- 本方 worktree `/home/liaozhengyan/.codex/worktrees/frontend-m12a/uniRobotPlatform`；本轮仅修改 `frontend/`，未改 backend、公共契约、native、根配置或公共锁文件，未推送。新实现与报告保留在本方工作树中，未自动提交第二次。
- 三路子任务只读核查最新 Schema、Actual 刷新/renderer 边界、故障验证要求，主智能体整合、修改与实际执行验证。子任务指出的 gripper Actual/Target 模型角映射遗漏已由主智能体补齐。

## 当前可操作内容与数据来源

默认进入 **真实只读监控**：从平台 scene/capabilities 初始化，持续读取 snapshot；23个真实 STL 使用本次 scene URI，经同源代理携带 sha256 查询参数获取，在解析前核对字节摘要。普通快照复用同一场景/renderer，不重置相机、选择、Dockview 布局或本地目标。

Actual 是后端实时反馈，按 `model_joint_positions_rad` 原生关节名渲染。用户角和模型角分别保留；joint4 用户零位约0、模型零位约 −π/2。后端已有 Target 独立只读显示（关节、底盘、夹爪）；`command_id=null/tcp=null` 没有被转成成功回执。本地 Joint 环/数值/滑条、TCP 手柄/数值、Ghost 和取消继续可用，不写 Actual，也不发控制请求。

本地候选使用已固定参考运动学 profile；元数据来源与匹配限制见 [provenance](provenance.md)。根 XML 摘要匹配不证明远端全部配置一致。未知模型不猜测用户角映射，禁用本地候选但保留只读 Actual；后端尚缺版本化映射/TCP安装元数据，最小建议见 [backend-gaps](backend-gaps.md)。本地 IK 只约束位置，未作姿态/碰撞/动力学/后端计划认证。

world_links 只标为编译初态，不是物体实时位姿。真实源的 Actual 使用显式字段投影，diagnostics/GT/Oracle 不从冻结来源合并。RGB/Depth 只显示缺少媒体，native SensorState 引用不用于下载图像。时间区域显示源 sim/feedback/tick 与本地接收年龄；没有伪造连续 Episode 或录制轨迹。

Session/Start、停止、接管、执行、录制、播放仍禁用；观察到的 Owner 不授权本方。`?source=frozen` 或数据源菜单可显式打开冻结样本；不自动回退，不把它称为历史 Episode 回放。没有新增模拟成功路径。

## 轮询、失效与代理

先在服务器测得 snapshot 约48–88ms，默认请求完成后再等1秒；可选择2/5秒。没有 setInterval 并发请求，10秒超时；切源/卸载取消请求，异步迟到结果被拒绝。连续3次失败后暂停自动重试并保留明确错误，用户可重新加载。

跨 scene/capabilities/snapshot 比较 adapter、robot、run/generation/episode、contract/model/hash/scene、interface profile。运行或资源身份变化立即作废旧 Target/Preview 并重载；初始化身份不一致不挂载混合场景。断连保留最后 Actual 并明确标陈旧；资产错误标不可用，可重新加载来源，不以冻结数据或旧网格补成功。

同源静态预览代理只允许四组 GET 路径；其他 API 不代理，写方法不转发。响应状态、ETag、no-store 与完整查询参数保留。没有访问 native 控制路径。

## 本次冻结版本与实际验证

- 前端 release：`m1-front-read-20261023T180841Z-25c387722858`；61个输入；聚合 SHA256 `25c387722858c7414ec4f539a26e88b457042d8ae798691565b4cef7548392af`。
- 对接网关：`m1-read-20261023T155543Z-cef9ddedf781`，wire `unirobot-mobilecar-read-1`；当前 native interface `g4a1-1.0`。
- native release：`drvfix-20261019T044549Z-0a80415b2577`。运行 `run_9c88e3e36e7648a3852c9f590e43ed5f` / generation 1 / `episode_43c22f95536f4517be04e4b195d6d354`；模型/场景身份见 [只读浏览器报告](../reports/m1-front-read-20261023T180841Z-25c387722858/browser/browser.json)。这不是更新 native pin 或完整部署内容核验。

| 实际执行，全部在服务器 cec-sim | 结果与证据 |
|---|---|
| 上传逐文件哈希、TypeScript 与生产构建 | 通过；[输入清单](../reports/m1-front-read-20261023T180841Z-25c387722858/source-manifest.json)、[构建日志](../reports/m1-front-read-20261023T180841Z-25c387722858/build.log)。保留 bundle 大于500KB的 Vite 提示，本轮未为此扩大拆包 |
| 单元检查 | 13 passed / 0 failed；含 Actual/Target 分离、关节零位、身份隔离、URI摘要边界与原FK/IK；[结果](../reports/m1-front-read-20261023T180841Z-25c387722858/unit.json) |
| 真实代理与只读浏览器 | 30 checks passed；三接口200，23/23资产字节摘要匹配，错误sha查询保留409；持续更新不重建renderer、不覆盖相机/选择/布局/目标；[结果](../reports/m1-front-read-20261023T180841Z-25c387722858/browser/browser.json) |
| 原 M1.2a 交互回归 | 29 checks passed；Joint/TCP拖拽、Actual隔离、输入焦点、失焦、单位、拾取、布局重建/恢复、取消与切源；[结果](../reports/m1-front-read-20261023T180841Z-25c387722858/frozen-browser/browser.json) |
| 故障夹具 | 1.5秒慢响应无重叠；503断连、运行/资源跳变、组间身份不一致、切源迟到、坏字节与502摘要错误均通过；全部合成响应，未 RESET/修改 native 制造故障 |
| 取景与持续拖拽补查 | 同一生产构建上6项通过；自动取景稳定后所有robot link中心在视口内；TCP手柄持续拖拽跨越两次Actual刷新，目标/相机/拖拽状态稳定；[补充输入脚本与结果](../reports/m1-front-read-20261023T180841Z-25c387722858/final-preview-check.json)。脚本作为独立验证输入以自身SHA记录，未修改61个构建输入 |
| 网络与原生影响 | 代理记录254次API读取均GET且在白名单；26个真实snapshot代理耗时中位31.905ms，22.25–233.21ms；[摘要](../reports/m1-front-read-20261023T180841Z-25c387722858/integration-summary.json)、[网络记录](../reports/m1-front-read-20261023T180841Z-25c387722858/proxy-network.json)。无运动/RESET/录制请求，无新增物理实例；[前后状态](../reports/m1-front-read-20261023T180841Z-25c387722858/native-read-only.json)、[补查后PID/状态](../reports/m1-front-read-20261023T180841Z-25c387722858/final-preview-check.json) |
| 环境与回传 | Node20.20.2/npm10.8.2、原锁文件、Chromium ANGLE SwiftShader；不外推真人操作手感或GPU性能。[环境](../reports/m1-front-read-20261023T180841Z-25c387722858/environment.json)、[产物索引](../reports/m1-front-read-20261023T180841Z-25c387722858/server-artifact-index.json)。约1.23MB精简包回传并核对22个文件，原始大数据/资产未回拉 |

较早候选不拼接为本次通过：首轮仅遇到测试JSON的TS tuple断言错误；第二轮浏览器24项后暴露测试在React切源完成前读取旧inspect hook，已修正等待。最终上述主检查均在同一冻结版本完整通过。末张快速截图曾早于自动fit timer结束，另以独立补查确认稳定取景与持续拖拽，并保存稳定后的预览；没有为截图改 Actual/场景或冒充真实控制。

## 预览与保留服务

- 联调预览：服务器 loopback18932，PID293264；当前SSH隧道提供 [http://127.0.0.1:18932/](http://127.0.0.1:18932/)。源目录与启动时间见 [preview.json](../reports/m1-front-read-20261023T180841Z-25c387722858/preview.json)。仅任务预览，随服务器进程/隧道存活。
- 旧样板18931/PID2614787、网关18941/PID1155600、native8792/PID941842 均保留，前后PID一致；只替换过本方明确验证身份的18932失败候选。未重启/停止其他任务服务。
- 后续最小差距仍为运行绑定/Start、控制权与命令回执、录制/可靠收尾、媒体与只读Episode reader，以及版本化运动学元数据。本轮不继续进入这些功能。

![服务器生产构建：真实只读Actual，编译初态世界对象，未授权](../reports/m1-front-read-20261023T180841Z-25c387722858/browser/settled-real-readonly.png)

---

# M1.2a 前端开发记录

日期：2026-10-23（America/Los_Angeles）。当前用户明确授权恢复前端，从 V0.7 M1.2a 开始；不修改 backend、native 或公共契约。此页是验证后的开发记录，刻意不纳入自身 release 哈希，避免报告自引用；运行源码与测试仍全部纳入 allowlist。

## 基线与文件所有权

- 原工作目录：`/home/liaozhengyan/Desktop/uniRobotPlatform`，main HEAD `1b17d6c1f7cccb171d5db8720a0e6f8ffd960623` 的现有未提交/未跟踪成果原地保留，未 reset/clean，也未改变原 index。
- 使用临时 Git index 固定包含最新 V0.7 文档、既有 M1.1/M1.2 代码/证据的共同基线 `2f7ff9b091c060034e55d2f387dbb6e130aaada3`（本地 `codex/m12a-common-baseline-20261023`），不是从旧 HEAD 直接开始。
- 独立 managed worktree：`/home/liaozhengyan/.codex/worktrees/frontend-m12a/uniRobotPlatform`；分支 `codex/m12a-workbench`。后端和公共契约在此相对共同基线没有修改，原主目录的并行修改不被覆盖。
- 本切片仅写 `frontend/`，包括独立 package.json/package-lock、工具、源资产与开发报告。没有改根配置或部署配置，没有推送。

## 实现与数据来源

详见 README 与 provenance。冻结真实几何/运行采样用于观察，Target/Ghost/FK/位置 IK 是前端本地预览。没有真实 Session、执行授权、指令提交、录制或连续 Episode 回放。

三路只读任务已回收：SceneView/资产/坐标与生命周期、交互条款、前后端数据缺口。原交互代理一次执行失败，由新只读代理接管完成；没有把失败任务算作完成。追加静态复核发现的场景替换 marker/失败记录清理与数据源 targetRef 清理已由主智能体处理。子代理没有修改文件或运行验证。

## 同一冻结版本的最终验证

最终 release：`m12a-20261023T162150Z-bf82d5697880`；56个输入文件逐项核对，aggregate SHA-256：`bf82d5697880125086002666d74046a2a103a96f868b9abee54bf2bf8b534102`。当前运行源码/测试/锁文件与该清单一致。本页与 reports 是验证后记录，排除在自引用哈希之外。

| 实际执行（全部在服务器） | 结果与边界 |
|---|---|
| 类型检查与生产构建 | `npm run build`（含 `tsc --noEmit`）通过；Node20.20.2，依赖锁摘要见 environment.json |
| 目标/FK/位置 IK 聚焦测试 | 6 passed：真实关节链 FK 与冻结 TCP 相符、单关节目标保留、joint4 零位、限位/非有限输入、本地位置候选、不可达反馈 |
| 生产构建的 Chromium 检查 | 29 checks passed；对象树/mesh/Inspector、Joint 环真实指针拖动、TCP 轴真实指针拖动与相机隔离、Actual 不变、文本焦点/取消、失焦事件、resize、布局重建/恢复、显式切源、零 native 命令请求 |
| 来源/执行隔离 | 冻结样本不授予 Session；Start/执行/接管/录制禁用；浏览器101项请求均 GET，没有 native 命令/runtime 请求 |
| 原生影响 | 验证前后 run/generation/Episode/recording 身份相同。没有新建物理实例或停止既有服务；只结束了本任务旧版静态预览进程 |
| 源码/证据回传 | 当前源码清单、12个精简证据文件哈希核对通过；回传包约0.7MB，原始数据与环境留在服务器 |

证据：[索引](../reports/m12a-20261023T162150Z-bf82d5697880/server-artifact-index.json)、[源码清单](../reports/m12a-20261023T162150Z-bf82d5697880/source-manifest.json)、[构建](../reports/m12a-20261023T162150Z-bf82d5697880/build.log)、[6项测试](../reports/m12a-20261023T162150Z-bf82d5697880/unit.json)、[29项浏览器检查](../reports/m12a-20261023T162150Z-bf82d5697880/browser/browser.json)、[原生前后](../reports/m12a-20261023T162150Z-bf82d5697880/native-read-only.json)、[环境](../reports/m12a-20261023T162150Z-bf82d5697880/environment.json)。

这些是 M1.2a 离线工作台交互与工程验证，对应既有交互 TEST 的适用子集；不将 TEST-MOBILE-001/002、真实权限/命令/采集/回放或完整交互条款标为已通过。

## 可操作预览与限制

- 最终静态预览：服务器回环端口18931，当前 SSH tunnel 转发为 `http://127.0.0.1:18931`。进程 PID/目录见 [preview.json](../reports/m12a-20261023T162150Z-bf82d5697880/preview.json)。预览随本任务服务器进程与隧道存活；没有对外发布。Codex 面板已请求打开该地址。
- 真实网格与运行单帧为冻结来源，位置 Target / Ghost 为本地计算；本样本含原生 GT_DEBUG 工程观察数据，不作为受限采集的 OperatorView/Policy 输入。后续真实接入的载荷权限应由服务端按 Profile 裁决。
- RGB/Depth 无媒体，时间轴没有连续 Episode；实时状态、真实授权/执行、录制和历史同步流尚待接通。本地 IK 只满足位置约束，没有姿态/碰撞/动力学/规划认证。
- 浏览器实际 GL renderer 为 ANGLE/SwiftShader 软件渲染，验证了1600×1000及1280×900桌面布局；没有宣称客户端GPU帧率或远程实时链路延迟达标。默认关闭实时阴影避免软件渲染负载和阴影伪影；真实几何/状态未更改。
- 生产 JS 约1.2MB（gzip约312KB），构建有大 chunk 提示；本切片没有为消除提示额外拆架构。手机布局未验收。
- 中间迭代保留在服务器，不拼接结果：首轮 TCP 测试坐标未命中手柄；新增 Joint 检查时修正了对 Three.js 旋转手柄几何类型的测试投影；新增失焦拖动后修正测试误用旧 revision 的断言。最终29项均在上述同一冻结版本重跑通过。

![服务器生产构建下的 TCP 本地目标预览，非真实执行](../reports/m12a-20261023T162150Z-bf82d5697880/browser/workbench-tcp-target.png)

## 后端接续

[最小数据/服务缺口与具体样例](backend-gaps.md)。平台只读 scene/Actual 可先接入，不等待控制/录制全部齐备；端点映射仍集中在 adapters，wire 契约由后端对话维护。M1.2b～M1.6 不因本前端样板而完成。
