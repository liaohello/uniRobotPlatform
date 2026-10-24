# M1.3 真实地图与带朝向 Route Draft/Version 端到端接线（2026-10-24）

本轮把 Scene Setup 从“会话内本地存储”接到后端候选 18953（`m1g-20261024T113913Z-platform`）真实交付的 Map/Route 资源：地图目录、固定版本、按摘要读取的 PGM 栅格，以及 Route Draft 创建/读取/条件保存/发布与不可变版本读取。DTO 全部按 18953 实际 OpenAPI 与 `CT-NAVIGATION-ROUTE` V0.6 映射，未自造 wire；导航采用与执行仍按后端 `navigation_eligible/adoption_supported/execution_supported=false` 禁用。只修改 `frontend/`，未推送。

## 冻结版本与入口

| 项 | 值 |
|---|---|
| 前端 release | `m1-front-geometry-20261024T160252Z-298deb4a4650` |
| 输入 / 聚合 SHA-256 | 86 个输入；`298deb4a4650322f097d66bcb1232815744f1b5c903cbfeac3b8bc1d08d655ab` |
| 地图/路线上游 | 18953 = `m1g-20261024T113913Z-platform`（真实 map/route，`read_contract_compatible=false`） |
| 3D/Session 上游 | 18949 = `m1e-20261024T090448Z-platform`（geometry-2 只读 envelope） |
| 本轮预览 | 18958 → 18953（PID 3122409，地图/路线实况）与 18957 → 18949（PID 2812567，3D/Session 回归），同一冻结 dist |
| 保留服务 | 18951 → 18949、18950 → 18944、18946 → 18943 与 18943/18944/18949/18953 后端全部未停止、未重启；端口按 `ss -ltnp` 实测选取，18954 是 mobileCar native 实例、18956 是 gateway uvicorn 夹具，均未触碰；上一轮中断候选的 18955 预览（本会话启动）已按 PID 身份核对后停止 |
| 真实 native | 8792 仍 `drvfix`/G4A2/PID 941842；两轮 pass 前后 `run_9c88e3e…` / generation 1 / `episode_43c22f…` / recording=IDLE 一致，`native_mutations_sent=false` |
| 环境 | cec-sim，Node 20.20.2 / npm 10.8.2，锁摘要 `1bb055b6e003c960…`，Chromium ANGLE SwiftShader |
| 证据 | `reports/m1-front-geometry-20261024T160252Z-298deb4a4650/`（18949 回归）与 `…-298deb4a4650-18953/`（真实地图/路线），含 build/unit/environment/preview/native-read-only/listeners 与各套件目录、截图 |

## 实现一：真实 wire 与 DTO 映射

- 新增 `src/adapters/platform-navigation.ts`：`MapListDto`、`MapVersionDto`、`MapAssetRefDto`、`RouteDraftDto`、`RouteVersionDto`、`RouteVersionSummaryDto`、`RouteVersionListDto`、`PublishResultDto` 与 `PlatformNavigationApi`（`listMaps`、`getMapVersion`、`mapImage`、`createDraft`、`getDraft`、`saveDraft`、`publishDraft`、`listVersions`、`getVersion`），路径、查询参数与请求体逐一对应 18953 OpenAPI。
- snake_case DTO 与 camelCase ViewModel 的转换集中在此：`map_ref.map_id/version/frame → mapRef`、`x_m/y_m/yaw_rad → xM/yM/yawRad`（`[-π, π)` 归一化）、`resolution_m/width_px/height_px/origin{x_m,y_m,yaw_rad}`、`coordinate_convention`、`compatibility`。`frame!=map` 或 `image_row!='-Y'` 直接抛 `MapContractError`，不猜坐标系。
- 版本标识与摘要以后端为权威：界面显示 `v1/v2` 字符串与后端 `content_digest`；本地 `route-store`（`local_session_only`、数字版本、`local-` 前缀摘要）整体删除，不再有任何本地摘要冒充服务端确认。
- 实测 wire 细节：`GET /routes/{id}/versions` 返回 `{route_id, versions[]}` 信封；无已发布版本时返回 404 `route_version_not_found`，前端按“空列表”处理而不是错误；`POST .../publish` 返回 `{route_version, reused}`，`reused=true` 明确显示为“内容与已发布版本相同，未新建版本”。

## 实现二：真实 PGM 与坐标约定

- `src/map/pgm.ts` 只接受 P2/P5；解析头、注释与像素后校验：声明摘要与实际字节 SHA-256 必须一致（`digest_mismatch`）、解码尺寸与声明 `width_px/height_px` 必须一致（`dims_mismatch`）、其它 magic/位深/截断/越界值显式失败。浏览器端把校验后的栅格画进 canvas 再作为 PNG 图层，CSS 使用 `image-rendering:pixelated`。
- 任何校验失败都保留该地图为“不可用”并禁用写入，不静默回退离线测试地图；离线 `offline-test-map` 仍在，但标记为 `offline_test_fixture` 且禁止创建后端路线。
- 保留既有几何：origin 为图像左下角在 map frame 的位姿、列随 +X、行随 −Y、格中心 `col+0.5,row+0.5`、yaw 逆时针从 +X 起；视图旋转/缩放/平移仍经 `getScreenCTM()` 逆变换，map 坐标不变。标记几何改为按栅格尺寸比例缩放，59×47 的真实栅格与 800×600 的离线夹具视觉一致。

## 实现三：Draft、版本与运行隔离

- 创建（POST）、读取（GET）、条件保存（PUT `base_revision`）、发布（POST `publish` `base_revision`）与固定版本读取全部走真实后端；`data-route-dirty` 区分本地未保存编辑，服务端 Draft 与不可变 Version 分区显示，`data-content-digest` 只显示后端值。
- 真实 409：`code=route_draft_revision_conflict` 与 `current_revision` 原样显示，本地编辑保留、服务器内容未被覆盖；提供“重载服务器草案（放弃本地编辑）”和“以服务器修订重试（用本地内容写入）”两条显式路径。旧的“服务端为 rN”本地推断文案随 `route-store` 一并删除。
- 后端没有路线目录 GET：新增“按 route_id 打开”入口，创建/打开后把 `?route=` 写入地址栏，刷新即重新读取服务端草案与版本列表；未虚构任何列表路由。
- 切换地图或路线使用串行序号 + AbortController：晚到结果不能覆盖当前对象；打开路线时若 `map_ref` 与当前地图不同则读取该路线绑定的地图，失败即显式报错，不回退。旧地图的 PointGoal 在新地图上以 `地图绑定不一致` 显式标记并禁用写入，需用户点“清空 PointGoal 以改用此地图”。
- 采用与执行保持禁用并给出后端理由（`adoption_supported=false`、`execution_supported=false`、`arrival_acceptance=not_checked`）；Simulation 导航小窗可切到“明确选中的固定版本”，标注“查看不等于采用”，并保留只读、非规划安全路径与“执行反馈：无”。
- 兼容性发现与解耦：18953 的 mobilecar 读取仍是 `unirobot-mobilecar-read-1`（无 `geometry_binding/geometry_provenance`，`data_source=live_native_http`），前端 3D 工作台按既有严格判定拒绝该来源并显示“3D 数据源不可用 + 使用冻结原生样本”。地图/路线资源不依赖机器人场景，因此 Scene Setup 改为不要求 3D 样本挂载即可使用；Simulation 视图与 Session 抽屉的原有门控、错误恢复按钮保持不变（`browser-workbench` 29 项回归通过）。

## 服务器结果（构建、类型检查、测试、浏览器全部在 cec-sim）

| 套件 | Pass A（18949） | Pass B（18953） |
|---|---|---|
| `npm run build`（含 `tsc --noEmit`） | 通过 | 通过 |
| `npm test` | 66 passed / 0 failed | 66 passed / 0 failed |
| browser-readonly / frozen | 32 / 29 | 跳过（该候选无 geometry-2，见上） |
| browser-geometry / usability | 23 / 100 | 跳过 |
| browser-config | 51（真实 Draft/validate/快照/409/envelope） | 跳过 |
| browser-session | 38（标注 synthetic 协议夹具） | 跳过 |
| browser-map `--mode offline` | 15（无 map 端点显式失败 + 朝向规则 + 小窗回归） | — |
| browser-map `--mode live` | — | 46（真实地图与路线端到端） |

Pass B 实况：目录 `local_map_packages · live=false · supported=true`，Room A/B 两个固定版本；选择 `map_room_a_g3b_release_v1/v1` 后按声明摘要读取 2786 字节 P5 栅格，实际 SHA-256 `01dcdb387aed81b521cba6d31bb5d403d9db1de84b35546c4e34988191069d71` 与声明一致、解码 59×47 与声明一致；`g1_recipe_status=failed`、`navigation_eligible=false`、`current_runtime_status=not_checked` 原样显示。专用测试路线 `route-db64648d23f84396a4c957d38643b5e5`：创建 r1 → 仅改 yaw 保存 r2（后端摘要变化）→ 发布 v1 `9b51b34d…` → 重排（ID 不变）保存 r3 → 发布 v2 `31b39ea1…`，v1 摘要不变、列表 `[v2, v1]`；外部 PUT 后 UI 用旧修订保存得到真实 409 `route_draft_revision_conflict · current_revision=4`，本地编辑保留并显式重载 r4；刷新页面凭 `?route=` 重新打开草案与两个版本；40 个请求中写请求仅为该路线的 route-drafts POST/PUT/publish。交付样本路线 `route-9e55257f…` 的 v1/v2 摘要在测试前后与交付记录完全一致，未被改写。

