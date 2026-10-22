# 地图、Waypoint 路线与执行反馈契约

规范 ID：`CT-NAVIGATION-ROUTE` · 责任层：共享契约 · 版本：V0.5（2026-10-22）

状态：详细设计基线建议；Waypoint 范围以 S10 的用户明确选择为准，字段名不是现存 API。产品实现及验收均未执行。

来源：[S15](../90-governance/sources/S15-scene-setup-first-loop.md)、[S09](../90-governance/sources/S09-unified-development-reuse-analysis.md)、[S10](../90-governance/sources/S10-waypoint-scope-confirmation.md)。

[上级目录](README.md) · [总索引](../README.md)

关联需求：[REQ-NAV-003](../indexes/05-requirements.md#req-nav-003)、[REQ-NAV-004](../indexes/05-requirements.md#req-nav-004)

## 地图与路线身份

| 对象 | 需要表达的语义，不冻结字段拼写 |
|---|---|
| Map Reference | map 身份/版本、Frame、分辨率、原点位姿、栅格尺寸、数据有效性与场景兼容信息 |
| Route Draft | 草案 ID/修订、地图绑定、有序点集合、编辑来源 |
| Waypoint | 稳定 ID、显示顺序、地图系 XY、可选朝向和任务参数 |
| Route Snapshot | 被本次运行采用的不可变保存版本、配置/模型/导航来源与运行身份 |
| Execution Feedback | 路线与目标代数、当前点、已完成/失败点、状态、原因、时间和回执引用 |

## 资源保存、采用与运行引用

Route 是独立资源。`routeId` 标识同一条逻辑路线，`routeVersion` 标识不可变内容；Route Draft 的 `draftRevision` 用于并发编辑。Waypoint ID 不由数组下标或名称派生，重排不换 ID，删除后新增使用新 ID；顺序唯一且连续。点位、朝向、顺序、地图或任务参数变化必须生成新 Route Version。

保存新版本不覆盖旧版本，不破坏历史引用；配置只有显式“采用此版本”后才改绑。已验证配置、Session、Episode 固定 `routeRef(id,version)` 与 `mapRef(id,version,frame)`，禁止 `latest` 或未保存 DraftRef。后台 v2 发布不使仍引用 v1 的配置自动变化或失效；当前配置采用 v2 时立即 stale。

内联“编辑本路线”建立 draft-only `pendingRouteDraftRef + revision/contentDigest`，从这一编辑意图起增加工作配置 executionRevision、标记 stale；它没有修改已保存配置的 v1 引用。资源库中的独立路线编辑只改变那份 Route Draft，不使无关配置失效。pending 时禁止验证通过；保存路线并显式采用后换为固定 RouteRef、清除 pending，再验证。具体修订规则由 [配置契约](07-task-scene-experiment-config.md) 定义。

Route Version 保存完整点序与地图绑定、内容摘要、作者和时间；旧版本可读取。保存依赖 baseRevision；并发冲突明确拒绝，不静默合并位姿。删除被引用资源采用归档等保留历史可解析性的机制。

最小示意形状（设计提议）：

```json
{
  "routeVersion": {
    "id": "office-loop", "version": "v2", "contentDigest": "sha256:...",
    "mapRef": {"id": "lab-map", "version": "v3", "frame": "map"},
    "waypoints": [
      {"id": "wp-a", "order": 1, "xM": 1.2, "yM": 0.8, "yawRad": null},
      {"id": "wp-b", "order": 2, "xM": 2.0, "yM": 1.4, "yawRad": 1.57}
    ]
  },
  "routeRef": {"id": "office-loop", "version": "v2"}
}
```

`yawRad=null` 表示不约束最终朝向，不能暗补为 0；界面可显示度，权威值使用 rad。独立 Goal Marker 若出现，应标明为“最后一个 waypoint 的目标角色”并引用其 ID；单独修改 Goal 必须更新该点或显式插入终点，不能另维护与路线脱节的终点。机器人初态不属于路线点序。

验证兼容性至少包括 Route/Map 固定版本、Scene 与地图关联、Robot footprint/导航能力与标定、参考系变换可解析和单位/原点。不得按同名地图或最新版本自动修复引用。资源不兼容为 failed；未提供转换/检查能力为 unsupported，给出原因和对象定位。

## 坐标转换

以米制地图局部二维坐标为例：世界点由地图原点旋转/平移映射；显示再经过像素尺度、Y 轴方向、视口平移/缩放。图像原点和格子中心/边界约定需要明确，不能直接把屏幕像素当 map 坐标；旋转地图与缩放后应能双向核对。共用 [时间/参考系](04-time-frames-units.md)。

## 检查与命令边界

地图身份/Frame 缺失或不兼容、越界、未知/障碍格、序列无效应给出明确结果；通过点位预检不等于路线无碰或动态可执行。导航健康、控制源、录制门、旧目标清理与授权继续走已有后端。

编辑、保存与提交执行是三种操作；保存不发速度/目标命令。活动路线不因 Draft 修订自动改变。CSV/Nav2 YAML 为候选适配格式，导入必须声明单位、朝向、Frame/地图绑定和缺省规则，不以文件扩展名推断兼容。

V1 已确认编辑位于 Scene Setup，Simulation 展示当前路线和执行结果。活动路线在线修改/热重规划尚不在此开放。

## 四种操作与反馈隔离

| 操作 | 配置/验证影响 | 运行影响 |
|---|---|---|
| 选点、视口缩放、显示隐藏 | 不改内容，不 stale | 无命令 |
| 内联编辑本路线 / 独立编辑资源 | 前者建立 pending、使工作配置 stale；后者仅资源 dirty | 无命令，已保存配置/Session 不变 |
| Save Route Version | 新建独立不可变资源；不自动采用 | 无命令 |
| Adopt Route Version | 修改 Experiment 执行修订并 stale | 不修改已有 Session |
| Run 已验证路线 | 由活动 Session 的快照、控制权与就绪状态决定 | 后端显式执行，显示真实回执 |

执行反馈携带 `sessionId + routeRef + goalGeneration`、当前/完成/失败 waypoint ID、状态/原因和时间。重置、取消、切换目标代数或接管后，旧回执不得推进新路线 UI。点预检通过与整条规划、动态避障、终止结果分别显示，未执行检查不得画绿色通过。

[实验配置与 Stale/快照](07-task-scene-experiment-config.md) 是验证身份、指纹和原子创建 Session 的唯一主责；[命令](02-control-intervention-commands.md) 与 [控制权](06-control-authority.md) 负责执行授权。验收沿用 [TEST-NAV-003～006](../40-verification/04-task-config-workflow-acceptance.md)，新增 [TEST-CONFIG-006](../40-verification/06-scene-setup-first-loop.md#test-config-006)。
