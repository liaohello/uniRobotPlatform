# 三个既有项目的适配边界

规范 ID：`BE-ADAPTERS-LEGACY` · 责任层：后端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-009](../../../设计过程与Specification总册_20261021.md#doc-009)、[doc-012](../../../设计过程与Specification总册_20261021.md#doc-012)、[doc-031](../../../设计过程与Specification总册_20261021.md#doc-031)、[doc-032](../../../设计过程与Specification总册_20261021.md#doc-032)

[上级功能包](README.md) · [总索引](../../README.md)

## 目标与责任边界

复用已有工程的执行能力，通过薄适配层对接统一工作台。此节点引用上一轮静态调查，不在本轮复验部署、训练或物理成绩；更晚需求覆盖旧分析中的 UI 建议。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| mobileCar | 作为小车命令、状态、录制与导航接入参考；保持已有权限和数据协议。 |
| bimanual_proj | 复用双臂专家、仿真、事件和回放；在线控制网关与实体主臂能力需分别核对。 |
| mujoco_learning | 按具体 Vision Bench / IK Lab 入口选择性接入，不整体导入实验 UI 的执行逻辑。 |
| 一致性 | 核对模型/标定、相机安装、动作单位、左右顺序、采样频率；每个在线实例只有一个物理推进者。 |

## 未决与依赖

具体运行版本、部署入口和既有 API 均待接入时逐项核对。滑条默认控制建议已被监控定位覆盖；Waypoint 又经 S10 扩展纳入 Scene Setup，接入时核对现有导航边界，不能从旧排除或旧设点实现推断新接口已经完成。

## 关联规范

- [机器人能力与适配边界](../../00-overview/06-robot-capabilities.md)
- [Robot / World State 契约草案](../../30-contracts/01-robot-world-state.md)
- [控制与干预命令契约草案](../../30-contracts/02-control-intervention-commands.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)

## 验收入口

暂无独立冻结 TEST；沿用关联规范中的待执行验收。实现前将本节点行为拆成可验证条件，不以本文存在作为验收通过。

上一轮工程调查：[前端需求分析 V0.2（历史）](../../../frontend_analysis_v0.2.md)。
