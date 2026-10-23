# 前后端共享契约

只负责跨边界共同理解的身份、数据、时间、命令与权限语义。通用部分仍为设计草案；[mobileCar read v1](01-robot-world-state.md#mobilecar-read-v1) 已落实场景/能力/实际状态/资产的HTTP读取子集，其他端点与频率不能据此视为已实现。前端负责呈现，后端负责权威执行。

V0.5 当前优先：[实验配置](07-task-scene-experiment-config.md) 的 Profile/权限/Stale/快照、[路线资源版本](08-navigation-map-route.md) 与 [数据到模型来源链](05-dataset-model-lineage.md)。示意字段用于实现对齐，现存后端任务目录结构不自动满足这些运行契约。

[总索引](../README.md) · [前后端功能映射](../indexes/06-feature-map.md)

## 规范节点

- [Robot / World State 契约草案](01-robot-world-state.md) — `CT-STATE`
- [控制与干预命令契约草案](02-control-intervention-commands.md) — `CT-COMMAND`
- [Episode、采集、事件与标注契约](03-episode-events-annotations.md) — `CT-EPISODE`
- [时间、坐标系与命令生命周期](04-time-frames-units.md) — `CT-TIME-FRAMES`
- [Dataset、Training、Checkpoint 与 Evaluation 关系](05-dataset-model-lineage.md) — `CT-LINEAGE`
- [控制权与受控人工接管](06-control-authority.md) — `CT-AUTHORITY`
- [Scene、Task Template 与 Experiment Configuration](07-task-scene-experiment-config.md) — `CT-EXPERIMENT-CONFIG`
- [地图、Waypoint 路线与执行反馈契约](08-navigation-map-route.md) — `CT-NAVIGATION-ROUTE`

- [评估报告与比较证据契约](09-evaluation-comparison.md) — `CT-EVAL-COMPARISON`
