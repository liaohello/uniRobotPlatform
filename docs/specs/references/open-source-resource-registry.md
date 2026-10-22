# 可复用资源登记表

规范 ID：`REF-RESOURCE-REGISTRY` · 责任层：参考 · 版本：V0.2（2026-10-21）

状态：设计草案；S08/S09 是用户提供的分析文本，不自动视为所有细节已确认。Waypoint 范围以 S10 的用户明确选择为准。实现及产品验收均未执行。

来源：[S08](../90-governance/sources/S08-frontend-ia-analysis.md)、[S09](../90-governance/sources/S09-unified-development-reuse-analysis.md)。

[上级目录](README.md) · [总索引](../README.md)

关联需求：[REQ-REUSE-001](../indexes/05-requirements.md#req-reuse-001)

## 复用清单

以下“能力”指拟研究的能力，不是对所有仓库的独立审计。只有标明官方资料核对的条目有本轮声明证据，所有运行验证均未执行。

| ID | 资源 | 任务/能力映射 | 复用层级 | 验证状态 | 当前决定 |
|---|---|---|---|---|---|
| LOC-01 | [mobileCar](C:/Users/Administrator/Desktop/embodied_intelligence_proj/mobileCar/README.md) | 小车状态、控制、录制、导航 | 封装适配 | 历史工程分析；本轮未复验 | 优先本地接入 |
| LOC-02 | [bimanual_proj](C:/Users/Administrator/Desktop/embodied_intelligence_proj/bimanual_proj/README.md) | 双臂专家、多相机、轨迹回放 | 封装适配 | 历史工程分析；本轮未复验 | 保留主要双臂基础 |
| LOC-03 | [mujoco_learning](C:/Users/Administrator/Desktop/embodied_intelligence_proj/mujoco_learning/README.md) | IK/视觉实验与交互参考 | 选择性适配 | 历史工程分析；本轮未复验 | 不搬入完整实验 UI |
| OSS-01 | [MuJoCo Scene Editor](https://github.com/markusgrotz/mujoco-scene-editor) | 对象摆放、Gizmo 与配置导出 | 交互复用/适配候选 | 官方 README/License 已核对；无运行验证 | 待 PoC；不覆盖源模型 |
| OSS-02 | [Drei](https://github.com/pmndrs/drei) | 相机、Transform/Pivot 控件 | 组件候选 | 官方 README/License 已核对；无运行验证 | 待 PoC；依赖 R3F 方案先评估 |
| OSS-03 | [Dockview](https://github.com/dockview/dockview) | 停靠、布局保存和恢复 | 组件候选 | 官方 README 已核对；无运行验证 | 待 PoC；基础包与 enterprise 分开 |
| OSS-04 | [ros2-web2d](https://github.com/Neoplanetz/ros2-web2d) | 地图、路径、位姿、雷达显示 | 封装适配候选 | 官方 README 已核对；无运行验证 | 评估 ROS2/rosbridge 或 feed 接口 |
| OSS-05 | [Waypoint Editor](https://github.com/kzm784/waypoint_editor) | 路线创建、顺序和文件交换 | 工作流/格式参考 | 官方 README 已核对；RViz2 工具 | 不直接当浏览器组件 |
| OSS-06 | [Nav2 Waypoint Follower](https://github.com/ros-navigation/navigation2/tree/humble/nav2_waypoint_follower) | 有序目标执行与当前/失败点反馈 | 后端接口参考 | Humble README 已核对；无集成验证 | 适配既有导航授权边界 |
| OSS-07 | [URDF Loaders](https://github.com/gkjohnson/urdf-loaders) | 模型层级、关节加载 | 加载/交互参考 | 材料提及；本轮未重新核对 | 待模型映射评估 |
| OSS-08 | [URDF Viewer](https://github.com/tony1213/urdf-viewer) | 选择与前端组织 | 参考实现 | 材料提及；本轮未重新核对 | 不推断已具备本平台 IK |
| OSS-09 | [mjswan](https://github.com/ttktjmt/mjswan) | 鼠标施力体验 | 交互参考 | 材料提及；本轮未重新核对 | 不迁移浏览器物理为权威源 |
| OSS-10 | [Rerun](https://github.com/rerun-io/rerun) | 同步回放、图层与布局 | 参考/分析出口候选 | 材料提及；本轮未重新核对 | 不替代控制层 |
| OSS-11 | [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie) | 机器人模型对照 | 资产参考候选 | 材料提及；本轮未核对具体 SO101 文件 | 不替换已校验模型 |
| OSS-12 | [robosuite](https://github.com/ARISE-Initiative/robosuite) | Arena/Objects/任务组合 | 后端建模参考 | 材料提及；本轮未重新核对 | 选择性研究 |
| OSS-13 | [RoboCasa](https://github.com/robocasa/robocasa) | 场景/物体资源与任务关系 | 资产/任务参考 | 材料提及；本轮未重新核对 | 不为简单桌面引入完整框架 |
| OSS-14 | [Habitat-Lab](https://github.com/facebookresearch/habitat-lab) | 导航任务和 Episode 定义 | 任务设计参考 | 材料提及；本轮未重新核对 | 不迁移仿真底座 |
| OSS-15 | [ManiSkill](https://github.com/mani-skill/ManiSkill) | 操作任务变体和评价 | 任务设计参考 | 材料提及；本轮未重新核对 | 不默认引入依赖 |
| OSS-16 | [MoveIt 2 Tutorials](https://github.com/moveit/moveit2_tutorials) | 规划/执行分离与轨迹显示 | 流程/算法参考 | 材料提及；本轮未重新核对 | 不是自动替换现有 IK |
| OSS-17 | [Open3D](https://github.com/isl-org/Open3D) | 点云与几何处理 | 后端算法候选 | 材料提及；本轮未重新核对 | 不在网页嵌入桌面 GUI |
| OSS-18 | [ViSP](https://github.com/lagadic/visp) | 视觉误差与闭环控制 | 后端算法参考 | 材料提及；本轮未重新核对 | 需适配和独立闭环验证 |
| OSS-19 | [Mink](https://github.com/kevinzakka/mink) | 微分 IK 与约束 | 算法候选 | 材料提及；本轮未重新核对 | 对照现有模型，不直接升级环境 |
| OSS-20 | [SimEngine](https://github.com/RajatDandekar/sim-engine) | 示教/训练/评估流程 | 代码对照 | 材料提及；本轮未核对骨架与已实现范围 | 不声称所有模型可训练 |
| OSS-21 | [SO101 MuJoCo LeRobot Adapter](https://github.com/SinfonIAUniandes/lerobot_robot_so101_mujoco) | 仿真机器人与数据接口 | 适配参考 | 材料提及；本轮未重新核对 | 不替换 bimanual 物理基线 |
| OSS-22 | [LeLab](https://github.com/huggingface/leLab) | 数据→训练→推理跳转 | 产品流程参考 | 材料提及；本轮未重新核对 | 仿真/双臂适配待验 |
| OSS-23 | [MimicGen](https://github.com/NVlabs/mimicgen) | 子任务分段、信号与数据生成 | 阶段设计参考 | 材料提及；本轮未重新核对 | 不把示例词表冻结 |
| OSS-24 | [CVAT](https://github.com/cvat-ai/cvat) | 图像/视频标注 | 后续工具候选 | 材料提及；本轮未重新核对 | 非首版完整标注平台 |
| OSS-25 | [FiftyOne](https://github.com/voxel51/fiftyone) | 数据筛选与失败案例 | 产品流程参考 | 材料提及；本轮未重新核对 | 待明确数据规模 |
| OSS-26 | [MLflow](https://github.com/mlflow/mlflow) | 作业/指标/Artifacts/模型关系 | 管理流程参考 | 材料提及；本轮未重新核对 | 不冻结后端选型 |
| OSS-27 | [Aim](https://github.com/aimhubio/aim) | 训练曲线与运行比较 | 管理流程参考 | 材料提及；本轮未重新核对 | 不与多套看板同时强绑 |
| OSS-28 | [LeRobot annotation pipeline](https://github.com/huggingface/lerobot) | 语言标注流程研究 | 后续调研 | 材料提及；本轮未核对锁定版本 | 不要求 ACT 具备所有语言标签 |
| OSS-29 | [RobolaWeb 社区介绍](https://github.com/google-deepmind/mujoco/discussions/2999) | 场景编辑与运行时同步 | 仅研究 | 材料提及；本轮未核对代码/授权 | 不当无条件可集成组件 |

## 每项资源的补充记录

采纳前记录固定版本/commit、兼容环境、代码许可证、资产许可证/来源、拟复用路径、引入依赖、限制、PoC 证据和最终决定。当前除官方核对页明确说明的代码授权外，其余均待核对；代码可用不代表所有第三方模型/纹理许可均一致。

统一决策状态为候选→待 PoC→通过有限验证/不通过→采纳或不采纳。官方文档阅读不升级成运行通过；PoC 通过也不代表机器人任务通过。

逐项字段另见 [机器可读资源记录](resource-registry.json)，包含来源、待固定版本、兼容性、代码/资产授权、风险、决定及验证状态。未知值明确保留待核对，不使用默认“兼容”或“可集成”。

新功能先登记本地实现，再评估外部资源，说明直接集成、封装适配、参考或自研理由。三个优先验证项见 [PoC 计划](02-reuse-poc-plan.md)，具体证据见 [官方核对记录](03-official-review-notes.md)。
