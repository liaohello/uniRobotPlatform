# M1.4b｜统一可联调候选与部署前发布身份

2026-10-25 · 范围：把已在 M1.2b～M1.4 分别验证的能力收敛到**一个冻结源码、一份启动配置、一份 OpenAPI**里对前端提供，同时补齐待部署 native 候选的**完整发布身份**与**维护流程顺序**。

**统一联调候选与部署准备已完成；生产未部署、真实停车/物理运动/录制/训练未执行、M1 闭环未通过。** 本轮不新建第二个物理实例，不停止/重启/替换 8792，不发任何真实 native 写请求，不修改 `frontend/`。

## 一、结论

| 项 | 状态 |
|---|---|
| 一个进程同时提供 geometry-2 场景与 23 资产、capabilities/snapshot/kinematics、Map/Route 资源、Draft/validate、Session envelope + `current`、STOP/end schema/回执/availability | 已验证：统一检查 27/27 通过 |
| 前端可直接消费的统一候选地址 | `http://127.0.0.1:18959` 常驻存活（服务器 pid 3608367），在该地址上重跑同一套 27 项断言 27/27（见第八b节与 `unified-candidate-check-live.json`） |
| 正向 STOP/end 生命周期（test-only recipe + mock backend + 真实 native HTTP + 真实 Recorder 文件） | 同一冻结源码上重跑 39/39 通过 |
| 待部署 native 候选的完整发布身份 | 已生成并可复算：154 个必需路径全部存在，release 摘要 `41b9c80c5d03eb11a2ff5551407430559514353d1d8bee324f4ad9111a5e038a` |
| 生产 recipe / 生产 pin 未被本轮改动或激活 | `mobilecar.g1.teleop` rev 3 仍只要求 `session_binding`+`recording_begin`；生产 pin 仍为 `a0109804…911c` |
| 生产部署、G1/G4A2 与 a5/drvfix 选择 | 仍待用户决定；本文推荐不等于授权 |

## 二、统一候选与启动配置（冻结）

服务器 release：`m1j-20261025T020857Z-platform`（由 `m1i-20261024T163746Z-platform` 叠加本轮工具/测试/配置而成，独立 release，未替换任何既有实例）。

| 冻结项 | 值 |
|---|---|
| 平台源码摘要 | `tools/launch_unified_gateway.py` 在启动时计算：`src/unirobot` + `backend/config` 共 30 个文件，聚合 `26c60b76acbac68a…`（写入 `unified-startup.json`） |
| 监听 | `127.0.0.1:18959`（启动前用 `ss` 确认空闲；本轮检查后按交付要求保留为常驻联调地址，18949/18953 等既有服务未替换） |
| native 地址 | `http://127.0.0.1:8792`，**仅 GET**（health/capabilities/snapshot）；本轮未向任何真实 native 发送写请求 |
| geometry bundle | 复用已核验导出 `releases/m1-geometry-20261023T192202Z-cdfc7472e5de/geometry`：23 个资产、`bundle.json` sha256 `a5f4a90ca5988ba0…`；未重新导出模型 |
| map catalog / 资源根 | `backend/config/maps.catalog.json` + `~/Desktop/mobileCar/var/maps`（9 个包，列表暴露 Room A/B `g3b_release_v1`，`live=false`、`assets_verified=true`、`manifest_sha256` 有值、compatibility 不含任何 eligible=true） |
| recipe | `backend/config/mobilecar-g1-recipe-v2.json`（生产 recipe，fingerprint 与 required_protocols 原样） |
| 数据库命名空间 | 每轮新生成 `releases/<R>/report/unified-<ts>.sqlite3`，启动清单记录 `existed_before=false`；不读不覆盖 18949/18953 使用的旧 SQLite，也不宣称旧资源已迁移 |

启动命令（服务器）：

```bash
PYTHONPATH=$PL/src UNIROBOT_REPO_ROOT=$REL python tools/launch_unified_gateway.py \
  --port 18959 --native-url http://127.0.0.1:8792 \
  --geometry-bundle $REL_GEOMETRY --map-catalog $PL/config/maps.catalog.json \
  --maps-root $MC/var/maps --draft-db $REL/report/unified-$TS.sqlite3 \
  --out-manifest $V/unified-startup.json
```

