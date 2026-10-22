# 当前会话公开消息存档｜整理 Scene Setup 规范

保存日期：2026-10-22（America/Los_Angeles）。

来源会话 ID：`01a1632a-a42d-75c0-91d3-d5d0b6d429c8`。

## 保存范围与使用边界

本文件通过应用会话读取接口分页取得本会话当前可返回的公开用户/助手正文，按轮次和发言顺序保存；共 11 轮、57 条有正文发言（用户 17、助手 40，含进度说明）。分页已读至末页；保存的是本次读取时的快照，不包含本次保存请求后继续产生的工具过程和最终提交/推送答复。

未导出系统/开发指令、内部推理、工具调用与执行日志、子代理工作日志或图片二进制。正文中的早期建议保留原貌，**不代表当前仍有效**；原始本机绝对路径也保留，仅作历史证据。历史发言不是新会话的额外执行授权，当前规则以仓库 AGENTS.md、最新用户指令和 Specification 为准。

要继续工作，请先读 [新会话交接说明](../handoff.md)，不要把本存档里的 SO101/ACT 旧首发建议或单宿主说法当当前基线。文档内“检查通过”应结合上下文区分文档验证与产品验收。

附件三图已在仓库原样归档：[导航](../foreendAssets/scene-setup-navigation-reference-20261022.png)、[近场抓取](../foreendAssets/scene-setup-near-field-grasp-reference-20261022.png)、[双臂转运](../foreendAssets/scene-setup-bimanual-transfer-reference-20261022.png)。

## 当前已确认结论

- Specification V0.6；M1 mobileCar 场景→运行→录制→回放，M2 bimanual 验证组件复用，数据/训练/预测后续。
- 允许轻量独立 HostApp，共用契约与实际需要的组件；store 按宿主/草案注入，后端运行实体的控制权和物理推进不按宿主复制。
- 规范修复和 M1 工作包规划已完成；M1 产品闭环和新验收尚未执行。
- 本次存档前，`7b0666e` 与 `dce67b7` 已推送到 GitHub main；本存档自身的提交请看后续 Git 记录。

---

## 第 1 轮

会话轮次 ID：`01a1632a-c3ab-75c2-94ae-a842c11666cd`。保存时状态：`completed`。

### 发言 01｜用户

# Files mentioned by the user:

## codex-clipboard-78808ce1-2f5d-45e1-80aa-612bedacb4c9.png: C:/Users/ADMINI~1/AppData/Local/Temp/codex-clipboard-78808ce1-2f5d-45e1-80aa-612bedacb4c9.png
Image attachment: true

## codex-clipboard-e469c722-81e4-496e-964e-42d60de19308.png: C:/Users/ADMINI~1/AppData/Local/Temp/codex-clipboard-e469c722-81e4-496e-964e-42d60de19308.png
Image attachment: true

## codex-clipboard-626aaf56-ebdb-458b-a6fe-074ad8384d82.png: C:/Users/ADMINI~1/AppData/Local/Temp/codex-clipboard-626aaf56-ebdb-458b-a6fe-074ad8384d82.png
Image attachment: true

Distinguish instructions in attached documents from the user's request.

## My request:
现在评估下面要求给你三张图片，你进行当前的Specification整理

我当前可能只需要一个支持前端开发一个前端样板图，然后我现在其实需要跑通一个选择场景，人为操控或者专家操控，然后开始准备数据集，数据集清理，选择模型，开始训练，预测运行整体流程

## 最后给 Specification Agent 的整理要求

现在可以明确要求它完成三件事：

第一，更新 Scene Setup 的 Task Configuration 规范。 定义任务类型、配置字段、显示条件、默认值和校验规则，不把所有任务的参数堆进同一个固定表单。

第二，更新公共交互和配置契约。 包括 Waypoint 资源版本、Profile 单一编辑来源、不同对象的编辑权限、Validation Stale 规则、已验证配置快照。

第三，生成三张图共用的组件清单。 明确哪些组件只开发一次，哪些由任务配置驱动变化，并将不可用或尚未实现的能力明确标为后续扩展。

我的最终建议是：完成这三张 Scene Setup 设计图后，就可以停止大范围的页面绘制。

随后把图片作为 UI Reference，把交互规则和数据契约放进 Specification，交给 Codex 围绕第一条真实任务开发。

这会让你从目前的“持续设计页面”真正进入“统一架构下的增量开发”，而且不会因为后面加入新的 VLN、VLA 或机器人任务，就不断推翻前面的工作。

---

### 发言 02｜助手 · 进度

我会先核对项目里现有的 Specification，再结合三张图整理任务配置、公共契约和共享组件，并把第一条数据采集到训练、预测的流程收敛成可开发范围。

---

### 发言 03｜助手 · 进度

三张图适合归为同一个 Scene Setup 页面：共用外壳，按导航、近场抓取、双臂转运切换配置。

现有工程也有一个需要写清的边界：部分能力仍停留在目录声明，训练资格尚未通过。Specification 会区分“可演示的前端流程”和“已接通的真实能力”，并把最小训练、预测闭环提到当前开发目标中。

---

### 发言 04｜助手 · 进度

核对本地工程证据后，我建议把 **SO101 台面转运**作为首条完整闭环：已有专家示范、数据格式验证和 ACT 训练产物可复用。LanderPi 近场抓取可作为后续适配，其现有数据仍有训练资格缺口。

这只是首任务建议，会在规范中明确标注。现有 ACT 开发测试为 0/20，也会如实保留，分别验收“流程跑通”和“策略任务表现”。

---

### 发言 05｜助手 · 进度

任务字段表、共享组件清单和版本/权限契约已整理到规范中。接下来会统一旧路线与新范围，并检查文档链接和需求追踪。

