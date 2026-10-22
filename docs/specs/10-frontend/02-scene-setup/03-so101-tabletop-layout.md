# SO101 桌面对象的 2D/3D 布置

规范 ID：`FE-SCENE-BIMANUAL-LAYOUT` · 责任层：前端 · 版本：V0.6（2026-10-22）

状态：设计草案；S08/S09 是用户提供的分析文本，不自动视为所有细节已确认。Waypoint 范围以 S10 的用户明确选择为准。实现及产品验收均未执行。

来源：[S08](../../90-governance/sources/S08-frontend-ia-analysis.md)、[S09](../../90-governance/sources/S09-unified-development-reuse-analysis.md)。

[上级目录](README.md) · [总索引](../../README.md)

关联需求：[REQ-SCENE-004](../../indexes/05-requirements.md#req-scene-004)

## 同一草案的两种视图

2D Top View 与 3D Scene View 读取同一 ExperimentDraft 的实例覆盖，不维护两份方块列表；基础布局来自固定 SceneVersion，资源编辑另走 SceneDraft。视图切换不提交运行命令，也不改变 Episode。

| 操作 | 2D 俯视图 | 3D 场景图 |
|---|---|---|
| 方块布置 | 数量、颜色/资产属性、XY、间距和删除 | 高度、旋转、遮挡、碰撞及相机关系检查 |
| 数值修改 | 与属性栏同步 | 相同稳定对象 ID 和修订 |
| 台面约束 | V1 候选先限制已知桌面高度 | 不开放任意物体在空中摆放作为默认路径 |
| 可达性 | 可切换左右臂/公共区域图层 | 显示来源、模型、计算配置和检查覆盖 |

工作空间图层必须来自对应模型的 FK/IK/采样结果或明确标记的示意，不把两个装饰圆当成可抓取保证。新增/删除、重叠、台面越界、随机摆放和资源上限的具体规则为 OQ-032。

修改只作用于初态配置。任务运行时改变物体属于 [物理干预](../07-viewport-tools/05-physical-force-tool.md) 或后续单独定义的测试输入，不自动通过 Teleport 写入在线世界。底层场景写入见 [场景构建](../../20-backend/01-session-scene/03-scene-builder-assets.md)。

验收入口：[TEST-SCENE-005](../../40-verification/04-task-config-workflow-acceptance.md#test-scene-005)。

## 页面图与设计归属（V0.3）

![相关工作区原始概念图，须结合页面修正使用](../../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E5%9C%BA%E6%99%AF%E9%85%8D%E7%BD%AE%E7%95%8C%E9%9D%A2.png)

[PAGE-02 页面设计与修正](../page-designs/02-scene-setup.md) · [全部页面图](../page-designs/README.md)。本图仅为功能所在页面的参考，实际可用工具、传感器和写入权限仍按本节点及共享契约。
