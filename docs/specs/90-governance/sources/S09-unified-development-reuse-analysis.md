我的建议非常明确：

不要先把 LanderPi 导航、视觉伺服、IK、SO101 双臂等子任务分别开发成独立的小前端，再试图把它们合并。也不要一次性开发完整的大平台。

最适合你当前项目的是第三条路线：

「统一前端骨架先行 + 按任务纵向开发 + 现有开源组件复用」。

这样既能避免重复开发，也能让你尽快做出真正可用的机器人实验界面。

而且我找到一个特别符合你新需求的开源项目：[mujoco-scene-editor](https://github.com/markusgrotz/mujoco-scene-editor?utm_source=chatgpt.com)。它已经实现了在浏览器中编辑 MuJoCo 场景、添加几何体和 Mesh、拖动 Gizmo 调整物体位姿、导出场景。这值得你优先研究，而不必从零开发场景布置的全部交互。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



# 一、先更新你的 V1 范围

你现在正式增加了一个能力：

V1 支持在 2D 地图上通过鼠标创建、编辑和保存 Navigation Waypoints。

这条需求我建议放在两个位置：

| 工作区         | Waypoint 的职责                 |
| ----------- | ---------------------------- |
| Scene Setup | 在地图上设定目标点、路径点，拖动修改，保存导航任务    |
| Simulation  | 展示规划路径、当前 Waypoint、导航进度和执行结果 |

Simulation 后续也可以允许修改正在执行的导航计划，但必须经过确认和导航控制器重新规划，不能随意把正在执行的路径直接覆盖。

V1 的地图编辑工具建议支持单击创建、拖动调整、删除、编号、调整顺序、显示方向、保存/加载，以及向导航后端提交。需要处理地图像素与 `map` 坐标系之间的转换、占据栅格障碍检查以及目标不可达反馈。

可以直接参考：

- [ROS2 Waypoint Editor](https://github.com/kzm784/waypoint_editor?utm_source=chatgpt.com)：已有在 2D/3D 地图上编辑路径点并保存为 CSV 或 Nav2 兼容 YAML 的实现，适合研究操作规则。

  [image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

  GitHub

- [Navigation2](https://github.com/ros-navigation/navigation2?utm_source=chatgpt.com)：`nav2_waypoint_follower` 接收有序 Waypoint，提供执行进度和失败反馈，适合作为后端接口参考。

  [image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

  GitHub



# 二、为什么不建议先开发多个独立小前端？

你的项目现在已经有三个开发基础：

- `mobileCar`：LanderPi 在线控制、TCP、键盘驾驶等。
- `bimanual_proj`：SO101 双臂专家执行、多相机、轨迹和回放。
- `mujoco_learning`：Viser IK、视觉感知和控制算法实验。

这些是你提供的本地代码分析结论，尚未在本轮重新检查源码。

如果现在分别把每个子任务包装成一个完整的小前端，后续很可能出现下面的问题：

| 功能       | 独立开发多个前端的结果           |
| -------- | --------------------- |
| 3D 选择与拖动 | 每个前端都有自己的鼠标事件与选择规则    |
| 机器人状态    | 不同系统使用不同字段、坐标系和单位     |
| 场景编辑     | 方块、障碍物与机器人初态重复开发      |
| 多面板布局    | 每个任务单独实现一套布局          |
| 控制权      | 不同前端对人工接管的定义不一致       |
| 数据回放     | 每个任务又写一套时间轴           |
| 数据录制     | Episode 格式和事件字段越来越难统一 |

因此，我建议把你已有的三个项目作为后端能力与参考实现保留，而新前端只维护一套统一的基础设施。

但也不应该先花很长时间开发一个完全没有接入真实机器人的空壳平台。

## 最适合的组织结构

Unified Frontend Shell

全局导航 · Workspace · Docking · 通知 · 项目状态

Shared Frontend Core

3D Viewport · Selection · Gizmo · Timeline · Robot State · Command Feedback

Navigation

地图与 Waypoint

Manipulation

Joint / TCP / IK

Bimanual

双臂与多相机

Backend Adapters

不同仿真、算法和录制接口的规范化适配

mobileCar

bimanual_proj

mujoco_learning

开发顺序应该是：

先搭一个最小的统一工作台，然后让一个真实任务从场景配置、仿真、控制、录制到回放完整跑通，再添加下一个任务。

我称它为“统一架构下的纵向切片”。

其中，独立的小原型仍然有价值。例如专门制作一个鼠标框选或 TCP Gizmo 实验，验证手感后移入统一组件库。但它不是一套长期维护的独立业务前端。

# 三、最值得复用的开源项目与资源

我把资源分成四类：前端交互组件、MuJoCo 场景与模型、任务算法、数据与训练流程。

这几类资源的复用程度不一样。有些可以直接集成，有些只能借鉴接口或算法思想。

## 3.1 场景布置：优先研究现成的 MuJoCo 编辑器

[mujoco-scene-editor · PyPI](https://images.openai.com/static-rsc-4/0DL50-8KZocrzW0P7zpKwv40fAEFp3NpnRDnd1BUCx1Ses-pjT6fYt-E01LWOLugRQp4ag1hzDcsfPP-rR8b2K5s6taUzRgnM5Dz2DFv1k1_PnG-VMnuBnm66FB6Kwg8ZvzEvXFOhRzivDtxmJ9y_BWdVXt8wqsmCrRZipak610?purpose=inline)

[MuJoCo Scene Editor](https://github.com/markusgrotz/mujoco-scene-editor?utm_source=chatgpt.com)

最值得先做独立验证。它支持在网页中添加 Box、Sphere、Cylinder、Mesh 和机器人，使用 Gizmo 修改位姿并导出 MJCF 或 JSON。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



适合：Scene Setup 的三维摆放、物体属性、场景保存。

[RoboCasa: Large-Scale Simulation of Everyday Tasks for Generalist Robots - Stretch Docs](https://images.openai.com/static-rsc-4/XB-1fel_JHvI8xa3Zx0DLZalj6BJ6qQm5DQpRhvBZmCAchdq8q2VfCkKlBLe1icglLDlxJjVwTseifFVqxQepGE64DLqd2UEjg47keqo_1ZfXtfO25Y2u4XFQYZ1HUSiWUIKQNAIu6pc4Uinb-HrxRtFWpMwTmJ_TwpKT5Hz7xo?purpose=inline)

[RoboCasa](https://github.com/robocasa/robocasa?utm_source=chatgpt.com)

提供大量 MuJoCo 厨房环境、物体及任务生成资源。现有项目包含数千个厨房场景和三维物体资产。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



适合：LanderPi 的室内环境与障碍物、后续复杂操作场景。

[4 - MuJoCo | ECE 4560](https://images.openai.com/static-rsc-4/Tw2LDe0aFDf66iR3cvFeQ0NXe1e9VO4Qhrede7naGZVErC5ybxC-X3fOlwxAL5lnsBbq8kAISKC3u68b8FilFE8eAccm2hfV9TlMbubeY45h0J4iNymXZGmSNAeYnWL20MzWrA7H_vD4qi1djELenQqBo2AtDvopRyTK8zVycIs?purpose=inline)

[MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie?utm_source=chatgpt.com)

官方维护的 MuJoCo 机器人模型集合，包含 The Robot Studio SO101 的模型和场景文件。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



适合：机器人模型、MJCF、Mesh、关节和执行器定义的参考。

[Robots — robosuite 1.5 documentation](https://images.openai.com/static-rsc-4/vXxJCEubLHzhjLYZOXDpCx-jqVyhOy5FaffjMaBjtvm0ismeNvLbTOuISFUZg5Aa5_RIm_Si2OrbXzJcPXzhPosnSw8g5uZnQuoLRbTfkrE6s8nrWZLXbzSzZTae9cEkKsXcVhFp8XiroGNZt5THGBTcDGuyuHigZeubdmCs6Bo?purpose=inline)

[robosuite](https://github.com/ARISE-Initiative/robosuite?utm_source=chatgpt.com)

提供 `Arena + Robot + Objects` 的场景组合方式，以及 TableArena、BinsArena、可复用物体和任务模型。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



适合：SO101 桌面、方块、托盘、任务初始化及物体随机摆放。

这里有一个重要的技术风险，尤其是第一个编辑器。

`mujoco-scene-editor` 当前 README 明确说明：导入并重新导出 MJCF 时，部分原始字段可能丢失，例如某些关节、执行器、摩擦和碰撞相关属性。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



所以我建议先参考它的场景操作界面，不要直接用它覆盖你已有的 LanderPi 或 SO101 原始 MJCF 模型。

更稳妥的方式是：

原始机器人与仿真模型保持不变，前端只编辑场景对象的配置（位置、姿态、尺寸、颜色和资产引用），由后端根据这份配置生成或更新场景。

例如：

```
原始机器人 MJCF
        +
桌面 / 障碍物 / 方块资产
        +
Scene Configuration（JSON）
        ↓
MuJoCo Scene Builder
        ↓
可加载的实验场景
```

这样你的关节限位、碰撞几何、执行器、传感器等不会因为重新保存场景而意外改变。

还可以看看 [RobolaWeb 的 MuJoCo 官方社区介绍](https://github.com/google-deepmind/mujoco/discussions/2999?utm_source=chatgpt.com)，它采用网页编辑器与本地 MuJoCo 运行时同步的方式。但它的代码授权和完整导入导出能力仍需单独检查，不应直接视为可无条件集成的组件。

## 3.2 三维前端操作：尽量使用成熟组件

你的很多基本交互实际上不用从零写。

| 你需要的功能       | 开源项目                                                                             | 推荐用法                                                |
| ------------ | -------------------------------------------------------------------------------- | --------------------------------------------------- |
| 3D 相机和 Gizmo | [React Three Drei](https://github.com/pmndrs/drei?utm_source=chatgpt.com)        | 复用 CameraControls、TransformControls、PivotControls 等 |
| URDF 模型加载    | [URDF Loaders](https://github.com/gkjohnson/urdf-loaders?utm_source=chatgpt.com) | 读取模型层级与关节信息                                         |
| 三维机械臂交互参考    | [URDF Viewer](https://github.com/tony1213/urdf-viewer?utm_source=chatgpt.com)    | 研究关节选择与 TCP 交互                                      |
| 多面板编辑器       | [Dockview](https://github.com/dockview/dockview?utm_source=chatgpt.com)          | 拖动、停靠、最大化、保存布局                                      |
| 物理受力交互       | [mjswan](https://github.com/ttktjmt/mjswan?utm_source=chatgpt.com)               | 借鉴鼠标施力交互                                            |
| 传感器与轨迹回放     | [Rerun](https://github.com/rerun-io/rerun?utm_source=chatgpt.com)                | 同步时间轴和可视化设计                                         |

Drei 已经提供平移、旋转等 Transform Controls，不需要从零编写整套三轴操作手柄。Dockview 也已经具备布局序列化和浮动面板机制。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



不过，通用 TransformControls 不等于机器人专用 Joint Gizmo 或 IK 控制器。你仍需要把它们产生的交互目标映射到机器人关节、TCP、控制权限和 MuJoCo 后端。

## 3.3 LanderPi 各个子任务可以借鉴什么？

| 你的任务         | 主要参考                                                                                  | 应优先复用的能力                          |
| ------------ | ------------------------------------------------------------------------------------- | --------------------------------- |
| 已知目标导航       | [Nav2](https://github.com/ros-navigation/navigation2?utm_source=chatgpt.com)          | 路径规划、导航执行、结果反馈                    |
| 路径点编辑        | [Waypoint Editor](https://github.com/kzm784/waypoint_editor?utm_source=chatgpt.com)   | 鼠标编辑、路径点顺序、保存                     |
| 2D 地图与 LiDAR | [ros2-web2d](https://github.com/Neoplanetz/ros2-web2d?utm_source=chatgpt.com)         | OccupancyGrid、Path、Pose、LaserScan |
| 语义目标导航       | [Habitat-Lab](https://github.com/facebookresearch/habitat-lab?utm_source=chatgpt.com) | PointNav、ObjectNav 的任务定义和评价思路     |
| RGB-D / 点云   | [Open3D](https://github.com/isl-org/Open3D?utm_source=chatgpt.com)                    | 点云处理、配准、几何计算                      |
| 视觉伺服         | [ViSP](https://github.com/lagadic/visp?utm_source=chatgpt.com)                        | 视觉特征、视觉误差与控制律                     |
| 末端 IK        | [Mink](https://github.com/kevinzakka/mink?utm_source=chatgpt.com)                     | MuJoCo 微分 IK、约束与目标跟踪              |
| 机械臂轨迹规划      | [MoveIt 2](https://github.com/moveit/moveit2_tutorials?utm_source=chatgpt.com)        | 运动规划、碰撞检查、轨迹预览                    |

这里面我想特别推荐你关注 `ros2-web2d`。它已经有 OccupancyGrid、地图图像、路径、机器人位姿和 LiDAR 的网页可视化组件，并提供 React 示例。这样你不用从头写整个 2D SLAM 地图渲染系统。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



ViSP 也值得深入研究，因为它是真正面向视觉伺服的库，能够计算基于视觉特征误差的控制律。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



但要注意兼容边界：

- Nav2 和 ViSP 并不意味着可以直接接入你现有 Python 控制循环，需要 ROS2 或其他适配接口。
- Habitat-Lab 的仿真环境不是 MuJoCo，主要借鉴任务定义与算法思路。
- Open3D 适合后端点云运算，不代表应让浏览器运行整个 Open3D 桌面 GUI。
- Mink 是否优于现有 IK，需要在 LanderPi 自由度、约束和实际抓取任务上进行对比。

## 3.4 SO101 双臂、专家数据与模型训练

除了你已经在使用的 LeRobot，我还找到了两个值得作为代码对照的资源。

[SO101 SimEngine](https://github.com/RajatDandekar/sim-engine?utm_source=chatgpt.com)

这个项目将 MuJoCo SO101 的示教录制、Policy、训练和评估放在同一套应用流程中，提供 HDF5 数据、训练曲线和成功率展示。它的 UI 主要是桌面式交互，并非你需要的完整浏览器工作台。ACT、Diffusion 和 SmolVLA 在仓库中部分以待实现的骨架形式提供，不能误认为这些策略全部已经训练成功。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



[SO101 MuJoCo LeRobot Adapter](https://github.com/SinfonIAUniandes/lerobot_robot_so101_mujoco?utm_source=chatgpt.com)

它尝试将模拟 SO101 包装为 LeRobot 的机器人接口，并提供虚拟 RGB/Depth 相机和录制配置。适合你参考如何将 MuJoCo 仿真从臂接入 LeRobot 数据采集链路。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



此外，[LeLab](https://github.com/huggingface/leLab?utm_source=chatgpt.com) 已经把遥操作、录制、浏览、训练、推理和回放组织在同一个浏览器工作流程中，是你的 Model Training 和 Data 工作区非常好的产品设计参考。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



对你来说，已有的 `bimanual_proj` 应继续作为主要的 SO101 任务基础。这些新项目主要用于补充缺失接口或借鉴工作流，而不是替换你已经验证过的接触、轨迹和多相机系统。

# 四、按复用价值，先研究哪些项目？

我给你整理一个优先级更明确的短表。

| 优先级 | 项目                                                                                               | 主要目的          | 复用方式                |
| --- | ------------------------------------------------------------------------------------------------ | ------------- | ------------------- |
| P0  | [MuJoCo Scene Editor](https://github.com/markusgrotz/mujoco-scene-editor?utm_source=chatgpt.com) | 省去大量场景编辑交互开发  | 先做 PoC，谨慎处理 MJCF 导出 |
| P0  | [Drei](https://github.com/pmndrs/drei?utm_source=chatgpt.com)                                    | 3D Gizmo 与相机  | 直接评估组件复用            |
| P0  | [Dockview](https://github.com/dockview/dockview?utm_source=chatgpt.com)                          | 全局工作区、多面板     | 直接评估组件复用            |
| P0  | [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie?utm_source=chatgpt.com)   | SO101 机器人模型   | 资产与模型对照             |
| P0  | [ros2-web2d](https://github.com/Neoplanetz/ros2-web2d?utm_source=chatgpt.com)                    | 2D 地图、导航可视化   | 组件或数据模型参考           |
| P0  | [Waypoint Editor](https://github.com/kzm784/waypoint_editor?utm_source=chatgpt.com)              | Waypoint 交互   | 工作流程参考              |
| P1  | [robosuite](https://github.com/ARISE-Initiative/robosuite?utm_source=chatgpt.com)                | 方块、桌面、容器、操作专家 | 后端资产与建模接口           |
| P1  | [RoboCasa](https://github.com/robocasa/robocasa?utm_source=chatgpt.com)                          | 大量复杂场景和物体     | 选择性复用资产             |
| P1  | [ViSP](https://github.com/lagadic/visp?utm_source=chatgpt.com)                                   | 视觉伺服闭环        | 算法参考与独立验证           |
| P1  | [LeLab](https://github.com/huggingface/leLab?utm_source=chatgpt.com)                             | 数据、训练、推理流程    | 界面与工作流参考            |

对于 RoboCasa 这样的大型项目，不建议为了几个桌面方块和障碍物就引入整套框架及大量资产依赖。

同样，复用现成机器人模型时，必须检查关节方向、零位、限位、执行器、夹爪行程、碰撞几何与相机外参是否与你现有模型一致。SO101 名称相同也不意味着状态数组和控制接口一定相同。

这些项目的代码许可证与资源文件许可证也需要分别核对，尤其是 RoboCasa 的第三方 Mesh、纹理和场景资产。

# 五、如何让“统一前端 + 分任务开发”真正可执行？

我建议你把开发过程划分为五个可验收阶段，而不是先开发六个完整页面。

1. Phase A — 统一前端最小骨架

   实现顶级导航、Dockview 布局、通用 3D Viewport、Inspector、机器人能力描述与命令状态接口。

   验收：能在同一个前端切换 LanderPi 和 SO101，保留一致的选择与视图操作。
2. Phase B — 第一个完整任务切片

   优先接入 `mobileCar` 的现有真实控制能力，完成受限场景配置、机器人观察、Joint/TCP 交互、命令回执、录制和回放。

   验收：一条真实 MuJoCo Episode 能够在统一前端中完整产生并同步回放。
3. Phase C — 场景配置与导航扩展

   增加桌面/物体编辑、2D 地图、Waypoint 创建和编辑，并连接现有导航算法。

   验收：能配置一条 Waypoint 路线，提交导航执行，记录路径、状态和结果。
4. Phase D — SO101 双臂接入

   复用统一选择系统、3D 控件、相机面板和录制机制，接入三相机、双实体主臂、专家执行、阶段事件。

   验收：双臂任务可以使用同一个工作台完成配置、执行、录制和回放，不再另写一套基础组件。
5. Phase E — 感知、训练与评估扩展

   接入视觉识别、视觉伺服、任务级评估；随后进一步完善 LeRobot 训练、模型管理和批量测试。

   验收：实验记录、数据集版本、模型 Checkpoint 和测试结果能够相互追溯。

这里有一个值得提前建立的能力：Task Plugin / Task Profile。

不同任务只声明自己需要的能力，而不是重新编写一套完整页面。

例如：

```
task_id: landerpi_visual_servo
robot: landerpi
scene_template: tabletop_targets

workspace: simulation

required_panels:
  - 3d_viewport
  - rgb_camera
  - depth_camera
  - tcp_inspector
  - visual_error_plot

control_capabilities:
  - joint_control
  - tcp_control
  - base_velocity
  - human_takeover

recording:
  profile: visual_servo_episode
```

这只是一个概念性的配置示例，不是已经确定的生产接口。

它表达的是：任务可以选择和组合通用组件，但不应该重新定义这些组件本身的行为。

# 六、还有一个非常重要的建议：建立可复用资源登记表

你现在看的 GitHub 项目越来越多，如果不管理，很容易发生“某个 Agent 发现一个新仓库，又重复开发了一套已经存在的功能”。

建议在 Specification Wiki 中增加：

`references/open-source-resource-registry.md`

每项资源记录：

| 字段            | 内容                                    |
| ------------- | ------------------------------------- |
| Resource      | 项目与 GitHub 链接                         |
| Capability    | 提供什么现成功能                              |
| Task Mapping  | 用于哪个 LanderPi / SO101 任务              |
| Reuse Level   | 直接集成、封装适配、参考实现、仅研究                    |
| Compatibility | MuJoCo / ROS2 / React / Python 版本兼容情况 |
| License       | 代码和资源授权                               |
| Risks         | 不兼容、丢失字段、依赖问题                         |
| Decision      | 采纳、待 PoC、拒绝                           |
| Verification  | 验证项目功能的测试记录                           |

你还可以给 Codex 一条明确规则：

实现新的前端功能前，先检查本地三个项目和 Resource Registry 是否已有对应实现；如果存在，必须先评估复用或适配方案。

这比单纯要求“尽量避免重复开发”更容易执行和验收。

## 七、现在应该如何继续设计？

我建议暂时不要再增加新的大模块，而是完成两项工作。

第一，冻结 Frontend IA V0.1 的主导航结构和工作区职责。这个层次以后不应该随着增加一个感知实验就大改。

第二，优先研究三个可直接减少工作量的核心项目：MuJoCo Scene Editor、Drei、Dockview。分别验证场景对象摆放、三维 Gizmo 和多面板布局。

它们的 PoC 验证通过后，再用你现有的 `mobileCar` 做第一个真实接入。

最终的开发策略是：大前端的架构先统一，小任务的功能逐个实现；成熟组件直接复用，现有仿真后端继续保留，只有无法满足统一交互契约的部分才重构。

这最适合你目前既有多套科研项目、又希望长期扩展 VLN/VLA 任务的情况。