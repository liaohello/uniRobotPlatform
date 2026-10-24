# M1.3｜版本化地图读取与带朝向 Route Draft/Version

日期：2026-10-24。本轮交付统一工作台可接线的真实历史地图读取、必填朝向 Waypoint、Route Draft/不可变 Version 保存链路，并整理真实 M1 的剩余部署决策。**候选完成；8792 未部署、未重启，未启动 SLAM/ROS 导航，未推进新物理实例，未执行运动、RESET、线上录制、真实 prepared/Start 或 M1 闭环验收。** 证据索引：[evidence/m1.3](evidence/m1.3/m1g-20261024T113913Z-platform/README.md)。

## 一、先交付的前端契约

来源 [S18](specs/90-governance/sources/S18-navigation-map-route-slice.md) 补充本次要求；历史 [S10](specs/90-governance/sources/S10-waypoint-scope-confirmation.md) 原文未改写。决定见 DEC-055，主责契约为 [地图、Waypoint 路线与执行反馈契约](specs/30-contracts/08-navigation-map-route.md)。

- `navigation.point_goal` 与每个 Waypoint 均必须携带 `x_m/y_m/yaw_rad`。OpenAPI 的 `WaypointInput.required` 已包含 `yaw_rad`，类型为 number；缺字段或显式 `null` 返回 HTTP 422，不暗补 `0.0`。显式 `0.0` 合法。
- `x/y` 单位 m，位于 map frame；`yaw` 单位 rad。map 为右手二维系，+X 为 0，向 +Y 为正（逆时针），服务输入归一化到 `[-π, π)`。
- 地图 `origin=[x_m,y_m,yaw_rad]` 表示图像**左下角**在 map frame 的位姿。图像列随 +X 增大，图像行向下随 map +Y 减小；格中心使用 `(col+0.5,row+0.5)`。`maps.py` 的 `world_to_pixel/pixel_to_world/world_to_cell/cell_center_to_world` 与 G3B/native 的底部原点、顶部第 0 行规则一致，测试覆盖旋转原点双向转换。
- 位置容差来自 Task Template `goal.position_tolerance`；朝向容差来自 `goal.yaw_tolerance_rad`。Route 保存只返回 `arrival_acceptance="not_checked"`，不声称到点或朝向验收。

真实 OpenAPI：[openapi.json](evidence/m1.3/m1g-20261024T113913Z-platform/platform/openapi.json)。前端只需以该文件和主责 Spec 为 schema 来源，不再自行维护另一套 Route/Map 定义。

## 二、真实 G3B 历史地图

候选读取服务器既有包，不把合成测试包伪装成环境数据：

| map_id / version / frame | 来源 | 栅格 | origin (m,rad) | resolution | image SHA-256 | manifest SHA-256 |
|---|---|---:|---|---:|---|---|
| `map_room_a_g3b_release_v1` / `v1` / `map` | `g3b_historical_offline` | 59×47 | `-1.2,-1.15,0` | 0.05 | `01dcdb387aed81b521cba6d31bb5d403d9db1de84b35546c4e34988191069d71` | `aaee75864a1a1edc7bdf73734640078640b0b40b69020574e80eef81c1b6fd34` |
| `map_room_b_g3b_release_v1` / `v1` / `map` | `g3b_historical_offline` | 74×57 | `-1.5,-1.45,0` | 0.05 | `f3242226c9d6492a24d5f63f25d191a3c8daff7be9a6639cc5f03cb8361cdd5a` | `a6e641a570c85e21523863f75e1346469c668993c1af0d75fe92ff4d1ea0382c` |

两者均为 trinary PGM，`occupied_thresh=0.65/free_thresh=0.196/negate=false`；`live=false`，当前接口没有 live SLAM 地图。Room A/B 的实际 `manifest.json`、YAML、PGM 和包内 `manifest.sha256` 已复制到 [maps/room_a](evidence/m1.3/m1g-20261024T113913Z-platform/maps/room_a/manifest.json)、[maps/room_b](evidence/m1.3/m1g-20261024T113913Z-platform/maps/room_b/manifest.json)。

`MapStore` 固定并核验 `manifest.json`，再逐字节核验 YAML、PGM 和 posegraph 资产的声明摘要；只解析 YAML/PGM，不导入 native Runtime 或 ROS，也不解析 posegraph。两个包的 `manifest.sha256` 文件内容记录的 manifest 摘要与当前 `manifest.json` 实际 SHA-256 不一致，这是历史包自身遗留的 stale self-check；本轮以 catalog 固定的**实际 manifest.json**摘要为准，不把该文件的内部值冒充已通过。该缺口不改变地图资源/显示用途，但说明历史 reader/包完整性后续需单独修复。

