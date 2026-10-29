# M1.5f｜历史完整静态模型树切片（解除前端 #34 的外部依赖，2026-10-29）

本轮只做一件事：让前端在**不读取 `/api/v1/mobilecar/scene`、snapshot 或 Actual** 的前提下，从历史只读面拿到完整静态装配树。基线 `ab9e35d`（M1.5e），分支 `codex/backend-m1-services`。

## 前端使用基址

唯一基址：`http://127.0.0.1:18977`（候选 `m1z-20261029T075630Z-platform`，PID 272431，独立 SQLite `frames-20261029T075630Z.sqlite3`）。18970（M1.5e）与其他既有服务保留未替换；用前以 `ss -ltnp sport = :18977` 与 `GET /api/v1/episodes?limit=1` 确认存活（`/health` 在本服务未注册，返回 404 不代表不可用）。

```text
GET /api/v1/episodes/{episode_id}/robot-state?run_id={run_id}                       # 默认：不含树（与上一轮完全兼容）
GET /api/v1/episodes/{episode_id}/robot-state?run_id={run_id}&include_model_tree=true  # 新增：整棵冻结树
GET /api/v1/episodes/{episode_id}/model/assets/{asset_id}?run_id={run_id}&sha256={sha}  # 网格字节（未变）
```

历史只读面仍是**八条 GET**：本轮没有新增路由，只在既有路由上加一个可选布尔查询参数（`include_model_tree`，默认 `false`）。非布尔取值 422 `bool_parsing`（见 `error-invalid-tree-flag.json`）。

## 1. 精确请求与实测响应

- 请求：`GET http://127.0.0.1:18977/api/v1/episodes/episode_27bfed5427684795b361cd2ec21e9aa7/robot-state?run_id=run_0104613ff7364ae78cf2f3946bd45f7b&include_model_tree=true`
- 响应 `schema_version` 仍为 `unirobot-mobilecar-history-pose-1`（**未升版**：纯新增键，向后兼容）。
- 体积（同一 compact 序列化重算）：默认响应 50,340 B，带树响应 114,988 B；服务端实测带树 `content-length: 107,835`、`cache-control: no-store`，且**两个响应都不带 `ETag`**。
- 树内容（真实冻结 bundle）：`links 71`、`world_links 2`、`geoms 100`、`mesh_geoms 22`；`model_resource.assets` 23 个资产中 22 个被树引用，`imu_link` 无树内引用（如实报告，不隐藏）。
- 世界链名：`world_static`、`target_cube`。

## 2. `model_resource.model_tree` 完整字段

`include_model_tree=true` 且该 Episode 的模型身份与 bundle 相符时返回：

| 键 | 内容 |
|---|---|
| `requested` / `included` | 请求位与是否给出；不符时 `included=false` 且无 `links`/`world_links` |
| `authority` | `frozen_compiled_geometry_bundle`（与资产响应头 `X-UniRobot-Model-Source` 同词） |
| `live_native_scene_proxied` | `false` |
| `links[]` / `world_links[]` | 逐 link 完整装配数据，**复用 geometry-2 的 `Link`/`Geom` 序列化**：`name / parent_name / joint_name / joint_type / joint_axis / local_transform{position_m, orientation_xyzw} / geoms[]`，每个 geom 带 `name / geom_type / size_m / local_transform / rgba / mesh_asset_id / collision / group / contype / conaffinity` |
| `counts` | `links / world_links / geoms / mesh_geoms` |
| `content_identity` | **沿用** `bundle_sha256 275389464eee…`、`content_identity_sha256 cb7899642604…`、`compiled_scene_sha256 a7b8b2c2d12d…`、`model_inputs_sha256 9e1b60c04b8d…`，并声明与 `model_resource` 同名字段是同一值；未另造摘要体系 |
| `caching` | 取树规则、`identical_for_every_frame_of_this_bundle=true`、`response_is_dynamic=true`、`model_content_etag_applies_to="GET …/model/assets/{asset_id} only"`、`etag_note` |
| `semantics` | `links` 为编译参考布局；`world_links = compiled_initial_layout_not_live_object_state`；`world_links_are_not_recorded_object_positions=true` + `world_links_note`；`is_recorded_state=false`；`recorded_pose_lives_in` |
| `mesh_bytes` | `geoms[].mesh_asset_id` 对 `model_resource.assets[]` 解析；字节只走 Episode 资产路由 |
| `summary_views_still_on_model_resource` | `true`：`root_joint`/`tcp_parent_body_view`/`end_effector_link`/`camera_link_chain` 保持原样，未被摘要替换 |

