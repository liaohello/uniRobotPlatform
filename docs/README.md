# 项目设计文档入口

当前持续维护的规范入口是 [Specification 总索引](specs/README.md)。文档按前端、后端、共享契约和验收分层，再按功能包与编号节点细化。

换笔记本时使用 [Git 追踪与恢复清单](laptop-migration.md)，区分本仓库源码、三个外部工程和本机私有环境。

当前优先阅读 [统一 3D 工作台实施计划](specs/00-overview/09-page-design-delivery-plan.md)：先统一 React/TS 外壳与 Three.js 复用边界，下一份前端产物为可操作 3D 样板，再在同一工作台接配置、控制、录制与回放。前端实现继续暂停。[M1.1](m1.1-integration-check.md) 与 [M1.2 草案切片](m1.2-drafts.md) 的诊断/草案证据保留，不代表主工作台或真实闭环完成。M1.2b 的[配置验证与 Session 准备链路](backend-m1.2b.md)（候选 18943）保留了历史契约与真实拒绝证据；M1.2c 的[原生绑定候选、配方证明与无 RESET 开录](backend-m1.2c.md)（平台候选 18944，原生补丁未部署）修正了锁核验；M1.2d 的[两项 P1 修复、当前状态刷新与真实 HTTP 集成](backend-m1.2d.md)（平台候选 18949，原生补丁未部署）进一步修复生命周期竞态/prepared-only TTL，并让平台实际客户端与 native mock 完成协议集成。M1.3 的[版本化地图读取与带朝向 Route Draft/Version](backend-m1.3.md)（平台候选 18953）交付历史 G3B Room A/B 固定版本、必填 x/y/yaw、Draft/不可变 Version 保存及地图/路线显示资源；保存与导航执行隔离，未部署 8792，也未证明导航能力。M1.4 的[身份绑定机器人 STOP 与可靠录制结束候选](backend-m1.4.md)（平台候选 `m1i-20261024T163746Z-platform`，native 补丁未提交未部署）交付 `m1-stop-1`/`m1-end-1` 契约、五层分离回执、并发与幂等规则，并在服务器完成 mock backend + 真实 Recorder 文件的隔离 HTTP 集成；真实停车确认与 8792 部署仍未执行。M1.4b 的[统一可联调候选与部署前发布身份](backend-m1.4b-unified-candidate.md)（候选 release `m1j-20261025T020857Z-platform`，统一候选常驻基址 `http://127.0.0.1:18959`，用前确认存活）把 geometry-2、Map/Route、Session/`current` 与 STOP/end 契约收敛进同一冻结源码与启动清单，并为待部署 native 候选提供缺项必失败的完整发布身份。M1.5a 的[真实历史 Episode/segment 只读 reader 首个切片](backend-m1.5a-history-reader.md)（候选 release `m1k-20261025T040435Z-platform`，历史候选常驻 `http://127.0.0.1:18960`）把服务器 348 条真实录制以五条受限 GET 暴露：有界列表、轻量详情、可用流、按流记录页与 Episode 内媒体资产，保留原生身份/时间/动作语义，并把记录声明、`complete_tail`、tail 校验和与实际读取验证分四层表达（native tail 对自身 `episode.json` 为过期自校验，抽样 16/16 如实报告为 `mismatch_present`）；61/61 服务器断言、已覆盖的 696 个身份文件聚合摘要读取前后不变（一次人工误发的 native validate 只重写了一条记录的派生 `quality_report.json`，已在交付记录与证据册如实记录）；同步回放与新采集闭环仍未完成。M1.5b 的[历史 reader 只读整改、根目录隔离与可复现发布](backend-m1.5b-history-readonly-hardening.md)（候选 release `m1p-20261025T053030Z-platform`，`http://127.0.0.1:18964`）把只读改为由构造保证（GET-only 探测入口 + 逐条请求日志，实测 51 次全为 GET）、统一索引与读取两侧的软链越界拒绝、修复 `event_seq` 区间过滤与日历时间基数值边界，并用重算断言把报告绑定到冻结源码摘要 `4090935b4c45c900…`（69/69 与 28/28，覆盖集合 946 文件 drift=[]）；同时撤回超出证据的表述并更正 `transforms.jsonl` 语义。M1.5c 的[真实帧关联切片与 run 身份边界修正](backend-m1.5c-frame-linkage.md)（候选 release `m1s-20261025T084308Z-platform`，`http://127.0.0.1:18966`）补上 run 目录身份必须在每次读取时校验（缓存索引建立后换成兄弟 run 的软链不再能以原身份读出），并新增第六条受限 GET `GET /api/v1/episodes/{episode_id}/frames`（`unirobot-mobilecar-frame-link-1`）：以真实 `observations/persist` 帧为锚点，只按记录里存在的键关联 rgb/depth 观测行、`transforms`、`rgbd_capture_timing` 与 capture tick 上的状态事件，未解析的 `feedback_sample_id`（实测 3/303 命中）如实返回 `unresolved_reference`，状态只带"早于采集 0.34–8.78 ms"这类记录字段相减得到的年龄，明确不插值、不同源已验证、不解锁历史 3D；86/86 帧与读取断言、28/28 统一回归、聚焦 31 passed、全量 159 passed / 3 项历史失败、59 次请求全为 GET、946 覆盖集合 `drift=[]`。真实运动、RESET、物理停车与回放仍未开放。

另开会话时先读 [新会话交接说明](handoff.md)；本次讨论的可读用户/助手正文保存在 [2026-10-22 会话存档](conversations/2026-10-22-scene-setup-dialogue.md)，历史建议以当前规范取代关系为准。

当前组织版本为 V0.8，未修改的规范保留各自版本。[mobileCar 四步闭环与 bimanual 复用](specs/00-overview/10-first-task-closed-loop.md) 次序不变：先场景→运行→录制→回放，再验证多宿主下组件复用，训练/预测后续。完整演变见 [修订记录](specs/90-governance/07-change-log.md)。

| 阅读目的 | 入口 |
|---|---|
| 理解目录组织与设计方法 | [阅读指南](specs/indexes/01-reading-guide.md) |
| 从画面区域找功能 | [前端区域索引](specs/indexes/03-ui-regions.md) |
| 从一个功能查到前后端与验收 | [功能映射](specs/indexes/06-feature-map.md) |
| 查看原需求、决定和未决问题 | [需求矩阵](specs/indexes/05-requirements.md) / [决策](specs/90-governance/01-decisions.md) / [未决](specs/90-governance/02-open-questions.md) |
| 查看来源与章节迁移 | [来源登记](specs/90-governance/06-sources.md) / [迁移表](specs/indexes/07-source-migration.md) |

[设计过程与 Specification 总册](设计过程与Specification总册_20261021.md) 保留原始讨论、建议和演变，当前主题规范在 `specs/` 维护。

[前端需求分析 V0.2](frontend_analysis_v0.2.md)、[产品需求初稿](productReq.md)、[原始前端参考材料摘录](设计过程与Specification总册_20261021.md#doc-044)、[原始需求分析](requireAnalysis.md)、[任务意图](coreIntent.md) 是历史与参考材料。其内容与更新用户决定不一致时，以当前规范中的来源与取代记录为准；目录整理不把建议转为已确认需求。

### V0.3 前端图片与页面 Specification

[页面与图片索引](specs/10-frontend/page-designs/README.md) · [设计冲突分析](specs/90-governance/08-visual-design-conflicts.md) · [图片/PPT 对照](specs/references/04-visual-asset-catalog.md)。原素材保留，页面设计与功能/后端规范交叉索引。
