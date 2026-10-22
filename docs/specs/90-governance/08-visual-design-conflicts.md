# 现有前端图片冲突分析与收敛方案

规范 ID：`GOV-VISUAL-CONFLICTS` · 责任层：设计治理 · 版本：V0.6（2026-10-22）

这是对现存设计图的分析，不是对已经实现前端的缺陷判定。按图片可观察内容与当前 Specification 的规则区分职责重叠、语义冲突、占位内容和后续范围；新的布局取舍仍标建议。

来源：[讨论可读摘录](sources/S11-design-discussions.md)、[PPT/图片](sources/S12-visual-materials.md)、[当前用户要求](sources/S13-current-visual-spec-request.md)。[按页面看修正与原图](../10-frontend/page-designs/README.md)。

## 主要结论

现有图片能共同支持“配置 → 运行 → 轨迹 → 数据版本 → 训练/模型 → 评估”的流程，但不适合按图片逐个建设独立控制台。优先收敛在线执行权威入口、资源与实验草案、Data 对象边界、真实机器人能力及比较证据。

图片 1–20 对应 PPT 页；21 为额外截图。评估运行副本不是另一方案，已按字节相同登记。

| ID | 主题 | 冲突类别 | 图片 | 当前处理状态 |
|---|---|---|---|---|
| [VIS-C01](08-visual-design-conflicts.md#vis-c01) | 导航入口数量与归属 | IA 重叠 | 1–20；21 | 方案待原型验证 |
| [VIS-C02](08-visual-design-conflicts.md#vis-c02) | 在线控制台重复 | 职责冲突 | 3、8、9、14 | 收敛建议，延续 DEC-031 |
| [VIS-C03](08-visual-design-conflicts.md#vis-c03) | 两个 Scene Editor | 职责重叠 | 2、20 | 设计建议 |
| [VIS-C04](08-visual-design-conflicts.md#vis-c04) | Live 中 Scale/编辑对象 | 与已定边界冲突 | 2、3、9 | 按现有契约纠偏 |
| [VIS-C05](08-visual-design-conflicts.md#vis-c05) | 图中机器人被当作真实模型 | 事实占位风险 | 3、8–20 | 图示事实不采纳 |
| [VIS-C06](08-visual-design-conflicts.md#vis-c06) | 播放、Pause、Reset、Stop 语义漂移 | 执行语义冲突 | 3–20 | 按状态域纠偏 |
| [VIS-C07](08-visual-design-conflicts.md#vis-c07) | 全局 Human 掩盖部件 Owner | 控制粒度冲突 | 3、9 | 按控制权契约纠偏 |
| [VIS-C08](08-visual-design-conflicts.md#vis-c08) | SO101 观测集合膨胀 | 与当前 Profile 冲突 | 8、9、10、14、19 | 当前基线优先 |
| [VIS-C09](08-visual-design-conflicts.md#vis-c09) | Episode 与 Dataset 界面混用 | 对象与交互重叠 | 4、5 | 延续 Data 方案 |
| [VIS-C10](08-visual-design-conflicts.md#vis-c10) | 资源/实验/在线配置混在一起 | 对象版本冲突 | 2、9、18、19、20 | 契约约束 |
| [VIS-C11](08-visual-design-conflicts.md#vis-c11) | 阶段、来源、结果互相替代 | 数据语义冲突 | 3、4、5、9、16、18 | 既有数据模型优先 |
| [VIS-C12](08-visual-design-conflicts.md#vis-c12) | 回放编辑与原始数据写入 | 数据边界冲突 | 4 | 按 Replay 契约纠偏 |
| [VIS-C13](08-visual-design-conflicts.md#vis-c13) | 训练配置与监控重复 | 页面状态重叠 | 6、7、21 | 设计建议 |
| [VIS-C14](08-visual-design-conflicts.md#vis-c14) | 模型名称等于可用能力 | 适配与状态冲突 | 6–13、19 | 能力与契约约束 |
| [VIS-C15](08-visual-design-conflicts.md#vis-c15) | 训练验证与正式 Evaluation | 指标职责冲突 | 6、14–16、21 | 设计建议 |
| [VIS-C16](08-visual-design-conflicts.md#vis-c16) | 可比较界面暗示并行调度 | 范围误推 | 7、15、17 | 范围保持未冻结 |
| [VIS-C17](08-visual-design-conflicts.md#vis-c17) | 图中数据被当作真实事实 | 占位内容 | 1–21 | 图片数字不采纳 |
| [VIS-C18](08-visual-design-conflicts.md#vis-c18) | 真机页扩展了当前边界 | 范围冲突 | 8–10、14、19 | 后续方案 |
| [VIS-C19](08-visual-design-conflicts.md#vis-c19) | 模型比较与批次比较重复 | 职责重叠 | 12、13、17 | 设计建议 |
| [VIS-C20](08-visual-design-conflicts.md#vis-c20) | 统计排名缺少共同条件 | 证据与统计冲突 | 13–17 | 新增契约草案 |
| [VIS-C21](08-visual-design-conflicts.md#vis-c21) | 设计标注混入产品画面 | 视觉表达冲突 | 1–4、8、9 | 视觉统一建议 |
| [VIS-C22](08-visual-design-conflicts.md#vis-c22) | 模板卡片扩大所有任务范围 | 范围误推 | 1、18、20 | 范围与接入分级 |

<a id="vis-c01"></a>
## VIS-C01｜导航入口数量与归属

- 观察：六项编号菜单、Resources 组、独立 Model Zoo 和 Training 子项并存。
- 依据：原图 1–20；21，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：采用 Home + 四业务组 + 辅助 Resources 的草案；Model Zoo 仅在 Models 下保留一个主入口。
- 状态：方案待原型验证；不是产品功能已完成或已验证。

<a id="vis-c02"></a>
## VIS-C02｜在线控制台重复

- 观察：Simulation、Inference & Rollout 和 Evaluation Setup 都出现 Start/Reset/Record 和交互 3D。
- 依据：原图 3、8、9、14，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：在线动作与接管只在同一 Simulation 组件/Session 权威链执行；评估页只读预览并链接该 Session；离线预测不执行。
- 状态：收敛建议，延续 DEC-031；不是产品功能已完成或已验证。

<a id="vis-c03"></a>
## VIS-C03｜两个 Scene Editor

- 观察：Scene Setup 与 Scenes 内都显示 Scene Editor，容易各自维护模型和对象。
- 依据：原图 2、20，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：Scenes 管资产/版本与预览；Scene Setup 管本次实验草案；复用同一受限编辑组件。
- 状态：设计建议；不是产品功能已完成或已验证。

<a id="vis-c04"></a>
## VIS-C04｜Live 中 Scale/编辑对象

- 观察：在线视口显示 Scale；Policy 侧栏允许 Edit Scene/Randomize。
- 依据：原图 2、3、9，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：草案变换与运行期 Joint/TCP/物理扰动分开；活动快照不可静默热改，Scale 等仅在白名单场景草案中使用。
- 状态：按现有契约纠偏；不是产品功能已完成或已验证。

<a id="vis-c05"></a>
## VIS-C05｜图中机器人被当作真实模型

- 观察：通用白色机械臂被标 SO101；19 写厂商、12 DoF、尺寸、负载、接口。
- 依据：原图 3、8–20，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：外形和所有参数从工程模型/Capability 读取；未核对标 Unknown。图片只能参考布局。
- 状态：图示事实不采纳；不是产品功能已完成或已验证。

<a id="vis-c06"></a>
## VIS-C06｜播放、Pause、Reset、Stop 语义漂移

- 观察：资源/结果页沿用运行播放控件，评估监控同时有实时画面和历史进度。
- 依据：原图 3–20，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：全局仅运行摘要；页面本地操作注明 Session/Job/Replay 对象；物理暂停、策略停止、录制和历史播放分开。
- 状态：按状态域纠偏；不是产品功能已完成或已验证。

<a id="vis-c07"></a>
## VIS-C07｜全局 Human 掩盖部件 Owner

- 观察：当前控制者只显示一个 Human/Policy，Shared Control 又像同时混合两个输入。
- 依据：原图 3、9，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：全局状态只作摘要，显示底盘/左右臂/夹爪的归属；Shared 表示按部件分配，未经设计不做同一执行器输入混合。
- 状态：按控制权契约纠偏；不是产品功能已完成或已验证。

<a id="vis-c08"></a>
## VIS-C08｜SO101 观测集合膨胀

- 观察：双臂三路 RGB 之外默认出现 Depth、Point Cloud 和 External Camera。
- 依据：原图 8、9、10、14、19，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：SO101 基线为中央与左右腕 RGB；其他视图只在新能力/观测配置验证后开放。主臂没有独立相机。
- 状态：当前基线优先；不是产品功能已完成或已验证。

<a id="vis-c09"></a>
## VIS-C09｜Episode 与 Dataset 界面混用

- 观察：Dataset 页顶 Mode Replay/倍速，右侧又编辑阶段；Replay 左侧承担全数据管理。
- 依据：原图 4、5，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：Library 查询轨迹、Detail 回放标注、Collections/Version 管集合与导出；共享 Data 导航，不复制全部功能。
- 状态：延续 Data 方案；不是产品功能已完成或已验证。

<a id="vis-c10"></a>
## VIS-C10｜资源/实验/在线配置混在一起

- 观察：所有地方都能 Edit Scene/Task/Robot，未说明改原件还是在线实例。
- 依据：原图 2、9、18、19、20，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：资源修订、Experiment Draft 与活动快照分离；Edit 创建明确草案，历史报告复制为新配置。
- 状态：契约约束；不是产品功能已完成或已验证。

<a id="vis-c11"></a>
## VIS-C11｜阶段、来源、结果互相替代

- 观察：Grasp 和 grasp_success 混成标签；Human/Expert 数据互斥；Intervened 与 Success 并列。
- 依据：原图 3、4、5、9、16、18，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：阶段/控制来源/结果/完整性/资格独立；同一 Episode 可混合来源和受控干预。
- 状态：既有数据模型优先；不是产品功能已完成或已验证。

<a id="vis-c12"></a>
## VIS-C12｜回放编辑与原始数据写入

- 观察：Split/Trim/Open in Simulation 容易被理解成裁原数据或任意时刻续跑。
- 依据：原图 4，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：原始轨迹不改，标注独立修订；片段是引用/派生；历史到仿真只建新运行，状态恢复能力另核对。
- 状态：按 Replay 契约纠偏；不是产品功能已完成或已验证。

<a id="vis-c13"></a>
## VIS-C13｜训练配置与监控重复

- 观察：Training 同时可改配置、启动并查看当前运行；Training Runs 又实现相同监控。
- 依据：原图 6、7、21，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：Training Setup 提交固定配置；Training Runs 承担状态/日志/Checkpoint；运行后编辑只建新草案。
- 状态：设计建议；不是产品功能已完成或已验证。

<a id="vis-c14"></a>
## VIS-C14｜模型名称等于可用能力

- 观察：图片把所有方法、Loss、输入、动作、频率、硬件和 Run 按钮默认开放。
- 依据：原图 6–13、19，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：适配器声明参数/指标与动作观测 Schema；导入/注册/适配/验证各自独立。权重存在不等于可执行。
- 状态：能力与契约约束；不是产品功能已完成或已验证。

<a id="vis-c15"></a>
## VIS-C15｜训练验证与正式 Evaluation

- 观察：训练页 Evaluation 和主评估重复；训练代理分数与正式任务成功率名称接近。
- 依据：原图 6、14–16、21，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：训练验证标 Validation 并注明 held-out 数据和方法；正式评估引用任务/场景/seed/协议与 Episode 证据。
- 状态：设计建议；不是产品功能已完成或已验证。

<a id="vis-c16"></a>
## VIS-C16｜可比较界面暗示并行调度

- 观察：多个 Running 与 Batch Comparison 容易被当成已经支持并行环境集群。
- 依据：原图 7、15、17，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：列表可监控后端已有作业；比较可以基于串行结果，批量/并行资源能力另定，不因图片成为 V1 要求。
- 状态：范围保持未冻结；不是产品功能已完成或已验证。

<a id="vis-c17"></a>
## VIS-C17｜图中数据被当作真实事实

- 观察：计数、成功率、Loss、硬件、模型参数/许可证及 Connected/Ready 都是概念稿文字。
- 依据：原图 1–21，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：开发时来自真实服务；原型明确标示例。未知不补零；同报告摘要和细节一致。16 的 Timeout 0 与分布 1 就是例子。
- 状态：图片数字不采纳；不是产品功能已完成或已验证。

<a id="vis-c18"></a>
## VIS-C18｜真机页扩展了当前边界

- 观察：Real Robot/Mixed、Reset Robot、浏览器 E-Stop、可关闭监控等设计未定义设备语义。
- 依据：原图 8–10、14、19，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：保留 PAGE-21 后续参考，不作为当前 V1 承诺；仿真按钮不能直接移植为硬件控制保证。
- 状态：后续方案；不是产品功能已完成或已验证。

<a id="vis-c19"></a>
## VIS-C19｜模型比较与批次比较重复

- 观察：My Models、Registry & Compare、Batch Comparison 都展示排名和对照。
- 依据：原图 12、13、17，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：My Models 仅摘要；P13 以模型版本为中心，P17 以评估 Run/条件为中心；共用比较契约。
- 状态：设计建议；不是产品功能已完成或已验证。

<a id="vis-c20"></a>
## VIS-C20｜统计排名缺少共同条件

- 观察：不同任务/协议/seed/随机化并排排名，单 Run 也显示 mean±std/95%CI，干预指标分母不明。
- 依据：原图 13–17，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：保存比较清单与差异，标明可比较性、统计单位、样本量和分母；条件不匹配仅描述性展示，缺重复实验不造统计量。
- 状态：新增契约草案；不是产品功能已完成或已验证。

<a id="vis-c21"></a>
## VIS-C21｜设计标注混入产品画面

- 观察：红框中文箭头、A/B 方案说明、Ghost 与实际外形叠在正式界面。
- 依据：原图 1–4、8、9，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：原图保留，产品中移除设计说明；A/B 选一套默认并保留高级折叠；预测/目标/实际明确标识。
- 状态：视觉统一建议；不是产品功能已完成或已验证。

<a id="vis-c22"></a>
## VIS-C22｜模板卡片扩大所有任务范围

- 观察：Screw/Cloth/户外/复杂装配与当前导航/近场/双臂并列，像已可执行任务。
- 依据：原图 1、18、20，可通过[页码对照](../references/04-visual-asset-catalog.md)定位。
- 建议/约束：按可用/待适配/仅规划登记；模板与资源选择不等于算法已完成。V0.5 曾建议 SO101/ACT 首发；当前由 [V0.6 M1/M2](../00-overview/10-first-task-closed-loop.md) 取代：先 mobileCar 场景→运行→录制→回放，再 bimanual 复用，训练/预测后续。
- 状态：范围与接入分级；不是产品功能已完成或已验证。

## 不属于冲突的差异

导航、近场抓取、感知与双臂拥有不同面板是 Profile 机制需要的正常差异。训练配置/作业监控、评估配置/运行/报告也是同一对象生命周期的不同视图；共享组件与状态语义即可，不应为了外观一致把它们强行放在一屏。

## V0.4 Simulation 新图的处理进度

下表只表示设计图已有变化，不表示产品验证已通过；其他页面的原冲突仍保留。

| 原主题 | 新图进展 | 仍需处理 |
|---|---|---|
| VIS-C04 在线通用编辑 | Select/Joint/TCP 取代 Move/Rotate/Scale，Scale 已从图中移除 | 工具启用条件与实际命令语义 |
| VIS-C06 状态/播放语义 | 顶部拆仿真、任务、录制 | Reset/结束任务/封口与按钮状态矩阵 |
| VIS-C07 部件 Owner | 新增 Base/Arm/Gripper 表 | Profile/混合控制、Coupled、交还条件及部件来源轨 |
| VIS-C11 阶段/来源/事件 | 增加独立系统事件轨 | 当前阶段一致性、未来事件与录制时钟 |
| VIS-C14/17 能力和占位值 | 增加 IK/规划/验证与指令状态 | 不能恒绿；单位、残差与 Command ID/目标版本绑定 |
| VIS-C21 设计标注 | 新图移除红框及中文引导箭头 | 轨迹图例仍需明确；其他页面不自动改为已解决 |

[V2 完整对照](../10-frontend/03-simulation/06-simulation-v2-review.md) 与 [当前页面](../10-frontend/page-designs/03-simulation.md)。
