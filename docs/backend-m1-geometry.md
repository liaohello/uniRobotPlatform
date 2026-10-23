# M1 后端联调修复：编译网格候选

日期：2026-10-23（America/Los_Angeles）。**18942 只读候选已在服务器验证；18941/read-1 与 native 8792 保持运行不变。整车装配视觉验收由前端完成，本记录不是 M1 运行/录制/回放验收。**

## 问题与修复边界

原生 `sensors/scene.py` 使用编译后的 `geom_pos/geom_quat`，却提供原始 STL 和 `mesh_scale`。MuJoCo 编译时会缩放、居中并对齐网格，随后将补偿变换合入 geom 位姿；原始 STL 直接配上编译后的 geom 位姿会产生偏移。依据：[MuJoCo 3.1.6 mesh/geom 定义](https://mujoco.readthedocs.io/en/3.1.6/XMLreference.html#asset-mesh)、原生 `src/mobilecar/sensors/scene.py`、参考工程 `mujoco_learning/robots/landerpi/ik_lab/ui.py` 的 `mesh_vert/mesh_face` 路径。

候选从同一服务器部署源码、同一 MuJoCo 3.1.6 环境离线编译 **MjModel**，直接导出 `mesh_vert` 与本地索引 `mesh_face` 为 binary STL。不创建 MjData，不调用 mj_step/mj_forward，不实例化原生 Backend/app。验证执行时上述三个物理入口被替换为抛错函数。原生源码、XML、资产、初态、运行实例均未修改，也没有新增物理循环。

主写 `backend/`、共享状态契约和本方证据；未修改 `frontend/`。平台网关仍不依赖 MuJoCo，编译工具与网关分别使用现有 native Python 3.10 和 gateway Python 3.14 环境，没有合并环境或安装依赖。

## 前端入口与明确差异

服务器回环 **`http://127.0.0.1:18942`**，网关 PID **397182**。这是远端服务器地址；前端服务器可代理到它。18941 PID1155600、native PID941842 保持不变。前端自行启用候选代理，不替换旧服务。

| 资源 | 18941 冻结服务 | 18942 候选 |
|---|---|---|
| GET `/api/v1/mobilecar/scene` | `unirobot-mobilecar-read-1` | `unirobot-mobilecar-geometry-1` |
| scene `data_source` | `live_native_http` | `live_native_http_with_verified_compiled_geometry` |
| mesh bytes / `sha256` | 原始 STL | 编译后顶点的 STL / 新摘要 |
| mesh `size_m` | 原生 mesh_scale | 固定 `[1,1,1]`，预处理已应用 |
| geom 位姿、body/joint 层级、axis、ID、RGBA | 原生编译值 | 完全保留 |
| geom group / collision | 原生默认值 | 实际编译 `geom_group` / 接触过滤参与标记；新增 `contype`、`conaffinity` |
| GET capabilities、snapshot | read-1 | **仍为 read-1，字段与语义不变** |
| Session Ready / 平台控制、录制、回放 | 未接通 | 未接通 |

mesh 资产新增字段：`coordinate_space="mujoco_compiled_mesh"`、`units="m"`、`mesh_preprocessing_applied=true`、`source_sha256`（原始 STL 摘要）、`source_mesh_name`（MuJoCo mesh 名称）。`asset_id` 不变；`uri` 仍指向当前网关的资产端点，但使用新的 `sha256` 查询参数。不要复用18941资产缓存或把旧摘要写死。

唯一正确的单个 geom 变换为 `p_body = R(geom.local_transform) * v_compiled + geom.local_transform.position_m`，之后使用既有 body 层级和实时模型关节状态。**不再应用 mesh_scale、mesh_pos、mesh_quat，也不额外旋转底盘、平移根节点或调整关节零位。** primitive 尺寸语义不变。

`collision = (contype != 0 or conaffinity != 0)` 仅表示参与动态接触过滤；不表示“碰撞专用外观”、当前发生接触或必然能与某对象碰撞，显式 contact pair 等规则仍由 native 决定。不能据此删除所有 collision=true 的可见几何。`group` 是原生编译组；可见性继续参考 RGBA/前端显示策略。例如 `chassis_collision` 的 group=3、contype=2、conaffinity=1、alpha=0；底盘外观 `base_link_visual` group=1、两个过滤位均0、alpha=1。后端不把 alpha=0 改成可见色。

## 真实请求与响应

以下命令在服务器执行：

```bash
curl --fail-with-body http://127.0.0.1:18942/api/v1/mobilecar/scene
curl --fail-with-body http://127.0.0.1:18942/api/v1/mobilecar/capabilities
curl --fail-with-body http://127.0.0.1:18942/api/v1/mobilecar/snapshot
curl --fail-with-body 'http://127.0.0.1:18942/api/v1/mobilecar/scene/assets/base_link?sha256=a04312293b54b7092e7fe947d82ae582f7d415eb5c352fc3e99b6f571021d1ae'
```

真实 scene 中的资产摘录：

```json
{
  "asset_id": "base_link",
  "uri": "/api/v1/mobilecar/scene/assets/base_link?sha256=a04312293b54b7092e7fe947d82ae582f7d415eb5c352fc3e99b6f571021d1ae",
  "sha256": "a04312293b54b7092e7fe947d82ae582f7d415eb5c352fc3e99b6f571021d1ae",
  "media_type": "model/stl",
  "coordinate_space": "mujoco_compiled_mesh",
  "units": "m",
  "mesh_preprocessing_applied": true,
  "source_sha256": "9eb685251829f79fb36a29c5bcafb7a8d6775eb6c9cae5e99a9451c633934223",
  "source_mesh_name": "base_link_mesh"
}
```

完整真实 envelope、mesh geom 位姿与来源见[真实样例](evidence/m1-geometry/m1-geometry-20261023T192202Z-cdfc7472e5de/report/real-geometry-sample.json)；完整 scene/capabilities/snapshot/OpenAPI 同目录保留。所有读取及错误禁止缓存，资产返回 `model/stl`、新摘要 ETag。

真实错误请求：未知 ID 使用 `.../assets/unknown?sha256=` 后接64个0，返回404：

```json
{"detail":{"code":"unknown_asset","message":"Unknown compiled scene asset","read_only":true,"session_ready":false}}
```

真实错误请求：有效 `base_link` 使用64个0摘要，返回409：

```json
{"detail":{"code":"asset_revision_changed","message":"Asset digest changed; reload the candidate scene manifest","read_only":true,"session_ready":false}}
```

新增409 `geometry_source_changed`：运行 run/generation/episode 或 native scene 摘要与导出不一致，拒绝返回旧网格；不回退原始 STL。此错误仅用合成测试验证，未为制造错误而改动真实 native。native断连仍503，读取中身份变化仍409 `native_identity_changed`。bundle/资产损坏使候选启动失败，不返回伪造成功。

## 来源与复现

- 源码 release：`/home/liaozhengyan/Desktop/uniRobotPlatform/releases/m1-geometry-20261023T192202Z-cdfc7472e5de`；31文件 aggregate `cdfc7472e5de3d86b7ca7f045715bf2917e4792df30996f5096dfe18c4fdeed6`。冻结源码清单包含当时的共享 catalog；之后本说明文档更新不改变该已验证源码身份。
- 编译输入：既有 native release `drvfix-20261019T044549Z-0a80415b2577` 的 `assets/landerpi/model/robot.xml`，32个递归 XML/mesh 输入分别散列，包含场景与物体；编译前后输入摘要不变。导出器只支持此模型的 include/mesh 路径结构，遇其他 file-backed asset 或目录重映射即拒绝，不是通用 MJCF 导出框架。
- 离线原生 `build_scene_manifest()` 结果与在线 `/api/v1/scene` **完整相等**，根XML/所有原始mesh摘要一致；候选保留所有body、joint、geom变换与对象ID。新增过滤位来自匹配的静态编译输入，不是在线接触真值。
- `geometry_provenance` 包含 compiler/version、runtime/resource身份、native_scene/model_inputs/compiled_scene/native_scene_builder/bundle 摘要。bundle摘要按排序键/紧凑JSON计算，计算时排除其自身 `bundle_sha256` 字段。`compiled_scene_sha256` 对应bundle中的scene，在网关重写资产URI之前计算，并非HTTP envelope或重写后data的摘要。bundle `275389464eee2f3de0c2ddf96ae85acbedfd382c496a589ec41a3662ee31d171`。
- 验证范围明确为 `static_compilation_matches_live_manifest_not_live_memory_or_contacts`。没有声称读取在线 C 内存或验证完整部署配置，因此仍保留 `deployed_content_verified=false`、`session_ready=false`，不能把这份几何校验作为控制授权或初态确认。

在服务器以 native 现有环境执行 `backend/tools/check_compiled_geometry.py`；导出示例（`$candidate_release`、`$native_release`、`$new_bundle_dir` 为操作员设置的上述冻结目录和一个全新输出目录）：

```bash
PYTHONPATH="$native_release/src" /home/liaozhengyan/Desktop/mobileCar/envs/g2a-py310-mujoco316/bin/python \
  "$candidate_release/backend/tools/export_compiled_geometry.py" \
  --native-root "$native_release" --model "$native_release/assets/landerpi/model/robot.xml" \
  --native-url http://127.0.0.1:8792 --output "$new_bundle_dir"
```

网关使用现有 gateway-py314 环境，在候选 release 中设置 `PYTHONPATH=backend/src`、`UNIROBOT_CATALOG=report/catalog.live.yaml`、独立 `UNIROBOT_DRAFT_DB`、`UNIROBOT_ALLOW_LAUNCH=0`、`UNIROBOT_GEOMETRY_BUNDLE=<candidate_release>/geometry`，运行 `python -m uvicorn unirobot.api:app --host 127.0.0.1 --port 18942`。**当前端口已有本候选进程时不重复启动，也不停止18941/native。** 实际进程/参数见[作业记录](evidence/m1-geometry/m1-geometry-20261023T192202Z-cdfc7472e5de/report/gateway-job.json)。

## 实际验证及限制

全部执行于服务器，未在本地运行测试/MuJoCo/浏览器：

- 既有50项读取/草案/API测试加3项候选测试：**53 passed**；保留一个既有 TestClient/httpx 弃用警告。[JUnit](evidence/m1-geometry/m1-geometry-20261023T192202Z-cdfc7472e5de/report/focused.junit.xml)
- 独立偏心四面体、非均匀缩放、90°旋转的编译/STL/body坐标检查：最大误差 `8.836669634102765e-9 m`；错误的raw STL+compiled pose组合误差 `0.1991931146966245 m`。断言物理入口不可调用。[数值记录](evidence/m1-geometry/m1-geometry-20261023T192202Z-cdfc7472e5de/report/geometry-fixture.log)
- scene、capabilities、snapshot真实GET均200；23个STL逐个GET并匹配摘要；真实404/409。过滤元数据、identity mesh scale、body/joint/geom位姿与ID保持检查通过。[HTTP报告](evidence/m1-geometry/m1-geometry-20261023T192202Z-cdfc7472e5de/report/live-read-check.json)
- native进程、run/generation/episode、录制状态未变；18941 OpenAPI字节完全一致，scene除retrieved_at之外相等。[冻结服务检查](evidence/m1-geometry/m1-geometry-20261023T192202Z-cdfc7472e5de/report/frozen-service-check.json)
- 大网格/原始native状态留服务器，本地只保留约39KB压缩的报告/来源摘要；[远端资产索引](evidence/m1-geometry/m1-geometry-20261023T192202Z-cdfc7472e5de/report/server-artifact-index.json)。

初次交付的前端接入范围为：新scene类型、编译STL URI、identity scale、真实group/过滤位、来源与错误展示，并用原有snapshot驱动Actual。正/侧/斜视、Ghost关闭时的整车装配与既有交互需由前端验证，回传结果见下节。资产能加载或数值检查通过不等于视觉验收。目标、控制权、录制、回放继续按[既有只读切片限制](backend-m1-read.md)执行；本轮不开放这些写入口。

## 前端集成回传（2026-10-23）

前端对话“Continue M1.1 前端”回传已完成集成。本方亲读其开发记录、`integration-summary.json`、`unit.json` 和 `geometry/geometry.json` 核对以下结果；**这些浏览器/视觉检查由前端执行，本方没有重新运行或独立复验截图。** 后端实现、接口、bundle与运行进程维持上述已验证版本，没有因此扩展功能。

- 前端 release `m1-front-geometry-20261023T192903Z-58a156740be8`，aggregate `58a156740be83a2879e5a1d2145f77d552d51f6682b1e3d318d6a2b048044276`；服务器预览18933/PID800217代理本方18942。来源 bundle 摘要与本记录一致；前端摘要记录18931/18932/18941/18942/native进程均保留。
- 前端记录服务器21项单元、30项只读浏览器、29项既有交互和23项装配/TCP检查通过；geometry-1字段、新资产摘要和过滤元数据已消费，compiled mesh不再重复缩放。
- 前端主智能体报告亲自查看Ghost关闭的车头、侧面与斜视截图，底盘水平，轮组/外壳/机械臂/夹爪装配完整。其数值报告最终真实TCP标记与渲染关节链误差 `1.694362330178007e-14 m`；持续TCP拖拽跨两次Actual更新和取消检查通过，joint4映射保留。
- 前端网络摘要记录261次API请求全部GET，native运行身份与录制IDLE保持；这些结果限定为**只读几何与交互集成**，不构成真实命令执行、Session Ready、录制或回放闭环通过，也不外推真人体验/GPU性能。

可核对来源：[前端开发记录](/home/liaozhengyan/.codex/worktrees/frontend-m12a/uniRobotPlatform/frontend/docs/development.md)、[集成摘要](/home/liaozhengyan/.codex/worktrees/frontend-m12a/uniRobotPlatform/frontend/reports/m1-front-geometry-20261023T192903Z-58a156740be8/integration-summary.json)、[装配与TCP证据](/home/liaozhengyan/.codex/worktrees/frontend-m12a/uniRobotPlatform/frontend/reports/m1-front-geometry-20261023T192903Z-58a156740be8/geometry/geometry.json)。服务器原始release在 `/home/liaozhengyan/Desktop/uniRobotPlatform/releases/m1-front-geometry-20261023T192903Z-58a156740be8`；本方未复制或改写前端证据。
