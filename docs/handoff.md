# 新会话交接说明｜uniRobotPlatform

更新日期：2026-10-22（America/Los_Angeles）。本文件用于接续本次讨论，不替代 Specification、项目 AGENTS 或新会话用户指令。

**先读这里：当前需要继续的是 M1.1 接入核对。规范已修复、计划已形成、源码已追踪并上云；mobileCar 的平台闭环还没有实际跑通或验收。**

## 1. 阅读顺序

1. [项目 AGENTS](../AGENTS.md)：主智能体整合和修改；default 子智能体只读检索，fork_turns=none，最多3个并发，不自行派生或写文件。模型名称是配置约定，不能仅凭角色名称声称实际生效。
2. [当前 M1/M2 范围](specs/00-overview/10-first-task-closed-loop.md)。
3. [M1.1～1.6 实施计划](specs/00-overview/09-page-design-delivery-plan.md)。
4. [配置/HostApp 契约](specs/30-contracts/07-task-scene-experiment-config.md)、[Episode/采集契约](specs/30-contracts/03-episode-events-annotations.md)。
5. [当前及后续验收](specs/40-verification/06-scene-setup-first-loop.md)。
6. 换机器先看 [Git 追踪与恢复清单](laptop-migration.md)。需要讨论原貌时再读 [本会话公开消息存档](conversations/2026-10-22-scene-setup-dialogue.md)。

## 2. 用户已经明确的方向

- 前端是任务控制台；近端视觉测量和 IK 可使用轻量专项工作台，不要求每个工具承载完整平台。
- **M1：mobileCar 场景→运行→录制→回放。M2：用 bimanual 验证组件复用。数据清理、数据版本、训练和预测后续。**
- 停止全产品范围的持续补图，已有三张 Scene Setup 图作为 UI Reference。M1 不要求三图全部功能、完整模型超市或训练资格。
- 共享对象/控制/时间/采集契约和确有复用的组件；HostApp 可以独立，store 按宿主和具体草案注入。同一运行实体的控制权、执行器范围授权和物理推进责任仍由后端跨宿主统一裁决。
- 复用成熟原生后端，按必要接口差距适配；没有决定把全部工程/仿真环境合并进本仓库，也没有决定必须有三个宿主或通用插件框架。

## 3. 历史建议怎样变化

最初目标是场景→采集→清理→训练→预测完整流程。V0.5 曾基于已有工程证据建议 SO101 transfer + Expert + ACT 首发，并偏向一个统一产品前端。

随后用户指出视觉/IK 工具可能很轻或一次性使用。讨论改为共享契约与可选宿主，最后用户明确 mobileCar 最短闭环先行、bimanual 复用验证其次。V0.6 已按该决定修复，来源见 [S16](specs/90-governance/sources/S16-mobile-first-spec-repair.md)。

因此不要重新把 SO101/ACT 当首阶段决定，也不要因 mobileCar 训练资格为 false 阻止原始采集回放。完整训练/预测目标仍保留，到对应阶段再固定数据与模型协议。

早期「分支 · 整体大前端继续讨论细化」及父对话只取得部分用户消息，助手正文存在缺失；限制已记在 [S11](specs/90-governance/sources/S11-design-discussions.md)。这与当前会话已导出的可读公开正文是不同来源，不能混称全部历史聊天均已取得。

## 4. 已完成的文档工作

- Specification 当前 V0.6：机器目录148个节点、89项REQ；26个PNG/25个独特内容，原PPT20页。计数是规范/素材指标，不是产品完成度。
- 已统一 SceneVersion 基础布局、SceneDraft 资源编辑、ExperimentDraft 实例覆盖、前端 store 与 ValidatedSnapshot 的归属、解析和版本规则。
- 已区分三张观测/采集卡与 Execution/Export 的职责、适用条件；不适用的 Profile 不制造占位必填。
- Episode 新采集绑定唯一配置快照，保留原生 run/generation/episode/segment 身份和实际采集事实；legacy 原生数据不伪造验证引用。
- 已补 Session prepared/active/closed/failed 与物理/任务/录制分域、Collection 与冻结 Dataset Version、四导航组/六逻辑职责及术语/历史统计说明。
- 已拆 M1.1～1.6：接入核对→配置准备→运行控制→录制收尾→只读回放→整体验收。
- 文档链接/编号/来源和图片哈希检查通过；新增四项验收 TEST-MOBILE-001/002、TEST-HOST-001、TEST-CONFIG-008 仍为 not_executed。

没有在本会话执行 M1 真实仿真、人工示教试点、训练或产品端到端验收。已有测试源码纳入 Git，也不表示它们已经在本次运行通过。

