# Replay & Annotation｜同步回放与标注

规范 ID：`FE-REPLAY-PLAYBACK` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-017](../../../设计过程与Specification总册_20261021.md#doc-017) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.3｜更新日期：2026-10-21（America/Los_Angeles）；原始内容来源保留。

状态：回放需求已明确；高级交互与标签协议为草案

来源：S01、S02、S05（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：[REQ-REPLAY-001](../../indexes/05-requirements.md#req-replay-001), [REQ-REPLAY-002](../../indexes/05-requirements.md#req-replay-002), [REQ-ANN-001](../../indexes/05-requirements.md#req-ann-001)

## 用户需求与建议扩展

用户需要独立回放入口，选择已录制数据，同步查看任务传感器、本体与轨迹，支持播放、倍速。逐帧、区间循环、标注审核等来自后续助手方案。

## 核心对象与流程

选择 Episode → 检查可用流及版本 → 打开回放 → 同步 3D / 相机 / 曲线 → 定位问题区间 → 添加或修订标注 → 保存 Annotation Revision。

| 回放对象 | 建议显示 |
|---|---|
| 3D / Robot | 记录的历史姿态及 Frame |
| Camera | 对应源时间的图像与缺帧提示 |
| Joint Chart | Actual / Target；速度按记录能力显示 |
| Trajectory | 实际 TCP 与记录过的目标 / 候选轨迹 |
| Task Phase | 在线事件与离线标签分轨 |
| Control Source | Human / Expert / Policy、接管区间 |
| Events | 碰撞、抓取、失败、恢复、连接异常等已记录事件 |

## 回放与标注的写入边界

历史状态浏览默认只读，不驱动在线 MuJoCo；标注操作写入独立标签层，不能修改原始传感器和动作记录。回放时间轴与在线仿真时钟必须使用各自上下文。

阶段标签由用户明确要求继续讨论；不能把助手示例的“接近/闭合/抬升/传递”直接变成冻结字典。应支持未标注 / 不确定的表达方式，最终格式、区间开闭、是否允许重叠、多任务层级、审核机制待定。

## 分析示例

对于 ACT “初次抓起后才失败”，可关联抓取接触、抬升高度、夹爪目标/实际、控制源、chunk 切换事件；这些是诊断视图建议，并非要求当前已录制全部诊断量。

## 验收草案

播放、暂停、倍速、拖动定位可用；缺失数据明确显示；回放操作不提交在线命令；修改标签形成可追踪版本。同步误差阈值和性能指标仍待实测冻结。

## 关联文档

- [统一时间轴与事件轨](../08-observation-inspector/03-timeline-event-tracks.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)
- [Dataset Management｜数据管理](../05-datasets/01-browser-quality-export.md)
- [回放、标注与数据管理验收](../../40-verification/03-replay-data-acceptance.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## V0.2 单条轨迹审核闭环

从 Data 列表筛选→打开 Episode Detail→同步检查阶段/动作/观测→修订标签→分别查看完整性、任务结果和用途资格→保存审核修订→按选择加入集合。详情与列表共享上下文，后台 Session 与历史 Episode 保持隔离。

## V0.3 图片中的编辑入口

页面与图片见 [Episode Detail](../page-designs/05-episode-detail.md)。Split/Trim/Export Clip 默认设计为片段引用或派生导出，不裁原始轨迹。“Open in Simulation”应改为以历史配置创建新运行；恢复任意时刻完整物理状态的能力未确定，不承诺直接从历史帧续跑。

## 页面图与设计归属（V0.3）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E5%9B%9E%E6%94%BE%E4%B8%8E%E6%A0%87%E6%B3%A8%E7%95%8C%E9%9D%A2.png)

[PAGE-05 页面设计与修正](../page-designs/05-episode-detail.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
