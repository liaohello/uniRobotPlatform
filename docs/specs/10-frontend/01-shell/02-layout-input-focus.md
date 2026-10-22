# 面板布局与输入焦点

规范 ID：`FE-SHELL-LAYOUT` · 责任层：前端 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-028](../../../设计过程与Specification总册_20261021.md#doc-028) · [上级功能包](README.md) · [总索引](../../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.6（2026-10-22）｜整理日期：2026-10-22（America/Los_Angeles）

状态：可折叠数据区有来源；布局交互为草案

来源：S01、S03、S05（详见[来源档案](../../90-governance/06-sources.md)）

关联需求：[REQ-STATE-004](../../indexes/05-requirements.md#req-state-004)

## 建议行为

Task Template 引用的 Layout Preset 提供宿主内默认面板组合，支持折叠、调整、保存与重置。用户希望实时画面能隐藏/展开关节数据或画面，并专门约束排版；拖拽 Docking 的具体机制仍是建议。

不能在拖动 Joint / TCP 或按键驾驶时因任务阶段变化强制换布局。布局状态可按任务保存，控制权与运行状态不能跟随布局预设改变。

## 输入焦点

快捷键仅在 Viewport 有效输入上下文生效；输入框编辑时优先输入文本。开始拖动时锁定操作类型，结束或失焦清理持续输入。离开驾驶视图、失焦或连接断开需撤销连续速度或受力，后端以超时兜底。

全局状态、接管和必要停止入口如何在窄屏/面板折叠时保持可达，需要布局原型确定。当前以桌面浏览器为主要验证环境，具体分辨率与多显示器行为未冻结。

## 关联文档

- [全局信息架构与工作区](01-navigation-context.md)
- [任务、观测与数据配置](../../00-overview/03-task-and-observation-profiles.md)
- [工作区、运行与记录验收](../../40-verification/02-workspace-runtime-acceptance.md)

[需求追踪矩阵](../../indexes/05-requirements.md) · [Wiki 首页](../../indexes/01-reading-guide.md) · [目录入口](../../README.md)

## 页面图与设计归属（V0.3）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E5%B9%B3%E5%8F%B0%E4%BB%AA%E8%A1%A8%E7%9B%98.png)

[PAGE-01 页面设计与修正](../page-designs/01-home.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
