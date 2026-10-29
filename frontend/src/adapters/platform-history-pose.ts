/**
 * history-pose-1 client: the robot state of one selected historical frame, the per-part readiness
 * that says whether a recorded value may drive the model at all, the reader's own forward-kinematics
 * cross-check for that same frame, and the mesh bytes of the frozen geometry bundle this Episode's
 * run manifest was compared against.
 *
 * Field names, status words and codes here were read off the live `unirobot-mobilecar-history-pose-1`
 * payloads of the two history candidates: 18969 (2026-10-26, nine mapping rows, nothing verified) and
 * 18970 (2026-10-28, M1.5e: `part_readiness` with nine capabilities and their `frontend_rule`,
 * `capability_summary` with `kinematic_agreement`/`abs_tcp_error_m`, `tcp_kinematic_cross_check` with
 * two tested root conventions, `version_binding.writer_identified=false`, and `verified` mapping rows
 * for arm joints, base position/orientation and the TCP site). Nothing is invented: a capability the
 * reader blocks or leaves conditional stays undriven, and a value it does not return is never
 * defaulted to 0. Model bytes come only from the history asset route.
 */
import { json, query, EpisodeContractError, type EpisodeSource } from './platform-episodes';
import { parseError } from './platform-config';

export const HISTORY_POSE_SCHEMA = 'unirobot-mobilecar-history-pose-1';

export interface HistoryMappingEvidence { [key: string]: unknown }
export interface HistoryModelToUserFormula {
  q_user?: string; q_model?: string; zero_model_rad?: number[]; user_direction?: number[]; authority?: string; used_for?: string;
}
export interface HistoryMappingRowDto {
  target: string; recorded_field: string | null; recorded_unit: string | null; recorded_length: number | null;
  target_field: string | null; status: string; evidence: HistoryMappingEvidence;
  verified_basis?: string[] | null; draw_source?: string; requires_user_angle_conversion?: boolean;
  model_to_user_formula?: HistoryModelToUserFormula | null; no_default_applied?: boolean; gap?: string | null;
}
export interface HistoryPartReadinessDto {
  capability: string; status: string; requires?: string[]; pose_input_required?: boolean;
  inputs_available?: Record<string, unknown> | null; frontend_rule?: string; evidence?: Record<string, unknown>; gaps?: string[];
}
export interface HistoryCapabilitySummaryDto {
  usable_now?: string[]; usable_only_with_the_named_caveat?: string[]; blocked?: string[];
  fixed_model_assembly_available?: boolean; whole_robot_pose_rebuildable?: boolean;
  escalation_forbidden?: string; defaults_forbidden?: string; kinematic_agreement?: string; abs_tcp_error_m?: number;
}
export interface HistoryFkHypothesisDto {
  hypothesis: string; status?: string; computed_tcp_position_m?: number[] | null; abs_error_m?: number | null;
  verdict?: string; tolerance_m?: number | null; chain_links?: string[]; note?: string | null; reason?: string | null;
}
export interface HistoryFkCheckDto {
  status?: string; method?: string; recorded_tcp_position_m?: number[] | null; computed_tcp_position_m?: number[] | null;
  abs_error_m?: number | null; difference_m?: number[] | null; verdict?: string; consistency_tolerance_m?: number | null;
  tolerance_authority?: string; supported_hypotheses?: string[]; chain_links?: string[]; hypotheses?: HistoryFkHypothesisDto[];
}
export interface HistoryVersionBindingDto {
  reference_source?: string; chain_verified_in_reference_source?: boolean; writer_identified?: boolean;
  record_carries_no?: string[]; conclusion?: string; later_release_note?: string; [key: string]: unknown;
}
export interface HistoryPoseReadinessDto {
  model_identity?: string; mapping_valid_for_this_episode?: boolean;
  mapped_targets_partially_or_fully_verified?: string;
  robot_state_can_be_rebuilt_without_assumptions?: boolean; blocking_fields?: string[];
  parts_ready?: string[]; parts_conditional?: string[]; parts_blocked?: string[];
  kinematic_agreement?: string; next_round_owner?: string; note?: string;
}
export interface HistoryAssetDto { asset_id: string; sha256: string; media_type: string; coordinate_space?: string; units?: string; bytes?: number | null }
export interface HistoryLinkJointDto {
  name?: string; parent_name?: string | null; joint_name?: string | null; joint_type?: string | null;
  joint_axis?: number[] | null; local_position_m?: number[] | null; local_orientation_xyzw?: number[] | null; geom_types?: string[];
}
export interface HistoryModelResourceDto {
  status?: string; comparison?: Record<string, { recorded?: string | null; bundle?: string | null; equal?: boolean }>;
  bundle_sha256?: string; content_identity_sha256?: string; compiler?: { name?: string; version?: string };
  verification_scope?: string; model_inputs_sha256?: string; compiled_scene_sha256?: string;
  compile_runtime_identity?: { run_id?: string; backend_generation?: number; episode_id?: string } | null;
  compile_runtime_identity_is_this_episode?: boolean | null;
  scene_source?: string; tcp_site?: string; camera_ids?: string[]; link_count?: number;
  arm_hinge_joints?: string[]; gripper_slide_joints?: string[]; gripper_other_joints_in_bundle?: string[]; wheel_hinge_joints?: string[];
  root_joint?: HistoryLinkJointDto | null; camera_link_chain?: HistoryLinkJointDto[];
  end_effector_link?: HistoryLinkJointDto | null; tcp_parent_body_view?: HistoryLinkJointDto | null;
  world_links?: { name: string; geom_types?: string[] }[]; link_frames?: string;
  assets?: HistoryAssetDto[]; asset_integrity?: string; live_native_scene_proxied?: boolean; served_via?: string;
}
export interface HistoryStateDto {
  linkage_status: string; source?: { stream_id?: string; relative_path?: string; line_index?: number; event_seq?: number | null; event_type?: string | null } | null;
  candidate_records?: number | null; single_state_selected?: boolean | null;
  /** Null whenever no single record was selected; the view never substitutes the first candidate. */
  recorded_payload?: Record<string, unknown> | null;
  multiple_candidates_note?: string | null; note?: string | null;
  candidates?: { line_index?: number; record_position?: string; payload?: Record<string, unknown> | null }[] | null;
  declared_reference?: { feedback_sample_id?: string | null; row_status?: string } | null;
  units?: Record<string, string>;
}
export interface HistoryPoseDto {
  schema_version: string; read_only: boolean; source: EpisodeSource; retrieved_at: string;
  identity: { run_id: string; episode_id: string; recorded_run_manifest?: Record<string, unknown>; identity_source?: string };
  frame: { sample_id: string; linkage_schema?: string; linkage_status?: string;
    anchor?: { relative_path?: string; line_index?: number; persist_sequence?: number | null; profile?: Record<string, unknown> } | null;
    media?: Record<string, unknown> };
  state: HistoryStateDto;
  time: { quantities?: unknown[]; state_time_quantity_keys?: string[]; sim_time_quantity_keys?: string[];
    recorder_declared?: Record<string, unknown>; semantics_rule?: string; same_clock_verified?: boolean; clock_sameness?: Record<string, unknown> };
  mapping: HistoryMappingRowDto[]; status_meaning?: Record<string, string>;
  part_readiness?: HistoryPartReadinessDto[]; part_status_meaning?: Record<string, string>;
  capability_summary?: HistoryCapabilitySummaryDto;
  pose_readiness?: HistoryPoseReadinessDto; model_resource?: HistoryModelResourceDto;
  model_vs_user_angles?: { render_source?: string; conversion_is_required_for_drawing?: boolean;
    user_angle_formula?: HistoryModelToUserFormula; zero_pose_authority?: Record<string, unknown> };
  tcp_kinematic_cross_check?: HistoryFkCheckDto; version_binding?: HistoryVersionBindingDto;
  arm_mapping_chain?: Record<string, unknown>;
  rendering?: { verified?: boolean; frontend_assembly_done?: boolean; note?: string };
  not_proven?: { target: string; status: string; gap: string }[]; capability_limits?: string[];
}

