# S20｜统一可联调候选与部署前发布身份

日期：2026-10-25。角色：用户；记录性质：本次会话当前 Goal 文本的转存，保留原始语义与边界，不改写历史来源。

用户要求（摘要）：

- 发布新的统一平台候选，不替换现有端口：在同一冻结源码、启动配置与 OpenAPI 中同时提供验证后的 geometry-2 scene 与 23 个资产、capabilities/snapshot/kinematics、Map/Route 持久化资源、Draft/validate、Session envelope/current、M1.4 STOP/end schema/回执/availability。复用已核验几何包，固定路径、摘要与来源，不重新导出不必要的模型，不开启第二个物理实例。
- 明确冻结发布配置：平台源码、geometry bundle、map catalog/资源根、recipe、数据库命名空间、native 地址与实际端口；说明新候选如何读取既有资源或使用独立测试数据；不覆盖旧 SQLite，不伪造旧资源迁移完成。
- 几何读取兼容与执行资格分开：geometry-2 有效不等于 profile/readiness 通过；真实 native 未声明协议时 prepared/Start/begin/STOP/end 继续按真实原因拒绝；不得换标签或放宽 pin 制造 Passed；不把 `/runs/{id}/stop` 当作机器人 STOP。
- 澄清并修正候选身份：`c550…` 仅为旧白名单子集摘要，不覆盖新增 `attestation.py`/`session_binding.py`，不能当完整 release pin，也不能据此声称 drvfix+m1h 已组装验证；保留既有 198 文件清单与历史证据，不改写其事实。
- 为待部署候选形成可复现的完整发布身份：明确基线、补丁、所有新增执行模块、配置/模型/锁文件，说明清单排除范围；必需路径缺失必须失败，不使用“只哈希存在文件”掩盖缺项；候选清单与生产 pin 分开，未获选择前不激活生产 recipe；不构建无必要的通用签名系统。
- 修正维护流程顺序：先完成最终 release、完整 pin、recipe/protocol、config/scene/lock 的冻结与核验，再进入已获授权的维护窗口和实际动作；不把更新生产 pin 放到 begin/STOP/end 成功之后；明确 G1/G4A2、a5/drvfix 尚待决定；推荐不等于授权，未经完整组装验证不承诺某基线可直接部署。
- 验证与交付：所有测试/构建/集成在服务器执行；先检查端口，使用独立 release/回环端口与测试目录；对统一候选验证 geometry-2、资产摘要、持续 Actual、真实地图/路线、配置/current 以及 STOP/end 的生产拒绝；正向生命周期继续使用明确 test-only recipe、mock backend、实际 native HTTP 与真实 Recorder，不冒充生产 G1 或物理验证；新增完整清单验证须证明新增执行模块被覆盖且缺文件/摘要不符能被发现；运行改动相关检查并保留全量失败项，历史失败归因需给出可核对基线，缺证据标待确认，不跳过或笼统称全绿；交付一个前端可直接消费的统一候选地址、启动配置清单、OpenAPI、源码/资产摘要、回归与限制；更新 handoff 为真实最新端口，不把前端暂停旧记录当当前授权。
- 边界：不修改 `frontend/`；平台本地提交、不推送；native 既有未提交补丁保持，候选变更单独记录，不提交/推送 native；不停止/重启/替换 8792，不发送任何真实 native 写请求，不执行物理停车、运动、录制或训练。
- 完成定义：Goal 完成只表示统一联调候选与部署准备完成，不表示生产已部署或 M1 闭环通过。

效力：本来源为统一候选的发布范围、"几何读取兼容 ≠ 执行资格"的判定要求、候选身份与完整发布身份的严格性，以及维护窗口先后顺序提供依据。实现与证据见 [M1.4b 交付记录](../../../backend-m1.4b-unified-candidate.md) 与 [M1.4b 证据册](../../../evidence/m1.4b-unified/README.md)。
