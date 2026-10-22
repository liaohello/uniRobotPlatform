# Episode、录制接入、事件与标注契约

规范 ID：`CT-EPISODE` · 责任层：共享契约 · 版本：V0.6（2026-10-22）

状态：当前 mobileCar 接入的语义基线；原生行为已只读核对，平台适配与产品验收未执行。来源：[S16](../90-governance/sources/S16-mobile-first-spec-repair.md)；原始 S02/S03/S04/S05/S07 需求保留。

[配置快照](07-task-scene-experiment-config.md) · [时间/坐标](04-time-frames-units.md) · [当前阶段](../00-overview/10-first-task-closed-loop.md)

## 一套配置权威与原生身份

平台新采集的 Episode 必须绑定平台 Session 和一个 ValidatedSnapshot；它固定已解析 Scene/Robot/Task、实例初态覆盖、Execution、适用的观测/录制引用。Episode 不再平行维护一份 Task Profile 或可变 Experiment Config 作为第二配置权威。

| 信息 | 必需性与归属 |
|---|---|
| platformSessionId / validatedSnapshotRef | 新平台采集必需，可保存在平台 sidecar/index；不要求修改原生数据格式 |
| origin | sourceProject/adapter、原生 run/backend generation/episode ID、schema/reader 版本及原始存储引用；标识不能只靠显示名 |
| recording segment | 原生区间 ID、起止、序列/时间、终态、同 Episode 多段关系；保留 native 边界 |
| 配置索引投影 | 可缓存 scene/robot/task/Execution/Recording refs，但必须与快照一致；冲突报告并阻止作为配置一致数据使用，不静默覆盖原文 |
| 实际采集事实 | 实际 Owner/来源/操作者、动作/观测 schema、起始 actual snapshot、结束/失败与完整性；与预期配置分开 |
| 条件引用 | Route 仅路线任务；算法观测/模型仅实际使用算法/策略时；seed 按任务；实际 Operator View 及变化按人工界面追溯需要记录 |

历史原生 Episode 可只有原生配置/身份：索引明确 provenance=legacy/native、缺哪些平台引用及验证证据，不伪造 ValidatedSnapshot，不反写原始文件。是否可用于后续训练由用途资格另判，不能因能播放就补写为已验证配置。

## 分层数据

| 层 | 内容 |
|---|---|
| 原始记录 | 观测、本体、变换、实际发出的动作及源时间/身份 |
| 在线事件 | 请求/受理/拒绝/执行反馈，控制源切换、接管/干预、阶段、Reset/碰撞/失败 |
| 派生/清理 | FK/重采样、片段、变换/排除原因及版本，不覆盖原始文件 |
| 离线标注 | 区间、作者/修订、词表、候选/审核来源；评估真值、预测与人工结论独立 |
| 训练视图 | 固定成员、观测/动作映射、split、导出与资格报告，属于后续阶段 |

动作注明底盘/关节/TCP、绝对或增量、目标或实测、单位、顺序、周期和对应观测身份；请求被拒绝不能混作实际执行 action。Human/Expert/Policy 是实际来源，Demonstration/Intervention 是用途，任务结果、录制完整性、停车确认和训练资格分别表达。

## 采集生命周期：begin / append / end / failure

| 操作职责 | 接受和完成条件 | 持久化及失败规则 |
|---|---|---|
| begin | 校验所需来源/流和配置绑定；进入 STARTING，起始记录/actual snapshot 可靠写入后才确认 RECORDING | 返回原生 Episode/segment 身份和真实状态；失败不授予 recording-ready，不伪造数据 |
| append | 原生 recorder 追加源观测、动作链和事件；浏览器不承担逐帧持久化 | 按原生 seq/sample/control tick、measurement/arrival 等时间和媒体引用关联；重入/丢样按原生策略显式记录 |
| end | 接受停止后进入 DRAINING；排空队列、终态/索引/完整性写入完成才确认 COMPLETE | 停车确认与 recorder finalize 分开显示，不能以 COMPLETE 证明物理已经停稳 |
| failure | 状态 FAILED、完整性 INCOMPLETE，保留已写记录、媒体与诊断，停止/保持依原控制契约 | 存储故障不保证尾事件/完整索引仍能写入；缺失尾部不能推定成功，不自动删除原始证据 |
| list/read | 按 source/native identity 读取索引、事件、状态、媒体及质量信息 | ReplayReader 只读，不发送动作或推进物理；不完整内容仅按可解析部分展示并明示缺失 |

