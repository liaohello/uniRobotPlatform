# 任务、观测、执行与采集配置

规范 ID：`SYS-PROFILES` · 责任层：系统 · 版本：V0.6（2026-10-22）

来源：[S16](../90-governance/sources/S16-mobile-first-spec-repair.md)、[S15](../90-governance/sources/S15-scene-setup-first-loop.md)，历史需求 S02/S05/S07 保留。任务差异已明确；此处细化配置分类，非实现/验收声明。

[总索引](../README.md) · [配置/Profile 唯一主责](../30-contracts/07-task-scene-experiment-config.md)

## 任务差异

| 维度 | LanderPi 导航 | LanderPi 近场测量/操作 | SO101 双臂 |
|---|---|---|---|
| 主要观察 | 地图/定位、本体、按任务选 RGB/Depth/LiDAR | 图像/测量、TCP/本体，3D/点云按实际能力 | 左右臂状态、中央/腕相机 |
| 人工输入 | 底盘控制与受支持目标 | 测量工具或 Joint/TCP，底盘按阶段约束 | 鼠标/受支持示教设备 |
| 专家/策略 | 导航/SLAM/已接通策略 | 几何测量、IK、视觉伺服/抓取按实际任务 | 已接通专家、运动规划或学习策略 |
| 宿主规模 | 到点测试可轻量，持久任务/数采可用完整平台 | Vision Bench、IK Lab 可独立轻量，未要求训练时不强加模型流程 | 专项工作台或完整任务流程 |

## 三张摘要卡与五类配置职责

| 规范名称 | 原称呼/职责 | 何时适用 |
|---|---|---|
| Operator View Profile | UI Observation 的人工可见信息；布局由 Layout Preset 表达 | 人工观察/操作；纯展示改动不隐式改变算法/录制 |
| Policy Observation Profile | 旧 Algorithm Observation；算法消费的流/预处理 | 适用的 Expert/Policy 路径；人工任务未用算法时明确未使用 |
| Recording Profile | 原生流/动作/时间/采样与保存配置 | 录制时必需；纯观察工具不强制录制 |
| Execution Profile | 来源集合、动作接口和受控切换策略 | 执行任务时使用，不与实际 Control Owner 等同 |
| Export Profile | 固定数据版本的格式/转换配方 | 后续导出/训练用途，不属于 M1 场景配置必填 |

前三项是 Scene Setup 的三张摘要卡，不意味着全系统只有三类配置；Execution 可独立分区，Export 在数据出口。一个页面不要求展示五张卡。隐藏相机面板不停止其录制，操作者可见真值不自动进入算法输入。

旧 Task Profile 是承载任务差异的组合建议，新接口改用 Task Template、Execution/观测引用和 Layout Preset，不再保存一个含义不清的平行 Task Profile。历史记录通过版本化映射读取，不反写原文件。

## 独立来源与版本

Human Demonstration、Expert Demonstration、Policy Rollout 是执行意图，录制状态由 Recorder 单独报告；受控接管是来源转换过程，不是第四个持久控制源。原始数据保留实际 Human/Expert/Policy、部件范围、事件与时间，自动脚本不冒充真人。

各 HostApp 通过同一组件/适配约定选择配置，按实验草案注入 store。资源编辑入口可以由不同宿主承载，保存权威和并发修订检查仍属于同一被编辑对象。Scene/Robot/Task/Experiment/ValidatedSnapshot 的边界、单一编辑来源和 Stale 规则全部引用 [配置契约](../30-contracts/07-task-scene-experiment-config.md)，此处不再复制第二套字段。

[Episode/数据来源](../30-contracts/03-episode-events-annotations.md) · [当前阶段](10-first-task-closed-loop.md)
