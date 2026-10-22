# 冲突、澄清与取代关系

规范 ID：`GOV-CONFLICTS` · 责任层：治理 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-040](../../设计过程与Specification总册_20261021.md#doc-040) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.6｜更新日期：2026-10-22（America/Los_Angeles）；原始内容来源保留。

状态：来源核对与整理结论

来源：S01–S05（详见[来源档案](06-sources.md)）

关联需求：见需求追踪矩阵中的引用与相关主责规范

| 早期说法 / 易混处 | 后续材料 / 当前处理 | 仍需明确 |
|---|---|---|
| 把 3D 鼠标规范当完整前端 | S04 明确它只是在线仿真交互；上层按业务拆分 | 正式全局导航 |
| 关节滑条作为控制入口 | S04 改为主要监控；S05 建议默认只读 | 调试编辑入口 |
| 主臂需要“捕捉画面” | S03 已澄清实体主臂无摄像头，只显示状态与映射 | 原始澄清连续记录缺失 |
| 独立受力模式 | S03 提议 Alt 临时工具 | 是否保留按钮、绑定兼容 |
| 框选自动整臂，可能跨双臂自动多选 | 单臂多个不同 Link 提升保持；S03 新草案跨臂需 Ctrl | 命中混合对象与取消行为 |
| 选中 Arm 就进入可执行控制 | 选择、Active Arm 与 Owner 分开 | 控制粒度与工具启用规则 |
| 双击 Arm 就自动进入 TCP 控制 | S03 写“选 Arm 后可切 TCP Tool” | 不把早期设想当最终自动激活规则 |
| 关节“轨迹”都等于 TCP 线 | S04 原意较广，S05 区分多种表示 | 默认显示语义 |
| 有 IK 就有可执行路径 | 终点解、候选轨迹、实际执行分别标明 | 后端真实规划能力 |
| 鼠标拖动覆盖 VLA | S04 明确按钮受控接管 | 停旧命令与恢复协议 |
| 暂停 Policy 等于暂停物理仿真 | S05 指出二者不同 | 各状态组合与例外 |
| 回放“只读”所以不能标注 | 只读指原始历史状态；标签作为独立修订层 | 标注版本与审核 |
| 任务成功就能训练 | S05 拆开成功、记录完整、用途资格 | 具体资格配方 |
| P0 Dataset 与 P1 Dataset 冲突 | 解释为基础 P0 / 完整 P1，保留为建议 | 正式排期 |
| 六工作区被历史摘要标作用户约束 | 当前原话只明确“多个部分”；具体六项来自 S05 | 不虚构用户逐项确认 |

本页记录变化，不删除早期来源。新的整理解释若未经用户确认，仍标为方案，而不是在总册里覆盖成已决定事实。

## 关联文档

- [决策与方案演变记录](01-decisions.md)
- [选择、相机与整臂框选](../10-frontend/07-viewport-tools/02-selection-camera.md)
- [TCP 操控与虚线运动轨迹](../10-frontend/07-viewport-tools/04-tcp-trajectories.md)
- [控制权与受控人工接管](../30-contracts/06-control-authority.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)

## 与仓库上一轮分析的关系

当前规则按本次总册中的更新用户决定组织。旧 [前端分析 V0.2](../../frontend_analysis_v0.2.md) 的默认滑条控制不再采用；其地图设点曾被排除，现又经 S10 按更窄的 Scene Setup 范围重新纳入，旧实现建议不能自动作为新协议；四工作区/六工作区均属于不同阶段的组织建议，不因本次目录采用六个阅读入口就冻结实际导航。

## V0.2 当前优先级与取代关系

| 冲突/演进 | 当前处理 |
|---|---|
| S08 仍排除 Waypoint，S09 称已加入 | 已向用户核实并取得 S10；采用 V1 Scene Setup 编辑保存、Simulation 展示进度 |
| 旧总册/REQ-NAV-001/DEC-016 排除编辑 | 原文与旧 ID 保留，活动规范改为 REQ-NAV-003 / DEC-027；旧 TEST-NAV-001 退役 |
| 六工作区与四导航组 | 六个逻辑职责不变；S08 建议四组导航，Data 两职责共享入口，不另复制控制台 |
| 所有标注都供所有模型训练 | Export/Training Profile 决定必需字段，阶段/语言标签不是每类模型的统一前提 |
| 编辑器能导出 XML 就替换机器人 | 改用受限场景配置/Scene Builder；不静默改原模型，先 PoC |
| 接管必定同一个 Episode | 仅连续录制、无 Reset/终止/故障等边界时成立；保留实际生命周期 |

其余模板、布局、A–E 路线和候选资源仍是设计建议，用户要求更新文档不等于所有细节均已冻结。

## V0.3 视觉材料的取舍

[原图冲突分析](08-visual-design-conflicts.md) 登记 22 项主题。图片作为设计参考，已确认交互/数据规则优先；局部参考与完整页面参考分开，不把图中按钮、硬件、指标或后续能力直接升级为 V1 需求。[页面设计](../10-frontend/page-designs/README.md) 给出每页采用与修正。

## V0.4 Simulation 主图取代关系

用户提交 IMG-022 作为 PAGE-03 当前设计参考，取代 IMG-003 的主图引用；旧图与 PPT 原件不删除。新图中的夹爪按钮/控制器卡片缺失不等于用户取消相关功能需求。具体 [删除/替换清单](../10-frontend/03-simulation/06-simulation-v2-review.md) 与运行状态矛盾继续保留，不能仅因换图关闭冲突。

## V0.5 当前三图与开发范围取代关系

| 旧建议 / 三图冲突 | 当前处理 |
|---|---|
| PAGE-02 只有 IMG-002；继续补齐全产品专图 | IMG-023/024/025 共用一个页面；旧图保留，停止大范围补图，交互规则进入 Specification |
| A–E 默认 mobileCar 首任务到回放，训练整体后置 | F0 样板 + R1 含清理/训练/预测完整纵切；首任务建议 SO101 transfer + Expert/ACT，非强制取消 mobileCar |
| 图一多处 Save Draft，图二三步骤/上下文不同 | 一个草案保存动作、一个上下文和派生步骤状态；独立 Route 保存仍保留 |
| 图中静态 Passed，保存/验证/创建/开始混淆 | 四动作独立；服务端验证和固定快照创建 prepared Session，Start 另行执行 |
| 所有 Profile 版本变化或任意视角变化都使验证过期 | 影响运行/策略/采集的变化 stale；纯 Operator View 展示不 stale |
| 图二移动抓取默认启用，图三 Tabletop 却勾同步/力反馈 | 固定底盘近场默认不启用导航；tabletop 顺序交接，未接同步/力能力禁用并列扩展 |
| 图中 Direct Transfer 与既有 BI-DIRECT 同名近似 | 不自动映射；首发只用 BI-TABLE-TRANSFER，空中交接留后续并定义清楚物理语义 |

规则见 [任务字段](../10-frontend/02-scene-setup/02-task-template-configuration.md)、[共享组件](../10-frontend/02-scene-setup/05-shared-scene-components.md) 与 [首任务基线](../00-overview/10-first-task-closed-loop.md)。

## V0.6 修复与当前权威

| 审核项 | 当前统一规则 | 主责 |
|---|---|---|
| Scene 布局、初态与草案别名 | 基础 SceneVersion→受限实例覆盖→固定 ValidatedSnapshot；资源 SceneDraft 与 ExperimentDraft 分开，store 是前端容器 | CT-EXPERIMENT-CONFIG / SYS-GLOSSARY |
| 三/四/五个 Profile | 三卡是展示分组，Execution 和 Export 按阶段使用；Policy Observation 为规范名，旧 Task Profile 不继续落盘 | CT-EXPERIMENT-CONFIG / SYS-PROFILES |
| Episode 配置引用 | 新采集以唯一 ValidatedSnapshot 为权威，条件 refs/索引投影须一致，legacy 原生不造验证记录 | CT-EPISODE |
| 四导航组/六工作区 | 导航组织、业务职责、具体 Page/View 和 WorkspaceShell 分层；不是算术冲突 | FE-SHELL-NAV / SYS-GLOSSARY |
| prepared Session | 是 Session 生命周期，物理/任务/录制另域；native enum/后台进程不直接等价 | SYS-STATE / BE-SESSION |
| Collection/版本 | 可编辑选择/查询与固定解析成员的 Dataset Version 分开；集合更新不回写旧版本 | CT-LINEAGE |
| 当前数字/历史统计 | 当前89项REQ、26PNG/25独特图；72、23/22等明确保留为历史版本统计 | 需求/图片索引与JSON |
| 单宿主与所有“唯一” | HostApp/草案隔离界面状态，资源保存权威与同一运行实体的控制权/物理推进仍跨宿主统一 | CT-EXPERIMENT-CONFIG / CT-AUTHORITY |
| SO101/ACT首发和训练前置 | 由 S16 mobileCar 四步闭环→bimanual复用→后续数据/训练/预测取代，V0.5资料保留历史 | SYS-FIRST-TASK-LOOP |

以上为文档规则修复，不表示适配器与产品验收已完成。来源：[S16](sources/S16-mobile-first-spec-repair.md)。
