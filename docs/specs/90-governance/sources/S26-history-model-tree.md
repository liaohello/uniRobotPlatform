# S26｜历史完整静态模型树实测（2026-10-29）

## 来源类型

平台后端只读切片的事实来源（M1.5f）。分三类并列：**真实归档实测证据**（服务器只读文件 + 平台 GET）、**结构核对证据**（同一进程直接加载的冻结 bundle）、**隔离夹具证据**（`tmp_path` 构造，不触碰真实归档）。绑定候选 `m1z-20261029T075630Z-platform`（`http://127.0.0.1:18977`，源码聚合 `5cb9a562a1190c11…`／49 文件，启动清单 sha256 `5503bb07f703fe6a…`）。用户 Goal：优先解除前端 #34 的外部依赖，只做完整历史静态树读取的小切片，不扩展夹爪、相机或统一时间轴。

## 观察到的事实

### 契约形状（真实归档 + OpenAPI）

1. `GET /api/v1/episodes/{episode_id}/robot-state` 新增可选布尔查询参数 `include_model_tree`，OpenAPI 中 `required=false`、`schema.type=boolean`、`default=false`；Episode 路由集合仍是**八条**，本轮没有新增路由。非布尔取值实测 422 `bool_parsing`（`loc=["query","include_model_tree"]`）。
2. `schema_version` 仍为 `unirobot-mobilecar-history-pose-1`：新增 `model_resource.model_tree` 属纯增键。带树响应的 `model_resource` 键集合只多出 `model_tree` 一个键，其余 28 个键的值与同一帧默认响应完全相等；`frame`/`mapping`/`part_readiness` 两个响应逐字相同（`retrieved_at` 除外）。
3. 真实代表记录 `run_0104613ff7364ae78cf2f3946bd45f7b / episode_27bfed5427684795b361cd2ec21e9aa7` 首帧 `rgbd_e3213e6cb64b4cd693c17d485d064d09` 的树：`counts = {links: 71, world_links: 2, geoms: 100, mesh_geoms: 22}`；前三个 link 名 `base_link / front_left_wheel / front_left_roller_0`；两条 world link 名 `world_static / target_cube`。
4. 逐 link 字段集合恰为 `name / parent_name / joint_name / joint_type / joint_axis / local_transform / geoms`，逐 geom 恰为 `name / geom_type / size_m / local_transform / rgba / mesh_asset_id / collision / group / contype / conaffinity`；响应里**不含** `_link_view` 摘要形状（`local_position_m`/`local_orientation_xyzw` 不作为树内 link 键出现），且 `root_joint / tcp_parent_body_view / end_effector_link / camera_link_chain` 四个既有摘要视图仍在 `model_resource` 原位保留。
5. 实测 `link3`：`joint_axis = [0.008593917497923844, -0.9999233363864473, 0.008914366597513988]`、`local_transform.position_m = [-0.000861228256677, 0.000635863697295, 0.074117298162]`，两条 geom 分别是 `link3_collision`（capsule，`size_m=[0.008, 0.03300000121818, 0.0]`，`rgba=[0,0,0,0]`，`mesh_asset_id=null`，`contype=4/conaffinity=31/group=3`）与 `link3_visual`（mesh，`size_m=[1,1,1]`，`mesh_asset_id="link3"`）。这证明几何/颜色/碰撞过滤与网格身份都随树到达，摘要视图做不到。

### 一致性与身份（结构核对）

6. 响应 `model_tree.links` 与 `model_tree.world_links` **等于**同一进程用 `GeometryBundle(<冻结目录>)` 加载后 `scene.links/scene.world_links` 的 `model_dump(mode="json")` 逐元素结果；bundle 加载本身逐文件校验 23 个资产摘要并重算 `bundle.json` 内容摘要，因此该相等是对"已通过完整性校验的冻结字节"成立，不是对任意磁盘内容成立。
7. `content_identity` 四值与 `model_resource` 同名字段一致，且等于 bundle provenance：`bundle_sha256 275389464eee2f3d…`、`content_identity_sha256 cb78996426040381…`、`compiled_scene_sha256 a7b8b2c2d12d8713…`、`model_inputs_sha256 9e1b60c04b8d8e2e…`。本轮未引入第二套摘要体系。
8. 树内 `mesh_asset_id` 引用集合是 `model_resource.assets` 资产 id 集合的子集：22 被引用、23 发布，`imu_link` 在树中无引用（如实报告）。
9. 树是静态的：同 Episode 另一帧 `rgbd_e553d6b613cd4c9399567fd0d98f953f` 的 `model_tree` 与首帧逐字节相同，而 `state.recorded_payload` 不同 → 前端只需按 `content_identity_sha256` 取一次，不必逐帧携带。
10. 带树响应 `content-length: 107835`、`cache-control: no-store`、**无 `ETag`**；默认响应同样无 `ETag`。网格内容 ETag（`"sha256:…"`）只出现在 `…/model/assets/{asset_id}` 响应上。
11. 取树两次请求在 `GetProbe` 日志里只有两条平台 GET，本轮 `live_scene_reads_in_this_run = 0`：树不读 `/mobilecar/scene`，也不读 snapshot/Actual。