Pass A 实况：`GET /sessions` 仍为 `{source:"stored", live:false, sessions:[]}`，preflight `read_contract_compatible=false`；真实校验仍 `failed`、`execution_eligible=false`、快照 `cs-cf2a57a1482a90a86dc6ebac0e55de2409e5b724`（sha256 `2e1e9fc5…1e5490`，recipe `4c3e5f42…5e9e`）。

## 仍未执行

18953 未部署 geometry-2 读取与 native binding 补丁，因此该候选上没有可用 3D 场景、真实 prepared/Start、运动、录制或回放；地图为 G3B 历史离线包，不是 live SLAM，`assets_verified` 只表示 manifest 声明资产的逐字节摘要核验（历史包 `manifest.sha256` 自校验遗留不一致仍由后端如实标注）；配置采用、导航执行、目标下发、热重规划与速度发布全部未实现；本轮新增的测试路线只是资源写入证据，不代表任何到点或朝向验收。

文档时点说明：`docs/development.md` 不进入冻结清单，`docs/backend-gaps.md` 进入；两者都在官方 pass 之后定稿，因此服务器 release 目录里的 `backend-gaps.md` 是运行时的较早版本。它们不参与 `vite build`，`dist` 与所有被测代码仍与冻结摘要逐字节一致。

# M1.2e 18949 current 迁移与带朝向 Waypoint 路线切片（2026-10-24）

本轮把 Session 抽屉迁到后端 M1.2d 候选 18949（`SessionList` envelope + 单 Session `current` 只读观测），并在同一 React/TS 工作台内交付 Scene Setup 的“位置＋朝向”地图/Waypoint 路线编辑与本地保存隔离切片。3D 工作台、相机、布局与只读监控保持不变；未开放运动、RESET、录制、导航执行或速度发布。仅写 `frontend/`，未修改 backend、公共契约、native 或根配置，未推送。

## 冻结版本与入口

| 项 | 值 |
|---|---|
| 前端 release | `m1-front-geometry-20261024T132145Z-05cd4ef709d4` |
| 输入 / 聚合 SHA-256 | 81 个输入；`05cd4ef709d43ca89e9a6419ff4e292242aa478c655601bdf3995385d8772ce0` |
| 后端候选 / 上游 | `m1e-20261024T090448Z-platform`（18949，production recipe，`read_contract_compatible=false`） |
| 本轮预览 | 服务器回环 18951 → 18949，PID 2066909（同一冻结 release，`--read-only` 白名单代理） |
| 保留服务 | 18950 → 18944（M1.2c 预览，未停止）；18946 → 18943（M1.2b 预览，未停止）；18943/18944/18949 后端未重启 |
| 真实 native | 8792 仍为 `drvfix` / G4A2 / PID 941842；本轮前后 `run_9c88e3e…` / generation 1 / `episode_43c22f…` / recording=IDLE 完全一致，`native_mutations_sent=false` |
| 环境 | cec-sim，Node 20.20.2 / npm 10.8.2，锁摘要 `1bb055b6e003c960…`，Chromium ANGLE SwiftShader |
| 证据 | 服务器 `reports/m1-front-geometry-20261024T132145Z-05cd4ef709d4/`（build/unit/environment/preview/native-read-only/listeners 与各套件目录） |

## 实现一：18949 Session envelope 与 current

- **类型与客户端**：新增 `SessionList`（`source/live/retrieved_at/sessions`）、`SessionCurrent`、`CurrentBinding`、`CurrentOwner`、`CurrentRecording`；`listSessions` 返回 envelope，`getSession` 返回带 `current` 的单文档。
- **存档与当前分离**：列表解包后显示 `source=stored · live=false · retrieved_at=…`，并明确“它是存档列表，不是 current”。选中 Session 由独立串行 `refreshCurrent()` 走 `GET /sessions/{id}` 读取 `current`，显示 `source / observed_at / valid / status / error / blockers`、runtime、binding、snapshot 资格、授权范围、recording、owner/lease、safety 与四个 ready/available 字段；历史 receipt、attempt 与存档 binding 留在“历史 / 存档字段”折叠区。
- **资格判定**：`可Start`、Owner、Recording、Motion 全部取 `current`，preflight 只作为全局 native 诊断（界面写明“Session 是否可 Start 只以下方单 Session current 为准”）。`current` 尚未读取或读取失败时提示“不能使用存档 execution / start_available / binding status 代替 current ready”，Start 保持禁用。
- **不作存档兜底**：夹具用 HTTP 200 + `current.status=offline, valid=false, error=native_offline` 验证界面仍禁用 Start、仍显示 blockers；`current` 请求被中断（断连）时同样禁用并可显式重试恢复。
- **切换与迟到响应**：切换 Session 触发新的 `current` 读取并作废在途结果；夹具把 `ps-fixture-b` 的 `current` 延迟 3 秒，切到 `ps-fixture-a` 后晚到响应没有覆盖当前选择。
- **TTL 与生命周期**：`prepared` 与 `started` 分开显示，界面写明“prepared TTL 与 started 生命周期由后端 current.status 判定，前端不按本地时钟计算”，存档 `expires_at_backend_monotonic_s` 仅作历史字段展示。夹具分别验证 `prepared`、`started`、`expired`、`identity_changed`。
- **失效处理**：`current` 身份/binding 不一致时 `data-session-invalidated=true`，取消旧手势与待提交目标（`__workbenchInspect().target===null`），保留同一 renderer 实例、相机与布局，Start 禁用且不自动重绑/重发。未取得 Owner、未开录与 binding 失效各自独立显示。

## 实现二：位置＋朝向的 Waypoint 编辑

- 新增共享 `MapWaypointEditor`（`src/map/MapWaypointEditor.tsx`）与坐标层 `src/map/route.ts`：`mapFromPixel / pixelFromMap` 处理原点位移与旋转、分辨率、图像 Y 轴向下；视图旋转/缩放/平移由 SVG 组变换与 `getScreenCTM().inverse()` 反算，因此 map 坐标不随视图变化。
- 每个 PointGoal 携带稳定 ID、顺序、`mapId/mapVersion/frame` 与 `xM/yM/yawRad`；顺序重排不换 ID，删除后新增使用新 ID。朝向为必填：`routeErrors` 拒绝 `yawRad===null`，界面在朝向未设时显示虚线与 `?`，不把缺省值当 0°。
- 手势互斥：空白拖动平移（>3px 不生成点）、点本体拖动移动位置、方向手柄拖拽设朝向；拖动距离小于 `MIN_YAW_DRAG_M`（0.12 m）不提交，因此零长度拖拽不会静默写入 0°。UI 输入角度用度，内部与 wire 用 rad 并归一化到 `[-π, π)`。
- Scene Setup（侧栏“场景布置”）负责创建/编辑/保存并显示地图身份、版本、frame、分辨率、原点、来源与场景兼容状态；地图为独立离线测试来源（`offline-test-map`，图内与元数据都写明“非 SLAM、非导航地图”），未拿 3D 地面或 world_sim 真值冒充地图；Simulation 视口工具栏“导航”小窗以只读方式复用同一编辑器，标注“本地草案 · 未保存 · 保存版本不可用”“执行反馈：无（本轮不导航）”“编辑连线，非规划安全路径”。

## 实现三：保存与运行隔离（后端契约缺口下的边界）

- 18949 `/openapi.json` 实际路径清单没有 map/route/waypoint 端点，代理白名单因此未增加任何路线相关转发，也没有猜测 wire。`data-backend-route-api=unavailable` 与说明写明这一事实。
- 新增 `src/map/route-store.ts` 作为明确标注 `local_session_only` 的会话内存储：保存是带 `draftRevision` 条件写（陈旧修订抛 `RouteConflict`，本地编辑保留并可显式重载存储草案），发布产生不可变 Route Version（内容摘要、来源草案修订、地图绑定、点集），发布不覆盖旧版本、不修改采用引用，采用仍禁用（需后端配置契约）。刷新后草案与版本全部丢失并如实显示“未保存到后端”。
- 单元测试用该存储验证 409 语义、旧版本保留与“仅改朝向也是内容变更”；浏览器测试验证本地保存/发布/重载、采用禁用、`data-route-adopted=none` 以及地图切片零写请求。后端路线 API 就绪后，把该存储替换为真实客户端即可，不需要新增协议假设。

## 服务器结果（全部构建/测试/浏览器在 cec-sim 执行）

| 套件 | 结果 | 归类 |
|---|---|---|
| `npm run build`（含 `tsc --noEmit`） | 通过 | 真实 |
| `npm test` | 54 passed / 0 failed（新增 `tests/route.test.ts` 17 项） | 真实 |
| browser-readonly | 32 checks | 真实 18949 只读 |
| frozen-browser（workbench） | 29 checks | 真实 |
| browser-geometry | 23 checks | 真实 |
| browser-usability | 100 checks | 真实（含最大化/全屏/紧凑布局回归） |
| browser-config | 51 checks | 真实 18949 |
| browser-session | 38 checks | 隔离 synthetic 协议夹具 |
| browser-map | 35 checks | 本地编辑与 `local_session_only` 存储（另加真实 18949 只读页面回归） |

