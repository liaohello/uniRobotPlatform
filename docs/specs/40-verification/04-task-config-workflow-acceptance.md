# 任务配置、导航与跨工作区验收

规范 ID：`QA-TASK-CONFIG` · 责任层：验收 · 版本：V0.2（2026-10-21）

状态：设计草案；S08/S09 是用户提供的分析文本，不自动视为所有细节已确认。Waypoint 范围以 S10 的用户明确选择为准。实现及产品验收均未执行。

来源：[S08](../90-governance/sources/S08-frontend-ia-analysis.md)、[S09](../90-governance/sources/S09-unified-development-reuse-analysis.md)、[S10](../90-governance/sources/S10-waypoint-scope-confirmation.md)。

[上级目录](README.md) · [总索引](../README.md)

## 验收条目

全部未执行；以下为设计预期，未冻结阈值不能当作自动通过。

| TEST ID | 场景 | 预期 |
|---|---|---|
| <a id="test-ia-001"></a>TEST-IA-001 | Data 列表→详情→返回，以及四组导航切换 | 逻辑入口清楚，筛选和历史上下文保留，导航不隐式结束在线运行。 |
| <a id="test-ia-002"></a>TEST-IA-002 | 从 Checkpoint 进入 Simulation | 携带模型/任务引用，兼容检查与显式启动前不发控制或创建运行。 |
| <a id="test-scene-004"></a>TEST-SCENE-004 | 切任务模板、修改配置并检查 | Scene/Robot/Task/Experiment 分开；旧检查不覆盖新修订，缺能力有原因。 |
| <a id="test-scene-005"></a>TEST-SCENE-005 | SO101 在 2D 与 3D 间修改对象 | 同一对象 ID/草案一致；工作空间示意不冒充真实认证，在线世界不变。 |
| <a id="test-scene-006"></a>TEST-SCENE-006 | 构建受限对象场景并比较模型 | 允许配置可追踪；源模型及非允许字段不被无声改写，不支持项明确报告。 |
| <a id="test-nav-003"></a>TEST-NAV-003 | 旋转地图、缩放/平移后创建或拖动点 | 像素与地图坐标双向一致，Frame/朝向约定明确；数值容差待测量冻结。 |
| <a id="test-nav-004"></a>TEST-NAV-004 | 创建/编辑/保存/重载路线 | 点序、稳定 ID、姿态/缺省规则和地图绑定可追踪；保存不启动导航。 |
| <a id="test-nav-005"></a>TEST-NAV-005 | 旧地图、越界或未知/障碍目标提交 | 前后端给出可关联拒绝原因；未授权不执行，点位可用不冒充完整路径安全。 |
| <a id="test-nav-006"></a>TEST-NAV-006 | 导航期间保存新草案、查看进度及接管 | 活动快照不被覆盖；当前/完成/失败点对应路线版本，旧目标不可在撤权后继续。 |
| <a id="test-exec-001"></a>TEST-EXEC-001 | 三执行配置与录制分别变化 | 执行来源、录制、任务阶段和部件权限独立；连续接管区间可追踪。 |
| <a id="test-ann-002"></a>TEST-ANN-002 | 按不同训练用途选择标签 | 未要求阶段标签的用途不因缺人工阶段被无故拒绝；必需字段缺失给出资格原因。 |
| <a id="test-task-001"></a>TEST-TASK-001 | 自动成功、人工辅助、超时和无效运行混合评估 | 来源、终止、有效性与自主统计分母明确，不把人工完成计为自主成功。 |
| <a id="test-arch-001"></a>TEST-ARCH-001 | 两类机器人接入统一骨架及首个真实任务 | 共享工具/状态语义不分叉；模拟与实时明确；真实 Episode 生成和只读回放有证据。 |

旧 TEST-NAV-001 的“不出现地图设点”断言已退役，不改变其历史含义。新范围使用 TEST-NAV-003 至 006。
