# S29｜拒绝回执分域与时间接近不提升同步（2026-10-30，M1.5i）

状态：本次用户 Goal 原文（要点保留）。来源：用户在 M1.5h 之后提出的新 Goal。A 段（不可判定行的覆盖边界）已在 `c79d9d6` 交付并由本轮在新候选上复验；本轮新增的是 B 段的两处收口：真实记录到的拒绝回执必须保持"回执"身份，以及任何时间数值接近都不得提升关联或同步声明。

## Goal 原文要点

执行 Goal："修正采集时间资格对不可判定行的处理，并交付历史动作／事件可读取、可分类、可关联到什么范围的最小证据面，为 M1 回放收敛。" 工作目录、分支与基线同前（`codex/backend-m1-services`，已交付基线 `a10b96b`）；先核对实际 HEAD、工作树，保留他人改动；遵守 native 工程的服务器执行政策。

**A. 修正时间资格边界**：`_stream_lines` 会跳过超限、无法解析等行，而 B 模式的整 Episode 资格没有考虑这些不可判定内容；用隔离夹具复现后做最小修正。必须区分"确实扫描到 EOF""能完整解释全部适用锚点""仅剩余可读锚点的时间满足条件"。无法判定的行不得被静默排除后仍证明整 Episode 可调度。明确哪些计数影响何种资格，空白行或已确认无关记录不要一概当损坏。A 追加顺序浏览仍可保留，诊断信息继续可见。更新 blockers、覆盖语义及迁移说明；不重写原始记录。

**B. 动作／事件的最小回放依据**：先对已使用的代表 COMPLETE、FAILED Episode 做有界清单，明确实际存在的 Actual/feedback、actuator_reference 或记录 Target、requested/命令意图、受理、拒绝、下发与执行反馈、控制来源与接管事件、Episode 开始/结束/失败事件。逐项给真实 event type、流、原始位置、时间字段、单位和关联键。没有记录就明确 missing/not_recorded/unknown，不能推定存在。优先复用现有 events records 分页和精确 `event_seq`／命名时间过滤；只有真实事件携带能与帧连接的键时，才增加最小帧关联角色；精确关联保持候选数量、缺失与歧义，不默认取第一条；没有关联键的事件保留为独立事件轨和自身记录位置，不得按时间最近或上一条事件强行归属当前帧。**保持 Actual、Target、意图、受理、下发和执行结果分域。被拒请求不当作已执行 action，actuator reference 不当作 Actual。控制来源缺失不能默认 Human。不因事件时间接近就提升 synchronized 或 same_clock_verified。** 若现有 GET 已能提供所需内容，补齐最小语义元数据、样例和检查即可；若存在具体调用缺口，再做最小扩展；不预先建设通用查询框架、服务端播放 Session 或新的时钟对齐系统。

**前端交接**必须包含：现存可调用请求与实际载荷；哪些事件可以精确关联帧、依据什么键；哪些只能独立浏览、哪些根本未记录；错误／歧义／缺失状态；对"状态、动作及声明必需流可重载"的验收差距。必需流只取已有 manifest/profile 声明，无声明就 unknown，不自行编造训练数据要求或补零动作。

**验证**：所有测试、HTTP 检查在授权服务器执行；覆盖坏行、超限、缺时、回退、重复 ID，以及事件缺失／多候选／**拒绝**；真实归档验证与 synthetic 夹具分列，保留原始事件值；运行聚焦与统一能力适用回归，按项目要求做健康检查；历史三项布局失败单列，不跳过、不称全绿。

**候选发布**：18979 和 18977 保持稳定，前端当前 Goal 不等待本候选；用实际空闲并登记的端口、独立 SQLite 发布新冻结候选；源码、启动清单、报告与实际监听进程对应一致；保留 geometry、Map/Route、Session、STOP/end、历史树和八条历史读取能力；必要扩展如改变兼容性应明确迁移，不能只称新增字段。

**边界**：只修改 `backend/` 和必要 `docs/`，不改 `frontend/`、native 工作树或生产 pin；8792 仅经 GetProbe GET，禁止 validate/assessment POST、运动、RESET、STOP、begin/end、重启及新物理实例；不修改历史 tail、媒体或归档；不进入点云、标定、导航或训练。交付后普通提交并推送当前后端分支（现有 liaoGithub 认证，不 force、不改 main、不打 tag），更新契约、交付记录、证据和 handoff。

## 本轮新增确认的事实

- **真实记录到的拒绝保持回执身份**：代表归档本没有 `rejected` 记录（如实记 `not_recorded`）；合成夹具补写一条 `rejected`（`decision.approved=false`、`reason=outside_declared_workspace`、`control_tick_id=null`）后，它会出现在 `categories.command_receipt_rejected`（`status=observed`、`counts={rejected:1}`），命令链显示该命令只有 `requested→rejected`、没有 `approved`/`dispatch`，且**从不出现在任何帧关联里**（关联类型集合恒为 `actuator_reference`/`dispatch`/`feedback`/`feedback_initial`）。已批准命令仍是唯一被下发的命令。
- **时间数值接近不提升关联或同步**：同一夹具把被拒回执的 `backend_monotonic_s` 设为与第二个帧的 `capture_backend_monotonic_s` **完全相等**且不带任何 tick；真实归档侧实测命令意图/受理的时间戳与某帧采集时间相差仅 **15.8 ms**。两种情况下读者都不建立关联（关联只按 `control_tick_id` 精确相等），`same_clock_verified`、`synchronized_across_streams`、`clock_sameness.verified_by_reader` 全部保持 false，`clock_parity` 规则明写"数值接近甚至相等都不提升链接"。
- **原始事件值不被改写**：被拒回执仍可从既有 `streams/events/records` 路由按 `event_seq` 窗口逐字读回（含原 `reason` 与原始时间戳），本轮不重写任何归档记录。

历史 S14～S28 原文与事实保持不变。来源字节哈希登记于 catalog.json 与 traceability.json。
