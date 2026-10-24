# 真实只读工作台：已接入与最小差距

此文件是前端交接记录，不定义第二套公共接口。权威语义仍在后端维护的 `docs/specs/30-contracts`，wire 以 backend `mobilecar_read.py` / `unirobot-mobilecar-read-1` 为准。

已接入 `GET /api/v1/mobilecar/scene`、`capabilities`、`snapshot`、`scene/assets/{id}?sha256=…`。适配层解 envelope/data 并比较 adapter/robot/runtime/resource/profile 身份；面板使用内部投影，后端无需返回 ViewSample。Actual、后端已有 Target、本地 Target/Ghost 分开；Owner 只读，所有执行资格仍为 false。world_links 是编译初态，无实时物体姿态。接口中的 media reference 不用于下载媒体。

| 仍需对齐的最小能力 | 输入/输出或语义建议 | 当前前端边界 |
|---|---|---|
| 版本化用户角映射 / TCP 几何 | 能力元数据中保留按 joint name 的 zero_model_rad、direction 和 TCP parent/local offset，并附配置/内容版本；例：joint4 `{zero_model_rad:-1.5707963267948966,direction:1}`，TCP `{body:"guide_rod_link",position_m:[-0.0030427614580541846,-0.0007270026737451543,0.01995871637761593]}`。具体路由与字段由后端维护，不要求新增聚合端点 | Actual 直接用 named model angles；本地预览暂用已固定参考 profile，只按已知模型匹配，不证明远端完整部署配置，未知模型禁用候选 |
| prepared Session / Start | 已验证快照、无运动绑定、显式Start、应用身份/初态确认 | Session不就绪；不用health、原生session或recording ready替代 |
| Target/plan/命令闭环 | 目标版本、Frame/自由度、有效计划身份、命令关联与Accepted/Rejected/执行终态 | native已有Target不视为本方回执；`command_id=null/tcp=null/preview=null`保留，本地线段不是轨迹 |
| Authority | 后端认可的owner/lease/scope和接管结果、过期/安全停止 | 原生owner仅观察，authorizes_caller=false；接管/执行禁用 |
| 相机媒体与真实观测 | frame/标定、source/capture/arrival时间、media reader与失效语义 | 只显示SensorState引用/quality，不把观察相机当RGB，不加载native_asset_uri |
| 录制/只读回放 | RESET应用身份、可靠开录、停车与finalize独立结果；Episode/segment复合身份和时间/媒体reader | 录制与播放禁用；监控时间不是采集轨迹或Episode回放 |

本轮不改 backend、公共契约或 native。上述元数据例子来自已固定参考配置，仅作为最小输入输出建议，未宣称后端已提供或完整配置已核验；控制/录制仍需后续授权与运行门控。

## 本轮几何候选协作

后端对话负责 `unirobot-mobilecar-geometry-1` scene 与编译资产，使用独立候选服务，旧read-1保持稳定；新增字段由其公共契约与类型维护。前端 `mobilecar-read.ts` 明确消费编译坐标标识、原资产身份和 geometry_provenance，拒绝缺失/歧义信息；mesh `size_m=[1,1,1]` 且不重复scale。contype/conaffinity/group/collision保留为后端原义，显隐仅消费RGBA。服务是否已通过本轮真实验证，以本方development记录和后端geometry交付记录为准。