响应显式给出 Scene/Robot 兼容状态：Room A/B 与当前 G1 recipe 的 `scene_id`、`model_sha256` 均不匹配，`g1_recipe_status=failed`、`current_runtime_status=not_checked`、`navigation_eligible=false`。历史地图可编辑和显示，不因此获得导航资格；接口不按名称或 `latest` 自动匹配，缺失 catalog/包/version/frame 分别返回明确原因。

## 三、最小 API

| 路由 | 用途 |
|---|---|
| `GET /api/v1/maps` | 固定 ID/version/frame、来源、栅格、origin、阈值、资产摘要、兼容与未核验信息 |
| `GET /api/v1/maps/{map_id}/versions/{version}?frame=map` | 读取固定版本；错误 version 404，错误 frame 409 |
| `GET /api/v1/maps/{map_id}/versions/{version}/image?sha256=...` | 读取与摘要匹配的 PGM；摘要不符 409 |
| `POST /api/v1/route-drafts` | 创建 Draft；每个 waypoint 必须显式 yaw |
| `GET /api/v1/route-drafts/{route_id}` | 读取 Draft |
| `PUT /api/v1/route-drafts/{route_id}` | 以 `base_revision` 保存；相同内容不增修订，冲突 409 |
| `POST /api/v1/route-drafts/{route_id}/publish` | 发布不可变 Version；同内容复用，新内容递增 vN |
| `GET /api/v1/routes/{route_id}/versions` | 按新到旧列出固定版本 |
| `GET /api/v1/routes/{route_id}/versions/{version}` | 按固定版本读取，无 `latest` |

Map/Route 响应统一 `Cache-Control: no-store`。错误信封使用 `{detail:{code,message,...}}`；JSON schema 字段缺失/类型错误仍由 FastAPI 返回 422 校验列表，消息明确含 `yaw_rad is required...`。没有增加通用资源管理框架或额外 Profile CRUD。

## 四、Route 身份、摘要与并发

`route_id` 稳定，`draft_revision` 仅用于编辑并发，`version` 是发布后的不可变内容标识。Waypoint 的 `id` 与 `order` 分开；重排保持原 ID，只改 order。内容摘要覆盖 schema、`map_ref(id,version,frame)` 和按 order 排列的 `id/order/x/y/yaw`；名称、草案修订和时间不进入摘要。

SQLite 使用同一 draft DB 中的 `route_drafts` 和 insert-only `route_versions`，保存/发布使用 `BEGIN IMMEDIATE` 并检查 baseRevision。旧版本不覆盖、不静默合并位姿；历史引用固定原 version。真实候选样本：

- route `route-9e55257fc5d24a03a54986d9fcaa8a80`；
- v1 digest `a9ee5895be83db986da5ea830fb12beff74f657feeba80d9e3ef5844dd484e62`；
- v2（仅重排 wp-a/wp-b 顺序，ID 不变）digest `370d246234a251d7adc8b8f1205c745a2ca37ebf4ea50b1d7f64f5aabaa7871c`；
- 以旧 revision 1 再次保存返回 `route_draft_revision_conflict`，`current_revision=2`；
- v1 重读仍保持原 digest/点序，证明 v2 没有修改 v1。完整请求与响应见 [route-evidence.json](evidence/m1.3/m1g-20261024T113913Z-platform/platform/route-evidence.json)。

## 五、校验分层和执行隔离

每个成功 Draft/Version 分开表达：

- `map_binding`、`map_frame`、`waypoint_sequence`、每个 `waypoint_pose:<id>`：真实地图 free cell 检查，已 passed；
- `footprint`、`path_reachability`、`dynamic_execution`、`g1_route_adoption`：本切片未实现，明确 unsupported；
- `arrival_acceptance`：not_checked。

RouteValidation 固定 `navigation_eligible=false`、`adoption_supported=false`、`execution_supported=false`、`display_supported=true`、`g1_navigation_supported=false`。真实失败样本返回 422/404/409 与定位：

- `waypoint_out_of_bounds`、`waypoint_occupied`、`waypoint_unknown`；
- `map_version_not_found`、`map_frame_mismatch`；
- 缺 yaw/null yaw → 422；错误 image digest → 409。

