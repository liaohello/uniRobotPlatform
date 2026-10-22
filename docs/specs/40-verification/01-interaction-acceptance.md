# 交互验收清单

规范 ID：`QA-INTERACTION` · 责任层：验收 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-035](../../设计过程与Specification总册_20261021.md#doc-035) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.1｜整理日期：2026-10-21（America/Los_Angeles）

状态：待执行；部分预期依赖未冻结方案

来源：S03、S04、S05（详见[来源档案](../90-governance/06-sources.md)）

关联需求：见需求追踪矩阵中的引用与相关主责规范

以下是待执行验收，未运行真实前端或 MuJoCo 测试，所有结果状态均为“未执行”。TEST-SEL、TEST-JOINT、TEST-TCP、TEST-FORCE、TEST-AUTH 编号沿用 V0.4。

| ID | 操作与预期 | 所验证规范 |
|---|---|---|
| <a id="test-sel-001"></a>TEST-SEL-001 | 普通选择另一条 Arm，替换旧 Arm Selection | Selection |
| <a id="test-sel-002"></a>TEST-SEL-002 | 框选同臂两个不同 Link，提升为 Arm | Selection |
| <a id="test-sel-003"></a>TEST-SEL-003 | Ctrl 可选择左右臂；松开后普通选择互斥 | Selection |
| <a id="test-sel-004"></a>TEST-SEL-004 | 全链高亮、Hierarchy/Inspector 正确联动 | Inspector |
| <a id="test-sel-005"></a>TEST-SEL-005 | 无 Ctrl 跨双臂框选不自动形成多臂集合 | Selection；保留旧选择细节待定 |
| <a id="test-sel-006"></a>TEST-SEL-006 | 任何 Selection 均不产生机器人运动命令 | Selection / Authority |
| <a id="test-joint-001"></a>TEST-JOINT-001 | 拖动选中 Joint 只改变该 Joint Target | Joint |
| <a id="test-joint-002"></a>TEST-JOINT-002 | 查看/操作默认监控控件不发运动命令 | Joint / Inspector |
| <a id="test-tcp-001"></a>TEST-TCP-001 | TCP Preview 不覆盖在线 Actual State | TCP |
| <a id="test-tcp-002"></a>TEST-TCP-002 | 仅 IK 终点时不伪称已有规划路径 | TCP |
| <a id="test-tcp-003"></a>TEST-TCP-003 | 候选、实际、关节中心轨迹可辨；切目标使旧候选失效 | TCP；显示方案待冻结 |
| <a id="test-force-001"></a>TEST-FORCE-001 | 候选 Alt 拖动命中正确 Body 并受限施力 | Physics |
| <a id="test-force-002"></a>TEST-FORCE-002 | Alt/鼠标释放、失焦、取消、连接断开/超时均撤销持续力 | Physics |
| <a id="test-input-001"></a>TEST-INPUT-001 | 正在 Gizmo 拖动时按 Alt，不改变操作语义 | Input / Physics |
| <a id="test-input-002"></a>TEST-INPUT-002 | 文本输入焦点下不响应机器人快捷键 | Input |
| <a id="test-auth-001"></a>TEST-AUTH-001 | 无权限不能驱动对应机器人范围 | Authority |
| <a id="test-auth-002"></a>TEST-AUTH-002 | Policy Active 拖动不隐式覆盖；接管 Pending 不开放控制 | Authority |
| <a id="test-auth-003"></a>TEST-AUTH-003 | 接管确认后旧策略动作/队列不再影响已移交范围 | Authority / Command |

遮挡拾取、单击/双击延迟、Alt 兼容性、直接拖动映射、轨迹默认显示应先用原型验证，再固化可量化验收阈值。此清单不等于自动化测试实现。

## 关联文档

- [选择、相机与整臂框选](../10-frontend/07-viewport-tools/02-selection-camera.md)
- [关节操控与监控](../10-frontend/07-viewport-tools/03-joint-manipulation.md)
- [TCP 操控与虚线运动轨迹](../10-frontend/07-viewport-tools/04-tcp-trajectories.md)
- [物理受力与临时工具](../10-frontend/07-viewport-tools/05-physical-force-tool.md)
- [控制权与受控人工接管](../30-contracts/06-control-authority.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)
