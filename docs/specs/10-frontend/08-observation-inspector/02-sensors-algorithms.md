# 传感器与算法观测面板

规范 ID：`FE-PANEL-SENSORS` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-029](../../../设计过程与Specification总册_20261021.md#doc-029) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.4｜更新日期：2026-10-22（America/Los_Angeles）；原始内容来源保留。

状态：观测差异已确认；组件显示契约为草案

来源：S01、S02、S04、S05（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：见需求追踪矩阵中的引用与相关主责规范

## 职责

根据 UI Profile 显示 RGB、Depth、相机视角、地图、LiDAR、点云、本体曲线等可用数据。小车与双臂的必需观测不同；不能固定为一套相机九宫格。

每个面板建议显示源名称、Frame、源时间/仿真时间、连接与缺帧/过期状态。RGB、深度与 3D 点云的显示变换要与时刻匹配；未知流不得悄悄用旧画面冒充实时。

面板隐藏只影响呈现，不应隐式改变算法输入或记录 Profile。若要停止某个传感器源，应是独立配置操作，并体现对算法及记录的影响。

双臂中央/左腕/右腕视图属于任务相机；实体主臂无独立相机需求。Simulation 的地图显示与后端路线共存；Waypoint 编辑位于 Scene Setup，见 [地图编辑规范](../02-scene-setup/04-map-waypoint-editor.md)。不要把观测面板点击默认变成导航命令。

## 关联文档

- [任务、观测与数据配置](../../00-overview/03-task-and-observation-profiles.md)
- [时间、坐标系与命令生命周期](../../30-contracts/04-time-frames-units.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## 页面图与设计归属（当前参考 V0.4）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png)

[PAGE-03 页面设计与修正](../page-designs/03-simulation.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
