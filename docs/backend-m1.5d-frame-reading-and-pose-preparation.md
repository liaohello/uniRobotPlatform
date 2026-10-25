# M1.5d｜帧读取分页与角色完整性修正、时间语义分离与历史姿态准备（2026-10-25）

状态：候选实现完成并服务器验证；不等于统一历史游标可用、历史渲染通过、同步回放可用或 M1/M1.5 验收通过。

契约的唯一权威来源是 [Episode/事件/标注契约](specs/30-contracts/03-episode-events-annotations.md)；本文件只记录实现取舍与实测证据。实测明细见 [M1.5d 证据册](evidence/m1.5d-frame-reading-and-pose/README.md)，事实来源登记为 [S24](specs/90-governance/sources/S24-frame-reading-and-pose-preparation.md)，决策为 [DEC-061](specs/90-governance/01-decisions.md#dec-061)。

## 做了什么

1. **分页判定修正**（`backend/src/unirobot/frames.py`）。`has_more` 不再比较"预过滤后的记录数"和"原始行号"，而是整页装满后继续扫描、遇到下一条合格锚点即停；`next_offset` 保持锚点文件原始行号语义，并新增 `next_qualifying_anchor_line_index`、`post_page_records_examined`、`scan.whole_file_scanned` 与 `anchor_lines`（读过的行、空行、超限行、坏行、非对象行、预过滤行分别计数）。样本装满时不假装扫描过整份文件，越过文件末尾才说没有下一页。`_stream_lines` 增加计数出参，`records()` 行为不变。
2. **角色完整性判定修正**。新增 `ROLE_REQUIREMENTS`：`image_observation` 要求必需 `sensor_kind`（`rgb`、`depth`）各恰一条，单记录角色要求 `exact_records: 1`；新增状态 `ambiguous_kind`、`ambiguous_candidates` 与公开优先级 `STATUS_PRECEDENCE`，角色响应给出 `required/matched/missing/duplicate/unexpected_kinds`、`kind_inventory`、`candidate_line_indexes`、`ambiguous_records`（含逐候选 `conflicts_with_first`）。状态与时间不再从多候选里取第一条：候选不唯一时 `recorded_state=null`、`single_state_selected=false`，全部候选带行号与负载列出。媒体项按 kind 聚合全部候选行，`agrees_with_observation_row` 表示"某个候选声明了该 uri"，并在多候选时给出 `observation_rows_conflict`。`unresolved_reference` 继续与主角色完整性分开。
3. **时间语义分离**。`times` 改为 `quantities`：每条差值由 `TIMING_QUANTITIES`/`SIM_TIME_QUANTITY` 固定其记录来源、字段、单位、时钟与含义；删除 `age_of_state_relative_to_frame`，新增 `recorder_declared`（原样复制录制器自己的 `observation_age_ms` 等时延字段 + 重算 `arrival − capture` + 一致性判定）、`semantics_rule`、`state_time_quantity_keys` 与 `version_migration`（`frame-link-1 → frame-link-2` 的变更、移除字段与兼容性说明）。`time.clock_sameness` 重写为"记录命名了什么 / 读取方能证明什么 / 写入版本能绑定到什么"，并明确 `synchronized_upgraded_by_numeric_closeness=false`。schema 版本升为 `unirobot-mobilecar-frame-link-2`。
4. **历史姿态与固定模型准备切片**（新增 `backend/src/unirobot/history_pose.py`）。`GET /api/v1/episodes/{episode_id}/robot-state` 复用帧关联规则取该帧状态，比对 run 清单身份与冻结 geometry bundle `resource_identity`，逐目标给出映射状态（`verified/partially_verified/unverified/missing/not_required_for_pose`）、证据、单位和 `no_default_applied`；未证实的底盘原点语义、四元数参考系、夹爪宽度→关节值规则、TCP 朝向与相机标定保持未证，不填默认值；动态世界物体明确"无历史记录位姿、不伪造"。`GET /api/v1/episodes/{episode_id}/model/assets/{asset_id}` 只从冻结 bundle 出字节（逐请求重算摘要 + ETag），服务前要求该 Episode 模型身份相符，不代理当前 `/mobilecar/scene`、snapshot 或 Actual。`episodes.py` 新增公共读取入口 `run_identity()`（复制 run 清单身份字段），路由与既有 6 条 GET 保持兼容。
5. **测试**：`backend/tests/test_frames.py` 扩到 20 项，新增重复 rgb 缺 depth、重复状态候选、空行/坏行/超限行与越过末尾分页、三个时间量互不折算、`robot-state` 映射与身份不符、mesh 摘要不符/未知资产、无 bundle 时 503 等隔离夹具用例；真实归档只读，任何夹具都在 `tmp_path` 内构造。

## 服务器实测

- 候选 `m1v-20261025T161014Z-platform`（`127.0.0.1:18969`，pid 3923606，独立 SQLite，清单 sha256 `8e32f91f6cf2a24f…`，源码聚合 `d022239329c0518d…`／47 文件）。
- 读取断言 **102/102**（含 40 项帧/姿态相关）；64 条 native 请求全为 GET；覆盖集合 946 文件 `drift=[]`；统一能力回归 **28/28**；聚焦 **39 passed**；全量 **167 passed / 3 failed**，失败为既有三项历史布局用例，名称与基线保留。
- 真实数值：状态事件写入早于采集 2.885407 ms、状态负载采样戳早于采集 3.669841 ms、录制器声明反馈时间早于采集 3.668296 ms（后两者相差 1.545 µs），`sim` 基差值为 0，`observation_age_ms = 33.451169` 等于 `arrival − capture`；`arm_model_qpos_rad` 5 值对应 bundle `joint1…joint5`，逐位凭证仅索引 3（`−π/2` 偏移，平台配置该处写为 `-1.5708` 四舍五入值）；模型/场景身份四项与 bundle 全等，23 个 mesh 资产逐文件校验。
- 中断记录：`m1t-…`（18967）与 `m1u-…`（18968）因检查工具自身缺陷（对整数取 `len()`；把外层 `body` 重新绑定为字节）未产出绑定报告，进程与目录保留为历史、未倒填；`tools/` 在摘要根内，故工具修正随新 release 生效。

## 未做与下一步

- 不做渲染：`rendering.verified=false`、`frontend_assembly_done=false`。下一轮前端据此做装配、姿态与切换验证。
- 不补标定与坐标语义：底盘位置参考系/原点、夹爪宽度→关节值、TCP 朝向、相机外参标定需要新的凭证来源（native 侧声明或经批准的标定资产），本轮只登记精确缺口。
- 不做跨流同步游标、不扩归档全量验证、不接新采集闭环、不改 native/前端/生产 recipe 与 pin。
- 检查工具仍需避免复用外层变量名（本轮两次中断的原因），并保持"报告↔冻结字节"断言。
