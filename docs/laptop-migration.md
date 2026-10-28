# 换笔记本开发：Git 追踪与恢复清单

本清单针对当前 uniRobotPlatform 仓库。2026-10-27 已恢复服务器发布的前后端源码及配套 V0.8 Specification，M1 仍是 mobileCar 场景→运行→录制→回放；源码入口和外部依赖见 [整体代码导览](code-overview.md)。迁移不启动仿真或改变三工程的运行边界。

## 应提交到本仓库

| 内容 | 原因 |
|---|---|
| `README.md`、`LICENSE`、`.gitignore`、`.gitattributes` | 项目入口、许可、追踪范围与来源字节保留规则 |
| `AGENTS.md` | 项目级协作/设计/开发规则；备份不作为权威版本 |
| `docs/` | Specification、需求/来源/机器索引、M1 计划、原始设计图/PPT 和历史支持材料 |
| `backend/pyproject.toml` | Python 包元数据、依赖范围与命令入口 |
| `backend/src/unirobot/` | 网关、配置/Session、地图路线、历史读取与几何适配源码；保留早期静态工具页 |
| `backend/config/catalog.yaml`、`backend/migration_manifest.json` | 无凭据的公共任务/适配模板和迁移计划数据 |
| `backend/tests/`、`backend/.gitignore` | 现有测试源码及后端输出排除规则；纳入不等于测试已通过 |

`frontend/` 已包含独立 React/TypeScript 3D 工作台、锁文件、测试、工具和显式冻结模型样本，应随 Git 迁移。`node_modules` 与 `dist` 不提交；按前端 README 的服务器执行政策安装、构建和验证。源码齐备不表示 M1 产品已完整验收。

## 保留本机或另行恢复，不提交

- `.venv/`、`node_modules/`、Python/pytest/Ruff 缓存、构建产物：在新机器依据项目依赖重新生成，不复制旧解释器环境。
- `backend/var/` 等日志、进程输出和运行截图，`.workbuddy/`、本机 IDE/系统状态。
- `AGENTS.md.*.bak`：本地备份保留，不删除，不加入 Git。
- `.env`、`.env.*`、`backend/config/*.local.yaml|yml|json`、私钥、访问 token、真实服务器连接信息。可共享模板另用 `.env.example` 等无秘密示例。
- 原始 Episode、模型权重、完整数据集和其他工程的运行目录：依原工程保存/备份，不借本仓库上传。需要它们做回放或训练时，另行授权访问和迁移。

AGENTS 中的 `C:/Users/Administrator/.codex/...` 是原开发机配置示例，不是新笔记本必须拥有的工程路径。项目规则会随 Git 恢复；账号、凭据、本机全局配置及角色安装需在新机器自行配置/核对，不复制到本仓库。

## 三个源工程仍是外部依赖

本仓库尚未把 mobileCar、bimanual_proj、mujoco_learning 的代码、机器人资产或 Git 历史搬入。公共 catalog 使用相对项目路径，建议新机器保持：

```text
workspace/
├── uniRobotPlatform/
├── mobileCar/
├── bimanual_proj/
└── mujoco_learning/
```

这三个工程需要分别从各自仓库恢复。它们的未提交改动、忽略文件和私有环境不会因为 push uniRobotPlatform 自动到新机器。本次不操作它们的 Git，也不把它们作为嵌套仓库或 vendor 目录塞入平台。

只继续阅读规范/制定计划时，本仓库即可使用。启动当前任务目录时，缺少源工程或证据文件会产生 warnings；目录仍可能显示声明的任务，不能把条目、历史 maturity 标签或网关启动视为当前能力已可运行。现有部分测试会直接检查相邻工程的源码/报告，单独克隆平台不代表这些测试前提满足。

不同的 Python/MuJoCo/ROS/CUDA 环境继续按各自项目维护。同一仓库或相邻目录布局不意味着合并运行环境；mobileCar 的仿真、构建、自动浏览器和相关验证继续遵守其服务器执行政策。

## 新 Windows 笔记本的最小恢复步骤

以下为供新机器执行的说明，本次没有在当前机器安装依赖或启动服务。

```powershell
git clone https://github.com/liaohello/uniRobotPlatform.git
Set-Location uniRobotPlatform

# 平台网关要求 Python 3.11+；不在此环境安装三个原生仿真栈。
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .\backend

# 默认关闭 native 进程启动；仅启动本机任务目录网关。
$env:UNIROBOT_ALLOW_LAUNCH = "0"
.\.venv\Scripts\python.exe -m unirobot --host 127.0.0.1 --port 8090
```

当前网关的依赖是 `pyproject.toml` 中的范围约束，未提供完整环境锁文件；以上是恢复开发入口，不承诺与旧机逐字节相同环境。测试/运行环境版本在 M1.1 按实际执行位置固定，不导入本机缓存来伪造可复现环境。

## 路径和服务器地址不同怎么办

默认项目根由 `docs/specs/catalog.json` 定位，不依赖原机器 Desktop 的绝对路径。默认 catalog 的 `project_root` 相对平台根解析；`base_url` 的 loopback 只在对应服务或授权隧道位于当前机器时有效。

目录布局或服务地址不同，可复制一份**完整 catalog**为本机配置：

```powershell
Copy-Item -LiteralPath backend/config/catalog.yaml -Destination backend/config/catalog.local.yaml
# 只编辑本机副本中的 project_root、base_url 等所需配置。
$env:UNIROBOT_CATALOG = (Resolve-Path -LiteralPath backend/config/catalog.local.yaml).Path
$env:UNIROBOT_ALLOW_LAUNCH = "0"
.\.venv\Scripts\python.exe -m unirobot --host 127.0.0.1 --port 8090
```

当前加载器没有 adapter-only 增量覆盖机制，不能只写一段 adapters 并假设自动与公共配置合并。也可用 `--catalog` 指向完整文件。显式 `UNIROBOT_REPO_ROOT` 仅在需要覆盖自动定位时使用。

模板中的 native 启动命令包含服务器/Linux 环境入口；新笔记本不应直接开启自动启动来试跑这些命令。若仿真仍在原服务器，按原工程方式恢复授权连接/隧道，在本机私有 catalog 指向可达服务；账号/密钥/真实连接字段不进入 Git。

## 恢复后检查

1. 检查 Git 版本与工作区状态，阅读 `AGENTS.md`、Specification 总索引和 M1 实施计划。
2. 核对源工程目录、配置/模型版本、服务可达性和接口能力；离线或缺失如实显示，不使用旧截图当 Ready。
3. 先做 M1.1 接入核对，再进入 prepared/Start、录制与回放；源码迁移完成不等于 M1 已验收。

[文档入口](README.md) · [当前范围](specs/00-overview/10-first-task-closed-loop.md) · [M1 计划](specs/00-overview/09-page-design-delivery-plan.md)
