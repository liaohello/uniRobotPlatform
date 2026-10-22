# 选择、相机与整臂框选

规范 ID：`FE-3D-SELECTION` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-021](../../../设计过程与Specification总册_20261021.md#doc-021) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.4｜更新日期：2026-10-22（America/Los_Angeles）

状态：历史基线与助手草案混合；边缘命中规则未冻结

来源：S01、S02、S03（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：[REQ-SEL-001](../../indexes/05-requirements.md#req-sel-001), [REQ-SEL-002](../../indexes/05-requirements.md#req-sel-002), [REQ-SEL-003](../../indexes/05-requirements.md#req-sel-003), [REQ-SEL-004](../../indexes/05-requirements.md#req-sel-004), [REQ-SEL-007](../../indexes/05-requirements.md#req-sel-007), [REQ-VIEW-002](../../indexes/05-requirements.md#req-view-002)

## 已有交互基线与来源强度

鼠标悬停高亮、单击选择、双击所属 Arm、同臂多个不同 Link 框选提升等为已讨论基线。同臂提升在历史记录中明确为用户决定；Ctrl 多选和跨臂细节在 S03 助手草案中完整呈现，原始用户逐字记录未全部取回。

| 输入 | 行为 | 备注 |
|---|---|---|
| 空白左键拖动 | Orbit | 应是拖动，不是单击就旋转 |
| 滚轮 | Zoom | 限制范围待定 |
| Hover Link | 局部高亮 | 与持续选中区分 |
| Click Link | 选择 Link / Joint | Link 到 Joint 的精确映射待定义 |
| Double Click Link | 选择所属 Arm，替换旧选择 | 选择不发运动命令 |
| Shift + Drag | 框选 | 遮挡 / 命中规则未决 |
| Ctrl + Double Click | 切换所属 Arm 的选中状态 | 历史方案 |
| Ctrl + Shift + Drag | 追加框选结果 | 不自动联合 IK |
| 中键拖动、F | Orbit、聚焦 | 助手补充建议 |

## 框选规则草案

| 命中 | 无 Ctrl | Ctrl 追加 |
|---|---|---|
| 同一 Arm 至少两个不同 Link | 提升到 Arm，替换旧选择 | 追加该 Arm |
| 只命中一个 Link | 保持 Link 级 | 普通追加规则待细化 |
| 多条 Arm 各有多个 Link | 不自动形成多臂选择，提示 Ctrl | 追加命中的 Arm |
| 混入环境物体 | 旧草案写“保持对象级，不自动提升” | 同样需澄清 |

无 Ctrl 跨 Arm 框选时，是保留旧选择还是只给提示，尚未写清；“不提交多臂”不能自动解释为清空选择。环境混选是否整体禁止提升或仅环境对象不提升，也需澄清。

## 三种不同状态

Selected Arms：所选集合；Active Arm：单个当前操作目标；Control Owner：后端授权。选择反馈可同步 Viewport 高亮、Hierarchy 展开和 Inspector；多臂选择默认展示摘要，不出现可执行联合 Gizmo。

## 输入仲裁

建议拖动开始时锁定工具与修饰键语义。单击/双击不能在等待判定期间先发送运动；框选不触发相机 Orbit；文本输入焦点不响应机器人快捷键。完整优先级需要原型验证。

沿用旧编号：INT-SEL-001/002/003；验收 TEST-SEL-001 至 TEST-SEL-006。

## 关联文档

- [控制权与受控人工接管](../../30-contracts/06-control-authority.md)
- [共用 3D Viewport](01-viewport-contexts.md)
- [Inspector 与层级联动](../08-observation-inspector/01-hierarchy-inspector.md)
- [关节操控与监控](03-joint-manipulation.md)
- [交互验收清单](../../40-verification/01-interaction-acceptance.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
