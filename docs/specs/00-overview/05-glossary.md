# 术语与边界

规范 ID：`SYS-GLOSSARY` · 责任层：系统 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-006](../../设计过程与Specification总册_20261021.md#doc-006) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

| 术语 | 本文含义 |
|---|---|
| HostApp | 承载控制台/专项工具的应用入口；提供组件上下文、草案 store、订阅和命令服务，不拥有物理状态 |
| Navigation Group | 宿主内菜单组织分组；完整平台的四业务组不等于四个逻辑工作区 |
| Workspace | Scene Setup/Simulation/Replay/Dataset/Training/Evaluation 等业务职责；可由多个页面呈现，不等于导航组或后端状态 |
| Page / View | 宿主内具体路由/视图；其选中、布局、相机状态与运行生命周期分开 |
| WorkspaceShell | 可复用的宿主布局组件职责名，不是后端对象或额外工作区 |
| Scene / SceneVersion | 场景逻辑资源及固定基础布局版本；对象有稳定 ID |
| SceneDraft | 基础场景资源编辑草案，发布为新 SceneVersion；不与实例初态混写 |
| Experiment Configuration / ExperimentDraft | 固定资源引用和本次允许覆盖组成的实验配置/草案 |
| ExperimentDraftStore | 宿主注入的某个实验草案状态容器，不是另一种资源/落盘对象 |
| Scene Document | 旧的笼统 UI 称呼，停止用于新接口；按实际目标明确为 SceneDraft 或 ExperimentDraft |
| ValidatedSnapshot | 已解析完整配置、固定依赖及验证证据的不可变快照，Session/Episode 的配置权威 |
| Session / RuntimeSession | 平台运行上下文；prepared 与实际物理/任务/录制状态分开，参见状态域和后端生命周期；不默认支持并行 |
| Episode / Recording Segment | 原生运行/Reset 定义的数据身份与其中录制区间；通过 origin 映射并保留原生 ID，不能固定假设一个 Session 只有一条 Episode |
| Arm / Link / Joint / Body | 机械臂、运动学连杆、关节、物理刚体；不可只凭名称混用 |
| Selected Arms | 当前选中观察的 Arm 集合 |
| Active Arm | 当前工具准备操作的 Arm；不自动拥有控制权 |
| Control Owner | 后端认可的控制来源与范围 |
| Human / Expert / Policy | 人工、专家算法、学习策略等来源维度 |
| Human Demonstration | 以人工示教为目的的数据上下文 |
| Human Intervention | 策略或任务过程中经流程切入的人工干预 |
| Takeover | 控制权转换机制，完成后来源通常为 Human |
| Physics Intervention | 对物理世界施加扰动；与策略动作可并行但需实验允许 |
| Live | 目标经检查实时提交，不表示绕过后端 |
| Preview-Confirm | 先预览目标/候选，显式确认后提交 |
| Actual / Target / Preview | 实际状态、控制目标、未执行预览 |
| TCP | Tool Center Point；控制目标需 Frame 与可实现自由度 |
| IK / FK | 逆运动学 / 正运动学；终点 IK 不等于完整轨迹 |
| q(t) | 随时间的关节配置序列 |
| Ghost Robot | 半透明候选或目标姿态，仅作预览 |
| Candidate Path | 来自指定候选的空间路径，需标检查状态 |
| Actual Trail | 实际历史状态计算出的运动轨迹 |
| Task Template | 任务类型/schema、能力与成功/终止语义的版本化定义 |
| Task Profile | 历史组合称呼；新接口按 Task Template、Layout Preset、Execution/观测引用拆分，不作为新持久化对象 |
| Operator View Profile | 人工可见信息与展示选择；旧 UI Observation，纯布局与执行指纹分开 |
| Policy Observation Profile | 算法输入；旧 Algorithm Observation，依实际算法路径决定适用性 |
| Execution Profile | 执行意图、允许控制源、动作通路及接管策略；不等于当前 Control Owner |
| Export Profile | 后续数据转换、映射与目标格式配方；不替代原生 Recording Profile |
| Recording Profile | 记录流、动作语义、频率和时间约定 |
| Task Phase / Annotation | 在线任务阶段/事件与离线标注层，不应混为不可修改真值 |
| Collection | 可编辑的 Episode 选择/查询工作集，可为固定成员或动态选择；不直接作为训练的可变输入 |
| Dataset Version | 冻结解析成员、清理/标注修订、变换/schema 与划分引用的数据快照；不随 Collection 后续修改变化 |
| Specification | 目标行为与约束的主责文档；不意味着已经实现 |
| Wiki | 导航、分类与交叉索引；不应复制全部主责规范 |
| ADR / DEC / OQ | 架构决策记录 / 决策条目 / 未决问题 |

[Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)

V0.6（2026-10-22）：术语权威分别见 [配置与宿主](../30-contracts/07-task-scene-experiment-config.md)、[Episode/采集](../30-contracts/03-episode-events-annotations.md)、[集合/来源链](../30-contracts/05-dataset-model-lineage.md)。来源：[S16](../90-governance/sources/S16-mobile-first-spec-repair.md)。
