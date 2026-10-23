# Simulation｜统一在线任务工作台

规范 ID：`PAGE-03` · 责任层：前端页面设计 · 版本：V0.7（2026-10-23）

状态：页面详细设计与实施计划约束；统一工作台和可操作 3D 方向有用户依据，具体布局比例/技术适配仍待样板验证。图片是概念稿，不是现有可运行界面的证据。前端实现继续暂停，本轮仅重新规划，见 [S17](../../90-governance/sources/S17-3d-workbench-replan.md)。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

使用同一工作台运行 Human Demo、Expert Demo 和 Policy Rollout，观察、干预与录制。

- 页面 ID：`PAGE-03`；导航归属：Run。
- 主要对象：Runtime Session、活动配置快照、部件控制权、Recording、Episode。
- 当前增量路线：M1 mobileCar Human 四步闭环，M2 bimanual 复用；Expert/Policy 按真实能力后续接入，同一工作台承载。这是范围和设计顺序，不是排期或启动实施。

## 图片参考

![Simulation V2，2026-10-22 用户提交的当前参考](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

主参考：`IMG-022`，用户在 2026-10-22 提交；尚未进入原 PPT。完整布局参考，仍按下文校正示例状态和数据。旧 `IMG-003`（PPT 第 3 页）与 `IMG-009` 为历史参考，见 [旧新对照与后续意见](../03-simulation/06-simulation-v2-review.md)；[S14 来源](../../90-governance/sources/S14-simulation-v2-update.md)。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| A–C 顶部 | 全局摘要、运行/录制工具栏、部件控制来源及显式接管。 |
| D–F 主区 | 层级树、共享 3D/地图主视口、Actual/Target 和命令状态 Inspector。 |
| G 观测区 | LanderPi 按导航/近场配置；SO101 默认中央及左右腕三路 RGB。 |
| H 时间轴 | 在线阶段、来源、事件和录制边界，允许折叠。 |

3D 为主要操作区域；顶部配置、诊断及高级详情可折叠，不能挤掉视口或运行/录制/Owner 反馈。区域关系、首个样板范围与后续集成门槛见 [统一 3D 工作台实施计划](../../00-overview/09-page-design-delivery-plan.md)。主平台采用统一外壳/面板职责，专项轻宿主仍可独立。

## 关键操作与跳转

- 选择执行配置并完成检查；显式启动后端任务。
- 选择对象仅改变选择；先申请对应部件控制权，再使用已允许的 Joint/TCP/夹爪工具。
- Policy/Expert 执行中通过接管按钮申请，收到确认后才开放人工命令；恢复也为显式操作。
- 运行、暂停物理、停止任务与开始/停止录制分别操作，接收后端反馈。
- 结束录制后跳转当前 Episode；Waypoint 只显示进度，不在此编辑。

## 状态、失败与恢复

- 空 Session、Ready、运行、物理暂停、控制权申请中、录制写入/封口与故障分别显示。
- 断连、拒绝、过期和数据陈旧显示具体原因；不凭按钮点击认定执行成功。
- 手动输入期间不因阶段事件强制重排面板；失焦清理持续输入。

## V2 已体现的调整与剩余修正

- 顶部拆分仿真、任务与录制；执行配置与部件控制权分开；通用 Move/Rotate/Scale 改为 Select/Joint/TCP/Layers。
- 实际/目标 TCP、IK/规划/验证状态、关节实际/目标/误差、指令反馈和系统事件轨分别呈现；真实能力与完成状态须由后端提供。
- 当前 Human Demonstration 与 Base Expert 的组合需标人工示范带辅助，或在专家任务接管时保持 Expert Profile；实际 Owner/来源始终按部件记录。
- 夹爪开闭入口和 TCP 残差不能因图中删卡而删除需求；Coupled 的授权与命令含义分别定义。
- 修正实时轴的未来事件、当前 Grasp/Place 不一致、来源轨无法表示混合控制，以及单位/指令版本与完成状态对应关系。
- 运行/接管按钮按真实状态启用；原侧栏导航未变，统一导航方案仍待收敛。详见 [逐项对照与优先建议](../03-simulation/06-simulation-v2-review.md)。

关联冲突：[VIS-C02](../../90-governance/08-visual-design-conflicts.md#vis-c02)、[VIS-C04](../../90-governance/08-visual-design-conflicts.md#vis-c04)、[VIS-C05](../../90-governance/08-visual-design-conflicts.md#vis-c05)、[VIS-C06](../../90-governance/08-visual-design-conflicts.md#vis-c06)、[VIS-C07](../../90-governance/08-visual-design-conflicts.md#vis-c07)、[VIS-C08](../../90-governance/08-visual-design-conflicts.md#vis-c08)、[VIS-C10](../../90-governance/08-visual-design-conflicts.md#vis-c10)、[VIS-C15](../../90-governance/08-visual-design-conflicts.md#vis-c15)、[VIS-C21](../../90-governance/08-visual-design-conflicts.md#vis-c21)。

## 主责功能与后端支撑

- [Simulation A–H 功能区域与任务布局](../03-simulation/04-ah-layout-presets.md)
- [执行配置与模型推理入口](../03-simulation/05-execution-profiles-policy-rollout.md)
- [TCP 操控与虚线运动轨迹](../07-viewport-tools/04-tcp-trajectories.md)

后端/契约：[06-control-authority](../../30-contracts/06-control-authority.md)、[01-ownership-takeover](../../20-backend/02-robot-control/01-ownership-takeover.md)、[01-recorder-events](../../20-backend/04-recording-replay/01-recorder-events.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 修改后续实验配置 | [PAGE-02](02-scene-setup.md) | 从活动快照创建新草案 |
| 查看本条录制 | [PAGE-05](05-episode-detail.md) | 已封口或可读的 Episode ID |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。

下一份可检查前端产物必须能加载固定真实模型、操作观察相机、联动对象树/3D/Inspector，并使用显式 Joint/TCP 工具编辑与取消同源 Target；Actual、Ghost、候选轨迹及目标辅助线的含义可辨。离线/历史/合成数据标明来源，不能显示虚假的 live、执行到位或 Session Ready。只有 TCP 球拖动或新增表单不足以完成该样板。

手柄拖动与 Orbit、单击选择与双击/框选、驾驶键与文本输入必须按 pointerdown 和焦点仲裁。实际命令仍受 Owner、准备态和录制门控；预览/取消不写 Actual，失焦撤销持续输入。沿用 [交互验收](../../40-verification/01-interaction-acceptance.md) 及 [工作区验收](../../40-verification/02-workspace-runtime-acceptance.md)，不增加一套重复 TEST 编号。

本轮工程方向为 React + TypeScript 外壳、Three.js SceneView 适配，Dockview 先验证尺寸/焦点/生命周期。详细适配边界在实施计划维护，不从图稿推断技术库或 API 已实现。Human/Expert/Policy 的部件控制源、仿真/任务/录制三域及只读历史回放始终保留在整体架构内。
