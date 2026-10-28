import type { LocalTarget, ViewSample, Vec3 } from '../adapters/types';
import { PreviewKinematics } from '../viewport/kinematics';
export const deg = (r: number) => r * 180 / Math.PI;
export const rad = (d: number) => d * Math.PI / 180;
export function jointTarget(sample: ViewSample, previous: LocalTarget | null, name: string, userRad: number): LocalTarget {
  if(!sample.armSpec)throw new Error('此模型缺少版本化用户角映射；只读监控可用，本地预览禁用');
  const index = sample.capabilities.arm_joint_names.indexOf(name);
  const [min,max] = sample.capabilities.arm_user_limits_rad[index];
  if (!Number.isFinite(userRad) || userRad < min - 1e-8 || userRad > max + 1e-8) throw new Error(`${name} 目标超出原生限位`);
  const joints = { ...(previous?.jointModelRad ?? sample.actual.model_joint_positions_rad), [name]: sample.armSpec!.user_coordinates.zero_model_rad[index] + userRad * sample.armSpec!.user_coordinates.direction[index] };
  const tcp = new PreviewKinematics(sample.scene, sample.actual, sample.armSpec).forward(joints);
  return { mode: 'joint', revision: (previous?.revision ?? 0)+1, jointModelRad: joints, tcpWorldM: tcp, frame: 'world_sim', preview: 'joint-pose', residualM: null };
}
export function tcpTarget(sample: ViewSample, previous: LocalTarget | null, position: Vec3): LocalTarget {
  if(!sample.armSpec)throw new Error('此模型缺少 TCP 安装/零位元数据，本地 IK 不可用');
  if (!position.every(Number.isFinite)) throw new Error('TCP 目标必须是有限数值');
  const ik = new PreviewKinematics(sample.scene, sample.actual, sample.armSpec).solve(position, previous?.jointModelRad ?? sample.actual.model_joint_positions_rad);
  return { mode: 'tcp', revision: (previous?.revision ?? 0)+1, jointModelRad: ik.joints, tcpWorldM: position, frame: 'world_sim', preview: ik.converged ? 'local-position-ik' : 'unreachable', residualM: ik.residual };
}
export function userJoint(sample: ViewSample, target: LocalTarget | null, name: string) {
  const i=sample.capabilities.arm_joint_names.indexOf(name);
  return target ? (target.jointModelRad[name] - sample.armSpec!.user_coordinates.zero_model_rad[i]) / sample.armSpec!.user_coordinates.direction[i] : sample.actual.arm.user_joint_positions_rad[i];
}
