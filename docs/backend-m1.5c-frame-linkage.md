# M1.5c：run 身份边界最小修正 + 一条真实 Episode 的图像—机器人状态关联切片

日期：2026-10-25。工作树：`/home/liaozhengyan/.codex/worktrees/backend-m1-read/uniRobotPlatform`，分支 `codex/backend-m1-services`。
上一轮基线：M1.5b（`08b9d57` 代码、`1f7f88e`/`90f7101`/`f25855f` 文档与链接修复、候选 `m1p-20261025T053030Z-platform`）。

## 一、结论

| 问题 | 结果 | 证据 |
|---|---|---|
| 缓存索引建立后 run 目录被替换为 root 内另一 run 的软链，能否仍以原 run 身份读取 | 不能。每次构造读取位置都重新验证 run 目录身份，拒绝该替换 | [episodes.py:require_run_directory](../backend/src/unirobot/episodes.py)，隔离夹具 2 项 |
| 一条真实 Episode 的图像帧能否与机器人状态建立**只依据记录键**的关联 | 能。代表记录 303 个持久帧全部通过 `sample_id` 关联到 rgb/depth 观测行与 transform 行，通过 `capture_control_tick_id == control_tick_id` 关联到 `feedback` 事件 | 冻结候选实测读取检查由 69 项增至 86 项（新增 17 项帧/关联/媒体断言） |
| 记录声明的 `feedback_sample_id` 是否总能找到对应观测行 | 否，实测 3/303 命中。读取侧把它作为 `unresolved_reference` 返回，不补造、不按时间相近顶替 | 同上 |
| 是否已经具备统一历史时间游标 | 不具备。本切片只提供单 Episode 内的帧关联与实测时间差；跨流/跨 Episode 游标与同步 3D 仍未证明 | 见第九节 |

**本切片完成不等于历史归档全量验证、同步 3D 回放或 M1.5/M1 验收通过。**

## 二、run 身份边界的最小修正

缓存的 Episode 索引只保存名字字符串（`episode_id -> [run_id]`），原先的边界检查只判断最后一层目录是否软链以及是否仍在 root 内。因此索引建好后把 `root/runA` 换成指向 `root/runB` 的软链，`runB` 中同名 Episode 会被以 `runA` 的身份读出，且 `episode_id_ambiguous` 不会触发（请求显式带了 `run_id`）。

