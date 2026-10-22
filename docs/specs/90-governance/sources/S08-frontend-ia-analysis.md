# Embodied 3D Workbench — Frontend Information Architecture V0.1

你这次列出的内容，已经足够让我们正式开始设计整个前端的信息架构（Information Architecture，简称 IA）。

我认为你对 Scene Setup 的构想尤其重要：你不希望只加载一个 MuJoCo 场景，而是希望针对不同科研实验，快速布置环境、设置机器人初始条件，然后进入统一的仿真工作台开展测试。

我建议现在先确定三个层次：

1. 全局信息架构：整个软件有哪些功能区域，如何进入和切换。
2. 任务场景配置：LanderPi 导航、视觉感知、IK、SO101 双臂分别需要哪些参数与场景编辑工具。
3. 工作区布局和交互：进入某项实验后，3D 画面、相机、传感器、控制面板、时间轴怎样排列和运作。

这三层不应该混在一起讨论。

## 一、Frontend Information Architecture 究竟是什么？

信息架构不是前端技术架构，也不只是把按钮摆到屏幕上。

它首先回答：

用户需要在软件中找到什么信息、使用什么功能、从哪里进入、如何从一个工作流程切换到另一个流程。

例如，在你的项目里：

- 用户从哪里选择 LanderPi 或 SO101？
- 在哪里布置目标方块和障碍物？
- 场景布置完成后，如何开始仿真？
- 正在执行 VLA 时，在哪里申请人工接管？
- Episode 录制结束后，如何找到刚才那条轨迹？
- 从回放中发现失败片段，如何找到对应的训练数据或模型？
- 从训练页面选择 Checkpoint 后，如何回到仿真页面执行预测？

这些就是 IA 必须解决的问题。

它产生的主要成果是页面地图（Sitemap）、导航结构、用户流程、各工作区职责和页面间状态规则。至于 React 组件如何通信，属于后续前端技术架构。

## 二、六个业务区是否就是之前定义的六个？

是的。你理解正确。

但我现在建议把它们看作六个逻辑工作区，不一定在顶部放六个等大的导航按钮。

Embodied AI Research Platform

项目 / 机器人 / 实验任务 / 历史记录

Prepare

01 Scene Setup

场景布置、任务配置

Run

02 Simulation

在线仿真、遥操作、接管

Data

03 Replay & Annotation

单条轨迹回放、阶段标注

04 Dataset Management

数据集合、筛选、导出

Models & Experiments

05 Model Training

训练、曲线、Checkpoint

06 Evaluation

模型测试和实验比较

这样做的好处是：用户首先看到的是四个清晰的工作阶段，而不是六个彼此孤立的页面。

对于你的 V1，我建议采用下面这个优先级：

| 工作区                 | V1 设计范围                |
| ------------------- | ---------------------- |
| Scene Setup         | 详细设计、优先开发              |
| Simulation          | 详细设计、优先开发              |
| Replay & Annotation | 详细设计、优先开发              |
| Dataset Management  | 设计基本流程，可以与 Replay 共享页面 |
| Model Training      | 先设计入口、数据关系和概念界面        |
| Evaluation          | 先设计基本评估结果，批量并行留到后续     |

最重要的原则：工作区负责用户操作流程，任务模板负责不同科研实验的差异。

比如，不应该为四种视觉识别实验分别开发四套完全不同的 Scene Setup 页面。

# 三、Scene Setup 应该怎样组织你列出的实验？

我认为 Scene Setup 应该采用：

选择任务类型 → 选择场景模板 → 配置对象和机器人 → 配置算法与实验条件 → 检查 → 进入 Simulation。

而不是把所有导航、视觉识别、IK、抓取和双臂配置堆在一张表单里。

## 3.1 建议建立任务模板（Task Template）体系

### Scene Setup · 任务模板选择

