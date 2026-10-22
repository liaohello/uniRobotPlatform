# 物理扰动与持续外力管理

规范 ID：`BE-CONTROL-FORCE` · 责任层：后端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-013](../../../设计过程与Specification总册_20261021.md#doc-013)、[doc-024](../../../设计过程与Specification总册_20261021.md#doc-024)、[doc-032](../../../设计过程与Specification总册_20261021.md#doc-032)、[doc-033](../../../设计过程与Specification总册_20261021.md#doc-033)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-FORCE-002](../../indexes/05-requirements.md#req-force-002)、[REQ-FORCE-003](../../indexes/05-requirements.md#req-force-003)、[REQ-FORCE-004](../../indexes/05-requirements.md#req-force-004)

## 目标与责任边界

执行独立的物理干预请求，管理受力范围、限幅、有效期和清理。与关节控制权、Teleport 和初态编辑分别处理。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 校验 | 核对 Session/Body/作用点/Frame/单位、实验许可和允许状态。 |
| 执行 | 按已定义的受力模型施加外力，不写 Joint Target 冒充力。 |
| 清理 | 结束、取消、断连或有效期届满后撤销持续力，不仅依赖浏览器 mouseup。 |
| 记录 | 保留力随时间变化、实际作用范围、结束原因及并行 Policy 来源。 |

## 未决与依赖

关联 OQ-014、OQ-015、OQ-016。Alt 仅是前端候选绑定；力模型、力矩和幅值阈值尚未决定。

## 关联规范

- [物理受力与临时工具](../../10-frontend/07-viewport-tools/05-physical-force-tool.md)
- [控制权与受控人工接管](../../30-contracts/06-control-authority.md)
- [控制与干预命令契约草案](../../30-contracts/02-control-intervention-commands.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)

## 验收入口

- [TEST-FORCE-002](../../40-verification/01-interaction-acceptance.md#test-force-002)（现有草案，未执行；依赖的未决规则须先收敛）。
