# S16｜mobileCar 优先、按宿主复用与规范修复授权

规范 ID：`SRC-S16-MOBILE-FIRST-REPAIR` · 责任层：来源档案 · 版本：V0.6（2026-10-22，America/Los_Angeles）

来源：当前会话用户直接消息。与历史材料中的助手建议分开记录。

## 当前已确认的范围

> 先用 mobileCar 把“场景→运行→录制→回放”这条最短闭环跑通，再用 bimanual 验证组件复用。

用户认可前端作为任务控制台；视觉测量和 IK 等专项工具可以有较轻的独立界面，组件复用不要求所有工具承载完整平台。用户要求审核 Scene/Experiment、Profile、Episode、Workspace、Session、Collection 和计数的一致性；审核后直接授权“帮我进行修复”“还是使用多agents”。

授权范围：修复 Specification、来源/索引和待执行验收，不启动产品实现、仿真、训练或仓库迁移。子代理负责只读检索/核验，主代理统一修改文档。

## 与旧基线的关系

- S15 的采集→清理→训练→预测是长期完整流程，继续保留。
- V0.5 的 SO101 + Expert + ACT 首发是助手建议，现由本次 mobileCar 首阶段决定取代；训练、数据资格和模型 IO 不作为本次四步闭环的完成条件。
- 三张 Scene Setup 图继续作为任务变体 UI Reference；不要求当前阶段全部实现，也不要求每个宿主共用一份全局 store。
- 多宿主表示应用入口可以独立，不要求必须三个宿主、三个仓库、微前端或通用插件框架。草案/界面状态按作用域隔离；同一运行实例的控制权和物理推进仍由后端统一裁决。

## 修复中的证据与设计强度

用户明确的是阶段顺序、轻量工具边界和修复授权。具体对象命名、状态表、Profile 适用条件、实例覆盖解析与采集映射属于依据本次审核收敛的设计基线，不代表已有 API 或产品已通过验收。计数中的历史值保留版本标记，不改写历史来源。

mobileCar 原生接口和录制行为仅做静态源码核对：当前场景/snapshot 只读，start 含 RESET 边界，录制收尾和停车确认独立；不能从接口名称推断任意场景编辑或创建未开始 Session 已接通。原生文件不为规范修复而改写。

[当前阶段](../../00-overview/10-first-task-closed-loop.md) · [配置契约](../../30-contracts/07-task-scene-experiment-config.md) · [Episode 契约](../../30-contracts/03-episode-events-annotations.md) · [修订记录](../07-change-log.md)
