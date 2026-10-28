# Scene Setup 任务配置与实验配置流程

规范 ID：`FE-SCENE-TEMPLATES` · 责任层：前端 · 版本：V0.7（2026-10-24）

状态：详细设计草案；本轮字段、默认值和校验行为是建议设计基线，不表示逐字段已由用户确认。Waypoint 在 Scene Setup 创建/编辑/保存为用户已确认范围；M1.3 PointGoal/Waypoint 必填 yaw 以 S18 补充。后端资源 API 已有候选，前端页面实现和端到端验收未执行。

当前范围来源：[S16](../../90-governance/sources/S16-mobile-first-spec-repair.md)；三图来源：[S15｜Scene Setup 首条闭环与三图](../../90-governance/sources/S15-scene-setup-first-loop.md)、[S10｜Waypoint 范围确认](../../90-governance/sources/S10-waypoint-scope-confirmation.md)；本切片字段来源：[S18｜版本化地图与带朝向 Waypoint 路线切片](../../90-governance/sources/S18-navigation-map-route-slice.md)。

[功能包](README.md) · [共享组件与交互契约](05-shared-scene-components.md) · [PAGE-02 三任务图稿](../page-designs/02-scene-setup.md) · [共享配置契约](../../30-contracts/07-task-scene-experiment-config.md)

