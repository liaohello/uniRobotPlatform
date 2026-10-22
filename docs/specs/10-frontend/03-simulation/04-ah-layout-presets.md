# Simulation A–H 功能区域与任务布局

规范 ID：`FE-SIM-LAYOUT-AH` · 责任层：前端 · 版本：V0.4（2026-10-22）

状态：设计草案；S08/S09 是用户提供的分析文本，不自动视为所有细节已确认。Waypoint 范围以 S10 的用户明确选择为准。实现及产品验收均未执行。

来源：[S08](../../90-governance/sources/S08-frontend-ia-analysis.md)、[S09](../../90-governance/sources/S09-unified-development-reuse-analysis.md)。

[上级目录](README.md) · [总索引](../../README.md)

关联需求：[REQ-LAYOUT-001](../../indexes/05-requirements.md#req-layout-001)

## A–H 区域契约

| 编号 | 区域 | 主责功能 | 当前显示建议 |
|---|---|---|---|
| A | Global Header | 项目、机器人、场景、任务、连接 | 常驻摘要；技术身份进详情 |
| B | Runtime Toolbar | 运行、暂停、继续、Reset、停止运动、录制 | 控件区分操作后果，等后端确认 |
| C | Control Authority | Human/Expert/Policy、部件范围、接管状态 | 常驻当前来源与阻塞原因 |
| D | Scene Hierarchy | Robot/Base/Arm/Sensors/Objects/Layers | 可折叠；选中与授权分开 |
| E | Main Viewport | 三维、地图或主要实验画面 | 主操作区，复用工具与显示语义 |
| F | Inspector | 选择对象、Actual/Target、残差、命令反馈 | 关节滑条以监控为主 |
| G | Sensor Panels | RGB/Depth/LiDAR/相机/点云 | 按实际能力和允许视图组合 |
| H | Live Timeline | 事件、阶段、来源、录制边界 | 按需展开，不代表物理可回退 |

这是内容和可达性草案，字号、尺寸、左右位置、浮窗/弹出尚未冻结。工具拖动和驾驶期间不因阶段切换强制重排；布局变化不转移控制权、不停止录制。

## 任务预设

| 预设 | E/G 重点 | F/C 重点 |
|---|---|---|
| 导航 | 地图或 3D、LiDAR、估计位置、路线 | 当前 Waypoint、导航来源、键盘驾驶与授权 |
| 感知 | RGB-D/诊断与 3D 对照 | 参考点、Frame、估计与评分来源、有效性 |
| 近场 IK/抓取 | 臂三维、RGB-D、按需点云 | TCP/关节、候选与实际、残差和接触反馈能力 |
| 双臂 | 双臂三维、中央/左右腕图像 | 两臂分组、主从误差、共享区/控制权 |

Operator View Profile 限制哪些信息可以获得；布局仅决定如何排列允许内容。隐藏禁止真值不够，后端载荷也必须按协议过滤；第三人称辅助采集须有独立版本，不能冒充受限采集。

制作通用 A–H 草图后分别检查导航、近场与双臂场景；不在本轮生成 PPT 或前端实现。关联 [区域索引](../../indexes/03-ui-regions.md)、[布局/焦点](../01-shell/02-layout-input-focus.md)。

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。

## V0.4 当前布局映射

当前参考 IMG-022：A 全局顶部；B 拆成 Simulation/Task/Recording；C 分 Execution Profile 与部件 Control Authority；D 左侧层级树；E 中央 Select/Joint/TCP/Layers；F 右侧实际/目标/IK与轨迹/关节/命令；G 下方传感器；H 来源/阶段/事件。区域职责不变，具体布局由旧图更新。

[V2 对照](06-simulation-v2-review.md) 标明已体现的修正和未决：实时来源轨需能表达混合部件、夹爪入口保留、指标单位和命令状态一致。顶部运行摘要可折叠，避免持续占用视口。