配置规则已明确：保存草案、验证通过、创建 Session、开始执行是四个独立动作；影响执行的修改会使验证过期，已创建运行继续使用原快照。

---

### 发言 06｜助手 · 进度

已把最小训练与预测前移到首条任务，并补上清理、同源数据划分、数据版本、训练产物和预测回放的验收条件。

还补充了一个关键限制：历史 ACT 使用混合任务数据，不能直接视为转运任务可用策略。真实接入时需固定转运数据、配置和代码版本，用本次训练所得权重完成一次预测运行，才算完整流程验收。

---

### 发言 07｜助手 · 进度

文档一致性检查已通过：新增的 9 项需求、12 项待执行验收，以及图片、来源和规范索引都能相互追踪，参考图片哈希也匹配。

当前交付是 Specification V0.5。它明确了样板演示与真实流程各自的验收边界；产品运行和训练仍待后续开发执行。

---

### 发言 08｜助手 · 答复

已更新为 **Specification V0.5**，三张图统一为同一页面的任务变体，完成三项整理：

- [任务配置规范](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/10-frontend/02-scene-setup/02-task-template-configuration.md)：按任务定义字段、显示条件、建议默认值和校验。
- [公共配置契约](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/30-contracts/07-task-scene-experiment-config.md)：明确路线版本、Profile 唯一编辑入口、对象权限、验证过期与配置快照。
- [共享组件清单](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/10-frontend/02-scene-setup/05-shared-scene-components.md)：区分共用组件、任务驱动变化和后续扩展。

[当前开发基线](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/00-overview/10-first-task-closed-loop.md)已收敛为：**先交付一个可交互前端样板，再接通场景选择→人工/专家采集→清理→数据版本→训练→预测运行**，停止大范围补图。

首任务建议采用 **SO101 台面转运＋专家采集＋ACT**；这是建议，历史模型表现限制已保留。

文档一致性检查通过。本轮仅整理规范与参考素材，未执行仿真或训练。

---

## 第 2 轮

会话轮次 ID：`01a16343-052b-7801-bd4e-98b664ffad35`。保存时状态：`completed`。

### 发言 09｜用户

当前项目规划是否已经读取参考了对话 分支 · 整体大前端继续讨论细化？

---

### 发言 10｜助手 · 进度

我会核对 Specification 的来源记录，确认是否读取过这段对话，以及实际取得了哪些内容。

---

### 发言 11｜助手 · 答复

**已经读取并参考过，但没有完整取得全部对话内容。** 刚核对的[来源档案 S11](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/90-governance/sources/S11-design-discussions.md:7)记录：

- 读取了「分支 · 整体大前端继续讨论细化」及父对话，各取得 **5 条用户消息**。
- 助手回复只返回内容占位，**未取得完整正文**；生成图片通过本地图片和 PPT 补充参考。
- 已吸收“统一前端架构、任务逐个实现、复用成熟组件、保留现有仿真后端”等原则。

因此，当前规划参考了其中可取得的需求与材料，不能声称完整吸收了所有讨论。

另外，历史对话曾提出 **mobileCar／LanderPi 近场操作优先**；上一轮改为建议 **SO101＋ACT**，是我根据完整训练闭环的工程证据提出的新建议，**不是你在原对话中已经确定的选择**。

---

## 第 3 轮

会话轮次 ID：`01a16345-3f16-7f82-8f37-d5092e76a164`。保存时状态：`completed`。

### 发言 12｜用户

当前对于 项目 C:\Users\Administrator\Desktop\embodied_intelligence_proj\mujoco_learning
C:\Users\Administrator\Desktop\embodied_intelligence_proj\bimanual_proj
C:\Users\Administrator\Desktop\embodied_intelligence_proj\mobileCar
三个项目而言，我需要做一定的迁移和取舍，我是已当前已经定好的specification来作为参考然后去规划每个项目的前端开发，还是我开发一个统一前端，然后将别的项目迁移到我这个系统项目中来？

---

### 发言 13｜助手 · 进度

我会结合三个项目现有的接口和运行边界，判断哪些适合保留、哪些需要适配，再给出统一前端与迁移的建议。

---

### 发言 14｜助手 · 进度

核对结果支持“统一前端、逐步接入现有能力”：mobileCar 已有较完整的小车控制与采集接口，mujoco_learning 的视觉和 IK 实验适合选择性接入。它们的协议、模型和运行环境有差异，需要保留边界。

当前平台已有任务目录和启动网关，但还没有完成 Specification 中的统一场景配置、控制、数据和训练流程。后续开发应集中在这套统一界面及其适配层。

---

### 发言 15｜助手 · 答复

**建议以当前 Specification 为共同目标，在 `uniRobotPlatform` 开发一套统一前端，再按任务逐步接入三个项目。迁移先从功能和操作入口开始，代码与运行环境可以继续独立。**

具体做法是：统一前端骨架与第一条真实任务的适配同步推进，跑通后再扩展下一条任务。

```mermaid
flowchart TD
    UI["uniRobotPlatform：统一前端"] --> P["平台服务：配置、会话、数据和模型管理"]
    P --> A["适配层：转换各项目的接口与数据"]
    A --> M["mobileCar：小车控制与采集"]
    A --> B["bimanual_proj：双臂、专家与训练"]
    A --> L["mujoco_learning：视觉、IK 等专项能力"]
```

**三个项目后续的开发职责，应这样划分：**