关联需求：[REQ-SCENE-003](../../indexes/05-requirements.md#req-scene-003)、[REQ-TASK-001](../../indexes/05-requirements.md#req-task-001)

## 配置流程

选择 Project / Robot / Scene → 选择 Task Type → 按该类型 schema 配置任务参数 → 编辑 Robot Initial State、Task Objects、Success Criteria → 选择独立的 Operator View、Policy Observation、Execution、Recording Profiles → 校验并保存草案 → 显式创建 Simulation Session。Profile 卡片只在自己的配置工作区编辑；Scene Setup 内仅显示摘要与跳转。

共享页面由任务类型决定字段、地图或三维视口工具、对象角色和必需能力。未激活任务的专属参数既不显示，也不参与序列化、校验或运行；切换任务不能在 payload 中残留上一个类型的值。

## 任务类型 schema（建议基线）

字段名是契约语义建议，不是已冻结 API 键。距离以 m，角度以 rad（界面可用度显示），时间以 s，频率以 Hz；坐标须附 Frame，离散枚举须由模板版本约束。默认值只在 UI 草案创建时显式写入；缺省与用户显式值应可区分。

### 共用配置区

| 字段 / 分区 | 类型与默认 | 显示/校验 |
|---|---|---|
| Project / Robot / Scene / Task | 固定资源 ID/version；仅一个兼容项时可显式预选 | 始终显示；引用存在、权限允许、资源/任务能力匹配 |
| Configuration Name / Description | string；建议由任务名称生成可编辑名称，描述默认空 | 名称去除空白后非空；描述可选，二者为元数据不影响验证 |
| Robot Initial State | root pose + joint/gripper values + Frame；从所选模板显式加载 | 仅允许字段可编辑；有限数值、维度、关节/夹爪限位；固定底座 root 只读 |
| Objects | stable object refs + pose/role；模板布局为默认 | 由当前任务角色过滤；引用存在、Frame/几何可解释、允许位姿/数量范围 |
| Operator View / Policy Observation / Recording | 适用时固定 Profile ID/version；兼容项唯一时可显式预选 | 三张摘要按用途显示；纯人工未用算法时 Policy Observation 标未使用，录制时 Recording 必需，禁止以 UI 布局替代实际输入/记录 |
| Execution / Action Space | 固定 recipe/schema 引用；M1 优先现有 mobileCar 人工遥操作 | 来源已接通、权限/IO 一致；未接通的专家/主臂等禁用并解释，不制造示教事实 |
| Execution allowed_sources / initial_source | source enum[] / enum；由已选 native recipe 显式给出 | M1 仅开放真实接通的来源；Run 只选快照允许者，变更未声明来源需改配置重验；不用 Expert 占位 |
| Seed | integer；从已选 recipe 初始化，无默认时要求显式选择 | 任务需要重现随机化时显示并纳入执行指纹；不以元数据排除 |
| Success / Termination | task criteria refs + timeout/failure 配方 | 仅启用模板已提供的判定器；采集任务可无自动成功评分，记录结束原因/完整性即可，不以缺评分阻止 M1 |

各任务数值必须有限，拒绝 NaN/Infinity。小于/大于边界、缺引用和单位转换都在 schema/服务端校验；上限只有在模板或机器人明确声明时才显示，不虚构设备约束。

### `navigation.point_goal`

| 字段 | 类型 / 单位 | 显示条件 | 建议默认与校验 |
|---|---|---|---|
| `map_ref` | MapReference | 始终 | 当前 Scene 兼容地图；必填且地图版本/Frame 可解析 |
| `goal.pose.xy` | Vec2 / m，map frame | 始终 | 不自动填成机器人当前位置；必填、位于地图范围且非已知障碍 |
| `goal.pose.yaw` | Angle / rad | 始终（本次 S18） | **必填**，有限值，从 map +X 向 +Y 为正，归一化到 [-π,π)；缺字段/null 报错，显式 0 合法；不暗补 0 |
| `goal.position_tolerance` | number / m | 始终 | 来源为 Task Template/导航配置；建议 0.30；>0，且不大于可配置上限 |
| `goal.yaw_tolerance_rad` | Angle / rad | 声称朝向验收时 | 来源为 Task Template/导航配置；本切片无默认值；未配置时朝向验收标 unsupported，不假定通过 |
| `termination.max_duration` | number / s | 始终 | 300；>0 |
| `termination.on_failure` | enum | 始终 | `terminate_episode`；必须属于模板枚举 |
| `target_visibility` | policy / operator / evaluator channel refs | 始终 | PointGoal 可按任务协议提供目标坐标；三通道分别声明，不从 UI 可见性推导 |

校验：地图可用/匹配、机器人定位与底盘导航能力可用、目标不在越界或静态障碍格、目标 Frame 明确。点位预检不保证整条路径可达；后端拒绝须显示原因。

### `navigation.waypoint_route`

| 字段 | 类型 / 单位 | 显示条件 | 建议默认与校验 |
|---|---|---|---|
| `map_ref` | MapReference | 始终 | 当前兼容地图；必填并锁定版本引用 |
| `route_ref` | RouteVersionRef(id, version) | 始终 | 正式引用固定版本；内联编辑可暂挂 draft-only pendingRouteDraftRef，发布/验证前必须保存并显式采用；绑定相同 map/version/frame |
| `stop_condition` | enum | 始终 | `reach_final_goal`；枚举值须被模板支持 |
| `goal.position_tolerance` | number / m | 始终 | 0.30；>0 |
| `termination.max_duration` | number / s | 始终 | 300；>0 |
| `termination.on_failure` | enum | 始终 | `terminate_episode` |

Route 编辑字段（稳定 waypoint ID、顺序、map-frame XY、**必填 yaw**）由 [Waypoint 编辑器](04-map-waypoint-editor.md) 负责；yaw 缺失必须报错，显式 0 合法。显示编辑器仅当底盘/地图能力存在；保存生成不可变版本，不启动导航。路线至少 1 个可执行点，ID 唯一，顺序连续；未知/障碍点作为校验错误，不能因 UI 保存而静默跳过。

### `navigation.object_nav`

| 字段 | 类型 / 单位 | 显示条件 | 建议默认与校验 |
|---|---|---|---|
| `map_ref` | MapReference | 始终 | 当前兼容地图；必填 |
| `goal.semantic_query` | string 或 category ref | 始终 | 空；必填，按模板允许词表/分类校验 |
| `goal.instance_ref` | SceneObjectRef | 仅 evaluator ground truth / 布置编辑上下文 | 不提供给 policy observation；可选，通道隔离 |
| `goal.approach_distance` | number / m | 始终 | 0.40；>0，与平台任务定义一致 |
| `goal.position_tolerance` | number / m | 当模板采用几何接近判据 | 0.30；>0 |
| `termination.max_duration` | number / s | 始终 | 300；>0 |
| `termination.on_failure` | enum | 始终 | `terminate_episode` |

校验：策略有获准的语义目标观测/语言输入与底盘能力；目标描述由策略可见通道输入，实例真实位姿仅可供布局/评估通道。未实现感知、搜索、语义输入能力时标记“后续扩展”并阻止创建该任务 Session。

### `manipulation.near_field_grasp`

| 字段 | 类型 / 单位 | 显示条件 | 建议默认与校验 |
|---|---|---|---|
| `target_object_ref` | SceneObjectRef | 始终 | 无隐式首对象；必选且引用可抓取对象；只读资产也可作为任务目标 |
| `grasp_type` | enum: top/side/auto | 始终 | `top`；机器人/模板须声明支持 |
| `approach_direction` | enum 或 Vec3(unit) | 始终 | `auto_top`；显式向量为单位向量且方向可达 |
| `grasp_height_offset` | number / m | 始终 | 0.00；有限值，范围受目标/夹爪几何约束 |
| `pregrasp_distance` | number / m | 始终 | 0.10；≥0 |
| `gripper_width` | number / m | 夹爪支持开口设置时 | 由 Robot Configuration 可用开口初始化；在夹爪范围内 |
| `use_base_navigation` | boolean | 具备移动底盘时 | `false`，首版固定底盘；仅导航/停靠适配器支持时允许启用并显示 `approach_distance`，建议 0.40 m，>0 |
| `avoid_collisions` | boolean | 具备碰撞检查能力时 | `true`；无该能力显示 unsupported 并阻止要求它的配置 |
| `termination.time_limit_enabled` | boolean | 始终 | `true` 为首版建议，与图中关闭示例不同；关闭需模板支持无时间终止 |
| `termination.max_duration` | number / s | time_limit_enabled=true | 60；>0；关闭后不把隐藏旧值当有效终止条件 |
| `success.goal` | enum: lift/place | 始终 | `lift`；place 仅在放置适配器支持时开放 |
| `success.lift_height`, `success.hold_duration` | number / m、s | success.goal=lift | 建议 0.05 m / 0.5 s；>0，由任务评定器在所声明参考面和稳定条件下检查 |
| `goal_region_ref` | SceneRegionRef | success.goal=place | 必填且与目标对象不同，目标区域几何和放置判据可解析 |
| `success.criteria` | criteria ref[] | 始终 | 至少包含 grasp/lift 或模板定义判据；不以 UI 勾选代替可执行判据 |

校验：机械臂/夹爪及所需 IK/规划、目标几何、台面/抓取位姿可达性与观测流按 Profile 能力校验。图片中的 RGB-D、点云、数值与 Passed 状态仅是参考稿字段示例，不代表已接入。

### `manipulation.bimanual_transfer`

| 字段 | 类型 / 单位 | 显示条件 | 建议默认与校验 |
|---|---|---|---|
| `active_arms` | arm-ref[] | 始终 | 由双臂机器人能力选中左右臂；至少两只受支持手臂 |
| `source_arm_ref`, `receiver_arm_ref` | arm-ref | 始终 | 从明确的任务 recipe 初始化；必须不同且属于 active_arms，不从左/右复选框或 UI 摆放推断控制分工；所选双臂配方恰好两臂 |
| `target_object_ref` | SceneObjectRef | 始终 | 必选且唯一；不隐式挑选 |
| `transfer_mode` | enum: tabletop_transfer/direct_handover | 始终 | `tabletop_transfer`：先放公共区，再由另一臂拾取。图中 Direct Transfer 语义未定，作为 direct_handover 后续占位，不映射为原项目 direct 单臂分类 |
| `source_side`, `goal_side` | SceneObjectRef | 始终 | 无自动绑定；须为不相同、角色兼容的源/目标托盘/区域 |
| `staging_region_ref` | SceneRegionRef | transfer_mode=tabletop_transfer | 必填，需源臂可放、目标臂可取；引用现有模板公共区，不默认当成 source/goal 托盘 |
| `object_count` | integer | 始终 | 1；转运接入按已选配方限制数量，非 mobileCar M1 门槛。多物体扩展需 target_object_refs 列表与兼容配方，数量不超过已选目标数 |
| `object_layout` | enum/template ref | count > 1 | `line_tabletop`；仅当该布局受模板支持 |
| `constraints.avoid_arm_collision` | boolean | 双臂碰撞检查能力可用时 | `true`；缺能力不得显示为通过 |
| `constraints.min_arm_distance` | number / m | avoid_arm_collision=true | 0.10；≥0 |
| `constraints.synchronized_handoff` | boolean | `transfer_mode=direct_handover` 且支持同步执行时 | `false`；开启才显示 sync threshold，建议 0.20 s，>0；tabletop_transfer 使用顺序事件，不默认同步 |
| `constraints.maintain_grasp_stability` | boolean | 有接触/夹持反馈时 | `true`；缺反馈时不可宣称可验证 |
| `constraints.grasp_force_limit` | number / N | 机器人支持力反馈/限制时 | 由夹爪上限给出能力默认；>0 且不超设备范围 |
| `success.criteria` | criteria ref[] | 始终 | grasp source → stage/release → receive → placement；每个阶段有受支持判据 |
| `termination.max_duration`, `termination.on_failure` | number/s、enum | 始终 | 先用选定任务 recipe 的显式默认，无已核实默认则留空待选；时限>0，失败默认 terminate_episode |

校验：左右臂/夹爪、目标和 source/staging/goal 区域、动作范围、所选 transfer mode 及双臂同步/碰撞检查能力须匹配；目标初态满足所选源区域配方，source arm/receiver arm 的放取分工可解析。图片中的 SO101、相机布局、阈值是设计示例，不证明对应机器人或算法已接入。

## 统一校验与任务切换

1. 校验目标是完整 Experiment Configuration Snapshot：Scene/Robot/Task schema 与 revision、对象初态、各独立 Profile revision、能力清单版本和路线版本（如适用）。
2. 未知 schema 字段、错类型/单位、缺必填、范围错误、引用失效、能力缺项为阻断错误；可复现但不影响任务定义的非必需传感器缺失可作为警告，模板不得将阻断项降级为警告。
3. 切换 Task Type 若当前有未保存修改，先提供保存、放弃、取消。保存允许不完整旧草案，不要求验证通过；放弃只放弃该 draft 的未保存更改。确认切换后构建新类型专属配置，不把隐藏值带入新 payload。返回原任务可重新加载其已保存 draft revision。
4. 影响运行的执行修订/依赖变化即 Stale；名称、纯显示 Operator View 等按公共契约排除。可只重验受影响依赖，但最终验证快照须完整绑定同一依赖集。
5. Session 仅可由显式创建动作提交已验证快照；服务器返回 Session 引用/接受回执后才能导航到运行页。校验本身、保存草案、切页面不创建 Session、不启动机器人动作。

校验状态、Stale 和快照由 [共享配置契约](../../30-contracts/07-task-scene-experiment-config.md) 唯一主责，[共享组件](05-shared-scene-components.md) 负责呈现。后端资产和 Session 接入分别见 [Scene Builder](../../20-backend/01-session-scene/03-scene-builder-assets.md)、[Session 生命周期](../../20-backend/01-session-scene/01-session-lifecycle.md)。

任务注册描述使用本页语义类型，现有目录枚举通过适配映射：point_goal→NAV-POINT、waypoint_route→NAV-ROUTE、object_nav→NAV-OBJECT、near_field_grasp→MOBILE-GRASP、bimanual_transfer/tabletop_transfer→BI-TABLE-TRANSFER；direct_handover 仅为未来 BI-HANDOVER 候选，不能以名称相似自动转换 BI-DIRECT。映射版本进入验证依赖。

## 配置对象边界

SceneVersion 保存基础资产/对象默认布局，SceneDraft 编辑资源；ExperimentDraft 固定版本引用并保存本次允许覆盖。Task Template 给出 schema，Profile 按用途引用，解析/验证后固定为 ValidatedSnapshot。普通任务配置编辑不反写源 Scene。唯一规则见共享契约；当前 mobileCar 仅开放原生支持的预设/字段，三图全部参数不作为 M1 前置。