/** `sample_id` is always sent: the reader answers the first anchor frame when it is omitted, and the
 *  view must never present a frame it did not select. */
export async function readRobotState(input: { episodeId: string; runId: string | null; sampleId: string }, signal: AbortSignal): Promise<HistoryPoseDto> {
  if (!input.sampleId) throw new Error('没有所选帧的 sample_id：不请求 robot-state，避免把 reader 的默认第一条当成所选帧。');
  const params: Record<string, string | undefined> = { run_id: input.runId ?? undefined, sample_id: input.sampleId };
  return json<HistoryPoseDto>(`/api/v1/episodes/${encodeURIComponent(input.episodeId)}/robot-state${query(params)}`, signal, HISTORY_POSE_SCHEMA);
}

/** The response must still be the frame that was asked for; identity is checked, not assumed. */
export function assertHistoryFrameIdentity(dto: HistoryPoseDto, expected: { episodeId: string; runId: string | null; sampleId: string }): void {
  if (dto.frame?.sample_id !== expected.sampleId) throw new EpisodeContractError('robot-state 返回的帧身份与所选帧不符', String(dto.frame?.sample_id));
  if (dto.identity?.episode_id !== expected.episodeId) throw new EpisodeContractError('robot-state 返回的 episode_id 与所选 Episode 不符', String(dto.identity?.episode_id));
  if ((dto.identity?.run_id ?? null) !== (expected.runId ?? null)) throw new EpisodeContractError('robot-state 返回的 run_id 与所选 run 不符', String(dto.identity?.run_id));
}

export interface HistoryAssetBytes { bytes: ArrayBuffer; mediaType: string; digest: string; etag: string; cacheControl: string }
/** Model bytes are read only from the history asset endpoint, with the bundle digest supplied so the
 *  server verifies before it returns anything (`409 history_asset_revision_changed` otherwise). */
export async function readHistoryModelAsset(input: { episodeId: string; runId: string | null; assetId: string; sha256: string | null }, signal: AbortSignal): Promise<HistoryAssetBytes> {
  const params: Record<string, string> = {};
  if (input.runId) params.run_id = input.runId;
  if (input.sha256) params.sha256 = input.sha256;
  const path = `/api/v1/episodes/${encodeURIComponent(input.episodeId)}/model/assets/${encodeURIComponent(input.assetId)}${query(params)}`;
  const response = await fetch(path, { method: 'GET', signal, cache: 'no-store' });
  const body = await response.arrayBuffer();
  if (!response.ok) {
    let detail: unknown = null;
    try { detail = JSON.parse(new TextDecoder().decode(body)); } catch { detail = null; }
    throw parseError(response.status, response.statusText, detail);
  }
  const etag = response.headers.get('etag') ?? '';
  return { bytes: body, mediaType: response.headers.get('content-type') ?? '', digest: etagDigest(etag), etag, cacheControl: response.headers.get('cache-control') ?? '' };
}
/** The model asset route carries the recomputed digest in the ETag (`"sha256:<hex>"`). */
export function etagDigest(etag: string): string {
  const match = /^"sha256:([0-9a-f]{64})"$/.exec(etag);
  return match ? match[1] : '';
}

// ---- mapping / part projections --------------------------------------------------------------------

