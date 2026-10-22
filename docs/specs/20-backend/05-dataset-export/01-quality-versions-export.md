# 数据质量、版本与训练出口

规范 ID：`BE-DATA-EXPORT` · 责任层：后端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-018](../../../设计过程与Specification总册_20261021.md#doc-018)、[doc-033](../../../设计过程与Specification总册_20261021.md#doc-033)、[doc-034](../../../设计过程与Specification总册_20261021.md#doc-034)、[doc-037](../../../设计过程与Specification总册_20261021.md#doc-037)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-DATA-001](../../indexes/05-requirements.md#req-data-001)、[REQ-DATA-002](../../indexes/05-requirements.md#req-data-002)

## 目标与责任边界

生成数据索引、用途资格、派生数据版本及导出报告。前端负责选择与预览，后端负责校验、转换和写入。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 三类结论 | 记录完整性、任务结果、特定训练用途资格分别判断。 |
| 版本与划分 | 追踪原始 Episode、筛选/变换、标注与数据划分。 |
| 导出配方 | 声明相机键、动作维度/单位/顺序、频率、对齐与目标格式版本。 |
| 兼容 | LanderPi 与 SO101 的原生动作不无差别拼接；LeRobot 目标版本需要实际核对。 |

## 未决与依赖

关联 OQ-022、OQ-024。存储规模、删除权限、云上传不在当前已确认承诺中。

## 关联规范

- [Dataset Management｜数据管理](../../10-frontend/05-datasets/01-browser-quality-export.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)
- [Dataset、Training、Checkpoint 与 Evaluation 关系](../../30-contracts/05-dataset-model-lineage.md)
- [回放、标注与数据管理验收](../../40-verification/03-replay-data-acceptance.md)

## 验收入口

- [TEST-EXPORT-001](../../40-verification/03-replay-data-acceptance.md#test-export-001)（现有草案，未执行；依赖的未决规则须先收敛）。

## V0.5 首条任务的最小清理与出口

按 [来源链契约](../../30-contracts/05-dataset-model-lineage.md) 固定清理修订、原始父 Episode、保留/排除原因、片段/变换、数据成员与同源组划分。归一化仅拟合 train；资格、完整性、任务结果独立。不可变 Dataset Version 必须带目标格式/IO schema 和加载验证报告；训练资格 false、空 train/val 或加载失败阻止训练。首任务只需一条支持 ACT recipe 的真实出口，具体格式版本从本地适配器核实，不从库名推导。

验收：[TEST-LOOP-002/003](../../40-verification/06-scene-setup-first-loop.md)。本轮不执行转换或删除原始文件。
