# 决策与方案演变记录

规范 ID：`GOV-DECISIONS` · 责任层：治理 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-038](../../设计过程与Specification总册_20261021.md#doc-038) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.8｜更新日期：2026-10-24；原始内容来源保留。

状态：混合决策记录；各条状态逐项标明

来源：S01–S07（详见[来源档案](06-sources.md)）

关联需求：见需求追踪矩阵中的引用与相关主责规范

“已确认”仅表示有明确用户原话或历史明确决定；不代表实现、验收或工期承诺。历史确认项的连续原文缺失时保留证据限制。

| ID | 决定 / 方案 | 状态与依据 | 影响 |
|---|---|---|---|
| <a id="dec-001"></a>DEC-001 | 三维编辑器操作手感 + 机器人工作台多面板/时间轴 | 已确认；S02 用户原话 | 全局产品方向 |
| <a id="dec-002"></a>DEC-002 | 场景/系统流程与科研任务交互解耦 | 已确认；S02 用户原话 | 状态域、工作区边界 |
| <a id="dec-003"></a>DEC-003 | 任务前默认 Observe / Edit 可配置 | 已确认；S02 用户原话 | Scene Setup |
| <a id="dec-004"></a>DEC-004 | 任务内支持 Live 与 Preview-Confirm | 已确认；S02 用户原话 | Joint / TCP / Command |
| <a id="dec-005"></a>DEC-005 | 小车与双臂的观测/干预/专家数据分别配置 | 已确认；S02 用户原话 | Task / Observation / Recording Profile |
| <a id="dec-006"></a>DEC-006 | 同一 Arm 多个不同 Link 框选提升整臂 | 历史已确认；S02 摘要、S03；缺连续原文 | Selection |
| <a id="dec-007"></a>DEC-007 | 默认互斥、Ctrl 多臂选择 | 历史基线；S03 引述用户决定、S02 摘要 | Selection；边缘规则未冻结 |
| <a id="dec-008"></a>DEC-008 | Selected Arms、Active Arm、Owner 分开 | 助手方案；S03 | Inspector、控制权 |
| <a id="dec-009"></a>DEC-009 | 无 Ctrl 跨臂框选不自动多选 | 助手 V0.4 草案；S03 | 原型与边缘命中测试 |
| <a id="dec-010"></a>DEC-010 | 物理受力从独立模式转为 Alt 临时工具候选 | 较早模式 → 助手新建议；S02/S03 | 不把独立模式当唯一最终交互 |
| <a id="dec-011"></a>DEC-011 | 实体主臂无独立相机，展示状态与映射 | 历史澄清；S03；S01 为早期不同表述 | 不误加主臂视频面板 |
| <a id="dec-012"></a>DEC-012 | 前端按场景布置/仿真/回放/训练等分别设计 | 已确认；S04 | 上层工作区结构 |
| <a id="dec-013"></a>DEC-013 | 六业务工作区 + 共用基础设施 | 助手建议；S05 | 本目录用作分类，非用户逐项冻结 |
| <a id="dec-014"></a>DEC-014 | TCP 移动时显示虚线运动轨迹 | 已确认；S04 | TCP / Trajectory；显示语义待定 |
| <a id="dec-015"></a>DEC-015 | 区分候选TCP、q(t)、Actual Trail、关节中心轨迹 | 助手解释/方案；S05 | 不把单点 IK 当规划路径 |
| <a id="dec-016"></a>DEC-016 | 历史：不做导航鼠标设点/Waypoint 编辑 | 已由 DEC-027 / S10 取代；原 S04 保留 | 不再作为当前排除 |
| <a id="dec-017"></a>DEC-017 | 关节滑条以监控为主 | 已确认修订；S04 | Inspector 不默认发送控制 |
| <a id="dec-018"></a>DEC-018 | 默认关节监控只读，编辑另设入口 | 助手实现建议；S05 | 需在详细交互冻结 |
| <a id="dec-019"></a>DEC-019 | 通过按钮停止 VLA，受控进入人工干预 | 已确认；S04 | 平台控制权协议 |
| <a id="dec-020"></a>DEC-020 | 接管 Pending、后端确认、显式恢复 | 助手协议建议；S05 | 防止旧策略动作残留 |
| <a id="dec-021"></a>DEC-021 | 页面切换与 Session 生命周期分开 | 助手建议；S05 | 全局状态与焦点处理 |
| <a id="dec-022"></a>DEC-022 | Replay 与在线仿真上下文隔离 | 助手方案；S05 | 只读历史状态；标注独立 |
| <a id="dec-023"></a>DEC-023 | 完整性、任务结果、训练资格独立 | 助手建议；S05 | Dataset Management |
| <a id="dec-024"></a>DEC-024 | P0/P1/P2 分层推进 | 助手建议；S05 | 未转化为用户承诺排期 |
| <a id="dec-025"></a>DEC-025 | 阶段标签继续讨论，不提前冻结 | 用户要求；S02 | 保留原始记录和事件 |
| <a id="dec-026"></a>DEC-026 | 原文、摘要、规范、索引分别保留 | 本轮整理方法；S06 | 防止来源和推导混淆 |
| <a id="dec-027"></a>DEC-027 | V1 Scene Setup 创建/编辑/保存 Waypoint，Simulation 展示执行进度 | 用户明确；S10；取代 DEC-016 | 范围、地图编辑、导航适配、验收 |
| <a id="dec-028"></a>DEC-028 | 四导航组容纳六逻辑工作区，Data 共用导航 | S08 设计建议 | IA/跨页上下文；未冻结 URL |
| <a id="dec-029"></a>DEC-029 | 任务模板与 Scene/Robot/Experiment 对象分开 | S08 设计建议 | 场景准备与配置契约 |
| <a id="dec-030"></a>DEC-030 | 三 Execution Profile 与录制、部件控制源分开 | S08 设计建议 | Simulation/采集/权限 |
| <a id="dec-031"></a>DEC-031 | Prediction 回到 Simulation，Training 不复制控制台 | S08 设计建议 | 模型入口与兼容检查 |
| <a id="dec-032"></a>DEC-032 | 受限对象配置经 Scene Builder 应用，编辑器不覆盖源模型 | S09 适配建议；官方 README 有相关限制 | 模型/资产身份与 PoC |
| <a id="dec-033"></a>DEC-033 | 标签按用途选用，结果/终止/有效性/人工辅助分别统计 | S08 设计细化 | 数据与评估契约 |
| <a id="dec-034"></a>DEC-034 | 统一骨架与真实任务切片，先评估本地复用和三项 PoC | S09 开发建议 | 资源登记与开发路线 |

后续如果某一项改变，新增决策条目，引用被取代项；来源原文保留，不直接改写历史。方案采纳时记录用户确认来源和日期，不能只把状态从“建议”改成“确认”却没有证据。

## 关联文档

- [冲突、澄清与取代关系](03-conflicts-supersession.md)
- [未决问题登记](02-open-questions.md)
- [讨论过程与设计形成路径](04-design-history.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)

## V0.3 图片设计收敛

| ID | 决定 / 方案 | 状态与依据 | 影响 |
|---|---|---|---|
| <a id="dec-035"></a>DEC-035 | 每个前端页面必须配图片参考 | 用户明确；S13 | 页面清单、图片映射、覆盖校验 |
| <a id="dec-036"></a>DEC-036 | 统一前端架构、任务逐个实现、优先复用，保留现有仿真后端 | S11 取得用户直接认可，补强 DEC-034 的原则部分；PoC/切片顺序仍建议 | 实施路线与适配边界 |
| <a id="dec-037"></a>DEC-037 | Home + 四业务组 + 辅助 Resources；页面/标签不等于独立系统 | 图片收敛建议；S12/S13 | 页面图与导航，未冻结 URL |
| <a id="dec-038"></a>DEC-038 | Training Setup/Run、Evaluation Setup/Running/Report 分清状态，在线控制仍统一 | 设计细化；S08/S12 | 不复制命令通道与可变运行配置 |
| <a id="dec-039"></a>DEC-039 | 模型与批次比较共用证据契约，分母/辅助控制/统计来源明确 | 新设计建议；S12 冲突分析 | 结果与报告 |
| <a id="dec-040"></a>DEC-040 | 原图保留并标采用/修正范围，局部参考不等于视觉定稿 | 整理方法；S13 | 不从图稿扩展所有 V1 功能 |

## V0.4 Simulation 图片更新

| ID | 决定 / 方案 | 状态与依据 | 影响 |
|---|---|---|---|
| <a id="dec-041"></a>DEC-041 | PAGE-03 当前参考采用用户提交的新 Simulation 图 IMG-022 | 用户更新材料 S14；原件归档 | 主图与相关功能节点替换引用，旧图/PPT 保留 |
| <a id="dec-042"></a>DEC-042 | 新图采用三组状态、Profile/部件 Owner、Joint/TCP 与独立事件轨的视觉结构 | S14 图中可见设计；状态转换细节仍待定 | 将已体现与待修正分别记录 |
| <a id="dec-043"></a>DEC-043 | 图中缺失夹爪入口/控制器详情不视为取消原需求 | 本轮分析结论，尚无用户取消指令 | 保留功能并建议折叠呈现 |

## V0.5 Scene Setup 与完整闭环

| ID | 决定 / 方案 | 状态与依据 | 影响 |
|---|---|---|---|
| <a id="dec-044"></a>DEC-044 | IMG-023/024/025 为同一 PAGE-02 的任务变体，旧图保留 | S15 当前三图及共用组件整理要求 | 当前 UI Reference、共享外壳与 schema |
| <a id="dec-045"></a>DEC-045 | 固定任务字段、Profile 唯一入口、对象权限、Stale/快照与路线版本语义 | 用户明确要求整理；具体默认和协议为本轮建议 | FE-SCENE-TEMPLATES / CT-EXPERIMENT-CONFIG / CT-NAVIGATION-ROUTE |
| <a id="dec-046"></a>DEC-046 | 一个前端样板与一个真实采集→清理→训练→预测纵切，停止大范围补图 | S15 当时方向；当前首发顺序由 DEC-049/S16 取代，完整目标保留 | F0/R1，保留 Waypoint V1 范围 |
| <a id="dec-047"></a>DEC-047 | 首任务建议 SO101 台面转运 + Expert，首模型 ACT | V0.5 本地证据建议，非用户指定；当前首发由 DEC-049/S16 取代 | 比 mobileCar 少训练资格/出口缺口；历史 0/20 不宣称策略成功 |
| <a id="dec-048"></a>DEC-048 | 配置创建只产生 prepared Session，Start 另行触发；展示与执行修订分开 | 本轮协议细化建议 | 防止过期验证、重复创建和纯展示改动无故失效 |

## V0.6 用户当前阶段与审核修复

| ID | 决定 / 方案 | 状态与依据 | 影响 |
|---|---|---|---|
| <a id="dec-049"></a>DEC-049 | mobileCar 场景→运行→录制→回放先行，bimanual 再验证复用；训练/预测后续 | S16 用户明确；取代 DEC-046/047 中 V0.5 的首发顺序与训练前置建议，保留长期完整流程 | M1/M2 与后续验收分开；训练资格不阻止原始回放 |
| <a id="dec-050"></a>DEC-050 | HostApp 可轻量独立，组件/契约共享，草案和视图状态按作用域注入 | 用户目标明确；具体注入/并发规则为本轮修复基线 | 不要求固定三个宿主、一个全局 store 或重写所有原 UI；后端权限仍跨宿主统一 |
| <a id="dec-051"></a>DEC-051 | SceneVersion 基础布局、SceneDraft 资源编辑、ExperimentDraft 实例覆盖、ValidatedSnapshot 运行权威分别定义 | S16 审核后修复授权下的契约收敛，非已有实现事实 | 保存/解析/Stale/版本不再有两个物体初态归属；Episode 不维护第二套配置权威 |

## V0.7 统一 3D 工作台执行计划复评

| ID | 决定 / 方案 | 状态与依据 | 影响 |
|---|---|---|---|
| <a id="dec-052"></a>DEC-052 | 主前端先统一为可持续遥操作、观察、采集与回放的 3D 工作台，再按 M1/M2 接通任务 | S17 当前要求重申 S11/DEC-036；非新创产品范围 | 保留轻量专项宿主；纠正诊断/草案页面代替主前端架构的实施偏差 |
| <a id="dec-053"></a>DEC-053 | React + TypeScript 外壳/面板，Three.js 优先封装 native SceneView；Dockview 先验证再采用，R3F 不作为重写前置 | 沿既有 frontend_analysis_v0.2 第8节形成的本轮工程建议；非用户指定库/版本，也未完成兼容性验证 | ES modules 诊断实现保留，但不约束主前端；复用成熟后端/资产/renderer，不整体搬 native main.js |
| <a id="dec-054"></a>DEC-054 | M1.2 内先交付外壳与可操作 3D 样板，再完成配置/prepared，在同一工作台接运行、录制与只读回放 | S17 计划复评下的实施拆分；M1.2a/b 不是新正式里程碑；生产实现继续暂停 | 补对象树/相机/Joint/TCP/Actual-Ghost 与焦点验收门槛；历史32项测试/11项浏览器检查仅证明诊断草案切片 |

## V0.8 导航资源切片

| ID | 决定 / 方案 | 状态与依据 | 影响 |
|---|---|---|---|
| <a id="dec-055"></a>DEC-055 | PointGoal 与每个 waypoint 必须有显式 x/y/yaw；缺 yaw 报错，显式 0 合法；地图/路线资源按固定版本读取，保存与导航执行隔离 | 本次用户明确；S18；不替代 S10，补充其未定义的朝向规则 | 地图/路线 API、前端编辑器、验证 |
| <a id="dec-056"></a>DEC-056 | 录制结束与机器人 STOP 必须是身份绑定动作，回执按"受理/下发/停车证据与覆盖/Recorder 排空/落盘终态与完整性"五层分别给出；整机停稳只在 `parking.coverage_complete=true` 且 `integrity=complete` 时成立，legacy 只有 reason 的 `episodes/stop` 与 `runs/{id}/stop` 都不作为替代 | S19；native 候选 `m1-stop-1`/`m1-end-1` 在服务器以 mock backend + 真实 Recorder 文件完成隔离集成，未部署、真机停车未验证 | Session 生命周期、Episode 采集契约、控制命令契约、STOP/end API、前端可用性文案 |
| <a id="dec-057"></a>DEC-057 | 统一候选必须在同一冻结源码与一份启动清单内提供 geometry-2 / Map-Route / Session / STOP-end 全部面；geometry 读取兼容与 profile/readiness 资格分开判定；待部署 native 候选使用缺项必失败的完整发布身份，且先冻结 release/pin/recipe/config/scene/lock 再进入已授权维护窗口 | S20；本轮服务器实测（统一检查 27/27、正向生命周期 39/39、身份 154 路径与 drvfix 反例）；生产未部署、物理未验证 | 网关启动配置、发布身份工具与回归、地图/几何/Session 契约、维护与回滚流程 |
| <a id="dec-058"></a>DEC-058 | 真实历史 Episode 读取必须是固定来源上的受限只读切片：五条 GET 与有界分页/按流读取保持轻量；复合身份与原生时间/动作语义逐字保留；记录声明、complete_tail、tail 校验和与实际读取验证分四层表达，过期自校验不得改写生命周期状态也不得宣布损坏；3D 只取记录内模型/变换身份，禁止套用在线 geometry/Actual；历史 API 不代理 validate/控制/RESET/录制/步进 | S21；服务器实测历史候选 18960 上 61/61 断言（348 条真实记录、COMPLETE 与 FAILED/incomplete 分别读取、归档聚合摘要 696 文件前后不变）、既有能力回归 27/27、聚焦 12 passed、全量 140 passed / 3 项历史失败；同步回放与新采集闭环未做 | Episode/采集契约、历史读取 API 与 OpenAPI、时间/坐标语义、前端回放接线、发布身份清单 |
| <a id="dec-059"></a>DEC-059 | 只读必须由构造保证而非约定：验证只经不接受 method/body 的 GET-only 入口访问 native，重算结论只在隔离副本上做；路径受限必须同时覆盖索引与读取（run/episodes/Episode/manifest/固定流/sidecar/assets 的解析结果都不得越出对应边界，缓存索引不得绕过读取时检查）；区间过滤下缺失/非整数/bool `event_seq` 必须排除并计数，不得补造；不变性声明只能覆盖事前记录并事后复核的同一文件集合；报告必须重算并断言等于冻结启动清单的源码摘要 | S22；服务器实测候选 18964 上 69/69 与 28/28（清单↔运行字节绑定、51 次请求全为 GET、946 文件覆盖集合 drift=[]）、聚焦 19 passed、全量 147 passed / 3 项历史失败；同步回放与归档全量验证仍未做 | 历史读取 API 与路径边界、records 分页/过滤契约、验证工具与证据绑定、发布与回滚流程 |
| <a id="dec-060"></a>DEC-060 | run 目录身份必须在每次构造读取位置时校验（目录不得是软链，解析结果仍须等于 `root/run_id`），否则缓建成的索引可被"换成兄弟 run 的软链"攻击以错误身份读出他人数据；图像—机器人状态关联只允许使用记录中真实存在的键（`sample_id`、`control_tick_id`、`payload.sample_id`），并区分 `matched/partial/missing/unresolved_reference/identity_mismatch/stream_absent`；不插值、不状态保持、不按时间相近或行号关联；差值只作为"记录字段相减的年龄"呈现，同钟命名不得表述为同源已验证；本切片不解锁历史 3D | S23；服务器实测候选 18966 上 86/86（含 23 项帧关联断言，59 次请求全为 GET、946 文件 drift=[]）与 28/28 统一回归、聚焦 31 passed、全量 159 passed / 3 项历史失败；真实记录 303 帧的键关联全命中而 `feedback_sample_id` 仅 3/303 有目标行、状态早于采集 0.34–8.78 ms | 历史读取 API 与帧关联契约、时间/游标语义、统一历史游标的后续设计、回放前端可用范围 |
| <a id="dec-061"></a>DEC-061 | 帧分页的 `has_more` 只由"整页装满后是否还存在下一条合格锚点"决定，`next_offset` 保持锚点文件原始行号语义，已读行与未读行、空行/超限/坏行分别计数，越过文件末尾才声明无下一页；角色完整性由角色语义决定（必需 `sensor_kind` 各恰一条、单记录角色恰一条），新增 `ambiguous_kind`/`ambiguous_candidates` 与公开判定优先级，多候选全部列出且不得默认取第一条，候选不唯一时不输出单一状态；时间差必须逐条命名来源记录、字段、单位、符号与含义，事件写入戳/状态负载采样戳/录制器声明时间/观测与落盘时延/`sim` 基差值互不折算，`observation_age_ms` 只作管线延迟，旧 `age_of_state_relative_to_frame` 随 `frame-link-1 → frame-link-2` 移除；同钟命名与写入版本绑定分开表述，`synchronized` 不因数值相近升级；历史姿态准备只使用冻结 geometry bundle 并重核记录与 bundle 的模型/场景身份与资产摘要，逐目标给出 `verified/partially_verified/unverified/missing/not_required_for_pose` 与精确缺口，未证实坐标或标定不补默认值、动态对象不伪造位姿，mesh 只由冻结 bundle 提供且不代理当前 scene/snapshot/Actual；资源就绪不等于渲染通过 | S24；服务器实测候选 18969 上 102/102（含 40 项帧/姿态断言，64 次请求全为 GET、946 文件 drift=[]）与 28/28 统一回归、聚焦 39 passed、全量 167 passed / 3 项历史失败；真实首帧三个时间量 2.885407/3.669841/3.668296 ms 且 `sim` 基差为 0、`observation_age_ms=33.451169` 等于 `arrival−capture`；run 清单身份四项与 bundle 全等、23 资产逐文件校验、9 项映射仅 1 项 partially_verified（关节顺序凭证只到索引 3） | 帧读取分页与关联契约、时间语义与 schema 版本迁移、历史姿态准备与冻结模型资产读取、统一历史游标与前端历史渲染的后续验证范围 |
| <a id="dec-062"></a>DEC-062 | `sim` 基时间量按来源记录拆分：负载量只取 `payload.sim_time_s`，事件信封量独立具名为 `state_event_envelope_sim_time_minus_frame_capture_sim_time`，缺数值时该量缺席而不回退，修正记入 `frame-link-2` 的 `version_migration.corrections`；机械臂模型映射以"源码按名称构造（`ARM_JOINTS`=joint1…joint5 → `ArmController.joints`/`qpos` → 反馈 `self.arm.qpos[:5]`）+ 录制时段三个冻结 release 快照含同一链 + 摘要与记录 `model_sha256` 一致 + 同一反馈负载内 TCP 运动学复现"为证据上限，当前源码语义不证明旧 writer 运行该版本（记录不含 release/commit 身份，`writer_identified=false`）；`arm_model_qpos_rad` 的模型绘制不要求先转用户角，`zero_model_rad` 实为精确 `-π/2`（此前"舍入为 -1.5708"的说法更正），用户照片零位不称为硬件标定；就绪条件按九项部件分别给出前提、所需姿态输入、前端规则、证据与缺口，整车 `pose_readiness=false` 不等于固定资源不可装配、局部可用不升级整车可重建；夹爪宽度在平台配置中已声明常数，缺的是与历史写者版本绑定的凭证（更正 M1.5d 的"任何地方都不存在规则"表述） | S25；服务器实测候选 18970 上 110/110（本轮新增 8 项，64 次请求全为 GET、946 文件 drift=[]）与 28/28 统一回归、聚焦 45 passed、全量 179 passed / 3 项历史布局失败；离线运动学对照 152/303 帧、`error_primary_m` 最大 1.68974e-14 m、五轴均有位移（`unexercised_joints=[]`，joint2/joint3 幅度仅 0.0029/0.0022 rad）、根坐标另一约定分离 0.0556000 m、关节序反转分离 0.20967 m；容差由本检查自述、非标定上限 | 帧时间语义与版本迁移说明、历史姿态映射的证据强度与版本绑定上限、按部件就绪条件与前端消费规则、运动学一致性检查工具、历史整车渲染与正式 M1 验收范围 |
| <a id="dec-063"></a>DEC-063 | 逐 link 历史装配数据由既有 `GET /api/v1/episodes/{id}/robot-state` 上的可选布尔参数 `include_model_tree`（默认 `false`）给出：Episode 只读面仍是八条 GET、`unirobot-mobilecar-history-pose-1` 不升版（纯新增 `model_resource.model_tree`）；树直接复用冻结 bundle 的 `Link`/`Geom` 序列化（`parent_name`、joint 名/型/轴、`local_transform`、完整 `geoms[]` 的类型/尺寸/变换/颜色/`mesh_asset_id`/碰撞过滤），不得改用缺几何字段的 `_link_view` 摘要形状，既有摘要视图原位保留；模型身份不符时只拒给（`included=false`、`links_are_substituted=false`、无 `links`/`world_links` 键），不返回替代树；不读 live scene/snapshot/Actual；缓存沿用既有四个摘要与 `content_identity_sha256`，树按内容键取一次、逐帧请求省略该参数，网格内容 `"sha256:…"` ETag 只属于 `…/model/assets/{asset_id}`，动态 `robot-state` 响应不带 ETag；`world_links` 继续声明 `compiled_initial_layout_not_live_object_state` 并新增 `world_links_are_not_recorded_object_positions=true`——名为 `target_cube` 的世界链是编译初态而非记录位姿，`dynamic_scene_objects` 仍为 `missing` | S26；服务器实测候选 `m1z-20261029T075630Z-platform`（18977）118/118（110→118，本轮 +8）、统一回归 28/28、冻结 release 内聚焦 55 passed、dev 树全量 183 passed / 3 项历史布局失败，66 条请求全为 GET、946 文件 `drift=[]`；树与同一进程直接加载的 `GeometryBundle` 逐元素相等（71 links / 2 world_links / 100 geoms / 22 mesh_geoms，23 资产中 22 被引用、`imu_link` 无引用），带树响应 `content-length 107835` 且无 `ETag`，换帧树逐字节相同、状态负载不同，`live_scene_reads_in_this_run=0`；隔离夹具把 native 指向 `127.0.0.1:1` 时 `/mobilecar/scene` 503 `native_offline` 而历史树完整 | Episode 只读契约的逐 link 装配数据来源、前端固定模型装配与内容键缓存规则、动态响应与资产 ETag 的分工、编译初态与记录位姿的词汇区分、历史整车渲染与正式 M1 验收范围 |
| <a id="dec-064"></a>DEC-064 | 采集锚点的播放资格按**逐时间基、逐覆盖范围**判定并由后端定义字段：`GET /api/v1/episodes/{id}/frames` 增加可选布尔 `include_time_quality`（默认 `false`，非法布尔 422 `bool_parsing`），开启时以顶层 `time_quality` 返回有界 census（`coverage` 含 `covers_whole_episode/not_a_whole_archive_sweep/page_filter_context`；`time_bases` 逐基给出 `unit/clock/source_record/numeric_count/missing_count/non_numeric_count/first_in_file_order/last_in_file_order/min_recorded_value/max_recorded_value/recorded_gaps/equal_adjacent_gaps/backwards_gaps/monotonic_non_decreasing_in_file_order/file_order_matches_value_order`；`identity` 列出重复 `sample_id` 的每组 occurrences 与 `record_positions`；`playback_eligibility` 分 A/B/C 三块）；A 只需可读锚点，B 必须"扫描覆盖完整 + 该基每锚点存在且数值 + 按文件顺序不回退"才 `eligible_for_whole_episode`，缺时/非数值/回退列入 `blocking_reasons` 且不补值、不插值、不用零间隔除出速率，`implied_rate_hz_from_median_recorded_gap` 明确标注不是录制器声明的速率也不是播放保证（禁止默认 30Hz、浏览器到达补时、跨 RESET 连成一条时钟），C 恒 `eligible=false` 且 `not_derivable_from=["A","B"]`；读取面不因 census 改写锚点位置、顺序或关联身份，也不新增端点、通用查询框架或服务端播放 Session；`unirobot-mobilecar-frame-link-2` 不升版（默认页逐键不变，census 为唯一新增顶层键）。**行为收紧并如实声明**：`robot-state?sample_id=` 命中多个锚点时不再静默取第一条，改为 409 `frame_sample_id_ambiguous` 并给出两个匹配位置与 `no_first_match_was_assumed=true`，调用方须按 census 位置消歧而非依赖"总能拿到一条" | S26 之后的本轮；服务器实测候选 18979 上 130/130（118→130，本轮 +12 项）、统一回归 28/28、冻结内聚焦 63 passed、全量 191 passed / 3 项历史布局失败、71 次请求全为 GET、946 文件 `drift=[]`、源码聚合与本地工作树全等；真实 COMPLETE 记录 303 锚点三基均 0 缺失/0 非数值/0 相等/0 回退、A 与三基 B 合格、隐含速率 4.998/5.000/4.967 Hz 而锚点无声明速率字段（profile 名含 5hz 不作证据）、2 页遍历 303 锚点无跳漏且末页 `has_more=false`/`next_offset=null`、窗口页仍是筛选（返回 1 帧、302 条窗外、顺序未改）、census 8,733 B 对页本体 5,181,012 B；代表 FAILED 记录 4 锚点同法测量（其记录完整性属另一层事实）；隔离夹具覆盖缺时/非数值/相等/回退/重复 id/触顶，未断开真实 8792 | 帧读取契约的时间质量与播放资格词汇、`robot-state` 选帧拒绝语义与兼容声明、统一时间轴与前端倍速/逐帧实现的输入、跨流同步与正式 M1.5/M1 验收范围 |
| <a id="dec-065"></a>DEC-065 | 时间资格按**三个独立事实**判定并收紧覆盖边界：`reached_end_of_file`、`line_accounting.every_line_of_the_anchor_file_is_decided`（`blank`/`prefiltered` 为良性，`oversize`/`unparseable`/`non_object` 为不可判定并给出 `undecidable_positions[].record_position`；解析成功却被规则剔除的锚点另计 `parsed_records_rejected_by_rule`）、逐基 `readable_anchor_timing_satisfies_schedule`；`covers_whole_episode` 与逐基 `eligible_for_whole_episode` 需前两者同真——**不可判定行可能藏着锚点，排除它之后不得再用其余干净锚点宣称整 Episode 调度资格**（旧行为只看 EOF，作为缺陷复现并记入 `version_migration.corrections`；旧串 `scan_truncated_at_anchor_limit` 停用为 `scan_stopped_at_anchor_limit_before_eof`）；A 追加顺序浏览继续可用但须声明 `displayed_sequence_may_have_gaps`；`scope_note` 更正为"时间窗只筛帧页、普查独立扫描锚点文件、整集资格与页面是否有窗无关"，并以真实请求"窗口页 1 帧 + 302 窗外 vs census 303 锚点"验证。动作／事件依据以既有读取面为内容源（`streams/{stream_id}/records` 分页与 `event_seq`／命名时间过滤不变），语义与关联由同一 `frames` 路由上可选布尔 `include_action_basis`（默认 `false`）的 `action_basis` 块承担：十类逐类 `observed`/`not_recorded_in_this_scan`、逐 type 计数与首末位置、逐键 present/null、单位取自字段名后缀（无后缀 `unknown_from_field_name`）、逐帧按 `capture_control_tick_id == control_tick_id` 精确关联 `feedback`/`actuator_reference`/`dispatch`（`matched`/`missing`/`ambiguous_candidates`，候选全部列出，不取第一条、不插值、不从相邻 tick 延续、不造零动作）、命令按 `command_id` 成链但明言不证明执行结果、控制来源只报告 payload 内 `operator_id`/`operator_kind`/`session_id`/`owner_session_id` 且不默认为 Human、无共享键类别只作独立事件轨；不新增端点/通用查询框架/服务端播放 Session/时钟对齐系统，`frame-link-2` 不升版、默认页逐键不变 | S28；服务器实测候选 `m1h-20261030T002258Z-platform`（`127.0.0.1:18983`，PID 3745241，端口启动前 `ss -ltn` 实测空闲，独立 SQLite，源码聚合 `68f481b38843d2bc…` 50 文件与启动清单 MATCH、清单内 `frames.py`=`f4b4187fc5b4e0cf…` 与运行目录全等，启动清单 sha256 `90b5234d6308860d…`）读取检查 **146/146**（130→146，本轮 +16）、统一回归 **28/28**、冻结树聚焦 **69 passed**、全量 **203 passed / 3 项历史布局失败**（具名保留）、75 条请求全为 GET、946 文件 `drift=[]`、`live_scene_reads=0`；同一含不可解析行的隔离夹具在基线 `a10b96b` 源码上报 `covers_whole_episode=true`/`any_base=true`/逐基空阻塞，在修正源码上报 `covers_whole_episode=false` 与逐基 `1_lines_are_undecidable_and_could_hide_anchors`（A 两版均合格）；真实 COMPLETE events 全量 12561 条 12 类（`actuator_reference`/`feedback` 各 6074、`rgbd_capture_timing` 303、`lease_heartbeat` 45、`requested`/`approved`/`dispatch` 各 20、`recording_start`/`recording_stop`/`episode_terminal`/`feedback_initial`/`lease_expired` 各 1）与 FAILED 224 条 11 类（无 `lease_heartbeat`）；逐帧候选 `actuator_reference={"1":200}`、`dispatch={"0":199,"1":1}`；`rejected`、执行完成回执与接管事件类型 `not_recorded`；`episode_terminal` 两个数值时钟为 null；必需流无按 Episode 声明，只引用已有声明否则 `unknown`；18977（M1.5f）与 18979（M1.5g）未被替换 | 帧普查覆盖边界与整集资格声明、动作／事件读取与逐帧关联词汇、`not_recorded` 与 `unknown` 的分工、前端事件轨／命令轨／状态轨实现输入、M1"状态、动作及声明必需流重载"的剩余差距、跨流同步与正式 M1.5/M1 验收范围 |