启动器是**全有或全无**的：端口被占用、bundle/asset/map catalog/recipe 任一缺失、或数据库已存在（未显式 `--allow-existing-db`）都会拒绝启动；`GeometryBundle` 在导入期逐资产校验摘要、尺寸与 mesh 单位缩放，不通过就整进程不起。这是刻意的：一个"部分可用"的统一候选会让前端误判能力。

## 三、几何读取兼容与执行资格是分开的两件事

统一候选提供 geometry-2 读取（`schema_version: unirot-mobilecar-geometry-2`，带 `geometry_provenance` 与 `geometry_binding`），但这**不**代表 profile/readiness 通过：

- 生产 recipe 仍要求 `interface_profile`/config/scene/runtime 摘要与真实 8792 一致；实测 `POST /experiment-drafts/{id}/validate` 返回 `status=failed`、`execution_eligible=false` 并给出具体 `blocking_reasons`，因此 `POST /sessions` 无法创建 Session。
- 8792 的 `capabilities` 不声明 `session_stop_protocol`/`recording_end_protocol`，所以 prepared/Start/begin/STOP/end 继续按真实原因被拒；本轮未换标签、未放宽 pin、未修改生产 recipe 来制造 Passed。
- 统一候选对不存在的 Session 执行 STOP/end 返回 `session_not_found`（404），且整个检查前后 8792 的 run/generation/episode、recording 状态、owner、safety latch、`base.stopped` 完全一致——用这一点证明"拒绝发生在传输之前、没有 native 写"。
- 生产配置下 STOP/end 的 `stop_unsupported`/`recording_end_unsupported` 信封由平台生产代码路径（同一 `PreparationService` + 生产 recipe）产出并记录在 M1.4 证据册 `api-samples/stop-end-openapi-and-refusals.json`；线上 8792 之所以看不到该 409，是因为更前置的资格校验就已失败，这条事实如实记录，不做等价替换。
- `POST /api/v1/runs/{run_id}/stop` 仍是 run 记录/进程管理，与机器人 STOP 是不同操作；统一检查显式断言两者并存且描述互不混淆。

## 四、候选身份澄清（修正 M1.4 的表述）

`c550a4e495680c8895ca28e92b6aac7de22727086aa351cbad8f42a1618549de` 的真实含义：**生产 recipe 白名单（155 路径）中、在该 release 副本里存在的那 152 个路径的子集摘要**。它：

- 不覆盖 `src/mobilecar/attestation.py`、`src/mobilecar/session_binding.py`（两者都不在那份 155 路径白名单里），也不覆盖 3 个新增集成测试；
- 不能当完整 release pin，也不能据此声称 "drvfix+m1h 已组装验证"；
- 已有的 198 行 `frozen-source-listing.txt` 与 M1.4 证据保持原样，本轮不改写其事实。

本轮实测（只读比较 release 副本摘要与 native 仓库/其它 release）：m1h 冻结副本在 `backends/mujoco/backend.py`(`108dc2d5…`)、`ui/static/g4a2.html`(`35086272…`)、`ui/static/app.js`(`ada45e4d…`)、`assets/landerpi/source_description/urdf/mecanum.xacro`(`4460617c…`) 上与 **drvfix release** 一致、与 `a5cef52` 工作树不同；被补丁改写的 5 个文件摘要与打过补丁的工作树一致，`app.py` 的基线（`bd29d065…`）在 a5cef52 与 drvfix 中相同。结论：该 release 是 **drvfix 内容 + m1h 补丁** 的组装，且**只完成到"组装"这一步**——从未作为 drvfix+m1h 实例启动、集成或 attestation 验证。`backend/config/release-identity.native-m1h.json` 与 `release-identity.m1h.json` 记录这一事实。

## 五、完整发布身份（可复现、缺项必失败）

`backend/tools/release_identity.py` + `backend/config/release-identity.native-m1h.json`：

