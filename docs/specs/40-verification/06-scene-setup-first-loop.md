# 当前 mobileCar 闭环、宿主复用与后续完整流程验收

规范 ID：`QA-SCENE-FIRST-LOOP` · 责任层：验收 · 版本：V0.6（2026-10-22）

来源：[S16](../90-governance/sources/S16-mobile-first-spec-repair.md)、[S15](../90-governance/sources/S15-scene-setup-first-loop.md)。以下均为待执行产品验收，文档和图片检查不等于产品通过。

[三图页面](../10-frontend/page-designs/02-scene-setup.md) · [任务字段](../10-frontend/02-scene-setup/02-task-template-configuration.md) · [配置契约](../30-contracts/07-task-scene-experiment-config.md) · [完整闭环](../00-overview/10-first-task-closed-loop.md)

| ID | 验收场景 | 预期与所需证据 |
|---|---|---|
| <a id="test-mobile-001"></a>TEST-MOBILE-001 | M1：mobileCar 场景→运行→录制→重新加载回放 | 仅选择真实支持的预设/初态字段；准备不触发运动/RESET/录制，创建绑定快照的 prepared Session。显式 Start 后保留原生控制/录制门控；start 的 RESET/生效初态独立核验。accepted/RECORDING 后才确认采集，结束返回实际停车反馈与 Recorder 终态；取得原生 Episode/segment 身份并重载状态/动作/所声明必需流。回放只读不控制在线实例；训练资格 false 不阻止 M1。 |
| <a id="test-mobile-002"></a>TEST-MOBILE-002 | M1：录制收尾失败、缺尾与 RESET 边界 | 起始写入失败不标 recording-ready；STOP 未停稳与 finalize 结果分别显示。COMPLETE、FAILED/INCOMPLETE、complete_tail 不互相替代；已写数据/诊断保留。RESET 显式形成原生 epoch/Episode/segment 边界，不支持录制中 RESET 则先 end 并禁用该动作；旧上下文命令不重放，缺尾不冒充完整。 |
| <a id="test-host-001"></a>TEST-HOST-001 | M2：mobileCar 与 bimanual/轻宿主复用组件 | 按宿主/草案注入 store、能力、订阅和命令服务；选择/视角/草案互不串写，同一 draft 跨宿主保存冲突明确。不同机器人使用原生单位/动作适配；两个宿主访问同一运行实例仍由后端独占授权范围和单一物理推进者裁决。共享的是组件/契约，非隐藏全局单例。 |
| <a id="test-config-008"></a>TEST-CONFIG-008 | Scene 默认布局与两个实验实例覆盖 | 两个 ExperimentDraft 引用同一 SceneVersion 并覆盖允许位姿，分别解析/验证为不同固定快照，源场景不变；清除覆盖恢复所引用版本默认。未知/越权字段拒绝，SceneDraft 发布新资源不改旧引用，运行实际状态不反写初态；随机化实际结果与来源可追踪。未支持编辑能力时仅允许预设并明示原因。 |
| <a id="test-config-001"></a>TEST-CONFIG-001 | 在同一页面切换导航、抓取、双臂任务 | 共享外壳/选中对象一致；仅出现对应字段。任务切换显式处理脏草案；隐藏字段不进入活动配置。字段默认、单位、边界和能力不足有可重现用例。 |
| <a id="test-config-002"></a>TEST-CONFIG-002 | 从顶部、底部、任务面板查看同一个 Profile | 所有摘要引用同一 ID/版本，编辑只进入统一入口；保存新版本并显式采用后摘要同步。纯操作者视角变更与影响策略/录制的变更分别判断 stale。 |
| <a id="test-config-003"></a>TEST-CONFIG-003 | 选择机器人、对象、地图、Waypoint、传感器及活动快照 | 按权限矩阵仅开放允许字段；禁止请求也由服务端拒绝。选择/隐藏不发控制，草案改初态不写运行态或源模型；冻结快照只读。 |
| <a id="test-config-004"></a>TEST-CONFIG-004 | Passed 后修改依赖、再改回；检查期间修改配置 | 影响运行的修改立即 stale；过期检查不能覆盖当前修订；改回不自动恢复 Passed。名称、选中、缩放等不影响运行的改动不无故使结论失效。 |
| <a id="test-config-005"></a>TEST-CONFIG-005 | 检查通过后到创建 Session 之间更新依赖或断开适配器 | 服务端原子核对验证身份、依赖及当前 readiness；不兼容则拒绝并返回定位原因。双击/重试同一请求不产生重复 Session，成功绑定唯一不可变快照，处于未开始执行状态。 |
| <a id="test-config-006"></a>TEST-CONFIG-006 | 保存 Route v2，配置仍引用 v1；再显式采用 v2 | v1 不变；配置不自动追随 latest。采用 v2 后 stale，点稳定 ID 与顺序可追踪，地图/参考系不兼容给出原因。已有 Session 继续使用旧快照，保存不执行。 |
| <a id="test-config-007"></a>TEST-CONFIG-007 | 在 Mock / Offline / 未实现能力下访问三图 | 明确显示演示/离线/后续扩展；无真实验证时不显示真实 Passed，不提供可执行创建/训练按钮。样例 RGB/点云/就绪指标有来源标识。 |
| <a id="test-loop-001"></a>TEST-LOOP-001 | 一条配置分别用 Human 与受支持的 Expert 采集 | 每次生成可重载的真实 Episode，绑定配置快照、操作者、实际控制来源与时间；结束有回执且可同步回放。未接通专家时显式不可用，不能自动改用人工并报专家成功。 |
| <a id="test-loop-002"></a>TEST-LOOP-002 | 缺帧、异常动作、失败示范、重复派生片段混合清理 | 原始 Episode 不变；质量规则、保留/排除原因、trim/变换与审核修订可追踪。任务成功、完整性、用途资格独立，失败数据按用途处理。 |
| <a id="test-loop-003"></a>TEST-LOOP-003 | Collection 选择/动态查询冻结为 Dataset Version、导出并重载；同源片段尝试跨划分 | 记录 Collection 修订/解析成员（如有），后续集合变化不改旧 manifest；成员/清理/标注/IO/变换/split 固定。同源组不跨 train/val/test，归一化只用 train，目标加载器实读成功。空划分、资格或 schema 不合阻止训练，不阻止 M1 原始回放。 |
| <a id="test-loop-004"></a>TEST-LOOP-004 | 选择一个已接通模型并提交短训练，包含失败与取消 | 接受不可变 Job 配置；真实状态/日志/指标可查询，失败原因明确。成功必须生成可加载 Checkpoint、训练数据/代码/归一化引用；不把提交回执或模拟进度当作训练完成。 |
| <a id="test-loop-005"></a>TEST-LOOP-005 | 选择训练所得权重进入 Simulation 预测运行 | IO、帧、动作维度/单位/顺序/频率、归一化与机器人匹配后显式启动；至少一条真实闭环 Rollout 可回放并追溯至原始数据。记录结果与干预；运行失败或成功率为零也如实报告，不凭 loss 下降宣称任务成功。 |

阶段适用：M1 以 TEST-MOBILE-001/002 为真实闭环门，使用 TEST-CONFIG-003/004/005/007/008 中与已开放功能相关的检查；M2 用 TEST-HOST-001 及对应共享组件条目。三图跨任务切换、Waypoint 等条目按各自功能切片执行，不要求 M1 全部实现。

TEST-LOOP-001 保留多来源采集的长期要求，M1 不因尚未接通第二来源而失败。TEST-LOOP-002～005 属于后续清理、数据版本、训练与预测；不作为 M1/M2 的完成前置。真实权限/Session/持久化不能仅用 Mock 通过，所有条目当前仍 not_executed，不从图中读取训练步数、成功率或性能阈值。
