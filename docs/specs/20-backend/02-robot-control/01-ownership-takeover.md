# 控制源仲裁与受控接管执行

规范 ID：`BE-CONTROL-AUTHORITY` · 责任层：后端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-013](../../../设计过程与Specification总册_20261021.md#doc-013)、[doc-016](../../../设计过程与Specification总册_20261021.md#doc-016)、[doc-032](../../../设计过程与Specification总册_20261021.md#doc-032)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-AUTH-001](../../indexes/05-requirements.md#req-auth-001)、[REQ-AUTH-002](../../indexes/05-requirements.md#req-auth-002)、[REQ-AUTH-003](../../indexes/05-requirements.md#req-auth-003)、[REQ-AUTH-004](../../indexes/05-requirements.md#req-auth-004)

## 目标与责任边界

负责执行器范围的权限裁决、旧控制源停止、新来源授权和恢复。前端显示接管流程，共享契约定义跨边界语义，本页定义后端需要提供的执行能力。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 范围 | Base / Arm / Gripper / 执行器组的授权粒度尚未确定。 |
| 接管 | 显式请求后处理 Policy/Expert 输出、在途命令与 action chunk，再反馈实际授权结果。 |
| 失败 | 定义保持、拒绝、超时和恢复策略；失败不自动推断旧策略仍在执行。 |
| 恢复 | 显式恢复策略时核对当前状态，队列重建/策略重初始化尚待设计。 |

## 未决与依赖

关联 OQ-017、OQ-018、OQ-019。租约、取消代数、超时数值不能从草案自动生成。

## 关联规范

- [控制权与受控人工接管](../../30-contracts/06-control-authority.md)
- [控制与干预命令契约草案](../../30-contracts/02-control-intervention-commands.md)
- [实体主臂与仿真从臂](../../10-frontend/03-simulation/03-leader-follower-panel.md)
- [交互验收清单](../../40-verification/01-interaction-acceptance.md)

## 验收入口

- [TEST-AUTH-003](../../40-verification/01-interaction-acceptance.md#test-auth-003)（现有草案，未执行；依赖的未决规则须先收敛）。

## V0.2 协议细化方向

接管屏障覆盖策略在途目标、动作队列及 Action Chunk，恢复时声明重新观测/决策或策略状态恢复，不直接继续旧尾段。部件控制与物理干预分别授权；细节参见 [共享控制权契约](../../30-contracts/06-control-authority.md)。

## V0.4 部件表需要的权威反馈

为每个授权范围提供当前 Owner、控制设备/生成器、转移中状态、允许的操作及拒绝/不可恢复原因。Coupled 展示真实的授权继承，夹爪命令通道仍按已实现能力处理。交还不能恢复未经同步的旧队列。

前端接管/交还按钮和按部件来源轨来自同一后端事件/状态，不由图中卡片的选中颜色生成。新图不是所有并行控制能力已经可用的证据。
