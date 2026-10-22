# 设计图片与 PPT 页码对照

规范 ID：`REF-VISUAL-ASSETS` · 责任层：参考资料 · 版本：V0.6（2026-10-22）

当前统计：**26 个 PNG 文件／25 个独特内容／20 页 PPT**，以 [visual-assets.json](visual-assets.json) 为准；V0.6 只修复规范，未新增/改写图片。

V0.3 初次读取范围：`docs/foreendAssets` 中22个 PNG 文件和1个 PPTX，PNG 为21个独特内容；评估运行图“副本”与原件 SHA-256 相同。PPT 为20页，均插入这些 PNG，未发现额外文字说明，备注仅为页码；第5页同图插入两次，不计为新设计。

对 21 张独特图片逐张查看；PPT 图片与本地 PNG 按字节核对一致，因此直接引用现有 PNG。原 PPT 和所有原图不修改、不重命名、不移动。界面图是设计素材，并不证明功能已实现或图中硬件/指标真实。

[按页面看图](../10-frontend/page-designs/README.md) · [冲突分析](../90-governance/08-visual-design-conflicts.md) · [结构化图片与页面映射](visual-assets.json) · [原件完整性与来源](../90-governance/sources/S12-visual-materials.md)

| 图片 ID | 原文件 | PPT 页 | 关联页面 | 尺寸与备注 |
|---|---|---|---|---|
| IMG-001 | [RoboLab机器人仿真平台仪表盘.png](../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E5%B9%B3%E5%8F%B0%E4%BB%AA%E8%A1%A8%E7%9B%98.png) | 1 | [PAGE-01](../10-frontend/page-designs/01-home.md) | 1536×1024 |
| IMG-002 | [RoboLab机器人仿真场景配置界面.png](../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E5%9C%BA%E6%99%AF%E9%85%8D%E7%BD%AE%E7%95%8C%E9%9D%A2.png) | 2 | [PAGE-02](../10-frontend/page-designs/02-scene-setup.md) | 1672×941 |
| IMG-003 | [RoboLab机器人仿真控制台.png](../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0.png) | 3 | [PAGE-03](../10-frontend/page-designs/03-simulation.md) | 1672×941 |
| IMG-004 | [RoboLab机器人回放与标注界面.png](../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E5%9B%9E%E6%94%BE%E4%B8%8E%E6%A0%87%E6%B3%A8%E7%95%8C%E9%9D%A2.png) | 4 | [PAGE-04](../10-frontend/page-designs/04-episode-library.md)、[PAGE-05](../10-frontend/page-designs/05-episode-detail.md) | 1536×1024 |
| IMG-005 | [RoboLab机器人数据集管理界面.png](../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E6%95%B0%E6%8D%AE%E9%9B%86%E7%AE%A1%E7%90%86%E7%95%8C%E9%9D%A2.png) | 5 | [PAGE-06](../10-frontend/page-designs/06-dataset-collections.md)、[PAGE-07](../10-frontend/page-designs/07-dataset-version.md) | 1536×1024 |
| IMG-006 | [RoboLab模型训练控制台.png](../../foreendAssets/RoboLab%E6%A8%A1%E5%9E%8B%E8%AE%AD%E7%BB%83%E6%8E%A7%E5%88%B6%E5%8F%B0.png) | 6 | [PAGE-08](../10-frontend/page-designs/08-training-setup.md) | 1672×941 |
| IMG-007 | [RoboLab模型训练监控仪表板.png](../../foreendAssets/RoboLab%E6%A8%A1%E5%9E%8B%E8%AE%AD%E7%BB%83%E7%9B%91%E6%8E%A7%E4%BB%AA%E8%A1%A8%E6%9D%BF.png) | 7 | [PAGE-09](../10-frontend/page-designs/09-training-runs.md) | 1672×941 |
| IMG-008 | [RoboLab机器人推理与仿真控制台.png](../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E6%8E%A8%E7%90%86%E4%B8%8E%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0.png) | 8 | [PAGE-10](../10-frontend/page-designs/10-offline-inference.md) | 1536×1024 |
| IMG-009 | [RoboLab机器人策略仿真控制台.png](../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E7%AD%96%E7%95%A5%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0.png) | 9 | [PAGE-03](../10-frontend/page-designs/03-simulation.md) | 1536×1024 |
| IMG-010 | [机器人推理与真实部署控制台.png](../../foreendAssets/%E6%9C%BA%E5%99%A8%E4%BA%BA%E6%8E%A8%E7%90%86%E4%B8%8E%E7%9C%9F%E5%AE%9E%E9%83%A8%E7%BD%B2%E6%8E%A7%E5%88%B6%E5%8F%B0.png) | 10 | [PAGE-21](../10-frontend/page-designs/21-real-robot-future.md) | 1536×1024 |
| IMG-011 | [RoboLab 模型动物园仪表盘.png](../../foreendAssets/RoboLab%20%E6%A8%A1%E5%9E%8B%E5%8A%A8%E7%89%A9%E5%9B%AD%E4%BB%AA%E8%A1%A8%E7%9B%98.png) | 11 | [PAGE-11](../10-frontend/page-designs/11-model-catalog.md) | 1536×1024 |
| IMG-012 | [RoboLab机器人模型园深色仪表盘.png](../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E6%A8%A1%E5%9E%8B%E5%9B%AD%E6%B7%B1%E8%89%B2%E4%BB%AA%E8%A1%A8%E7%9B%98.png) | 12 | [PAGE-12](../10-frontend/page-designs/12-my-models.md) | 1672×941 |
| IMG-013 | [RoboLab模型库对比与注册仪表板.png](../../foreendAssets/RoboLab%E6%A8%A1%E5%9E%8B%E5%BA%93%E5%AF%B9%E6%AF%94%E4%B8%8E%E6%B3%A8%E5%86%8C%E4%BB%AA%E8%A1%A8%E6%9D%BF.png) | 13 | [PAGE-13](../10-frontend/page-designs/13-model-registry-compare.md) | 1672×941 |
| IMG-014 | [RoboLab机器人评估控制台.png](../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E8%AF%84%E4%BC%B0%E6%8E%A7%E5%88%B6%E5%8F%B0.png) | 14 | [PAGE-14](../10-frontend/page-designs/14-evaluation-setup.md) | 1536×1024 |
| IMG-015 | [机器人评估运行监控仪表盘.png](../../foreendAssets/%E6%9C%BA%E5%99%A8%E4%BA%BA%E8%AF%84%E4%BC%B0%E8%BF%90%E8%A1%8C%E7%9B%91%E6%8E%A7%E4%BB%AA%E8%A1%A8%E7%9B%98.png) | 15 | [PAGE-15](../10-frontend/page-designs/15-evaluation-running.md) | 1536×1024；副本与原件字节相同 |
| IMG-016 | [RoboLab 机器人评估结果仪表板.png](../../foreendAssets/RoboLab%20%E6%9C%BA%E5%99%A8%E4%BA%BA%E8%AF%84%E4%BC%B0%E7%BB%93%E6%9E%9C%E4%BB%AA%E8%A1%A8%E6%9D%BF.png) | 16 | [PAGE-16](../10-frontend/page-designs/16-evaluation-results.md) | 1536×1024 |
| IMG-017 | [机器人评测批次对比仪表板.png](../../foreendAssets/%E6%9C%BA%E5%99%A8%E4%BA%BA%E8%AF%84%E6%B5%8B%E6%89%B9%E6%AC%A1%E5%AF%B9%E6%AF%94%E4%BB%AA%E8%A1%A8%E6%9D%BF.png) | 17 | [PAGE-17](../10-frontend/page-designs/17-batch-comparison.md) | 1672×941 |
| IMG-018 | [机器人任务预设控制台.png](../../foreendAssets/%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BB%E5%8A%A1%E9%A2%84%E8%AE%BE%E6%8E%A7%E5%88%B6%E5%8F%B0.png) | 18 | [PAGE-18](../10-frontend/page-designs/18-task-presets.md) | 1536×1024 |
| IMG-019 | [RoboLab双臂机器人平台控制台.png](../../foreendAssets/RoboLab%E5%8F%8C%E8%87%82%E6%9C%BA%E5%99%A8%E4%BA%BA%E5%B9%B3%E5%8F%B0%E6%8E%A7%E5%88%B6%E5%8F%B0.png) | 19 | [PAGE-19](../10-frontend/page-designs/19-robot-platform.md) | 1536×1024 |
| IMG-020 | [RoboLab 场景库与机器人仿真编辑器.png](../../foreendAssets/RoboLab%20%E5%9C%BA%E6%99%AF%E5%BA%93%E4%B8%8E%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E7%BC%96%E8%BE%91%E5%99%A8.png) | 20 | [PAGE-20](../10-frontend/page-designs/20-scenes.md) | 1536×1024 |
| IMG-021 | [ScreenShot_2026-10-21_211828_609.png](../../foreendAssets/ScreenShot_2026-10-21_211828_609.png) | PPT 外截图 | [PAGE-08](../10-frontend/page-designs/08-training-setup.md) | 1656×1056 |