export interface MappingRow { target: string; recordedField: string; recordedUnit: string; recordedLength: string; targetField: string; status: string; statusMeaning: string; basis: string; drawSource: string; conversion: string; evidence: string; formula: string; noDefault: string; gap: string }
/** Mapping rows are shown as the reader wrote them: per-target status, its stated basis, evidence and
 *  gap — never collapsed into one "pose is fine" verdict. */
export function mappingRowsOf(dto: HistoryPoseDto | null): MappingRow[] {
  return (dto?.mapping ?? []).map((row) => ({
    target: row.target,
    recordedField: row.recorded_field ?? '该目标没有记录字段（recorded_field=null）',
    recordedUnit: row.recorded_unit ?? '未声明单位',
    recordedLength: row.recorded_length === null || row.recorded_length === undefined ? 'null' : String(row.recorded_length),
    targetField: row.target_field ?? 'reader 未给出模型侧目标',
    status: row.status,
    statusMeaning: dto?.status_meaning?.[row.status] ?? 'reader 未定义该状态词的含义',
    basis: (row.verified_basis ?? []).join('；') || 'reader 未给出 verified_basis',
    drawSource: row.draw_source ?? 'reader 未声明绘制来源',
    conversion: row.requires_user_angle_conversion === undefined ? 'reader 未声明是否需要用户角换算' : `requires_user_angle_conversion=${String(row.requires_user_angle_conversion)}`,
    evidence: JSON.stringify(row.evidence ?? {}),
    formula: row.model_to_user_formula ? JSON.stringify(row.model_to_user_formula) : 'reader 未声明模型↔用户换算',
    noDefault: String(row.no_default_applied),
    gap: row.gap ?? 'reader 未列出缺口',
  }));
}

export interface PartRow { capability: string; status: string; meaning: string; rule: string; requires: string; poseInput: string; inputs: string; gaps: string; evidence: string }
/** `part_readiness` is the per-capability answer: status, the reader's own meaning of that word, the
 *  `frontend_rule` the interface has to obey, and the inputs it checked for this frame. */
export function partReadinessOf(dto: HistoryPoseDto | null): PartRow[] {
  return (dto?.part_readiness ?? []).map((part) => ({
    capability: part.capability, status: part.status,
    meaning: dto?.part_status_meaning?.[part.status] ?? 'reader 未定义该就绪词的含义',
    rule: part.frontend_rule ?? 'reader 未声明 frontend_rule',
    requires: (part.requires ?? []).join('；') || 'reader 未列出前置条件',
    poseInput: part.pose_input_required === undefined ? 'reader 未声明' : String(part.pose_input_required),
    inputs: part.inputs_available ? JSON.stringify(part.inputs_available) : 'reader 未列出本帧输入',
    gaps: (part.gaps ?? []).join('；') || '无',
    evidence: part.evidence ? JSON.stringify(part.evidence) : 'reader 未附证据',
  }));
}
export const partOf = (dto: HistoryPoseDto | null, capability: string): HistoryPartReadinessDto | null =>
  (dto?.part_readiness ?? []).find((part) => part.capability === capability) ?? null;
export const mappingOf = (dto: HistoryPoseDto | null, target: string): HistoryMappingRowDto | null =>
  (dto?.mapping ?? []).find((row) => row.target === target) ?? null;

export function capabilitySummaryText(dto: HistoryPoseDto | null): string {
  const c = dto?.capability_summary;
  if (!c) return 'reader 未返回 capability_summary。';
  return `usable_now=${(c.usable_now ?? []).join('/') || '空'} · usable_only_with_the_named_caveat=${(c.usable_only_with_the_named_caveat ?? []).join('/') || '空'} · blocked=${(c.blocked ?? []).join('/') || '空'} · fixed_model_assembly_available=${text(c.fixed_model_assembly_available)} · whole_robot_pose_rebuildable=${text(c.whole_robot_pose_rebuildable)} · kinematic_agreement=${text(c.kinematic_agreement)} · abs_tcp_error_m=${text(c.abs_tcp_error_m)} · 不得升级：${text(c.escalation_forbidden)} · 不得补默认值：${text(c.defaults_forbidden)}`;
}

/** The reader's own same-frame FK check, kept as numbers: which root convention it tested, what it
 *  computed, how far that was from the recorded TCP, and who owns the tolerance. */
export interface FkCheck { status: string; method: string; verdict: string; absError: string; tolerance: string; toleranceAuthority: string; recorded: string; computed: string; supported: string; chain: string; hypotheses: { hypothesis: string; status: string; computed: string; absError: string; verdict: string }[] }
export function fkCrossCheckOf(dto: HistoryPoseDto | null): FkCheck | null {
  const fk = dto?.tcp_kinematic_cross_check;
  if (!fk) return null;
  return {
    status: text(fk.status), method: fk.method ?? 'reader 未声明方法', verdict: text(fk.verdict),
    absError: text(fk.abs_error_m), tolerance: text(fk.consistency_tolerance_m),
    toleranceAuthority: fk.tolerance_authority ?? 'reader 未声明容差归属',
    recorded: JSON.stringify(fk.recorded_tcp_position_m ?? null), computed: JSON.stringify(fk.computed_tcp_position_m ?? null),
    supported: (fk.supported_hypotheses ?? []).join('/') || 'reader 未列出被支持的约定',
    chain: (fk.chain_links ?? []).join('→') || 'reader 未列出链',
    hypotheses: (fk.hypotheses ?? []).map((row) => ({
      hypothesis: row.hypothesis, status: text(row.status), computed: JSON.stringify(row.computed_tcp_position_m ?? null),
      absError: text(row.abs_error_m), verdict: text(row.verdict),
    })),
  };
}
export function versionBindingText(dto: HistoryPoseDto | null): string {
  const v = dto?.version_binding;
  if (!v) return 'reader 未返回 version_binding。';
  return `writer_identified=${text(v.writer_identified)} · chain_verified_in_reference_source=${text(v.chain_verified_in_reference_source)} · 参考来源=${text(v.reference_source)} · 记录不含=${(v.record_carries_no ?? []).join('/')} · 结论=${text(v.conclusion)}`;
}
export function modelVsUserText(dto: HistoryPoseDto | null): string {
  const m = dto?.model_vs_user_angles;
  if (!m) return 'reader 未返回 model_vs_user_angles。';
  return `绘制来源=${text(m.render_source)} · conversion_is_required_for_drawing=${text(m.conversion_is_required_for_drawing)} · 用户角用途=${text(m.user_angle_formula?.used_for)} · 零位权威=${JSON.stringify(m.zero_pose_authority ?? 'reader 未声明')}`;
}

