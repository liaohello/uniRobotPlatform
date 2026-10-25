# M1.5a 证据册｜真实历史 Episode/segment 只读 reader 首个切片

目录：`m1k-20261025T040435Z-platform/`（服务器 release `releases/m1k-20261025T040435Z-platform`，由 `m1j-…-platform` 叠加本轮 reader/工具/测试而成，独立 release，未替换任何既有实例）。全部读取验证在服务器执行；本地未运行测试或构建。8792 全程仅 GET，原始 Episode 未被修改。

## 一、冻结标识

| 项目 | 值 |
|---|---|
| 平台 release | `m1k-20261025T040435Z-platform`，历史候选监听 `127.0.0.1:18960`（独立会话常驻；18959/18949/18953/8792 未替换） |
| 平台源码聚合摘要 | `e86a709fb6e59f44…`，42 个文件，`SOURCE_ROOTS = src/unirobot + config + tools`（启动器与检查工具首次被纳入） |
| 历史来源声明 | `backend/config/mobilecar-history-source.json`，sha256 `fbfcc6a69edb9472…`，`source_id=mobilecar-server-history-20261017`，root `/home/liaozhengyan/Desktop/mobileCar/var/runs` |
| 归档聚合基线 | 696 个 `episode.json` + `episode_complete.json` 的折叠摘要 `60c0c6963bc9ae8442bc3d9c9e5f0c33c19973cee966994365313b57ae9d6664`（读取前后一致） |
| 数据库命名空间 | 独立 `report/history-<ts>.sqlite3`，`existed_before=false`；历史读取本身不使用 SQLite，未读取或覆盖任何更早候选的库 |
| 生产 recipe / pin | `mobilecar.g1.teleop` rev 3（fingerprint 不变）与生产 pin `a0109804…911c` 未修改、未激活 |

## 二、文件

| 文件 | 内容 |
|---|---|
| `history-startup.json` | 冻结启动清单：端口/native 地址/geometry bundle/Map catalog/recipe/独立 DB + 新增 `history` 块（来源文件摘要、`configured=true`、解析后的 recording root、`root_override=null`、声明规模、访问策略） |
| `history-check.json` | 61/61 断言（第三节），含每条断言的 `name/passed/detail`，并记录所选真实 COMPLETE 与 FAILED 记录身份 |
| `unified-on-history-candidate.json` | 同一候选上的 M1.4b 统一能力回归 27/27（geometry-2、Map/Route、Session/`current`、STOP/end 契约仍在同一 OpenAPI） |
| `history-before-digests.json` | 逐文件 `episode.json`/`episode_complete.json` 摘要表（696 条），实现落地前采集，用于证明读取路径未写盘 |

## 三、必须分开读的三层结论

1. **真实历史记录的读取事实**（生产来源、native 仅 GET）
   - 索引 348 条与 native `GET /api/v1/episodes` 完全一致；272 个 run id、磁盘 295 个 run 目录、跨 run 重复 episode_id 0、多段 Episode 0。
   - 声明状态：342 COMPLETE / 6 FAILED，audit 342 COMPLETE / 6 INCOMPLETE，`complete_tail` 全为 true——注意这是目录声明，不是本平台验证结论。
   - COMPLETE 记录 `run_0104613f…/episode_27bfed54…`：events 12561 条 / 12,472,413 字节、control 12188、commands 60、observations-index 与 persist、transforms、initial_snapshot 均可读；rgb/depth/masks 各 303 个资产，样例 PNG 摘要与 tail 声明一致；平台轻量详情 21,031 字节对 native 整条详情 20,946,833 字节。
   - FAILED 记录 `run_1f6fb348…/episode_879cf704…`：`RECORDING_FAILED` + `audit_status=INCOMPLETE` + tail 存在 → `incomplete_terminal_recorded`，事件仍可读、缺流为空并如实报告。
2. **完整性与身份的关键发现**
   - tail 声明的校验和对本 Episode 的 `episode.json` **过期不符**（先写 tail、后定稿 `episode.json`）。抽样 16 条真实记录 16/16 同样 `mismatch_present`，而生命周期状态仍为 `complete`：分层表达，不改写、不称"全 Episode 已验证"。
   - `backend_generation` 仅存在于记录的命令 payload（该记录 distinct_values=[1]），平台如实标注采样范围，不伪装成每条记录的顶层字段。
   - legacy 记录无平台 sidecar → `platform_association.known=false`，不伪造 ValidatedSnapshot/Session 关联。
   - 所选记录的 `model_sha256 3ca3d6d0a92a…` 与 scene 均等于生产 pin 期望值 → `identity_verified_rendering_unverified`；不匹配/不可证时才是 `restricted`。任何情况下 `live_geometry_or_actual_may_be_applied=false`。
3. **未执行**：同步 3D 回放渲染与跨流时间对齐、真机 STOP/停车确认、新采集闭环、补丁部署、物理运动/录制/训练、M1.5/M1 正式验收。

## 四、故障覆盖（隔离夹具/副本）

`backend/tests/test_episodes.py`（服务器 12 passed）在 `tmp_path` 的副本归档上覆盖：缺 `episode_complete.json` → `finalize_failed_missing_tail`；坏 JSON 行 → `integrity.corrupt_lines` 定位行号；缺流 → 404 `episode_stream_unavailable`；不支持流名 → 404 `episode_stream_unsupported`；跨 run 同名 → 409 `episode_id_ambiguous`；`..`/绝对路径/软链越界 → 400/409；缺失媒体 → 404；未知后缀 → 415；`sha256` 不符 → 409；未知 `time_base` → 400；`sidecar` 缺失 → 关联未知；过期声明摘要 → `mismatch_present` 且状态不改写；OpenAPI 只有 5 条 GET。**原始 Episode 未被修改，也未为制造案例启动任何录制。**

## 五、复现方式（服务器）

```bash
# 1) 端口空闲检查：18960（18959/18949/18953/8792 不参与）
ss -ltnH sport = :18960            # 必须为空
# 2) 以固定来源启动历史候选（见交付记录第十节命令）
# 3) 61 项历史断言 + 27 项既有能力回归
PYTHONPATH=$REL/backend/src $PY tools/episode_history_check.py ... --out $REPORT/history-check.json
PYTHONPATH=$REL/backend/src $PY tools/unified_candidate_check.py --platform-url http://127.0.0.1:18960 ...
# 4) 单测（隔离夹具，不触碰真实归档）
PYTHONPATH=src $PY -m pytest tests/test_episodes.py -q
```

平台全量：140 passed / 3 failed（同一历史三项：`test_catalog_loads_real_tasks`、`test_every_task_has_existing_evidence`、`test_migrate::test_manifest_sources_exist`；链条 128/3 → 140/3，未新增失败）。`*.log` 若被仓库 `.gitignore` 排除，保留在服务器 `~/Desktop/uniRobotPlatform/var/reports/m1k-20261025T040435Z-platform/`。
