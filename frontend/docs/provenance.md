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

`src/adapters/robot-profile.ts` 现在有两条明确来源，互不回退。live 模式消费 `GET /api/v1/mobilecar/kinematics` 的 `landerpi.kinematics.v1` profile（零位、direction、TCP site/父体/局部平移、夹爪、相机挂载、sources、authority、limitations），并与 `GET /api/v1/mobilecar/execution-recipe` 的 `expected.model_id/model_sha256/scene_id` 与 `kinematics.digest` 交叉核对。缺元数据、recipe pin 不符、关节顺序/TCP/相机不一致或 consistency 失败时禁用本地 Joint/TCP 并显示原因；不会使用冻结样本的 arm-spec 顶替。冻结模式只使用 `public/sample/arm-spec.json`，明确标为独立历史参考，不参与 live 资格。`orientation_xyzw=null` 只保留“源未声明”语义，不生成姿态。authority 为 `platform_reference_not_native_attested`，零位是用户照片位姿且未标定；这些是本地位置 IK 预览的边界，不是部署核验、标定或执行许可。Actual 渲染始终直接使用后端完整 named model_joint_positions_rad。

本轮修正以 [MuJoCo 3.1.6 mesh 编译约定](https://mujoco.readthedocs.io/en/3.1.6/XMLreference.html#asset-mesh) 和参考 IK lab `_geom_mesh` / `_body_meshes` 为依据：源STL会经过编译预处理，编译后的geom位姿包含相应补偿；因此不能直接把原STL挂到该geom位姿下。实时源改为后端验证的编译STL（mesh_vert/mesh_face），前端只做 compiled geom→body→关节链→world_sim→Three 显示坐标变换；不修改根节点、joint4零位或Actual来补外观。几何来源身份通过后端 geometry_provenance 和每项 asset 的 coordinate_space/units/preprocessing/source_sha256/source_mesh_name 进入适配层。

材质处理保留真实RGBA：alpha=0时连同Ghost都跳过渲染构造；0<alpha<1时启用混合、不写opaque深度。源模型可见的基础primitive和mesh都按原身份保留，不按collision/group默认值或零件名称删除。几何验证诊断返回可见geom的局部AABB、变换后的world_sim AABB及矩阵，后者是变换局部包围盒的范围，不冒称接触真值。