/**
 * The interface's driving rule, per capability rather than per joint count. A part may move the model
 * only when the reader's own `part_readiness` calls it usable (`ready` / `ready_with_caveats`), the
 * matching `mapping` row reads `verified`, and this frame actually carries the inputs — a `conditional`
 * part is never switched on by default, and a `blocked` part is never drawn from the record. Values are
 * the recorded ones: model radians for the arm hinges with no user-zero step, the base body's world
 * pose for the chassis (the reader's cross-check excludes re-adding the bundle root offset), and a
 * position-only marker for the TCP because no orientation is recorded. Zero is a legal value; absence
 * is never filled.
 */
export interface PartDriveDecision { capability: string; status: string; allowed: boolean; reason: string; rule: string }
export interface PoseDrive {
  joints: Record<string, number>; base: { position: number[]; quaternion: number[] } | null; tcp: { position: number[] } | null;
  parts: PartDriveDecision[]; withheld: string[]; attributable: boolean; summary: string;
}
const USABLE = new Set(['ready', 'ready_with_caveats']);
const numbersOf = (value: unknown): number[] | null => {
  if (Array.isArray(value)) { const list = value as unknown[]; return list.every((item) => typeof item === 'number' && Number.isFinite(item)) ? list as number[] : null; }
  if (typeof value === 'number' && Number.isFinite(value)) return [value];
  return null;
};
export function poseDriveOf(dto: HistoryPoseDto | null): PoseDrive {
  const parts: PartDriveDecision[] = [];
  const withheld: string[] = [];
  const joints: Record<string, number> = {};
  let base: PoseDrive['base'] = null;
  let tcp: PoseDrive['tcp'] = null;
  const payload = dto?.state?.recorded_payload ?? null;
  const attributable = Boolean(dto) && dto?.state?.single_state_selected === true && Boolean(payload);
  const decide = (capability: string, allowed: boolean, reason: string) => {
    const part = partOf(dto, capability);
    const row: PartDriveDecision = { capability, status: part?.status ?? 'reader 未返回该能力', allowed, reason, rule: part?.frontend_rule ?? 'reader 未声明 frontend_rule' };
    parts.push(row);
    if (!allowed) withheld.push(`${capability}（${row.status}）：${reason}`);
    return row;
  };
  if (!dto) {
    return { joints, base, tcp, parts, withheld: ['未读取 robot-state：不驱动任何部件。'], attributable: false, summary: '未读取 robot-state：不驱动任何部件，画面保持固定参考姿态。' };
  }
  // The assembly itself is a capability with its own answer: it needs identity and bytes, not a pose.
  const assembly = partOf(dto, 'fixed_model_reference_assembly');
  decide('fixed_model_reference_assembly', assembly === null || USABLE.has(assembly.status),
    assembly ? `status=${assembly.status}：${assembly.frontend_rule ?? 'reader 未声明规则'}` : 'reader 未返回该能力：只按身份与摘要门控装配，不宣称该项已就绪。');
  if (!attributable) {
    decide('arm_local_pose', false, `本帧没有单一选中的状态记录（single_state_selected=${text(dto.state?.single_state_selected)}、recorded_payload=${payload ? '有' : 'null'}）：不挑候选、不补 0、不沿用上一帧。`);
    decide('base_pose_placement', false, '本帧没有单一选中的状态记录：底盘保持编译初始布局。');
    decide('tcp_position_marker', false, '本帧没有单一选中的状态记录：不画 TCP 点。');
    // The reader answered every other capability for this frame too; each of them keeps its own reason
    // (status, frontend_rule, gaps) instead of collapsing into one generic "nothing to draw" line.
    (dto.part_readiness ?? []).filter((part) => !parts.some((row) => row.capability === part.capability)).forEach((part) => {
      decide(part.capability, false, `本帧没有单一选中的状态记录，且该能力自身 status=${part.status}：按 frontend_rule${part.gaps?.length ? `（缺口：${part.gaps.join('；')}）` : ''}不驱动。`);
    });
    return { joints, base, tcp, parts, withheld, attributable, summary: `本帧状态不可归属（single_state_selected=${text(dto.state?.single_state_selected)}）：画面保持固定参考姿态，未驱动 ${withheld.length} 项。` };
  }
  // arm_local_pose — five model radians onto the five bundle hinges, no user-zero conversion.
  const armPart = partOf(dto, 'arm_local_pose');
  const armMap = mappingOf(dto, 'arm_joint_positions');
  const names = dto.model_resource?.arm_hinge_joints ?? [];
  const angles = numbersOf((payload as Record<string, unknown> | null)?.arm_model_qpos_rad);
  const armInputs = (armPart?.inputs_available ?? {}) as Record<string, unknown>;
  if (!armPart) decide('arm_local_pose', false, 'reader 未返回该能力的就绪状态：不驱动。');
  else if (!USABLE.has(armPart.status)) decide('arm_local_pose', false, `status=${armPart.status}：按 frontend_rule 不驱动（${armPart.gaps?.join('；') || 'reader 未列缺口'}）。`);
  else if (armMap?.status !== 'verified') decide('arm_local_pose', false, `映射 arm_joint_positions 的 status=${text(armMap?.status)}，不是 verified：不驱动。`);
  else if (armMap.requires_user_angle_conversion !== false || armInputs.draw_in_model_radians !== true) decide('arm_local_pose', false, 'reader 未同时声明 requires_user_angle_conversion=false 与 draw_in_model_radians=true：不猜测角度空间，不驱动。');
  else if (!angles || !names.length || angles.length !== names.length) decide('arm_local_pose', false, `记录值 ${angles ? angles.length : '无'} 个与 bundle 臂铰链 ${names.length} 个数量不符：不猜对应关系，不驱动。`);
  else {
    decide('arm_local_pose', true, `status=${armPart.status} + 映射 verified + 模型弧度直接施加：按记录原值驱动 ${names.join('/')}（0 是合法数值；没有跨帧运动覆盖证据就不宣称某轴已验证）。`);
    names.forEach((name, index) => { joints[name] = angles[index]; });
  }
  // base_pose_placement — the recorded pose is the base body's world pose, replacing the compiled offset.
  const basePart = partOf(dto, 'base_pose_placement');
  const basePos = numbersOf((payload as Record<string, unknown> | null)?.base_position_world_sim_m);
  const baseQuat = numbersOf((payload as Record<string, unknown> | null)?.base_quaternion_xyzw);
  const posMap = mappingOf(dto, 'base_position');
  const quatMap = mappingOf(dto, 'base_orientation');
  const convention = (dto.tcp_kinematic_cross_check?.supported_hypotheses ?? []).includes('recorded_pose_is_base_body_world_pose');
  if (!basePart) decide('base_pose_placement', false, 'reader 未返回该能力的就绪状态：底盘保持编译初始布局。');
  else if (!USABLE.has(basePart.status)) decide('base_pose_placement', false, `status=${basePart.status}：不放置底盘（${basePart.gaps?.join('；') || 'reader 未列缺口'}）。`);
  else if (posMap?.status !== 'verified' || quatMap?.status !== 'verified') decide('base_pose_placement', false, `映射 base_position=${text(posMap?.status)} / base_orientation=${text(quatMap?.status)}：任一未 verified 都不放置。`);
  else if (!dto.tcp_kinematic_cross_check) decide('base_pose_placement', false, 'reader 未返回 tcp_kinematic_cross_check：该能力的 frontend_rule 要求“核对不一致就不放置”，没有核对结果同样不放置。');
  else if (dto.tcp_kinematic_cross_check.verdict !== 'consistent' || !convention) decide('base_pose_placement', false, `同帧运动学核对 verdict=${text(dto.tcp_kinematic_cross_check.verdict)}、supported_hypotheses=${(dto.tcp_kinematic_cross_check.supported_hypotheses ?? []).join('/') || '空'}：核对不支持 recorded_pose_is_base_body_world_pose 时不猜约定、不放置底盘。`);
  else if (!basePos || basePos.length !== 3 || !baseQuat || baseQuat.length !== 4) decide('base_pose_placement', false, `记录位姿长度不符（位置 ${basePos?.length ?? '无'}/3、四元数 ${baseQuat?.length ?? '无'}/4）：不补值。`);
  else {
    decide('base_pose_placement', true, `status=${basePart.status} + 位置/朝向 verified + 同帧核对 verdict=${text(dto.tcp_kinematic_cross_check?.verdict)} 且支持 recorded_pose_is_base_body_world_pose：直接以记录的世界位姿替换 base_link 的编译初始位姿，不再叠加初始根偏移（root joint local_position_m=${JSON.stringify(dto.model_resource?.root_joint?.local_position_m ?? null)}）。限制：${basePart.gaps?.join('；') || 'reader 未列缺口'}；${versionBindingText(dto)}`);
    base = { position: basePos, quaternion: baseQuat };
  }
  // tcp_position_marker — a point only; orientation is blocked by the reader.
  const tcpPart = partOf(dto, 'tcp_position_marker');
  const tcpPos = numbersOf((payload as Record<string, unknown> | null)?.tcp_position_world_m);
  const tcpMap = mappingOf(dto, 'tcp_site_position');
  if (!tcpPart) decide('tcp_position_marker', false, 'reader 未返回该能力的就绪状态：不画点。');
  else if (!USABLE.has(tcpPart.status)) decide('tcp_position_marker', false, `status=${tcpPart.status}：不画 TCP 点。`);
  else if (tcpMap?.status !== 'verified') decide('tcp_position_marker', false, `映射 tcp_site_position 的 status=${text(tcpMap?.status)}：不画点。`);
  else if (!tcpPos || tcpPos.length !== 3) decide('tcp_position_marker', false, `记录 TCP 长度 ${tcpPos?.length ?? '无'}/3 不符：不补值。`);
  else {
    decide('tcp_position_marker', true, `status=${tcpPart.status} + 映射 verified：只画位置点（world_sim 记录原值），不合成朝向。`);
    tcp = { position: tcpPos };
  }
  // The remaining capabilities keep their own limits; one gap never blocks the others.
  decide('gripper_visual_appearance', false, `status=${partOf(dto, 'gripper_visual_appearance')?.status ?? 'reader 未返回'} 属于 conditional：只有消费者接受并显示平台声明的非常量背书才允许摆位，界面不默认开启。`);
  decide('tcp_orientation_frame', false, `status=${partOf(dto, 'tcp_orientation_frame')?.status ?? 'reader 未返回'}：${mappingOf(dto, 'tcp_site_orientation')?.gap ?? 'reader 未列缺口'}`);
  decide('camera_view_from_record', false, `status=${partOf(dto, 'camera_view_from_record')?.status ?? 'reader 未返回'}：${mappingOf(dto, 'camera_extrinsics')?.gap ?? 'reader 未列缺口'}`);
  decide('dynamic_scene_objects_from_record', false, `status=${partOf(dto, 'dynamic_scene_objects_from_record')?.status ?? 'reader 未返回'}：世界物体保持 bundle 编译初始布局并标注非历史状态。`);
  decide('wheel_pose_from_record', false, `status=${partOf(dto, 'wheel_pose_from_record')?.status ?? 'reader 未返回'}：本切片摆位不需要轮角。`);
  const driven = Object.keys(joints).length + (base ? 1 : 0) + (tcp ? 1 : 0);
  return {
    joints, base, tcp, parts, withheld, attributable,
    summary: `已驱动 ${Object.keys(joints).length} 个臂关节模型弧度、底盘位姿=${base ? '已按记录世界位姿放置' : '未放置（保持编译初始布局）'}、TCP 点=${tcp ? '已画位置点' : '未画'}；未驱动 ${withheld.length} 项；whole_robot_pose_rebuildable=${text(dto.capability_summary?.whole_robot_pose_rebuildable)}（驱动 ${driven} 项不升级为整车重建）。`,
  };
}
/** The values the surface really applied, one row per moved item, named by the frame they belong to.
 *  `model` is what moved the joint; `display` is the reader's user angle computed here only to make it
 *  visible that drawing never passed through it. A withheld part never gets a row, and nothing is filled
 *  with zero. */