- 必需集合 = 生产白名单基线（减去显式声明的 3 个 `docs/*.md`）+ 补丁新增执行模块（`attestation.py`、`session_binding.py`）+ 依赖/构建锁（`requirements.lock`、`requirements-test.lock`、`pyproject.toml`）+ 从 `configs/default.yaml`、`configs/g4a2_server.yaml` 出发**沿 `extends` 链闭包**得到的执行配置（4 个）。
- **必需路径缺失即失败**：任一缺失 → 退出码 2、`complete=false`、列出缺失路径，并且**不发布任何聚合摘要**（不提供"只哈希存在文件"的可用性错觉）。
- 摘要 = 对全部必需路径 `{path: sha256}` 做 `json.dumps(sort_keys, separators)` 的 sha256；`verify` 模式重算并报告 removed/changed/摘要比对。
- 显式声明排除范围并给出原因：`var/`、`runs/`、`envs/`、`tools/`、`scripts/`、`provenance/`、`tests/`、`requirements-g2b-lerobot.lock`、`docs/`、生成的 `src/mobilecar/ui/static/app.js(.map)`。
- `watched_roots=src/mobilecar` 的反查：任何位于源码根下、既未列入必需也未声明排除的文件都会作为 `unlisted_under_watched_roots` 报告（正是它暴露了 app.js/app.js.map 是生成物，从而被显式声明）。

服务器实测：m1h 副本 `complete=true`，required=hashed=154，unlisted=0，摘要 `41b9c80c…`；同一规格对**纯 drvfix** 副本 `complete=false`，缺失恰为两个新增执行模块，且未发布摘要；`verify` 重算匹配（`match=true`）。回归 `backend/tests/test_release_identity.py` 5 项在服务器通过，覆盖"新增模块被包含""缺失文件被发现并点名""缺项时不发布摘要""未列入的源码文件被报告""extends 闭包""篡改/删除可被 verify 检出"。

候选清单与生产 pin 分离：本轮不产出、不激活新的生产 pin；生产 recipe 的 `manifest_sha256`/`native_commit` 保持 `a0109804…`/`a5cef52`。未构建任何通用签名体系。

## 六、维护流程顺序修正

M1.4 文档把"更新生产 pin"排在 begin/STOP/end 物理确认之后，等于让一个尚未固定身份的实例先启动。修正后的顺序（见 [backend-m1.4.md](backend-m1.4.md) 第十一节）：

1. **窗口前**冻结：选定 native release 副本 → 生成并核验完整发布身份（第五节的工具）→ 选定 recipe/protocol 集与 config/scene/lock 摘要 → 把 pin 与 recipe 一起固化；
2. 只在 1 完成且全部可复算后，进入**已获授权**的维护窗口；
3. 窗口内：停 8792 前确认无活动录制 → 部署 → 只读核对 `capabilities` 协议声明 → 单次 begin/STOP/end 物理确认（记录 `parking.coverage_complete`、`integrity`、覆盖作用域）；
4. 运行成功后只做一件事：把"pin 与实际运行 release 一致"的核对结论写进交接；**不在此时重新计算 pin**；
5. 任一步失败按回滚判据恢复原 release，内存 binding 随重启消失不伪造恢复。

仍待用户决定（推荐不等于授权，且未做完整组装验证前不承诺任一基线可直接部署）：① G1 还是独立 G4A2 recipe；② `a5cef52` 还是已部署 `drvfix` 为基线；③ 新生产 source pin 的最终签发对象。

## 七、服务器验证结果（本轮全部在服务器执行）

| 检查 | 结果 |
|---|---|
| 统一候选 27 项 HTTP 断言（一个进程、生产 recipe、8792 只读） | 27/27 通过；含 geometry-2 + 23 资产逐字节摘要、持续 Actual、真实地图版本/图像摘要/compatibility、Route 草稿发布与陈旧 baseRevision 409、资格失败、STOP/end 拒绝、native 前后完全一致、DB 全新 |
| 正向 STOP/end 生命周期（test-only recipe + mock native + 真实 Recorder） | 39/39 通过，`episode_terminal` 事件数与预期一致（并发 1 个 + 新 segment 清理 1 个），磁盘尾记录摘要与回执一致 |
| 平台全量 | 128 passed / 3 failed（131 项）|
| 历史失败基线（未跳过、不称全绿） | `test_catalog::test_catalog_loads_real_tasks`、`test_catalog::test_every_task_has_existing_evidence`、`test_migrate::test_manifest_sources_exist`。可核对链条：74/3 → 90/3 → 98/3 → 108/3 → 123/3 → 本轮 128/3，均为读取仓库文档布局/外部工程资产的断言，在服务器 release 副本（不含 `docs/`）上必然失败；本轮未新增失败项，新增 5 项身份回归全部通过 |
| 8792 | 全程仅 GET：`run_9c88e3e3…/gen 1/episode_43c22f95…`、`recording_status=IDLE`、无 owner、未 latched、`base.stopped` 与检查前后一致 |
| 测试服务 | 18954/18956 test-only 服务用前确认空闲、检查后已停止；统一候选 18959 用前确认空闲、检查后保留为常驻联调地址（见第八b节）；未触碰 18949/18953/前端预览 |

