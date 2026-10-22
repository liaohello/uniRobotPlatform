# 受限对象配置与 MuJoCo 场景构建

规范 ID：`BE-SCENE-BUILDER` · 责任层：后端 · 版本：V0.2（2026-10-21）

状态：设计草案；S08/S09 是用户提供的分析文本，不自动视为所有细节已确认。Waypoint 范围以 S10 的用户明确选择为准。实现及产品验收均未执行。

来源：[S08](../../90-governance/sources/S08-frontend-ia-analysis.md)、[S09](../../90-governance/sources/S09-unified-development-reuse-analysis.md)。

[上级目录](README.md) · [总索引](../../README.md)

关联需求：[REQ-SCENE-005](../../indexes/05-requirements.md#req-scene-005)、[REQ-REUSE-002](../../indexes/05-requirements.md#req-reuse-002)

## 建议构建路径

原始机器人模型＋受控场景/资产＋Scene Configuration → Scene Builder → 可检查的实验场景与配置清单。

V1 优先已有 MuJoCo 模板和受限对象编辑；允许资产类型、数量、大小/颜色/位姿编辑范围逐项列入白名单，不提前构建通用建模器。颜色/尺寸修改也可能影响视觉与物理语义，必须绑定新配置。

## 模型与资产保持

保持机器人关节、零位、限位、惯量、执行器、碰撞/摩擦、传感器安装等源模型语义。不要让编辑器“导入—导出”未经检查地覆盖基线模型。Scene Builder 只应用允许的配置变换，保留源模型与资产身份。

这是一项适配建议：MuJoCo Scene Editor README 的 Limitations 确认可能丢弃未纳入机器人描述的 joints/actuators、geom 属性以及部分全局元素。因此先验证编辑交互与对象配置导出，不以能生成 XML 就视为模型等价。[官方说明](https://github.com/markusgrotz/mujoco-scene-editor#limitations)

## 检查输出

构建返回稳定对象映射、模型/资产/配置身份、允许改动和不支持项。加载成功、初态有效、动作接口一致、任务成功分别报告。模型等价核对与几何/物理验证的具体标准在 PoC 收敛；本轮没有编译模型或运行仿真。

参见 [复用 PoC](../../references/02-reuse-poc-plan.md)、[SO101 布置](../../10-frontend/02-scene-setup/03-so101-tabletop-layout.md)。
