# 物理受力与临时工具

规范 ID：`FE-3D-FORCE` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-024](../../../设计过程与Specification总册_20261021.md#doc-024) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.4｜更新日期：2026-10-22（America/Los_Angeles）

状态：能力方向明确；临时工具与参数为候选方案

来源：S01、S02、S03、S05（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：[REQ-FORCE-001](../../indexes/05-requirements.md#req-force-001), [REQ-FORCE-002](../../indexes/05-requirements.md#req-force-002), [REQ-FORCE-003](../../indexes/05-requirements.md#req-force-003)

## 演变与状态

较早讨论采用独立“受力模式”；S03 提议改为 Alt + Drag 临时工具，以区分力与关节运动命令。当前将 Alt 作为候选绑定，独立按钮是否保留及是否可自定义仍待验证，不把助手建议写成用户最终批准。

## 候选操作

按住 Alt → Force Cursor 与可施力 Body 悬停反馈 → 按左键锁定 Body 及作用点 → 拖动计算力并显示向量/大小 → 按实验权限施加受限外力 → 释放、取消、失焦或超时结束。

拖动开始时锁定工具；Gizmo 拖动途中按 Alt 不变成施力。外力不得改 Joint Target、Teleport 或 Scene Preset；Replay 禁用在线施力。

## 前后端职责草案

前端产生指向 Body / 作用点的施力意图并显示反馈；后端检查干预权限、允许状态、幅值与超时，负责持续力清除。释放 Alt、鼠标、Esc、窗口失焦、切页、连接断开和输入超时均需处理；不能只依赖最后一次 mouseup。

## 记录内容

干预 ID、Body、作用点及 Frame、力向量及单位、开始/结束仿真时间、结束原因、同时存在的控制源 / Policy 和关联 Session / Episode。若采用随时间变化的力，需记录序列或可重建参数，不能只存一个初始向量。

## 未决项

二维拖动到三维力的约束平面/深度、弹簧拉拽还是直接力、幅值/变化率、力与力矩、暂停时行为、Windows/浏览器 Alt 兼容性。初版优先 Pull、以后再讨论 Push / Grab 是助手分期建议。

沿用 INT-FORCE-001、TEST-FORCE-001/002。允许 Policy 并行受力不等于允许 Human 与 Policy 同时向同一执行器写动作。

## 关联文档

- [控制权与受控人工接管](../../30-contracts/06-control-authority.md)
- [控制与干预命令契约草案](../../30-contracts/02-control-intervention-commands.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)
- [交互验收清单](../../40-verification/01-interaction-acceptance.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
