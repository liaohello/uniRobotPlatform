# Dataset、Training、Checkpoint 与 Evaluation 关系

规范 ID：`CT-LINEAGE` · 责任层：共享契约 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-034](../../设计过程与Specification总册_20261021.md#doc-034) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.6｜更新日期：2026-10-22（America/Los_Angeles）

状态：分阶段的数据/模型设计基线；M1 仅要求 Session/配置快照→原始 Episode→只读回放，集合、导出、训练及预测为后续阶段。

来源：S05（详见[来源档案](../90-governance/06-sources.md)）

关联需求：[REQ-TRAIN-002](../indexes/05-requirements.md#req-train-002)

## 对象关系草案

| 对象 | 关联 |
|---|---|
| Collection | 可编辑的命名选择/查询工作集；发布时解析为固定成员，不直接提供可变训练输入 |
| Dataset Version | Episode 集合、筛选与变换、标注版本、动作/观测 schema |
| Training Job | Dataset Version、划分、模型/配置版本、运行状态 |
| Checkpoint | Training Job、step、存储位置、元数据 |
| Model Version | Checkpoint、推理配置、动作解码 / 控制接口 |
| Evaluation Run | Model Version、任务/场景版本、种子、Episode、结果 |

这些关系用于未来追溯“模型来自哪份数据、在哪种场景验证”，不代表已实现训练服务。精确 ID、版本策略、后端生命周期和存储位置待定。

## Collection 与 Dataset Version

Collection 有稳定 collectionId 和可编辑 revision，membershipMode 明确为 explicit（显式 Episode 引用）或 query（版本化筛选条件）。显式添加/删除改变 Collection 修订，查询结果可随数据增长而变化；界面预览数量不能当成已冻结训练成员。

创建 Dataset Version 时服务端按一次确定的 Collection revision/查询条件解析成员，冻结 source/native Episode refs、清理/片段/标注修订、schema/变换/配方、split/资格检查引用及解析时间。若 Collection 在解析期间改变，拒绝发布到错误修订；不把随后新增结果加入旧版本。若允许直接选成员创建版本，可没有 parentCollectionRef，但必须有相同的固定成员 manifest。

Dataset Version 不可变；Collection 后续变更、标签更正、split/变换改变都产生新的 Dataset Version。版本记录 parentCollectionRef/revision（如有）和解析成员，不能仅保存动态 query 或 `latest`。失败发布不生成可训练的“半完成版本”，原始 Episode 和已发布版本保持可读。

这一定义属于后续数据治理，不要求 M1 先做动态 Collection、导出或训练资格。[S16](../90-governance/sources/S16-mobile-first-spec-repair.md) 的当前阶段优先于旧“全部作为首条任务必需”的表述。

数据划分原则、模型和机器人 action schema 兼容性必须进入正式训练规范；前端不能凭文件名相同就视为兼容。训练与评估的运行状态需来自服务，不由页面是否打开推断。

## 关联文档

- [Model Training｜训练管理概念](../10-frontend/06-training-evaluation/01-training-workspace.md)
- [Evaluation｜评估概念](../10-frontend/06-training-evaluation/02-evaluation-workspace.md)
- [Dataset Management｜数据管理](../10-frontend/05-datasets/01-browser-quality-export.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)

## V0.3 版本与状态补充

Training Job 保存接受的配置快照，后续草案修改不能原地改变作业；指标包括适配器定义、名称、单位、step/时间，未提供的字段保留缺失。Model Version 区分导入、注册、观测/动作/归一化适配、运行验证等事实，注册标签不授予运行兼容性。

Evaluation Report Revision 与 Comparison Manifest 的固定证据、分母和聚合规则见 [评估比较契约](09-evaluation-comparison.md)。导出/训练绑定的 Dataset Version 固定成员与标注引用，后续更正产生新修订/版本。

## 后续完整数据/模型流程的绑定（保留 V0.5 需求，V0.6 按阶段适用）

来源：[S15](../90-governance/sources/S15-scene-setup-first-loop.md)、[S16](../90-governance/sources/S16-mobile-first-spec-repair.md)。以下分别在采集、清理、发布数据和模型阶段适用，不全部作为 mobileCar M1 的完成门槛；仍未实现/验收。

| 对象 | 首条任务必需记录 |
|---|---|
| Episode | 新平台采集绑定 Session/ValidatedSnapshot；原生身份、实际来源/时间/完整性依 CT-EPISODE；历史原生数据不伪造平台验证引用 |
| 清理/审核修订 | 原始父 Episode、片段区间、保留/排除原因、变换/标签版本、规则与人工审核来源；原始记录不变 |
| Dataset Version | 固定成员/修订、IO schema、导出配方/版本/校验报告、用途资格与 Split Manifest |
| Split Manifest | train/val/test 固定成员、同源父组与 seed；片段/增强/重导出不跨组，归一化只拟合 train |
| Training Job | 固定 dataset/split、模型 recipe、超参/seed、代码/环境指纹、IO/预处理/动作解码与归一化引用、状态/错误/日志 |
| Checkpoint / Model Version | Job/step、权重位置和摘要、配置/归一化依赖、加载兼容结论；不凭文件名判同一模型 |
| Rollout / Result | Model Version、推理配置、新 Session 快照、Episode、实际控制/干预、有效性与任务结果 |

Dataset 资格 false、空 train/val、无法加载目标格式或 IO 不匹配时禁止真实训练。小样本可明确无 test，仅做 train/val 流程验证；没有独立测试就不报告独立测试表现。提交作业不等于产出可加载模型，模型可加载不等于自主任务成功。

上述训练门控不阻止 M1 原始记录的列表/只读回放。Episode 配置引用的唯一权威与条件字段由 [CT-EPISODE](03-episode-events-annotations.md) 定义；重复索引不是平行配置真值。

[首任务详细路线](../00-overview/10-first-task-closed-loop.md) · [TEST-LOOP-001～005](../40-verification/06-scene-setup-first-loop.md)
