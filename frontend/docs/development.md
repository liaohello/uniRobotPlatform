# M1.2a 前端开发记录

日期：2026-10-23（America/Los_Angeles）。当前用户明确授权恢复前端，从 V0.7 M1.2a 开始；不修改 backend、native 或公共契约。此页是验证后的开发记录，刻意不纳入自身 release 哈希，避免报告自引用；运行源码与测试仍全部纳入 allowlist。

## 基线与文件所有权

- 原工作目录：`/home/liaozhengyan/Desktop/uniRobotPlatform`，main HEAD `1b17d6c1f7cccb171d5db8720a0e6f8ffd960623` 的现有未提交/未跟踪成果原地保留，未 reset/clean，也未改变原 index。
- 使用临时 Git index 固定包含最新 V0.7 文档、既有 M1.1/M1.2 代码/证据的共同基线 `2f7ff9b091c060034e55d2f387dbb6e130aaada3`（本地 `codex/m12a-common-baseline-20261023`），不是从旧 HEAD 直接开始。
- 独立 managed worktree：`/home/liaozhengyan/.codex/worktrees/frontend-m12a/uniRobotPlatform`；分支 `codex/m12a-workbench`。后端和公共契约在此相对共同基线没有修改，原主目录的并行修改不被覆盖。
- 本切片仅写 `frontend/`，包括独立 package.json/package-lock、工具、源资产与开发报告。没有改根配置或部署配置，没有推送。

## 实现与数据来源

详见 README 与 provenance。冻结真实几何/运行采样用于观察，Target/Ghost/FK/位置 IK 是前端本地预览。没有真实 Session、执行授权、指令提交、录制或连续 Episode 回放。

三路只读任务已回收：SceneView/资产/坐标与生命周期、交互条款、前后端数据缺口。原交互代理一次执行失败，由新只读代理接管完成；没有把失败任务算作完成。追加静态复核发现的场景替换 marker/失败记录清理与数据源 targetRef 清理已由主智能体处理。子代理没有修改文件或运行验证。

## 同一冻结版本的最终验证

最终 release：`m12a-20261023T162150Z-bf82d5697880`；56个输入文件逐项核对，aggregate SHA-256：`bf82d5697880125086002666d74046a2a103a96f868b9abee54bf2bf8b534102`。当前运行源码/测试/锁文件与该清单一致。本页与 reports 是验证后记录，排除在自引用哈希之外。

| 实际执行（全部在服务器） | 结果与边界 |
|---|---|
| 类型检查与生产构建 | `npm run build`（含 `tsc --noEmit`）通过；Node20.20.2，依赖锁摘要见 environment.json |
| 目标/FK/位置 IK 聚焦测试 | 6 passed：真实关节链 FK 与冻结 TCP 相符、单关节目标保留、joint4 零位、限位/非有限输入、本地位置候选、不可达反馈 |
| 生产构建的 Chromium 检查 | 29 checks passed；对象树/mesh/Inspector、Joint 环真实指针拖动、TCP 轴真实指针拖动与相机隔离、Actual 不变、文本焦点/取消、失焦事件、resize、布局重建/恢复、显式切源、零 native 命令请求 |
| 来源/执行隔离 | 冻结样本不授予 Session；Start/执行/接管/录制禁用；浏览器101项请求均 GET，没有 native 命令/runtime 请求 |
| 原生影响 | 验证前后 run/generation/Episode/recording 身份相同。没有新建物理实例或停止既有服务；只结束了本任务旧版静态预览进程 |
| 源码/证据回传 | 当前源码清单、12个精简证据文件哈希核对通过；回传包约0.7MB，原始数据与环境留在服务器 |

证据：[索引](../reports/m12a-20261023T162150Z-bf82d5697880/server-artifact-index.json)、[源码清单](../reports/m12a-20261023T162150Z-bf82d5697880/source-manifest.json)、[构建](../reports/m12a-20261023T162150Z-bf82d5697880/build.log)、[6项测试](../reports/m12a-20261023T162150Z-bf82d5697880/unit.json)、[29项浏览器检查](../reports/m12a-20261023T162150Z-bf82d5697880/browser/browser.json)、[原生前后](../reports/m12a-20261023T162150Z-bf82d5697880/native-read-only.json)、[环境](../reports/m12a-20261023T162150Z-bf82d5697880/environment.json)。

这些是 M1.2a 离线工作台交互与工程验证，对应既有交互 TEST 的适用子集；不将 TEST-MOBILE-001/002、真实权限/命令/采集/回放或完整交互条款标为已通过。

## 可操作预览与限制

- 最终静态预览：服务器回环端口18931，当前 SSH tunnel 转发为 `http://127.0.0.1:18931`。进程 PID/目录见 [preview.json](../reports/m12a-20261023T162150Z-bf82d5697880/preview.json)。预览随本任务服务器进程与隧道存活；没有对外发布。Codex 面板已请求打开该地址。
- 真实网格与运行单帧为冻结来源，位置 Target / Ghost 为本地计算；本样本含原生 GT_DEBUG 工程观察数据，不作为受限采集的 OperatorView/Policy 输入。后续真实接入的载荷权限应由服务端按 Profile 裁决。
- RGB/Depth 无媒体，时间轴没有连续 Episode；实时状态、真实授权/执行、录制和历史同步流尚待接通。本地 IK 只满足位置约束，没有姿态/碰撞/动力学/规划认证。
- 浏览器实际 GL renderer 为 ANGLE/SwiftShader 软件渲染，验证了1600×1000及1280×900桌面布局；没有宣称客户端GPU帧率或远程实时链路延迟达标。默认关闭实时阴影避免软件渲染负载和阴影伪影；真实几何/状态未更改。
- 生产 JS 约1.2MB（gzip约312KB），构建有大 chunk 提示；本切片没有为消除提示额外拆架构。手机布局未验收。
- 中间迭代保留在服务器，不拼接结果：首轮 TCP 测试坐标未命中手柄；新增 Joint 检查时修正了对 Three.js 旋转手柄几何类型的测试投影；新增失焦拖动后修正测试误用旧 revision 的断言。最终29项均在上述同一冻结版本重跑通过。

![服务器生产构建下的 TCP 本地目标预览，非真实执行](../reports/m12a-20261023T162150Z-bf82d5697880/browser/workbench-tcp-target.png)

## 后端接续

[最小数据/服务缺口与具体样例](backend-gaps.md)。平台只读 scene/Actual 可先接入，不等待控制/录制全部齐备；端点映射仍集中在 adapters，wire 契约由后端对话维护。M1.2b～M1.6 不因本前端样板而完成。