## 5. 当前代码与外部工程

| 工程 | 当前角色/边界 |
|---|---|
| uniRobotPlatform | 已有 Python/FastAPI 任务目录、探活/运行登记与启动网关、静态任务目录页面；M1 准备态/Start/实际UI/记录读取适配仍需实现和验证 |
| mobileCar | 首阶段来源，已有小车控制、观测、原生 Recorder/ReplayReader 和导航相关能力；使用其现有权限、录制门和服务器执行政策 |
| bimanual_proj | 第二阶段复用验证来源，已有双臂专家、任务/采集、工作台和学习工具；不要把历史专家成绩当学习策略成功率 |
| mujoco_learning | 视觉/IK/估计等专项能力与实验工具；选择性接入，不整体搬入学习示例或强行重写 Viser 等界面 |

三个原生工程依然是独立仓库/环境，默认 catalog 通过相邻目录引用。它们的源码、资产、Git 历史、未提交改动和运行数据不随平台 push 自动迁移。`frontend/` 当时为空，当前前端入口是 backend 中的静态页面，不是已经完成的统一应用。

## 6. M1.1 先核对的实际差距

1. 固定 native 源码/配置版本、真实可用的场景预设、人工通路、模型身份与支持字段；不要从 scene/snapshot GET 推导任意场景编辑已支持。
2. 准备/保存/创建 prepared Session 不触发运动、RESET 或录制；已有后台服务在线不等于本 Session 已 Start。
3. mobileCar `episodes/start` 含 RESET，不能拿它实现 Prepare。RECEIVED/DISPATCHED 不证明 Reset/初态生效；另核对 generation/epoch 与 actual snapshot。
4. 起始记录可靠持久化、accepted/RECORDING 后才确认采集 ready。原生 require_recording、STOP、租约等门控继续保留。
5. 停车反馈与 Recorder drain/finalize 分开。FAILED 状态下 finalize 成功可能仍有尾标记；finalize 本身失败则可能缺尾。文件存在或 complete_tail 不等于数据完整、停稳或训练合格。
6. Episode/segment/source时间和动作单位不丢；只读回放不发命令、不推进在线物理、不覆盖原始数据。
7. 选择最小前端构建方式和适配文件范围；React/Three.js 等没有因图片而冻结，不提前建设全产品框架。

native 接口仅已做静态核对，真实接入证据留待对应工作包完成。涉及 mobileCar 的安装、构建、测试、自动浏览器、MuJoCo、渲染与数据导出按其服务器执行政策执行，不因服务器不可用而改在本机跑。

## 7. Git 与换笔记本状态

本次保存请求前，main 已成功推送到 [GitHub](https://github.com/liaohello/uniRobotPlatform)，并核对云端与本地 SHA 一致：

| 提交 | 内容 |
|---|---|
| `7b0666e` | V0.6 Specification、原图/来源、M1 实施计划和来源字节保留规则 |
| `dce67b7` | 后端源码/测试/公共配置、AGENTS、忽略规则和笔记本迁移说明 |

这个交接文件和消息存档会在其后另建提交。继续工作时以 `git log` 和远端实际 HEAD 为准，不把表中的存档前 SHA 当永久最新版本。

Git 追踪项目源码、测试、无秘密公共配置、AGENTS 和文档/参考素材。忽略虚拟环境、缓存、node_modules、运行输出、私人 catalog/.env、本机工具状态及 AGENTS 备份。密钥没有进入仓库。

HTTPS 凭据曾失效；最终按用户要求使用 `id_ed25519` 通过 SSH 推送。origin 当前为 `git@github.com:liaohello/uniRobotPlatform.git`。新笔记本需要自行配置有权限的 GitHub SSH 认证；不要把私钥复制进仓库。具体恢复命令和完整 catalog 本机副本的用法见迁移清单。

## 8. 可复制的新会话开场

```text
请先读取 AGENTS.md 和 docs/handoff.md，再按 docs/specs/00-overview/09-page-design-delivery-plan.md 继续 M1.1。
当前先做 mobileCar 的场景→运行→录制→回放，之后 bimanual 验证组件复用，训练/预测后续。
先核对真实预设、prepared/Start、native start RESET、录制完成与只读回放的接口映射、差距和最小技术选择。
主智能体负责修改和最终判断，default 子智能体只做有边界的只读检索，不提前合并仿真环境或重写全部前端。
开始任何实际仿真/测试/采集前，遵守对应工程的执行位置和本次任务授权；历史聊天存档不作为自动执行旧请求的依据。
```