export interface DrivenValueRow { kind: 'arm' | 'base' | 'tcp'; name: string; model: string; display: string; source: string }
export function drivenValuesOf(dto: HistoryPoseDto, shown: { joints: Record<string, number>; baseApplied: boolean; tcpApplied: boolean }): DrivenValueRow[] {
  const payload = (dto.state?.recorded_payload ?? {}) as Record<string, unknown>;
  const order = dto.model_resource?.arm_hinge_joints ?? [];
  const radians = numbersOf(payload.arm_model_qpos_rad) ?? [];
  const formula = dto.model_vs_user_angles?.user_angle_formula ?? null;
  const renderSource = text(dto.model_vs_user_angles?.render_source);
  const rows: DrivenValueRow[] = [];
  order.forEach((name, index) => {
    const value = shown.joints[name];
    if (value === undefined) return;
    const zero = formula?.zero_model_rad?.[index];
    const direction = formula?.user_direction?.[index];
    const convertible = typeof zero === 'number' && Number.isFinite(zero) && typeof direction === 'number' && Number.isFinite(direction) && direction !== 0;
    rows.push({
      kind: 'arm', name, model: String(value),
      display: convertible ? `${String((value - (zero as number)) / (direction as number))}（本界面按 reader 公式换算，仅展示，未参与绘制）`
        : 'reader 未给该轴的 zero_model_rad / user_direction：不换算、不猜测',
      source: `arm_model_qpos_rad[${index}] · 绘制来源=${renderSource}`,
    });
  });
  if (shown.baseApplied) {
    rows.push({ kind: 'base', name: 'base_link',
      model: `${JSON.stringify(numbersOf(payload.base_position_world_sim_m) ?? null)} / ${JSON.stringify(numbersOf(payload.base_quaternion_xyzw) ?? null)}`,
      display: `替换编译初始位姿；root joint local_position_m=${JSON.stringify(dto.model_resource?.root_joint?.local_position_m ?? null)} 未再叠加`,
      source: 'base_position_world_sim_m + base_quaternion_xyzw（同帧运动学核对背书）' });
  }
  if (shown.tcpApplied) {
    rows.push({ kind: 'tcp', name: text(dto.model_resource?.tcp_site), model: JSON.stringify(numbersOf(payload.tcp_position_world_m) ?? null),
      display: `只画位置点，不合成朝向（tcp_orientation_frame=${text(partOf(dto, 'tcp_orientation_frame')?.status)}）`,
      source: 'tcp_position_world_m · 帧归属见显示帧' });
  }
  return rows;
}