字段级完整样例见 [证据册](evidence/m1.5f-history-model-tree/README.md) 的 `model-tree-excerpt.json`（`link3` 的 hinge 轴与 capsule/mesh 双 geom、`base_link`、两条 world link 原文）与 `robot-state-with-tree.json`（整条响应）。

## 3. 冻结身份

- release `m1z-20261029T075630Z-platform`；源码聚合 `5cb9a562a1190c11d4526125d26b8218c62e41668af369336f6a48f0913fe869`（49 文件，`src/unirobot + config + tools`）
- 启动清单 `history-startup.json` sha256 `5503bb07f703fe6a095abfd0d0db712644bd3bde7aa6014487fb524b4d56b4f3`；检查工具重算与清单 **MATCH**
- geometry bundle：`releases/m1-geometry-20261023T192202Z-cdfc7472e5de/geometry`（`bundle.json` 文件摘要 `a5f4a90ca5988ba0…`，23 个 mesh 资产逐文件校验）
- 本轮还核对了**冻结 release ↔ 本地工作树**同一聚合（49 文件全等），核对时刻 2026-10-29T07:57Z 前后；本文档与证据 README 在该核对之后写入，属预期滞后，不代表运行字节变化

## 4. 验证结果

- 真实归档只读检查 **118/118**（M1.5e 110 → 本轮 +8）：默认响应不含树且其余键值原样不变；带树答案与**直接加载的冻结 bundle** 逐 link `model_dump` 全等；每个 link/geom 字段集合完整（不含 `_link_view` 的 `local_position_m` 摘要形状）；网格引用落在资产清单内；四个摘要与 `model_resource` 同值且等于 bundle provenance；换一帧（`rgbd_e553d6b6…`，状态负载不同）树**逐字节相同**；动态响应无 `ETag`；请求树只发出 2 条平台 GET，`live_scene_reads_in_this_run=0`
- 统一能力回归 **28/28**；冻结 release 内聚焦 **55 passed**（`test_frames` + `test_history_fk` + `test_episodes`）；dev 树全量 **183 passed / 3 failed**（M1.5e 的 179+4，三项历史布局失败名称与基线不变：`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`）
- 隔离夹具（`tmp_path`，不触碰真实归档）：默认兼容、完整树等于加载后的 bundle、身份不符时拒给树且 `links_are_substituted=false`、**把进程内唯一 native 连接指向不可达地址**（`http://127.0.0.1:1`）时 `/api/v1/mobilecar/scene` 返回 503 `native_offline` 而历史树照常完整
- 执行纪律：全部测试/构建/离线检查在授权服务器；本轮经 `GetProbe` 发出 **66 条请求全为 GET**（`non_get` 无），946 文件覆盖集合事前记录、事后复核 **`drift=[]`**；未启动新 native、未运动、未 RESET、未录制、未 STOP/end、未重启 8792；历史归档/tail/native/生产 recipe 与 pin 未改动；`frontend/` 未修改

## 5. 过程中的替代候选

同轮先冻结并验证过 `m1y-20261029T075301Z-platform`（18976，118/118 + 28/28 全绿），交付前发现 `world_links` 需要显式声明"编译初态≠记录位姿"（bundle 里确有名为 `target_cube` 的世界链），补该语义后重新冻结为 `m1z-…`；`m1y` 的 release 与报告目录保留为历史、未回填，其进程由本轮自己启动并已按身份核对后停止（未清理任何非本轮注册的进程）。

## 6. 边界（本轮不主张）

- 树是**静态参考布局**，不是历史物体位姿：`target_cube` 等世界链不得据树摆成"记录中的位置"，`mapping.dynamic_scene_objects` 仍为 `missing`。
- 姿态、夹爪、相机、TCP 朝向、跨流同步、统一历史游标的状态与 M1.5e 一致，本轮未推进；不扩展夹爪换算、相机外参或时间轴。
- 前端取树规则：按 `content_identity_sha256` 首次或内容变化时取一次，后续逐帧姿态请求**省略该参数**；不要把 `…/model/assets/{asset_id}` 的 `"sha256:…"` 内容 ETag 用到整个 `robot-state` 响应上。
- 本轮不是历史整车渲染通过、不是前端装配验证通过、不是同步回放通过、不是 M1.5/M1 验收通过。
