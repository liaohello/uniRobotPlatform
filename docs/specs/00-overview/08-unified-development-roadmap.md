# 共用契约与任务控制台的增量路线

规范 ID：`SYS-DELIVERY-SLICES` · 责任层：系统 · 版本：V0.6（2026-10-22）

来源：[S16](../90-governance/sources/S16-mobile-first-spec-repair.md)、[S09](../90-governance/sources/S09-unified-development-reuse-analysis.md)。当前 mobileCar→bimanual 次序已由用户明确，具体组件/适配为设计基线；验收未执行。

[上级](README.md) · [当前阶段详情](10-first-task-closed-loop.md)

## 当前顺序

| 阶段 | 交付 | 验收边界 |
|---|---|---|
| M1 | mobileCar 场景→运行→录制→回放 | 已支持预设、固定配置与实际初态、真实 Episode/segment、结束状态和只读回放；不要求训练资格 |
| M2 | bimanual 验证组件与契约复用 | 不同宿主/草案状态隔离，机器人能力与数据/命令接口注入，后端控制权不按宿主拆分 |
| 后续数据/模型阶段 | 审核清理、Collection/Dataset Version、训练和预测 | 按对应 recipe 的资格/split/IO 和真实产物验收；不回填为 M1 前置 |

F0 可按需验证组件手感和状态，不要求先完成三种任务的全产品 Mock。现有三张 Scene Setup 图继续作参考；Waypoint 的 V1 编辑保存范围保留，导航执行按独立切片接入。

## 复用边界

共享目标是对象/命令/时间/数据语义与确有复用的组件，不强制所有专项工具合并为一个 HostApp 或使用同一技术栈。视觉测量和 IK 可保留轻量宿主；已有后端和仿真执行者继续复用。只读工具不另建控制通道，同一运行实例仅一个物理推进责任者。

进入具体适配前查 [本地与开源资源登记](../references/open-source-resource-registry.md)，按需要验证候选库；不将所有 PoC、依赖升级或整个仓库迁移作为 M1 门槛。HostApp 只需上下文与依赖注入约定，不建设通用插件框架。

V0.5 的 F0/R1/SO101+ACT 首发建议保留于历史来源，当前以 S16/M1/M2 为准。验收见 [当前及后续闭环](../40-verification/06-scene-setup-first-loop.md)，既有 TEST-ARCH-001 继续覆盖共享骨架部分。