真实 18949 关键事实：`GET /sessions` 返回 `{source:"stored", live:false, retrieved_at:"2026-10-24T13:26:14+00:00", sessions:[]}`；preflight `read_contract_compatible=false` 且 `interface_profile` failed；Draft 创建/保存 201/200（`draft-dbe119d3d3c84dca85101ec0ead74a0c`，draft_revision 2、execution_revision 1）；validate 200 但 `status=failed`、`execution_eligible=false`、`validated_snapshot_id=null`、19 项检查、6 条 blocking reasons；快照 `cs-aa52608a27c0f6d579d2ea29d163cf9effa6709d`，sha256 `46bb89ba5960ba268998a35d139849548a8fa332da777e8c362d468cd7e6f57`，recipe fingerprint `4c3e5f42…5e9e`；真实创建/Start 仍禁用，未发送真实 `POST /sessions`。地图套件共 95 个请求，全部为 GET，无 `/commands`、`/episodes`、`/reset`、`/recording`、`/start` 与任何自造 route 路径。

同一冻结 release 的首轮官方运行在 `browser-usability` 的“退出全屏恢复停靠视口”检查处因等待窗口偏短而中断（未产生 native 影响，证据目录 `reports/m1-front-geometry-20261024T130141Z-5ab2bfba83bc`、`…-r2` 保留为中断记录）；本轮未改动任何产品代码，仅把 `browser-session` 中断后的错误显示改为等待 `data-current-error` 非空，随后对最终冻结输入 `05cd4ef709d4` 重跑全部套件通过。开发记录中此前指向 `091342Z` 的 20 个报告链接已改为服务器实际存在的 `m1-front-geometry-20261024T092102Z-eecb7395d87a`。

## 仍未执行（不得当作已完成）

真实 native binding/录制补丁未部署到 8792，因此没有真实 prepared/active Session、真实 Start、物理运动、录制与回放；SLAM/导航地图来源、后端 Route Draft/Version API 与配置采用契约仍缺；运行中改目标、热重规划、导航执行与速度发布本轮未实现也未开放。地图与路线结果只证明本地交互与保存隔离语义，不证明导航资格。

# M1.2c Session 准备与显式 Start 交付（2026-10-24）

本轮把 Session 抽屉接到 18944（M1.2c, recipe revision 3）：真实 Draft/validate/快照/409 成果保留，新增 `preflight` 当前观测、prepared Session 创建、独立显式 Start、binding/owner/recording/motion 分区展示和状态新鲜度。真实 native 仍未部署 binding 补丁，所以真实环境准确显示阻塞；成功交互只在隔离的有状态协议夹具中验证。仅写 `frontend/`，未修改 backend、公共契约、native 或根配置，未推送。

## 冻结版本与入口

| 项 | 值 |
|---|---|
| 前端 release | `m1-front-geometry-20261024T092102Z-eecb7395d87a` |
| 输入 / 聚合 SHA-256 | 70 个输入；`eecb7395d87a8020da602f85cdc9460dccf23c27a4f4b66d3d22a2700b8444c1` |
| 后端候选 / 上游 | `m1c-20261024T065943Z-platform`（recipe revision 3，fingerprint `4c3e5f42…5e9e`），服务器 18944 |
| 预览 | 服务器回环 18950，代理 18944；PID 1253949（同一冻结 release）。18946→18943 旧预览保留；临时 18947/18948 已停止 |
| 真实 native | 8792 仍为 `drvfix` / G4A2 / PID 941842；未部署 binding 补丁，未重启、未发送运动/RESET/录制/命令 |
| 环境 | cec-sim，Node 20.20.2 / npm 10.8.2，Chromium ANGLE SwiftShader，原锁文件 |

## 本轮行为

- **Session 类型与接口**：新增 `SessionExecution`、`OwnerLease`、`StartReceipt`、`StartBlock`、`StartAttempt`、`RecordingAttempt`、`RecordingBeginReceipt`、`SessionEnvelope`、`CreateSessionRequest` 和 `PreflightRecord`；客户端新增 `createSession`、`startSession`、`preflight`。
- **创建与 Start 分离**：只有当前快照 `execution_eligible=true` 且 `validated_snapshot_id` 非空时创建按钮可用；创建使用快照的 `execution_revision`、`fingerprint`、validated id 与幂等键。创建成功只进入 prepared，不自动 Start。Start 仅在 `state=prepared`、`start_available=true`、binding verified、运行身份新鲜时启用。
- **幂等与超时**：同一快照/修订/指纹的重试复用同一个 `idempotency_key`；不同快照生成新键。创建/Start 使用 8s 动作超时；超时显示“结果未知”并立即回读 `GET /sessions`/`GET /sessions/{id}`，恢复则采用存档，不伪造失败或成功。
- **错误语义**：409 `session_conflict` 回读后端返回的 `session_id`；`idempotency_conflict`、`snapshot_not_found`、`stale_execution_reference`、`recipe_changed`、`validation_incomplete`、`native_offline`、`start_preconditions_unmet`、`native_start_failed` 均保留 code/message/blocking reasons。失效快照提示重新校验或新建草案，不跨数据库复用旧 Draft/快照 ID。
- **生命周期与独立状态**：抽屉分别显示配置/执行合格、prepared、可 Start、active、Owner/lease、recording required/begin_required/ready、motion_ready/motion_blockers、授权范围、Start/recording 回执和 attempt。active 明确不表示取得 Owner、正在录制或允许运动。
- **新鲜度**：`GET /sessions` 只读“最近平台动作存档”，按钮明确写“刷新存档（不调用 native）”，显示 `execution.source/observed_at` 和最近读取时间；`GET /mobilecar/preflight` 显示 `checked_at`、当前 runtime、recording 和真实 checks，按钮写“刷新 native 观测（只读）”。preflight 不改变 Session 存档或资格。
- **失效处理**：选中 Session 的 `native_identity` 与当前 Actual 或 preflight 不一致、或 `native_binding.status!=verified` 时，取消旧手势/待提交目标并禁用 Start；不改变 sample，同内容网格、相机和布局保留，不自动重绑或重发。错误显示 `data-session-invalidated`。
- **代理**：新增 `GET /mobilecar/preflight`、`POST /sessions`、`POST /sessions/{id}/start`；保留 Draft 写入与既有读取。未代理 `recording/begin`、运动、STOP、RESET、回放、媒体或 native 命令。代理放行不等于授权。
- **测试夹具**：`tests/browser-session.py` 以 `page.route` 建立进程内状态机，所有 Session/配置响应标注 synthetic；mobilecar 场景/Actual 仍来自真实 18944 GET，用于保留 3D 回归。夹具验证创建、幂等键复用、超时回读、409、Start 拒绝/成功、freshness、binding 失效与目标取消。未加入生产模拟 Passed 或门禁开关。

## 真实 18944 结果（非夹具）

| 操作 | 真实结果 |
|---|---|
| GET preflight | 200；`checked_at=2026-10-24T09:25:25+00:00`，`read_contract_compatible=false`，`session_ready=false`，`interface_profile` failed |
| GET sessions | `[]`；没有 prepared/active/failed Session |
| Draft create/save/reload | 201/200/200；Draft `draft-525edd1875b241f291d552017a93f263`，draft_revision 2，execution_revision 1，名称/描述持久化 |
| validate | 200；`status=failed`，`execution_eligible=false`，`validated_snapshot_id=null`，19 项检查，6 条 blocking reasons |
| 快照 | `cs-78f4238e15010a2a9b8f929f7f5f047389530027`；sha256 `394085075397e3f08147d4d3e027af14ebcc3a456e08f318d9fc65582b64e594` |
| 创建 / Start | 真实环境不满足条件；创建按钮禁用，未发送真实 `POST /sessions` 或 `/start` |
| 409 冲突 | 外部宿主 PUT 推进 revision 后，UI 用旧 base_revision 保存得到真实 409 `conflict`；服务端保留外部值，UI 保留本地文本，显式读取后采用服务器版本 |
| 请求 | 同一 release 经代理 542 GET / 3 POST / 3 PUT；平台写请求来自 Draft create/save/validate，无 Session/start、commands、episodes、RESET、recording 或 native 命令 |
| native 影响 | run/generation/episode、recording=IDLE 前后一致；无 native mutation、无新物理实例 |

真实运行身份：`run_9c88e3e...` / generation 1 / `episode_43c22f...`；几何内容身份 `cb789964...18a7cc`。

## 合成夹具结果（与真实分开）

`browser-session.py` 24 checks passed，全部标注 synthetic：

- 首次创建 503 `native_offline` 后重试，两个请求使用同一幂等键；创建成功不自动 Start。
- Start 先被 409 `start_preconditions_unmet` 拒绝，Session 保持 prepared 并记录 refused attempt；显式重试后 active，owner=`not_acquired`、recording_ready=false、motion_ready=false。
- 同 runtime 已有 Session 时 409 `session_conflict` 被回读；延迟创建超时后通过 GET 存档恢复为 prepared，未自动 Start。
- 刷新存档不改变 `execution.observed_at`；刷新 preflight 更新 `checked_at` 而不改变 Session 存档。
- binding/native identity 变化后取消本地 Target，Start 禁用，renderer/camera/instance 不变，且不自动重发。
- 所有 live mobilecar 请求为 GET；没有 native `/session/*`、commands、recording、RESET 路径；夹具写请求仅 Session create/start。

## 同一冻结版本的验证

