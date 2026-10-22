# TCP 求解、轨迹检查与执行

规范 ID：`BE-CONTROL-PLANNING` · 责任层：后端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-012](../../../设计过程与Specification总册_20261021.md#doc-012)、[doc-023](../../../设计过程与Specification总册_20261021.md#doc-023)、[doc-032](../../../设计过程与Specification总册_20261021.md#doc-032)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-TCP-001](../../indexes/05-requirements.md#req-tcp-001)、[REQ-TCP-003](../../indexes/05-requirements.md#req-tcp-003)、[REQ-TCP-004](../../indexes/05-requirements.md#req-tcp-004)

## 目标与责任边界

接收 TCP 目标及约束，区分终点 IK、候选轨迹、检查结果与实际执行。算法可以复用现有项目，本文不选择新的求解器。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 求解 | 结合实际自由度返回候选关节配置、残差与失败原因，不能保证任意六维目标。 |
| 轨迹 | 有 q(t) 才能计算沿程 TCP/关节中心位置；仅终点解不伪造安全路径。 |
| 检查 | 标明限位、路径/碰撞检查与动态跟踪验证覆盖范围。 |
| 版本与取消 | 目标更新使旧候选如何失效、执行前复查和 Live 更新策略待定义。 |

## 未决与依赖

关联 OQ-010、OQ-011、OQ-012、OQ-013。规划能力、检查级别、目标版本、残差门槛待接口核对与原型收敛。

## 关联规范

- [TCP 操控与虚线运动轨迹](../../10-frontend/07-viewport-tools/04-tcp-trajectories.md)
- [控制与干预命令契约草案](../../30-contracts/02-control-intervention-commands.md)
- [Robot / World State 契约草案](../../30-contracts/01-robot-world-state.md)
- [时间、坐标系与命令生命周期](../../30-contracts/04-time-frames-units.md)

## 验收入口

- [TEST-TCP-002](../../40-verification/01-interaction-acceptance.md#test-tcp-002)（现有草案，未执行；依赖的未决规则须先收敛）。
