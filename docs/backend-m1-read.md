# M1 后端切片｜mobileCar 场景、资产、能力与实际状态

日期：2026-10-23（America/Los_Angeles）。本切片已经实现并在服务器验证；**它是只读接入，不是 M1 运行/控制/录制/回放闭环验收。**

## 当前联调稳定约束

用户已明确前端开始接入本组服务。保持服务器18941和 `unirobot-mobilecar-read-1` 稳定；不重启native，不开放运动、RESET或录制，不修改frontend。当前网关PID1155600、native PID941842；本轮只读核对确认两者未变，OpenAPI字节与冻结报告相同，capabilities/snapshot运行身份一致，`read_only=true`、`session_ready=false`。

wire Schema、资产URI、身份一致性和错误码的问题由后端修复，优先保留当前兼容行为。若接口必须变化，提供字段/语义/错误码的明确差异、真实请求响应与前端适配说明；不能以扩大控制能力解决读取联调问题。本约束优先于此前后续控制/录制的实施顺序，直到用户明确调整范围。

## 协作与源码位置

- 与前端使用同一共同基线：`2f7ff9b091c060034e55d2f387dbb6e130aaada3`，内容树 `76289b0fb63b5afbd6c6086eb42e6c0a462d6e3c`。此前另存的 `codex/parallel-base-20261023` 内容相同，原工作目录和未提交成果没有被 reset/clean。
- 本方分支：`codex/backend-m1-services`；worktree：`/home/liaozhengyan/.codex/worktrees/backend-m1-read/uniRobotPlatform`。本轮只写后端、共享读取契约和本方记录，未修改 `frontend/`、前端页面设计或原生仓库，未推送。
- 保留 M1.1 pin/preflight 和 M1.2 草案/冲突/stale 处理。当前新增服务不依赖它们签发执行快照，不创建平台 Session。

## 前端可以开始联调的接口

服务器 `cec-sim` 上的网关监听 **`127.0.0.1:18941`**，读取既有 native `127.0.0.1:8792`。这是服务器回环地址；前端开发服务器可代理到它，不能把本机浏览器的 localhost 当作远端服务器。没有对公网新增监听。

| 方法 / 路径 | 已开放行为 |
|---|---|
| GET `/api/v1/mobilecar/scene` | 编译场景、link/joint/geom、对象树 ID、相机名称与 mesh 清单；`data` 可用于封装现有 SceneView |
| GET `/api/v1/mobilecar/capabilities` | 实际机器人关节顺序/限位/速度、底盘/夹爪限位、TCP 容差、原生命令与传感器声明；平台动作能力另外保持 false |
| GET `/api/v1/mobilecar/snapshot` | 实际关节/底盘/夹爪/TCP、独立 Target、源时间/身份、传感器引用、原生 Owner/录制状态的只读投影 |
| GET `/api/v1/mobilecar/scene/assets/{asset_id}?sha256={digest}` | 只读取当前场景已列出的 STL；先检查请求摘要，再核验收到的字节，成功返回 `model/stl` 与 ETag |
| GET `/openapi.json` | 上述返回结构的 Pydantic/OpenAPI 类型，包含 `SceneRead`、`CapabilitiesRead`、`SnapshotRead` |

在服务器执行的请求示例：

```bash
curl --fail-with-body http://127.0.0.1:18941/api/v1/mobilecar/scene
curl --fail-with-body http://127.0.0.1:18941/api/v1/mobilecar/capabilities
curl --fail-with-body http://127.0.0.1:18941/api/v1/mobilecar/snapshot
curl --fail-with-body 'http://127.0.0.1:18941/api/v1/mobilecar/scene/assets/base_link?sha256=9eb685251829f79fb36a29c5bcafb7a8d6775eb6c9cae5e99a9451c633934223'
```

资产应采用本次 `scene.data.mesh_assets[].uri`，不要把示例摘要长期写死。URI 指向本平台，原生提供的任意外部 URI 不被代理。所有读取与错误返回 `Cache-Control: no-store`，失败不返回缓存的旧成功状态。

## 数据约定与实际限制