| 套件 | 结果 |
|---|---|
| 类型检查 + 生产构建 | `tsc --noEmit && vite build` 通过；保留既有大 chunk 提示 |
| 单元 | 37 passed：新增 create/start/preflight wire、身份/运动学/配置回归 |
| 真实只读 | 32 passed：三接口、23 资产、Actual 持续、断连/身份/坏字节夹具 |
| 冻结工作台回归 | 29 passed：Joint/TCP、Actual/Target/Ghost、取消、Orbit、布局 |
| 几何/装配 | 23 passed：23 网格、TCP 对齐、三视图、跨 Actual 持续拖动 |
| 可用性 | 100 passed：缩放/取景/分隔条/最大化/全屏/预设/持续拖动/1366/1920/125% |
| 真实 18944 配置 | 46 passed：preflight、Draft 保存/重载/校验、动态 checks/reasons、快照、真实 409、迟到 validate、断连、创建按钮禁用、无 Session 写 |
| 合成 Session 协议 | 24 passed（synthetic）：创建幂等、超时恢复、409、Start 拒绝/成功、freshness、binding 失效、3D 目标取消 |

报告：[集成摘要](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/integration-summary.json)、[源码清单](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/source-manifest.json)、[构建](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/build.log)、[37 单元](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/unit.json)、[32 只读](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/browser/browser.json)、[29 冻结](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/frozen-browser/browser.json)、[23 几何](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/geometry/geometry.json)、[100 可用性](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/usability/usability.json)、[46 真实配置](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/config/browser.json)、[24 合成 Session](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/session/browser.json)、[native 前后](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/native-read-only.json)。

截图：[prepared](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/session/session-prepared.png)、[active 且 owner/recording/motion 分离](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/session/session-active.png)、[超时回读恢复](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/session/session-recovered.png)、[binding 失效并取消目标](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/session/session-invalidated.png)、[真实 18944 配置校验](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/config/config-validated.png)、[真实 409 错误态](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/config/config-conflict-actual-final.png)、[Session 抽屉真实空状态](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/usability/usability-session.png)、[真实只读](../reports/m1-front-geometry-20261024T092102Z-eecb7395d87a/browser/real-readonly.png)。

## 验证中修掉的问题

1. 首轮测试在闭合 `<details>` 内等待 attempt“可见”；改为等待 DOM 挂载，产品本身正常。
2. 超时创建实际在毫秒级完成“unknown → 存档回读恢复”，测试无法稳定捕获瞬时横幅；改为验证恢复后的提示、最终 prepared 状态和同一幂等键，不把瞬时提示当作唯一证据。
3. 测试夹具在第二次延迟创建时被“已有 active Session”规则误拦；仅对显式 conflict 模式保留单 Session 冲突，成功/超时路径使用独立合成 runtime 会话。
4. 真实配置测试早期断言默认快照已存在，改为在自身 Draft validate 后检查 `execution_eligible=false`、创建按钮 blocked、无 Session Start 动作。
5. 新增 preflight 后，只读/可用性网络白名单同步扩展；仍断言无 native 写路径。
6. 收紧跨数据库/删除边界：如果选中的草案已不在当前后端列表，抽屉清空旧草案与快照并提示新建；`draft_not_found` 显示具体重建提示，不保留可误用的旧 ID。

## 边界与未覆盖

**真实通过**：18944 preflight 当前观测、真实 Draft 保存/重载/validate、动态 checks/blocking reasons、不可变快照读取、真实 409 冲突、空 Session 读取、创建按钮在真实不合格快照上禁用、无 Session/运动/录制写请求。

**仅合成夹具通过**：prepared 创建、幂等重试/重放、超时回读恢复、Start 拒绝/成功、owner/recording/motion 分离、binding 失效与目标取消、preflight/存档 freshness 分离。夹具不提交到真实 18944，也不证明 native binding。

**等待 native 部署**：真实 G1 prepared/Start、`m1-binding-1` 原生端点、无 RESET 开录 `m1-recording-1`、owner/lease 获取、STOP/停车确认/finalize、真实录制与回放、运动学标定/TCP 姿态/部署 attestation。本轮没有把这些写成 M1 通过，也没有进入运动、录制或回放开发。

## Git

本轮只写 `frontend/`；源码、测试与证据保存在 `codex/m12a-workbench`，未推送。历史保存点 `71c52e5`、`af8ab60a`、`eed1537` 等保留。冻结 release 的 70 个输入在交付前逐一核对与工作树一致；本页按既有约定不参与源码聚合。

---

# M1.2b 配置接线交付（2026-10-24）

本轮把已完成的 3D 工作台接到 M1.2b 候选 18943：真实 Draft 创建/列表/读取/保存、`validate`、不可变配置快照、configuration/readiness 逐项检查、`blocking_reasons`、recipe fingerprint 和空/失败 Session 读取。仅写 `frontend/`；未修改 backend、公共契约、native 或根配置，未推送。

## 冻结版本与入口

| 项 | 值 |
|---|---|
| 前端 release | `m1-front-geometry-20261024T073114Z-af8ab60a4c56` |
| 输入 / 聚合 SHA-256 | 69 个输入；`af8ab60a4c5672556b0c20a4f76a82480915b0a4b23f618e3d4940596a82d67a` |
| 后端候选 / 上游 | `m12b-20261024T034103Z-4be0d6c86d7b`（提交 `4be0d6c`），服务器 18943；实测进程 cwd 与该 release 一致 |
| 后端 wire | `unirobot-mobilecar-geometry-2`、`read-1`、`unirobot-mobilecar-kinematics-1`、`unirobot-execution-recipe-1` |
| 预览 | 服务器回环 18946，代理 18943；PID 3659380（同一冻结 release） |
| 保留服务 | 18935、18933、18932、18931、18941、18942、18943、native 8792 均保留；只停止本方失败/上一轮临时预览 |
| 环境 | cec-sim，Node 20.20.2 / npm 10.8.2，Chromium ANGLE SwiftShader，原锁文件 |

## 本轮行为

- **Draft**：列出、读取、创建（默认 preset）、保存。可编辑字段仅为后端声明的 `name` / `description`；保存使用 `base_revision`，`execution_revision` 由后端维护。没有任意初态、场景编辑或机器人配置写入。
- **校验 / 快照**：`POST /experiment-drafts/{id}/validate` 使用当前 `execution_revision` + `fingerprint`；响应更新 Draft，并自动 `GET /config-snapshots/{id}`。抽屉逐项显示 configuration/readiness 的 `key/status/phase/scope/detail`、`blocking_reasons`、`execution_eligible`、`validated_snapshot_id`、`reused`、`snapshot_id/sha256`、`validation_scope`、recipe fingerprint 与来源摘要。
- **摘要不等于资格**：界面只把“通过 X/Y”作摘要，单独显示 `execution_eligible`；只有后端 Session 状态才表示 Session 资格。
- **Session 准备**：读取 `GET /sessions`，空数组、failed、unsupported 均作为正常可解释结果；Start/运动/RESET/录制/回放继续禁用。本轮不代理 `POST /sessions` 或 start。
- **geometry-2**：运行身份变化只取消旧手势与本地目标，保留已验证网格、相机、布局；内容身份变化或 binding 不一致明确失效并重载。`contentKey` / `runtimeKey` 分开，snapshot 轮询不会因正常 RESET 重建 renderer。
- **运动学**：live 模式消费 `GET /mobilecar/kinematics` 的 `landerpi.kinematics.v1`，并用 `execution-recipe` 的模型/场景 pin 与 profile digest 交叉核对；检查关节顺序、单位声明、TCP 父节点/site、相机父节点、5 项实时一致性。`orientation_xyzw=null` 显示“未声明”，不生成姿态。元数据缺失/不匹配禁用本地 Joint/TCP 并显示原因，不自动回退冻结 profile。
- **冻结来源**：保留独立 `sample/arm-spec.json` 参考 profile，明确标为非 live；不参与平台资格。
- **代理**：按方法+路径白名单放行既有读取、kinematics、execution-recipe、Draft POST/PUT/validate、配置快照与 Session 读取；保留真实 HTTP 状态、错误体、查询参数和 Content-Type。Session 创建/start、运动、RESET、录制、媒体、native 命令未放行。

## 真实环境结果（非夹具）

最终 release 的真实配置测试创建并使用 Draft `draft-68597f12a82545c8aeadc8cb8d7c4b56`：

| 操作 | 真实结果 |
|---|---|
| POST create | 201，`draft_revision=1`，`execution_revision=1`，`validation.status=unvalidated` |
| PUT save | 200，`draft_revision=2`，`execution_revision=1`；名称/描述持久化 |
| 浏览器重载 + GET draft | 读取到同一 revision 2 与保存后的名称 |
| POST validate | 200，`validation.status=failed`，`execution_eligible=false`，`validated_snapshot_id=null` |
| 快照 | `cs-00c41826ad4a3e2155bc32081ff46ba01001b6c7`；sha256 `6df8af76cfeb7c9728a71396d771233d09e61fa76d9074b48f8edc7dff327752`；17 项检查（12 passed / 1 failed / 4 unsupported） |
| 快照独立读取 | GET `/config-snapshots/{id}` 的 sha256、checks、eligibility、blocking_reasons 与 validate 一致 |
| 阻塞原因 | 5 条：`interface_profile`（configuration）；`deployed_config_attestation`、`scene_manifest_attestation`、`session_binding_protocol`、`recording_begin_protocol`（readiness） |
| GET sessions | 空数组；Start 仍禁用 |
| 409 冲突 | 外部宿主 PUT 推进 revision 后，UI 用旧 `base_revision` 保存得到真实 409 `conflict`；服务端保留外部值，UI 保留本地文本，显式“读取服务器版本”后才采用 |
| 请求 | 同 release 代理记录 500 GET / 3 POST / 3 PUT；3 个写请求为 Draft create、validate、save/冲突重试链，没有 Session/start、commands、episodes、RESET、recording 或 native 命令 |
| native 影响 | run/generation/episode、recording=IDLE 前后一致；无 native mutation、无新物理实例 |

