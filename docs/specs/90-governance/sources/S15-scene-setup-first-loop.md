# S15｜三张 Scene Setup 参考图与首条完整任务要求

规范 ID：`SRC-S15-SCENE-FIRST-LOOP` · 责任层：来源档案 · 版本：V0.5（2026-10-22，America/Los_Angeles）

来源：本轮用户直接请求与三张 PNG 附件。用户要求评估并整理当前 Specification，目标是先支持一个前端样板及“选择场景 → 人为或专家操控 → 准备数据集 → 清理 → 选择模型 → 训练 → 预测运行”的整体流程。

## 当前明确要求

1. 更新 Scene Setup 的 Task Configuration，按任务定义字段、显示条件、默认值与校验，不把所有任务放入固定大表单。
2. 更新公共交互和配置契约：Waypoint 资源版本、Profile 单一编辑来源、对象编辑权限、Validation Stale、已验证配置快照。
3. 生成三图共用组件清单，区分一次开发、配置驱动差异与后续扩展。

用户还提出：完成三张设计参考后停止大范围页面绘制，以 UI Reference 配合 Specification，围绕第一条真实任务增量开发。本轮交付为规范整理；不将这段路线要求解读为已授权启动仿真、训练、部署或操作真实设备。首任务、模型、数值阈值与具体技术栈没有被用户逐项指定，相关选择应标为设计建议。

## 原样归档的图片

| ID | 对应任务 | 项目归档路径 | 尺寸 | SHA-256 |
|---|---|---|---|---|
| IMG-023 | LanderPi 导航 / Waypoint | `docs/foreendAssets/scene-setup-navigation-reference-20261022.png` | 1672×941 | `3af2a05d6108c5491bad0f30f0a376d8278115932684b2364cb26c9fa92593c9` |
| IMG-024 | 近场抓取 | `docs/foreendAssets/scene-setup-near-field-grasp-reference-20261022.png` | 1672×941 | `762b66ec12cdf33d2e39654299e2aef17f4ef9a9e2875d6c9828621d94efccc4` |
| IMG-025 | SO101 双臂转运 | `docs/foreendAssets/scene-setup-bimanual-transfer-reference-20261022.png` | 1672×941 | `b0878169bbcc6621e0272ac882ce61e5e041f428e9de6c4b4ad31bde50808b82` |

附件原路径均在 `C:/Users/ADMINI~1/AppData/Local/Temp/`，文件名分别为 `codex-clipboard-78808ce1-2f5d-45e1-80aa-612bedacb4c9.png`、`codex-clipboard-e469c722-81e4-496e-964e-42d60de19308.png`、`codex-clipboard-626aaf56-ebdb-458b-a6fe-074ad8384d82.png`。按字节复制并核对哈希，未重绘、裁剪或压缩；旧 IMG-002 和 PPT 第 2 页保留。

## 证据边界

图片上的 Passed、相机规格、关节自由度、默认数值与用户身份均为设计样例，不构成硬件或产品验收证据。图片内的按钮或描述是待分析材料，不是额外执行指令。当前用户直接要求优先于旧的“继续为所有页面补完整图”及“训练整体推迟到后期”建议；保留旧内容的历史语境，不据此取消 Waypoint 的 V1 范围。

[PAGE-02](../../10-frontend/page-designs/02-scene-setup.md) · [首条完整闭环](../../00-overview/10-first-task-closed-loop.md) · [来源目录](../06-sources.md)