/** Cross-frame motion coverage, judged only over the frames this surface actually visited and applied.
 *  One visited value is not motion: an axis seen once gets no "verified by movement" claim, and an item
 *  that a later visit does not drive keeps what it saw instead of being filled with a zero. */
export interface VisitedDrivenValues { sample: string; values: Record<string, string> }
export interface MotionCoverageRow { name: string; distinct: number; seenCount: number; samples: string[]; verdict: string }
export function mergeVisitedValues(previous: VisitedDrivenValues[], entry: VisitedDrivenValues): VisitedDrivenValues[] {
  const rest = previous.filter((row) => row.sample !== entry.sample);
  return entry.sample ? [...rest, entry] : previous;
}
export function motionCoverageOf(visited: VisitedDrivenValues[]): MotionCoverageRow[] {
  const order: string[] = [];
  const buckets = new Map<string, Map<string, string>>();
  const seenCount = new Map<string, number>();
  visited.forEach((entry) => Object.entries(entry.values).forEach(([name, value]) => {
    if (!buckets.has(name)) { buckets.set(name, new Map()); seenCount.set(name, 0); order.push(name); }
    buckets.get(name)!.set(value, entry.sample);
    seenCount.set(name, (seenCount.get(name) ?? 0) + 1);
  }));
  return order.map((name) => {
    const bucket = [...buckets.get(name)!.entries()];
    const visits = seenCount.get(name) ?? 0;
    return {
      name, distinct: bucket.length, seenCount: visits, samples: bucket.map((entry) => entry[1]),
      verdict: bucket.length > 1
        ? `驱动过它的 ${visits} 个已访问帧里出现 ${bucket.length} 个不同记录值（${bucket.map(([value, sample]) => `${sample}=${value}`).join('，')}）：有跨帧运动证据，且只对已访问帧成立。`
        : `只在 ${visits} 个已访问帧里见过 1 个记录值（${bucket[0][1]}=${bucket[0][0]}）：没有跨帧运动覆盖证据，不宣称该轴已被验证。`,
    };
  });
}
/** `single_state_selected=false` / `recorded_payload=null` are reported as answers, not patched. */
export function poseStateText(dto: HistoryPoseDto | null): string {
  if (!dto) return '未读取 robot-state。';
  const state = dto.state;
  return `linkage_status=${state.linkage_status} · candidate_records=${text(state.candidate_records)} · single_state_selected=${text(state.single_state_selected)} · recorded_payload=${state.recorded_payload ? `有 ${Object.keys(state.recorded_payload).length} 个字段` : 'null（不按第一条候选绘制，不补 0，不沿用上一帧）'} · 记录位置=${state.source ? `${state.source.relative_path}#${state.source.line_index}` : '无'} · declared_reference=${text(state.declared_reference?.row_status)}${state.multiple_candidates_note ? ` · 原文：${state.multiple_candidates_note}` : ''}`;
}
export function poseReadinessText(dto: HistoryPoseDto | null): string {
  const r = dto?.pose_readiness;
  if (!r) return 'reader 未返回 pose_readiness。';
  return `model_identity=${text(r.model_identity)} · mapping_valid_for_this_episode=${text(r.mapping_valid_for_this_episode)} · 已证/部分已证目标=${text(r.mapped_targets_partially_or_fully_verified)} · robot_state_can_be_rebuilt_without_assumptions=${text(r.robot_state_can_be_rebuilt_without_assumptions)} · parts_ready=${(r.parts_ready ?? []).join('/') || '空'} · parts_conditional=${(r.parts_conditional ?? []).join('/') || '空'} · parts_blocked=${(r.parts_blocked ?? []).join('/') || '空'} · blocking_fields=${(r.blocking_fields ?? []).join('/') || '空'} · kinematic_agreement=${text(r.kinematic_agreement)} · 下一步归属=${text(r.next_round_owner)} · ${text(r.note)}`;
}
export function renderingText(dto: HistoryPoseDto | null): string {
  const r = dto?.rendering;
  if (!r) return 'reader 未返回 rendering 状态。';
  return `rendering.verified=${text(r.verified)} · frontend_assembly_done=${text(r.frontend_assembly_done)}：${text(r.note)}`;
}
/** Identity comparison rows: what the run manifest recorded against what the frozen bundle carries. */
export function comparisonRowsOf(dto: HistoryPoseDto | null): { key: string; recorded: string; bundle: string; equal: string }[] {
  return Object.entries(dto?.model_resource?.comparison ?? {}).map(([key, row]) => ({
    key, recorded: text(row.recorded), bundle: text(row.bundle), equal: String(row.equal),
  }));
}
export interface ModelAssetRow { assetId: string; declaredSha256: string; mediaType: string; bytes: string; coordinateSpace: string; units: string }
export function modelAssetRowsOf(dto: HistoryPoseDto | null): ModelAssetRow[] {
  return (dto?.model_resource?.assets ?? []).map((asset) => ({
    assetId: asset.asset_id, declaredSha256: asset.sha256, mediaType: asset.media_type,
    bytes: text(asset.bytes), coordinateSpace: asset.coordinate_space ?? '未声明', units: asset.units ?? '未声明',
  }));
}
export function modelResourceText(dto: HistoryPoseDto | null): string {
  const m = dto?.model_resource;
  if (!m) return 'reader 未返回 model_resource。';
  return `status=${text(m.status)} · bundle_sha256=${text(m.bundle_sha256)} · content_identity_sha256=${text(m.content_identity_sha256)} · model_inputs_sha256=${text(m.model_inputs_sha256)} · compiled_scene_sha256=${text(m.compiled_scene_sha256)} · compiler=${text(m.compiler?.name)}/${text(m.compiler?.version)} · scene_source=${text(m.scene_source)} · link_count=${text(m.link_count)} · tcp_site=${text(m.tcp_site)} · root_joint=${m.root_joint ? `${m.root_joint.name}/${m.root_joint.joint_name}/${m.root_joint.joint_type}/local=${JSON.stringify(m.root_joint.local_position_m)}` : 'null'} · arm_hinge_joints=${(m.arm_hinge_joints ?? []).join(',')} · gripper_slide=${(m.gripper_slide_joints ?? []).join(',')} · gripper_other=${(m.gripper_other_joints_in_bundle ?? []).join(',')} · wheel=${(m.wheel_hinge_joints ?? []).join(',')} · tcp_parent_body=${text(m.tcp_parent_body_view?.name)} · world_links=${(m.world_links ?? []).map((w) => `${w.name}[${(w.geom_types ?? []).join('+')}]`).join(' ')} · link_frames=${text(m.link_frames)} · compile_runtime_identity=${m.compile_runtime_identity ? `${m.compile_runtime_identity.run_id}/${m.compile_runtime_identity.episode_id}` : 'null'} · compile_runtime_identity_is_this_episode=${text(m.compile_runtime_identity_is_this_episode)} · live_native_scene_proxied=${text(m.live_native_scene_proxied)} · 资产来源=${text(m.served_via)} · 校验范围=${text(m.verification_scope)} · ${text(m.asset_integrity)}`;
}
/** What the reader says is not proven, per target — never collapsed into a single verdict. */
export function notProvenText(dto: HistoryPoseDto | null): string {
  const rows = dto?.not_proven ?? [];
  return rows.length ? rows.map((row) => `${row.target}[${row.status}]：${row.gap}`).join(' ｜ ') : 'reader 未列出 not_proven';
}
export function poseBoundaryText(dto: HistoryPoseDto | null): string {
  return `能力限制：${(dto?.capability_limits ?? []).join('；') || 'reader 未声明'}。本面板不发命令、不推进物理、不执行回放、不伪造动态物体位姿，也不把在线 scene/snapshot/Actual 当作历史资源。`;
}