`IMG-021` 是 PPT 外训练截图，保留双 Evaluation 入口的历史冲突证据。每个资产的哈希、别名、原始路径和每个页面的参考覆盖程度在 JSON 中登记。资产图的时间戳/文件名不被用来推断方案优先级。

## 设计计划如何进入规范

上层 IA 与业务对象维持单一来源；页面图负责区域与交互；功能包负责规则；后端与共享契约负责权威状态和数据。每次任务切片开始前细化相关页面/契约/验收，实现后记录差异和证据，再进入下一任务，不等所有代码完成后才补 Specification。

## V0.4 新增用户设计图

2026-10-22 新增 IMG-022 后，本目录现有 23 个 PNG、22 个独特内容。上方 22 文件/21 独特内容是 V0.3 读取基线，原清单及其哈希保持不变；PPT 仍为 20 页旧版。

| 图片 ID | 原文件 | PPT 页 | 当前用途 | 尺寸 |
|---|---|---|---|---|
| IMG-022 | [Simulation V2](../../foreendAssets/RoboLab%E6%9C%BA%E5%99%A8%E4%BA%BA%E4%BB%BF%E7%9C%9F%E6%8E%A7%E5%88%B6%E5%8F%B0_v2_20261022.png) | 未收录 | PAGE-03 当前主参考，取代 IMG-003 的活动引用 | 1672×941 |