## 八、端口与既有服务

| 端口 | 身份 | 本轮处理 |
|---|---|---|
| 8792 | 真实 native（PID 941842、`drvfix`、`g4a2_server.yaml`、`backend_kind=mujoco`） | 仅 GET；未 STOP/RESET/begin/end/重启/替换 |
| 18949 | M1.2d 生产 recipe 候选（启用 `UNIROBOT_GEOMETRY_BUNDLE`，提供 geometry-2） | 保留 |
| 18953 | M1.3 Map/Route 候选（未设置该变量 → read-1 场景） | 保留，未替换 |
| 18958 → 18953、18957 → 18949 | 当前前端预览代理（18958 为最新前端端口） | 只作现状记录，未启停前端 |
| 18944 / 18943 / 18950 / 18951 / 18946 / 18942 / 18941 / 18935 / 18933 / 18932 / 18931 / 18905 | 既有候选与预览 | 保留 |
| 18954 / 18956 | 本轮 test-only native mock、test-only 平台 | 用前确认空闲，用后已停止 |
| **18959** | **统一可联调候选（当前存活）** | 用前确认空闲后以 `setsid` 常驻启动；对前端即为可消费基址，未替换 18949/18953 |

统一候选与 18953/18949 的关系是**新增**，不是替换：三者可在不同端口同时存在，差异只在启动配置（是否给 geometry bundle、maps 根、DB 命名空间、native 地址）。

## 八b、统一候选地址（交付给前端）

- 基址：`http://127.0.0.1:18959`（服务器本机回环；前端沿用现有同源代理即可，无鉴权、不需要 `Authorization`）。
- 该地址即本轮冻结 release `m1j-20261025T020857Z-platform` 的常驻进程（服务器实测：`PID 3608367`、`PPID 1`、`SID=PID` 即独立会话，启动时间 2026-10-25 10:16:57 本地；逐字命令行、工作目录、环境变量与只读探测结果记录在 `live-candidate-identity.json`，由 `m1j_live_identity.sh` 以 `ss`/`/proc`/GET 生成）。存活确认命令：服务器上 `ss -ltnp sport = :18959` 与 `pgrep -af launch_unified_gateway`。常驻启动脚本见 `m1j_live.sh`（端口被占用即拒绝，不替换已存活实例；该脚本按存活进程的 `/proc` 命令行复现，实时启动当时是逐条交互执行的，不是当时的原始输入记录）。
- 实际启动参数（服务器实测的进程命令行，逐字）：

  ```bash
  REL=$HOME/Desktop/uniRobotPlatform/releases/m1j-20261025T020857Z-platform
  cd $REL/backend
  PYTHONPATH=$REL/backend/src setsid \
    $HOME/Desktop/uniRobotPlatform/envs/gateway-py314/bin/python \
    tools/launch_unified_gateway.py --port 18959 \
      --native-url http://127.0.0.1:8792 \
      --geometry-bundle $HOME/Desktop/uniRobotPlatform/releases/m1-geometry-20261023T192202Z-cdfc7472e5de/geometry \
      --map-catalog $REL/backend/config/maps.catalog.json \
      --maps-root $HOME/Desktop/mobileCar/var/maps \
      --draft-db $REL/report/unified-live-021657.sqlite3 \
      --out-manifest $HOME/Desktop/uniRobotPlatform/var/reports/m1j-20261025T020857Z-platform/unified-startup-live.json
  ```

  进程环境只有 `PYTHONPATH`；仓库根由 `settings.py` 向上查找 `docs/specs/catalog.json` 解析到该 release 副本自身（副本内含 `docs/`），因此不依赖 `UNIROBOT_REPO_ROOT`。`UNIROBOT_ALLOW_LAUNCH` 未设置，平台不会启动任何本地进程。