真实运行身份：`run_9c88e3e...` / generation 1 / `episode_43c22f...`；内容身份 `cb789964...18a7cc`；当前 `runtime_identity_matches=true`。

## 夹具验证（与真实结果分开）

以下由自动浏览器合成响应验证，**不是真实 RESET 或真实故障**：

- geometry-2 仅运行身份变化：renderer 实例、`contentKey`、相机与布局保持；旧 Target 清空；Actual/Target/身份更新。截图与 trace 见 `browser/browser.json` 的 `identity_transitions`。
- 内容身份变化：明确失效并重建场景，未沿用旧网格。
- 延迟 validate 后切换 Draft：迟到结果未覆盖当前 Draft。
- Draft 列表断连：显示错误，解除后显式刷新恢复。
- 慢 snapshot / 断连 / 坏资产 / 身份跳变沿用既有只读测试。

## 同一冻结版本的验证

全部在服务器 cec-sim、同一解包产物执行。

| 套件 | 结果 |
|---|---|
| 类型检查 + 生产构建 | `tsc --noEmit && vite build` 通过；保留既有大 chunk 提示 |
| 单元 | 35 passed：身份拆分、geometry-2 binding、kinematics 模型 pin/一致性/orientation=null、配置 wire/409/422、冻结回归 |
| 真实只读 | 32 passed：三接口 + 23 资产、Actual 持续、慢响应不重叠、断连/身份/坏字节夹具、运行身份保持内容、资源变化重建 |
| 冻结工作台回归 | 29 passed：Joint/TCP、Actual/Target/Ghost、取消、焦点、Orbit、布局重建/恢复、切源 |
| 几何/装配 | 23 passed：23 网格、TCP 对齐、前/侧/顶视图、跨 Actual 持续拖动 |
| 可用性 | 100 passed：滚轮/按钮缩放、适配/全景/聚焦、分隔条、最大化、全屏、布局预设/保存恢复、持续拖动、1366×768 / 1920×1080 / 125% |
| 真实配置流程 | 38 passed：创建/保存/重载/validate/快照/session 空、真实 409、迟到 validate、断连、写方法边界 |
| 只读边界 | 所有浏览器 API 读取为允许的 GET；写请求仅为 Draft create/save/validate |

报告：[集成摘要](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/integration-summary.json)、[源码清单](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/source-manifest.json)、[构建](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/build.log)、[35 单元](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/unit.json)、[32 只读](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/browser/browser.json)、[29 冻结](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/frozen-browser/browser.json)、[23 几何](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/geometry/geometry.json)、[100 可用性](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/usability/usability.json)、[38 配置](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/config/browser.json)、[native 前后](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/native-read-only.json)、[环境](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/environment.json)。

截图：[真实配置校验](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/config/config-validated.png)、[409 冲突错误态](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/config/config-conflict-actual.png)、[Session 抽屉](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/usability/usability-session.png)、[1366×768](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/usability/usability-1366.png)、[3D 专注](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/usability/usability-focus3d.png)、[125%](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/usability/usability-125.png)、[真实只读](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/browser/real-readonly.png)、[几何斜视](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/geometry/oblique-viewport.png)。冲突错误态截图在冻结套件后用同一预览补拍，源码/测试未改；见 [conflict-capture.json](../reports/m1-front-geometry-20261024T073114Z-af8ab60a4c56/config/conflict-capture.json)。

## 验证中修掉的真实问题

1. 首轮类型检查发现 recipe 可能为 null 的收窄错误与 Vitest Mock 调用签名错误；修正后通过。
2. 只读夹具把 `scene_id` 改为 `fixture-scene-0`，与 execution-recipe 的真实 pin 不符，模型 pin 检查正确禁用了本地预览；夹具改为仅在资源变化时改内容，运行身份变化保留真实 scene_id。
3. 配置测试误把 async Playwright `expect_response().value` 当同步属性；修正为 `await`。
4. 可用性测试缺少 `urlsplit` 导入；修正。
5. 运行身份变化检查与 reload 后的自动取景 timer 竞争；测试在捕获前等待取景稳定，并在报告中记录前后 instanceId/contentKey/camera。
6. 实际发现控制条会在慢首帧（如 1132 ms）时因监控文字变长而换行，1366×768 固定条带从 150px 涨到 180px；收紧控制条间距并把 monitor chip 限制到 200px，重跑同一冻结流程通过。

## 边界与限制

**真实可用**：3D 只读监控、geometry-2、版本化运动学元数据与 recipe pin 核对、Draft 创建/列表/读取/保存、validate、快照读取、逐项检查/阻塞原因/Session 空列表读取、真实 409 处理。

**仅夹具通过**：运行身份漂移时保留网格/相机/布局、内容身份变化失效、延迟 validate、Draft 列表断连恢复。真实 native 未 RESET，也没有制造真实断连。

**仍被 native 阻塞**：prepared Session 创建/Start（无 `m1-binding-1` 无运动绑定）、真实 Passed/ValidatedSnapshot（interface_profile 与 readiness 证明缺失）、运动学标定与 TCP 姿态、Owner/lease/命令回执、录制 begin/finalize、RESET 实际应用、媒体、只读 Episode 回放。本轮不显示 Ready，不开放这些端点。

## Git

本轮只写 `frontend/`；源码、测试与证据保存在 `codex/m12a-workbench`，未推送。历史保存点 `eed1537`、`596c0d7` 等保留。冻结 release 的 69 个输入在交付前逐一核对与工作树一致；本页按既有约定不参与源码聚合。

---

# M1.3 3D 视口与布局可用性交付

2026-10-23。保存点 `596c0d7`（真实只读联调 + 车体修正，含 63 个未提交证据文件）之后开始本轮；只写 `frontend/`，未改 backend、公共契约、native 或公共锁文件，未推送。本轮目标是把 3D 工作台做成真正可操作，并在同一外壳准备 Session 界面。下方原车体渲染记录按历史保留。

## 本轮行为

| 能力 | 实现 | 边界 |
|---|---|---|
| 聚焦选中对象 | `focusSelection`：选中 `arm` 时框住整臂，选中 link 时框住该 link；保持视角方向。视口内 `F` 同义 | 只改相机 pivot/距离，不改选中、Target 或控制权 |
| 适配模型 | `fitModel`：只框机器人可见几何（排除 pending、隐藏 geom、地面 plane），保持方向 | 不含场景物件 |
| 恢复全景 | `fitScene`：机器人 + 可见场景对象，并恢复默认 3/4 俯视方向 | 不旋转模型根节点 |
| 应用内最大化 | 锁定版 Dockview 公开 API：`maximizeGroup` / `exitMaximizedGroup` / `hasMaximizedGroup` / `onDidMaximizedGroupChange` | 未升级 Dockview、未重写布局框架 |
| 浏览器全屏 | `main` 元素全屏，覆盖数据源、状态、布局条、视口（含 HUD 与取消目标）、Inspector、传感器、时间轴、状态栏与弹层 | 被环境拒绝时显示 `NotAllowedError` 等真实原因，应用内最大化仍可用，不显示假成功 |
| 相机缩放 | 滚轮/触控板沿用 OrbitControls；工具栏 ＋/− 用相机 dolly，受 `minDistance/maxDistance` 限制 | 不缩放 mesh、不拉伸 Canvas |
| 面板缩放 | 分隔条加可见描边 + `::after` 命中扩展；左右栏、传感器、时间轴可拖动、折叠、恢复 | 折叠/恢复时重新分配垂直空间，不重建视口 |
| 布局预设 | 标准工作台 / 3D 专注（收起传感器与时间轴、收起导航、最大化视口） | 预设切换不改变 Target、Actual 或控制权 |
| 顶部压缩 | 原 runtime 63 + authority 39 + monitor 30 合并为 42px 控制条 + 可展开详情 | 只读、陈旧、Owner、重新加载仍可达 |
| Session 准备 | Draft / 校验 / prepared Session 三段抽屉，读取真实 envelope 标志 | 不出现 Ready；Start/运动/RESET/录制仍禁用 |

## 修掉的实际缺陷

