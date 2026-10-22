# Inspector 与层级联动

规范 ID：`FE-PANEL-INSPECTOR` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-027](../../../设计过程与Specification总册_20261021.md#doc-027) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.4｜更新日期：2026-10-22（America/Los_Angeles）

状态：选择联动为历史草案；监控定位已确认

来源：S03、S04、S05（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：[REQ-SEL-005](../../indexes/05-requirements.md#req-sel-005)

## 内容草案

| 选择 | Inspector |
|---|---|
| Link | 名称、所属 Arm、关联 Joint / Body、可用操作 |
| Joint | Actual / Target、限位、单位、控制来源、状态反馈 |
| Arm | 关节列表、Actual/Target TCP、Gripper、Authority、错误 |
| 多 Arm | 分组摘要；可显式指定 Active Arm |
| 环境对象 | 位姿与可编辑/可施力属性，按工作区约束 |

单臂选中：Viewport 全链高亮、Hierarchy 定位展开、Inspector 展示所属内容。多臂选中：保留各臂状态，不自动产生联合 TCP Gizmo。

关节滑条/数值默认以监控为主；默认只读为助手建议。若另有编辑入口，必须有明确工具状态和权限提示。Actual / Target 不应仅以颜色区分，应有文本标签与单位。

显示“当前选择”与“谁拥有控制权”两个区域。若控件不可用，应提供具体原因，如尚未接管、Replay、无此能力、不可达、数据过期；不要将所有情况笼统写为错误。

## 关联文档

- [选择、相机与整臂框选](../07-viewport-tools/02-selection-camera.md)
- [关节操控与监控](../07-viewport-tools/03-joint-manipulation.md)
- [控制权与受控人工接管](../../30-contracts/06-control-authority.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
