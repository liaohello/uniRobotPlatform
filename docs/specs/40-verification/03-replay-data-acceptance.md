# 回放、标注与数据管理验收

规范 ID：`QA-DATA` · 责任层：验收 · 文档成熟度：基础草案（保留原文逐项状态）

[来源总册 doc-037](../../设计过程与Specification总册_20261021.md#doc-037) · [上级功能包](README.md) · [总索引](../README.md)

> 本文件已按主题迁入当前目录；需求确认程度以原文标记为准。文档迁移不表示已实现、已验收或技术栈已冻结。后续在此维护主题正文，总册保留历史。

版本：V0.1｜整理日期：2026-10-21（America/Los_Angeles）

状态：待执行；功能细节为方案

来源：S01、S02、S05（详见[来源档案](../90-governance/06-sources.md)）

关联需求：见需求追踪矩阵中的引用与相关主责规范

所有测试均为未执行的规格草案。

| ID | 操作 | 预期 |
|---|---|---|
| <a id="test-replay-001"></a>TEST-REPLAY-001 | 选择 Episode，播放/暂停/倍速/定位 | 3D、相机、曲线按约定时间同步 |
| <a id="test-replay-002"></a>TEST-REPLAY-002 | 回放时拖动时间轴或 3D | 不修改后台在线仿真；不产生在线运动命令 |
| <a id="test-replay-003"></a>TEST-REPLAY-003 | 某个数据流缺帧或过期 | 明确缺失，不伪装同步连续 |
| <a id="test-ann-001"></a>TEST-ANN-001 | 添加/修订阶段标签 | 独立版本，不覆盖原始状态、动作与事件 |
| <a id="test-data-001"></a>TEST-DATA-001 | 任务失败但记录完整 | 成功与完整性字段独立 |
| <a id="test-data-002"></a>TEST-DATA-002 | 任务成功但缺相机帧 | 可按用途判定不满足训练资格，保留原因 |
| <a id="test-export-001"></a>TEST-EXPORT-001 | 导出 LeRobot 训练数据 | 相机键、动作语义、维度/单位、频率/对齐有检查报告 |
| <a id="test-trace-001"></a>TEST-TRACE-001 | 从模型/评估查看来源 | 追到数据版本、配置和 Episode；该功能后续分期 |

逐帧、循环、标注区间边界和对齐误差的具体阈值应在回放详细设计后补充；此目录尚未执行实际采集/回放验收。

## 关联文档

- [Replay & Annotation｜同步回放与标注](../10-frontend/04-replay-annotation/01-synchronized-playback.md)
- [Dataset Management｜数据管理](../10-frontend/05-datasets/01-browser-quality-export.md)
- [Episode、采集、事件与标注契约](../30-contracts/03-episode-events-annotations.md)

[需求追踪矩阵](../indexes/05-requirements.md) · [Wiki 首页](../indexes/01-reading-guide.md) · [目录入口](../README.md)
