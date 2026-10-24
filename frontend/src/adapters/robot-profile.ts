import type { ArmSpec, Capabilities, KinematicsCheck, KinematicsReport, Quat, RuntimeIdentity, SceneManifest, Vec3 } from './types';
import type { ExecutionRecipe } from './platform-config';

// Wire projection of GET /api/v1/mobilecar/kinematics. The backend owns this
// contract; this file only validates and maps the fields the workbench consumes.
export interface KinematicsRead {
  schema_version: string; profile_id: string; digest: string; authority: string;
  profile: {
    schema_version: number; profile_id: string; robot_id: string;
    arm: { joint_names: string[]; user_direction: number[]; zero_model_rad: number[]; zero_status?: string; calibration_session?: string };
    gripper: { min_width_m: number; max_width_m: number; zero_width_m: number; zero_model_rad: number; width_per_drive_rad_m: number; jaw_origin_correction_m: number; source_gap_m: number; mimic: ArmSpec['mimic'] };
    tcp: { site: string; parent_body: string; position_m: Vec3; orientation_xyzw: Quat | null; orientation_status: string };
    camera_mount: { parent_body: string; status: string };
    sources?: { role: string; path: string; sha256: string }[];
    authority?: string; limitations?: string[];
  };
  sources?: { role: string; path: string; sha256: string }[];
  runtime_identity: RuntimeIdentity;
  consistency: { joint_order_consistent: boolean; user_limits_consistent: boolean; tcp_mount_consistent: boolean; camera_mount_consistent: boolean; gripper_limits_consistent: boolean; max_user_limit_error_rad: number };
  limitations: string[];
}
export interface KinematicsMapping { armSpec: ArmSpec | null; report: KinematicsReport }

