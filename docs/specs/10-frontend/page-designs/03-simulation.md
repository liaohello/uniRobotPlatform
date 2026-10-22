# Simulation｜统一在线任务工作台

规范 ID：`PAGE-03` · 责任层：前端页面设计 · 版本：V0.4（2026-10-22）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

使用同一工作台运行 Human Demo、Expert Demo 和 Policy Rollout，观察、干预与录制。

- 页面 ID：`PAGE-03`；导航归属：Run。
- 主要对象：Runtime Session、活动配置快照、部件控制权、Recording、Episode。
- 增量路线：A/B 首条闭环，C/D 增量。这是设计顺序，不是排期或启动实施。

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
