# 未决问题登记

规范 ID：`GOV-QUESTIONS` · 责任层：治理 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-039](../../设计过程与Specification总册_20261021.md#doc-039) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.6｜更新日期：2026-10-22（America/Los_Angeles）；原始内容来源保留。

状态：开放问题；无新增用户批准要求

来源：S01–S07（详见[来源档案](06-sources.md)）

关联需求：见需求追踪矩阵中的引用与相关主责规范

下表为待讨论，不是阻止当前整理的审批清单。优先级是本轮组织建议。

| ID | 问题 | 影响文档 | 建议顺序 |
|---|---|---|---|
| <a id="oq-001"></a>OQ-001 | 四导航组/六逻辑工作区作为最新方案；Data 共享入口及最终导航呈现仍待原型 | Navigation | 先讨论 |
| <a id="oq-002"></a>OQ-002 | 离开 Simulation 的全局状态与危险持续输入如何显示/终止 | Navigation / Input | 先讨论 |
| <a id="oq-003"></a>OQ-003 | Scene Draft 如何应用：停止旧 Session、Reset 或新建运行 | Scene / Runtime | 先讨论 |
| <a id="oq-004"></a>OQ-004 | 运行/暂停/录制/任务的组合规则和 Reset 的 Episode 边界 | Runtime / Recording | 先讨论 |
| <a id="oq-005"></a>OQ-005 | 单击 Link 到 Joint 的映射；原草案“单击恢复互斥”具体作用层级 | Selection | 原型 |
| <a id="oq-006"></a>OQ-006 | 框选是可见表面、投影中心还是穿透选择 | Selection | 原型 |
| <a id="oq-007"></a>OQ-007 | 跨臂无 Ctrl 的结果保持旧选择还是取消；环境混选如何提升 | Selection | 原型 |
| <a id="oq-008"></a>OQ-008 | Ctrl 单击/框选 Link 与 Arm 混合集合的追加/去重 | Selection | 原型 |
| <a id="oq-009"></a>OQ-009 | Joint Link 屏幕拖动到角度的映射、退化视角和灵敏度 | Joint | 原型 |
| <a id="oq-010"></a>OQ-010 | TCP 的姿态约束、局部/世界轴与自由度投影 | TCP | 先讨论 |
| <a id="oq-011"></a>OQ-011 | “虚线关节轨迹”的默认对象：TCP、各关节中心、Ghost 或组合 | TCP | 先讨论 |
| <a id="oq-012"></a>OQ-012 | 后端提供终点 IK、插值还是规划；碰撞/可执行性反馈级别 | TCP / Command | 先核对后端 |
| <a id="oq-013"></a>OQ-013 | Live 下的轨迹预览、目标版本和旧候选失效方式 | TCP | 原型/接口 |
| <a id="oq-014"></a>OQ-014 | Alt 绑定兼容性、独立按钮是否保留、自定义键 | Physics / Input | 原型 |
| <a id="oq-015"></a>OQ-015 | 外力的三维映射、幅值/变化率、力矩、暂停行为 | Physics | 先讨论 |
| <a id="oq-016"></a>OQ-016 | 哪些实验允许与 Policy 并行物理扰动 | Physics / Authority | 先讨论 |
| <a id="oq-017"></a>OQ-017 | 控制权按 Arm / Gripper / Base / 执行器组分到何种粒度 | Authority | 先讨论 |
| <a id="oq-018"></a>OQ-018 | 接管时旧动作/chunk 清空、保持控制、失败和恢复策略 | Authority | 先核对后端 |
| <a id="oq-019"></a>OQ-019 | 鼠标与 Leader 来源切换、断连超时/重连对齐 | Leader / Authority | 先讨论 |
| <a id="oq-020"></a>OQ-020 | Algorithm Observation 与 UI / Recording 配置版本关系 | Profiles / Contracts | 先讨论 |
| <a id="oq-021"></a>OQ-021 | 在线时间、传感器时间、时差阈值与回放插值 | Time / Timeline | 先核对链路 |
| <a id="oq-022"></a>OQ-022 | 原始记录 schema、动作绝对/增量、频率与单位 | Recording | 先核对后端 |
| <a id="oq-023"></a>OQ-023 | 小车导航/近场操作与双臂的阶段标签字典及区间规范 | Annotation | 专题讨论 |
| <a id="oq-024"></a>OQ-024 | Dataset 资格规则、LeRobot 导出版本和校验 | Dataset | P0/P1 冻结时 |
| <a id="oq-025"></a>OQ-025 | 任务默认布局、面板停靠、状态/接管入口位置 | Simulation / Components | 布局原型 |
| <a id="oq-026"></a>OQ-026 | 接口传输、订阅频率、渲染负载及延迟/丢帧指标 | Contracts / Verification | 实测后 |
| <a id="oq-027"></a>OQ-027 | 训练后端、模型支持、资源与作业控制 | Training | 概念后续 |
| <a id="oq-028"></a>OQ-028 | Evaluation 成功条件、干预结果分组与批量测试 | Evaluation | 概念后续 |
| <a id="oq-029"></a>OQ-029 | 更早完整聊天原文尚未取得，如何补入来源档案 | Sources / History | 后续有来源时补齐 |

未决条目收敛时，应更新主责 Spec、相关需求行、决策记录及验收条件，并保留旧问题的关闭依据。

## 关联文档

- [决策与方案演变记录](01-decisions.md)
- [讨论过程与设计形成路径](04-design-history.md)
- [工作目录使用与维护规则](05-maintenance.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)

## V0.2 新增未决问题

| ID | 问题 | 影响 | 收敛方式 |
|---|---|---|---|
| <a id="oq-030"></a>OQ-030 | 路线/地图版本、朝向缺省、CSV/YAML 适配与失败继续策略 | Waypoint / Contracts | 接口细化；创建编辑保存范围已确认 |
| <a id="oq-031"></a>OQ-031 | V1 模板允许编辑/新增哪些对象和属性，Scene Builder 白名单 | Scene / Assets | 受限场景原型 |
| <a id="oq-032"></a>OQ-032 | SO101 2D 固定高度、重叠/边界、数量和工作空间图层证据 | Scene / Bimanual | 布局原型 |
| <a id="oq-033"></a>OQ-033 | A–H 区域的尺寸/折叠/小屏和任务切换保护 | Simulation / Layout | 布局原型 |
| <a id="oq-034"></a>OQ-034 | 任务成功容差、终止/评估有效性与自主成功率分母 | Task / Evaluation | 任务协议 |
| <a id="oq-035"></a>OQ-035 | Checkpoint 跳转引用、加载兼容检查与 Policy Adapter 输出 | Models / Simulation | 接口细化 |
| <a id="oq-036"></a>OQ-036 | 三项 PoC 的固定版本、依赖、许可证与通过条件 | References / Architecture | 执行 PoC 前 |
| <a id="oq-037"></a>OQ-037 | 视觉伺服目标扰动采用外力还是独立测试输入，如何保留物理/数据边界 | Physics / Perception | 实验专题 |
| <a id="oq-038"></a>OQ-038 | 底盘辅助 IK 的地图/停靠/臂约束与可达区域定义 | Navigation / IK | 算法接入核对 |
| <a id="oq-039"></a>OQ-039 | 首批启用哪些任务模板，训练/标注需要哪些可选字段 | Profiles / Data | 任务切片收敛 |

S10 已确认 Waypoint 的 V1 范围，OQ-030 不再询问是否纳入，只讨论其协议细节。

## V0.3 页面设计待收敛项

| ID | 问题 | 当前可继续的工作 | 收敛方式 |
|---|---|---|---|
| <a id="oq-040"></a>OQ-040 | 四业务组、Home 和辅助 Resources 的最终菜单词汇及嵌套呈现 | 页面图与对象边界已登记，不阻塞规范分析 | 统一导航原型 |
| <a id="oq-041"></a>OQ-041 | Episode Library/Version Export、SO101 2D/三相机、导航专图等缺少完整定稿 | 每页已有至少局部参考并明示覆盖缺口 | 按首条任务依赖补专图 |
| <a id="oq-042"></a>OQ-042 | 模型导入/适配/验证状态、训练参数/指标与作业控制的实际字段 | 先保持能力驱动的页面和契约语义 | 核对选定后端与首批模型 |
| <a id="oq-043"></a>OQ-043 | 自主尝试纳入/排除、辅助结果分母与比较统计方法 | 不把干预救回计纯自主，不造缺失统计 | 固定任务评估协议 |
| <a id="oq-044"></a>OQ-044 | 历史 Episode 能恢复哪些初态/完整仿真状态 | 目前只承诺引用配置创建新运行，不承诺任意帧续跑 | 后端保存能力核对 |
| <a id="oq-045"></a>OQ-045 | 深色主题准确 token、桌面最小尺寸、响应布局与面板折叠 | 采用现有视觉方向作为候选，保留功能可达性 | 桌面布局与输入原型 |

## V0.4 新图待收敛项

| ID | 问题 | 当前处理 | 收敛方式 |
|---|---|---|---|
| <a id="oq-046"></a>OQ-046 | Human Demo + Base Expert 的语义，运行中 Profile 卡片如何转换 | 区分人工示范带辅助和专家任务中的人工干预，不自行判为纯人类数据 | 任务意图与控制源专题 |
| <a id="oq-047"></a>OQ-047 | Coupled 授权范围、夹爪开闭入口和控制器/TCP 残差详情位置 | 保留既有命令/反馈需求，不因删卡取消 | Inspector 详细交互 |
| <a id="oq-048"></a>OQ-048 | Live 轨的部件来源、计划/已发生、时钟与当前阶段一致性 | 实际事件不画到未来，混合来源说明范围，用户标记独立 | 状态样例与时间契约核对 |

## V0.5 收敛与接入待核实项

OQ-003 的“新建配置 Session”基线已细化为固定验证快照→prepared→显式 Start；旧实例替换/Reset 的更多策略仍待接入。OQ-020 的 Profile 来源及版本关系、OQ-030 的路线版本和缺省朝向、OQ-031 的对象权限已有本轮设计基线，见 [公共契约](../30-contracts/07-task-scene-experiment-config.md)，不再以其“完全未定义”阻断样板。OQ-041 中导航/双臂 Setup 已有三图，其余缺专图不再是开发前置。

| ID | 待核实事项 | 当前可继续工作 | 收敛方式 |
|---|---|---|---|
| <a id="oq-049"></a>OQ-049 | 首条任务的具体场景/对象配方、ACT IO/动作/频率/归一化、运行环境与服务协议 | S16 已明确 M1 mobileCar 预设与录制回放适配；ACT/模型 IO 后续，未核实能力显示不可用 | 接入本地工程时固定版本和产物指纹，做真实最小闭环验收 |
| <a id="oq-050"></a>OQ-050 | F0/R1 首任务是否后续改选 LanderPi，以及模型任务成功率目标 | 首阶段选择已由 S16 关闭：mobileCar 优先、bimanual 复用；后续模型表现阈值另定 | 用户后续偏好或实测结果可调整适配顺序，无需重做架构 |

这些是后续接入核对项，不是本轮规范交付的审批清单；本轮不启动仿真/训练。

## V0.6 当前收敛状态（覆盖上方历史问题的旧状态）

- OQ-003/020/031：SceneVersion/SceneDraft/ExperimentDraft、实例覆盖解析、Profile 分类和 HostApp 注入已由 CT-EXPERIMENT-CONFIG 收敛；剩余是具体适配器支持哪些字段，不再是对象归属未定义。
- OQ-004/021/022：mobileCar M1 采集的 begin/append/end/failure、Reset/segment、原始索引和只读 reader 按 CT-EPISODE 收敛。原生已存在部分实现；平台调用、prepared/实际初态绑定与时序证据尚待接通测试，不伪称已验证。
- OQ-024：Collection 与冻结 Dataset Version 的关系已定义于 CT-LINEAGE；实际导出/训练资格在后续阶段固定，不阻止 M1。
- OQ-049：当前先核对 mobileCar 预设、准备态/Start、原生 start RESET 与录制完成回执的适配；ACT IO/processor/训练环境转后续模型阶段。
- OQ-050：首阶段选择问题已由 S16 用户直接决定 mobileCar 优先、bimanual 复用；后续模型任务表现阈值仍按届时任务协议确定，无需再次询问首任务选择。

未关闭的项目限实际接入事实和后续功能参数；本轮没有新增用户审批前置。来源：[S16](sources/S16-mobile-first-spec-repair.md)。
