# 执行配置与模型推理入口

规范 ID：`FE-SIM-EXECUTION` · 责任层：前端 · 版本：V0.4（2026-10-22）

状态：设计草案；S08/S09 是用户提供的分析文本，不自动视为所有细节已确认。Waypoint 范围以 S10 的用户明确选择为准。实现及产品验收均未执行。

来源：[S08](../../90-governance/sources/S08-frontend-ia-analysis.md)、[S09](../../90-governance/sources/S09-unified-development-reuse-analysis.md)。

[上级目录](README.md) · [总索引](../../README.md)

关联需求：[REQ-EXEC-001](../../indexes/05-requirements.md#req-exec-001)、[REQ-IA-003](../../indexes/05-requirements.md#req-ia-003)

## 三种执行配置

| Execution Profile | 默认控制来源 | 录制与干预 |
|---|---|---|
| Human Demonstration | Human | 录制独立启停；记录输入设备与辅助生成器 |
| Expert Demonstration | Classical Expert | 可录制，可显式接管 |
| Policy Rollout | Learned Policy | 可录制，可显式接管，模型与解码版本绑定 |

执行配置、当前部件控制源、录制状态、任务阶段、物理扰动分别表达。选择三种配置之一不自动创建 Episode、不自动取得控制权。混合控制按部件记录，是否允许并行动作仍由后端约束。

## 模型推理流程

Training/Model Registry 选择 Checkpoint → 携带模型/推理配置与任务引用进入 Simulation → 核对机器人/观测/动作兼容性 → 显式准备/加载 → 用户启动 → 运行、接管与可选录制 → 进入 Data 或 Evaluation。

跳转和选模型不等于执行；不在 Training 页面再实现一套遥操作工作台。VLN 的输出可能是目标/局部速度/高层指令，VLA 可能是关节/TCP 动作，Policy Adapter 必须显式声明接口，不强行对齐成同一个匿名动作向量。

## 接管与恢复

遵循 [控制权契约](../../30-contracts/06-control-authority.md)。接管时使对应控制范围旧 Action Chunk 失效，后端确认后才启用人工工具；物理可继续。恢复必须明确从新观测重新决策或按声明策略状态恢复，不盲目重放剩余动作。只有连续录制且没有 Reset/终止/写入故障时，接管前后才保留同一 Episode 并记边界；不能无条件拼接。

验收：[TEST-EXEC-001](../../40-verification/04-task-config-workflow-acceptance.md#test-exec-001)、[TEST-IA-002](../../40-verification/04-task-config-workflow-acceptance.md#test-ia-002)。

## V0.3 统一在线入口与离线诊断

素材中 Online Rollout 的控制/录制面板合并为 [Simulation 页面](../page-designs/03-simulation.md) 的 Policy 预设；不在训练/推理/评估页建立第二套独立运动命令通道。评估的只读预览复用同一 Session 的状态；接管跳转统一工作台。

[Offline Inference](../page-designs/10-offline-inference.md) 是后续候选诊断视图，只生成预测结果，不执行动作；固定输入快照、模型/预处理版本及输出语义。缺本体/历史/其他必需字段时不把单图上传当完整策略输入。真机页仅作后续参考。

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。

## V0.4 Profile 与部件 Owner 的区别

新图把 Execution Profile 与按 Base/Arm/Gripper 的控制权分开，作为当前视觉方向。专家任务中接管 Arm 不自动把任务起源改为 Human Demonstration；若人工示范允许专家辅助底盘，必须显式注明辅助并保留部件来源。当前图的选中组合是待解释示例，不冻结混合语义。

Profile 卡片不能直接绕过接管协议覆盖运动。点击行为、运行中转换与按钮适用条件见 [V2 评审](06-simulation-v2-review.md)，依赖 OQ-017/018/046。
