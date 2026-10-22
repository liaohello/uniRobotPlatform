# 机器人能力与适配边界

规范 ID：`SYS-CAPABILITIES` · 责任层：系统 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-012](../../设计过程与Specification总册_20261021.md#doc-012) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.3｜整理日期：2026-10-21（America/Los_Angeles）

状态：能力适配为草案；机器人任务差异已有来源

来源：S01、S02、S05（详见[来源档案](../90-governance/06-sources.md)）

关联需求：见需求追踪矩阵中的引用与相关主责规范

## 能力驱动的共用工作台

Robot Capability 描述机器人有哪些 Arm、Joint、Link、TCP、Gripper、Base、Sensor，以及支持哪些命令。前端据此显示工具，避免把 SO101 面板强行用于 LanderPi。

| 能力 | LanderPi | SO101 双臂 |
|---|---|---|
| 底盘 | 键盘控制需求 | 无导航底盘需求 |
| Arm | 单臂近场操作 | 左右独立 Arm |
| TCP 控制 | 根据实际自由度支持可达位置 / 姿态 | 根据实际模型与控制器适配 |
| 相机 | RGB-D 为当前需求 | 三路 RGB 视图 |
| Leader | 当前首要键盘与鼠标；不自动引入实体主臂要求 | 双实体主臂映射从臂 |
| 专家 | SLAM / 导航、视觉伺服 | IK / 动作规划 |

能力字段建议包含稳定 ID、关节类型/限位/单位、运动学链、参考坐标系、可编辑对象、可施力 Body、控制源及可用控制模式。精确字段属于接口草案。

不得用“TCP 6D 目标”推断实际机械臂可任意实现六维位姿。未满足自由度或约束时，应说明不可达维度；不能把后端无法实现的姿态显示为已执行成功。

URDF / MJCF 的分工、前后端模型一致性及 Frame / Link / Body ID 映射需要单独核对；参考项目里出现 URDF 不等于已决定从 MuJoCo 改用另一套仿真。

## 关联文档

- [任务、观测与数据配置](03-task-and-observation-profiles.md)
- [Robot / World State 契约草案](../30-contracts/01-robot-world-state.md)
- [关节操控与监控](../10-frontend/07-viewport-tools/03-joint-manipulation.md)
- [TCP 操控与虚线运动轨迹](../10-frontend/07-viewport-tools/04-tcp-trajectories.md)
- [实体主臂与仿真从臂](../10-frontend/03-simulation/03-leader-follower-panel.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)

## V0.3 概念图与模型事实

[Robot Platform 页面](../10-frontend/page-designs/19-robot-platform.md) 中机器人外形、厂商、DoF、负载、尺寸、频率、模型文件和通信接口都是未核实占位。能力值以现有工程资产/适配器声明为准，缺失保留未知。SO101 当前三路 RGB，额外深度/点云或主臂相机不由概念图自动加入。
