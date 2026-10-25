# M1.4b 证据册｜统一可联调候选与部署前发布身份

目录：`m1j-20261025T020857Z-platform/`（服务器 release `releases/m1j-20261025T020857Z-platform`）。全部测试、构建与集成在服务器执行；本地未运行任何测试或构建。8792 全程仅 GET。

## 一、冻结标识

| 项目 | 值 |
|---|---|
| 平台 release | `m1j-20261025T020857Z-platform`（由 `m1i-20261024T163746Z-platform` 叠加本轮工具/测试/配置，独立 release，未替换任何既有实例） |
| 平台源码聚合摘要 | `26c60b76acbac68a…`（`src/unirobot` + `backend/config` 共 30 个文件，完整值见 `unified-startup.json` 的 `platform_source`） |
| native 候选完整发布身份 | `release-identity.m1h.json`：required=hashed=154，摘要 `41b9c80c5d03eb11a2ff5551407430559514353d1d8bee324f4ad9111a5e038a`，受监视源码根下未列入文件 0 个 |
| 同一规格对纯 drvfix 副本 | `release-identity.drvfix.json`：`complete=false`，缺失恰为 `src/mobilecar/attestation.py`、`src/mobilecar/session_binding.py`，**未发布任何摘要** |
| 复算 | `release-identity.verify.json`：`match=true`（removed/changed 均为空） |
| 规格与工具（已入仓） | `backend/config/release-identity.native-m1h.json`、`backend/tools/release_identity.py`、`backend/tests/test_release_identity.py` |
| 上一轮 M1.4 证据（保持原样） | [../m1.4-stop-end/README.md](../m1.4-stop-end/README.md)：`frozen-source-listing.txt`（198 行）、`native-m1h.patch`（sha256 `d182801d…a99f`）、子集摘要 `c550a4e4…` |

生产 pin `a01098040d953608004a34b3c76519d7884eaa4b2c95e36822bd4e7d283b911c`（`native_commit a5cef52`）与生产 recipe 未修改、未激活。

## 二、文件

| 文件 | 内容 |
|---|---|
| `unified-startup.json` | 统一候选的冻结启动配置：端口、native 地址、geometry bundle 路径与 `bundle.json` 摘要、23 资产逐文件摘要、map catalog/资源根与包列表、recipe（id/revision/fingerprint/required_protocols）、数据库命名空间与 `existed_before=false`、平台源码摘要 |
| `unified-candidate-check.json` | 27 项断言全通过（见第三节） |
| `unified-check.log`、`unified-gateway.log` | 检查与网关输出 |
| `cross/cross-http-stop-end.json` | 同一冻结源码上的正向 STOP/end 生命周期 39/39（test-only recipe + mock backend + 真实 native HTTP + 真实 Recorder 文件），尾事件与摘要核对一致 |
| `cross-run.log` | 上述集成的退出码与摘要行 |
| `release-identity.m1h.json`、`release-identity.drvfix.json`、`release-identity.verify.json` | 完整发布身份、缺项反例与复算 |
| `m1j_identity.sh`、`m1j_unified.sh`、`m1j_cross.sh`、`m1j_final.sh` | 本轮在服务器上实际执行的编排脚本 |

## 三、三类结论必须分开读

1. **真实生产拒绝**（生产 recipe + 真实 8792 的统一候选）
   - 一个进程同时暴露全部面：`/openapi.json` 含 Session/STOP/end/Map/Route/Draft 全部路径与 `StopSession/EndRecording/StopReceipt/RecordingEndReceipt/SessionCurrent` schema；`/api/v1/mobilecar/scene` 返回 `unirobot-mobilecar-geometry-2`，23 个资产逐字节摘要与冻结 bundle 一致；`geometry_binding`/`geometry_provenance` 与 bundle 声明的 `bundle_sha256`、`compiled_scene_sha256` 相符；`capabilities`/`snapshot`/`kinematics` 可读且 Actual 随读取推进；地图列表与固定版本可读、`live=false`、`assets_verified=true`、compatibility 不含任何 eligible=true；Route 草稿发布产生不可变版本且 `navigation_eligible/adoption_supported/execution_supported=false`、陈旧 `baseRevision` 保存返回 409。
   - 资格与读取分开：`POST /experiment-drafts/{id}/validate` 返回 `status=failed`、`execution_eligible=false` 与具体 `blocking_reasons`，`POST /sessions` 因此被拒；8792 的 capabilities 不声明 `session_stop_protocol`/`recording_end_protocol`，故 `current.stop_available=false`、`recording_end_available=false`；对未知 Session 的 STOP/end 返回 `session_not_found`。
   - 无 native 写：整个检查前后 8792 的 run/generation/episode、recording 状态、owner、safety latch、`base.stopped` 完全一致（`native_read_state.before == after`）。
   - `POST /api/v1/runs/{run_id}/stop` 仍是独立的记录/进程操作，检查显式断言两者并存且描述不混淆。
2. **test-only 通过**（正向生命周期）：begin → STOP → 并发 end → 重复请求 → 回读 → 新 segment 清理，39/39；只在明确标注的 mock backend 与独立记录目录上成立。
3. **未执行**：真实停车确认、真机 STOP、G1 或独立 G4A2 生产 recipe 下的实际 prepared/Start/begin/STOP/end、8792 或任何运行实例的补丁部署、物理运动/录制/训练、M1 闭环验收。

## 四、复现方式（服务器）

```bash
# 1) 端口空闲检查：18954 / 18956 / 18959
# 2) 正向生命周期：test-only mock native（独立 recording.root）+ mock_native_protocol_app
python tools/cross_http_stop_end_check.py --platform-url http://127.0.0.1:18956 \
  --native-url http://127.0.0.1:18954 --native-runs <独立目录> --out <证据目录>/cross
# 3) 统一候选（生产 recipe，geometry-2 + 真实地图/路线 + 独立 SQLite）
python tools/launch_unified_gateway.py --port 18959 --native-url http://127.0.0.1:8792 \
  --geometry-bundle <已核验 geometry 目录> --map-catalog backend/config/maps.catalog.json \
  --maps-root <mobileCar/var/maps> --draft-db <release>/report/unified-<ts>.sqlite3 \
  --out-manifest <证据目录>/unified-startup.json
python tools/unified_candidate_check.py --platform-url http://127.0.0.1:18959 \
  --native-url http://127.0.0.1:8792 --bundle-dir <geometry 目录> \
  --startup-manifest <证据目录>/unified-startup.json --out <证据目录>/unified-candidate-check.json
# 4) 发布身份
python tools/release_identity.py build  --root <native release> --spec backend/config/release-identity.native-m1h.json --out identity.json
python tools/release_identity.py verify --root <native release> --manifest identity.json --out verify.json
```

`*.log` 若被仓库 `.gitignore` 排除，保留在服务器 `~/Desktop/uniRobotPlatform/var/reports/m1j-20261025T020857Z-platform/`。
