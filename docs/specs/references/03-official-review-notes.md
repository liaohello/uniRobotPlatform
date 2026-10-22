# 本轮官方资料核对与兼容边界

规范 ID：`REF-OFFICIAL-REVIEW` · 责任层：参考 · 版本：V0.2（2026-10-21）

状态：设计草案；S08/S09 是用户提供的分析文本，不自动视为所有细节已确认。Waypoint 范围以 S10 的用户明确选择为准。实现及产品验收均未执行。

来源：[S09](../90-governance/sources/S09-unified-development-reuse-analysis.md)。

[上级目录](README.md) · [总索引](../README.md)

## 核对方式

2026-10-21 只读官方仓库 README/License；未安装或运行，网页分支未固定 commit，不构成锁定版本的兼容证明。以下结论只对应所读声明。

| 资源 | 本轮核对结果 | 来源 |
|---|---|---|
| MuJoCo Scene Editor | 浏览器编辑、对象/Gizmo 与导出；Limitations 明示部分 XML 内容不保留 | [README](https://github.com/markusgrotz/mujoco-scene-editor#limitations) |
| Scene Editor 授权 | 所读代码 LICENSE.md 为 MIT；依赖/机器人资产仍单独核对 | [LICENSE](https://github.com/markusgrotz/mujoco-scene-editor/blob/main/LICENSE.md) |
| Drei | R3F 工具集合；通用变换控件不能替代机器人 IK/权限 | [README](https://github.com/pmndrs/drei)、[代码 License](https://github.com/pmndrs/drei/blob/master/LICENSE) |
| Dockview | 布局序列化、停靠/标签/浮动；基础包与 enterprise 授权分开 | [README](https://github.com/dockview/dockview#licence) |
| ros2-web2d | ROS2 地图/路径/位姿/扫描渲染；README 有 feed 模式与 React 示例 | [README](https://github.com/Neoplanetz/ros2-web2d) |
| Waypoint Editor | RViz2 上编辑、保存/加载 CSV 或 Nav2 YAML 的工具，适合交互/格式参考 | [README](https://github.com/kzm784/waypoint_editor) |
| Nav2 Waypoint Follower | Humble 文档描述有序点数组、当前索引及未完成点反馈 | [版本化 README](https://github.com/ros-navigation/navigation2/blob/humble/nav2_waypoint_follower/README.md) |

ros2-web2d 默认通信栈与本项目 API 不是同一个接口，需评估 feed/共享缓存适配；不因其示例提供设点就绕过后端授权。其 README 声明 BSD-3-Clause，实际选定包和资源仍需归档。其余登记项仅保留新材料的参考意图，未在本轮逐项核对。