const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
const vec3 = (value: unknown): value is Vec3 => Array.isArray(value) && value.length === 3 && value.every(finite);
function check(key: string, label: string, ok: boolean, detail: string): KinematicsCheck {
  return { key, label, status: ok ? 'passed' : 'failed', detail };
}
function baseReport(response: KinematicsRead): Omit<KinematicsReport, 'status' | 'reason' | 'checks'> {
  const tcp = response.profile?.tcp;
  return {
    source: 'live-metadata', profileId: response.profile_id ?? '', digest: response.digest ?? '',
    authority: response.authority ?? '', tcpOrientation: tcp?.orientation_xyzw === null ? 'not-specified' : 'declared',
    tcpOrientationStatus: tcp?.orientation_status ?? '', consistency: response.consistency ?? null,
    limitations: response.limitations ?? response.profile?.limitations ?? [],
  };
}
// Versioned live metadata replaces the former hard-coded reference mapping.
// It is still platform reference data, not a calibration or native attestation.
export function liveKinematicProfile(response: KinematicsRead, robotId: string, caps: Capabilities, scene: SceneManifest, recipe: ExecutionRecipe | null): KinematicsMapping {
  const base = baseReport(response);
  if (response.schema_version !== 'unirobot-mobilecar-kinematics-1' || !response.profile || !response.consistency) {
    const reason = `运动学元数据版本或结构不兼容（${response.schema_version ?? 'missing'}）`;
    return { armSpec: null, report: { ...base, status: 'unavailable', reason, checks: [check('schema', '接口版本', false, reason)] } };
  }
  const p = response.profile;
  const arm = p.arm;
  const names = arm?.joint_names ?? [];
  const zero = arm?.zero_model_rad ?? [];
  const direction = arm?.user_direction ?? [];
  const tcp = p.tcp;
  const camera = p.camera_mount;
  const c = response.consistency;
  const orderOk = names.join(',') === caps.arm_joint_names.join(',');
  const jointMetadata = names.length === 5 && zero.length === names.length && direction.length === names.length
    && zero.every(finite) && direction.every((value) => finite(value) && Math.abs(value) === 1);
  const unitsOk = vec3(tcp?.position_m) && finite(p.gripper?.min_width_m) && finite(p.gripper?.max_width_m)
    && finite(p.gripper?.zero_width_m) && finite(p.gripper?.zero_model_rad) && finite(p.gripper?.width_per_drive_rad_m);
  const tcpOk = tcp?.parent_body === caps.tcp_parent_body && tcp?.site === scene.tcp_site && vec3(tcp?.position_m);
  const cameraOk = camera?.parent_body === caps.camera_parent_body;
  const orientationOk = tcp != null && (tcp.orientation_xyzw === null
    ? tcp.orientation_status === 'not_specified_in_source'
    : Array.isArray(tcp.orientation_xyzw) && tcp.orientation_xyzw.length === 4 && tcp.orientation_xyzw.every(finite));
  const consistencyOk = c.joint_order_consistent === true && c.user_limits_consistent === true
    && c.tcp_mount_consistent === true && c.camera_mount_consistent === true && c.gripper_limits_consistent === true
    && finite(c.max_user_limit_error_rad) && c.max_user_limit_error_rad <= 1e-9;
  const expected = recipe?.expected as Record<string, unknown> | undefined;
  const modelOk = expected !== undefined && expected.model_id === scene.model_id
    && expected.model_sha256 === scene.model_sha256 && expected.scene_id === scene.scene_id;
  const recipeProfileOk = recipe !== null && recipe.kinematics.profile_id === response.profile_id
    && recipe.kinematics.digest === response.digest;
  const checks = [
    check('schema', '接口版本', true, `unirobot-mobilecar-kinematics-1 · profile schema ${p.schema_version}`),
    check('profile_id', 'profile 标识', p.profile_id === response.profile_id, `${response.profile_id} / ${p.profile_id}`),
    check('robot', '机器人模型', p.robot_id === robotId, `kinematics ${p.robot_id} · scene ${robotId}`),
    check('model', '模型 / 场景 pin', modelOk, recipe ? `recipe ${String(expected?.model_id)} / ${String(expected?.model_sha256)} / ${String(expected?.scene_id)} · native ${scene.model_id} / ${scene.model_sha256} / ${scene.scene_id}` : 'execution-recipe 未读取，无法核对模型 pin'),
    check('recipe_profile', '配方 profile 绑定', recipeProfileOk, recipe ? `recipe ${recipe.kinematics.profile_id} · ${recipe.kinematics.digest}` : 'execution-recipe 未读取'),
    check('joint_order', '关节顺序', orderOk, `${names.join(',')} / native ${caps.arm_joint_names.join(',')}`),
    check('joint_metadata', '零位 / 方向', jointMetadata, `zero_model_rad=${zero.join(',')} · direction=${direction.join(',')}`),
    check('units', '单位', unitsOk, '字段声明 m / rad；未提供独立单位版本字段'),
    check('tcp_mount', 'TCP 父节点 / site', tcpOk, `${tcp?.parent_body ?? '—'} / ${tcp?.site ?? '—'} · native ${caps.tcp_parent_body} / ${scene.tcp_site}`),
    check('camera_mount', '相机父节点', cameraOk, `${camera?.parent_body ?? '—'} / native ${caps.camera_parent_body}`),
    check('orientation', 'TCP 姿态声明', orientationOk, tcp?.orientation_xyzw === null ? `未声明 · ${tcp.orientation_status}` : '已声明姿态'),
    check('consistency', '实时一致性', consistencyOk, `5 项一致性 · max_user_limit_error_rad=${c.max_user_limit_error_rad}`),
  ];
  const failed = checks.filter((item) => item.status === 'failed');
  if (failed.length) {
    return { armSpec: null, report: { ...base, status: 'mismatch', checks, reason: failed.map((item) => `${item.label}: ${item.detail}`).join('；') } };
  }
  const limits: Record<string, [number, number]> = {};
  for (let i = 0; i < names.length; i++) {
    const [low, high] = caps.arm_user_limits_rad[i];
    const a = zero[i] + direction[i] * low;
    const b = zero[i] + direction[i] * high;
    limits[names[i]] = [Math.min(a, b), Math.max(a, b)];
  }
  return {
    armSpec: {
      profileId: response.profile_id, digest: response.digest, authority: response.authority,
      user_coordinates: { zero_model_rad: zero, direction, status: arm.zero_status },
      tcp: { body: tcp.parent_body, site: tcp.site, position: tcp.position_m, orientation_xyzw: tcp.orientation_xyzw, orientation_status: tcp.orientation_status },
      mimic: p.gripper.mimic ?? {}, limits,
      gripper: { min_width_m: p.gripper.min_width_m, max_width_m: p.gripper.max_width_m, zero_width_m: p.gripper.zero_width_m,
        zero_model_rad: p.gripper.zero_model_rad, width_per_drive_rad_m: p.gripper.width_per_drive_rad_m,
        jaw_origin_correction_m: p.gripper.jaw_origin_correction_m, source_gap_m: p.gripper.source_gap_m },
      camera_mount: { parent_body: camera.parent_body, status: camera.status },
      consistency: c, limitations: response.limitations ?? [],
    },
    report: { ...base, status: 'verified', checks, reason: '' },
  };
}
// Frozen samples keep their own captured arm-spec. They are never a fallback
// for live metadata and are labelled as an unverified historical reference.
export function frozenKinematicProfile(file: ArmSpec): KinematicsMapping {
  const limitations = ['冻结样本自带的参考 profile，不是 live 运动学元数据', '不能用于 live 会话资格或部署内容核验'];
  return {
    armSpec: {
      ...file, profileId: 'landerpi-frozen-reference-v1', digest: 'frozen-sample-arm-spec',
      authority: 'frozen_sample_reference_not_live',
      tcp: { ...file.tcp, orientation_xyzw: file.tcp.orientation_xyzw ?? null, orientation_status: file.tcp.orientation_status ?? 'not_specified_in_source' },
      limitations,
    },
    report: {
      status: 'frozen-reference', source: 'frozen-sample', profileId: 'landerpi-frozen-reference-v1',
      digest: 'frozen-sample-arm-spec', authority: 'frozen_sample_reference_not_live', tcpOrientation: 'not-specified',
      tcpOrientationStatus: 'not_specified_in_source', consistency: null,
      checks: [{ key: 'source', label: '独立参考 profile', status: 'not_applicable', detail: '冻结样本自带 arm-spec；不请求 live kinematics，也不作为 live 回退' }],
      reason: '', limitations,
    },
  };
}
export function unavailableKinematics(reason: string): KinematicsReport {
  return {
    status: 'unavailable', source: 'none', profileId: '', digest: '', authority: '',
    tcpOrientation: 'not-specified', tcpOrientationStatus: '', consistency: null,
    checks: [check('metadata', '运动学元数据', false, reason)], reason, limitations: [],
  };
}
