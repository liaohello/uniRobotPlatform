# 工作区、运行与记录验收

规范 ID：`QA-RUNTIME` · 责任层：验收 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-036](../../设计过程与Specification总册_20261021.md#doc-036) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.6（2026-10-22）｜更新日期：2026-10-22（America/Los_Angeles）；原始内容来源保留。

状态：待执行；运行策略含助手建议

来源：S02–S05（详见[来源档案](../90-governance/06-sources.md)）

关联需求：见需求追踪矩阵中的引用与相关主责规范

所有测试均为未执行的规格草案。

| ID | 场景 | 预期 |
|---|---|---|
| <a id="test-scene-001"></a>TEST-SCENE-001 | Observe 模式尝试编辑 | 不写 ExperimentDraft 实例覆盖或 SceneDraft 资源 |
| <a id="test-scene-002"></a>TEST-SCENE-002 | 编辑 ExperimentDraft 实例覆盖或独立 SceneDraft，后台 Session 运行 | 两种草案写入归属明确；都不覆盖活动快照和运行状态 |
| <a id="test-scene-003"></a>TEST-SCENE-003 | 保存配置并重新加载 | 初态和配置可关联复现 |
| <a id="test-nav-001"></a>TEST-NAV-001 | 历史：导航地图只读范围 | 旧“不出现鼠标设点”断言已由 S10 取代，退役保留；当前使用 TEST-NAV-003 至 006 |
| <a id="test-nav-002"></a>TEST-NAV-002 | Simulation 切到其他页 | 后台运行/录制/Authority 按 Session 持续 |
| <a id="test-input-003"></a>TEST-INPUT-003 | 键盘驾驶时离开视图或失焦 | 持续速度撤销；后端超时也生效 |
| <a id="test-profile-001"></a>TEST-PROFILE-001 | 切换小车/双臂 Profile | 对应观测、能力和输入正确；不误改算法/记录配置 |
| <a id="test-leader-001"></a>TEST-LEADER-001 | 选择另一 Arm | 不自行改变主臂映射与控制权 |
| <a id="test-leader-002"></a>TEST-LEADER-002 | 主臂断连 | 按已定义后端策略反馈；未定义前不可宣称通过 |
| <a id="test-rec-001"></a>TEST-REC-001 | Policy → 人工接管 → 恢复 | 控制源时间段、动作和事件可关联 |
| <a id="test-rec-002"></a>TEST-REC-002 | Policy 同时受物理扰动 | 动作源与外力干预分别记录 |
| <a id="test-rec-003"></a>TEST-REC-003 | 隐藏传感器面板 | 不隐式停止对应原始采集 |
| <a id="test-rec-004"></a>TEST-REC-004 | 停止/重置期间录制 | 按 CT-EPISODE 的 mobileCar 原生边界确认 Episode/segment 与 finalize；停车/录制/完整性独立，不支持录制中 Reset 则先显式 end，不伪报连续数据 |

交互延迟、帧率、同步误差、丢帧率和超时数值尚未冻结；先测量真实场景负载，再确定阈值。没有实测结果时不写“已通过”。

## 关联文档

- [Scene Setup｜场景布置](../10-frontend/02-scene-setup/01-workflow-initial-state.md)
- [全局信息架构与工作区](../10-frontend/01-shell/01-navigation-context.md)
- [Simulation｜在线仿真工作台](../10-frontend/03-simulation/01-workflow-task-panels.md)
- [Episode、采集、事件与标注契约](../30-contracts/03-episode-events-annotations.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)