1. `cancelGesture()` 只清 `gizmo.dragging`，不释放 `interacting`，一次失焦即可让工具、布局、数据源全部卡死；现在统一释放并清 `gizmo.axis`。
2. Dockview 布局事件与 `disableDnd` 属性抖动会在拖动中触发取消；`resize()` 现在只在宿主尺寸真变时返回 true，取消只在真实重排时发生，DnD 改为常量关闭。用新增的 gesture trace 定位（`cancel:layout`）。
3. 继承相机位于 pivot 下方，被 `maxPolarAngle` 夹成近乎水平视角；改为显式 3/4 俯视，默认取景框机器人。
4. `fitView` 把 4 m 地面当主体，相机被推到 5.5 m 上限；取景排除 plane。
5. 折叠传感器时 Dockview 把空间给时间轴、视口反而缩小；新增结构化 rebalance，折叠后视口变大、恢复后对称。
6. 布局“重置”用 `key` 重建整个 Dockview，会销毁 renderer 与相机；改为结构化重置，同一 renderer/相机/目标保持不变。
7. 1366×768 下固定条带 270px、视口仅约 140px 高；现在固定条带 150px，视口画布 319px（1920×1080 为 518px）。
8. 125% 页面缩放下 `.application{min-height:640px}` 造成页面溢出、状态栏被裁；已移除，并让短视口默认进入 3D 专注。
9. 分隔条颜色与背景几乎同色；改为可见描边与 hover 高亮。
10. Inspector 单一滚动会把“取消目标/提交执行”滚出屏幕；改为局部滚动 + 固定动作栏 + `<details>` 诊断。
11. 相机“前/侧”与车体方向相反（旧“前”为 world_sim −Y）；按车轴重命名为车头(+X)/车侧(−Y)/顶视(+Z)，只改相机。

## 同一冻结版本的实际验证

release `m1-front-geometry-20261024T041729Z-254ee2318a57`（65 个输入，aggregate `254ee2318a574695643a02fc72e64bf94090da737789de116a6d8e03d588ad64`），全部在服务器 cec-sim 的同一份解包产物上执行：Node 20.20.2 / npm 10.8.2，Chromium ANGLE SwiftShader，代理上游为几何候选 18942。

| 验证 | 结果 |
|---|---|
| 类型检查与生产构建 | `tsc --noEmit && vite build` 通过；保留既有大 chunk 提示 |
| 单元 | 23 passed：含 envelope 能力标志不升级为就绪、声称 ready 的 envelope 被拒绝、编译网格不二次 scale、Joint4 零位 |
| 真实只读 | 30 passed：三接口、23 资产摘要、Actual 持续更新、慢响应不重叠、断连/身份跳变/坏字节夹具 |
| 冻结交互回归 | 29 passed：Joint 环、TCP 轴、数值、取消、焦点、Orbit、布局、切源 |
| 装配/几何 | 23 passed：23 网格装配、TCP 对齐误差、前/侧/顶视图、跨 Actual 刷新的持续拖动 |
| 可用性（新增） | 99 passed：滚轮/按钮缩放、适配/全景/聚焦、分隔条双向拖动、最大化、全屏进入退出、布局预设、面板折叠、布局保存恢复、Esc 全屏、TCP 持续拖动、1366×768 / 1920×1080 / 125% |
| 只读边界 | 全部浏览器请求仅 GET；无运动/RESET/录制端点；native run/generation/episode 前后一致 |

关键数值（同一 release）：1366×768 画布 678×319、固定条带 150px、页面不滚动；1920×1080 画布 1048×518；125%（CSS 1093×614、DPR 1.25）画布 472×170，状态栏仍在视口内；滚轮 0.969→0.782→0.969 m；最大化 618×319→1202×541，同一 renderer、相机与目标；TCP 持续拖动跨 12 次快照、Actual 位移 5.5e-16 m、相机不动、面板尺寸不变。

证据：[源码清单](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/source-manifest.json)、[构建](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/build.log)、[23 项单元](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/unit.json)、[30 项只读](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/browser/browser.json)、[29 项冻结交互](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/frozen-browser/browser.json)、[23 项装配/几何](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/geometry/geometry.json)、[99 项可用性](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/usability/usability.json)、[原生只读前后](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/native-read-only.json)、[preview](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/preview.json)、[release 摘要](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/release.json)。

可用性截图为同一 release：[1366×768](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/usability/usability-1366.png)、[1920×1080](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/usability/usability-1920.png)、[3D 专注](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/usability/usability-focus3d.png)、[125% 缩放](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/usability/usability-125.png)、[Session 准备](../reports/m1-front-geometry-20261024T041729Z-254ee2318a57/usability/usability-session.png)。

## 预览与版本

- 候选预览：服务器回环 18935，代理 18942；SSH 隧道提供 http://127.0.0.1:18935/ 。已验证的 18933（`m1-front-geometry-20261023T192903Z-58a156740be8`）与 18931/18932 保持原状，未重启或停止。
- 本轮不进入 prepared Session 的真实 Start/接管/录制；Session 抽屉只呈现后端已返回的 false 标志与阻塞原因。
- 遗留：运动学仍是本地固定参考 profile（按模型摘要匹配），等待后端版本化元数据；媒体与连续 Episode 仍未接入；浏览器全屏在嵌入环境可能被拒绝，此时只有应用内最大化可用；软件渲染下会触发像素比降至 1.0 的自适应提示。

---

# LanderPi 车体渲染修正交付

2026-10-23。本轮按用户要求只修车体几何与材质；现有 TCP 手柄、拖动、数值编辑、取消、Joint、Actual/Target/Ghost 与实时只读监控保留。没有改为Viser、加入点云/可达性层、逐件位移/旋转补偿、移动模型根节点、改关节零位或伪造Actual。下方原只读联调记录按历史保留。

## 前端已修复

- `native-scene-view.js` 的 `_buildGeom` 在构造/拾取前跳过 authored alpha<=0；可见primitive和mesh都保留，不使用collision/group或零件名字删外观。半透明Actual实际启用混合并关闭opaque深度写入；Ghost保持既有蓝色候选样式并乘源alpha。
- 服务适配层消费 `unirobot-mobilecar-geometry-1` / verified compiled geometry scene。compiled STL的scale、居中与主轴预处理已烘焙，前端仅应用既有geom→body→joint→world_sim显示链，不二次scale。新增资产坐标、单位、source身份和geometry_provenance穿过内部类型/适配层；新增contype/conaffinity保留原义。无编译坐标约定的live scene拒绝，不能把旧raw STL组合标为已修正。
- 真实源继续按关节名使用model_joint_positions_rad；joint4用户0→模型−π/2未改。TCP实际标记不依赖本地目标，编译网格不会改变关节链或真实TCP。`geometry_source_changed`作身份失效处理，清旧预览并重载/明确不可用。
- 旧冻结资产与交互夹具保留，显式标为“冻结旧样板 · 网格坐标未修正”；不作为本轮装配证据。23个新compiled STL留在后端服务器，经API加载，未拉回平台模型目录。
- 检查模式只增加只读的geom局部AABB、变换局部AABB得到的world_sim范围、矩阵及TCP误差；这些是可视几何诊断，不是在线接触真值。页面header显示本次release摘要。

## 后端已补齐及仍有边界

用户明确授权与后端对齐后，向“Continue M1.1(后端)”发出坐标契约与原生导出字段修复请求。后端选择编译网格方案，独立提供18942；主智能体只写frontend，未修改backend、公共契约或原生工程。

后端交付记录：[backend-m1-geometry.md](/home/liaozhengyan/.codex/worktrees/backend-m1-read/uniRobotPlatform/docs/backend-m1-geometry.md)。geometry-1的scene、每资产coordinate_space/units/preprocessing/source_sha256/source_mesh_name、新字节SHA/URI、真实group/contype/conaffinity与来源摘要均已补齐；capabilities/snapshot仍为read-1。`chassis_collision`实际group3/contype2/conaffinity1/alpha0，`base_link_visual`仍是可见外观；collision只表示过滤参与。

当前必要几何信息已足够完成本切片。候选绑定本次native运行和静态编译来源，换run/模型/场景后需后端重新生成验证包，不承诺通用热切换；18941保持旧版兼容服务。验证范围为static compilation匹配live manifest，不是读取在线C内存/接触，也不授予执行资格。用户角/TCP本地运动学仍采用已有固定参考profile，版本化元数据和Session/控制/录制/媒体/回放仍按既有缺口保留，未在本轮扩展。

## 当前预览与版本

