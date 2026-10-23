# M1.2a 前端与后端交接：最小缺口

主责仍为 `docs/specs/30-contracts`；此页仅记录前端投影和待对齐样例，不定义第二套公共 API，也不要求后端返回某个自创聚合端点。

目前平台 `GET /api/v1/mobilecar/preflight` 只返回指定字段的兼容诊断。草案 API 只开放固定 recipe 元数据；验证 failed，Session 创建 unsupported。通用 `/ws` 不是机器人状态流，旧 RunRecord 不是本工作台的 Session。前端不会把这些结果转成 Ready/Owner/执行成功。

| 所需能力 | 最小输入/输出建议（待后端对话按现有契约维护） | 前端当前行为 |
|---|---|---|
| Scene / assets / capabilities | native SceneManifest 几何层级、stable link/object IDs、mesh URI/hash；joint ID、axis、模型/用户零位映射、限位/单位、TCP site/父体 | 使用冻结真实样本；资产 URL 只在服务层解析；G1 任意初态编辑不开放 |
| Actual 与传感器 | run/generation/episode 与 platform Session 绑定、seq/tick、clock_id/source/sim 时间、Frame/单位、base/joints/TCP、相机媒体及时间/失效原因 | 显示冻结采样时刻，媒体缺失；没有伪造连续流或“最新年龄” |
| Target / preview | target revision、Frame/自由度、joint/TCP 输入；IK 状态/残差、候选终点/完整 q(t) 的分别声明、检查级别、有效期、plan_id | 只有本地 Target / FK / position-only IK；没有后端计划，辅助线不叫轨迹 |
| Authority / command | execution scope、source、后端认可的 owner/lease；command ID/seq/TTL/targetRevision/plan_id；Accepted/Rejected/执行终态与原因 | 控制组展示未接入，所有提交/接管禁用；不发 native POST |
| Session / recording | 已验证快照、无副作用 prepared 绑定、显式 Start；录制 RESET 应用身份与实际初态确认、可靠开录、停车与 finalize 独立反馈 | 全部未接入；不将抓取到的原生健康字段映射成平台 Session 或录制成功 |
| Read-only replay | Episode/segment 复合身份、历史 samples/media/events 的 source clock 与统一 cursor；缺失/完整性说明 | 单帧冻结观察不冒称 Episode；连续历史回放在 M1.5 接入且不注入执行服务 |

## 已有 native 样例（不宣称平台已有端点）

以下片段来自真实已冻结样本的同一组身份/单位；完整记录保存在 public/sample。采样不是平台 G1 初始化/验收。

```json
{
  "contract_version": "mobilecar-1.0",
  "model_id": "landerpi_mecanum_dynamic_5dof_3ca3d6d0a92a",
  "scene_id": "mobile_pick",
  "links": [{
    "name": "link1", "parent_name": "back_shell_black_link",
    "joint_name": "joint1", "joint_type": "hinge", "joint_axis": [0, 0, 1]
  }],
  "tcp_site": "grasp_tcp"
}
```

上例只节选身份/层级字段；完整几何还必须保留 `local_transform`（m / xyzw）、geoms、mesh_assets。Actual 读取保留 native `run_id/backend_generation/episode_id/sim_time_s/backend_monotonic_s/wall_utc/clock_id/control_tick_id`；TCP 保留 `frame_id/position_m/orientation_xyzw`。模型关节角 rad 与用户角 rad 不是同一个零位。

待服务端支持后的 TCP 输入/反馈最小语义建议：

```json
{
  "intent": "TCP Target",
  "context": {"session_id": "<bound-session>", "source": "human", "control_scope": "arm"},
  "target": {"revision": 7, "frame_id": "world_sim", "position_m": [0.33, 0.0, 0.30]},
  "constraints": {"position_only": true},
  "mode": "Preview-Confirm"
}
```

```json
{
  "target_revision": 7,
  "preview": {"kind": "endpoint_only", "joint_positions_rad": [0, 0, 0, 0, 0]},
  "frame_id": "world_sim",
  "checks": {"collision": "not_checked", "dynamics": "not_checked"},
  "execution": {"status": "not_submitted"}
}
```

这些是 CT-COMMAND / CT-TIME-FRAMES 的对齐示例，不是已实现的请求 Schema，零向量也不是有效计划证据。后端选择具体路由、单位/零位定义、响应字段和错误码后，仅调整 `src/adapters/` 的映射。当前 `ViewSample` 是内部面板投影；`PlatformService` 没有配置或猜测上述端点，明确报未接入。

待对齐前不增加假 Owner、假 plan_id、静默 fallback 或模拟 Accepted。后端能提供只读 Scene+Actual 时即可先替换冻结源，无需等录制和全部控制接口完成。
