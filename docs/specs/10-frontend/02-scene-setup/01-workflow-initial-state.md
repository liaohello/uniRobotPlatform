# Scene Setup｜场景布置

规范 ID：`FE-SCENE-WORKFLOW` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-015](../../../设计过程与Specification总册_20261021.md#doc-015) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.6（2026-10-22）｜更新日期：2026-10-22（America/Los_Angeles）；原始内容来源保留。

状态：独立模块已确认；具体流程为方案

来源：S02、S04、S05（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：[REQ-SCENE-001](../../indexes/05-requirements.md#req-scene-001), [REQ-SCENE-002](../../indexes/05-requirements.md#req-scene-002)

## 职责与入口

负责机器人实验初态和配置，不承担完整三维建模器职责。用户已确定需要单独的场景布置部分；以下控件和流程由助手建议。

进入后选择已有 MuJoCo 场景和机器人，按可配置 Observe / Edit 模式观察或编辑。Scene Hierarchy 选择允许编辑的对象，在 3D 中平移 / 旋转，Inspector 显示位姿和坐标系。

## 建议流程

选择固定场景/机器人与 Task Template → 编辑 ExperimentDraft 允许初态覆盖 → 选择适用执行/采集配置 → 检查并保存 → 创建 prepared Session → 在运行视图显式 Start。基础资源编辑另走 SceneDraft，不覆盖运行态。

| 配置域 | 内容 | 待确定 |
|---|---|---|
| 场景 | 既有场景、可编辑物体 | 资产来源与允许增删范围 |
| 初态 | 机器人关节、物体位姿 | 数值输入、碰撞时提交规则 |
| 任务 | 类型、目标、成功条件 | 不同任务配置 schema |
| 仿真 | 随机种子、必要物理参数 | 哪些参数允许前端编辑 |
| 传感 / 录制 | Profile、必需数据流 | 缺失流是阻塞还是告警 |
| 版本 | 场景预设、实验配置版本 | 保存与覆盖规则 |

## 关键边界

Move Object 修改场景初态；Alt 拖动施力影响在线物理过程。两者可共享 Picking / Gizmo 渲染，但不能共享无区分的修改操作。对在线 Session 的任何配置应用应显式确认目标 Session 和后果；是否必须先停止或新建运行尚未冻结。

## 验收草案

Observe 不写场景；Edit 只写可编辑对象；保存能复现初态与配置；在 Scene Setup 编辑草案时不改变后台运行机器人；无效初态给出对象级原因。场景切换、未保存变更、Reset 的细节待原型确定。

## 关联文档

- [独立状态域与运行模型](../../00-overview/04-runtime-state-domains.md)
- [共用 3D Viewport](../07-viewport-tools/01-viewport-contexts.md)
- [选择、相机与整臂框选](../07-viewport-tools/02-selection-camera.md)
- [任务、观测与数据配置](../../00-overview/03-task-and-observation-profiles.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## V0.2 功能节点入口

本包按任务配置展开，不按导航/感知/IK 各复制一套页面：[模板选择](02-task-template-configuration.md)、[SO101 2D/3D 摆放](03-so101-tabletop-layout.md)、[地图与 Waypoint](04-map-waypoint-editor.md)。场景与物体配置交给 [Scene Builder](../../20-backend/01-session-scene/03-scene-builder-assets.md)，在线控制和扰动留在 Simulation。

## 页面图与设计归属（V0.3）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E5%9C%BA%E6%99%AF%E9%85%8D%E7%BD%AE%E7%95%8C%E9%9D%A2.png)

[PAGE-02 页面设计与修正](../page-designs/02-scene-setup.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
