# 当前开发基线：mobileCar 最短闭环与 bimanual 复用验证

规范 ID：`SYS-FIRST-TASK-LOOP` · 责任层：系统规划 · 版本：V0.6（2026-10-22，America/Los_Angeles）

状态：用户已明确阶段顺序；实现方案按下述边界细化，产品实现/验收未因文档修订而完成。来源：[S16](../90-governance/sources/S16-mobile-first-spec-repair.md)；长期完整流程来源 [S15](../90-governance/sources/S15-scene-setup-first-loop.md) 保留。

[总索引](../README.md) · [Scene Setup 三图](../10-frontend/page-designs/02-scene-setup.md) · [共享组件](../10-frontend/02-scene-setup/05-shared-scene-components.md) · [当前与后续验收](../40-verification/06-scene-setup-first-loop.md)

## 当前阶段与完成条件

**M1：先用 mobileCar 跑通场景→运行→录制→回放。** 选择实际可用的场景/机器人预设，确认允许初态与配置，创建未开始的 Session，显式进入运行，依原生录制和控制门控采集，结束并取得真实 Episode/segment 回执，重新加载只读回放。至少一种真实可用来源即可；当前优先已存在的人工遥操作，专家来源仅在对应任务实际接通时提供。

**M2：再用 bimanual 验证组件复用。** 在相同组件职责和数据/控制契约下，注入不同宿主上下文、机器人能力、数据源和命令服务，验证选择、位姿/状态展示、相机列表、录制/回放适配。允许平台宿主或独立轻量工作台；不复制隐含全局状态，不要求重写已有 Viser 等工具。

**后续：清理/数据版本→训练→模型预测。** 保留整体产品目标；Dataset 资格、split、Export、ACT/其他模型 IO 在受影响阶段接入前固定。M1/M2 不因训练资格为 false、未训练或缺模型超市而失败。完整训练/预测验收继续使用 TEST-LOOP-002～005，不标成当前已执行。

F0 是按需的 UI 演示/组件验证，不是必须先完成全产品 Mock 的阶段。三张 Setup 图是参考变体，不要求 M1 全部接通；导航 Waypoint 编辑保存的 V1 范围保留，按其功能切片推进。

## M1 最小输入、操作与产物

| 阶段 | 最小行为 | 可核验产物与边界 |
|---|---|---|
| 场景与准备 | 选择已接通 native preset；核对 SceneVersion/robot/model 身份、允许初态、录制和控制能力 | ExperimentDraft→ValidatedSnapshot→prepared Session；验证覆盖范围明确，未实现的任意场景/对象编辑禁用 |
| 运行 | 显式 Start、核对当前 Session 与原生 runtime 绑定；启动过程不绕过 STOP/租约/require_recording 等门控 | 服务端回执、actual state/观测身份；后台服务在线不等于本 Session 已开始 |
| 录制开始 | 复用原生 start；明确提示其 RESET/Episode 边界，起始内容持久化后确认 RECORDING | 原生 run/backend generation/episode/segment ID，配置快照 sidecar 引用，实际初态记录与来源 |
| 录制结束 | STOP 的实际反馈与 Recorder finalize 分别显示；完整收尾后才标录制完成 | Episode/segment 终态、完整性与原始位置；失败保留已写数据，不假造尾事件 |
| 回放 | 通过原生只读 reader 重新加载记录，独立历史时间轴显示状态/动作/必需流 | Episode 可重载，缺流/不完整明确；不控制在线机器人、不推进物理、不覆盖原始文件 |

当前 mobileCar 的 scene/snapshot GET 只证明可读取当前编译场景和 actual state；它们不证明通用场景切换、任意初态应用或 ValidatedSnapshot 已实现。第一步只启用实际支持的预设/字段；未知能力不伪装 Ready。adapter 必须区分原生只读状态、预期配置和录制启动 RESET 后的实际初态。

创建 Session 不调用原生 episodes/start，不以启动录制来模拟准备。原生运行时若无法提供未开始状态或配置绑定，须显式报告差距并在接通前补适配；不把纸面语义算成已有能力。Start 或录制 RESET 后，实际生效的 generation/epoch/初态证据独立记录，命令 RECEIVED/DISPATCHED 不等于配置已应用。

## 共用对象与宿主边界

- SceneVersion 固定基础布局和对象 ID；SceneDraft 修改资源；ExperimentDraft 只保存本次允许的实例覆盖。解析、验证后产生包含实际配置的 ValidatedSnapshot，Session/Episode 绑定它。
- HostApp 是承载控制台/专项工具的应用入口。组件接收宿主注入的草案状态、能力、订阅和命令接口，不依赖全平台单例 store；同一草案跨宿主仍做修订冲突检查。
- 宿主导航/布局/选择与后端 Session、物理执行、任务、录制、控制权独立。同一运行实例即使被多个宿主访问，也只有一个物理推进责任者，并按执行器范围统一授权。
- 三张卡展示 Operator View、Policy Observation、Recording；Execution 是运行来源/动作通路，Export 属于后续数据出口。不适用的 Profile 可明确未使用，不制造占位依赖阻止纯人工 M1。

这些规则以 [配置契约](../30-contracts/07-task-scene-experiment-config.md)、[状态域](04-runtime-state-domains.md)、[Episode/采集](../30-contracts/03-episode-events-annotations.md) 为主责。

## 验收边界

当前先执行 TEST-MOBILE-001/002、TEST-CONFIG-008；M2 执行 TEST-HOST-001 及对应既有共享交互验收。参数/单位、动作回执、控制权、原始采样身份和只读回放必须真实，不以 UI 演示或自动化冒充真人示教。

M1 通过需要一条真实记录的成功开始、可解释结束、重新加载和只读回放证据；失败/RESET 路径另验。任务物理成功、录制完整性、停车确认、特定训练用途资格分别显示。未取得证据不写“已通过”，不新增未经测量的频率/误差承诺。

## V0.5 建议的取代与保留

V0.5 的 SO101 transfer + Expert + ACT 首发、三种 Setup 都进入 F0、R1 必须含训练预测，由 S16 的 M1/M2 次序取代。旧来源和证据保留，不反向修改报告：bimanual P4/P5 可供后续适配，既有 mixed direct/transfer 模型不能直接当 transfer-ready 策略；mobileCar 训练资格 false 仍阻止相应用途的训练，不阻止 M1 原始采集/回放。

后续训练阶段继续固定同源划分、只由 train 拟合归一化、模型/processor/IO/动作/频率/代码指纹和新训练产物。无需在 M1 前建设多模型管理、批量调度、任意资产编辑或把三个工程合并为一个仿真进程。
