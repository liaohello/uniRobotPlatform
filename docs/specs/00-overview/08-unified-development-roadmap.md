# 共用契约与任务控制台的增量路线

规范 ID：`SYS-DELIVERY-SLICES` · 责任层：系统 · 版本：V0.7（2026-10-23）

来源：[S16](../90-governance/sources/S16-mobile-first-spec-repair.md)、[S11](../90-governance/sources/S11-design-discussions.md)、[S17](../90-governance/sources/S17-3d-workbench-replan.md)。当前 mobileCar→bimanual 次序与统一前端架构原则已由用户明确，具体技术/组件适配为工程建议；正式闭环验收未执行。

[上级](README.md) · [当前阶段详情](10-first-task-closed-loop.md)

## 当前顺序

| 阶段 | 交付 | 验收边界 |
|---|---|---|
| M1 | mobileCar 场景→运行→录制→回放 | 已支持预设、固定配置与实际初态、真实 Episode/segment、结束状态和只读回放；不要求训练资格 |
| M2 | bimanual 验证组件与契约复用 | 不同宿主/草案状态隔离，机器人能力与数据/命令接口注入，后端控制权不按宿主拆分 |
| 后续数据/模型阶段 | 审核清理、Collection/Dataset Version、训练和预测 | 按对应 recipe 的资格/split/IO 和真实产物验收；不回填为 M1 前置 |

切片状态与正式里程碑分开记录（2026-10-24）：

- 地图/Route 版本化读取与保存是 M1.3 范围内的**资源 API 切片**，其候选完成不表示 M1.3（运行与人工操作基础）已通过。
- M1.4 的机器人 STOP 与录制可靠结束已交付**契约与平台候选**，并在服务器完成无物理隔离集成；真实停车确认、8792 部署与真机驾驶仍未执行，因此 M1.4 工作包状态为"候选完成，验收未执行"。
- 两者都不改变 M1 整体验收状态：M1.6 的操作者闭环与 TEST-MOBILE-001/002 尚未通过。

M1 先统一主工作台骨架，再逐条接通功能。下一份前端产物是可操作的 3D 样板：对象树/视口/Inspector 联动、相机、Joint/TCP 目标预览与取消，再在同一界面接实时控制、录制和回放；详见 [M1.2a～M1.6](09-page-design-delivery-plan.md)。诊断页和元数据草案是接入基础，不是工作台已完成的依据。前端实现当前继续暂停，本轮仅修订计划。

样板不要求先完成三种任务的全产品 Mock。现有 Scene Setup 与 Simulation 图继续作参考；Waypoint 的 V1 编辑保存范围保留，导航执行按独立切片接入。

## 复用边界

共享目标是对象/命令/时间/数据语义与确有复用的组件，不强制所有专项工具合并为一个 HostApp 或使用同一技术栈。视觉测量和 IK 可保留轻量宿主；已有后端和仿真执行者继续复用。只读工具不另建控制通道，同一运行实例仅一个物理推进责任者。

上述轻量宿主边界不取消主平台的统一工作台：Setup / Simulation / Replay 使用一致的外壳、3D 与面板职责。当前工程方向沿用前端分析的 React + TypeScript、Three.js SceneView 复用；Dockview 先验证后采用，R3F 不作为重写前置。状态按宿主、草案、Session 与历史来源注入，不新增跨宿主可写全局单例。

进入具体适配前查 [本地与开源资源登记](../references/open-source-resource-registry.md)，按需要验证候选库；不将所有 PoC、依赖升级或整个仓库迁移作为 M1 门槛。HostApp 只需上下文与依赖注入约定，不建设通用插件框架。

V0.5 的 F0/R1/SO101+ACT 首发建议保留于历史来源，当前以 S16/M1/M2 为准。验收见 [当前及后续闭环](../40-verification/06-scene-setup-first-loop.md)，既有 TEST-ARCH-001 继续覆盖共享骨架部分。
