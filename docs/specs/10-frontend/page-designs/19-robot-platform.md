# Robot Platform｜机器人能力资源

规范 ID：`PAGE-19` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

查看机器人模型、关节、传感器和控制适配能力，供场景与运行复用。

- 页面 ID：`PAGE-19`；导航归属：Resources / 辅助资源入口。
- 主要对象：Robot Configuration Revision、模型资产身份、Capability、设备映射。
- 增量路线：A/B 只读能力登记；D 主臂与双臂。这是设计顺序，不是排期或启动实施。

## 图片参考

![Robot Platform｜机器人能力资源 原始概念图](../../../foreendAssets/RoboLab%E5%8F%8C%E8%87%82%E6%9C%BA%E5%99%A8%E4%BA%BA%E5%B9%B3%E5%8F%B0%E6%8E%A7%E5%88%B6%E5%8F%B0.png)

主参考：`IMG-019`，PPT 第 19 页。覆盖程度：完整页面构图参考；硬件事实与外形须全部替换为工程来源。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 左侧 | 实际登记机器人配置列表。 |
| 中央 | 只读模型预览、关节树、传感器与模型文件引用。 |
| 右侧 | 能力与适配状态；配置编辑创建新修订。 |

## 关键操作与跳转

- 查看工程中的稳定 Joint/Link/TCP/Camera ID、单位、限位和控制方式。
- 选择机器人配置进入 P02；模型预览只供观察不执行运动。
- 主臂连接/标定/映射只在对应桥接能力接入后开放。

## 状态、失败与恢复

- 能力未知/未接入显示 Unknown，不显示假 Ready/Connected。
- 模型与后端资产版本不符时禁止当作可执行配置。

## 相对原图的取舍

- 图中制造商、12 DoF、负载、尺寸、频率及接口均未核实，不采纳为 SO101 规格。
- SO101 基线三路 RGB；Depth Optional 不自动启用，主臂没有独立摄像头。
- URDF/MJCF/SRDF 文件卡片不证明实际都存在，也不意味着自动完成格式转换。

关联冲突：[VIS-C05](../../90-governance/08-visual-design-conflicts.md#vis-c05)、[VIS-C08](../../90-governance/08-visual-design-conflicts.md#vis-c08)、[VIS-C17](../../90-governance/08-visual-design-conflicts.md#vis-c17)、[VIS-C18](../../90-governance/08-visual-design-conflicts.md#vis-c18)、[VIS-C19](../../90-governance/08-visual-design-conflicts.md#vis-c19)。

## 主责功能与后端支撑

- [机器人能力与适配边界](../../00-overview/06-robot-capabilities.md)
- [实体主臂与仿真从臂](../03-simulation/03-leader-follower-panel.md)

后端/契约：[01-robot-world-state](../../30-contracts/01-robot-world-state.md)、[01-integration-boundaries](../../20-backend/07-existing-project-adapters/01-integration-boundaries.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 用于实验 | [PAGE-02](02-scene-setup.md) | Robot Configuration Revision，创建/更新草案 |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
