# 历史数据读取与标注修订存储

规范 ID：`BE-DATA-REPLAY` · 责任层：后端

文档状态：基础草案；本轮按已有需求整理职责，尚未冻结具体实现。需求确认程度逐项继承来源，未声明已有 API 或运行能力。

来源：[doc-017](../../../设计过程与Specification总册_20261021.md#doc-017)、[doc-030](../../../设计过程与Specification总册_20261021.md#doc-030)、[doc-033](../../../设计过程与Specification总册_20261021.md#doc-033)、[doc-037](../../../设计过程与Specification总册_20261021.md#doc-037)

[上级功能包](README.md) · [总索引](../../README.md)

关联需求：[REQ-REPLAY-001](../../indexes/05-requirements.md#req-replay-001)、[REQ-REPLAY-002](../../indexes/05-requirements.md#req-replay-002)、[REQ-ANN-001](../../indexes/05-requirements.md#req-ann-001)

## 目标与责任边界

为历史数据浏览提供索引与时间查询，保存独立标注版本。浏览回放不调用在线控制和物理推进；动力学重执行若另行支持，应与只读回放区分。

## 设计节点

| 节点 | 当前基线 / 需要定义的行为 |
|---|---|
| 读取 | 查询 Episode、数据流、图像/状态与时间关系，缺帧显式返回。 |
| 对齐 | 按共享时间契约查询；插值与时差阈值待定。 |
| 标注 | 保留来源、字典/修订版本与作者；不覆盖原始事件。 |
| 隔离 | 历史上下文与当前 Session 分离，标注写入不成为在线机器人操作。 |

## 未决与依赖

关联 OQ-021、OQ-023。区间规则、重叠和审核协议未冻结。

## 关联规范

- [Replay & Annotation｜同步回放与标注](../../10-frontend/04-replay-annotation/01-synchronized-playback.md)
- [统一时间轴与事件轨](../../10-frontend/08-observation-inspector/03-timeline-event-tracks.md)
- [Episode、采集、事件与标注契约](../../30-contracts/03-episode-events-annotations.md)
- [回放、标注与数据管理验收](../../40-verification/03-replay-data-acceptance.md)

## 验收入口

- [TEST-REPLAY-002](../../40-verification/03-replay-data-acceptance.md#test-replay-002)（现有草案，未执行；依赖的未决规则须先收敛）。
- [TEST-ANN-001](../../40-verification/03-replay-data-acceptance.md#test-ann-001)（现有草案，未执行；依赖的未决规则须先收敛）。