| 项目 | 建议定位 | 后续重点 |
|---|---|---|
| `uniRobotPlatform` | 唯一长期维护的产品前端 | Scene Setup、Simulation、数据清理、训练与预测流程，以及共享组件和状态 |
| `mobileCar` | 小车运行与采集后端 | 保留控制器、导航、录制及已有协议，补统一平台需要的接口 |
| `bimanual_proj` | 双臂任务与学习后端 | 保留仿真、专家、任务判定、数据出口、训练和推理，逐步接入平台 |
| `mujoco_learning` | 算法实验与专项能力来源 | 选择性接入视觉、IK、估计与诊断能力，保留有价值的实验工具 |

旧前端可以继续承担调试和专项验证。对应流程在统一前端接通并验收后，再决定退役哪些旧操作入口。这个方向与已有的[三项目适配边界](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/20-backend/07-existing-project-adapters/01-integration-boundaries.md)一致。

**Specification 应作为共同的产品契约使用。**

例如，“移动目标物体→验证配置→创建 Session”这套交互只在统一前端开发一次；各项目负责解释配置、检查能力、初始化场景并返回真实结果。各项目需要的是自己的**接口适配计划和能力差异表**，无需再各做一套 Scene Setup 页面。

同时，当前 Specification 中标为“建议”的默认值、模型和首任务仍可根据接入结果调整。已有可用后端遇到图稿中的未实现能力时，应明确显示限制，再决定是否补能力。

**迁移顺序建议分四步：**

1. **盘点能力与差异。** 明确每项功能由哪个项目提供、接口是什么、数据如何转换、目前缺什么。
2. **建立统一骨架，接通一条真实任务。** 从配置、操控、采集一直做到清理、训练和预测。
3. **逐项迁移用户操作。** 新功能集中进入统一前端，原项目主要补算法、运行能力和适配接口。
4. **最后决定代码抽取。** 只有接口稳定、确有复用收益的模块才迁入共享包；仿真核心、训练环境、ROS 环境按兼容要求保留。

对 `mobileCar` 和 `mujoco_learning` 的重叠能力尤其需要取舍：建议小车日常控制与采集优先由 `mobileCar` 承担，视觉和 IK 专项能力从 `mujoco_learning` 选择性接入；同一次运行明确选定后端，每个仿真实例只有一个物理推进者。

当前仓库的[迁移清单](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/backend/migration_manifest.json)也采用分阶段接入方向。不过现有平台主要还是任务目录和启动网关，接下来真正要建设的是统一交互与完整数据流程。

---

## 第 4 轮

会话轮次 ID：`01a1634a-56e0-7ce3-8515-1e1fde8bf250`。保存时状态：`completed`。

### 发言 16｜用户

你可以开子agent 也就是gpt 6luna的子agent帮你去查找哪些项目的关键信息

并且其实对于每个项目我想做的观察其实也有不同，或许应该是设定良好的specification作为参考然后分别开始开发前端？

比如小车近端视觉测量，我需要的前端可能比较简单，不需要这么复杂的前端，另外小车的IK变换监测也同理可能只是一个3D操作台可以让我测试功能即可

导航可能会复杂，所以开发一个统一前端是否会导致后续的成本变大，因为我有些项目用完前端基本上前端就无用了？

值得优先补齐的是：

- **宿主与状态作用域**：组件可共享，store 实例应由各宿主注入；“唯一编辑来源”限定到具体实验草案。
- **场景数据所有权**：Scene 保存基础布局，Experiment 保存实例覆盖；明确哪些字段由谁写、如何解析到最终快照。
- **数采接入契约**：定义开始、追加、结束、失败保留，以及各工程原始记录如何被索引和读取。
- **模型 IO 契约**：把观测、动作、时间对齐、预处理和归一化变成可检查的结构。
- 这些补全是什么意思？

---

### 发言 17｜助手 · 进度

我会让子 agent 分别核对视觉测量、IK、导航和双臂工作台的实际边界，重点判断哪些适合轻量实验界面、哪些需要完整流程。再结合你的例子解释这四项契约，区分现在必需的规则和可以后补的抽象。

---

### 发言 18｜助手 · 进度

子 agent 的核对支持你说的差异：Vision Bench 和 IK Lab 已有各自明确的实验边界，近端测量和 IK 测试可以保留轻量界面。上一轮我把“唯一长期前端”说得过于绝对；更合适的是共享必要的契约，让轻量实验工具和完整平台分别承载各自的流程。

mobileCar 也已经实现了录制开始、追加、收尾和失败保留的核心逻辑。“补契约”主要是明确统一平台如何接入这些记录，不需要重写录制器。

---

### 发言 19｜助手 · 答复

已让 **3 个 GPT-6-luna 子 agent** 分别核对视觉/IK、小车导航数采、双臂工作台。

**你的顾虑成立。上一轮“唯一长期前端”的说法过于绝对，应该收窄为：共享必要的规范和组件，各任务可以有不同规模的界面，完整平台只是其中一种承载方式。**

对于临时实验，平台化确实可能增加配置、状态管理、部署和维护成本。

| 用途 | 更合适的界面 | 按需增加 |
|---|---|---|
| 近端视觉测量 | 图像、标记叠加、测量值、坐标系、有效性和误差 | 样本保存、结果比较 |
| IK 功能测试 | 3D 操作台、目标手柄、求解/执行状态、TCP 误差 | 轨迹保存、批量测试 |
| 导航 | 简单到点测试可轻量；长期运行可进入平台 | 地图/路线版本、接管、录制和回放 |
| 采集→清理→训练→预测 | 完整平台流程 | 更多任务和模型 |

这也符合现有工程：Vision Bench 和 IK Lab 已有独立边界，IK Lab 明确排除了 RGB-D、SLAM、训练等范围。可以保留这些工具，分别完善其小型 Specification。[视觉工作台说明](C:/Users/Administrator/Desktop/embodied_intelligence_proj/mujoco_learning/docs/landerpi_vision_bench.md)、[IK Lab 说明](C:/Users/Administrator/Desktop/embodied_intelligence_proj/mujoco_learning/docs/landerpi_ik_lab.md)

