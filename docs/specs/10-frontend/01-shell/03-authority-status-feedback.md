# 控制权、接管与全局状态反馈

规范 ID：`FE-SHELL-AUTHORITY` · 责任层：前端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-010](../../../设计过程与Specification总册_20261021.md#doc-010)、[doc-013](../../../设计过程与Specification总册_20261021.md#doc-013)、[doc-016](../../../设计过程与Specification总册_20261021.md#doc-016)、[doc-027](../../../设计过程与Specification总册_20261021.md#doc-027)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-AUTH-001](../../indexes/05-requirements.md#req-auth-001)、[REQ-AUTH-002](../../indexes/05-requirements.md#req-auth-002)、[REQ-AUTH-003](../../indexes/05-requirements.md#req-auth-003)

## 目标与责任边界

负责把后端认可的控制源、请求中状态和拒绝原因呈现给操作者。接管裁决、旧动作失效和保持策略属于后端；转移语义由共享契约定义。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 当前对象 | 分别显示观察选择、Active Arm 与当前控制源；选择本身不抢占权限。 |
| 显式接管 | 用户已确认 VLA 运行时使用按钮进入受控人工干预；Pending 等显示状态是草案。 |
| 请求反馈 | 取得后端确认之前，不把可执行工具显示为已授权；失败显示实际状态与原因。 |
| 显示与布局 | 状态入口可达性、范围选择器、告警位置需要布局原型；不在本页重新定义移交协议。 |

## 未决与依赖

关联 OQ-002、OQ-017、OQ-018、OQ-025。按钮位置、全局停止入口和接管范围尚未冻结。

## 关联规范

- [控制权与受控人工接管](../../30-contracts/06-control-authority.md)
- [独立状态域与运行模型](../../00-overview/04-runtime-state-domains.md)
- [控制与干预命令契约草案](../../30-contracts/02-control-intervention-commands.md)
- [Inspector 与层级联动](../08-observation-inspector/01-hierarchy-inspector.md)
- [交互验收清单](../../40-verification/01-interaction-acceptance.md)

## 验收入口

- [TEST-AUTH-002](../../40-verification/01-interaction-acceptance.md#test-auth-002)（现有草案，未执行；依赖的未决规则须先收敛）。

## 页面图与设计归属（V0.3）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E5%B9%B3%E5%8F%B0%E4%BB%AA%E8%A1%A8%E7%9B%98.png)

[PAGE-01 页面设计与修正](../page-designs/01-home.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
