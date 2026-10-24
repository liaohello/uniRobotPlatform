# SceneView 与模型来源

- 参考仓库：`/home/liaozhengyan/Desktop/embodiedIntelligenceProj/mobileCar`。
- 参考 HEAD：`a5cef52d932ba41424b4bcc134539914031fda39`。
- renderer 来源：`src/mobilecar/ui/web/scene-view.js`，前端自有副本位于 `src/viewport/native-scene-view.js`。保留 Z-up→Y-up 根变换、xyzw、局部关节链、STL 几何与 Actual 映射，没有整页搬入 main.js。
- 副本必要改动：释放实际场景树而非先移除后漏清理；销毁时清 fit timer、RAF、observer、controls、几何/材质和 WebGL context；异步 STL 增加 disposed/manifest revision 检查；网格就绪后尊重用户相机操作。
- WorkbenchScene 增加选择/hover、显式单轴 Joint 目标环、TCP translate gizmo、手势仲裁、标准视角、Ghost/Target 与只读诊断。TransformControls 只操作本地代理对象，Actual 不作为其附着对象。
- 23 个必要 STL 与 arm_spec.json 来自参考资产；scene manifest 和一次运行快照来自已有 native 服务的只读 GET，未新建物理循环、RESET 或开录。每个网格的摘要、捕获时间及来源 profile 在 public/sample/provenance.json。
- native `model_sha256` 仅覆盖根 XML；本次完整前端输入另由 release source-manifest.json 固定，不能用根 XML 的 hash 代替全部资产/配置身份。运行采样不冒称初态或 G1 部署已验证。

库版本来自 frontend/package-lock.json。官方资料用于核对封装方式：[React effect lifecycle](https://react.dev/reference/react/useEffect)、[Three.js TransformControls](https://threejs.org/docs/pages/TransformControls.html)、[Dockview](https://github.com/dockview/dockview)。实际兼容性以本次服务器类型检查、构建和浏览器证据为准。

本轮只读接入：实时场景/资产/状态来自平台 `unirobot-mobilecar-read-1`，不合并 frozen diagnostics/Oracle。world_links 明确为编译初态；mesh 字节在解析 STL 前以 Web Crypto 核对清单 SHA256。相同 URI 在当前 manifest 内复用读取，切源/卸载取消请求，跨 manifest 不复用旧缓存。

`src/adapters/robot-profile.ts` 只提取已有 arm-spec 的 `user_coordinates` 与 TCP 父体/局部偏移，丢弃 initial_positions 和动态诊断；模型限位取本次 capabilities 的用户角限位加已固定零位。仅匹配模型 XML 摘要 `3ca3d6d0a92a48bbfbce5ac7a04e37a0f7cf7a73297045ae327bf461ad50e280`、joint1…5 和 guide_rod_link。此匹配不证明 deployed_content_verified，不能保证远端全部配置未变化；它是明确版本化的前端本地候选依据，不用于生成任何在线请求。公共能力接口尚缺版本化坐标映射/TCP安装偏移，建议后端后续暴露并验证后替换该本地元数据。Actual 渲染始终直接使用后端完整 named model_joint_positions_rad。

本轮修正以 [MuJoCo 3.1.6 mesh 编译约定](https://mujoco.readthedocs.io/en/3.1.6/XMLreference.html#asset-mesh) 和参考 IK lab `_geom_mesh` / `_body_meshes` 为依据：源STL会经过编译预处理，编译后的geom位姿包含相应补偿；因此不能直接把原STL挂到该geom位姿下。实时源改为后端验证的编译STL（mesh_vert/mesh_face），前端只做 compiled geom→body→关节链→world_sim→Three 显示坐标变换；不修改根节点、joint4零位或Actual来补外观。几何来源身份通过后端 geometry_provenance 和每项 asset 的 coordinate_space/units/preprocessing/source_sha256/source_mesh_name 进入适配层。

材质处理保留真实RGBA：alpha=0时连同Ghost都跳过渲染构造；0<alpha<1时启用混合、不写opaque深度。源模型可见的基础primitive和mesh都按原身份保留，不按collision/group默认值或零件名称删除。几何验证诊断返回可见geom的局部AABB、变换后的world_sim AABB及矩阵，后者是变换局部包围盒的范围，不冒称接触真值。