修正只加一条规则并被两处共用（[backend/src/unirobot/episodes.py:168](../backend/src/unirobot/episodes.py#L168)）：

- `require_run_directory(root, run_id)`：run 目录本身不得是软链，且解析结果必须等于 `root/run_id`；否则沿用既有 `history_path_escape`（409），detail 为 `{episode_id, run_id, run_directory_is_symlink}`。不回显软链指向的路径，避免顺带泄露同级 run 的位置。
- 每次 `EpisodeLocation` 构造时先做该检查（所有读取路径都经过它，包括列表分页），`_run_manifest` 也改为经同一入口解析，被替换的 run 不会再读到兄弟 run 的 manifest。
- 错误码、状态码与既有路径语义保持不变；没有新增文件系统沙箱层。

隔离夹具覆盖（真实归档未被修改）：`test_run_directory_swapped_for_a_sibling_run_is_refused_after_the_index_is_cached`（四条读取路由都返回 409，响应体不出现 `run_bbb` 与其内容，兄弟 run 自身仍可正常读取）、`test_run_directory_identity_is_checked_on_every_read`（含 manifest 入口）。

## 三、真实关联事实（服务器实测，非推断）

代表记录 `run_0104613ff7364ae78cf2f3946bd45f7b / episode_27bfed5427684795b361cd2ec21e9aa7`（COMPLETE/COMPLETE，`contract_version=mobilecar-1.0`）：

| 记录 | 数量 | 关联事实（实测） |
|---|---|---|
| `observations/persist.jsonl` | 303 | 每条即一个持久图像帧，带 `run_id/episode_id/stream_id/sample_id/kinds/persist_sequence`、`capture_backend_monotonic_s`、`capture_sim_time_s`、`capture_control_tick_id`、`feedback_sample_id`、`rgb_uri/depth_uri/valid_mask_uri`、`arrival_to_persist_ms/capture_to_persist_ms`、`profile_id/profile_version/profile_sha256` |
| `observations/index.jsonl` | 3038 | 每个 `sample_id` 恰有 2 行（`sensor_kind=rgb` 与 `depth`）；`asset_uri` 非空 606 行、`valid_mask_uri` 非空 303 行（在 depth 行上），606 个 uri 全部在 `assets/` 下存在；`metadata.asset_sha256` 覆盖同样的 606 行，抽查 6/6 与实际文件摘要相等 |
| `transforms.jsonl` | 303 | `sample_id` 与持久帧一一命中（303/303，反向 0 多余）；`frame_id=rgbd_optical`、`clock_id=backend_monotonic`、`metadata.transform_version=g2a-transform-1`，含 `T_base_link4/matrix_storage`；**不是逐 body 位姿序列** |
| `events.jsonl` | 12561 | `rgbd_capture_timing` 303 条，`payload.sample_id` 一一命中；同条 payload 还声明 `feedback_sample_id`、`feedback_time_s`、`feedback_clock=backend_monotonic`；`feedback` 6074 条按 `control_tick_id` 与帧的 capture tick 关联，实测 303/303 命中 |
| `joint_feedback` 观测行 | 608 | 其自身 `sample_id` 形如 `joint_feedback_000007120`，但只有 3 个等于某帧声明的 `feedback_sample_id`；`value` 携带 `model_joint_positions_rad/user_joint_positions_rad/joint_velocities_rad_s/joint_torques_nm/gripper_width_m`，`frame_id=arm_base` |

时间实测：`state_event.backend_monotonic_s - frame.capture_backend_monotonic_s` 全为负，范围 **-0.008776 … -0.000340 秒**（即状态记录早于采集 0.34–8.78 ms），首页第一帧为 **-2.885 ms**；`rgbd_capture_timing` 自己声明的 `feedback_time_s` 与采集差 -3.668 ms；`persist - capture = +0.100 s`（与 `capture_to_persist_ms≈99.4` 一致）；观测行 `measurement_time_s` 与采集同值，`arrival_time_s` 晚 33.45 ms。这些是**记录字段相减**得到的年龄，不是同步证明：两侧的 `clock_id/backend_monotonic_s` 命名同一时钟基，但读取侧不验证两个写入者是否共享时钟（`clock_sameness.verified_by_reader=false`）。

不完整记录 `run_1f6fb34853f94130aadedb8fa486705b / episode_879cf70489064a3b83bb15b5395a8341`（FAILED/INCOMPLETE）实测：4 个持久帧的四个主角色全部 matched，4/4 的 `feedback_sample_id` 无对应观测行；另有 1 条 transform 行没有对应持久帧（索引锚点来自持久帧，故不出现在响应里）；index 中 rgb 行 5、depth 行 4。

## 四、契约：`unirobot-mobilecar-frame-link-1`

唯一 schema 来源是运行中的 OpenAPI 与响应自身；实现只有一份：[backend/src/unirobot/frames.py](../backend/src/unirobot/frames.py)。

新增一条只读路由（历史面从五条 GET 变为六条，全部仍为 GET，无写入代理）：

```
GET /api/v1/episodes/{episode_id}/frames
    ?run_id=&stream=rgbd&limit=50&offset=0
    &time_base=capture_backend_monotonic_s|capture_sim_time_s|persist_backend_monotonic_s&time_from=&time_to=
    &sample_id=
```

- 锚点是 `observations/persist.jsonl` 的一条记录 = 一帧；`offset`/`next_offset`/`has_more` 沿用 records 页语义（锚点流的原生追加顺序行号），`line_index_is_not_a_clock=true`，`persist_sequence` 只是记录者自己的计数器。
- 角色与关联键固定：`image_observation`(sample_id)、`camera_transform`(sample_id)、`capture_timing_event`(payload.sample_id)、`state_feedback_event`(control_tick_id)、`feedback_observation_row`(sample_id = 帧声明的 feedback_sample_id)。
- 状态词汇：`matched / partial / missing / unresolved_reference / identity_mismatch / stream_absent`，每种含义写在响应 `linkage.status_meaning` 里。
- `linkage_status` 只统计四个主角色；`feedback_observation_row` 单列为 `declared_reference_status`，避免把"记录声明了一个找不到目标的引用"混进"关联失败"。
- 选样规则显式声明：只做记录键相等；不做状态保持（`carried_over_from_another_frame=false`）、不插值（`interpolated=false`）、不按时间取最近（数值相近不等于同一）、不按行号或浏览器到达顺序。
- 每条关联带可回溯位置：`record_position="<相对路径>#<line_index>"`、`identity.{run_id_matches,episode_id_matches}`；声明身份与请求不符的候选被剔除并计入 `identity_mismatched_records`。锚点自身也校验（`excluded_anchor_identity_mismatch`）。
- 媒体只报现状：`availability=present|absent|refused|not_recorded_on_this_frame`、与观测行 uri 是否一致、观测行声明的 `asset_sha256/asset_bytes`（摘要仍是声明，只有资源端点真正服务该文件时才重算）。
- 时间：`times.deltas` 逐条给出 `label/from/to/value_s/abs_value_ms/direction/basis`；`age_of_state_relative_to_frame` 给出毫秒年龄与"状态早于采集"布尔值；`same_clock_verified=false`、`synchronized_across_streams=false`。
- 3D 边界保持：`three_d_replay.this_slice_does_not_enable_3d_replay=true`、`live_geometry_or_actual_may_be_applied=false`、`transforms_are_full_per_body_pose_sequences=false`；transform 行只回显 `frame_id/clock_id/source/metadata_keys`，矩阵与关节数组不在此端点复制。

## 五、真实请求与响应（冻结候选实测）

| 文件 | 内容 |
|---|---|
| `frame-sample-complete.json` | COMPLETE 记录首页 1 帧：四主角色 matched、`declared_reference_status=unresolved_reference`、`age_ms=2.8854069532826543`、三个 uri 全 present 且 rgb/depth 与观测行一致 |
| `frame-sample-second-page.json` | `offset=1` 的第二帧，行号与 `persist_sequence` 递增 |
| `frame-sample-incomplete.json` | FAILED/INCOMPLETE 记录 4 帧，主角色全 matched、引用全 unresolved |
| `error-unsupported-time-base.json` | `time_base=wall_utc` → 400 `time_base_unsupported`，附可选基列表 |
| `error-invalid-sample-id.json` | `sample_id=bad!token` → 400 `sample_id_invalid` |
| `openapi.json` | 六条历史路径，方法集合均为 `{"get"}` |

隔离夹具构造的错误/缺失情形在证据册单独标注（`unresolved_reference`、软链媒体 `refused`、无持久帧流、同名 Episode 跨 run 拒绝等），不与真实归档结果混写。

## 六、错误样例

| 情形 | HTTP | code |
|---|---|---|
| Episode 没有 `observations/persist.jsonl` | 404 | `episode_stream_unavailable` |
| 未知 `time_base`（含 `wall_utc`） | 400 | `time_base_unsupported` |
| 给了 `time_base` 却没有边界 | 400 | `time_range_required` |
| `sample_id` 不是原生 id token | 400 | `sample_id_invalid` |
| 选中时间基在锚点记录上缺失 | — | 计数 `records_missing_selected_time_base`，不补值 |
| 候选记录声明别的 run/Episode | — | 角色 `identity_mismatch`，剔除并计数 |
| run 目录被替换为软链 | 409 | `history_path_escape` |
| 媒体 uri 逃出 Episode 的 `assets/` | — | 该项 `availability=refused`，`refusal_code=episode_asset_escape` |

## 七、前端迁移说明

- 帧回放先取 `frames`，用 `paging.next_offset` 翻页，用 `anchor.persist_sequence` 显示"记录者自己的序号"，但游标推进依据行号顺序；不要把 `line_index` 当时间。
- 展示机器人状态时同时显示 `state.source.event_seq` 与 `times.age_of_state_relative_to_frame.abs_ms`（"状态早于采集 X ms"）；`unresolved_reference` 应渲染为"记录声明了引用但归档中没有该观测行"，不能画成"状态缺失"或"已同步"。
- 需要像素/深度负载时按 `media.items[].uri` 走既有 `assets` 端点；`availability` 非 `present` 就显示缺帧，不要按文件名推测。
- `three_d_replay` 三个布尔位与 `not_proven` 必须原样透出；本切片不提供逐 body 位姿，历史 3D 仍不可用。
- 时间基只有三个可选（`capture_backend_monotonic_s / capture_sim_time_s / persist_backend_monotonic_s`），窗口参数是数值秒。

## 八、验证（全部在授权服务器执行）

- 隔离副本运行冻结 release：**聚焦 31 passed**（`test_frames.py` 12 + `test_episodes.py` 19），其中新增覆盖 run 目录替换、真实形状关联、缺失/软链媒体、引用未解析、时间基与有界分页、跨 Episode 候选剔除。
- 全量：**159 passed / 3 failed**；三项历史失败名称与基线不变：`test_catalog::test_catalog_loads_real_tasks`、`test_catalog::test_every_task_has_existing_evidence`、`test_migrate::test_manifest_sources_exist`（断言仓库文档/外部工程布局，在 release 副本内不成立）。不使用"全绿"表述。
- 读取检查（含帧切片）对真实归档：**86/86**，`requests.methods=["GET"]`、`total=59`、`platform_source.match=true`（recorded=recomputed=`932582d19de263ab…`）、覆盖集合 946 文件 `drift=[]`。
- 统一能力回归：**28/28**（geometry-2、Map/Route、Draft、Session/current、STOP/end、既有历史五条 GET 全部继承）。
- native 8792 只经 `GetProbe` 发 GET；`GetProbe` 的保证仅覆盖经它发出的请求，不是所有工具或人工会话的全局网络门控。8792 未重启（连续运行 6 天以上），状态仍为 `run_9c88e3e3…/gen 1/episode_43c22f95…`。

## 九、发布与运行登记

| 项 | 值 |
|---|---|
| 交付候选 | `m1s-20261025T084308Z-platform`，`http://127.0.0.1:18966` |
| 源码聚合摘要（46 文件，roots `src/unirobot`/`config`/`tools`） | `932582d19de263ab6a74cc8f5e85b77caf309edf0dc474b92b000a5727263a04` |
| 启动清单 sha256 | `6872adad98dbc75fb253e18725c81309b53d0a4c40c03d573c72d4298404a9d4` |
| 进程 | PID `3668527`，启动 `Sun Oct 25 16:43:08 2026`（本地），owner `liaozhengyan`，完整 argv 见 `launch-registry.json` |
| 数据库 | 独立新文件 `…/var/reports/m1s-…/frames-20261025T084308Z.sqlite3`（`existed_before=false`，未覆盖任何旧库） |
| 保留未动 | 18964（m1p）、18960、18959、18953、18949、18961/18962/18963（他人服务）、native 8792 |
| 被取代的同轮尝试 | `m1q-20261025T084007Z-platform`（PID `3492357`，`http://127.0.0.1:18965`，聚合 `71e984c347416da3…`，清单 sha `fd62b390…`）：检查工具里一条帧断言写死了默认页大小导致读取检查中途中断，`history-check.json` 未生成。平台代码字节与 m1s 相同，差异只在 `tools/`；作为历史保留，未回填、未删除，进程仍存活未清理。另有一次 sed 变量替换失误产生的空 `m1r-…` 目录（无 backend、仅一份失败启动日志），已删除，因为其中没有证据价值。 |

复现：

```bash
REL=$HOME/Desktop/uniRobotPlatform/releases/m1s-20261025T084308Z-platform
R=$HOME/Desktop/uniRobotPlatform/var/reports/m1s-20261025T084308Z-platform
cd $REL/backend && PYTHONPATH=src $PY tools/episode_history_check.py --platform-url http://127.0.0.1:18966 \
  --native-url http://127.0.0.1:8792 --source-config config/mobilecar-history-source.json \
  --complete-episode run_0104613ff7364ae78cf2f3946bd45f7b:episode_27bfed5427684795b361cd2ec21e9aa7 \
  --failed-episode run_1f6fb34853f94130aadedb8fa486705b:episode_879cf70489064a3b83bb15b5395a8341 \
  --startup-manifest $R/history-startup.json --probe-log $R/get-probe-log.jsonl \
  --coverage-out $R/coverage-digests.json --out $R/history-check.json
curl -sS "http://127.0.0.1:18966/api/v1/episodes/episode_27bfed5427684795b361cd2ec21e9aa7/frames?run_id=run_0104613ff7364ae78cf2f3946bd45f7b&limit=1"
```

## 十、边界与未覆盖

- 未证明：跨流/跨 Episode 的统一历史游标；两侧命名同一时钟基是否真是同一时钟；`rgbd_capture_timing` 声明的 feedback 时间与实际状态记录时间的等价性；历史 3D 渲染正确性；逐 body 位姿可否由现有流重建。
- 未覆盖：`observations/persist` 之外流作为锚点的帧关联（本切片锚点只有持久图像帧）；transform-only / index-only 样本的对外呈现（锚点集合之外）；资产字节的全量摘要复核（只重算实际被服务的那几个）；除 946 覆盖集合以外的归档文件；训练资格。
- 未做：native 任何写请求、8792 变更、物理运动/录制/RESET/训练、历史 tail 修补、原始归档修复、`frontend/` 改动、native 提交/推送、生产 pin 变更（`mobilecar.g1.teleop` rev 3、指纹 `4c3e5f42…` 未动）。
- 完成含义：run 身份边界修正与帧关联切片交付完成；不表示统一游标可用、历史归档已全量验证或 M1.5/M1 通过。
