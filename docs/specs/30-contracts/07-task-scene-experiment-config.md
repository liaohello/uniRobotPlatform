# Scene、Task Template 与 Experiment Configuration

规范 ID：`CT-EXPERIMENT-CONFIG` · 责任层：共享契约 · 版本：V0.6（2026-10-22）

状态：详细设计基线建议；字段名和示意数据不代表现存 API。三图是 UI Reference；产品实现及验收未执行。

来源：[S16](../90-governance/sources/S16-mobile-first-spec-repair.md)、[S15](../90-governance/sources/S15-scene-setup-first-loop.md)、[S08](../90-governance/sources/S08-frontend-ia-analysis.md)、[S09](../90-governance/sources/S09-unified-development-reuse-analysis.md)。

[上级目录](README.md) · [总索引](../README.md)

关联需求：[REQ-SCENE-003](../indexes/05-requirements.md#req-scene-003)、[REQ-SCENE-005](../indexes/05-requirements.md#req-scene-005)、[REQ-TASK-002](../indexes/05-requirements.md#req-task-002)

## 资源、草案与运行快照的关系

| 对象 | 责任 | 身份与版本草案 |
|---|---|---|
| Scene / SceneVersion | Scene 是逻辑资源；SceneVersion 固定基础环境、对象身份和默认布局 | 固定 id/version、asset refs、稳定对象 ID；已发布内容不可覆盖 |
| SceneDraft | 编辑基础场景资源和默认布局 | 独立草案修订，保存/发布创建新 SceneVersion；不等于本次实验初态 |
| Robot Configuration | 机器人、关节/执行器、传感器与安装 | 模型、映射、标定和能力版本 |
| Task Template | 任务要做什么以及允许的能力 | task type/version、目标语义、成功/失败判据引用 |
| Experiment Configuration / ExperimentDraft | 本次实验配置及其可编辑草案 | 引用固定资源版本、允许的实例初态覆盖、seed、执行与采集选择；保存配置版本不改 SceneVersion |
| ExperimentDraftStore | 宿主内某个实验草案的前端状态容器 | 注入 draftId/revision 和服务；不是另一种落盘配置或源场景 |
| ValidatedSnapshot | 已解析、通过所声明检查的不可变执行配置 | 固定 resolvedConfig、依赖内容/摘要及验证身份；Session/Episode 的配置权威 |

同一 Scene 可绑定不同任务，同一任务可用于不同初态。资源引用固定 `(id, version)`，不使用 `latest` 表示已验证依赖；保存新版本不修改旧引用。精确传输、存储与端点在接入时固定。

### 写入归属与解析顺序

1. 加载固定 SceneVersion 的对象 ID、资产引用和基础布局，以及 Robot Configuration 的模型/标定/初态默认。
2. Task Template 默认只补充未定义的允许字段；不隐式覆盖基础资源已明确的布局/模型。载入旧配置时不因新默认值改变历史内容。
3. 按稳定 objectId/fieldPath 应用 ExperimentDraft 的显式实例覆盖。只有 schema/资源白名单允许的位姿、初态、角色和实例数量可写；质量、惯量、源网格/碰撞、机器人限位/映射/标定与 Profile 定义不由实例覆盖改写。未知字段或对象 ID 拒绝；获准新增实例必须显式选资产并获得新实例 ID。
4. 若任务启用随机化，解析时按固定 seed/配方生成允许字段并保存实际结果；默认不覆盖显式实例值，确需覆盖必须由字段规则明示。不得在 Session 开始或回放时悄悄重新抽样。
5. 服务端验证解析后的完整配置，固定为 ValidatedSnapshot；快照同时保存来源版本、覆盖值及最终值/内容引用，不能只保留一串失效后无法读取的资源名。

普通 Scene Setup 的物体移动写 ExperimentDraft 覆盖。只有明确“编辑基础场景/保存场景新版本”才写 SceneDraft；该操作不自动改绑其他实验。清除覆盖恢复该配置所引用版本的默认，而非最新 Scene。运行实际状态、录制起始 actual snapshot 与配置期初态分别记录，不反写 SceneVersion。

## HostApp 与唯一性的作用域

HostApp 是承载任务控制台或专项工具的应用入口，不是仿真实例、物理推进者或用户账号。可有平台宿主、视觉/IK 轻量宿主，不要求固定三个宿主或先实现通用插件框架。

| 作用域 | 权威与隔离规则 |
|---|---|
| 宿主/视图实例 | 导航、布局、选中、相机和订阅生命周期各自持有；组件通过输入/事件和服务注入工作，不导入共享可写单例 |
| 实验草案 | 每个 draftId/revision 只有一份被接受的内容；store 由宿主按草案实例注入。同一草案多窗口/宿主保存依然走服务端 baseRevision 冲突检查 |
| 资源 | 已发布 Scene/Profile/Route 版本的内容权威与编辑保存路径不按宿主复制；多个界面可复用同一编辑组件，但不能有相互覆盖的第二份资源定义 |
| Session/运行实体 | 后端统一裁决实际状态、执行器范围 Control Owner/租约与物理推进责任；多个宿主访问同一实体不各自获得控制权 |

“唯一 Simulation”仅指完整平台宿主内的在线控制页面职责；轻量宿主可有自己的控制入口，仍走同一运行实体的后端授权契约。页面唯一、草案唯一、资源权威与单一物理推进者不能相互替代。

## 必需语义分组

任务类型、初态、目标、Execution Profile、适用的 Policy Observation Profile、Action Space、Success Criteria、Failure/Termination、Recording Profile 需要可追踪引用。各配置的适用条件如下；未使用算法的人工任务无需占位 Policy Observation，未录制工具无需占位 Recording，M1 不要求 Export。

Action Space 声明底盘速度、关节目标、TCP 目标或高层任务指令及其单位/频率/解码方式。状态、命令、轨迹和控制权继续由已有契约主责，不在本页复制。

Execution 配方固定允许的来源集合、各来源的控制通路/动作协议、起始来源和接管策略。Run 中只能显式选择快照允许且当前就绪的 Human/Expert/Policy；选择/移交仍须后端授权并记录实际 Owner。切换到未声明的来源或改变模型/IO 配方需要新配置和验证；按既定授权策略发生的 Owner 变化是运行事件，不追改原快照或把运行中接管当作草案编辑。

## Profile 的单一编辑来源

Operator View、Policy Observation（旧文称 Algorithm Observation）、Recording 三个 Profile 独立版本化，各只有一个权威编辑器。Scene Setup 顶部允许选择已有版本，顶部/底部卡片的 View 打开同一只读详情；Edit 进入同一个编辑器创建新版本，再显式采用。卡片、弹层、Task Panel 不维护可覆盖源对象的第二份字段。Execution Profile 是执行意图的独立引用，不与三种 Profile 混为一体。

Operator View 只控制操作者展示；Policy Observation 声明模型输入；Recording 声明要采集的流、频率和元数据；Export Profile 另行控制数据出口。共用相机不使它们自动等价。

| 规范名称 | 旧名/关系 | 适用位置和必需条件 |
|---|---|---|
| Operator View Profile | UI Observation 的信息展示部分；Layout Preset 是其展示布局 | 人工操作/观察宿主；纯布局可宿主本地保存，需要追溯时固定版本/记录变化 |
| Policy Observation Profile | 旧文 Algorithm Observation；按算法入口声明所需输入 | 只有消费算法观测的 Expert/Policy 路径才必需；原生专家可映射其实际配方，不因无学习模型伪造 Profile |
| Recording Profile | 原生采集配置 | 录制时必需；不等于导出数据格式 |
| Execution Profile | Human/Expert/Policy 意图、允许来源和动作通路 | 实际执行时必需，独立于三张观测/采集摘要卡 |
| Export Profile | 数据转换/目标格式配方 | 发布导出/训练用途时按需引用，非 Scene Setup 或 M1 前置 |

三张卡是页面呈现分组，不限制全部配置对象为三个；Execution 和 Export 不必硬塞入同一组卡片。旧 `Task Profile` 是任务/布局/执行的组合称呼，停止作为新落盘对象；按用途映射 Task Template、Layout Preset、Execution/观测引用，并保留原生配置版本。不得简单把旧组合对象无损视为 Task Template 别名。

单一编辑来源限定到被编辑的资源/草案及保存服务；它不禁止不同 HostApp 挂载编辑器。Operator View 纯展示变更不使执行验证 stale，但若需复现人工采集界面，应记录实际 View 版本/变化事件，不把旧快照副本当作后续实际界面证据。

## 对象编辑权限矩阵

最终可写范围是**角色权限 ∩ 资源可编辑能力 ∩ 当前上下文**。服务端强制相同白名单；禁用按钮不能代替拒绝非法请求。首版可只有单用户角色，不因此建设完整账号/多租户系统。

| 对象 | Scene Setup 草案 | 资源定义 | 活动 Runtime / 历史 |
|---|---|---|---|
| Robot root | 仅允许的初始位姿，固定底座模型禁用 root 移动 | 模型/根连接修改需资源编辑权限与新版本 | 草案不写在线 root；运行命令走控制权契约 |
| 关节/夹爪 | 仅声明允许的初始值，检查限位 | 限位、映射、执行器定义需资源权限 | 默认监控只读；运动命令经授权执行服务 |
| 任务对象/托盘 | 允许的位姿、数量、角色；尺寸仅在资产声明可变时开放 | 网格、质量、惯量、碰撞几何等不由普通 Inspector 修改 | 在线扰动须独立授权并记录；历史对象只读 |
| 静态地图/墙/桌面 | 选择固定版本；允许的实例布局覆盖可写，源栅格/几何只读 | 在资源编辑入口创建新版本并检查兼容 | 不热替换活动地图/几何 |
| Waypoint/Route | 独立 Route Draft 编辑、保存新版本、显式采用 | [路线契约](08-navigation-map-route.md) 管版本 | 活动路线只读显示进度；历史版本可重载 |
| 传感器/标定/Profile | 选择版本；编辑进入唯一权威入口 | 挂载、标定等需资源权限与新版本 | 运行/历史数据不追溯改写 |
| 已验证配置快照 | 只读，可派生新草案 | 只读 | Session/Episode 持有原快照 |

选择、可见性、相机移动不会获得写权限。已有 Session 时仍可编辑一个独立草案；“未开始”指该草案不直接绑定的运行状态，而非要求后台没有任何 Session。应用新配置需显式新建，替换或 Reset 现有 Session 仍按其生命周期执行。

## 保存、验证与 Stale

保存状态 `dirty / saved` 与验证状态独立。草案可不完整地保存，但不完整配置不能通过验证；Route/配置正式版本和运行快照必须满足各自发布约束。

| 验证状态 | 含义 |
|---|---|
| `unvalidated` | 当前配置尚无服务端验证结果 |
| `validating` | 正在检查发起时的执行修订和依赖指纹 |
| `passed` | 服务端检查适用当前配置，必需能力/检查均满足 |
| `failed` | 已执行检查不通过，包含字段/对象定位和原因 |
| `stale` | 配置或验证依据改变；保留旧结果供参考，不能创建 Session |

每个检查项记录 `passed / failed / warning / unsupported / not_checked` 与检查范围。必需项 unsupported/not_checked 阻止全局 passed；可选项缺失显示警告。静态字段校验不证明物理可达、无碰撞或路径可执行；前端 Mock 的结果不能签发真实验证快照。

| 变更 | 是否 Stale |
|---|---|
| Scene/Robot/Task schema、模型、初态、对象布局、地图、活动 Route 引用 | 是 |
| Policy Observation、Recording、Action Space、Execution/模型及推理配置、成功/终止、运行 seed | 是 |
| 验证依赖的能力/标定/验证器版本改变，或依赖撤销 | 是 |
| 仅新建一个未被配置采用的 Route/Profile 版本 | 否；当前引用仍固定旧版本 |
| Operator View 的纯显示视角或版本、面板、选择、缩放、显示隐藏 | 否；若其改动同时改变策略/录制/传感器资源则是 |
| 名称、描述、标签或最近查看时间 | 否；不得暗含任务语义变更 |

草案维护 `draftRevision`（所有持久化编辑）与 `executionRevision`（影响运行的编辑），验证绑定后者和规范化 `fingerprint`。fingerprint 覆盖所有执行字段与固定依赖、验证器/能力版本；纯展示和元数据排除。快照仍可附带展示配置副本供重现，但其展示更新不改变既有快照。

从当前配置点“编辑本路线”会建立独立 Route Draft，并在**工作配置草案**挂 `pendingRouteDraftRef + revision/contentDigest`；这一步增加该工作草案的 executionRevision 并 stale，因为用户正在提出新的路线内容。它不改变已保存配置的固定 RouteRef 或已有 Session。若只在资源库编辑一条未采用路线，则当前工作配置不 stale。pending 状态阻止验证通过和创建 Session；保存新路线并显式采用固定版本后清除 pending，再验证。pending 引用只允许出现在草案，不进入已发布配置/ValidatedSnapshot。

任一相关修改立刻 stale；修改后再改回也不自动恢复 Passed，必须由服务端重新认可。验证期间修改执行配置后，迟到结果只入历史，不覆盖当前状态。名称等非执行修改不增加 executionRevision。并发保存使用 baseRevision 等乐观并发条件，冲突拒绝并提示加载/合并；不得静默覆盖物理初态。

## 已验证快照与创建 Session

`ValidatedSnapshot` 由服务端生成，固定规范化完整执行配置、初态、依赖内容/可解析摘要、验证身份、executionRevision、fingerprint、validator/capability 版本、证据和时间。只有摘要或一组可被后续覆盖的引用不构成可重现快照。资源保存后必须能按旧版本读取。

示意数据形状如下；`...` 字符串仅为例，实际必需字段须在实现 schema 中定义，现有 `backend/src/unirobot/contracts.py` 尚不等于这些契约的实现。

```json
{
  "experimentConfig": {
    "id": "exp-transfer", "draftRevision": 9, "executionRevision": 7,
    "sceneRef": {"id": "tabletop", "version": "v1"},
    "robotRef": {"id": "so101-dual", "version": "v1"},
    "taskRef": {"type": "manipulation.bimanual_transfer", "version": "v1"},
    "profileRefs": {
      "operatorView": {"id": "three-camera", "version": "v1"},
      "policyObservation": {"id": "act-transfer", "version": "v1"},
      "recording": {"id": "transfer-raw", "version": "v1"}
    }
  },
  "validationResult": {
    "id": "val-7", "executionRevision": 7, "fingerprint": "sha256:...",
    "status": "passed", "validatorVersion": "v1", "capabilityRevision": "cap-3",
    "checks": [{"key": "required_streams", "status": "passed", "evidenceRef": "check-1"}]
  },
  "validatedSnapshot": {
    "id": "snap-7", "validationResultId": "val-7", "fingerprint": "sha256:...",
    "executionRevision": 7, "resolvedConfigRef": "immutable-config-blob-7",
    "dependencyManifestRef": "immutable-dependencies-7", "createdAt": "2026-10-22T12:00:00Z"
  },
  "createSession": {
    "validatedSnapshotId": "snap-7", "expectedExecutionRevision": 7,
    "expectedFingerprint": "sha256:...", "idempotencyKey": "request-1"
  }
}
```

示例省略的 taskParams、initialState、success/termination、seed、Action/Execution 等必须包含在真实 resolvedConfig 中；路线任务另固定 `routeRef(id,version)`，不保留未发布 DraftRef。

服务端创建时原子核对：快照归属和权限、请求与当前被接受的执行修订/指纹一致、验证和依赖未撤销、所需适配器/能力此刻就绪、资源完整。验证后发生变化不能在“检查→创建”间绕过门控；明确返回 stale、unsupported、offline、conflict 等原因。运行启动还需再次检查实时 readiness，快照不保证设备持续在线。

同一幂等键和请求重试返回同一创建结果；同键不同内容返回冲突。若只能单 Session，已有活动实例时返回冲突，不默默停止旧运行。创建只产生 `prepared` 的未开始 Session，不启动任务、物理推进、控制或录制；显式 Start 及回执由 [Session 生命周期](../20-backend/01-session-scene/01-session-lifecycle.md) 主责。Session/Episode 永久绑定所接受快照，之后的新草案不会修改它。

PointGoal 可按任务协议把已知目标坐标提供给策略；ObjectNav 的目标实例真值只在布局/评估通道，不因 UI 可见就泄露给 Policy。真值、操作者可见信息、策略观测和评分通道分别声明。

参考 [任务字段](../10-frontend/02-scene-setup/02-task-template-configuration.md)、[路线契约](08-navigation-map-route.md)、[场景版本](../20-backend/01-session-scene/02-scene-config-versions.md)、[时间/单位](04-time-frames-units.md)、[TEST-CONFIG-002～006](../40-verification/06-scene-setup-first-loop.md)。

## M1.2 当前实现切片

固定 G1 recipe 的持久草案保存/重载、baseRevision冲突、元数据与执行修订分离、依赖过期和迟到结果拒绝已实现，精确 HTTP 字段与服务器证据见 [M1.2 交付记录](../../m1.2-drafts.md)。初态可写字段为空，必需的 native Session 绑定仍unsupported；验证不会签发Passed/ValidatedSnapshot，Session创建返回409/unsupported。上述完整快照/创建契约仍是后续必须实现的要求，不能由当前元数据草案功能替代。