你列出的四项“补全”，主要是在说明**界面可以独立，但数据和状态不能含糊**。

**1. 宿主与状态作用域：明确“这个组件正在操作哪一次实验”。**

“宿主”就是承载工具的应用，例如独立 IK 页面、视觉测试页或完整平台。`store` 可以理解为这次实验的前端状态容器。

同一个位姿编辑组件可以被这些应用复用，但状态由各应用传入：

- IK 页面保存自己的目标、选中对象和预览结果。
- 视觉页面保存自己的测量设置。
- 平台保存某个实验草案。

因此，“唯一编辑来源”应理解为：**同一个实验草案只有一份权威状态**，而不是所有工具共用一个全局 store。实时机器人状态仍以后端为准；两个界面编辑同一草案时，还要检查版本冲突。

这项应该较早明确，因为它直接决定组件能否独立使用。

**2. 场景数据所有权：明确“改的是公共场景，还是本次实验”。**

例如基础 Scene 保存桌面和方块的默认布局：

- 实验 A 把方块移到左侧。
- 实验 B 把方块移到右侧。

A、B 应保存各自的实例覆盖，基础 Scene 保持原样。只有显式“保存为场景新版本”，才修改公共资源。

运行前再解析：

`固定版本的 Scene + Robot 配置 + 本次 Experiment 覆盖 → 最终运行快照`

需要补齐的是：允许覆盖哪些字段、由哪个入口修改、冲突时谁优先，以及随机化何时生效。运行中的实际位置另行记录，不反写初始配置。

这可以避免一次视觉测试拖动方块后，其他实验的默认布局也被改掉。

**3. 数采接入契约：明确“一次记录怎样开始、怎样完整结束、失败后还剩什么”。**

它至少回答：

| 环节 | 必须说明 |
|---|---|
| 开始 | 记录身份、任务/初态、数据来源、采集配置，何时确认开始成功 |
| 追加 | 观测、动作、时间、序号和媒体文件怎样关联 |
| 结束 | 如何排空写入、生成索引、标记完整性 |
| 失败 | 保留哪些文件，哪些数据缺失，能否回放或用于训练 |
| 读取 | 平台如何找到、列出并只读读取原工程记录 |

这里的“追加”是录制器的职责，**不要求浏览器逐帧上传数据**。

mobileCar 已实现相当一部分生命周期，接入时应复用。[现有录制器](C:/Users/Administrator/Desktop/embodied_intelligence_proj/mobileCar/src/mobilecar/data/recorder.py)  
双臂采集则有不同语义：失败尝试会留下原因和诊断，但未成功的 LeRobot episode buffer 会被丢弃。因此，“有失败日志”与“保留了完整失败轨迹”必须分别标明。[双臂采集逻辑](C:/Users/Administrator/Desktop/embodied_intelligence_proj/bimanual_proj/src/bimanual/recording/collection.py)

原始格式可以继续保留，平台先通过索引和读取适配器接入。

**4. 模型 IO 契约：明确“模型究竟吃什么、输出代表什么”。**

只记录模型名称“ACT”远远不够，还需要检查：

- 输入哪些相机、图像尺寸/颜色顺序、状态维度与关节顺序。
- 图像、机器人状态和动作如何按时间对齐。
- 动作是绝对目标还是增量，单位是什么。
- 图像如何裁剪/缩放，数据如何归一化，推理时使用哪份参数。

一个实际差异是：mobileCar 近场动作采用关节 **rad**、夹爪开口 **m**；双臂公开特征使用关节 **degree**、夹爪 **percent**。这些数据即使维度相近，也不能直接混用。[小车动作约定](C:/Users/Administrator/Desktop/embodied_intelligence_proj/mobileCar/docs/g4a1_report.md)、[双臂特征约定](C:/Users/Administrator/Desktop/embodied_intelligence_proj/bimanual_proj/src/bimanual/types.py)

这项主要在训练和预测接入前补齐。纯几何视觉测量、传统 IK 测试可以先定义自己的输入输出，不必提前建设完整模型管理。

所以，当前 Specification 更适合分成：**少量公共契约、各实验工具的专项规范、完整平台的流程规范**。视觉和 IK 可以先分别开发轻量界面；出现实际共享需求时再抽组件。现有 IK 使用 Viser，也没有必要仅为统一技术栈而重写。

---

## 第 5 轮

会话轮次 ID：`01a1639d-e455-73d3-9eea-53622f9c9a6c`。保存时状态：`failed`。

### 发言 20｜用户

那对于当前不同的项目我全部建在一个github 仓库是否合理？共享组件的方式的话，能给我画一个系统逻辑图么？开多个agents进行所有项目扫描可以读取C:\Users\Administrator\Desktop\embodied_intelligence_proj\uniRobotPlatform\AGENTS.md

---

### 发言 21｜用户

所以其实本质上来说，当前前端只是一个操作终端，后面运行的只是业务，仿真器部分固定
整体来说就类似于一个操作平台+一系列的操作资源+仿真器
还属于一个项目？

---

### 发言 22｜助手 · 进度

我会先读取你指定的 AGENTS.md，再并行核对几个项目的目录、依赖和运行边界。随后给出仓库组织建议，并画出“操作平台—任务资源—业务执行—仿真器”的逻辑图，区分哪些可以共享、哪些需要独立运行。

---

## 第 6 轮

会话轮次 ID：`01a163bb-3b92-7572-a841-2607e87265e8`。保存时状态：`completed`。

### 发言 23｜用户

