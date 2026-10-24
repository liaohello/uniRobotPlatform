# M1.4 证据册｜受 Session/运行身份约束的机器人 STOP 与录制可靠结束候选

生成时间：2026-10-24（UTC 时间戳见各 release 目录名）· 执行位置：开发服务器（本地未运行任何测试、构建或集成）

本目录只证明候选实现与**无物理**集成结果。**没有**部署、重启、替换或停止 8792，**没有**推进 MuJoCo 物理，**没有**验证真实机器人停稳。

## 一、冻结标识

| 项目 | 值 |
|---|---|
| 平台 release | `m1i-20261024T163746Z-platform`（服务器 `~/Desktop/uniRobotPlatform/releases/`） |
| 平台源码清单 | `platform-source-listing.txt`（42 个 src/tests/tools/config 文件）· sha256 `789e8072e07337e98982f366acefa7c729172e783af51e8e74a53767ee5af81e` |
| native release（候选补丁应用后的冻结副本） | `m1h-20261024T152235Z-native`（服务器 `~/Desktop/mobileCar/releases/`） |
| native 补丁 | `native-m1h.patch` · sha256 `d182801df7381bc45717ff40b0d61df28b5437e92f6ee5528127bdf6d231a99f` · 10 个文件 |
| native 冻结源码清单 | `frozen-source-listing.txt`（198 个文件）· sha256 `8ded7de6ecd031135e5ea4278de9d709950290377dd8311587a8723a3e9fc674` |
| native 候选 source pin | `native-candidate-pins.json` · pin `c550a4e495680c8895ca28e92b6aac7de22727086aa351cbad8f42a1618549de`（生产 recipe 白名单中 release 内实际存在的 152 个路径） |
| 生产 pin（**未修改、未复用**） | `backend/config/mobilecar-g1-source.json` · `a01098040d953608004a34b3c76519d7884eaa4b2c95e36822bd4e7d283b911c`（`a5cef52` base，无本轮补丁） |
| 补丁基线 | native 仓库既有未提交补丁全部保留；本轮补丁叠加在其上，**未提交、未推送 native**，native git 索引未改动 |

候选 pin 与生产 pin 不可互换：生产 recipe 的 `required_protocols` 只声明 `session_binding`/`recording_begin`，因此生产配置下 STOP 与录制结束必须被平台拒绝为 unsupported。

## 二、目录内容

| 路径 | 内容 | 性质 |
|---|---|---|
| `cross/cross-http-stop-end.json` | 39 项断言的完整结果、STOP/end 回执、并发回执、拒绝样本、Recorder 文件摘要 | 真实 native HTTP + 真实 Recorder 磁盘（mock backend） |
| `cross-runs-dir.txt`、`native-runs-path.txt` | 独立记录目录与 test-only profile 的服务器路径 | 运行索引（`.log` 被 Git 忽略，见下） |
| 服务器上的 `cross-run.log`、`platform-final.log`、`native-final.log` | 检查退出码、两端服务请求日志 | 保留在服务器 `~/Desktop/uniRobotPlatform/var/reports/m1i-20261024T163746Z-platform/` 与 `~/Desktop/mobileCar/var/reports/m1h-20261024T152235Z-native/`；仓库 `.gitignore` 排除 `*.log`，故未入库 |
| `native-reports/m1i-mock-run-163748.yaml` | 本轮每次启动生成的 test-only profile：`backend.kind: mock`、独立 `recording.root` | test-only 配置 |
| `native-runs/m1i-cross-163748/…` | Recorder 真实落盘：`events.jsonl`、`episode_complete.json`、`episode.json`、初始快照、质量/评估报告 | 磁盘证据（10 个文件） |
| `recorder-file-list.txt`、`recorder-file-digests.txt` | 上述落盘文件的清单与 sha256；本地副本已逐一核对一致 | 完整性核对 |
| `api-samples/stop-end-openapi-and-refusals.json` | OpenAPI 路径/Schema 摘录、生产 recipe 拒绝信封、`current` 可用性字段 | 前端接线样例 |
| `production-8792-get-only/` | 8792 的 `GET /api/v1/capabilities`、`GET /api/v1/health` 原文 | 只读，未发送任何控制请求 |
| `native-junit/` | native 聚焦（31）与适用全量（122，2 项历史失败）JUnit | 测试报告 |
| `native-candidate-pins.json`、`native-artifact-sha256.txt` | 候选 pin 规则与补丁/清单摘要 | 冻结记录 |

## 三、三类结论必须分开读

1. **真实生产拒绝**（生产配置下会发生什么）
   - 8792 的 capabilities **不含任何** `*_protocol` 字段（`production-8792-get-only/capabilities.json`，`backend_kind: mujoco`，`interface_profile: g4a1-1.0`），即既未声明 `m1-stop-1`，也未声明 `m1-end-1`。
   - 生产 recipe 下平台直接拒绝：`POST …/stop` → HTTP 409 `stop_unsupported`；`POST …/recording/end` → HTTP 409 `recording_end_unsupported`；`current` 报告 `stop_available=false`、`recording_end_available=false`（`api-samples/…json` 的 `production_refusals`、`production_current_availability`）。
   - 以上均来自平台生产代码路径，与 mock 成功样本使用同一份代码。
2. **mock 成功**（候选行为是否正确）
   - 明确标注的 mock backend + 真实 native HTTP + 真实 Recorder 文件系统：begin → STOP → 并发 end → 回读 → 新 segment 清理，39/39 断言通过（`cross/cross-http-stop-end.json`）。
   - 落盘核对：一次结束只写一个 `episode_terminal`；并发两个请求最终一个 `ended`（下发 STOP 并 finalize）、一个 `end_already_finalized`（不下发、不重复尾事件），两个回执各自保留；`episode_complete.json` 摘要与回执一致；终态 `audit_status=COMPLETE`、`integrity=complete`。
   - 停车证据 `parking.coverage_complete=false`（gripper `not_observed`）：候选没有把 `base.stopped` 单独当成"整机停稳"。
   - 两次独立运行覆盖了两种竞态顺序（一次 `end-race-2` 先完成、一次 `end-race-1` 先完成），断言与顺序无关。
3. **尚未执行**（不能由本证据推出）
   - 真实 MuJoCo 停车确认、真实 G1 机器人 STOP、维护窗口部署、8792 或任何运行实例的补丁部署。
   - 停车未确认与 finalize 失败缺尾两条路径无法只靠 HTTP 触发，在 native 测试套件中以注入方式覆盖（`native-junit/`），不等同于真机行为。

## 四、复现方式（服务器）

```bash
PREL=m1i-20261024T163746Z-platform
NREL=m1h-20261024T152235Z-native
# 1) 确认 18954/18956 空闲（8792、18953、前端预览端口不参与本轮）
# 2) 用 test-only profile 启动 native（backend.kind: mock，独立 recording.root，PYTHONPATH=$N/src）
# 3) 启动 test-only 平台 app（uvicorn mock_native_protocol_app:app，独立 SQLite）
# 4) 运行 backend/tools/cross_http_stop_end_check.py --platform-url ... --native-url ... \
#      --native-runs <独立目录> --out <证据目录>
```

`mock_native_protocol_app.py` 与 `cross_http_stop_end_check.py` 只声明 test-only recipe（`mobilecar.g1.teleop.mock-testonly`，`recipe_revision: 2`，四个 required protocol）。生产 recipe 文件未被修改，生产期望也未为通过测试而放宽。