[Project 1 - Odometry Mapping and ICP - Yiyan’s Homepage](https://images.openai.com/static-rsc-4/T2fZiH_Ky7jka8CnU4lMKkddzcPusl-l-Sh9PNjHV0iQ2yoLtxYDvJmXezgw3QOaQyNbgwEqnMeeWVxOxJgVyOyh8QVY6RcLGWXzniHq84BsjdjCY1ITopyPV3hLCG3S8190DuMYU9a_3PLVlyr2ZyrDYF7uwRRTTFVDVOyzlxI?purpose=inline)

LanderPi Navigation

位置导航、预设轨迹、语义目标导航

[How to generate "photoreal synthetic data" from Omniverse environments with Cosmos? - #2 by andras4 - Synthetic Data Generation (SDG) - NVIDIA Developer Forums](https://images.openai.com/static-rsc-4/DeaxCE7Wa1GmMz1XkSFlEQ1pl3OSR2xNYIDrhYU_LQNidjaKLpCQT9WFRpCyW03V6jdDLt-ITWo_57XAoH7M9e7k1TY9tAeQROhyv8yaanWmRHVmHRTL80iROqsVG0hw6Dk_DK-rVGgLga25cqG7OdvIDbCe7fGORz-e1NUQfko?purpose=inline)

LanderPi Perception

远距离、中距离、近场相对定位、视觉伺服

[compas_fab - Introduction to the Reachability Map](https://images.openai.com/static-rsc-4/5syXneGJ40fWRRT6d3DjBdO5Lby-ESnd47t8ujeE_tg6emns-sulmBn9HD2saT8HsfYql7cpgnck-fASyr7mY4VU9VbQlY1f0xq11TXuWVf7hS7wCtZbE144lynLfjJ2CfPBxdickE_rBY4yP58kRWC4l8Vi_r5Pwv2-R4QwMoo?purpose=inline)

LanderPi IK & Grasp

固定底盘 IK、底盘辅助调整、近场抓取

[Demo Scripts — ManiSkill 3.0.0b22 documentation](https://images.openai.com/static-rsc-4/mVGe0HQ26WWS94pyf1n4fc17NmG4RlMlMoEf18nLKputvCzRB4ZrvJNJccSFy6n36W12wHtTj9RdWwaH53-PkOZC3LRyPjpcBrSCOi54C7AoC6wkZtqccNTTYO9Q-W94aDO8QgqsvfKAzA3szEzXDUyvk5o60b_JVF4MKegEkY8?purpose=inline)

SO101 Bimanual

方块布局、双臂传递、协同操作

图片仅用于帮助你构思 PPT 的任务卡片；实际任务模型和环境仍以现有 MuJoCo 工程为准。

建议明确区分下面四个对象：

| 概念                       | 含义          | 示例                             |
| ------------------------ | ----------- | ------------------------------ |
| Scene                    | 物理环境与场景资产   | 桌子、障碍物、地面、物体                   |
| Robot Configuration      | 使用哪个机器人及传感器 | LanderPi、SO101、Aurora 930      |
| Task Template            | 实验要完成什么     | Object Navigation、Visual Servo |
| Experiment Configuration | 本次实验怎样运行    | 初始位置、随机种子、算法、控制来源、成功条件         |

同一个 Scene 可以用于多个 Task Template。

例如同一张桌子上摆放不同物体，既可以验证目标检测，也可以验证 IK、视觉伺服和最终抓取。

这样你不需要为每项算法重复创建场景。

## 3.2 LanderPi Navigation：三个导航子任务

你描述的三种导航任务应该保留，但最好区分目标的来源。

| 导航任务                         | Scene Setup 要设置什么 | 算法需要做什么       |
| ---------------------------- | ----------------- | ------------- |
| PointGoal Navigation         | 已知目标位置、初始位姿、地图    | 规划并到达目标点      |
| Route Following              | 选择预设轨迹或路径文件、初始位姿  | 沿参考路线跟踪       |
| Object / Semantic Navigation | 指定目标物体或语义类别、环境分布  | 搜索、识别、定位并导航接近 |

例如第三种：

用户选择目标为“红色方块”，但不直接把目标真实坐标输入导航策略。算法需要依据其允许使用的观测发现目标。

这与第一种 PointGoal 的问题定义不同。

你之前已经明确不希望 V1 开发鼠标在地图上编辑 Waypoint 的工具。因此，Route Following 可以在 Scene Setup 中选择一个已有轨迹文件，而不是开发完整的路径编辑器。

这套任务配置思路在 [Habitat-Lab](https://github.com/facebookresearch/habitat-lab?utm_source=chatgpt.com) 中有成熟参考。Habitat 明确区分 Point Navigation、Object Navigation、Image Navigation 等任务，并将场景、起点、目标和评价指标组织为 Episode 配置。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



## 3.3 LanderPi Perception：你的四种视觉实验

我建议将你描述的四种视觉识别能力设计为同一个工作区下的四种实验预设。

| 实验预设            | 主要观察量                   | 用户可以调整什么      |
| --------------- | ----------------------- | ------------- |
| P1：远距离方位识别      | RGB 中的目标类别、检测框、方位角或方向区间 | 目标位置、朝向、遮挡、背景 |
| P2：中距离 RGB-D 定位 | 相机坐标系下的目标 3D 位置及误差      | 目标距离、姿态、物体大小  |
| P3：近场相对位姿识别     | 目标与 TCP 的相对位置/姿态        | 小物体位置、相机观察姿态  |
| P4：视觉伺服跟踪       | 图像误差、控制输出、目标是否保持在视场内    | 在运行时扰动目标物体位置  |

有一个重要技术区别：

超过可靠深度测量范围后，RGB 检测通常仍可以提供图像位置、视线方向或大致方位，但不能仅凭单幅 RGB 图像就声称获得了精确的 3D 距离。

因此远距离实验主要检查方向估计；中距离实验才强调 RGB-D 三维坐标精度。

你的 P4 则是闭环控制实验。

例如把目标小方块从位置 A 移动到 B，算法重新检测目标，视觉伺服更新控制指令，使目标尽可能回到图像中心。

我建议 Scene Setup 负责设置初始物体分布与扰动规则，Simulation 负责实时拖动物体、运行视觉伺服并查看结果。

这样不会把正在运行的控制实验错误放进场景编辑阶段。

## 3.4 LanderPi IK：两种实验应该分开

你提出的两个场景有不同的控制问题：

IK-A：固定底盘末端控制

给定底盘初始位姿，用户在机械臂可达工作空间内设置 TCP 目标，系统计算 IK、显示候选运动和执行结果。

IK-B：底盘辅助的移动操作

当 TCP 目标超出当前机械臂可达范围时，系统先求解合适的底盘位姿，再由机械臂完成末端目标。

第二类不仅是机械臂 IK，还需要底盘可达性、环境障碍物、停靠姿态和后续手臂可达性共同约束。

建议显示机械臂工作空间和底盘候选位置；所谓“整个可执行圈”，更准确地说是满足导航和机械臂操作约束的候选底盘区域，它不一定是一个规则圆形。

在 Scene Setup 中只配置目标和初始条件；具体 TCP 拖动、轨迹虚线、IK 实时执行应该属于 Simulation。

## 3.5 SO101：二维摆放和三维摆放可以同时保留

你的想法很好：对于桌面小方块，直接使用二维俯视图布置，经常比在三维空间里反复调整更高效。

### SO101 Scene Setup — 顶视图布置概念

添加方块移除最后方块

示意图展示台面、双臂基座、参考覆盖范围和方块；并非实际工作空间计算，也不是可拖动的真实场景编辑器。

Scene Setup 可以提供两个标签：

2D Top View：调整方块数量、颜色、XY 位置、间距，适合快速配置桌面实验。

3D Scene View：检查高度、遮挡、碰撞、物体姿态、双臂与相机的实际空间关系。

对于 V1，可以先限制方块位于已知桌面高度，避免做通用任意三维物体编辑器。

双臂的两个工作空间建议通过真实 FK/IK 或采样计算生成，而不是只画两个固定圆圈。

# 四、Simulation 在线工作台：我建议你这样画 PPT

这是你接下来最值得做的设计工作。

我建议不要急着追求漂亮的页面，而是先确定：

在不同科研任务中，用户最需要看什么、最常操作什么、哪些信息必须始终可见。

## 4.1 在线工作台的页面要素集合

可以先分成八个区域。

| 编号 | 区域名称              | 包含的要素                    | 优先级  |
| -- | ----------------- | ------------------------ | ---- |
| A  | Global Header     | 机器人、场景、任务、连接状态           | 必须   |
| B  | Runtime Toolbar   | 启动、暂停、继续、重置、停止、录制        | 必须   |
| C  | Control Authority | Human、Expert、Policy、接管状态 | 必须   |
| D  | Scene Hierarchy   | 机器人、关节、传感器、物体、图层         | 必须   |
| E  | Main Viewport     | 3D 机器人、地图或主要实验画面         | 必须   |
| F  | Inspector         | 当前选择对象的状态、目标和控制信息        | 必须   |
| G  | Sensor Panels     | RGB、Depth、LiDAR、相机、点云等   | 按任务  |
| H  | Live Timeline     | 关键事件、阶段、控制来源、录制状态        | 按需展开 |

### 这是我推荐你先画的第一张 Simulation PPT

A · Project / Robot / Task

Connection

B · Simulation Controls

C · Control Authority

Policy / Expert / Human

D · Hierarchy

World

　Robot

　　Base

　　Arm

　　Sensors

　Objects

Layers / Visibility

E · Main 3D Viewport

Robot · TCP · Gizmo · Paths

Select · Joint · TCP · Force

F · Inspector

Selected: Left Arm

Joint State

Actual / Target TCP

IK Status

Controller

Command Feedback

G1 · RGB

G2 · Depth

G3 · Metrics / Map

H · Live Timeline

00:12.40

Recording · Task Phases · Interventions

这里展示的是结构，不是最终尺寸比例。PPT 中你可以直接使用 A–H 编号，标记哪些区域需要调整。

### 三种任务应该有不同的默认布局

[Autonomous Navigation — ros-docs  documentation](https://images.openai.com/static-rsc-4/700edu3qnvsa5iGy0vcH4WC7PuMeGDY8cGshqZj9-dR5pnNCdet9LMMUIQMKcdAQqA1x9LeOdup4O7UY_IcVlusuEqO4XqIU8d0Ne8sJ_fNYDegj_fepfRrW6f8qDyf54fxN9d1olpkTHSVEomdNL7miRBwmzAFAKkX90mUMnOI?purpose=inline)

LanderPi 导航布局

中央以 3D 场景或 2D 地图为主；侧边展示 LiDAR、定位估计、规划路径和导航状态。键盘驾驶与控制来源需要明显可见。

[Visualizing Multi-Modal Data | asMagiClaw | AncoraSpring Docs](https://images.openai.com/static-rsc-4/1EAeongsIItwHdVcpfublpfgesANwf1Vp3cyE4XuVV7NJRaWHMNNQsESGyMQUQ60nZ-P673xLWogn8vqHdv_PnbrphBFkkvmFpGNvS9U_I9O2WJJLnm4CnPBwJTI60UiWQ3fioKUo6lFFruP6n-GT-TUgJ8GaIuYWMvspGZOG8Q?purpose=inline)

LanderPi 近场布局

中央 3D 机械臂，RGB-D 作为重要辅助画面；Inspector 展示 TCP、关节状态、IK 反馈与轨迹，必要时展开点云。

[How I Trained Action Chunking Transformer (ACT) on SO-101: My Journey, Gotchas, and Lessons](https://images.openai.com/static-rsc-4/nDc5feSfrdhG3JIW-58IXWoXleJI0V-jW5X4jZABThAx1UB9YQH6odQx7Vr4VfHnMHiaAq2EVW8MiZPLNC8eTPWoNtA39MOl_eKVAeIWE7A_5lxFqBM3YkkQiAHxbNTbVnyTtIhrxo1KBko-KcvnGwrZS5vAkbEeiz2Ew7rK59Q?purpose=inline)

SO101 双臂布局

中央双臂 3D 画面，中央相机、左右腕相机作为三路辅助视图；两侧关节与主从误差分组显示。

这三个布局预设应该共享一个工作台，但不应强制使用相同的面板数量或尺寸。

我建议你先画 4 张 PPT：一个通用 Simulation 布局，再加上上述三种任务的专用布局。

# 五、统一 3D 工具与轨迹显示具体指什么？

它不是一个新的业务页面，而是被 Scene Setup、Simulation 和 Replay 复用的底层交互与可视化能力。

可以理解成一个统一的 3D Viewport Toolkit。

| 工具组                  | 核心要素                                | 典型用途              |
| -------------------- | ----------------------------------- | ----------------- |
| Camera Tools         | Orbit、Pan、Zoom、Focus、视角预设           | 观察场景              |
| Selection Tools      | Hover、Click、Double Click、Box Select | 选择 Link、Joint、Arm |
| Transform Tools      | XYZ 平移、旋转 Gizmo、坐标输入                | 场景布置              |
| Robot Tools          | Joint Ring、TCP Gizmo、夹爪控制           | 机器人操作             |
| Visualization Layers | 坐标系、接触点、碰撞几何、工作空间                   | 科研分析              |
| Trajectory Layers    | 目标路径、规划路径、实际路径、Ghost Robot          | 运动分析              |
| Physics Tools        | Alt + Drag 外力、受力方向与大小               | 干预测试              |

你之前确定的选择逻辑仍然有效：

框选同一条机械臂的多个不同 Link，自动提升为整臂选择；默认单臂互斥，Ctrl 追加多臂选择；选中并不自动获取控制权。

### TCP 虚线轨迹应该在哪些地方使用？

在 Simulation 中，当用户设置目标 TCP 并且后端得到候选轨迹 \\(q(t)\\) 后，通过 FK 计算各关节中心及 TCP 随时间的空间轨迹。

可以显示：

- TCP 候选路径：虚线。
- 各关节中心的候选路径：按需显示细虚线。
- 候选姿态：半透明 Ghost Robot。
- 真实执行过的轨迹：实线。
- 不可达或碰撞段：用不同颜色或断点标识。

这里不能把单个 IK 目标点与完整的运动轨迹混为一谈。

建议默认只显示 TCP 规划虚线，用户勾选后才展开各关节轨迹，避免多条曲线遮挡机器人本体。

这方面很值得参考 [MoveIt 2 Tutorials](https://github.com/moveit/moveit2_tutorials?utm_source=chatgpt.com)。其示例区分运动规划与执行，并在 RViz 中展示规划轨迹、目标坐标系和路径线。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



# 六、Simulation 的三种模式和控制权系统

这里我建议对你的描述做一个细小但重要的调整。

你提出：

1. 完全人工录制。
2. 经典专家自动执行，可人工干预。
3. VLN/VLA 模型执行，可人工干预。

这三种应该称为 Execution Profile（执行配置），不应直接等同于 Recording Mode（录制模式）。

因为三种执行来源都可能同时需要录制数据。

| 执行配置                 | 默认控制来源            | 是否可录制 | 是否允许接管 |
| -------------------- | ----------------- | ----- | ------ |
| Human Demonstration  | Human             | 是     | 已由人工控制 |
| Expert Demonstration | Expert Controller | 是     | 允许受控接管 |
| Policy Rollout       | VLN / VLA / ACT 等 | 是     | 允许受控接管 |

另外，控制权应该按机器人部件分配，而不是简单地给整个机器人一个总开关。

比如 LanderPi 可以底盘归导航控制器、机械臂归 VLA；SO101 可以分别处理左臂和右臂。

## 6.1 运行状态与控制权细化，具体要做什么？

要定义两套不同的状态机。

第一套是仿真运行状态：

`Ready → Running ↔ Paused → Stopped / Reset`

第二套是控制权状态：

### Control Authority 状态流

Policy / Expert Active

算法持有指定执行器的控制权

Request Takeover

Handover Pending

停止旧命令流、撤销未完成目标、等待后端确认

Human Intervention

允许鼠标或实体主臂执行控制

Resume Policy / Continue Human / End

由用户选择下一步操作

还要处理几种异常：

| 情况                        | 系统应该怎么办                  |
| ------------------------- | ------------------------ |
| 点击接管，但后端没有确认              | 保持未授权状态，禁止人工命令           |
| 主臂断开                      | 停止接收过期输入，执行安全保持/停止策略     |
| 用户切换页面                    | 不擅自结束实验，但解除持续的键盘驾驶输入     |
| VLA 已产生尚未完成的 Action Chunk | 在交接时使旧命令失效，避免恢复执行        |
| 恢复模型                      | 必须明确从新观测/新目标开始还是恢复某个策略状态 |
| 数据正在录制                    | 保留同一 Episode，并记录控制权切换边界  |

尤其是 VLA 的 Action Chunk，暂停后不能假设剩余动作仍适合新的机器人状态。

另外，物理外力干预与控制接管并不是一回事。你可以允许算法持续控制，同时通过受控外力干预测试鲁棒性；这类操作需要独立的干预权限和事件记录。

# 七、Replay & Annotation 应该怎样工作？

你的理解方向正确，但 Replay & Annotation 不只是把轨迹重新播放。

它是一套单条 Episode 的检查、解释与标注工作流。

我建议采用这样的流程：

1. 选择 Episode

   按机器人、任务、采集时间、Human/Expert/Policy、成功状态和数据质量进行筛选。
2. 同步回放

   统一时间轴控制 3D 机器人、相机图像、关节曲线、TCP 路径和事件。
3. 检查关键阶段

   例如接近、闭合夹爪、抬升、交接、释放，检查对应动作与观测。
4. 添加或修订标注

   在时间轴上标记阶段区间、失败原因、控制来源或任务语言描述，保留标注来源和版本。
5. 检查数据质量

   判断记录是否完整、任务是否成功、数据是否满足特定训练用途。
6. 保存审核结果

   保存标注版本，必要时将 Episode 加入一个已命名的数据集。

## 7.1 需要标注什么？模型究竟使用哪些标注？

这里要纠正一个常见误解：

不是所有机器人训练模型都必须使用人工阶段标签。

例如 ACT、普通 BC、Diffusion Policy 通常可以使用同步的 Observation-Action 序列进行训练；任务阶段标签可以帮助分析、切片或构建更精细的数据集，但不一定是模型的直接输入。

而语言条件 VLA、VLN 等任务，则可能需要任务语言、目标描述或其他语义监督。

我建议将标注分为四类：

| 标注类型                  | 示例                           | 主要用途         |
| --------------------- | ---------------------------- | ------------ |
| Task Metadata         | “拾起红色方块”                     | 任务识别、语言条件训练  |
| Phase Annotation      | Approach、Grasp、Lift、Handover | 阶段分析、切片与专家生成 |
| Outcome / Failure     | 成功、抓取滑脱、碰撞、超时                | 数据筛选和评估      |
| Perception Annotation | 检测框、物体类别、位姿、分割掩码             | 感知模型训练和误差评估  |

对于你的两条任务线，我建议先支持 Phase、Outcome、Task Metadata 三类，再按视觉算法需要扩展图像级标注。

还要区分自动生成的仿真标签与人工审核后的标签。例如物体的 Ground Truth 位姿可以从 MuJoCo 获得，但模型预测的位姿应单独记录。

## 7.2 推荐参考哪些项目？

[Shihan Wu's Homepage](https://images.openai.com/static-rsc-4/zp-H6aUDuXgFhCrmKGwpDhrYx2ZGuyysvU0deVVKgnms1P2Xa0KDziOmScyNQvuPFMRbvRDtb9keYLJ--tumTsceWkCBGndft4OvqGAybx4tdpPcKTxwQRJXUCQ2B6lTNo-WYBY7mEAO0TiLg1vCW9qBCb3Jy57XlPso0t69Zyc?purpose=inline)

[MimicGen](https://github.com/NVlabs/mimicgen?utm_source=chatgpt.com)

最值得参考机器人阶段标注与专家数据生成。它将演示分割为子任务片段，使用子任务终止信号和轨迹片段生成新数据，还提供可视化调试工具。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



[How to Run Object Tracking in CVAT Online with SAM2 and AI Agents | CVAT Changelog](https://images.openai.com/static-rsc-4/_tHWvRZBEEuqD5LzeVKSQ_cwZuG4a0zyJiQtqXXCay1D5rRvxf5IajDMK0gOJv9-pJRbVp9FiZF8XZKwcJ738l5lRT_IZno71rI_0HFaUV_YdOSvapg3ZnO1odnMTw2pBYUS_JCSV4fE-aCUPddYIL52ht1ggCcp-yvTUWKRq0Q?purpose=inline)

[CVAT](https://github.com/cvat-ai/cvat?utm_source=chatgpt.com)

参考视频检测框、跨帧目标追踪、人工修订与插值标注。如果后续做物体识别数据集，它比较有价值。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



[Introducing FiftyOne Enterprise Workflows - Voxel51](https://images.openai.com/static-rsc-4/mFkRZOdHihaMlneoQKzMCnynYgS4GizSQHv04ppOdI1S5qKKNiDNnnRYJjCZ3DFd4fAonLnYKI8vpC6CHa7iz_PeyPlp6c5LiRQO2UiWC0KdwqccbEWYwZgmCXT2BKcFBAgwU-iywJ40U9i8Oac2wAwvCwIz4flN8evochlimA4?purpose=inline)

[FiftyOne](https://github.com/voxel51/fiftyone?utm_source=chatgpt.com)

参考数据筛选、质量检查、标签查看、视频片段和模型失败案例检索。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



另外，LeRobot 的近期公开文档已有面向语言注释的 `lerobot-annotate` 管线，能够生成与 Episode 关联的语言字段。这值得你调研，但不代表你当前使用的 ACT 或 LeRobot 数据配置已经自动支持或需要全部语言字段。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



# 八、Dataset Management 是否和 Replay 重复？

确实存在功能重叠，而且我建议 V1 将它们放进同一个 Data 工作区，而不是做两个完全独立的顶级页面。

但两者负责不同粒度的数据：

|       | Replay & Annotation | Dataset Management   |
| ----- | ------------------- | -------------------- |
| 主要对象  | 单条 Episode / 时间片段   | 多条 Episode / Dataset |
| 主要操作  | 播放、查看、标注、修订         | 筛选、分组、去重、导出          |
| 时间轴   | 核心组件                | 通常不是核心               |
| 3D 视图 | 必须支持                | 可选预览                 |
| 训练用途  | 检查单条数据              | 生成可训练的数据集版本          |

我建议实际导航可以这样做：

```
Data
├── Episode Library
│   ├── 搜索 / 分类 / 过滤
│   └── 选择 Episode
├── Episode Detail
│   ├── 3D Replay
│   ├── Camera Views
│   ├── Timeline
│   ├── Phase Annotation
│   └── Quality Review
└── Dataset Collections
    ├── Episode 集合
    ├── Train / Validation Split
    ├── Dataset Version
    └── LeRobot Export
```

这样用户先进入数据列表，点击一条 Episode 后自然进入回放详情页面。

我还建议保持三种独立的质量字段：

Recording Validity、Task Success、Training Eligibility。

例如“方块传递失败但三路相机和动作数据完整”，仍然可能是有价值的失败样本，而不是应该直接删除的垃圾数据。

# 九、Model Training、Prediction 和 Evaluation 怎样划分？

你的直觉是正确的：Prediction 实际执行应该回到 Simulation，而不是在 Training 页面再造一套机器人实时控制工作台。

建议这三个概念分开：

Model Training

选择数据 → 配置模型 → 训练 → Checkpoint

Model Registry

模型版本 · 数据来源 · 配置 · 训练指标

Simulation · Policy Rollout

加载模型进行真实仿真推理、观察、接管与录制

Evaluation

测试结果、任务指标、对照实验与模型比较

Training 页面主要负责训练配置、资源状态、Loss 曲线、验证指标、日志与 Checkpoint。

如果训练过程中需要观察模型行为，可以展示周期性验证 Rollout 的视频或链接到一个独立的 Simulation Run，但不必把实时 3D 仿真窗口作为每次训练的必要组件。

VLN 的 Prediction 同样可以先复用 Simulation，只是它的 Policy Adapter 输出可能是导航目标、局部速度、子任务指令等，而 VLA 可能输出末端动作或关节目标。两者不应被强行定义为相同维度的动作数组。

### 最值得参考的项目

[LeLab](https://github.com/huggingface/leLab?utm_source=chatgpt.com)：它已经将标定、遥操作、录制、浏览、训练和推理组织在浏览器工作流里。你应该特别研究从 Dataset 到 Training Job，再到推理执行的页面跳转。官方当前说明其面向 SO-ARM101，仍需要为你的仿真机器人做适配。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



[MLflow](https://github.com/mlflow/mlflow?utm_source=chatgpt.com)：参考训练任务列表、超参数、Metrics、Artifacts 和模型版本关系。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



[Aim](https://github.com/aimhubio/aim?utm_source=chatgpt.com)：参考训练曲线、多训练运行比较和资源监控。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



# 十、Task Configuration 与成功条件应该怎样定义？

我认为这一部分必须从现在开始考虑，因为它会影响 Scene Setup、Simulation、Replay 和 Evaluation 四个工作区。

一个 Task 不应该只包含 `task_name`。

建议至少包含以下内容：

| 字段                    | 说明                    |
| --------------------- | --------------------- |
| Task Type             | 当前是什么实验类型             |
| Initial Conditions    | 场景、机器人、物体初态           |
| Objective             | 任务目标和目标对象             |
| Controller Profile    | Human、Expert 或 Policy |
| Observation Profile   | 该算法允许使用哪些数据           |
| Action Space          | 控制底盘、关节、TCP 或更高层动作    |
| Success Criteria      | 任务完成的可检查条件            |
| Failure / Termination | 超时、碰撞、失效、人工停止等        |
| Recording Profile     | 记录哪些观测、动作和事件          |

注意 Observation Profile 要与Operator View Profile 分开。

例如人类遥操作时能看到第三人称视角，不代表 VLA Policy 也能使用该画面。否则后续训练和评估很容易发生观测信息泄漏或数据分布不一致。

## 10.1 两条任务线的成功条件候选

以下是适合你后续讨论的任务验收方向；具体容差、阈值和重复次数仍应通过实验标定。

| 任务                   | 可检查的主要成功条件               |
| -------------------- | ------------------------ |
| PointGoal Navigation | 到达指定位置容差内，满足朝向要求（如有），未超时 |
| Route Following      | 沿参考路线完成目标进度，横向偏差在允许范围内   |
| Object Navigation    | 找到正确目标，停靠在可接受位置，满足导航完成判定 |
| 远距离目标识别              | 正确类别、方位估计误差符合要求          |
| 中距离 RGB-D 定位         | 三维位置误差、识别稳定性符合要求         |
| 近场 TCP 相对识别          | 目标与 TCP 的相对位姿估计误差符合要求    |
| Visual Servo         | 目标图像误差收敛，扰动后能够重新跟踪       |
| 固定底盘 IK              | 到达受约束目标，满足关节限制、碰撞及末端误差要求 |
| 底盘辅助 IK              | 找到可达停靠位置，完成底盘与机械臂协同末端任务  |
| LanderPi 抓取          | 物体离开支撑面，抬升、保持和随夹爪运动满足要求  |
| SO101 方块传递           | 完成抓取、交接或台面中转、释放和最终放置     |
| SO101 拧螺丝            | 后续定义对准、接合、旋入、扭矩及装配完成条件   |

尤其 SO101，你需要将空中手递手与台面中转视为两个不同的任务模板。它们的物体交接条件、接触过程和成功标准不同。

此外，我建议把任务结果分成：

`Success`、`Failure`、`Timeout`、`Aborted`、`Invalid Run`

并额外记录是否发生人工接管。

这样统计模型自主成功率时，就不会把人工帮助完成的结果误计为模型独立成功。

对于 LanderPi 抓取，你此前已经讨论过抬升、持续抓持、双侧接触等指标，可以作为后续任务验收规范的基础，但不必在整个 Scene Setup 的第一版 UI 中一次冻结所有数值门槛。

# 十一、按照你的需求重新筛选 GitHub 参考项目

除了之前的 URDF Viewer、mjswan、Vuer、robosuite，我认为现在有必要新增更贴近场景配置、标注、任务管理、训练监控的项目。

| 你正在设计的功能      | 推荐 GitHub 项目                                                                          | 最应该学习的内容                           |
| ------------- | ------------------------------------------------------------------------------------- | ---------------------------------- |
| 场景与桌面任务配置     | [RoboCasa](https://github.com/robocasa/robocasa?utm_source=chatgpt.com)               | MuJoCo 场景、物体库、任务演示和遥操作             |
| 导航任务模板        | [Habitat-Lab](https://github.com/facebookresearch/habitat-lab?utm_source=chatgpt.com) | PointNav、ObjectNav、Episode 配置与成功条件 |
| 多样化操作任务       | [ManiSkill](https://github.com/mani-skill/Maniskill?utm_source=chatgpt.com)           | 机器人操作任务、场景变化、任务评估；底层不是 MuJoCo      |
| TCP 轨迹与规划反馈   | [MoveIt 2](https://github.com/moveit/moveit2_tutorials?utm_source=chatgpt.com)        | 目标位姿、规划轨迹、运动预览                     |
| Docking 工作台布局 | [Dockview](https://github.com/dockview/dockview?utm_source=chatgpt.com)               | 面板拖拽、分屏、浮动窗口、布局保存                  |
| 多模态回放         | [Rerun](https://github.com/rerun-io/rerun?utm_source=chatgpt.com)                     | 同步时间轴、多视图布局、传感器回放                  |
| 示教阶段标注        | [MimicGen](https://github.com/NVlabs/mimicgen?utm_source=chatgpt.com)                 | 子任务分段、阶段信号与专家轨迹生成                  |
| 数据集检查与筛选      | [FiftyOne](https://github.com/voxel51/fiftyone?utm_source=chatgpt.com)                | 结果分类、数据质量、标签检查                     |
| 视觉标注          | [CVAT](https://github.com/cvat-ai/cvat?utm_source=chatgpt.com)                        | 目标框、视频轨迹与人工修订                      |
| 录制到训练流程       | [LeLab](https://github.com/huggingface/leLab?utm_source=chatgpt.com)                  | Dataset、Training、Inference 的完整流程   |
| 训练曲线与模型管理     | [MLflow](https://github.com/mlflow/mlflow?utm_source=chatgpt.com)                     | 超参数、Metrics、模型及运行历史                |

其中 RoboCasa 提供场景、物体和遥操作相关 Demo，适合你研究 Scene Setup 与实验任务的关系；它不是现成的网页拖拽式场景编辑器。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Dockview 支持面板拖拽、网格分割、浮动、弹出和布局序列化；Rerun 的 Blueprint 则将录制数据与数据显示布局区分开来，非常适合作为你保存任务工作区预设的参考。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



这也是我建议你先研究这些项目的原因：它们分别解决了你不同层次的设计问题，而不是让一个仓库承担所有功能。

# 十二、我建议你接下来画哪些 PPT？

你现在可以开始制作一组真正用于交互设计讨论的 PPT，不需要画得很漂亮。

我建议总共 6 张核心草图。

| PPT | 页面                     | 你需要重点表达                         |
| --- | ---------------------- | ------------------------------- |
| 1   | 全局导航结构                 | 四个主要导航组、六个工作区和用户跳转流程            |
| 2   | Scene Setup 通用结构       | 场景模板选择、主画面、物体列表、任务配置、启动入口       |
| 3   | SO101 Scene Setup      | 桌面俯视图、方块布置、双臂范围、3D 检查           |
| 4   | Simulation 通用结构        | A–H 八个面板区域、控制条、3D 核心视图          |
| 5   | LanderPi 专用 Simulation | 导航布局与近场操作布局、RGB-D、地图、TCP        |
| 6   | Replay & Annotation    | Episode 列表、同步 3D/相机、时间轴、标签与质量检查 |

每张 PPT 只需要用矩形表示组件，注明哪些区域允许调整尺寸、哪些始终显示、哪些只在特定任务下出现。

对尚未确定的交互，可以直接用箭头或文字标注，例如“点击以后是否进入新界面？”“三路相机能不能最大化？”“目标方块怎样拖动？”。

## 目前我最推荐的下一步

先集中设计 Scene Setup V0.1，特别是它的通用布局。

因为你已经描述了 LanderPi 导航、四类感知、两类 IK、近场抓取和 SO101 方块布置，我们现在已经有足够多的真实任务，可以检验一套通用 Scene Setup 是否合理。

我建议把首张场景配置 PPT 分成五块：

左侧任务模板、中央 2D/3D 场景、右侧对象属性、底部实验条件、顶部场景检查与启动。

然后分别放入 LanderPi 与 SO101 的场景，看看是否能够保持统一结构。

还有一个值得讨论的设计问题：Scene Setup 中的场景布置，是以「打开已有 MuJoCo 场景并修改对象」为主，还是以「从资产库拖入桌子、方块、障碍物，重新组合实验场景」为主？

我的建议是 V1 优先采用已有 MuJoCo 场景模板与受限对象编辑，同时保留未来资产库扩展能力。这样可以先实现你真正需要的实验准备流程，不会提前陷入通用三维场景编辑器的开发。