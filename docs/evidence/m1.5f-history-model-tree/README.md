# M1.5f 证据册｜历史完整静态模型树（候选 `m1z-20261029T075630Z-platform`）

权威语义与实现边界在后端 `docs/backend-m1.5f-history-model-tree.md`；本册只登记本轮实测得到的字节、请求与断言结果。真实归档、源码核对与隔离夹具三类证据分列，互不冒充。

## 冻结身份

| 项 | 值 |
|---|---|
| 实际运行地址 | `http://127.0.0.1:18977`（`GET /api/v1/episodes?limit=1` 实测 200） |
| release / PID | `m1z-20261029T075630Z-platform` / PID 272431（`launch-registry.json`，进程启动时间 2026-10-29 15:56:30 本地） |
| 独立 SQLite | `var/reports/m1z-20261029T075630Z-platform/frames-20261029T075630Z.sqlite3`（启动前不存在，未复用任何既有库） |
| 源码聚合 | `5cb9a562a1190c11d4526125d26b8218c62e41668af369336f6a48f0913fe869`，49 文件（`src/unirobot + config + tools`） |
| 启动清单 | `history-startup.json` sha256 `5503bb07f703fe6a095abfd0d0db712644bd3bde7aa6014487fb524b4d56b4f3`；检查工具重算 ↔ 清单 **MATCH** |
| 冻结 bundle | `releases/m1-geometry-20261023T192202Z-cdfc7472e5de/geometry`（`bundle.json` 文件摘要 `a5f4a90ca5988ba0…`） |
| 工作树核对 | 冻结 release 与本地工作树聚合全等（49 文件），核对时刻约 2026-10-29T07:57Z；本 README 与该核对之后写入，属声明过的滞后 |

## 实测结果

| 项 | 结果 |
|---|---|
| 历史只读断言 | **118/118**（上一轮 110，本轮 +8） |
| 统一能力回归 | **28/28**（同一冻结进程） |
| 聚焦测试（冻结 release 内） | **55 passed**（`test_frames.py` + `test_history_fk.py` + `test_episodes.py`） |
| 全量（同一 dev 树） | **183 passed / 3 failed**，三项历史布局失败名称与基线不变 |
| native 请求 | 本轮经 `GetProbe` 发出 **66 条，methods 仅 `GET`**；无 validate/assessment |
| 归档不变性 | 事前记录、事后复核的 **946 文件集合 `drift=[]`**（其余文件该时点无前置摘要，属未覆盖） |
| 树响应 | `links 71 / world_links 2 / geoms 100 / mesh_geoms 22`；`content-length 107,835`、`cache-control: no-store`、**无 `ETag`** |
| 体积对比 | compact JSON 重算：默认响应 50,340 B，带树 114,988 B |
| 资产引用 | 23 个发布资产中 22 个被树引用；`imu_link` 在树中无引用（如实列出） |
| 静态性 | 同一 Episode 换帧（`rgbd_e3213e6c…` → `rgbd_e553d6b6…`，状态负载不同）树逐字节相同 |
| 拒绝形状 | `include_model_tree=notabool` → 422 `bool_parsing` |

## 本轮八条新断言（`history-check.json` 原名）

- the default response carries no tree and the requested one adds it without changing anything else
- the opt-in answer is the whole frozen tree, equal link for link to the loaded bundle
- every link carries the assembly fields the three named summary views do not
- the tree's mesh references resolve inside the same frozen asset list the viewer already uses
- the tree reuses the four published digests instead of a second identity scheme
- the static tree is the same answer for another frame, so it needs no per-frame re-read
- the tree is labelled reference layout, and the dynamic response carries no content ETag
- asking for the tree issues no live native scene read, only the platform GET

## 文件清单

- `history-check.json`（118 项断言与逐项 detail）、`unified-on-history-candidate.json`（28 项）
- `history-startup.json`、`launch-registry.json`、`coverage-digests.json`（946 文件前后摘要）
- `get-probe-log.jsonl` / `get-probe-log.json`（逐条 URL、方法、状态、字节与汇总）
- `robot-state-sample.json`（默认响应，无 `model_tree`）、`robot-state-with-tree.json`（完整带树响应）
- `model-tree-summary.json`（树块去掉 `links`/`world_links` 后的全部元数据）、`model-tree-excerpt.json`（`link3`、`base_link` 与两条 world link 原文 + 块头）
- `tree-response-headers.json`（头、体积、ETag 判定）、`openapi.json`、`openapi-tree-parameter.json`（`include_model_tree` 参数与八条 Episode 路由）
- `error-invalid-tree-flag.json`（422 拒绝体）

## 夹具证据（不进真实归档）

`backend/tests/test_frames.py` 的四条新用例在 `tmp_path` 内构造冻结 bundle 副本：默认兼容、整树等于加载后的 bundle、身份不符时拒给树（`links_are_substituted=false`）、以及把进程唯一 native 连接指向 `http://127.0.0.1:1` 时 `/api/v1/mobilecar/scene` 503 `native_offline` 而历史树仍完整。**没有**通过断开真实 8792 来证明这一点。

## 过程记录

`m1y-20261029T075301Z-platform`（18976）同轮 118/118 + 28/28 全绿，交付前补 `semantics.world_links_are_not_recorded_object_positions` 后重冻结为 `m1z-…`；`m1y` 的 release 与报告目录保留为历史、未回填，其进程由本轮注册且身份全等核对后停止。

## 不主张

历史整车渲染、前端装配验证、局部姿态推进、跨流同步、统一历史游标与正式 M1.5/M1 验收。