代码路径只读取文件和平台 SQLite；handler 不调用 `MobileCarIntegration`/native。测试用真实 `MobileCarIntegration` 包装 `FakeNative`，每个 map/route HTTP 场景后断言 `fake.calls == []`。真实 18953 route 操作期间，8792 的 run/generation/episode、owner、`recording=IDLE`、`safety_latched=true` 前后一致，证据见 [native-comparison.json](evidence/m1.3/m1g-20261024T113913Z-platform/platform/native-comparison.json)。这不等同于“没有真实 prepared/Start”，而是本轮没有新增任何真实机器人动作。

## 六、服务器验证

所有构建、测试和转换在服务器执行。

| 检查 | 结果 |
|---|---|
| M1.3 新 map/route 聚焦 | **10 passed**（`test_navigation_maps.py`） |
| M1 相关回归聚焦 | **104 passed**（api/drafts/prepare/navigation maps/mobilecar/read/geometry） |
| 平台全量 | **108 passed / 3 failed**（共 111） |
| 已知失败 | `catalog_loads_real_tasks`、`every_task_has_existing_evidence`、`manifest_sources_exist`；bimanual/mujoco_learning sibling 与 native release acceptance docs 布局缺失，未跳过或改绿 |
| 真实地图 | Room A/B 列表/固定版本/PGM 摘要读取通过；G1 不兼容、无导航资格如实显示 |
| 真实路线 | create → publish v1 → save revision2 → stale 409 → publish v2 → fixed reads 全通过 |
| 坐标 | yaw 必填/显式 0/2π 归一化；旋转 origin 的 world↔pixel 双向误差 < 1e-12；cell center 对齐 |
| native | 未启动 SLAM/ROS/planner，未创建物理实例；未发 Nav2 goal、cmd_vel、RESET、运动或录制命令 |

JUnit：[focused-m1g.junit.xml](evidence/m1.3/m1g-20261024T113913Z-platform/platform/focused-m1g.junit.xml)、[full-m1g.junit.xml](evidence/m1.3/m1g-20261024T113913Z-platform/platform/full-m1g.junit.xml)。

## 七、候选与端口

最终 release `m1g-20261024T113913Z-platform`，服务器 PID 497279，监听 **18953**。backend 非缓存文件 50 个；服务器与工作树 source listing SHA-256 均为 `353a03176994a05c0047913aca03454bdde38c53659a30d9b46802e2b00866bd`，见 [source-listing-m1g.txt](evidence/m1.3/m1g-20261024T113913Z-platform/platform/source-listing-m1g.txt)。

当前服务器端口经 `ss -ltnp` 核对：

| 端口 | 身份 | 本轮处理 |
|---|---|---|
| 8792 | native PID 941842，drvfix/G4A2 | 只读观察，未停止/重启/修改 |
| 18949 | M1.2d 生产 recipe 平台候选 | 保留，未重做 Session freshness |
| 18944 | M1.2c 平台候选 | 保留，前端当前 upstream |
| **18950 → 18944** | 前端最新预览（frontend 404c1fc） | 保留；这是当前前端端口，不能当测试空闲端口 |
| 18946 → 18943 | 前端预览 | 保留 |
| 18935/18933 → 18942 | 前端/几何预览 | 保留 |
| 18932/18931/18905 | 其他既有预览/服务 | 保留 |
| 18941/18942/18943 | 既有平台服务 | 保留 |
| 18953 | M1.3 最终平台候选 | 本轮发布；旧 18953 m1f 进程已停止并由最终源码替换 |

旧记录中的“18947/18948 → 18944”和“18950/18951 为 native mock/测试平台”已过时；本轮没有占用这些号段，也不把旧临时端口记录当当前空闲依据。

## 八、真实 M1 部署矩阵

M1.3 只增加资源读取/保存链路，不改变 M1.2d 的 native 补丁决策。候选补丁仍是 `native-m1e.patch`，基线 `a5cef52d932ba41424b4bcc134539914031fda39`；旧 source pin `a01098040d953608004a34b3c76519d7884eaa4b2c95e36822bd4e7d283b911c` 只覆盖 a5 base，不能复用于 patch 候选。

