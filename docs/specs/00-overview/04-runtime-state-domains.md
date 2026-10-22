# 独立状态域与运行模型

规范 ID：`SYS-STATE` · 责任层：系统 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-011](../../设计过程与Specification总册_20261021.md#doc-011) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.6｜更新日期：2026-10-22（America/Los_Angeles）

状态：V0.6 收敛平台语义与作用域，原生枚举/实际运行映射仍需接入验证，不宣称代码已实现。

来源：S02、S03、S05（详见[来源档案](../90-governance/06-sources.md)）

关联需求：[REQ-STATE-001](../indexes/05-requirements.md#req-state-001), [REQ-STATE-002](../indexes/05-requirements.md#req-state-002)

## 状态域草案

| 状态域 | 平台语义值/本轮基线；原生枚举单独映射 | 管理职责 |
|---|---|---|
| HostApp / Page Context | 当前 Workspace/View、选择、布局、相机 | 各宿主实例注入；不控制 Session 生命周期 |
| SceneDraft | clean / dirty / saved / conflict | 基础场景资源编辑与新 SceneVersion 发布 |
| ExperimentDraft | clean / dirty / saved / conflict；独立 validation 状态 | 本次配置和实例覆盖，按 draftId/revision 隔离；取代笼统 Scene Document |
| Session lifecycle | prepared / active / closed / failed | 后端运行上下文；prepared 不执行，active 可包含物理暂停，closed/failed 不接新运动命令 |
| Simulation | Ready / Running / Paused / Stopped / Error | 物理仿真生命周期 |
| Task | Idle / Active / Completed / Failed | 任务语义与结果 |
| Recording | Idle / Recording / Finalizing / Error | 数据记录生命周期 |
| Control Authority | Human / Expert / Policy / Pending | 指定执行器范围的命令归属 |
| Interaction | Observe / Edit、Joint / TCP / Force | 当前工具及可用行为 |
| Execution Policy | Live / Preview-Confirm | 目标如何被提交 |

这些维度不应压成一个大枚举。仿真 Running + Policy Active + Recording 可以同时成立；切到 Replay 观察历史也不意味着后台仿真变成 Replay 状态。

Session 是运行身份和接受配置的生命周期，Simulation 是其中物理执行状态，Task 是语义进度，Recording 是录制状态。prepared→active 只由显式 Start 的后端成功回执发生；启动失败可 failed。active 内 Running/Paused 不改 Session 身份；显式结束且录制收尾有结论后 closed，故障终止 failed，原始失败资料保留。Reset 不自动新建平台 Session，但必须报告原生 generation/epoch/Episode 边界；需要采用新配置时重新验证并显式创建，不覆盖原快照。

这些是平台语义，不直接把原生进程状态、RunRecord 枚举或各工程 Task 状态当别名。适配器记录原生 run/session 映射；只有能保证 prepared 未开始行为才声明支持，差异必须返回明确原因。原生后台服务在线不等于某个新 Session 已开始。

Experiment 验证另有 unvalidated/validating/passed/failed/stale，与 saved/dirty 独立，唯一规则见 [配置契约](../30-contracts/07-task-scene-experiment-config.md)。资源 SceneVersion 不因为实验创建 Session 而变为“已消费”或不可复用。

## 已确认与未确认

任务前可配置 Observe / Edit，以及任务中支持实时 / 预览确认来自用户。其余状态名、组合矩阵和状态所有权来自助手方案，需要结合现有后端核对。

## 建议约束

- 运行中常规 Scene Edit 不直接修改在线仿真实体；若以后支持 Debug 修改，应另列权限、重置及记录规则。
- Live 也需权限检查和执行反馈，Preview 也不能覆盖 Actual State。
- Preview 的草案取消与已受理命令的停止是不同操作；Esc 不能承诺回滚已发生的物理运动。
- Replay 使用独立历史数据上下文；录制状态不得由页面是否可见推断。

暂停时是否允许施力、单步、关节提交，以及 Reset 对 Episode 的关闭规则均待定义。

V0.6 当前采集 Reset/Episode 边界已按 [Episode 契约](../30-contracts/03-episode-events-annotations.md) 和 mobileCar 原生行为收敛；暂停施力等不属于 M1 必需能力，仍按实际适配器声明。后端控制权与单一物理推进者按运行实体跨宿主裁决，不按 HostApp 分配第二份 owner。来源：[S16](../90-governance/sources/S16-mobile-first-spec-repair.md)。

## 关联文档

- [全局信息架构与工作区](../10-frontend/01-shell/01-navigation-context.md)
- [控制权与受控人工接管](../30-contracts/06-control-authority.md)
- [Scene Setup｜场景布置](../10-frontend/02-scene-setup/01-workflow-initial-state.md)
- [Episode、采集、事件与标注契约](../30-contracts/03-episode-events-annotations.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)