完整字段和行为见 [CT-STATE 的实现子集](specs/30-contracts/01-robot-world-state.md#mobilecar-read-v1)。机器类型见 [实现](../backend/src/unirobot/mobilecar_read.py) 和本 release 的 [OpenAPI](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/openapi.json)。

- envelope 的 `schema_version=unirobot-mobilecar-read-1`、`data_source=live_native_http`、`read_only=true`；`platform_session_id=null`、`session_ready=false`。`retrieved_at` 是网关时间，不能替代 `data.time` 的采样/反馈时间。
- 返回真实 `runtime_identity={run_id,backend_generation,episode_id}`、`resource_identity`、`interface_profile`。每组读取以两次 health 检查身份；组内变更返回409。跨请求不是原子事务，前端切换 run/epoch 或资源时应丢弃旧 Target/Preview 并重载场景。
- 当前 native profile 是 **g4a1-1.0**，不是固定 G1 recipe 的 g2a-1.0；本次读取并未更新 native pin。`resource_matches_pin=true` 仅比较 model ID、根 XML 摘要和 scene ID；`deployed_content_verified=false`，不证明整个源码/配置/资产清单相同，更不授予执行资格。
- 当前真实能力为5个臂关节，camera ID 为 `rgbd`。不得由页面图扩展成6-DoF或多路腕相机。原生 `supported_commands` 是 native 的声明；本平台 `platform_commands_available/platform_recording_available/platform_replay_available` 仍为 false。
- `data.actual` 只放实际状态，`data.target` 放 native 已持有的关节/夹爪/底盘目标；`preview=null`，`target.command_id=null`、`target.tcp=null` 明确缺少命令关联/独立 TCP 目标。前端本地拖动 Target 不写 Actual，也不能把读取到的 native 目标当成新命令回执。
- 用户关节与模型关节角均保留 rad；两者有零位映射差异。机器人渲染优先使用 `actual.model_joint_positions_rad` 的原生关节名称映射，不把用户角直接当全部模型角。底盘位置在 world_sim、速度在 base_link，姿态为 xyzw；TCP 在 world_sim，距离 m，角度 rad，速度 m/s 与 rad/s，关节力矩 Nm。
- `objects[].object_id` 使用 `body:{encoded_name}`、`joint:{encoded_name}`、`geom:{encoded_body}/{encoded_geom}`，绑定当前编译场景；完整来源还需保留 adapter/运行/资源身份。`data.links/world_links` 的变换是编译初始布局，world_links **不是物体实时位姿**，以 `world_pose_semantics` 明示。
- 场景几何参数保留原生 SceneView 的格式；特别是 mesh 的 `size_m` 数组实际用作各轴缩放，不能把所有几何的该数组统一解释为物体长宽高。
- Snapshot 默认删除未受限的 diagnostics、contact_summary、plan 和任意额外载荷，不透传 Oracle/物体真值；这不是完整 Policy Observation API。传感器保留 sample/stream、measurement/arrival/capture/feedback 引用及原生 fresh/quality；native SensorState 未给 frame，因此明确 `frame_id=null`。`native_asset_uri` 仅为原生记录引用，`sensor_media_status=not_exposed`；当前不能据此在平台加载 RGB/Depth 媒体。原生 `simulated_nominal_preview` 等 quality 保留，不外推训练图像资格。
- Owner 只反映原生当前身份：`authorizes_caller=false`，`lease_status=not_exposed`；`active_session_id` 是 native session，不是平台 prepared Session。STOP/租约/require_recording 仍由原生保留，本切片没有调用它们。

真实响应节选（省略的字段见完整 JSON，不是另一种响应形状）：

```json
{
  "schema_version": "unirobot-mobilecar-read-1",
  "data_source": "live_native_http",
  "read_only": true,
  "session_ready": false,
  "platform_session_id": null,
  "interface_profile": "g4a1-1.0",
  "runtime_identity": {
    "run_id": "run_9c88e3e36e7648a3852c9f590e43ed5f",
    "backend_generation": 1,
    "episode_id": "episode_43c22f95536f4517be04e4b195d6d354"
  },
  "data": {
    "target": {
      "base_velocity": {"frame_id": "base_link", "vx_m_s": 0.0, "vy_m_s": 0.0, "wz_rad_s": 0.0},
      "command_id": null,
      "tcp": null
    },
    "preview": null,
    "sensor_media_status": "not_exposed"
  }
}
```

完整真实响应：[scene](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/scene.json)、[capabilities](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/capabilities.json)、[snapshot](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/snapshot.json)。这些是带时间的只读取样，不能重放成命令或当作当前持续值。

## 错误样例

| HTTP / code | 含义与前端处理 |
|---|---|
| 503 `native_not_configured` / `native_offline` | 未配置/断连/超时，清理 live 可用状态；不显示旧值仍为最新 |
| 502 `native_incompatible` / `native_error` | 外部字段、长度、Frame、有限数值或 native HTTP 失败；显示原因，不用零值补齐 |
| 409 `native_identity_changed` | health 与快照或读取前后的 run/generation/episode 不一致；重载来源并作废旧目标 |
| 404 `unknown_asset` | 当前场景中不存在该资产，不把任意 ID 转为 native 文件请求 |
| 409 `asset_revision_changed` | 请求摘要与场景清单不同，重新加载清单 |
| 502 `asset_integrity_failed` | 资产字节不符合清单摘要，不交给 renderer |
| 422 | 缺少或格式错误的 sha256 请求参数 |

真实错误请求：

```bash
curl -i 'http://127.0.0.1:18941/api/v1/mobilecar/scene/assets/unknown?sha256=0000000000000000000000000000000000000000000000000000000000000000'
```

```json
{"detail":{"code":"unknown_asset","message":"Unknown scene asset","read_only":true,"session_ready":false}}
```

真实错误回执：[404](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/unknown-asset.json)、[409](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/stale-asset.json)。断连、损坏状态、身份跳变和字节不符的回归使用合成夹具，未通过改变既有物理实例制造故障。

## 修改边界与仍待实施的服务

平台修改 `api.py`、`mobilecar.py`，新增 `mobilecar_read.py` 与聚焦测试。读取复用原生 health/capabilities/scene/snapshot/scene-assets HTTP，不 import MuJoCo、不改原生源码、不新增物理执行者。未新增工作台页面，也未改旧草案行为。

| 后续职责 | 当前状态 / 最小真实差距 |
|---|---|
| Draft / 验证快照 / prepared / Start | 已有元数据草案继续可用；Session创建仍409 unsupported。native 缺少无运动绑定、显式Start与唯一上下文回读保证，不能用 health 或 episodes/start 代替 |
| 控制、Owner/lease、命令回执/终态 | 本平台仍未开放。native 请求包含运行/Episode/session/operator/ID/seq/TTL；需落实绑定、授权与旧命令失效，完整lease只读查询目前缺失 |
| 录制 begin/end | native start 含RESET，须确认实际应用身份/初态；起始持久化、独立停车结论与drain/finalize仍需接入，不把接收或COMPLETE当作停稳 |
| 相机媒体/观测流 | 当前只开放 SensorState 引用与质量；实际媒体、Frame/标定和受限观测载荷仍需明确接口后开放 |
| Episode / segment / ReplayReader | 尚未开放平台历史API。保留native身份，需解决仅按episode查询的歧义，默认历史读取不得带在线命令/步进能力 |

这些后续工作不影响前端先替换场景、资产、能力、Actual/Target 监控的模拟服务；真实运动仍须等运行绑定/授权和录制门控均满足。

## 实际验证与复现

最终冻结 release：`m1-read-20261023T155543Z-cef9ddedf781`。27个输入文件，聚合 SHA-256 `cef9ddedf7815bff4158f25e21737b49aa20cfe70f691a0c90c281dfbf19def3`；上传后逐文件核对。

测试后仅补交付文档、共享契约和目录元数据；本地后端源码/测试与该冻结清单逐文件一致。release保留当时的目录元数据，部署输入身份以清单为准。

| 检查 | 结果 / 证据 |
|---|---|
| 服务器聚焦回归 | 50 passed（原32项接入/API/草案与新增18项读取）；[JUnit](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/focused.junit.xml)、[日志](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/focused.log)。1项现有 TestClient/httpx 弃用提示，未为此升级共享环境 |
| 真实只读HTTP | scene/capabilities/snapshot 均200，71个robot links、2个world links、237个对象ID；[读取结果](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/live-read-check.json) |
| 真实网格 | 23/23 HTTP成功且字节SHA-256匹配清单；[逐资产记录](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/asset-checks.json)，没有把大网格复制回平台仓库 |
| 原生影响 | 同一既有PID941842、run/generation/episode与录制状态前后相同；[摘要](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/native-before-after-summary.json)。只做GET，没有运动/RESET/录制调用，未启动/停止任何物理实例 |
| 可复核输入/环境 | [源码清单](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/source-manifest.json)、[环境](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/environment.txt)、[产物索引](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/server-artifact-index.json)；精简回传约34KB压缩，不含DB/原始Episode/媒体 |

只读网关保持运行供联调，进程身份在 [gateway-job.json](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/gateway-job.json)；旧候选网关经核对PID/命令/cwd后已优雅退出，未触及native。当前网关 `UNIROBOT_ALLOW_LAUNCH=0`。不要按进程名批量停止，也不要覆盖其他任务端口。

当该网关已经停止、18941为空闲时，可在服务器冻结release目录复现：

```bash
cd /home/liaozhengyan/Desktop/uniRobotPlatform/releases/m1-read-20261023T155543Z-cef9ddedf781
UNIROBOT_CATALOG=report/catalog.live.yaml UNIROBOT_DRAFT_DB=report/live-drafts.sqlite3 \
  UNIROBOT_ALLOW_LAUNCH=0 UNIROBOT_PROBE_TIMEOUT=3 PYTHONPATH=backend/src \
  /home/liaozhengyan/Desktop/uniRobotPlatform/envs/gateway-py314/bin/python \
  -m uvicorn unirobot.api:app --host 127.0.0.1 --port 18941
```

聚焦测试的完整命令、退出状态和耗时见 [test-result.json](evidence/m1-read/m1-read-20261023T155543Z-cef9ddedf781/report/test-result.json)。本轮没有执行浏览器/前端验收、真实示教、训练、native全量回归或 TEST-MOBILE-001/002，不能宣称 M1 闭环通过。
