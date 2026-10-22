# 实体主臂与仿真从臂

规范 ID：`FE-SIM-LEADER` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-025](../../../设计过程与Specification总册_20261021.md#doc-025) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.4｜更新日期：2026-10-22（America/Los_Angeles）

状态：遥操作与无主臂摄像头为历史基线；设备协议待定义

来源：S01、S02、S03、S05、S07（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：[REQ-LEADER-001](../../indexes/05-requirements.md#req-leader-001), [REQ-LEADER-002](../../indexes/05-requirements.md#req-leader-002), [REQ-LEADER-003](../../indexes/05-requirements.md#req-leader-003)

## 已讨论需求

左右实体主臂分别映射到 SO101 MuJoCo 从臂，支持双臂遥操作录制。后续已澄清实体主臂无独立摄像头，只需状态监控与控制；S01 中早期“捕捉画面”不能继续作为必需相机视图。

## 前端建议展示

设备连接、左右映射、标定状态、输入关节、从臂实测与目标、跟踪误差、当前控制权及断连原因。三路场景/腕相机属于任务观测，不能与实体主臂摄像头混为一谈。

## 进入控制草案

连接 → 识别设备 → 标定 / 校验映射 → 请求对应 Arm 控制权 → 对齐与启用 → 实时跟随 → 录制并标明来源。鼠标选择另一条 Arm 不自动切换主臂映射、解除授权或抢占控制。

关节映射的顺序、方向、比例、零偏、限位、夹爪单位和控制频率需适配；不能只按相同数组下标假定兼容。超时/断连后如何保持或停止、重连如何重新对齐由后端协议定义，目前没有冻结参数。

鼠标与主臂在同一 Arm 的切换需要明确来源与权限；一臂 Human、一臂 Policy 的混合控制是架构允许讨论的情形，不等于已承诺实现联合协作策略。

## 关联文档

- [控制权与受控人工接管](../../30-contracts/06-control-authority.md)
- [机器人能力与适配边界](../../00-overview/06-robot-capabilities.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)
- [工作区、运行与记录验收](../../40-verification/02-workspace-runtime-acceptance.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