喔喔我好像明白了这个前端确实就像是**任务控制台**  对么？行我大致有些清楚了先用 mobileCar 把“场景→运行→录制→回放”这条最短闭环跑通，再用 bimanual 验证组件复用；现在我可能需要你确定下面specification存在的问题进行审核，然后梳理一遍当前的specification是否存在矛盾和冲突，可以开多个agent进行辅助审核

##

我把当前 `docs/specs` 的 147 篇文档重新对了一遍。**索引本身已经同步**：`catalog.json` / `traceability.json` 都是 0.5，87 条 REQ、25 张独特图、2,411 条链接都一致。剩下的冲突主要是**同一个对象被不同文档定义成了不同东西**，不是索引漏登记。

## 8 处值得改的冲突

| **#** | **冲突**                                 | **文档 A 说**                                                       | **文档 B 说**                                                                                                                                           | **影响**                                                 |
| :---- | :------------------------------------- | :--------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------- |
| 1     | **Scene 是否包含物体布局**                     | `CT-EXPERIMENT-CONFIG`：Scene 含“桌台/障碍/**物体布局**”                   | `02-task-template-configuration`：Scene 只是环境与资产，**初态由 Experiment 声明**；`05` 的 `ExperimentDraftStore` 持有初态                                              | 物体位姿有两个“家”；改场景和改实验会互相覆盖，Stale/版本判不清                    |
| 2     | **Profile 是 3、4 还是 5 个**               | `SYS-PROFILES`：必须分开的**三份**配置（UI/Algorithm/Recording）             | `CT-EXPERIMENT-CONFIG`：Operator/Policy/Recording **+ Execution + Export = 5**；`02` 又写成 **4** 个，且用旧名 Algorithm Observation                            | 组件不知道该渲染 3 张还是 5 张卡；`ProfileKind` 无法定                  |
| 3     | **Episode 引用哪套配置**                     | `CT-EPISODE` 正文：Task Profile + Algorithm Observation + Recording | 同一篇的 V0.2 补充：Task Template + Execution + Operator View，**旧段没删**                                                                                      | Episode 到底绑定哪套对象没有唯一答案，数据 lineage 会分叉                  |
| 4     | **Workspace 是 6 个还是 4 组**              | `SYS-PRODUCT` / `FE-SHELL-NAV`：**六工作区**                          | `README` / `DEC-037`：**四导航组**（Home + 四业务组 + Resources）；`SYS-GLOSSARY` 把 Workspace 定义为“导航入口”；`05` 又有 `WorkspaceShell` 组件                              | “Workspace”同时指导航组、逻辑工作区、页面状态、组件；4/6 计数无法判定             |
| 5     | **Scene 这个对象叫什么**                      | `SYS-STATE`：**Scene Document**                                   | `BE-SCENE-CONFIG`：**Scene Draft**；`CT-EXPERIMENT-CONFIG`：**Scene**；`05`：**ExperimentDraftStore**                                                     | 同一个可编辑对象四种叫法，组件接口和落盘对象对不上                              |
| 6     | **`prepared` Session 没有状态域**           | `CT-EXPERIMENT-CONFIG`：创建只产生 **prepared 的未开始 Session**           | `SYS-STATE` 的状态域只有 Workspace / Scene Document / Simulation / Task / Recording / Control / Interaction / Execution Policy，**没有 Session，也没有 prepared** | `prepared` 属于 Simulation、Task 还是 Session 不明；UI 状态机无法实现 |
| 7     | **Collection 与 Dataset Version 边界未定义** | `PAGE-06`：主要对象是 **Collection、筛选快照、Dataset Version**              | `PAGE-07` / `CT-LINEAGE`：只定义 **Dataset Version**，没有 Collection                                                                                       | Collection 是动态查询还是冻结版本、和 Version 谁包含谁，没有契约             |
| 8     | **两处数字陈旧**                             | `indexes/05-requirements.md` 顶部：**72 项**（原 56 + 新增 16）           | 实际 **87 条** REQ                                                                                                                                      | 读者或脚本按 72 核对会误判                                        |
| 8b    | 同上                                     | `references/04-visual-asset-catalog.md`：**23 PNG / 22 独特内容**     | `visual-assets.json`：**26 文件 / 25 独特内容**                                                                                                             | 图片核对和覆盖率会算错                                            |

## 还有一处不是“文档互相打架”，而是“规范和你现在的目标不一致”

- `10-first-task-closed-loop.md` 写的是：**“一个前端工程、一套共享组件、三种 Setup UI 变体”**。
- `05-shared-scene-components.md` 写的是：**“三图不各做一套 Shell”**，以及“跳转唯一 Simulation 工作台”。
- `01-visual-design-rules.md` 写的是：**“Run | 唯一在线运动/接管工作台”**。

这些在“一个前端应用”的前提下是自洽的；但你的目标是**三个工程各自有前端、复用组件**。所以这不是文档之间的逻辑矛盾，而是**规范还停留在单宿主模型**。要改成三宿主，就必须引入 `HostApp`，把所有“唯一/全局”限定为“每个 HostApp 内唯一”。

---

### 发言 24｜助手 · 进度

对，可以把前端理解为“任务控制台”；视觉测量和 IK 工具则可以是更轻的专项控制台。你现在确定的顺序是：先用 mobileCar 跑通“场景→运行→录制→回放”，再用 bimanual 验证组件复用。

我会按 AGENTS.md 进入只读 Specification 审核，逐项核对你列出的冲突，也检查这些问题对首条闭环的实际影响。审核中会特别区分：界面状态可以按宿主隔离，真实运行实例的控制权仍须由后端统一裁决。

---

### 发言 25｜助手 · 进度

初步核对后，这份清单需要分开处理：Scene/Experiment 的写入归属、Episode 的当前引用集合确实需要收敛；“四组导航与六工作区”已有映射，图片的旧数字也已标为历史统计，不能直接算作硬冲突。

另有一项比计数更影响当前开发：V0.5 仍以 SO101＋ACT 训练闭环为首阶段建议，尚未反映你现在明确选择的 mobileCar 最短闭环。

---

### 发言 26｜助手 · 答复

对，**“任务控制台”是合适的定位**。当前顺序以你这次明确的决定为准：mobileCar 先跑通“场景→运行→录制→回放”，再用 bimanual 验证组件复用。

已由 3 个 Luna 子 agent 辅助检索，并核对主责规范。**审核结论：PASS WITH ISSUES。** 架构可以保留，但现有 V0.5 尚不能直接作为这条 mobileCar 首阶段的冻结实现规格。

你列出的内容中，部分是实际缺口，部分是层次关系或历史统计，不能全部按硬冲突处理。

| 用户项 | 审核判断 | 影响与最小修正 |
|---|---|---|
| **1＋5：Scene、初态与多种草案名称** | **P1：所有权和对象关系未闭合** | Scene 可以合理地包含默认布局，Experiment 可以保存本次覆盖，二者并不天然矛盾。但目前缺少覆盖、保存和解析规则。应明确：`SceneVersion` 保存基础布局；`SceneDraft` 编辑场景资源；`ExperimentDraft` 保存实例覆盖；`ExperimentDraftStore` 只是前端状态容器；最终解析成不可变运行快照。不能把四者简单视为同一个对象的别名。[配置对象定义](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/30-contracts/07-task-scene-experiment-config.md:17)、[草案 Store](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/10-frontend/02-scene-setup/05-shared-scene-components.md:31) |
| **2：Profile 是三、四还是五个** | **P1：分类与名称需要统一，数量本身不矛盾** | 三张卡对应 Operator View／Policy Observation／Recording；Execution 管执行方式，Export 管数据出口，不需要同时渲染成五张卡。应建立“规范名称、旧名、所属阶段、何时必需”的表，并消除含义过宽的旧 `Task Profile`。[当前契约已区分这些职责](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/30-contracts/07-task-scene-experiment-config.md:34) |
| **3：Episode 引用集合** | **P1：当前完整集合不明确** | 同文后段写“增加”，可以解释为扩展，但正文、补充和 lineage 没有合成唯一的当前要求。建议明确 Episode 必须绑定 Session 与已解析配置快照；具体资源/Profile 版本由快照解析，冗余索引不得成为另一份权威配置。模型、路线等按任务条件记录。[Episode 正文与补充](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/30-contracts/03-episode-events-annotations.md:19)、[快照引用要求](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/30-contracts/05-dataset-model-lineage.md:51) |
| **4：六工作区与四导航组** | **P2：术语混用，不是数量冲突** | 已有“四导航组承载六逻辑工作区”的映射。应分别使用 Navigation Group、Workspace、Page/View；`WorkspaceShell` 是组件，不参与业务区数量统计。[现有映射](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/10-frontend/01-shell/01-navigation-context.md:50) |
| **6：prepared Session** | **P1：总览状态表未同步，不能说完全没有定义** | 后端生命周期已明确 prepared、创建与 Start 分离。缺的是 SYS-STATE 中 Session 生命周期与 Simulation／Task 状态的对应关系。补齐状态归属和合法转换即可，无需重新发明状态机。[总览状态表](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/00-overview/04-runtime-state-domains.md:20)、[后端已有定义](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/20-backend/01-session-scene/01-session-lifecycle.md:44) |
| **7：Collection 与 Dataset Version** | **P1，后续数据阶段收敛** | 页面要求区分动态查询与固定成员，但没有定义冻结规则。建议 Collection 表示可编辑的组织/选择，Dataset Version 表示某次解析出的不可变成员与处理清单；集合更新不修改旧版本。它不应阻塞当前录制回放切片。[Collection 操作](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/10-frontend/page-designs/06-dataset-collections.md:33)、[版本关系](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/30-contracts/05-dataset-model-lineage.md:21) |
| **8：72 与 87 条需求** | **P2：当前总数展示不足** | 顶部明确写的是“V0.2 共72项”，并非当前数据算错。应在顶部补当前87项，历史统计保留。[原文](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/indexes/05-requirements.md:3) |
| **8b：图片数量** | **不是活跃矛盾** | 23／22 已标为 V0.4 历史统计，V0.5 段明确写26／25。可以把当前统计移到顶部提高可读性。[当前统计及历史说明](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/references/04-visual-asset-catalog.md:53) |

另外，有 **三项直接影响当前首阶段**，应该优先于术语和计数修正。

**第一，首阶段目标已经变化，文档尚未同步。**

当前基线仍要求 SO101＋ACT，并把训练、数据资格和预测纳入首条验收；甚至规定改选 LanderPi 后也要补训练资格才能完成 R1。[当前基线](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/00-overview/10-first-task-closed-loop.md:23)

这与本轮确定的 mobileCar 最短闭环不一致。应将当前完成条件收敛为：

> 选择已有场景及允许的初态 → 进入运行 → 按原有控制和录制门控采集 → 正常结束或明确报告失败 → 取得可重新加载的 Episode → 只读回放。

训练资格为 false 不应阻止这条链路完成；训练和模型 IO 留到对应阶段。

**第二，需要补宿主作用域，但不能把所有“唯一”都改成宿主内唯一。**

你的单宿主判断基本成立，不过修正必须分层：

| 作用域 | 应负责的状态或约束 |
|---|---|
| **宿主／页面实例** | 导航、布局、选择、相机视角、组件使用的 store 实例 |
| **具体实验草案** | 编辑状态、修订、保存、验证结果；同一草案跨界面编辑仍检查版本冲突 |
| **运行实例与执行器范围** | 后端控制权、命令失效、停止、物理推进者；跨宿主仍统一裁决 |
| **资源版本** | Scene／Profile／Route 的不可变身份与权威内容 |

当前组件规范只写“本页唯一草案编辑来源”，尚未定义宿主注入和实例隔离。[组件状态定义](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/10-frontend/02-scene-setup/05-shared-scene-components.md:31)

引入一个轻量的宿主上下文是合理修正，**不需要为此先开发通用插件或微前端框架**。而且多宿主可以各自有控制页面，但不能各自授予同一个机器人控制权。[后端控制权定义](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/30-contracts/06-control-authority.md:23)

**第三，录制完成到回放的接入契约仍然没有收敛。**

Episode 契约仍把开始、停止、Finalize、失败保留及 Reset 边界列为未冻结；验收也仍写“按正式规则执行；规则待定”。[契约缺口](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/30-contracts/03-episode-events-annotations.md:39)、[现有验收](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/40-verification/02-workspace-runtime-acceptance.md:33)

这里应优先映射 mobileCar 已有录制器，明确结束回执、完整性状态、原生记录位置和只读读取方式，不必重写录制器。[现有实现](C:/Users/Administrator/Desktop/embodied_intelligence_proj/mobileCar/src/mobilecar/data/recorder.py:391)

建议修订顺序为：**当前阶段与验收范围 → Scene/Experiment 和宿主边界 → Session/Episode/录制回放契约 → Profile 名称 → 后续集合与术语整理。** bimanual 随后验证组件能否通过注入不同数据和服务复用，避免串用草案或运行状态。

本轮为只读审核，未修改 Specification、代码或配置；也未执行仿真或产品验收。

---

## 第 7 轮

会话轮次 ID：`01a163d8-0bf2-7ab0-bb0a-f15c666364e9`。保存时状态：`completed`。

### 发言 27｜用户

帮我进行修复

---

### 发言 28｜用户

还是使用多agents

---

### 发言 29｜助手 · 进度

我会继续用多个子 agent 核对修订涉及的条款，由我统一修改 Specification。先把 mobileCar 最短闭环设为当前阶段，再修正对象归属、宿主作用域、配置引用和录制回放契约，最后同步索引与验收。

---

### 发言 30｜助手 · 进度

当前阶段已改为 mobileCar 四步闭环，bimanual 作为下一步复用验证，训练和预测保留为后续目标。

核对原生接口时还发现一个必须写清的行为：mobileCar 的“开始录制”包含 RESET 边界，不能拿它来模拟“准备 Session”。规范会分开描述准备、运行和录制，并将停车反馈与文件收尾状态分别展示。

---

### 发言 31｜助手 · 进度

对象边界已收敛：基础 SceneVersion、资源编辑 SceneDraft、实验实例覆盖和前端 store 现在分别定义。Episode 也改为绑定一份已解析配置快照，并保留原生记录身份。

宿主规则已补上：轻量工具可以独立承载界面和状态；同一运行实例的控制权与物理推进责任仍由后端统一裁决。

---

### 发言 32｜助手 · 进度

子 agent 的复核结果已收齐。核心定义和阶段顺序未发现新的实质冲突；还需收尾几处旧版本提示、日期，以及“FAILED 状态下收尾成功”和“收尾本身失败”的措辞区别。

接下来做链接、需求/验收编号、来源哈希和文件范围检查。这些检查只验证文档一致性，不代表产品或仿真验收通过。

---

### 发言 33｜助手 · 答复

已使用 **3 个子 agent 辅助核对**，完成修复并更新为 **Specification V0.6**。

- [当前阶段](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/00-overview/10-first-task-closed-loop.md)：mobileCar 四步闭环先行，bimanual 验证复用，训练与预测后续。
- [配置与宿主契约](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/30-contracts/07-task-scene-experiment-config.md)：明确 Scene、实例覆盖、快照和 store 的归属；跨宿主控制权仍由后端裁决。
- [录制回放契约](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/30-contracts/03-episode-events-annotations.md)：统一 Episode 引用，明确原生 RESET、录制收尾、失败保留及只读回放。
- 同步修复 Profile 分类、Session 状态、Collection/Version 边界及历史计数提示。

文档检查通过：**148 个节点、89 项需求、2,440 个本地链接**。新增 4 项产品验收仍待执行；本轮没有启动仿真或训练。

---

## 第 8 轮

会话轮次 ID：`01a1640f-2a18-7d51-9810-470628117b37`。保存时状态：`failed`。

### 发言 34｜用户

当前是否可以开始规划开发计划？

---

### 发言 35｜助手 · 进度

我会先核对 V0.6 的阶段基线和待接入项，确认现在是否具备制定开发计划的条件，并区分规划前提与实现验收要求。

---

### 发言 36｜用户

并且是否可以提交一个git版本？

---

### 发言 37｜助手 · 进度

现在可以开始制定开发计划：M1 的范围和验收目标已经明确，剩余的适配问题可以列为开发任务。

我会补一份 M1 实施拆分，并把本轮 Specification 与计划提交为一个本地 Git 基线。现有后端、AGENTS 调整和临时备份会保留在工作区，不混入这次文档提交。

---

### 发言 38｜助手 · 进度

M1 已拆成六个工作包：接入核对、配置准备、运行控制、录制收尾、只读回放、整体验收，每包都列出了依赖和完成检查。

提交范围也已核对：README 和文档参考素材约 88 MB，最大文件是原始设计 PPT。接下来检查文档内容与暂存范围，然后创建本地提交。

---

### 发言 39｜助手 · 进度

文档检查已通过。提交前发现 Git 启用了 Windows 换行转换；我会补上来源档案的字节保留规则，避免提交或重新检出后使已登记的来源哈希失效。

---

## 第 9 轮

会话轮次 ID：`01a164b1-fbd9-75b0-b45b-52718609107f`。保存时状态：`completed`。

### 发言 40｜用户

继续

---

### 发言 41｜助手 · 进度

我继续核对刚才的提交结果和工作区范围，确认规范与开发计划已保存，再明确下一步的起点。

---

### 发言 42｜助手 · 答复

已确认：**可以进入开发计划阶段，计划也已保存。**

[M1 实施计划](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/specs/00-overview/09-page-design-delivery-plan.md)分为六个工作包：

接口核对 → 配置准备 → 运行控制 → 录制收尾 → 只读回放 → 整体验收。

已创建本地提交 **`7b0666e`**：
`docs: establish v0.6 specification baseline and M1 plan`

提交包含规范、参考素材和计划，尚未推送 GitHub；后端、AGENTS 和备份等其他变更保留在工作区。

下一步从 **M1.1：核对 mobileCar 接口与准备态适配差距**开始。

---

## 第 10 轮

会话轮次 ID：`01a164b5-3fea-7b00-8cc7-eb5e8551a1f5`。保存时状态：`completed`。

### 发言 43｜用户

先push一波云端

---

### 发言 44｜助手 · 进度

我先确认远端和当前分支，再推送刚保存的规范与 M1 计划提交。

---

### 发言 45｜用户

先确定哪些是需要追踪的，现在我主要要迁移当前项目到另一个笔记本去开发

---

### 发言 46｜助手 · 进度

我先暂停推送，按“换一台笔记本后能继续开发”的目标核对追踪范围。会检查源码、配置模板、项目规则和文档是否齐全，并排除本机环境、缓存、备份和凭据；同时确认哪些依赖仍需从另外三个仓库或服务器取得。

---

### 发言 47｜助手 · 进度

确认需要补追踪的是后端源码、测试、公共配置、迁移清单和项目级 AGENTS.md；文档与参考图已经提交。虚拟环境、缓存、运行输出、私人配置和 AGENTS 备份应排除。

还需注意：另外三个工程目前是独立仓库，推送本仓库不会自动带上它们。我会把新笔记本的目录布局、恢复步骤和外部依赖写进迁移说明，再准备推送。

---

### 发言 48｜助手 · 进度

迁移说明和忽略规则已补齐。本次准备上云的内容包括：规范与设计素材、后端网关源码及测试、公共配置、迁移清单、项目级 AGENTS.md。

本机备份、环境、缓存和运行输出会继续保留在本地。个人地址配置可使用完整的 `catalog.local.yaml` 副本，该文件已排除出 Git；新笔记本不必沿用当前 Desktop 的绝对路径。

---

### 发言 49｜助手 · 进度

追踪范围检查已通过：新增暂存的 22 个文件包含后端源码、测试、项目规则、忽略规则和迁移说明，没有混入备份或运行产物。

我现在提交这份迁移基线，并将它与前一份规范提交一起推送到 `origin/main`。

---

### 发言 50｜助手 · 进度

迁移基线已在本地提交，但云端推送被 GitHub 拒绝：当前 HTTPS 登录凭据无效。

我先检查这台机器是否已有可用的 GitHub 登录或 SSH 认证。若需要重新登录，会请你在自己的登录界面完成，不需要把 token 发到聊天里。

---

### 发言 51｜助手 · 进度

本地迁移提交已完成，工作区也已清理到正确的追踪范围。推送目前只卡在认证：HTTPS 凭据失效，SSH 也未通过。

Git 自带的设备登录暂时还没有返回验证码；若无法完成连接，我会保留这两个本地提交，并明确给出需要你完成的登录步骤。

---

### 发言 52｜用户

Administrator@JXEAELAXKDDAPJB MINGW64 ~/Desktop/embodied_intelligence_proj/uniRobotPlatform (main)
$ ssh -T git@github.com
Hi liaohello! You've successfully authenticated, but GitHub does not provide shell access.

Administrator@JXEAELAXKDDAPJB MINGW64 ~/Desktop/embodied_intelligence_proj/uniRobotPlatform (main)
$ C

---

### 发言 53｜用户

id_ed25519 用这个密钥连接

---

### 发言 54｜助手 · 进度

收到。Git Bash 已确认能以 `liaohello` 身份连接，我会改用你指定的 `id_ed25519` 密钥推送，停止等待 HTTPS 设备登录。密钥内容不会读取或加入仓库。

---

### 发言 55｜助手 · 答复

已使用 **`id_ed25519` 成功推送**到 [GitHub 仓库](https://github.com/liaohello/uniRobotPlatform)，最新提交为 **`dce67b7`**。本地与云端一致，工作区干净。

- **已追踪**：源码、测试、公共配置、AGENTS、规范、参考素材和迁移说明。
- **已排除**：本机环境、缓存、备份、运行输出及私人配置。

新笔记本配置好 GitHub SSH 认证后：

```bash
git clone git@github.com:liaohello/uniRobotPlatform.git
```

恢复步骤见[迁移说明](C:/Users/Administrator/Desktop/embodied_intelligence_proj/uniRobotPlatform/docs/laptop-migration.md)。另外三个原生工程仍需分别恢复。

---

## 第 11 轮

会话轮次 ID：`01a164d7-deab-7701-a6e2-5e79bd518608`。保存时状态：`inProgress`。

### 发言 56｜用户

当前对话记录是否有保存成md文件，我可能需要另开一个会话，保存完后上传git

---

### 发言 57｜助手 · 进度

我先核对现有 Markdown 是否包含这段对话。如果尚未保存，我会整理一份可供新会话接续的记录，保留关键决定、已完成工作和下一步，再提交并推送到 Git。

---

