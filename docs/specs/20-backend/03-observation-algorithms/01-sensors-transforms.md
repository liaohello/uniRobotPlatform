# 传感器、状态与时刻变换

规范 ID：`BE-OBSERVATION-STREAMS` · 责任层：后端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-009](../../../设计过程与Specification总册_20261021.md#doc-009)、[doc-012](../../../设计过程与Specification总册_20261021.md#doc-012)、[doc-014](../../../设计过程与Specification总册_20261021.md#doc-014)、[doc-029](../../../设计过程与Specification总册_20261021.md#doc-029)、[doc-031](../../../设计过程与Specification总册_20261021.md#doc-031)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-OBS-001](../../indexes/05-requirements.md#req-obs-001)、[REQ-OBS-002](../../indexes/05-requirements.md#req-obs-002)、[REQ-OBS-005](../../indexes/05-requirements.md#req-obs-005)

## 目标与责任边界

提供有身份、时间、Frame 和有效性的观测，不由面板是否可见决定算法输入或录制内容。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 流描述 | 区分小车 RGB-D/SLAM/本体与双臂三相机，缺失能力明确发布。 |
| 时间 | 保留源时刻、有效性与必要变换；相机随关节运动，不能固定使用起始世界外参。 |
| 分发 | UI、算法、录制使用各自 Profile；隐藏面板不停止原始采集。 |
| 诊断 | 算法可见数据与诊断/真值路径分开，精确允许集合需采集协议确定。 |

## 未决与依赖

关联 OQ-020、OQ-021、OQ-026。传输方式、频率与同步阈值未冻结。

## 关联规范

- [任务、观测与数据配置](../../00-overview/03-task-and-observation-profiles.md)
- [时间、坐标系与命令生命周期](../../30-contracts/04-time-frames-units.md)
- [传感器与算法观测面板](../../10-frontend/08-observation-inspector/02-sensors-algorithms.md)
- [Robot / World State 契约草案](../../30-contracts/01-robot-world-state.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)

## 验收入口

- [TEST-REC-003](../../40-verification/02-workspace-runtime-acceptance.md#test-rec-003)（现有草案，未执行；依赖的未决规则须先收敛）。
