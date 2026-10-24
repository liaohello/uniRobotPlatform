# 2D 地图与 Waypoint 路线编辑

规范 ID：`FE-SCENE-WAYPOINTS` · 责任层：前端 · 版本：V0.4（2026-10-24）

状态：设计草案；S08/S09 是用户提供的分析文本，不自动视为所有细节已确认。Waypoint 范围以 S10 的用户明确选择为准，M1.3 必填 yaw 以 S18 补充。后端 Route Draft/Version 资源候选已可接线；前端页面实现及端到端验收未执行。

来源：[S09](../../90-governance/sources/S09-unified-development-reuse-analysis.md)、[S10](../../90-governance/sources/S10-waypoint-scope-confirmation.md)、[S18](../../90-governance/sources/S18-navigation-map-route-slice.md)。

[上级目录](README.md) · [总索引](../../README.md)

关联需求：[REQ-NAV-003](../../indexes/05-requirements.md#req-nav-003)、[REQ-NAV-004](../../indexes/05-requirements.md#req-nav-004)

## 已确认范围与细化建议

S10 已确认 V1 在 Scene Setup 创建、编辑、保存 Waypoint；Simulation 展示执行进度。旧“不做导航设点”边界已被取代。下面的操作形式和字段是细化草案，不代表已经实现。

| 节点 | 行为草案 | 关键反馈 |
|---|---|---|
| 地图加载 | 显示当前 map 身份、分辨率、原点/旋转及有效区域 | 未加载或参考系不明时不提交路线 |
| 创建/选择 | 点击生成路线草案点；与地图平移工具互斥 | 当前点、编号、map 坐标明确 |
| 编辑 | 拖动/数值修改 XY；朝向用独立箭头或字段 | **本切片每个 waypoint 必须显式 yaw**；缺省/null 报错，显式 0 合法，不把缺省值伪装成用户目标 |
| 序列 | 删除、调整顺序、重编号作为建议交互 | 点稳定 ID 与显示序号分开 |
| 校验 | 显示地图外、未知/障碍区域、配置不匹配 | 格子有效不等于完整路径可达 |
| 保存/加载 | 保存路线修订、map/Frame 绑定，再加载核对 | CSV/YAML 只是候选交换格式，精确 schema 待核对 |
| 启动 | 本切片不提供路线采用/导航执行；版本只供显示和后续显式采用 | 编辑器不直接发布速度、目标或把点击变成在线控制 |

## 草案与活动路线

编辑路线只改变 Draft。正在执行的 Route Snapshot 保持不可变；新保存修订不热更新活动目标。V1 Simulation 显示已执行路径、当前点、进度与失败反馈，现有取消/接管仍走统一控制权流程。运行中编辑/重规划属于后续扩展，需要取消旧目标、版本校验和重新授权，不由本范围自动开放。

## 坐标与失败

像素/地图转换必须包含缩放、平移、图像轴方向、分辨率和地图原点姿态；map +X 随图像列增大，图像行向下对应 map -Y，origin 为图像左下角；见 [导航路线契约](../../30-contracts/08-navigation-map-route.md)。后端地图版本失配、不可通行、定位未就绪或授权失败均应保留具体原因，不能只弹“导航失败”。

后端职责：[地图与路线执行](../../20-backend/03-observation-algorithms/03-map-waypoint-execution.md)。验收：[TEST-NAV-003](../../40-verification/04-task-config-workflow-acceptance.md#test-nav-003)、[TEST-NAV-004](../../40-verification/04-task-config-workflow-acceptance.md#test-nav-004)、[TEST-NAV-006](../../40-verification/04-task-config-workflow-acceptance.md#test-nav-006)。

## 页面图与设计归属（V0.3）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E5%9C%BA%E6%99%AF%E9%85%8D%E7%BD%AE%E7%95%8C%E9%9D%A2.png)

[PAGE-02 页面设计与修正](../page-designs/02-scene-setup.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
