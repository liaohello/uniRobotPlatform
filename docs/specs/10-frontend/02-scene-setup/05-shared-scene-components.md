# Scene Setup 共享组件与任务变体

规范 ID：`FE-SCENE-COMPONENTS` · 责任层：前端 · 版本：V0.6（2026-10-22）

状态：组件边界与交互是本轮设计基线建议；产品未因写入规范而实现或验收。当前来源：[S16](../../90-governance/sources/S16-mobile-first-spec-repair.md)，原图来源：[S15](../../90-governance/sources/S15-scene-setup-first-loop.md)。

[功能包](README.md) · [任务字段](02-task-template-configuration.md) · [三图页面](../page-designs/02-scene-setup.md) · [配置契约](../../30-contracts/07-task-scene-experiment-config.md) · [首条闭环](../../00-overview/10-first-task-closed-loop.md)

## 一次开发、配置驱动和扩展

下表组件名是职责名称，不冻结框架或第三方库。一次开发指共享实现和状态语义，可按职责拆模块，不要求一个巨大组件。

| 组件 / 职责 | 共用一次 | 由任务/能力驱动的变化 | 当前边界 |
|---|---|---|---|
| `WorkspaceShell` / `ContextBar` | 导航、项目/机器人/场景/任务上下文、连接和草案状态 | 资源选项、任务名称 | 同一宿主的三图不重复实现 Shell；不同轻宿主可选择性复用 |
| `SetupStepper` | 资源→任务→Profiles→验证→创建的引导 | 完成条件从配置/验证派生 | 可直接返回已完成步骤；访问过不等于完成 |
| `SceneHierarchy` / `SelectionModel` | 搜索、选择、可见性、稳定对象 ID | 机器人部件、地图/物体、目标与托盘角色 | 与视口/Inspector 同一选中源；选择不发控制 |
| `AssetPicker` | 已有资源搜索、兼容过滤、加载/失败状态 | 地图、桌面对象、机器人白名单 | M1 先选择现成且真实支持的预设；任意导入/网格编辑后续 |
| `ViewportFrame` / `ViewportToolbar` | 主视图容器、切换、相机、全屏、选择工具 | Map2D、Tabletop2D、Scene3D 插件及工具集合 | 三维渲染可用能力决定；无流显示占位原因 |
| `TaskConfigRenderer` | schema 字段渲染、分组、单位、错误定位 | 五类任务的字段/默认/条件/校验 | 由 task type/version 选 schema，非固定全字段大表单 |
| `ObjectInspector` / `PoseFields` | 对象角色、坐标/单位、只读/错误反馈 | 位姿、初态、目标、托盘/区域允许属性 | 最终写权限由契约裁决；不改源资产/运行态 |
| `ProfileSummary` / `ProfileVersionPicker` | Operator View、Policy Observation、Recording 三卡与版本摘要 | 流/相机/频率、缺失能力 | View 只读；编辑走该资源的权威保存路径；不适用的观测卡标未使用，Execution 独立展示 |
| `CameraStrip` | 预览卡、时间/分辨率/流状态 | 导航/主摄像头/左右腕等相机列表 | 由 Profile 和真实流驱动，示例媒体显示 Demo |
| `ValidationPanel` | 未验/检查中/通过/失败/过期、错误列表与版本 | 检查项、覆盖范围和证据 | unsupported/not_checked 明示，静态 UI 不授予真实 Passed |
| `DraftSummary` / `DraftActions` | 名称/描述/版本、保存、验证、创建 | 保存/验证/就绪决定操作可用性 | 一个权威保存入口，无重复 Save Draft |
| `MapWaypointEditor` | 导航任务共用地图变换和点编辑逻辑 | PointGoal 目标、Route 点序，ObjectNav 只显示获准内容 | 单独适配模块，绑定地图版本；热重规划后续 |
| `ManipulationTaskAdapter` | 共用对象/区域选择、桌面位姿编辑 | 单臂目标/抓取，双臂 source/staging/goal 及模式 | 双臂同步、力控制和任意资产生成按能力后续接入 |

## 单一状态与组件接口

