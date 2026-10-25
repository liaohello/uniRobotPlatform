# S23｜真实帧关联只读切片与 run 目录身份边界（2026-10-25）

## 来源类型

平台后端只读切片的实测证据与契约扩展来源（M1.5c）。绑定候选 `m1s-20261025T084308Z-platform`（`http://127.0.0.1:18966`，源码聚合 `932582d19de263ab…`，启动清单 sha256 `6872adad98dbc75f…`）。

## 观察到的事实

1. 缓存的 Episode 索引只保存名字字符串，原有边界检查只覆盖最后一层目录；索引建立后把 `root/runA` 替换为指向 `root/runB` 的软链，会以 `runA` 身份读出 `runB`，且显式带 `run_id` 时不触发 `episode_id_ambiguous`。现要求 run 目录本身不是软链且解析后仍等于 `root/run_id`，沿用既有 `history_path_escape`。
2. 代表记录 `run_0104613ff7364ae78cf2f3946bd45f7b / episode_27bfed5427684795b361cd2ec21e9aa7` 有 303 个持久图像帧。每个 `sample_id` 恰有两个观测行（rgb、depth），606 个 `asset_uri` 全部存在并带 `metadata.asset_sha256`（抽查 6/6 与实际摘要相等）。
3. `sample_id` 对 `transforms.jsonl` 命中 303/303；`capture_control_tick_id` 对 `events.jsonl` 的 `control_tick_id` 命中 303/303，可取得带单位后缀的关节、轮速、底盘与 TCP 状态。
4. 帧声明的 `feedback_sample_id` 只有 3/303 能在观测索引中找到自身 `sample_id` 等于它的观测行；`rgbd_capture_timing` 事件同时声明 `feedback_sample_id`、`feedback_time_s` 与 `feedback_clock=backend_monotonic`。
5. 实测时间差（记录字段相减）：状态事件早于采集 0.340–8.776 ms（首页帧 2.8854 ms），声明反馈时间早于采集 3.668 ms，采集到落盘约 100 ms，观测 `arrival_time_s` 晚于 `measurement_time_s` 33.451 ms。两侧只命名同一时钟基，同源性未验证。
6. 不完整记录 `run_1f6fb34853f94130aadedb8fa486705b / episode_879cf70489064a3b83bb15b5395a8341` 的 4 个持久帧主角色全部命中，4/4 的 `feedback_sample_id` 无对应观测行；另有 1 条 transform 行没有对应持久帧。
7. 本轮经 `GetProbe` 发出的 59 条请求全为 GET；946 文件覆盖集合事前记录、事后复核 `drift=[]`；平台聚焦测试 31 passed，全量 159 passed / 3 项历史布局失败。

## 对设计的影响

- 帧与状态的关联必须按"记录里存在什么键就只用什么键"表达：`matched / partial / missing / unresolved_reference / identity_mismatch / stream_absent` 分开呈现；无键可证时返回缺失，不按文件名、行号、到达顺序或数值相近补造，不插值、不状态保持。
- 时间差与"状态年龄"可以是公开契约字段，但同一时钟基命名不等于同时刻；统一历史时间游标仍需单独设计与验证。
- 只读边界必须覆盖目录身份的动态变化，而不只是静态包含关系；缓存不得成为绕过读取时校验的通道。
- `transforms.jsonl` 仍是相机外参加伴随记录值，不是逐 body 位姿序列；模型摘要相等不构成渲染证明，历史 3D 限制继续保留。

## 效力

本来源为"run 目录身份必须在每次读取时校验""图像—状态关联只能建立在记录键上""未解析引用必须显式呈现""状态年龄不等于同步"提供依据。实现与证据见 [M1.5c 交付记录](../../../backend-m1.5c-frame-linkage.md) 与 [M1.5c 证据册](../../../evidence/m1.5c-frame-linkage/README.md)。
