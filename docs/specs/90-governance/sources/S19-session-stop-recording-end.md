# S19｜受 Session/运行身份约束的机器人 STOP 与录制可靠结束

日期：2026-10-24。角色：用户；记录性质：本次会话当前 Goal 文本的转存，保留原始语义与边界，不是历史来源的改写。

用户要求（摘要）：

- 交付"受 Session/运行身份约束的机器人 STOP 与录制可靠结束候选"。这是候选实现与**无物理**集成验证，不包含部署，也不操作 8792。
- 确定最小 STOP 与录制结束请求/回执并更新 OpenAPI，清楚区分：请求受理；STOP 下发/执行反馈；实际停车证据及覆盖范围；Recorder drain/finalize；Episode/segment 终态与完整性。不能把 `accepted`、`base.stopped`、`complete_tail` 或文件存在单独当作"整机停稳且录制完整"。
- 优先复用 native 既有停止与 Recorder 收尾流程；不以 `POST /api/v1/runs/{run_id}/stop` 替代机器人 STOP；不重写 Recorder；不附带 RESET、清安全锁、获取 Owner 或恢复运动。
- 普通录制结束必须绑定本 Session、binding、run/generation/episode/segment，防止结束其他 Session 或新录制。既有 legacy `episodes/stop` 只有 reason，不能靠"平台先 GET 校验再 POST"声称获得原子身份保护。如确需 native 扩展，只制作最小补丁候选，在 lifecycle 临界区重检身份。新增能力必须显式声明，不能把 `m1-recording-1` 擅自解释为已包含 end。
- 保留 lifecycle → backend → recorder 顺序、prepared-only TTL、`require_recording`、租约与安全停止规则。安全 STOP 不以 `motion_ready`/`recording_ready` 为前置条件；不新增会阻止既有紧急停止的 Owner/lease 门槛。失联或反馈不足时报告未知/未确认，不伪造已停止。
- 处理同一请求重复、超时结果未知和并发结束：重试不得产生重复尾事件、结束后来的 segment 或误清历史失败；停车超时与 finalize 结果分别保留；`FAILED`/`INCOMPLETE`、有尾但失败、drain/finalize 失败缺尾分别可诊断；`current` 只读观察继续不触发任何控制副作用。
- 完成隔离集成：实际平台客户端 → 真实 native HTTP → 真实 Recorder 文件系统，backend 使用明确标注的 mock；覆盖 begin → STOP/end → 重复请求 → 回读，以及错误身份、并发、停车未确认与收尾失败的适用路径，核对事件、segment、文件哈希、终态与回执。测试专用 recipe 明确 test-only，不得修改生产期望来制造 Passed。
- 提供前端可直接接线的 OpenAPI、请求/响应与错误样例，把真实生产拒绝、mock 成功、尚未执行的物理验证分别标注。修正交接中的当前端口/版本；将 Map/Route 资源切片与正式 M1.3/M1.4 完成状态分开。

执行与交付边界（用户原文要点）：

- 所有测试、构建和集成在服务器执行。使用检查后确认空闲的新回环端口和独立记录目录；不启动第二个物理仿真实例，不替换 18953。
- 对 8792 只允许 GET；不得 STOP、RESET、begin/end、重启或替换。
- 保留 native 既有未提交补丁；新增候选记录基线、patch 和源码摘要。不提交/推送 native，不复用旧 source pin。
- 不修改 `frontend/`，不实现导航、Owner 获取、运动遥操作、训练或回放 UI。
- 执行聚焦及适用全量检查；历史 3 项布局失败单列名称和基线，不跳过、不称全绿；本轮新增回归必须解决。
- 冻结独立候选，保存源码清单、HTTP/文件证据和前端迁移说明。平台本地提交，不推送。
- 更新既有维护/回滚方案，明确仍待决定的 profile、部署基线及新 pin；推荐方案不视为部署授权。
- Goal 完成只代表停止与录制收尾候选完成，不代表 8792 已部署、真实停车已验证或 M1 闭环通过。
- 基线更正：最新前端为 18951 → 18949，不沿用"当前只有 18950"的旧记录；`POST /runs/{id}/stop` 是进程/记录管理，不是机器人停止。

效力：本来源为 `m1-stop-1`/`m1-end-1` 候选协议、回执分层判据、并发与幂等规则、隔离集成范围与"候选≠部署"边界提供依据。实现与证据见 [M1.4 交付记录](../../../backend-m1.4.md) 与 [M1.4 证据册](../../../evidence/m1.4-stop-end/README.md)。
