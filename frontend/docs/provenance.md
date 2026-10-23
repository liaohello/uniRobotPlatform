# SceneView 与模型来源

- 参考仓库：`/home/liaozhengyan/Desktop/embodiedIntelligenceProj/mobileCar`。
- 参考 HEAD：`a5cef52d932ba41424b4bcc134539914031fda39`。
- renderer 来源：`src/mobilecar/ui/web/scene-view.js`，前端自有副本位于 `src/viewport/native-scene-view.js`。保留 Z-up→Y-up 根变换、xyzw、局部关节链、STL 几何与 Actual 映射，没有整页搬入 main.js。
- 副本必要改动：释放实际场景树而非先移除后漏清理；销毁时清 fit timer、RAF、observer、controls、几何/材质和 WebGL context；异步 STL 增加 disposed/manifest revision 检查；网格就绪后尊重用户相机操作。
- WorkbenchScene 增加选择/hover、显式单轴 Joint 目标环、TCP translate gizmo、手势仲裁、标准视角、Ghost/Target 与只读诊断。TransformControls 只操作本地代理对象，Actual 不作为其附着对象。
- 23 个必要 STL 与 arm_spec.json 来自参考资产；scene manifest 和一次运行快照来自已有 native 服务的只读 GET，未新建物理循环、RESET 或开录。每个网格的摘要、捕获时间及来源 profile 在 public/sample/provenance.json。
- native `model_sha256` 仅覆盖根 XML；本次完整前端输入另由 release source-manifest.json 固定，不能用根 XML 的 hash 代替全部资产/配置身份。运行采样不冒称初态或 G1 部署已验证。

库版本来自 frontend/package-lock.json。官方资料用于核对封装方式：[React effect lifecycle](https://react.dev/reference/react/useEffect)、[Three.js TransformControls](https://threejs.org/docs/pages/TransformControls.html)、[Dockview](https://github.com/dockview/dockview)。实际兼容性以本次服务器类型检查、构建和浏览器证据为准。
