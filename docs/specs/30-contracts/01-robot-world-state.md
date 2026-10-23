# Robot / World State 契约草案

规范 ID：`CT-STATE` · 责任层：共享契约 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-031](../../设计过程与Specification总册_20261021.md#doc-031) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.7｜更新日期：2026-10-23（America/Los_Angeles）；通用字段草案原文保留。

状态：通用部分为接口概念草案；下文 mobileCar read v1 是已实现的 HTTP 读取子集，不代表 Session/控制/录制/回放已接通。

来源：S02、S03、S05（详见[来源档案](../90-governance/06-sources.md)）

关联需求：[REQ-CONTRACT-001](../indexes/05-requirements.md#req-contract-001)

## 目的

使在线 3D、Inspector、传感器、录制和回放能引用同一机器人身份与时间，而不是各面板自行解释数组。

| 字段组 | 建议内容 |
|---|---|
| 身份 | schema_version、session_id、robot_id、arm_id、稳定 joint/link/body ID |
| 时间 | sim_time、source_time、sequence、状态有效性 |
| 本体 | joint actual position/velocity；其他状态按实际能力 |
| 目标 | 单独的 joint target / TCP target 与关联 command_id |
| 变换 | Frame ID、世界/机器人/相机变换、单位与约定 |
| 控制 | 每个控制范围的 owner、模式、接管状态 |
| 物体 | 可供 3D 与回放使用的世界实体位姿 |

Actual、Target、Preview 分开；是否记录接触、力矩和加速度由任务/记录配置决定。缺失或过期字段应有明确状态，而不是以零填补。

当前未选择 WebSocket/HTTP、序列化形式、字段拼写、压缩、广播频率，也未声明上表是可直接调用的 API。字段草案只有在与既有后端核对后才能冻结。

<a id="mobilecar-read-v1"></a>
## mobileCar read v1：已实现的只读工作台子集

本节将上面的通用语义落实到当前 mobileCar HTTP 适配，版本 `unirobot-mobilecar-read-1`。仅以下读取接口已经实现；其他机器人、通用命令信封、prepared/Start 与历史服务继续按各主责规范推进。完整类型在 `backend/src/unirobot/mobilecar_read.py`，由 `/openapi.json` 提供；[后端交付记录和真实样例](../../backend-m1-read.md)给出冻结输入与验证范围。

| GET 路径 | 返回的 `data` / 额外字段 |
|---|---|
| `/api/v1/mobilecar/scene` | 原生 SceneManifest 的显式字段；mesh URI 重写为本平台资产端点；额外 `objects` 提供 body/joint/geom 选择ID |
| `/api/v1/mobilecar/capabilities` | 实际原生能力、关节顺序和SI限位、传感器声明；平台 commands/recording/replay available 独立为false |
| `/api/v1/mobilecar/snapshot` | `time`、`arm_joint_names`、`actual`、`target`、`preview`、`sensors`、`authority`、`recording`、`safety_latched`、原生 `task_phase` |
| `/api/v1/mobilecar/scene/assets/{asset_id}?sha256={digest}` | 当前清单中的STL字节，摘要匹配后返回；未知资产404、修订不同409、字节摘要不符502 |

JSON envelope：`schema_version`、`data_source=live_native_http`、adapter/robot ID、`retrieved_at`、`runtime_identity={run_id,backend_generation,episode_id}`、`resource_identity={contract_version,model_id,model_sha256,scene_id}`、`interface_profile`、`recording_required_for_motion`。`read_only=true`、`platform_session_id=null`、`session_ready=false`；看到native运行不表示平台已创建/开始Session。

`resource_matches_pin` 只比较model ID、根XML摘要与scene ID；`deployed_content_verified=false`。它不能代替完整配置/资产校验或 readiness；当前真实读取 profile 为g4a1-1.0，不是固定G1的g2a-1.0。

Snapshot 的明确投影：

- `actual.base`：world_sim位置m/姿态xyzw、base_link速度m/s与rad/s、停止/锁存；`actual.arm`：用户角/模型角rad、速度rad/s、力矩Nm、边界与坐标状态；`actual.gripper`：宽度m与模型驱动角rad；`actual.tcp`：world_sim位置m/姿态xyzw/原生残差。
- `actual.model_joint_positions_rad`：原生名称→模型角，用于模型关节映射；臂数组顺序为 `arm_joint_names`，不能把用户角与模型角的零位混用。
- `target.base_velocity={frame_id:base_link,vx_m_s,vy_m_s,wz_rad_s}`；另含用户/模型关节目标、夹爪宽度/驱动角。它只描述native持有的目标，不代表新提交已受理；`target.command_id=null`、`target.tcp=null`，`preview=null`，缺失项不伪造。
- `time` 原样保留 episode起始/backend单调时间、sim时间、feedback时间、wall UTC、clock_id与control_tick_id。`retrieved_at`是网关收取时间。读取前后health身份或snapshot身份不一致返回409 `native_identity_changed`；跨HTTP调用不保证原子性，前端遇运行/资源身份变化应重载并作废旧目标。
- `sensors` 保留原生sample/stream、measurement/arrival/capture/feedback引用、fresh/quality等；原生SensorState没有Frame，明确`frame_id=null`，不得从link4安装关系伪造光学Frame。`native_asset_uri`是原生引用，`sensor_media_status=not_exposed`，本切片未提供相机媒体/完整Observation载荷。
- `authority` 是native Owner/session/kind的观察投影，`authorizes_caller=false`、`lease_status=not_exposed`；不生成控制权、lease或接管成功。`recording`是原生状态/segment/ready/counters/error，不表示平台已接通录制入口。

对象ID在当前编译清单中稳定，使用 `body:{URL编码名称}`、`joint:{URL编码名称}` 和 `geom:{URL编码body}/{URL编码geom}`；调用方同时保留adapter/运行/资源身份。world_links是编译初始布局，以 `world_pose_semantics=compiled_initial_layout_not_live_object_state` 标明，不作为在线物体真值。mesh字节只从已配置native服务的固定资产路径取得，外部URI不透传。

SceneManifest几何参数保留原生renderer语义；mesh的`size_m`数组实际表示各轴缩放，不能把所有geometry尺寸数组都解释成普通物体的长宽高。

读取使用网络边界类型检查、有限数值/向量长度/关节顺序检查，不以默认零补状态。未知native字段被丢弃，默认不返回diagnostics、contact_summary、plan或Oracle；该投影不冒充受限Policy Observation API。所有mobileCar读取禁止缓存，断连503、外部响应不兼容502、身份变化409，错误提供`detail.code/message`，不附原始响应体；具体样例与限制见交付记录。

## 关联文档

- [机器人能力与适配边界](../00-overview/06-robot-capabilities.md)
- [时间、坐标系与命令生命周期](04-time-frames-units.md)
- [控制与干预命令契约草案](02-control-intervention-commands.md)
- [Episode、采集、事件与标注契约](03-episode-events-annotations.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)
