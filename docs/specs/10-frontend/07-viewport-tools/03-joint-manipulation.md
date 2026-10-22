# 关节操控与监控

规范 ID：`FE-3D-JOINT` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-022](../../../设计过程与Specification总册_20261021.md#doc-022) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.4｜更新日期：2026-10-22（America/Los_Angeles）

状态：滑条定位为用户明确修订；操控细节为草案

来源：S03、S04、S05（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：[REQ-JOINT-001](../../indexes/05-requirements.md#req-joint-001), [REQ-JOINT-002](../../indexes/05-requirements.md#req-joint-002)

## 用户修订

关节滑条主要用于监控数据；不能把普通 Inspector 上的滑条继续设计为默认控制入口。助手建议将默认关节数值/滑条设为只读，必要时另开显式 Joint Edit 或调试输入。

## 鼠标操控草案

选择 Joint → 显示轴 / Joint Ring → 在权限与模式允许时拖动 → 计算目标 → Live 或 Preview-Confirm 提交 → 显示后端反馈及 Actual / Target 差异。

明确选中 Joint 后，可支持拖动对应 Link 以修改该 Joint 目标。屏幕位移到关节角的映射尚未定义；不能对任意 Link 拖动就默认猜测要控制哪个关节。

## 语义

一次关节直接控制只修改所选关节目标；下游 Link 随运动学链变化，不代表修改了所有下游关节的目标。限位、关节类型、零位、单位由机器人适配描述，前端显示与后端检查均需一致。

Policy Active 下不隐式发送覆盖动作；先走受控接管。Force 工具的 Link 拖动不写 Joint Target。Scene Edit 的初态关节修改也与在线控制区分。

## 反馈与待验证

显示当前值、目标值、限位、控制源、受理/拒绝/执行状态。待验证 Joint Ring 的可拾取宽度、视角接近平行时的退化行为、拖动灵敏度、取消草案与停止运动语义。

沿用 TEST-JOINT-001；增加监控控件不发命令的验收。

## 关联文档

- [选择、相机与整臂框选](02-selection-camera.md)
- [控制权与受控人工接管](../../30-contracts/06-control-authority.md)
- [控制与干预命令契约草案](../../30-contracts/02-control-intervention-commands.md)
- [Inspector 与层级联动](../08-observation-inspector/01-hierarchy-inspector.md)
- [交互验收清单](../../40-verification/01-interaction-acceptance.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。

## V0.4 监控列与夹爪

Joint Monitor 的 actual/target/error 单位明确，误差的带符号或绝对值约定统一；若由 rad 转 ° 必须同时转换值。Gripper 按自身角度/宽度/归一化开度显示，不继承整表的角度单位。

新图移除了显式 Open/Close 按钮，但原夹爪控制需求仍保留。Coupled 的 Owner 不等于自动生成开闭命令；人工授权后应提供明确的开闭/开度工具。位置和姿态目标的残差与指令反馈另按 TCP/命令契约呈现。
