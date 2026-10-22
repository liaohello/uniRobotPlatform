# Real Robot Deployment｜真机部署后续参考

规范 ID：`PAGE-21` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

保留真机部署的设计意图，等待硬件协议与验证后再制定可执行规格。

- 页面 ID：`PAGE-21`；导航归属：后续环境能力；不加入当前活动 V1 导航。
- 主要对象：未来 Hardware Session、设备能力/映射、Calibration Revision。
- 增量路线：后续，不因存在图片纳入当前 V1。这是设计顺序，不是排期或启动实施。

## 图片参考

![Real Robot Deployment｜真机部署后续参考 原始概念图](../../../foreendAssets/%E6%9C%BA%E5%99%A8%E4%BA%BA%E6%8E%A8%E7%90%86%E4%B8%8E%E7%9C%9F%E5%AE%9E%E9%83%A8%E7%BD%B2%E6%8E%A7%E5%88%B6%E5%8F%B0.png)

主参考：`IMG-010`，PPT 第 10 页。覆盖程度：完整候选构图参考；执行与安全语义尚未定义。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 配置 | 实际硬件/模型与标定/兼容信息。 |
| 观察 | 真实相机、本体与来源明确的状态重建。 |
| 执行 | 未来明确授权的设备指令与实际反馈。 |

## 关键操作与跳转

- 当前只归档页面设计与缺口，不提供可执行真机入口。
- 未来接入复用 Session/Ownership/Recording 概念，设备停止、断连和复位语义单独定义。

## 状态、失败与恢复

- 仿真与真机身份持续区分，进入页面不连接或启动设备。
- 真实设备状态来自桥接服务；浏览器按钮不能证明硬件已停。

## 相对原图的取舍

- 不把 Reset Robot 等同于 MuJoCo Reset；不照搬速度倍率/逐帧播放去控制真实设备。
- 图片 Safety Monitor 可关闭、力限位等控件缺少设备依据，不能直接实现。
- 深度/外部相机、USB/CAN、力反馈和频率均待核对，中央与腕部相机也须实际登记。

关联冲突：[VIS-C06](../../90-governance/08-visual-design-conflicts.md#vis-c06)、[VIS-C08](../../90-governance/08-visual-design-conflicts.md#vis-c08)、[VIS-C17](../../90-governance/08-visual-design-conflicts.md#vis-c17)、[VIS-C18](../../90-governance/08-visual-design-conflicts.md#vis-c18)。

## 主责功能与后端支撑

- [范围与建议分期](../../00-overview/02-scope-and-staging.md)
- [机器人能力与适配边界](../../00-overview/06-robot-capabilities.md)

后端/契约：[01-integration-boundaries](../../20-backend/07-existing-project-adapters/01-integration-boundaries.md)。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
