# S28｜时间资格覆盖边界修正与历史动作／事件读取依据（2026-10-30）

状态：本次用户 Goal 原文（要点保留），实现与实测见 M1.5h 交付记录。来源：用户在 M1.5g 之后提出的新的开发 Goal。

## Goal 原文要点

执行新的开发 Goal："修正时间资格覆盖边界，并交付历史动作／事件的最小读取与关联依据。" 这不是 M1.5g 的复审计，旧 Goal 已完成；`a10b96b` 尚未包含本任务要求的资格修正和动作／事件扩展，不得用旧 130/130、28/28 或活体核查代替本 Goal 的完成证据。

**A. 时间资格修正——必须有实现和新增验证。** 先用隔离夹具复现：文件含不可判定的超限／无法解析内容，其余可读锚点时间正常，当前仍可能报告整 Episode B 资格。做最小修正，分别表达"是否扫描到 EOF""是否能完整解释适用锚点""可读锚点的时间是否满足调度条件"。不可判定内容可能隐藏锚点时，不能排除后继续证明整集资格。明确哪些计数影响哪些资格；空白行、已确认无关记录不一概当作损坏。A 追加顺序浏览继续可用，保留定位诊断。同时修正 `scope_note` 和交付表述：时间窗只过滤帧页，census 独立扫描 Episode 锚点文件；是否支持整集资格取决于 census 自身覆盖与内容，不是因为页面有时间窗就降为窗口资格。用"窗口页 1 帧但 census 303 锚点"的真实请求验证。

**B. 动作／事件回放依据。** 针对已使用的代表 COMPLETE、FAILED Episode，有界核对真实存在的：Actual/feedback、actuator_reference/Target、requested/命令意图、受理／拒绝／下发／执行反馈、控制来源／接管和 Episode 起止／失败事件。逐项记录真实 type、流、原始位置、时间字段、单位和关联键。缺失写 missing/not_recorded/unknown；不默认 Human，不补零动作，不把拒绝请求当执行动作。优先复用现有 events records 分页与 event_seq／命名时间过滤。只有记录确有共享键时，才补最小帧关联角色；保留缺失、全部候选与歧义，不默认选第一条。无共享键的事件作为独立事件轨呈现，不按时间最近或上一条记录强行归属当前帧。如果现有 GET 已能提供内容，补齐必要语义元数据、真实样例和检查；只有存在具体调用缺口时才扩展接口。不建设通用查询框架、服务端播放 Session 或新时钟对齐系统。若历史样本没有某类事件，完成事实交付，不为制造正向样例改归档。

**前端交接**必须给出可直接调用的请求与真实响应、哪些事件可按什么键关联帧、哪些只能独立读取、哪些未记录、缺失／歧义／拒绝状态，以及 M1"状态、动作及声明必需流重载"的剩余差距。必需流只引用已有声明；没有声明就 unknown，不自行编造要求。

**验证与发布**：所有测试、HTTP 检查在授权服务器执行；新增验证覆盖 A 的旧错误、修复结果和窗口范围语义，B 覆盖真实事件读取及适用的精确关联／缺失／多候选；真实归档与 synthetic 证据分列，不用旧套件计数代替新增行为；运行聚焦与统一能力回归并按项目要求执行健康检查；历史三项布局失败保持具名列出。18979、18977 保持稳定，前端本轮不等待本候选；使用核实空闲的新端口、独立 SQLite 发布冻结候选，源码、清单、报告与实际进程对应一致；保持现有历史树与其他已交付能力，必要兼容变化明确写迁移。

**边界**：只改 `backend/` 与必要 `docs/`，不改 `frontend/`、native 或生产 pin；8792 仅经 GetProbe GET，禁止 validate/assessment POST、运动、RESET、STOP、begin/end、重启与新物理实例；不修改归档、tail 或原始媒体，不扩展点云、标定、导航与训练。

**交付**：验证后普通提交并推送 `codex/backend-m1-services`（现有 liaoGithub 认证，不 force、不改 main、不打 tag）。A、B 都有可核验产物才算完成；若只完成一段，报告部分完成，不再以"M1.5g 已复审计"收尾。本 Goal 不代表跨流同步、生产部署或正式 M1 验收。

## 本 Goal 完成后确认的事实

- 覆盖边界缺陷确实在 `a10b96b` 上成立：同一隔离夹具（两个干净锚点 + 一行不可解析内容）在基线源码上报告 `covers_whole_episode=true`、`any_base_eligible_for_whole_episode=true`、逐基 `blocking_reasons=[]`；修正后同一夹具报告 `reached_end_of_file=true`、`every_line_of_the_anchor_file_is_decided=false`、`covers_whole_episode=false`、逐基阻塞原因 `1_lines_are_undecidable_and_could_hide_anchors`，而 A 仍合格。证据文件为交付册中的 `m1h_repro_baseline.json` 与 `m1h_repro_corrected.json`。
- 真实 COMPLETE 记录的普查未被此次收紧误伤：303 锚点、`undecidable_total=0`、`benign_lines` 两类均为 0，整集资格仍为真；"窗口页 1 帧 + 302 条窗外，census 仍 303 锚点"经真实 HTTP 复现。
- 真实归档的动作／事件词表（有界全量扫描，COMPLETE events 12561 条 12 类、FAILED 224 条 11 类）与共享键实测：`actuator_reference`/`feedback`/`dispatch` 携带 `control_tick_id`（`command_id` 为 null），`requested`/`approved` 携带 `command_id`（`control_tick_id` 为 null），`rgbd_capture_timing` 在负载内携带 `sample_id`/`feedback_sample_id`；`rejected`、`executed/completed/failed` 回执与接管事件在这两条记录中未出现，按 `not_recorded` 交付，不补零、不把审批当执行、不默认 Human。
- 逐帧关联的真实基数：`actuator_reference` 对 303 帧每个捕获 tick 恰一条候选；`dispatch` 仅 1/303 命中自身 tick，其余按 `missing` 报告且不得从相邻 tick 借用。控制来源只出现在 payload 的 `operator_id`/`operator_kind`/`view_source`/`session_id`/`owner_session_id` 字段内，未发现任何 `takeover`/`control_source_change` 事件类型。
- 必需流：真实归档与 run 清单中没有按 Episode 声明的必需流集合（平台侧 `declared_streams` 检查只核对在线能力通告），故 M1"声明必需流重载"只到"引用已有声明、无声明即 unknown"，不自行编造要求。

历史 S14～S27 原文与事实保持不变；本轮只收紧 M1.5g 的覆盖表述并新增动作／事件依据，不撤销任何既有已交付能力。来源字节哈希登记于 catalog.json 与 traceability.json。
