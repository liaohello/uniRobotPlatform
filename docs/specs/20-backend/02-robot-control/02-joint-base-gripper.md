# 关节、底盘与夹爪命令执行

规范 ID：`BE-CONTROL-ACTUATORS` · 责任层：后端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-012](../../../设计过程与Specification总册_20261021.md#doc-012)、[doc-022](../../../设计过程与Specification总册_20261021.md#doc-022)、[doc-025](../../../设计过程与Specification总册_20261021.md#doc-025)、[doc-032](../../../设计过程与Specification总册_20261021.md#doc-032)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-JOINT-002](../../indexes/05-requirements.md#req-joint-002)、[REQ-OBS-003](../../indexes/05-requirements.md#req-obs-003)

## 目标与责任边界

把合法控制意图交给既有机器人控制器，发布命令结果与实际反馈。屏幕拖动映射、Joint Ring 和监控滑条属于前端。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 动作语义 | 显式关节顺序、单位、绝对/增量、夹爪开度与底盘速度参考系。 |
| 目标层 | Joint Target、TCP 规划产物、实际状态分别保留，不用反馈反推并冒充动作标签。 |
| 受理与执行 | 权限、模型限位、状态和目标有效性由后端检查；Accepted 与到位分开。 |
| 持续命令 | 速度与目标流分别定义过期和中止；不把所有工具松手处理成同一动作。 |

## 未决与依赖

关联 OQ-009、OQ-017、OQ-022。LanderPi 与 SO101 的动作单位和夹爪映射先核对现有接口，不强行统一原生数组。

## 关联规范

- [机器人能力与适配边界](../../00-overview/06-robot-capabilities.md)
- [关节操控与监控](../../10-frontend/07-viewport-tools/03-joint-manipulation.md)
- [控制与干预命令契约草案](../../30-contracts/02-control-intervention-commands.md)
- [时间、坐标系与命令生命周期](../../30-contracts/04-time-frames-units.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)

## 验收入口

- [TEST-JOINT-001](../../40-verification/01-interaction-acceptance.md#test-joint-001)（现有草案，未执行；依赖的未决规则须先收敛）。