| 方案 | 运行时口径 | 身份影响 | 可观察效果 | 主要风险/维护 | 回滚判据 |
|---|---|---|---|---|---|
| G1 + `a5cef52+patch` | `configs/default.yaml --backend mujoco --require-recording` | patch aggregate `c325a2b38570db7616a20637afe8b0e26ec5ccb243e586772302c1adb4496efd`；必须重新签发 pin/config/scene/runtime | 可测 G1 prepare/readback/start/begin | a5 基线同时带入 G4A2 UI、驾驶安全、modelgen 与 assets 差异；需重新核验这些非本轮行为 | validation/prepared 链任一步失败，立即恢复 drvfix release + `g4a2_server.yaml` |
| G1 + `drvfix+patch` | G1 配置与 require-recording | drvfix patch aggregate `dd24d1c80d68afa2c80665eb197b9184a267086bf4d5db76c2103475c414f7da`；新 pin 必需 | 在已部署 drvfix 行为上增加生命周期/TTL修复 | 仍需切换 G1 profile，并签发 G1 recipe；interface/config 不匹配则继续拒绝 | 保持 18949/旧 release 可访问，只回 8792，不删数据 |
| **独立 G4A2 recipe + `a5cef52+patch`** | 保留当前 8792 profile，另签 G4A2 recipe/采集口径 | aggregate 同上；必须把 a5 基线差异纳入新 recipe 证明 | 平台可按实际 G4A2 capabilities 验证 | 把尚未复核的 a5 UI/modelgen/驾驶安全变化带入生产；证据范围更大 | 新 G4A2 attestation/readiness 任一失败则不切换 |
| **推荐：独立 G4A2 recipe + `drvfix+patch`** | 保留当前 G4A2 profile，另签独立 recipe；不伪装成 G1 | `dd24d1c80d68afa2c80665eb197b9184a267086bf4d5db76c2103475c414f7da` | 最大程度保留已部署行为，同时获得 M1.2d P1 修复 | 必须先定义 G4A2 配置/场景/package/runtime digest 和 Session 口径；仍不是导航能力 | 维护窗口失败即回 drvfix release；binding 内存态随重启消失，新 recording 独立目录，不迁移/删除旧数据 |

矩阵只是待用户决策，不授权本轮部署。若以后进入维护窗口，步骤固定为：

1. 冻结选择（G1 或独立 G4A2、a5+patch 或 drvfix+patch）并记录决策人/时间；为新 release 重签 source manifest/aggregate、patch hash、requirements lock、config/scene digest 和 recipe revision，禁止复用 `a010…911c` 旧 base pin。
2. 在隔离端口安装并运行聚焦测试，核对 health/capabilities/attestation、binding prepare/readback、Start、begin；失败不触碰 8792。
3. 启动前记录 8792 的 PID、release、profile、run/generation/episode、owner、safety latch、recording 状态和当前前端/平台端口；确认无活动控制/录制后才停止旧服务。
4. 用选定 release/profile替换，启动平台候选，验证对应 recipe validation 与 prepared → active → RECORDING；每步保存响应和文件哈希。
5. 任一步失败立即恢复原 drvfix release + `g4a2_server.yaml`。内存 binding 随重启消失，不伪造恢复；新 recording 使用独立目录，不迁移或删除历史数据。成功判据包括 current 有效、identity/config/binding 一致、durable RECORDING、回执/文件一致、无重复 RESET/start/begin，以及 lease/STOP 门控未放宽。

本轮未执行上述任何部署步骤。

## 九、真实闭环仍缺

1. **Owner/lease**：平台已有 current observation，但没有取得/续租/释放控制权端点和真实交接流程。
2. **机器人 STOP**：`POST /api/v1/runs/{run_id}/stop` 只终止网关持有的进程或在平台侧标记 stopped；当 adapter 没有持有进程时只记录“平台侧标记停止”。它不发送 native STOP、不停机器人、不等待停车反馈。
3. **录制 end/finalize**：平台只有 begin；没有 end、STOP/drain、finalize、失败尾标记诊断或可审计完整性判定。
4. **历史 reader**：平台可读取 Session/Draft/Map/Route 资源，但没有原生 episode/segment/events 的统一历史读取与回放契约实现。
5. **导航**：当前 G1 没有真实导航执行能力。Route 只可编辑/显示，不能据此采用为可执行路线；G3B 历史地图也不等于 live SLAM。
6. **M1 验收**：真实 G1/G4A2 prepared、运动、录制、停止、回放和 Scene Setup → Simulation → Recording → Replay 闭环仍待维护窗口和后续切片。

## 十、冻结状态与边界

- 平台改动：`maps.py`、`routes.py`、API/settings、map catalog、测试与上述文档/证据；本地提交，不推送。
- native：`mobileCar` 仓库和补丁未修改、未提交、未部署；8792/前端/其他服务不重启。
- 本 Goal 完成只代表“地图读取与 Route 草案/保存候选及交付记录完成”，不代表到点/朝向验收、导航、部署或 M1 闭环通过。
