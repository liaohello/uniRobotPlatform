# Dataset Management｜数据管理

规范 ID：`FE-DATA-BROWSER` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-018](../../../设计过程与Specification总册_20261021.md#doc-018) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.6（2026-10-22）｜更新日期：2026-10-22（America/Los_Angeles）；原始内容来源保留。

状态：多 Episode 管理与导出方案；尚待独立评审

来源：S02、S05、S07（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：[REQ-DATA-001](../../indexes/05-requirements.md#req-data-001), [REQ-DATA-002](../../indexes/05-requirements.md#req-data-002)

## 职责

面向多个 Episode 的组织、查找、筛选、检查、版本和导出；单条 Episode 的行为分析交给 Replay。将其单列工作区是助手建议。

## 列表与详情草案

显示任务、机器人、采集时间、控制源组成、观测 Profile、Episode 时长、任务结果、数据完整性、标注状态和用途资格。支持从某条记录进入 Replay，返回时保留筛选条件。

| 判断 | 示例 | 与其他判断的关系 |
|---|---|---|
| Recording Integrity | 是否缺帧、丢动作、时间异常 | 与任务成功独立 |
| Task Outcome | 成功、失败、未完成、未知 | 与可训练性独立 |
| Training Eligibility | 对指定数据配方是否满足观测/动作/标签要求 | 需要绑定用途和规则版本 |

任务失败但记录完整可用于故障分析；成功但缺相机帧可能不满足某个训练配方。不能用一个绿色“有效”字段代替三项判断。

## 导出草案

选中 Dataset Version / Episode 筛选结果 → 指定导出配方 → 检查相机键、动作维度、单位、频率、时间对齐、标签版本 → 导出并给出报告。

LeRobot 作为明确相关数据生态保留；具体目标版本和 schema 不在本文中假定。导航、视觉伺服和双臂动作的数据语义不同，统一采集底座不意味着可无差别混成同一种 action 向量。

原始数据保存、派生变换、数据划分和人工筛除需保留来源关系。是否支持大规模存储、删除、权限和云上传不属于已讨论的 V1 承诺。

## 关联文档

- [Replay & Annotation｜同步回放与标注](../04-replay-annotation/01-synchronized-playback.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)
- [Dataset、Training、Checkpoint 与 Evaluation 关系](../../30-contracts/05-dataset-model-lineage.md)
- [回放、标注与数据管理验收](../../40-verification/03-replay-data-acceptance.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## V0.2 Data 共用导航

Data 导航组合 Episode Library、Episode Detail（回放/标注/质量审核）和 Dataset Collections。Library 负责搜索筛选，Detail 负责单条轨迹，Collections 负责多条轨迹集合、划分、版本与导出；逻辑职责不合并。返回列表保留过滤条件；由刚结束录制入口直接定位该 Episode。

单条审核可引用已命名集合，筛选结果、标注版本和 Dataset Version 分别可追踪，不因修改标签就改写历史数据。

## V0.3 列表与版本页面图

V0.6 当前 M1 只需原始 Episode 列表/重载/只读回放，M2 验证复用；V0.5 的审核/清理→固定数据版本→训练要求作为后续目标保留。到对应阶段再做 Collection/版本/资格/split；资格 false 阻止相应用途训练，不阻止 M1 回放。具体绑定见 [CT-LINEAGE](../../30-contracts/05-dataset-model-lineage.md)，阶段交付见 [首条闭环](../../00-overview/10-first-task-closed-loop.md)，验收 [TEST-LOOP-002/003](../../40-verification/06-scene-setup-first-loop.md)。

[Episode Library](../page-designs/04-episode-library.md)、[Collections](../page-designs/06-dataset-collections.md)、[Dataset Version](../page-designs/07-dataset-version.md) 分别展示轨迹检索、集合组织与固定版本/导出。图片中的 Data 页面顶部 Replay 控件不采用；底部预览可保留摘要，完整分析进入 Episode Detail。Library/Version 的原图仅覆盖局部，后续仍需专图。

## 页面图与设计归属（V0.3）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E6%95%B0%E6%8D%AE%E9%9B%86%E7%AE%A1%E7%90%86%E7%95%8C%E9%9D%A2.png)

[PAGE-06 页面设计与修正](../page-designs/06-dataset-collections.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
