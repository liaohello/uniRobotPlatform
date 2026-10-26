# 来源目录与完整性声明

规范 ID：`GOV-SOURCES` · 责任层：来源 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-043](../../设计过程与Specification总册_20261021.md#doc-043) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

本目录是需求证据档案。当前取得的并非全部早期会话逐字记录；摘要、原文片段、当前原话和现存文件分别标明。没有用推测补齐失落轮次。

| 来源 | 材料 | 完整性 | 覆盖主题 |
|---|---|---|---|
| [S01](../../设计过程与Specification总册_20261021.md#doc-044) | foreEndDes.pdf 当前六页文本 | 现存文件，非聊天导出；图片未复刻 | URDF/3D/坐标系、主从臂、回放、实时面板和力交互探索 |
| [S02](../../设计过程与Specification总册_20261021.md#doc-045) | 更早主题的检索摘要与上下文用户片段 | 摘要和单条原话混合，逐段标明；缺连续角色历史 | 统一方向、Observe/Edit、Live/Preview、任务差异、产品目标 |
| [S03](../../设计过程与Specification总册_20261021.md#doc-046) | 3D Interaction V0.4 的先前助手回复 | 开头截断的可见片段，内部 V0.4 正文可见 | 快捷键、选择、Joint/TCP/Force、Leader、初步验收 |
| [S04](../../设计过程与Specification总册_20261021.md#doc-047) | 最新用户轮，msg_idx 32 | 本轮上下文完整可见的单条用户消息 | 业务拆分、虚线轨迹、导航边界、关节监控、按钮接管 |
| [S05](../../设计过程与Specification总册_20261021.md#doc-047) | 对 S04 的助手回复，msg_idx 33 | 本轮上下文完整可见；格式空白有规范化 | 六工作区、轨迹区分、接管协议、十个缺口和 Spec 目录 |
| [S06](../../设计过程与Specification总册_20261021.md#doc-048) | 本轮用户整理要求 | 本轮原话完整 | 整理过程、Spec 分类、Wiki 与交叉索引 |
| [S07](../../设计过程与Specification总册_20261021.md#doc-049) | coreIntent.md 当前文本 | 现存两行任务意图，不是聊天历史 | 小车 VLN/VLA 与双臂、专家和遥操作意图 |

## 来源优先级

当前明确用户原话优先于早期建议；后续明确澄清优先于早期探索；现存文件按本次读取内容使用；检索摘要用于补充并标记证据限制。助手回复中的“我建议”不能因进入索引而自动变成用户决定。

## 还未取得的材料

较早“需求讨论流程 / (完整版)需求讨论流程”“3D交互流程解析”“产品边界与核心对象”的完整连续用户/助手导出未取得。更早逐字记录、交互演示的可执行状态、PDF 内截图未收入逐字文本。未来有原始记录时追加尚未占用的来源编号并补齐，不覆盖当前档案。

## 参考项目入口（仅记录提及，不作当前能力核验）

| 项目入口 | 对话中的参考意图 |
|---|---|
| [gkjohnson/urdf-loaders](https://github.com/gkjohnson/urdf-loaders) | 加载机器人、关节与拾取基础 |
| [tony1213/urdf-viewer](https://github.com/tony1213/urdf-viewer) | URDF/3D 基础交互参考 |
| [qkrdkwl9090/urdf-viewer](https://github.com/qkrdkwl9090/urdf-viewer) | 机械臂控制与前端组织探索 |
| [rerun-io/rerun](https://github.com/rerun-io/rerun) | 多传感器、曲线、统一时间轴 |
| [vuer-ai/vuer](https://github.com/vuer-ai/vuer) | Python 驱动 3D / 遥操作探索 |
| [ttktjmt/mjswan](https://github.com/ttktjmt/mjswan) | 鼠标物理拖拽体验 |
| [ARISE-Initiative/robosuite](https://github.com/ARISE-Initiative/robosuite) | MuJoCo 控制、IK、OSC 与示教的探索问题 |

以上用途来自需求对话，未在本轮重新访问各仓库，因此不将“项目不支持某能力”等早期用户观察转写为当前事实。

[Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)

## 本次拆分来源与完整性

[原始总册](../../设计过程与Specification总册_20261021.md) 保持不变；读取时 SHA-256：`995e4bf3c3fdc19f6874e1d221d5e52195db5f38e79fcac8c082b8ac9939119a`。

本轮用户要求：吸收进一步讨论，建立有索引的多文档 Specification；前端与后端分开，按大类、功能包和节点组织，并提供更易读的分类思路。该要求授权组织文档，不自动批准六页面、技术栈、全部 API 或排期。

当前会话另有用户明确选择：浏览器允许绘制 3D，仿真、感知与规划仍在服务器。技术栈具体选型保持建议状态。

上一轮 [工程分析](../../frontend_analysis_v0.2.md) 作为历史参考；默认滑条控制已由总册覆盖；地图设点的旧排除现又经 S10 扩展，当前以该直接确认和新主责规范为准。

## V0.2 补充来源登记

| 来源 | 性质 | SHA-256 |
|---|---|---|
| [S08](sources/S08-frontend-ia-analysis.md) | 用户提供的助手分析文本；非用户逐项确认 | `ceb01d36c0b0de8c5ae6397157fb0c010600172fd9f746bfd73610a540dfe4ad` |
| [S09](sources/S09-unified-development-reuse-analysis.md) | 用户提供的助手分析文本；非用户逐项确认 | `377bc8d4b39c55f014826b538f70430b60af8875a46e28337f4a143700233adb` |
| [S10](sources/S10-waypoint-scope-confirmation.md) | 当前用户范围确认 | `2280782bc2eafcd2cd84b394959b974b8a518547adc7b496e57871cb9432cdb5` |

S08/S09 原文件按字节归档；其中远程图片/仓库声明不构成本轮产品验证。官方资料核对另见 [参考记录](../references/03-official-review-notes.md)。

## V0.3 会话与视觉材料

| 来源 | 实际取得内容 | 限制 |
|---|---|---|
| [S11](sources/S11-design-discussions.md) | 指定分支 5 个用户轮次及父对话 5 个用户轮次，含统一前端增量开发的直接认可 | 助手消息为内容引用占位，未取得完整正文；原工具返回保留为 JSON |
| [S12](sources/S12-visual-materials.md) | 本地 22 PNG、20 页 PPT 的图片关系/哈希，逐张查看 21 个独特内容 | 概念图不是现有实现/硬件/性能事实；PPT 无额外文字计划 |
| [S13](sources/S13-current-visual-spec-request.md) | 当前用户要求读会话、纳入图/计划、每页有图、分析冲突并优化规范 | 不意味着批准全部图中功能或立即开始实现 |

各来源 Markdown、会话快照与素材清单的哈希登记于 traceability.json；原图不复制，参考 visual-assets.json 的原件路径。

## V0.4 新图来源

[S14](sources/S14-simulation-v2-update.md)：用户在 2026-10-22 更新 Simulation 设计图并要求同步规范、说明删除/替换与建议。原样归档为 IMG-022，SHA-256 `281a2d190f5fb2d6af5fe54c8090d71e4a028f5b4443d031a3218ea2506b4497`。新版当前参考和未冻结语义分开；图片本身不授权运行设备或修改产品代码。

## V0.5 三图与完整闭环

[S15](sources/S15-scene-setup-first-loop.md)：用户提供导航、近场抓取、双臂转运三张 Scene Setup 图，要求更新任务字段、公共契约和共享组件，并将当前路线收敛至一个前端样板及采集→清理→模型训练→预测运行。图归档为 IMG-023/024/025，哈希见来源页。原图文字只作参考；本轮具体默认值、首任务与模型选择为设计建议，未虚构字段级用户确认或产品运行证据。

## V0.6 当前范围与修复授权

[S16](sources/S16-mobile-first-spec-repair.md)：用户明确 mobileCar 四步闭环优先、bimanual 验证复用，并在只读审核后授权修复、继续使用多 agents。替换 V0.5 的首发顺序/训练前置建议，保留完整数据/模型流程为后续目标；轻量工具与平台可有不同宿主，不强制共享可写全局状态。原生 mobileCar 仅做静态接口核对，没有启动仿真、迁移工程或执行产品验收。

## V0.7 前端执行计划复评

[S17](sources/S17-3d-workbench-replan.md)：当前用户要求依据已有设计和 Specification 重新规划好操作的 3D 界面，并明确可用多 agent 核定。重申 S11 的统一前端架构原则，保留 S16 的阶段/轻量宿主边界。具体 React/TS、SceneView 封装、Dockview 验证与样板顺序是本轮工程建议，不虚构历史库选型确认；本轮仅修订文档，前端实现继续暂停。来源字节哈希登记于 catalog.json 与 traceability.json。

## V0.8 地图/路线切片来源

[S18](sources/S18-navigation-map-route-slice.md)：本次用户要求版本化地图读取、带朝向 Waypoint 的 Draft/Version 保存链路、地图/姿态约定和执行隔离。S10 原文保留；S18 是新增需求来源，不重写 S10 的历史范围确认。


## V0.8 STOP 与录制收尾切片来源

[S19](sources/S19-session-stop-recording-end.md)：本次用户 Goal 要求交付受 Session/运行身份约束的机器人 STOP 与录制可靠结束候选，明确回执五层分离、身份在 lifecycle 临界区重检、安全 STOP 不受 motion/recording ready 门控、并发与幂等规则、隔离无物理集成范围以及"候选≠部署"。历史 S14/S15 关于停止/结束录制的表述保持原样，S19 只补充其未定义的结束侧原子性。来源字节哈希登记于 catalog.json 与 traceability.json。

## V0.8 统一候选与发布身份来源

[S20](sources/S20-unified-candidate-release-identity.md)：本次用户 Goal 要求把已验证能力收敛为一个统一可联调候选（同一冻结源码/启动配置/OpenAPI），把几何读取兼容与执行资格分开判定，把候选身份升级为缺项必失败的完整发布身份，并修正维护窗口顺序。历史 S14～S19 原文与事实保持不变。来源字节哈希登记于 catalog.json 与 traceability.json。

## V0.8 真实历史读取来源

[S21](sources/S21-history-episode-read-slice.md)：本次用户 Goal 要求完成真实历史 Episode/segment 只读 reader 首个切片——固定一个历史来源与实际 recording_root、冻结最小读取契约与 OpenAPI、保留复合身份与原生时间/动作语义、把声明状态与实际读取验证分层、路径受限只读并把启动器纳入发布身份。历史 S14～S20 原文与事实保持不变。来源字节哈希登记于 catalog.json 与 traceability.json。

## V0.8 历史只读整改与可复现发布来源

[S22](sources/S22-history-readonly-hardening.md)：本次用户 Goal 要求把历史 reader 整改为构造级只读（只经不接受 method/body 的 GET-only 入口访问 native，重算只在隔离副本）、统一受限路径解析（索引与读取两侧都不得借目录或文件软链越界，缓存索引不得绕过读取时检查）、修复 `event_seq` 区间过滤（缺失/非整数/bool 排除并计数，不补造），修正超出证据的"全部原始文件未改"表述，并让报告重算并绑定冻结启动清单的源码摘要；保留违规记录、旧清单值与旧报告，不倒填、不猜测回滚。历史 S14～S21 原文与事实保持不变。来源字节哈希登记于 catalog.json 与 traceability.json。

## V0.8 真实帧关联切片与 run 身份边界来源

[S23](sources/S23-frame-linkage-slice.md)：本次用户 Goal 要求先最小修正 run 目录身份边界（缓存索引建立后把 `root/runA` 换成 root 内 `runB` 的软链时，不得再以 `runA` 身份读出 `runB`；每次构造读取位置都校验 run 目录身份，错误语义沿用既有码，只在隔离夹具构造该条件），再交付一条真实 Episode 的"图像—机器人状态关联 + 有界只读帧读取"切片，为统一历史时间游标提供可验证契约：关联只依据记录中存在的键，未解析的 `feedback_sample_id` 显式返回缺失，差值只作为记录字段相减的年龄呈现，不插值、不状态保持、不把命名同钟说成已验证同源，不扩展到历史 3D，也不宣称归档全量完整性或 M1.5/M1 验收。历史 S14～S22 原文与事实保持不变。来源字节哈希登记于 catalog.json 与 traceability.json。

## V0.8 帧读取修正与历史姿态准备来源

[S24](sources/S24-frame-reading-and-pose-preparation.md)：本次用户 Goal 要求修正帧关联的分页判定（`has_more` 不得混用预过滤计数与原始行号，必须由下一条合格锚点决定，`next_offset` 保持原始行号语义，坏行/超限行/空行如实计数且不静默给出末页）、收紧角色完整性判定（图像观测按必需 `sensor_kind` 与逐角色基数判定，重复候选给 `ambiguous_kind`/`ambiguous_candidates` 并全部列出，不得无说明取第一条；主角色完整性与 `unresolved_reference` 分开，不按时间相近补造状态）、分离时间语义（事件写入戳、状态负载采样戳、录制器声明反馈时间与采集/观测/落盘时延分别命名并给出来源记录、字段、单位、符号与含义，`observation_age_ms` 属管线延迟；`sim` 基与 backend monotonic 基不折算；说明同钟命名的证据强度与写入版本可绑定范围，不因数值相近升级 `synchronized=true`），并交付历史机器人 3D 所需的固定模型资源与姿态映射准备切片（复用不可变 geometry bundle，重核记录与 bundle 的模型/场景身份、资产摘要、关节名称与顺序、单位与根坐标映射；未证实的坐标或标定不补默认值，动态场景对象不伪造历史位姿；不代理当前 scene/snapshot 或 Actual；资源就绪与渲染验证分开）。历史 S14～S23 原文与事实保持不变。来源字节哈希登记于 catalog.json 与 traceability.json。

## V0.8 时间量来源修正与分部姿态就绪来源

[S25](sources/S25-time-sources-and-pose-readiness.md)：本次用户 Goal 要求修正 `sim` 时间量的来源标注（此前状态负载缺少数值 `sim_time_s` 时改取事件信封的同名字段，却仍把该量标为负载来源；现拆为两个各自具名、各自标明来源记录的量，缺负载值就不生成该负载量，不用回退值掩盖缺失，并在 `version_migration.corrections` 中显式说明），补全机械臂模型映射证据（`ARM_JOINTS` = joint1…joint5 → `ArmController` 按名称取 `jnt_qposadr` → 反馈序列化 `self.arm.qpos[:5]` 的源码链、该链在录制时段已冻结 release 快照中的存在、与记录 `model_sha256` 相符的摘要，以及当前源码语义不能证明旧 writer 运行该版本的上限），把模型角与用户角分离（`arm_model_qpos_rad` 的绘制映射不要求先转用户角；`zero_model_rad` 实为精确 `-π/2`，此前"舍入为 -1.5708"的说法更正，用户照片零位不称为硬件标定），给出按部件划分的就绪条件（固定模型装配、机械臂局部姿态、底盘位姿、夹爪、TCP/相机等九项各自的前提、所需姿态输入、前端规则、证据与缺口；整车 `pose_readiness=false` 不等于固定资源不可装配，局部可用也不升级），并用纯运动学独立对照复核可证明的映射（同一条反馈负载内重建 TCP 位置与记录的 `tcp_position_world_m` 相比，报告误差与样本覆盖，只支持运动学一致性、不代表硬件标定）。同时更正 M1.5d 记录中"任何地方都不存在夹爪宽度规则"的说法：平台运动学配置已声明宽度与 mimic 常数，缺的是这些常数与历史写者版本绑定的凭证。历史 S14～S24 原文与事实保持不变。来源字节哈希登记于 catalog.json 与 traceability.json。
