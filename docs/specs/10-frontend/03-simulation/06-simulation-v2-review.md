# Simulation V2｜删除、替换与待修正项

规范 ID：`FE-SIM-V2-REVIEW` · 责任层：前端设计评审 · 版本：V0.4（2026-10-22）

状态：用户提交图已作为当前参考；下文观察为图片对比，后续行为建议与已确认需求分开。所有结论只针对设计图，不表示产品已实现。

[Simulation 页面](../page-designs/03-simulation.md) · [功能包](README.md) · [S14 来源](../../90-governance/sources/S14-simulation-v2-update.md) · [图片登记](../../references/04-visual-asset-catalog.md)

## 当前图与历史图

![Simulation V2：当前用户提交设计](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

当前主参考：`IMG-022`。[上一版 IMG-003](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0.png) 和 [Policy 参考 IMG-009](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E7%AD%96%E7%95%A5%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0.png) 保留为历史对照。原件不删除，更新的是规范主图引用。

## 逐项对照

| 旧版元素 | 新版处理 | 类型与含义 |
|---|---|---|
| 一个 Simulation Control 栏内的 Start/Pause/Resume/Reset/Stop | 仿真状态、任务执行、录制三个区域 | 替换并拆分。原通用 Stop 不再出现，改为 End Task 与 Stop Recording；暂停物理仍独立 |
| Recording 时间/状态块 | 录制时长和明确的停止录制按钮 | 补充。未录制态的开始入口仍需定义，当前仅画正在录制态 |
| Human/Expert/Policy 与当前控制者合在同一区 | Execution Profile 卡片与 Control Authority 部件表分开 | 替换。运行意图与当前实际控制源不再由同一按钮承担 |
| 一个全局 Take Over 和 Currently Controlling Human | Base/Arm/Gripper 行及接管/交还 | 删除旧全局入口，替换为按部件的入口与状态；按钮适用条件尚需收敛 |
| 视口 Select/Move/Rotate/Scale | Select/Joint/TCP/Layers | 替换。移除在线通用物体 Scale；Move/Rotate 应由 Joint/TCP 工具表达具体语义 |
| 图中的大红框与中文指示箭头 | 页面内标题和中英字段 | 删除设计讲解标记；页面层级由实际界面承载 |
| TCP 位置、位置误差和一个 IK Solved 状态 | Actual State、Target & Preview、IK & Trajectory | 重组并新增姿态、规划/验证状态。TCP 位置/姿态残差没有完整保留，应补回 |
| Controller Status 卡片（Controller、Mode、Tracking Error） | IK/轨迹状态与 Command Feedback | 独立旧卡片被移出；控制器身份、控制方式和跟踪误差仍需在折叠详情中可查看 |
| Joint States 单行当前值 | Joint Monitor 实际值、目标值、误差 | 替换；监控表达更完整，单位与误差计算必须一致 |
| Gripper 开度条与 Open/Close 按钮 | 关节表里的 Gripper 行、Coupled 控制权状态 | 监控保留，手动夹爪命令入口未画出；不据此删除原夹爪控制需求 |
| 来源轨与阶段轨 | 来源、阶段、系统事件三轨 | 新增独立事件轨；混合部件来源、实时与计划仍有表达缺口 |
| 无独立命令完成区 | 最新指令、发送/完成时间及耗时 | 新增；需要绑定指令身份、目标版本、状态及结果时间 |

层级树、3D/Ghost/TCP 虚线、LanderPi 观测区、机器人摘要与原侧栏业务入口总体保留。导航尚未迁移为四组建议，不能因这次页内更新声称全局导航已收敛。

## 后续优先修改

### 1. 执行配置与当前控制权的一致性

图中选中 Human Demonstration，但 Base Owner 为 Expert，Arm 为 Human。这是可以定义的混合行为，却需要明确其语义。候选处理：

- 若本任务从 Expert 开始、后来人工接管臂：Execution Profile 保持 Expert Execution，标记“机械臂人工干预中”；接管本身不切成 Human Demonstration。
- 若确为从头人工示范并允许导航辅助：明确标记“人工示范（底盘专家辅助）”，按部件记录真实来源，不能导出为纯人类示范。
- Profile 是本次尝试的执行意图；部件 Owner 和人工输入设备是实时状态。运行中改 Profile 应有显式转换流程，不能点击卡片即覆盖控制权。

以上选择待任务语义收敛，不修改用户原图的选中状态来假装已经确认其中一种。

### 2. 接管/交还按钮与夹爪入口

图中 Base 为 Expert 时仍出现“交还控制”；Arm 为 Human 时同时有“已控制”和交还。建议按实际状态启用：自动控制下提供申请接管；申请中显示等待/可支持的取消；人工控制且有可恢复来源时提供“交还给 Expert/Policy”；拒绝、超时或不可恢复有具体原因。

Coupled 表示夹爪授权跟随机械臂的候选设计，不代表夹爪开闭自动由 TCP 位姿决定。保留一个清楚的 Open/Close 或开度命令入口，可放在 Arm Inspector 的折叠 Gripper 区；得到对应授权才可用。夹爪行与普通旋转关节分单位显示。

### 3. 实时轴与当前状态必须一致

- 当前游标约 02:34，却画出 03:05 控制权交还与 04:32 任务完成。实际 Live 轨不能把未来事件画成已发生；如需展示计划，用明确的计划轨/虚线；完整历史应进入 Replay 语义。
- Robot Status 显示 Grasp，而当前游标附近阶段轨显示 Place。阶段摘要和轨道必须引用同一时间/同一状态源；手动阶段标记属于注释，不应伪装成改写任务状态机。
- Base Expert、Arm Human 的同时状态无法由一条无范围的来源色带完整表达。建议可展开 Base/Arm/Gripper 子轨，或明确这一行仅显示 Active Arm。
- 顶部录制时长与时间轴录制开始事件需说明各自时钟。若轨道从 Session 00:00 起、录制从 00:12 起，则录制时长不能直接复制 Session 游标时间。
- “添加事件”写入带来源的用户标记；系统事件由后端追加，二者在来源和修改权限上分开。

### 4. 单位、目标和完成反馈

图中关节栏标 °，数值与旧图 rad 示例接近。实现时从声明的单位转换，不能只换列名；误差统一定义为 target−actual 或明确的绝对误差。Gripper 使用其真实角度、宽度或归一化开度，不强行继承整表的 °。

Actual TCP 与 Target TCP 目前不同，Command Feedback 显示 Completed；若这些值属于同一指令与同一时刻就需要解释容差/残差，若是上一指令完成加新草案目标，则需用 Command ID/目标版本/时间区分。补目标残差，IK、规划、验证与执行完成各自绑定对应版本；未接入规划/验证时显示不支持/未验证，不恒绿。

TCP 姿态列明参考系、角度单位和旋转顺序；Joint 数量与 Arm DoF 标签从真实 Capability 生成。预测 Ghost、已验证计划和实际执行轨迹的图例继续细化。

### 5. 控件状态与界面密度

仿真 Running 时禁用重复 Start/Resume，Paused 时才提供 Resume；任务执行时禁用重复 Begin Task；录制收尾时显示 Finalizing 而不是立刻标 Saved。Reset 对任务、旧命令与 Episode 的边界仍按 OQ-004 细化。

保留当前 A–H 布局，将 Execution Profile 卡片折叠为运行摘要以释放视口高度；点云/高级诊断按需展开。侧栏、双语密度、真实模型与观测能力在后续统一原型中核对，不扩展功能范围。

## 图中进展与验收边界

已在图中体现：三类运行状态分区、Profile/Owner 分离、部件授权表、Joint/TCP 工具、目标/实际与命令反馈、事件轨。尚未解决：混合来源语义、按部件时间轴、按钮条件、夹爪输入、单位/目标版本与实时数据一致性。图片更新不能关闭产品验收，也不能证明后端已支持规划或验证。

关联原有验收：TEST-AUTH-003、TEST-JOINT-001、TEST-REC-004、TEST-VIS-002、TEST-CTX-002，均未因本图更新而执行。