- 在该存活地址上重新执行了同一套 27 项断言并全部通过（27/27）：证据 `unified-candidate-check-live.json` + `unified-startup-live.json`（与首次一次性检查的 `unified-candidate-check.json`/`unified-startup.json` 是两次独立运行，结论一致）。两次启动清单只在 `database.path` 上不同，源码聚合摘要、recipe、geometry bundle 与 maps 配置逐字段一致。
- 存活的是**联调候选**，不是生产部署：native 仍是 8792 的 drvfix/G4A2 实例（仅 GET），生产 recipe/pin 未改；`current.stop_available`/`recording_end_available` 在该地址上仍为 `false`。
- 该进程使用独立 SQLite（`existed_before=false`），不读写任何更早候选的数据库；如需回收端口，用 `ss` 找到 pid 后终止该进程即可，不影响 8792/18949/18953。

## 九、前端接线（本轮不改前端代码）

前端 worktree 的 `backend-gaps.md`/`development.md`（2026-10-24）记录的现状是：3D/Session 走 18957→18949（geometry-2 可用）、地图/路线走 18958→18953（read-1，故其严格判定拒绝在 18953 挂 3D 工作台）。本轮提供的是一个**同时满足两侧**的候选基址：`http://127.0.0.1:18959`（存活地址与完整启动参数见第八b节；同源代理即可，无鉴权，`Authorization` 不需要）。要点：

1. 场景契约版本要按 `schema_version` 判定（geometry-2 才挂 3D 工作台），而**执行 ready/available 只认 `current` 的字段**，不因 geometry-2 可读就推断已 Start/已 ready。
2. STOP/end 可用性由 `current.stop_available`/`recording_end_available` 决定；当前生产 recipe + 8792 下二者为 false，应显示"当前运行实例不支持该动作"，不可隐藏或伪造成功。
3. 结果文案按 `code` 分支：`accepted=true` 只代表受理；`parking.coverage_complete=false` 时按 `scope_coverage` 列出 `confirmed/unconfirmed/not_observed`（夹爪首版恒 `not_observed`）；`ended_parking_unconfirmed`、`ended_incomplete_terminal`、`end_finalize_failed`、`end_already_finalized` 各不相同；409 `session_not_stoppable` 表示 Session 已关闭；同一 `request_id` 重试返回 200 `replayed=true`。
4. `POST /api/v1/runs/{run_id}/stop` 不得作为停止按钮后端。
5. 仍缺的能力（前端不应假设存在）：Route 列表/采用端点、footprint/整条路径可达/动态执行的资格结论、导航执行、真实运动与录制闭环。

契约与样例：`/openapi.json`（含 `StopSession/EndRecording/StopReceipt/RecordingEndReceipt/SessionCurrent`）、`docs/evidence/m1.4-stop-end/*/api-samples/stop-end-openapi-and-refusals.json`、本轮 `docs/evidence/m1.4b-unified/*/unified-startup.json` 与 `unified-candidate-check.json`。

## 十、冻结状态与边界

- 平台：本轮新增 `backend/tools/release_identity.py`、`backend/tools/launch_unified_gateway.py`、`backend/tools/unified_candidate_check.py`、`backend/config/release-identity.native-m1h.json`、`backend/tests/test_release_identity.py`；服务器冻结 release `m1j-20261025T020857Z-platform`，平台源码聚合摘要 `26c60b76acbac68a…`（30 文件）。平台改动本地提交、**不推送**。
- 统一候选 18959 保留为**联调用**常驻进程（非生产、非 8792、非物理实例）；它只读真实 native HTTP，写入范围限于自己的 SQLite 与内存状态。前端或后续会话把它当基址使用时，先确认存活（`ss -ltnp sport = :18959`），不要因为本文件写了地址就假设它永远在。
- native：既有未提交补丁保持，不提交、不推送、不部署；本轮候选变更只以清单/摘要形式单独记录。
- 未验证：真实停车确认、G1 或 G4A2 生产 recipe 下的实际 prepared/Start/begin/STOP/end、8792 部署、物理运动与录制、训练与回放闭环。
- 本 Goal 完成只表示"统一联调候选与部署准备"完成，不表示生产已部署或 M1 闭环通过。