这些是能力职责，不冻结一套新的公共 HTTP begin/append API。适配器包装已有 Recorder/Reader；只在原协议缺少必要身份/完成回执时补适配，不并行建设第二录制器。

## mobileCar M1 的已核对映射

下表是原项目实际入口的静态证据，不意味着统一平台已完成调用或验证。

| 平台含义 | mobileCar 现有入口/行为 | 平台必须保留的边界 |
|---|---|---|
| 读当前资源/状态 | GET `/api/v1/scene`、`/api/v1/snapshot`；manifest 含 model_id/model_sha256/scene_id | 只读当前编译场景/actual state，不证明任意编辑/切场景或预设初态应用 |
| 开始录制 | POST `/api/v1/episodes/start`，含 operator_id/operator_kind/view_source 等；先请求 RESET 再 Recorder.start | 明示 RESET 边界，不能用于 Prepare Session；accepted=true 且 recording_status=RECORDING 才确认起始记录持久化；RESET RECEIVED/DISPATCHED 不等于实际初态已应用，另核对生效 generation/epoch 与 actual snapshot |
| 停止录制 | POST `/api/v1/episodes/stop`；先 STOP(latch)，等待停车反馈或超时，再暂停/排空采样并 Recorder.stop/finalize | accepted=true 且状态 COMPLETE 才标录制完成；仍单独显示停车反馈/超时；FAILED 不冒充完整 |
| 列表/历史/媒体 | GET `/api/v1/episodes`、`/api/v1/episodes/{episode_id}` 及 assets 子资源 | 保留 read_only、recording_status、segment_count、complete_tail；有尾标记也须结合终态/质量判断 |

原生身份与边界规则：Episode 由实际 backend snapshot 中的 episode_id 标识，RESET 可改变 Episode/generation；Recording Segment 是录制区间，不能假设每次重开只换 segment 或每次都只换 Episode。以实际响应/事件报告原生身份，平台 Session 与 origin 组合索引；同一 Episode 的多个 segment 不展平成互不相关的数据。

M1 在停止/Reset 发生时必须给当前 segment 的终态和身份切换结论：由原生服务按顺序 finalize 旧记录、确认新 epoch，再启用新采集/命令上下文。若原生不支持“录制中任意 Reset”，界面禁用该路径，先显式 end；不能承诺连续跨 Reset 同一 Episode。旧命令/lease/epoch 按既有后端规则失效，不由宿主自行重放。

mobileCar 的 native start 会写 recording_start、feedback_initial、initial_snapshot 并 sync；正常 stop 排空后写 terminal/checksums/episode_complete。FAILED 状态下若 finalize 成功，可能写出尾标记但仍为 FAILED/INCOMPLETE；若 drain/finalize 本身失败，尾标记可能缺失。complete_tail 是尾部存在性信息，不等于录制完整性结论。队列溢出/写盘故障沿用原生失败和停车机制；平台不静默掉流来保持绿色。

## 原始存储与读取适配

索引记录 sourceProject/adapter/native IDs、原始位置、format/schema/reader 版本、媒体/事件引用、完整性与可用流。原始文件继续由各工程保存，平台只维护映射/sidecar，不为统一前端强制搬目录或重写格式。使用原始 source time 和记录的变换，不能按浏览器收包顺序对齐。

M1 只要求其已声明必需流能重载和只读回放；缺失流、损坏或不支持 reader 给出定位原因。动力学重执行、离线重算和任意帧续跑是额外能力，不能从只读播放推导。

源码依据：[原生契约](../../../../mobileCar/docs/interface_contract_v1.md)、[API/运行入口](../../../../mobileCar/src/mobilecar/app.py)、[Recorder](../../../../mobileCar/src/mobilecar/data/recorder.py)、[ReplayReader](../../../../mobileCar/src/mobilecar/data/replay.py)。这些路径为本地调查证据，正式接入还需固定对应源码版本与实际运行结果。

验收：[TEST-MOBILE-001/002](../40-verification/06-scene-setup-first-loop.md)，保留 [TEST-REC-001/004](../40-verification/02-workspace-runtime-acceptance.md) 的来源/Reset 测试；训练与集合不作为 M1 前置。
