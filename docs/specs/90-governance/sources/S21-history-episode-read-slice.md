# S21｜真实历史 Episode/segment 只读 reader 首个切片（2026-10-25）

类型：当前用户 Goal 原文记录（本次会话）。本文件只保存该 Goal 的范围与约束，不替代 Specification 主责契约，也不改变此前 S14～S20 的事实。

## 用户 Goal 要点

工作目录 `~/.codex/worktrees/backend-m1-read/uniRobotPlatform`。基线：HEAD `dfa2400`；18959 是前端正在消费的统一候选，必须保留不替换；8792 仍为原 drvfix/G4A2，只允许 GET；原生历史接口已能列出 348 条记录，但目录 COMPLETE 不等于已独立验证完整性；原生已有 ReplayReader 与 list/detail/assets，平台尚无历史 reader；不需要先决定 G1/G4A2 或部署 native 才能读取历史记录。

实施要求：

1. 先固定一个明确历史来源及实际 recording_root；优先复用既有只读 reader/HTTP/文件格式；原始数据留在服务器，不搬目录、不重写、不导出重算，不修改或重启 8792 来增加接口。
2. 由主智能体冻结最小历史读取契约与 OpenAPI：Episode 列表、轻量详情、segment/可用流、状态与动作、事件/观测索引、媒体资产读取；依据真实记录规模提供有界分页或按流/时间区间读取；不让前端每次查看都加载整份大型详情；不提前建设通用数据查询框架。
3. 身份必须保留 source/adapter、run、generation（若原记录有）、episode、segment、reader/schema 版本及原始引用；不把 episode 显示名当全局唯一键；同名不同 run 不能串读；legacy 无 ValidatedSnapshot/Session sidecar 时明确未知，不伪造平台配置关联。
4. 时间和动作保持原义：保留 source/sim/backend 时间、序列、clock/frame、单位，区分 Actual、记录的 Target、命令意图及执行反馈；只冻结本切片需要的游标/时间选择规则，不按浏览器到达顺序或文件下标伪造同步时间。
5. 完整性分层：原记录声明的 COMPLETE/FAILED、complete_tail、校验和、实际读取验证分别表达；未全量核验不得声称全 Episode 已验证完整；training_qualified=false 不阻止合格原始读取；缺流、坏索引、缺媒体、未知时钟和不支持格式明确定位，不静默丢弃或制造默认帧。
6. 为未来 3D 回放提供记录中的模型/场景/变换身份；不能把当前在线 geometry 或 Actual 自动套到历史 Episode；无法证明模型匹配时明确 3D 回放受限；仍可提供真实元数据、事件与可用媒体。
7. 历史 API 只提供受限读取：路径限定在已配置来源和 Episode 目录内，复用已有路径保护，拒绝越界或跨 Episode 资产引用；不代理 validate/assessment 写操作、控制、RESET、录制、物理步进或任何重执行功能。
8. 顺带补齐发布身份的小缺口：将实际启动器纳入身份清单或独立记录工具摘要；保留完整 native 清单与生产 pin 的边界；不重复实现已完成的 STOP/end，不另造签名系统。

验证与交付：所有测试与读取验证在服务器执行；选择真实代表记录，至少验证 COMPLETE 与 FAILED/不完整来源以及实际存在的状态、动作、事件和媒体读取；损坏/缺文件/重复 ID 等故障在隔离夹具或副本中验证，不修改原始 Episode、不为制造案例启动录制；记录验证前后原始文件摘要不变，native 请求仅 GET，无新物理实例；发布新独立候选端口，保留 18959 及既有服务，继续携带 geometry-2、Map/Route、Session/STOP/end 原有能力；交付实际 API、来源身份、时间/单位、分页规则、可用流、完整性范围、错误样例及前端接线说明；运行聚焦及适用回归并保留历史失败与基线，不跳过或称全绿；只修改 backend/ 与必要契约/证据，不修改 frontend/；平台本地提交，不推送；不提交/部署 native；Goal 完成只表示真实历史 reader 切片完成，不表示同步回放 UI、新采集闭环或正式 M1.5/M1 验收通过。

## 多 agent 约定

主智能体负责设计裁决、代码/契约修改、服务器验证与整合；`default`、`fork_turns=none`，最多 3 个只读子 agent：A 原生历史格式、可用流、身份和时钟字段检索；B 既有回放契约与最小读取 API 对照；C 只读路径、完整性、缺流/损坏及验证覆盖核查。子 agent 不改文件、不执行测试/构建/安装、不派生 agent。

## 效力

本来源为历史 reader 首切片的范围、"读取兼容 ≠ 完整性验证 ≠ 渲染能力"的分层要求、身份与时间语义保留要求、有界分页与受限读取路径边界，以及启动器纳入发布身份的做法提供依据。实现与证据见 [M1.5a 交付记录](../../../backend-m1.5a-history-reader.md) 与 [M1.5a 证据册](../../../evidence/m1.5a-history/README.md)。