/**
 * The static placement tree the pane assembled from must be the tree this Episode's record was compiled
 * against. The Episode-scoped static manifest the backend still owes is not available yet, so the tree
 * comes from the frozen geometry bundle read and is bound to the record by comparing every identity
 * field the two sides publish — mesh digests alone are not enough, since identical meshes can sit in a
 * different tree. Only comparable identity fields belong here (where the tree came from is reported
 * beside the table, not as a row that could never be equal).
 */
export interface TreeBindingRow { field: string; history: string; tree: string; equal: string; note: string }
export function treeBindingRowsOf(dto: HistoryPoseDto | null, tree: {
  bundle_sha256?: string | null; content_identity_sha256?: string | null; model_inputs_sha256?: string | null;
  compiled_scene_sha256?: string | null; link_count?: number | null; world_link_count?: number | null;
  arm_hinge_joints?: string[] | null;
} | null): TreeBindingRow[] {
  const m = dto?.model_resource ?? null;
  if (!m || !tree) return [];
  const row = (field: string, history: unknown, current: unknown, note: string): TreeBindingRow => ({
    field, history: text(history), tree: text(current), equal: String(String(text(history)) === String(text(current))), note,
  });
  return [
    row('bundle_sha256', m.bundle_sha256, tree.bundle_sha256, '冻结 bundle 包摘要'),
    row('content_identity_sha256', m.content_identity_sha256, tree.content_identity_sha256, '编译内容身份：相同 mesh 但不同树内容也会在这里显形'),
    row('model_inputs_sha256', m.model_inputs_sha256, tree.model_inputs_sha256, '模型输入摘要'),
    row('compiled_scene_sha256', m.compiled_scene_sha256, tree.compiled_scene_sha256, '编译场景摘要'),
    row('link_count', m.link_count, tree.link_count, '机器人 link 条数'),
    row('world_link_count', (m.world_links ?? []).length, tree.world_link_count, '世界物体 link 条数'),
    row('arm_hinge_joints', (m.arm_hinge_joints ?? []).join(','), (tree.arm_hinge_joints ?? []).join(','), '臂铰链名与文档顺序'),
  ];
}

