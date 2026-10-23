# uniRobot 3D Workbench · M1.2a

恢复前端实现的用户指令已解除本切片的暂停。此应用位于独立 worktree；主写者只写 `frontend/`，backend、公共契约、参考工程和根配置保持只读。现有诊断和草案实现保留。

## 现在可以操作

- 冻结真实 mobile_pick 场景与 LanderPi 网格，旋转/平移/缩放、前/侧/顶视角和聚焦。
- 对象树、mesh 点击/悬停、Inspector 共用稳定 link ID；双击机械臂部件选整臂。选中不授予控制权。
- 显式 Joint 模式：单关节环或用户角数值/滑条编辑，其他已有目标保留；°/rad 仅改变显示。native 模型 joint4 零位偏移继续保留。
- TCP 模式：world_sim（m、Z-up）轴/平面拖动及数值联动。Ghost 是本地位置 IK 或 FK 候选，Actual 来自冻结样本；预览和取消不写 Actual。
- 观察用相机、传感器区域与时间/事件区域统一装配。传感器媒体及连续 Episode 不在本单帧样本中，明确显示缺失，不放假视频或轨迹。
- Dockview 调整布局、关闭/重建面板、保存/恢复/重置布局；布局不改变目标、权限或运行状态。

空白左键拖动 Orbit，右键平移，滚轮缩放；手柄拖动期间不 Orbit。视口内 F 聚焦、Esc 取消本地目标，文本输入优先。失焦结束当前手势，保留最后本地草案；没有在线速度/力输入服务。

## 来源与限制

`public/sample/scene.json` 来自既有 native 服务的只读 SceneManifest；`snapshot.json` 是一次真实运行采样，**不是初始化状态、Episode 回放或实时状态**。23 个 STL 由本地参考资产复制并与 native 清单哈希核对。原生服务的 g4a1 来源不证明平台选定 G1 recipe 的集成已通过。身份、源时钟、模型摘要、捕获方式见 `public/sample/provenance.json`。

TCP 本地 DLS 仅尝试位置约束；没有姿态规划、碰撞检查、动力学验证、服务端 plan_id 或执行许可。不可达目标保留标记并隐藏 Ghost。虚线只作目标辅助线，不是已规划轨迹。Ghost 只显示机械臂，避免把重复底盘误认为实际运动。

Session、Owner/接管、执行与录制按钮保持禁用。平台 feed 未配置时明确失败并清掉旧场景；只有用户显式选择才回到冻结样本。所有数据读取集中于 `src/adapters/`，端点变更不散落到面板。[后端最小缺口与样例](docs/backend-gaps.md) 是交接建议，公共 wire 契约继续由后端对话维护。

## 代码边界

React/TypeScript 负责外壳、状态及面板；Three.js SceneView 采用参考模块的前端自有副本，并补齐生命周期和交互。没有导入 native main.js、R3F 或浏览器物理。依赖和锁文件仅位于本目录，主智能体为唯一写入者。

源码复用与资产来源见 [provenance](docs/provenance.md)。在原生服务器政策下执行构建、测试与浏览器；本地只读写源码/清单和传输。

## 运行和验证

以下 npm 命令**仅在授权服务器**、Node >=20.19 的独立环境中运行：

```bash
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm test -- --maxWorkers=2
npm run preview -- --port 18928
```

本地可运行 `python3 frontend/tools/release-source.py` 制作文件白名单、哈希和归档；上传后使用服务器 `tools/check-release.py` 核对输入、构建、测试并运行生产构建的 Chromium 检查。禁止用本机测试替代服务器执行。报告绑定同一 release，旧失败迭代不拼成最终通过。具体交付结果另见本方 [开发记录](docs/development.md)。
