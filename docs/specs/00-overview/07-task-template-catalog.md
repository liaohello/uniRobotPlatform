# 任务模板目录与能力差异

规范 ID：`SYS-TASK-CATALOG` · 责任层：系统 · 版本：V0.6（2026-10-22）

状态：设计草案；S08/S09 是用户提供的分析文本，不自动视为所有细节已确认。Waypoint 范围以 S10 的用户明确选择为准。实现及产品验收均未执行。

来源：[S08](../90-governance/sources/S08-frontend-ia-analysis.md)、[S09](../90-governance/sources/S09-unified-development-reuse-analysis.md)。

[上级目录](README.md) · [总索引](../README.md)

关联需求：[REQ-TASK-001](../indexes/05-requirements.md#req-task-001)

## 模板体系

工作区负责用户流程，任务模板负责实验差异；不为每一种算法复制 Scene Setup 或 Simulation。下列 ID 为稳定命名草案，记录模板版本后才能投入采集，不是当前已提供的运行能力。

| 模板草案 | 目标与输入 | Scene Setup 配置 | Simulation 重点 | 当前成熟度 |
|---|---|---|---|---|
| NAV-POINT | 已知目标位置到点 | 地图、起点、目标、可选朝向 | 估计位置、路线、到达反馈 | 复用现有有限导航，统一适配待验 |
| NAV-ROUTE | 跟随有序路线 | Waypoint 编辑或导入、路线版本、起点 | 当前点、总进度、失败点 | V1 编辑范围已确认，接口待细化 |
| NAV-OBJECT | 搜索语义目标并接近 | 类别/目标描述、允许观测、场景分布 | 检测、搜索、导航与结果 | 概念；不向策略泄漏目标真值 |
| PER-FAR | 远距方向识别 | 距离、朝向、遮挡、背景 | 类别/图像位置、方向及有效性 | 不用单幅 RGB 默认声称精确距离 |
| PER-RGBD | 中距三维定位 | 目标距离/姿态、深度配置 | RGB-D 估计、Frame、误差 | 可靠深度范围及参考点待定 |
| PER-RELATIVE | 近场目标/TCP 相对识别 | 小物体、观察姿态 | 相对变换、时刻与误差 | 位姿能力按真实算法提供 |
| PER-SERVO | 视觉伺服跟踪 | 初态、目标、允许扰动规则 | 视觉误差、控制、失视野/恢复 | 运行期扰动属于独立干预通道 |
| IK-FIXED | 固定底盘 TCP 目标 | 基座、TCP、姿态约束 | IK 残差、候选与实际 | 不承诺任意 6D 目标 |
| IK-BASE-ASSIST | 底盘辅助末端任务 | 障碍、目标、底盘/臂约束 | 候选停靠与后续臂可达性 | 联合约束任务，不是一个规则圆 |
| MOBILE-GRASP | 导航到近场抓取组合 | 子任务/交接条件、观测协议 | 停靠、操作、抓取与保持 | 独立子任务通过不代表组合已通过 |
| BI-DIRECT | 双臂直接抓放/分类 | 方块、容器、责任臂 | 双臂阶段、接触和最终放置 | 以既有工程能力为基线 |
| BI-TABLE-TRANSFER | 台面中转 | 共享落点、退出条件 | 支撑、释放、退让、接收 | 与现有台面中转对应，接入待验 |
| BI-HANDOVER | 空中手递手 | 交接约束、接触/释放协议 | 双臂接触、稳定与交接 | 独立后续模板，不借用中转成功声明 |
| BI-SCREW | 拧螺丝 | 对准/接合/扭矩等条件 | 装配阶段与反馈 | 远期意图，非当前 V1 承诺 |

## 跨模板约束

Operator View、适用的 Policy Observation（旧 Algorithm Observation）、Action/Execution、Recording 和后续 Export 分别绑定版本；按用途决定必需性，三张摘要卡不等于全部配置类型。模板要求某个面板不等于后端已经提供对应算法；缺少能力时呈现原因。

导航、感知、IK、抓取和双臂是可独立验证的任务，不强制每条轨迹从探索开始。PointGoal 的已知目标与 Object Navigation 的语义目标使用不同允许输入；两者不混算同一种成功率。

首批模板启用顺序与精确数值不在此冻结。详细规则见 [任务/实验配置契约](../30-contracts/07-task-scene-experiment-config.md)、[Scene Setup 模板配置](../10-frontend/02-scene-setup/02-task-template-configuration.md)、[任务结果评定](../20-backend/03-observation-algorithms/04-task-assessment.md)。
