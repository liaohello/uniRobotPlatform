# Scenes｜场景资源库

规范 ID：`PAGE-20` · 责任层：前端页面设计 · 版本：V0.3（2026-10-21）

状态：页面详细草案；“每页必须有图片参考”是本轮用户要求，具体布局与新增能力仍是设计建议。图片是概念稿，不是现有可运行界面的证据。

[页面总览](README.md) · [统一页面规则](../01-shell/04-visual-design-rules.md) · [冲突分析](../../90-governance/08-visual-design-conflicts.md)

## 定位与范围

浏览和复用环境资产，避免与实验场景编辑器重复。

- 页面 ID：`PAGE-20`；导航归属：Resources / 辅助资源入口。
- 主要对象：Scene Asset、Scene Preset Revision、允许的 Variation。
- 增量路线：A/B 已有场景选择；C 受限对象资产。这是设计顺序，不是排期或启动实施。

## 图片参考

![Scenes｜场景资源库 原始概念图](../../../foreendAssets/RoboLab%20%E5%9C%BA%E6%99%AF%E5%BA%93%E4%B8%8E%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E7%BC%96%E8%BE%91%E5%99%A8.png)

主参考：`IMG-020`，PPT 第 20 页。覆盖程度：完整页面构图参考。下面的修正优先于图中按钮、数值和字段。

## 区域与功能

| 区域 | 功能与反馈 |
|---|---|
| 左侧 | 环境/任务/机器人/来源筛选。 |
| 主体 | 场景列表与版本。 |
| 右侧 | 只读预览、对象资源、变体和兼容性说明。 |

## 关键操作与跳转

- “用于实验”进入 P02 创建草案；场景本身不含活动控制权或录制状态。
- Edit Scene 使用同一 Scene Setup 编辑器组件与受限配置契约，不建设第二套编辑实现。
- 资源新修订与既有实验引用分离；默认不静默升级引用。

## 状态、失败与恢复

- 加载失败、模型依赖缺失和兼容性未知给出原因。
- 现存场景与示意候选分开，图片卡片不等于文件可加载。

## 相对原图的取舍

- Scenes 内的 Scene Editor 标签收敛为调用统一编辑器的入口。
- Lighting & Physics/Variations 仅暴露后端白名单，不提供任意 XML 覆写。
- 仓库、户外、装配等场景只是未来参考，不自动承诺全套仿真资产。

关联冲突：[VIS-C01](../../90-governance/08-visual-design-conflicts.md#vis-c01)、[VIS-C03](../../90-governance/08-visual-design-conflicts.md#vis-c03)、[VIS-C10](../../90-governance/08-visual-design-conflicts.md#vis-c10)、[VIS-C17](../../90-governance/08-visual-design-conflicts.md#vis-c17)、[VIS-C22](../../90-governance/08-visual-design-conflicts.md#vis-c22)。

## 主责功能与后端支撑

- [Scene Setup｜场景布置](../02-scene-setup/01-workflow-initial-state.md)

后端/契约：[03-scene-builder-assets](../../20-backend/01-session-scene/03-scene-builder-assets.md)、[02-scene-config-versions](../../20-backend/01-session-scene/02-scene-config-versions.md)。

## 常用页面跳转

| 触发操作 | 目标页面 | 携带的对象与限制 |
|---|---|---|
| 用于实验/编辑场景 | [PAGE-02](02-scene-setup.md) | Scene Revision，调用统一受限编辑器 |

跳转本身不启动运动、改变控制权或覆写活动配置；提交作业/执行的状态以明确操作和后端确认为准。

## 原型验证关注点

参考图可查看、数据对象可追溯、同一操作只有一个权威入口；不支持的操作有明确原因。涉及运动、标注、导出或作业时，分别按主责功能验收，不能以页面截图代替验证。
