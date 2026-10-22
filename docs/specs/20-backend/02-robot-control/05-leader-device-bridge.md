# 实体主臂设备桥与关节映射

规范 ID：`BE-CONTROL-LEADER` · 责任层：后端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-012](../../../设计过程与Specification总册_20261021.md#doc-012)、[doc-025](../../../设计过程与Specification总册_20261021.md#doc-025)、[doc-032](../../../设计过程与Specification总册_20261021.md#doc-032)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-LEADER-001](../../indexes/05-requirements.md#req-leader-001)、[REQ-LEADER-002](../../indexes/05-requirements.md#req-leader-002)、[REQ-LEADER-003](../../indexes/05-requirements.md#req-leader-003)

## 目标与责任边界

连接实体主臂并产生有来源的从臂动作，管理左右映射、标定、对齐与失效。主臂无独立摄像头为历史澄清；任务三相机不属于主臂设备。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 设备身份 | 左右设备识别、连接与标定状态。 |
| 映射 | 明确关节顺序、方向、零偏、比例、限位、夹爪单位及采样/控制频率。 |
| 启用 | 请求对应控制范围、对齐并启用；鼠标选择不改变设备映射。 |
| 失效 | 超时、断连、重连与鼠标来源切换的策略待冻结。 |

## 未决与依赖

关联 OQ-019、OQ-022。设备桥所在机器、硬件协议和真实验收未定义；本目录不宣称已接通实体双主臂。

## 关联规范

- [实体主臂与仿真从臂](../../10-frontend/03-simulation/03-leader-follower-panel.md)
- [控制权与受控人工接管](../../30-contracts/06-control-authority.md)
- [机器人能力与适配边界](../../00-overview/06-robot-capabilities.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)

## 验收入口

- [TEST-LEADER-002](../../40-verification/02-workspace-runtime-acceptance.md#test-leader-002)（现有草案，未执行；依赖的未决规则须先收敛）。
