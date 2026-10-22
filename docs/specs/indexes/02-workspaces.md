# 按工作区查找

V0.2 采用四导航组组织六个逻辑职责的设计草案：Prepare→场景布置，Run→仿真，Data→回放/标注与数据管理，Models & Experiments→训练和评估；不等于六个独立顶级页面。

| 工作区 | 前端入口 | 后端支撑 | 共享规则 |
|---|---|---|---|
| 场景布置 | [Scene Setup｜场景布置](../10-frontend/02-scene-setup/01-workflow-initial-state.md) | [能力域](../20-backend/01-session-scene/README.md) | [Robot / World State 契约草案](../30-contracts/01-robot-world-state.md) |
| 在线仿真 | [Simulation｜在线仿真工作台](../10-frontend/03-simulation/01-workflow-task-panels.md) | [能力域](../20-backend/02-robot-control/README.md) | [控制权与受控人工接管](../30-contracts/06-control-authority.md) |
| 回放与标注 | [Replay & Annotation｜同步回放与标注](../10-frontend/04-replay-annotation/01-synchronized-playback.md) | [能力域](../20-backend/04-recording-replay/README.md) | [Episode、采集、事件与标注契约](../30-contracts/03-episode-events-annotations.md) |
| 数据管理 | [Dataset Management｜数据管理](../10-frontend/05-datasets/01-browser-quality-export.md) | [能力域](../20-backend/05-dataset-export/README.md) | [Dataset、Training、Checkpoint 与 Evaluation 关系](../30-contracts/05-dataset-model-lineage.md) |
| 模型训练 | [Model Training｜训练管理概念](../10-frontend/06-training-evaluation/01-training-workspace.md) | [能力域](../20-backend/06-training-evaluation/README.md) | [Dataset、Training、Checkpoint 与 Evaluation 关系](../30-contracts/05-dataset-model-lineage.md) |
| 评估 | [Evaluation｜评估概念](../10-frontend/06-training-evaluation/02-evaluation-workspace.md) | [能力域](../20-backend/06-training-evaluation/README.md) | [Dataset、Training、Checkpoint 与 Evaluation 关系](../30-contracts/05-dataset-model-lineage.md) |

[返回总索引](../README.md)

## 页面与视图分工

[完整页面图](../10-frontend/page-designs/README.md) 按四业务组、Home 和辅助资源呈现。Training Setup/Runs、Models 三标签、Evaluation 四视图是同一能力的页面状态；Offline Inference 与 Real Robot 仅是后续候选。逻辑视图不等于冻结路由或全部 V1 开发清单。