### 拒绝与隔离（夹具证据）

12. 模型身份不符（bundle `model_sha256` 与 run 清单声明不同）时：HTTP 仍 200、`model_resource.status="mismatch"`、`model_tree.requested=true`、`included=false`、`links_are_substituted=false`，且 `links`/`world_links` 键**不存在**——不返回任何替代树。
13. 把进程唯一 native 连接指向不可达地址（`http://127.0.0.1:1`）的隔离夹具中：`GET /api/v1/mobilecar/scene` 返回 503 `native_offline`，而 `robot-state?include_model_tree=true` 返回完整且与加载 bundle 相等的树，`live_native_scene_proxied=false`。证明"历史树不依赖在线 native"用的是夹具，**没有**断开真实 8792。

### 语义边界

14. `semantics.world_links = "compiled_initial_layout_not_live_object_state"`、`world_links_are_not_recorded_object_positions=true`、`is_recorded_state=false`：bundle 里名为 `target_cube` 的世界链是编译时的初始摆放，不是该 Episode 中物体的记录位置；`mapping.dynamic_scene_objects` 仍为 `missing`，前端不得据树摆放动态物体。
15. 本轮经 `GetProbe` 发出 66 条请求全为 GET；946 文件覆盖集合事前记录、事后复核 `drift=[]`；历史读取断言 118/118（110→118，+8）、统一回归 28/28、冻结 release 内聚焦 55 passed、dev 树全量 183 passed / 3 项历史布局失败（`test_catalog.py::test_catalog_loads_real_tasks`、`test_catalog.py::test_every_task_has_existing_evidence`、`test_migrate.py::test_manifest_sources_exist`，基线不变）。未启动新 native、未运动、未 RESET、未录制、未 STOP/end、未重启 8792；归档、tail、生产 recipe 与 pin 未改；`frontend/` 未修改。
16. 过程记录：同轮 `m1y-20261029T075301Z-platform`（18976）已 118/118 + 28/28 全绿，交付前补入第 14 条的 `world_links` 非记录位姿声明后重新冻结为 `m1z-…`；`m1y` 的 release 与报告目录保留为历史、未回填，其进程为本轮注册且身份全等核对后停止。

## 对设计的影响

- 前端 #34 的"历史侧缺逐 link 位姿表"是**一条既有路由上的一个可选参数**可解的，不需要新 GET、不需要代理 live 路由，也不需要前端维护跨 Episode 的可变树缓存：内容键已随响应给出（`content_identity_sha256`）。
- 摘要视图与完整树应并存而非互相替换：摘要负责"命名关键 link/链"，树负责"逐 link 装配数据"，两者字段形状不同是有意区分（树里不得混入摘要形状）。
- 静态数据与动态响应共存于一条路由时，缓存键必须由响应内的内容摘要承担；ETag 属于字节资产路由，错用到动态响应会把姿态响应伪装成不可变内容。
- 编译初态与记录状态必须在同一响应里用词汇区分开，否则一个名字像任务物体的世界链会被误读成历史记录位姿。

## 效力

本来源为"逐 link 完整装配数据由历史只读面直接给出且与冻结 bundle 逐元素相等"、"默认响应保持兼容、树为显式 opt-in"、"身份不符只拒给、不替代"、"树为静态一次取、按内容摘要缓存、动态响应无内容 ETag"、"world 链是编译初态不是记录位姿"提供依据。实现与证据见 [M1.5f 交付记录](../../../backend-m1.5f-history-model-tree.md) 与 [M1.5f 证据册](../../../evidence/m1.5f-history-model-tree/README.md)。