`ExperimentDraftStore` 是宿主注入的某个 draftId/revision 的状态容器，持有固定资源引用、实例覆盖、Profile 引用和验证回执。不同 HostApp/草案不共享可写单例；同一草案跨宿主保存仍使用服务端修订检查。SceneDraft 是独立资源草案，普通物体移动写 ExperimentDraft 覆盖，不修改 SceneVersion。Route/Profile 资源保存权威也不因宿主复制。持久化、实际机器人状态和控制权由服务端负责。

HostContext 提供当前 backend/session/draft 引用、能力、权限、订阅及命令服务；组件通过输入/事件使用它们，不自行读取全平台全局 store。选中/相机/布局按视图实例持有；宿主卸载清理自身订阅和持续输入，不重置其他 Session。原生技术栈不相容时优先共用协议/适配，不为组件复用重写已有实验工具。无需建立 HostApp 插件平台。

| 输入/事件概念 | 最小语义 |
|---|---|
| 组件输入 | `context + draft + selection + capabilities + permissions + validation + pending/error` |
| `SelectionChanged` / `ViewChanged` | 稳定对象 ID/纯展示状态，不修改执行参数 |
| `EditRequested` | objectId、fieldPath、value、frame/unit、baseRevision；统一白名单和 schema 校验后应用 |
| `TaskTypeChangeRequested` | 目标 type/version；脏草案先保存/放弃/取消，隐藏参数不参与新 payload |
| `ProfileViewRequested` / `ProfileEditRequested` | Profile kind、id、version；查看同一详情或进入单一编辑器 |
| `ResourceVersionAdoptRequested` | 明确资源种类与固定新版本；采用影响执行的版本后 stale |
| `DraftSaveRequested` / `ValidationRequested` | 当前修订与依赖身份；异步返回的旧结果不覆盖新草案 |
| `SessionCreateRequested` | 仅已验证 snapshot、预期执行修订/指纹及幂等键；成功回执后进入该宿主的运行视图 |

状态转移、权限矩阵、fingerprint 与 Stale 的唯一规则在 [配置契约](../../30-contracts/07-task-scene-experiment-config.md)。组件消费它，不另订一套“任何 UI 改动都失效”的规则。保存草案不要求验证通过；创建 Session 必须通过真实服务端验证且当前就绪。新版本保存不自动改绑运行引用。

## 能力和未实现反馈

组件区分 `available / unavailable / unknown`，附适配器与版本、原因；编辑器预览可在 Demo 数据下展示，真实验证/创建/训练仅在所需能力 available 时启用。unknown 不能推断为可用。稳定 UI 可保留禁用入口并解释“尚未接入/当前离线/不支持”，勿用静态勾选代替结果。

ObjectNav 搜索/语言输入、完整 VLN/VLA、点云算法、物理可达/碰撞认证、移动抓取联动、双臂空中同步交接和力反馈均须独立实现/声明后开放。三图的摄像头规格、6-DoF、力阈值等不作为真实机器人能力；资源描述和实际适配器决定可用工具。

## 三图共用修正

1. 顶部统一显示 Project / Robot / Scene / Task；图一的 Task Preset 与图二三 Task Type 指向同一版本化任务定义，不另成平行对象。
2. 步骤条按资源有效、必填完整、Profile 完整、当前验证、Session 创建五个事实派生。草案/已保存和验证状态独立；Failed/Stale 后第 4/5 步不得继续显示完成。
3. 图一重复 Save Draft 收敛一个保存操作；Save Route Version 仍是独立资源保存，采用到配置需明确动作。
4. 三卡均为版本摘要与 View；操作员视图的纯展示变化不使执行验证失效。图中 Passed/“2 min ago”取真实服务端回执和时间。
5. 地图路线、近场抓取 3D、双臂桌面 3D 是同一视口容器的变体。Camera Strip/3D Preview 按任务布局可折叠，不能改变 Policy/Recording 输入。
6. 从 Scene Setup 创建 `prepared` Session 后进入当前宿主的 Run/轻量运行视图；完整平台内 Simulation 承担在线控制，不在 Setup 混入在线动作。不同宿主仍服从同一后端 Session/控制权，不各自成为物理推进者。

验收：[TEST-CONFIG-001～007](../../40-verification/06-scene-setup-first-loop.md)。当前 M1 mobileCar 四步闭环、M2 bimanual 复用分别验收，训练后续，见 [当前开发基线](../../00-overview/10-first-task-closed-loop.md)。