IMG-003 对 PAGE-03 改为历史对照，其原 PPT 第 3 页关系不变。详见 [S14](../90-governance/sources/S14-simulation-v2-update.md) 和 [旧新对照](../10-frontend/03-simulation/06-simulation-v2-review.md)。

## V0.5 三张 Scene Setup UI Reference

原样新增 3 张 PNG 后，素材目录为 26 个 PNG、25 个独特内容，PPT 仍 20 页未改。此处保留 V0.3/V0.4 历史统计；最新机器登记见 [visual-assets.json](visual-assets.json)。

| 图片 ID | 文件 | 当前用途 | PPT |
|---|---|---|---|
| IMG-023 | [导航 / Waypoint](../../foreendAssets/scene-setup-navigation-reference-20261022.png) | PAGE-02 导航变体 | 未收录 |
| IMG-024 | [近场抓取](../../foreendAssets/scene-setup-near-field-grasp-reference-20261022.png) | PAGE-02 单臂抓取变体 | 未收录 |
| IMG-025 | [双臂台面转运](../../foreendAssets/scene-setup-bimanual-transfer-reference-20261022.png) | PAGE-02 双臂转运变体 | 未收录 |

均为 1672×941；哈希/附件来源见 [S15](../90-governance/sources/S15-scene-setup-first-loop.md)。旧 IMG-002 保留为 PAGE-02 历史参考，新图字段和状态须服从 [任务规范](../10-frontend/02-scene-setup/02-task-template-configuration.md) 与 [公共契约](../30-contracts/07-task-scene-experiment-config.md)。不再以补齐全产品专图作为实现前置。