- 请查看 [http://127.0.0.1:18933/](http://127.0.0.1:18933/)，它代理服务器18942；18931/18932仍是旧预览。新预览PID800217，SSH仅作本地回环转发；页面header摘要为 `58a156740be8`。
- 前端release `m1-front-geometry-20261023T192903Z-58a156740be8`，63个输入；aggregate SHA256 `58a156740be83a2879e5a1d2145f77d552d51f6682b1e3d318d6a2b048044276`。
- 后端候选 `m1-geometry-20261023T192202Z-cdfc7472e5de`（后端提交42cdd6a），geometry bundle `275389464eee2f3de0c2ddf96ae85acbedfd382c496a589ec41a3662ee31d171`。接口 `geometry-1 + read-1`，native profile `g4a1-1.0`。
- 既有native8792/PID941842、read网关18941/PID1155600、几何候选18942/PID397182、旧18931/PID2614787和18932/PID293264均保留。只停止了本方核对PID/argv后的失败18933候选，未触及其他服务。

## 实际验证与截图

全部在服务器 cec-sim 的同一冻结前端release执行，Node20.20.2/npm10.8.2/原锁文件；Chromium ANGLE SwiftShader。没有以GPU性能或真人体验验收作扩张声明。

| 验证 | 实际结果 |
|---|---|
| 输入、类型检查、生产构建 | 63文件上传逐项SHA一致，`tsc --noEmit && vite build`通过；仍保留既有大chunk提示 |
| 单元 | 21 passed：旧FK/IK/零位、只读投影隔离，加alpha0/半透明/基础几何保留、编译网格不二次scale与缺失坐标约定拒绝 |
| 只读浏览器 | 30 checks passed；三接口、23网格新摘要、身份/断连/迟到/坏资产夹具及相机/目标稳定 |
| 旧交互回归 | 29 checks passed；TCP/Joint手柄、数值、取消、焦点/失焦、选择、Orbit、布局与源切换 |
| 新装配与TCP | 23 checks passed；Ghost关闭、无本地目标、所有可见geom保留、不可见碰撞不构造；四轮前后/左右分离、薄轴沿Y、支撑高度一致、底盘水平、两壳体/臂基座/两夹爪完整；TCP拖拽跨两次Actual刷新不丢目标或相机 |
| 几何数值 | 四轮中心与AABB、底盘范围/可见网格矩阵存于geometry.json；最终渲染关节链到真实TCP标记误差 `1.694362330178007e-14 m`；未改Actual或机器人模型来满足断言 |
| 三视图人工复核 | 主智能体查看了本版前/侧/斜视截图，车体水平、轮组及壳体装配完整，机械臂/夹爪与既有TCP链一致。截图Ghost关闭、无Target，并关闭场景物体层防止方块遮挡；grid仍为观察辅助 |
| 原生与网络 | 所有浏览器与代理API记录仅GET；native运行/Episode/recording与PID前后相同，无运动/RESET/录制，无新物理实例 |
| 回传 | 约1.40MB，25个证据文件按索引核对SHA，原始大网格留服务器；63个运行输入在交付前再次核对一致。本页/报告排除自引用hash |

沿用既有观察相机按钮的命名：UI“前”为Three +Z，即world_sim −Y（车侧）；UI“侧”为Three +X，即world_sim +X（车头）；斜视为原全景相机方向。没有为截图改根节点或旋转机器人。前、侧使用相同相机距离/观察中心，具体相机与tick记录在geometry.json。以机器人方向命名的截图：

- [车头视图（world_sim +X）](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/geometry/side-viewport.png)
- [侧视图（world_sim −Y）](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/geometry/front-viewport.png)
- [斜视图](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/geometry/oblique-viewport.png)
- [TCP本地预览](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/geometry/tcp-local-preview.png)

证据：[源码清单](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/source-manifest.json)、[21项单元](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/unit.json)、[30项只读](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/browser/browser.json)、[29项交互](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/frozen-browser/browser.json)、[23项装配/几何/交互](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/geometry/geometry.json)、[真实geometry scene](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/geometry/scene.json)、[进程/身份/网络摘要](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/integration-summary.json)、[完整产物索引](../reports/m1-front-geometry-20261023T192903Z-58a156740be8/server-artifact-index.json)。

首轮同代码候选已通过装配15项与两组既有浏览器回归，后续测试将已显示的0再次fill为0而未触发React change，导致错误地等待一个未创建Target；修正为先编辑1再回0，完整冻结新版本重跑，未拼接旧候选结果。只读子代理关于Ghost transparent的担心经主智能体核对：Ghost材质构造时已保证transparent=true；实际补齐的是后续蓝色样式opacity继续乘源alpha。所有子代理只读，未运行验证或修改。

本轮切片可检查；未声明真实M1控制、录制或回放闭环通过。前端新改动/报告留在本方worktree，未提交或推送，原M1.2a保存提交e73624e及上一轮成果均保留。

---

# 第一轮真实只读联调交付记录

2026-10-23。最新记录优先；下方原 M1.2a 样板记录作为历史证据保留。前端恢复、只读接入及服务器验证均由用户明确授权，本轮已完成可检查切片，**不代表真实 M1 控制/录制/回放闭环通过**。

## 保存与修改边界

- 先将原 M1.2a 与验证证据保存为本地提交 `e73624e`；共同基线仍为 `2f7ff9b091c060034e55d2f387dbb6e130aaada3`，当前分支 `codex/m12a-workbench`。
- 本方 worktree `/home/liaozhengyan/.codex/worktrees/frontend-m12a/uniRobotPlatform`；本轮仅修改 `frontend/`，未改 backend、公共契约、native、根配置或公共锁文件，未推送。新实现与报告保留在本方工作树中，未自动提交第二次。
- 三路子任务只读核查最新 Schema、Actual 刷新/renderer 边界、故障验证要求，主智能体整合、修改与实际执行验证。子任务指出的 gripper Actual/Target 模型角映射遗漏已由主智能体补齐。

## 当前可操作内容与数据来源

默认进入 **真实只读监控**：从平台 scene/capabilities 初始化，持续读取 snapshot；23个真实 STL 使用本次 scene URI，经同源代理携带 sha256 查询参数获取，在解析前核对字节摘要。普通快照复用同一场景/renderer，不重置相机、选择、Dockview 布局或本地目标。

Actual 是后端实时反馈，按 `model_joint_positions_rad` 原生关节名渲染。用户角和模型角分别保留；joint4 用户零位约0、模型零位约 −π/2。后端已有 Target 独立只读显示（关节、底盘、夹爪）；`command_id=null/tcp=null` 没有被转成成功回执。本地 Joint 环/数值/滑条、TCP 手柄/数值、Ghost 和取消继续可用，不写 Actual，也不发控制请求。

本地候选使用已固定参考运动学 profile；元数据来源与匹配限制见 [provenance](provenance.md)。根 XML 摘要匹配不证明远端全部配置一致。未知模型不猜测用户角映射，禁用本地候选但保留只读 Actual；后端尚缺版本化映射/TCP安装元数据，最小建议见 [backend-gaps](backend-gaps.md)。本地 IK 只约束位置，未作姿态/碰撞/动力学/后端计划认证。

world_links 只标为编译初态，不是物体实时位姿。真实源的 Actual 使用显式字段投影，diagnostics/GT/Oracle 不从冻结来源合并。RGB/Depth 只显示缺少媒体，native SensorState 引用不用于下载图像。时间区域显示源 sim/feedback/tick 与本地接收年龄；没有伪造连续 Episode 或录制轨迹。

Session/Start、停止、接管、执行、录制、播放仍禁用；观察到的 Owner 不授权本方。`?source=frozen` 或数据源菜单可显式打开冻结样本；不自动回退，不把它称为历史 Episode 回放。没有新增模拟成功路径。

## 轮询、失效与代理

先在服务器测得 snapshot 约48–88ms，默认请求完成后再等1秒；可选择2/5秒。没有 setInterval 并发请求，10秒超时；切源/卸载取消请求，异步迟到结果被拒绝。连续3次失败后暂停自动重试并保留明确错误，用户可重新加载。

跨 scene/capabilities/snapshot 比较 adapter、robot、run/generation/episode、contract/model/hash/scene、interface profile。运行或资源身份变化立即作废旧 Target/Preview 并重载；初始化身份不一致不挂载混合场景。断连保留最后 Actual 并明确标陈旧；资产错误标不可用，可重新加载来源，不以冻结数据或旧网格补成功。

同源静态预览代理只允许四组 GET 路径；其他 API 不代理，写方法不转发。响应状态、ETag、no-store 与完整查询参数保留。没有访问 native 控制路径。

## 本次冻结版本与实际验证

- 前端 release：`m1-front-read-20261023T180841Z-25c387722858`；61个输入；聚合 SHA256 `25c387722858c7414ec4f539a26e88b457042d8ae798691565b4cef7548392af`。
- 对接网关：`m1-read-20261023T155543Z-cef9ddedf781`，wire `unirobot-mobilecar-read-1`；当前 native interface `g4a1-1.0`。
- native release：`drvfix-20261019T044549Z-0a80415b2577`。运行 `run_9c88e3e36e7648a3852c9f590e43ed5f` / generation 1 / `episode_43c22f95536f4517be04e4b195d6d354`；模型/场景身份见 [只读浏览器报告](../reports/m1-front-read-20261023T180841Z-25c387722858/browser/browser.json)。这不是更新 native pin 或完整部署内容核验。

| 实际执行，全部在服务器 cec-sim | 结果与证据 |
|---|---|
| 上传逐文件哈希、TypeScript 与生产构建 | 通过；[输入清单](../reports/m1-front-read-20261023T180841Z-25c387722858/source-manifest.json)、[构建日志](../reports/m1-front-read-20261023T180841Z-25c387722858/build.log)。保留 bundle 大于500KB的 Vite 提示，本轮未为此扩大拆包 |
| 单元检查 | 13 passed / 0 failed；含 Actual/Target 分离、关节零位、身份隔离、URI摘要边界与原FK/IK；[结果](../reports/m1-front-read-20261023T180841Z-25c387722858/unit.json) |
| 真实代理与只读浏览器 | 30 checks passed；三接口200，23/23资产字节摘要匹配，错误sha查询保留409；持续更新不重建renderer、不覆盖相机/选择/布局/目标；[结果](../reports/m1-front-read-20261023T180841Z-25c387722858/browser/browser.json) |
| 原 M1.2a 交互回归 | 29 checks passed；Joint/TCP拖拽、Actual隔离、输入焦点、失焦、单位、拾取、布局重建/恢复、取消与切源；[结果](../reports/m1-front-read-20261023T180841Z-25c387722858/frozen-browser/browser.json) |
| 故障夹具 | 1.5秒慢响应无重叠；503断连、运行/资源跳变、组间身份不一致、切源迟到、坏字节与502摘要错误均通过；全部合成响应，未 RESET/修改 native 制造故障 |
| 取景与持续拖拽补查 | 同一生产构建上6项通过；自动取景稳定后所有robot link中心在视口内；TCP手柄持续拖拽跨越两次Actual刷新，目标/相机/拖拽状态稳定；[补充输入脚本与结果](../reports/m1-front-read-20261023T180841Z-25c387722858/final-preview-check.json)。脚本作为独立验证输入以自身SHA记录，未修改61个构建输入 |
| 网络与原生影响 | 代理记录254次API读取均GET且在白名单；26个真实snapshot代理耗时中位31.905ms，22.25–233.21ms；[摘要](../reports/m1-front-read-20261023T180841Z-25c387722858/integration-summary.json)、[网络记录](../reports/m1-front-read-20261023T180841Z-25c387722858/proxy-network.json)。无运动/RESET/录制请求，无新增物理实例；[前后状态](../reports/m1-front-read-20261023T180841Z-25c387722858/native-read-only.json)、[补查后PID/状态](../reports/m1-front-read-20261023T180841Z-25c387722858/final-preview-check.json) |
| 环境与回传 | Node20.20.2/npm10.8.2、原锁文件、Chromium ANGLE SwiftShader；不外推真人操作手感或GPU性能。[环境](../reports/m1-front-read-20261023T180841Z-25c387722858/environment.json)、[产物索引](../reports/m1-front-read-20261023T180841Z-25c387722858/server-artifact-index.json)。约1.23MB精简包回传并核对22个文件，原始大数据/资产未回拉 |

较早候选不拼接为本次通过：首轮仅遇到测试JSON的TS tuple断言错误；第二轮浏览器24项后暴露测试在React切源完成前读取旧inspect hook，已修正等待。最终上述主检查均在同一冻结版本完整通过。末张快速截图曾早于自动fit timer结束，另以独立补查确认稳定取景与持续拖拽，并保存稳定后的预览；没有为截图改 Actual/场景或冒充真实控制。

## 预览与保留服务

- 联调预览：服务器 loopback18932，PID293264；当前SSH隧道提供 [http://127.0.0.1:18932/](http://127.0.0.1:18932/)。源目录与启动时间见 [preview.json](../reports/m1-front-read-20261023T180841Z-25c387722858/preview.json)。仅任务预览，随服务器进程/隧道存活。
- 旧样板18931/PID2614787、网关18941/PID1155600、native8792/PID941842 均保留，前后PID一致；只替换过本方明确验证身份的18932失败候选。未重启/停止其他任务服务。
- 后续最小差距仍为运行绑定/Start、控制权与命令回执、录制/可靠收尾、媒体与只读Episode reader，以及版本化运动学元数据。本轮不继续进入这些功能。

![服务器生产构建：真实只读Actual，编译初态世界对象，未授权](../reports/m1-front-read-20261023T180841Z-25c387722858/browser/settled-real-readonly.png)

---

# M1.2a 前端开发记录

日期：2026-10-23（America/Los_Angeles）。当前用户明确授权恢复前端，从 V0.7 M1.2a 开始；不修改 backend、native 或公共契约。此页是验证后的开发记录，刻意不纳入自身 release 哈希，避免报告自引用；运行源码与测试仍全部纳入 allowlist。

## 基线与文件所有权

- 原工作目录：`/home/liaozhengyan/Desktop/uniRobotPlatform`，main HEAD `1b17d6c1f7cccb171d5db8720a0e6f8ffd960623` 的现有未提交/未跟踪成果原地保留，未 reset/clean，也未改变原 index。
- 使用临时 Git index 固定包含最新 V0.7 文档、既有 M1.1/M1.2 代码/证据的共同基线 `2f7ff9b091c060034e55d2f387dbb6e130aaada3`（本地 `codex/m12a-common-baseline-20261023`），不是从旧 HEAD 直接开始。
- 独立 managed worktree：`/home/liaozhengyan/.codex/worktrees/frontend-m12a/uniRobotPlatform`；分支 `codex/m12a-workbench`。后端和公共契约在此相对共同基线没有修改，原主目录的并行修改不被覆盖。
- 本切片仅写 `frontend/`，包括独立 package.json/package-lock、工具、源资产与开发报告。没有改根配置或部署配置，没有推送。

## 实现与数据来源

详见 README 与 provenance。冻结真实几何/运行采样用于观察，Target/Ghost/FK/位置 IK 是前端本地预览。没有真实 Session、执行授权、指令提交、录制或连续 Episode 回放。

三路只读任务已回收：SceneView/资产/坐标与生命周期、交互条款、前后端数据缺口。原交互代理一次执行失败，由新只读代理接管完成；没有把失败任务算作完成。追加静态复核发现的场景替换 marker/失败记录清理与数据源 targetRef 清理已由主智能体处理。子代理没有修改文件或运行验证。

## 同一冻结版本的最终验证

最终 release：`m12a-20261023T162150Z-bf82d5697880`；56个输入文件逐项核对，aggregate SHA-256：`bf82d5697880125086002666d74046a2a103a96f868b9abee54bf2bf8b534102`。当前运行源码/测试/锁文件与该清单一致。本页与 reports 是验证后记录，排除在自引用哈希之外。

| 实际执行（全部在服务器） | 结果与边界 |
|---|---|
| 类型检查与生产构建 | `npm run build`（含 `tsc --noEmit`）通过；Node20.20.2，依赖锁摘要见 environment.json |
| 目标/FK/位置 IK 聚焦测试 | 6 passed：真实关节链 FK 与冻结 TCP 相符、单关节目标保留、joint4 零位、限位/非有限输入、本地位置候选、不可达反馈 |
| 生产构建的 Chromium 检查 | 29 checks passed；对象树/mesh/Inspector、Joint 环真实指针拖动、TCP 轴真实指针拖动与相机隔离、Actual 不变、文本焦点/取消、失焦事件、resize、布局重建/恢复、显式切源、零 native 命令请求 |
| 来源/执行隔离 | 冻结样本不授予 Session；Start/执行/接管/录制禁用；浏览器101项请求均 GET，没有 native 命令/runtime 请求 |
| 原生影响 | 验证前后 run/generation/Episode/recording 身份相同。没有新建物理实例或停止既有服务；只结束了本任务旧版静态预览进程 |
| 源码/证据回传 | 当前源码清单、12个精简证据文件哈希核对通过；回传包约0.7MB，原始数据与环境留在服务器 |

证据：[索引](../reports/m12a-20261023T162150Z-bf82d5697880/server-artifact-index.json)、[源码清单](../reports/m12a-20261023T162150Z-bf82d5697880/source-manifest.json)、[构建](../reports/m12a-20261023T162150Z-bf82d5697880/build.log)、[6项测试](../reports/m12a-20261023T162150Z-bf82d5697880/unit.json)、[29项浏览器检查](../reports/m12a-20261023T162150Z-bf82d5697880/browser/browser.json)、[原生前后](../reports/m12a-20261023T162150Z-bf82d5697880/native-read-only.json)、[环境](../reports/m12a-20261023T162150Z-bf82d5697880/environment.json)。

这些是 M1.2a 离线工作台交互与工程验证，对应既有交互 TEST 的适用子集；不将 TEST-MOBILE-001/002、真实权限/命令/采集/回放或完整交互条款标为已通过。

## 可操作预览与限制

- 最终静态预览：服务器回环端口18931，当前 SSH tunnel 转发为 `http://127.0.0.1:18931`。进程 PID/目录见 [preview.json](../reports/m12a-20261023T162150Z-bf82d5697880/preview.json)。预览随本任务服务器进程与隧道存活；没有对外发布。Codex 面板已请求打开该地址。
- 真实网格与运行单帧为冻结来源，位置 Target / Ghost 为本地计算；本样本含原生 GT_DEBUG 工程观察数据，不作为受限采集的 OperatorView/Policy 输入。后续真实接入的载荷权限应由服务端按 Profile 裁决。
- RGB/Depth 无媒体，时间轴没有连续 Episode；实时状态、真实授权/执行、录制和历史同步流尚待接通。本地 IK 只满足位置约束，没有姿态/碰撞/动力学/规划认证。
- 浏览器实际 GL renderer 为 ANGLE/SwiftShader 软件渲染，验证了1600×1000及1280×900桌面布局；没有宣称客户端GPU帧率或远程实时链路延迟达标。默认关闭实时阴影避免软件渲染负载和阴影伪影；真实几何/状态未更改。
- 生产 JS 约1.2MB（gzip约312KB），构建有大 chunk 提示；本切片没有为消除提示额外拆架构。手机布局未验收。
- 中间迭代保留在服务器，不拼接结果：首轮 TCP 测试坐标未命中手柄；新增 Joint 检查时修正了对 Three.js 旋转手柄几何类型的测试投影；新增失焦拖动后修正测试误用旧 revision 的断言。最终29项均在上述同一冻结版本重跑通过。

![服务器生产构建下的 TCP 本地目标预览，非真实执行](../reports/m12a-20261023T162150Z-bf82d5697880/browser/workbench-tcp-target.png)

## 后端接续

[最小数据/服务缺口与具体样例](backend-gaps.md)。平台只读 scene/Actual 可先接入，不等待控制/录制全部齐备；端点映射仍集中在 adapters，wire 契约由后端对话维护。M1.2b～M1.6 不因本前端样板而完成。