const text = (value: unknown) => value === undefined || value === null || value === '' ? 'null' : String(value);

/** The record additionally *names* individual links — the root free joint's body, the TCP parent body,
 * the end effector, the camera chain, each world object — and lists the arm/gripper/wheel joint names it
 * expects. Binding those node by node is what stops a tree that reuses identical mesh digests but rewires
 * a parent from passing. Fields the record leaves undeclared are not compared, and never guessed. */
export interface LinkBindingRow { name: string; field: string; history: string; tree: string; equal: string }
export function linkBindingRowsOf(dto: HistoryPoseDto | null, nodes: {
  name?: string | null; parent_name?: string | null; joint_name?: string | null; joint_type?: string | null;
}[] | null): LinkBindingRow[] {
  const m = dto?.model_resource ?? null;
  if (!m || !nodes) return [];
  const byName = new Map(nodes.filter((node) => node?.name).map((node) => [node.name as string, node]));
  const joints = new Set(nodes.map((node) => node?.joint_name).filter((value): value is string => Boolean(value)));
  const declared: HistoryLinkJointDto[] = [
    ...(m.root_joint ? [m.root_joint] : []), ...(m.tcp_parent_body_view ? [m.tcp_parent_body_view] : []),
    ...(m.end_effector_link ? [m.end_effector_link] : []), ...(m.camera_link_chain ?? []),
    ...(m.world_links ?? []).map((link) => ({ name: link.name })),
  ];
  const rows: LinkBindingRow[] = [];
  declared.forEach((fact) => {
    const name = fact?.name;
    if (!name) return;
    const node = byName.get(name) ?? null;
    if (!node) { rows.push({ name, field: 'link_exists', history: '记录点名该 link', tree: '装配用的树里没有同名 link', equal: 'false' }); return; }
    ([[`parent_name`, fact.parent_name, node.parent_name], [`joint_name`, fact.joint_name, node.joint_name], [`joint_type`, fact.joint_type, node.joint_type]] as const)
      .forEach(([field, want, got]) => {
        if (want === undefined || want === null) return;
        rows.push({ name, field, history: text(want), tree: text(got), equal: String(text(want) === text(got)) });
      });
  });
  ([`arm_hinge_joints`, `gripper_slide_joints`, `gripper_other_joints_in_bundle`, `wheel_hinge_joints`] as const)
    .forEach((list) => (m[list] ?? []).forEach((joint) => rows.push({
      name: joint, field: `joint_in:${list}`, history: '记录声明该关节', tree: joints.has(joint) ? '树里有同名关节' : '树里没有同名关节', equal: String(joints.has(joint)),
    })));
  return rows;
}
