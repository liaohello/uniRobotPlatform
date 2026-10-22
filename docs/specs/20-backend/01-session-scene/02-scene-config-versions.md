# 场景配置、初态检查与版本

规范 ID：`BE-SCENE-CONFIG` · 责任层：后端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-007](../../../设计过程与Specification总册_20261021.md#doc-007)、[doc-012](../../../设计过程与Specification总册_20261021.md#doc-012)、[doc-015](../../../设计过程与Specification总册_20261021.md#doc-015)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-SCENE-001](../../indexes/05-requirements.md#req-scene-001)、[REQ-SCENE-002](../../indexes/05-requirements.md#req-scene-002)

## 目标与责任边界

负责场景/机器人资源、配置版本、初态检查与运行实例创建边界。普通任务配置编辑 ExperimentDraft 的实例覆盖；基础场景编辑才写 SceneDraft 并发布新 SceneVersion。两者不可同名覆盖，后端解析并固定已验证配置后再创建运行上下文。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 加载与能力 | 返回可选资源、稳定对象 ID、可编辑范围和机器人能力。 |
| 检查 | 验证配置、必需传感器及初态有效性；具体碰撞和提交标准待任务定义。 |
| 保存 | 分开保存 SceneDraft/SceneVersion 和 ExperimentDraft/配置版本；保留固定引用及实例覆盖，未保存源场景不能隐式改变实验资源版本。 |
| 应用 | 明确新建 Session、Reset 或停止旧运行的规则，不直接覆盖在线 qpos 冒充控制。 |

## 未决与依赖

关联 OQ-003、OQ-020。资产格式、增删范围、允许编辑的物理参数及覆盖保存规则未冻结。

## 关联规范

- [Scene Setup｜场景布置](../../10-frontend/02-scene-setup/01-workflow-initial-state.md)
- [机器人能力与适配边界](../../00-overview/06-robot-capabilities.md)
- [Robot / World State 契约草案](../../30-contracts/01-robot-world-state.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)

## 验收入口

- [TEST-SCENE-003](../../40-verification/02-workspace-runtime-acceptance.md#test-scene-003)（现有草案，未执行；依赖的未决规则须先收敛）。

## V0.5 配置与验证消费职责

[实验配置契约](../../30-contracts/07-task-scene-experiment-config.md) 唯一定义固定依赖、对象写权限、draftRevision/executionRevision、fingerprint、Stale 与 ValidatedSnapshot；本服务必须强制实施，不能只依赖前端禁用按钮。保存不完整草案不等于通过验证。返回逐项 failed/unsupported/not_checked 和范围，不把静态校验当物理可达认证。

服务端保存可重现的不可变快照，并在创建 Session 时原子核对预期执行修订/指纹、权限、依赖和 readiness；用幂等键避免重复创建，单实例冲突明确返回。创建为 prepared，不开始执行。运行时新配置不覆盖在线实例；Route/Profile 新版本仅显式采用后改变工作配置。未接入适配器时显示未实现，不由目录 maturity 标签授予可运行状态。

消费验收：[TEST-CONFIG-002～006](../../40-verification/06-scene-setup-first-loop.md)。本节为待实现职责，不声称已存在这些 API。
