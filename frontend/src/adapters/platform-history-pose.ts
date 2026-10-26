/**
 * history-pose-1 client: the robot state of one selected historical frame, the per-part mapping
 * status that says whether a recorded value may drive the model at all, and the mesh bytes of the
 * frozen geometry bundle this Episode's own run manifest was compared against.
 *
 * Every field name, status word and code here was read off the live
 * `unirobot-mobilecar-history-pose-1` payloads of history candidate 18969 on 2026-10-26 (route
 * params `run_id`/`sample_id`/`sha256`, the nine `mapping` rows with their `evidence` and
 * `no_default_applied`, `pose_readiness`, `model_resource` with its 23 assets and identity
 * comparison, `rendering.verified=false`, and the 404 `frame_not_found` / 404
 * `history_model_asset_unavailable` / 409 `history_asset_revision_changed` answers). Nothing is
 * invented: a mapping the reader marks unverified or missing stays undriven, and a value it does not
 * return is never defaulted to 0. Model bytes come only from the history asset endpoint — this
 * module never reads the live scene, snapshot or Actual.
 */
import { json, query, EpisodeContractError, type EpisodeSource } from './platform-episodes';
import { parseError } from './platform-config';

export const HISTORY_POSE_SCHEMA = 'unirobot-mobilecar-history-pose-1';

export interface HistoryMappingEvidence { [key: string]: unknown }
export interface HistoryModelToUserFormula {
  q_user?: string; q_model?: string; zero_model_rad?: number[]; user_direction?: number[]; authority?: string;
}
export interface HistoryMappingRowDto {
  target: string; recorded_field: string | null; recorded_unit: string | null; recorded_length: number | null;
  target_field: string | null; status: string; evidence: HistoryMappingEvidence;
  model_to_user_formula?: HistoryModelToUserFormula | null; no_default_applied?: boolean; gap?: string | null;
}
export interface HistoryPoseReadinessDto {
  model_identity?: string; mapping_valid_for_this_episode?: boolean;
  mapped_targets_partially_or_fully_verified?: string;
  robot_state_can_be_rebuilt_without_assumptions?: boolean; blocking_fields?: string[]; next_round_owner?: string; note?: string;
}
export interface HistoryAssetDto { asset_id: string; sha256: string; media_type: string; coordinate_space?: string; units?: string; bytes?: number | null }
export interface HistoryModelResourceDto {
  status?: string; comparison?: Record<string, { recorded?: string | null; bundle?: string | null; equal?: boolean }>;
  bundle_sha256?: string; content_identity_sha256?: string; compiler?: { name?: string; version?: string };
  verification_scope?: string; model_inputs_sha256?: string; compiled_scene_sha256?: string;
  compile_runtime_identity?: { run_id?: string; backend_generation?: number; episode_id?: string } | null;
  compile_runtime_identity_is_this_episode?: boolean | null;
  scene_source?: string; tcp_site?: string; camera_ids?: string[]; link_count?: number;
  arm_hinge_joints?: string[]; gripper_slide_joints?: string[]; wheel_hinge_joints?: string[];
  root_joint?: HistoryLinkJointDto | null; camera_link_chain?: HistoryLinkJointDto[];
  end_effector_link?: HistoryLinkJointDto | null; world_links?: { name: string; geom_types?: string[] }[];
  assets?: HistoryAssetDto[]; asset_integrity?: string; live_native_scene_proxied?: boolean; served_via?: string;
}
export interface HistoryLinkJointDto {
  name?: string; parent_name?: string | null; joint_name?: string | null; joint_type?: string | null;
  joint_axis?: number[] | null; local_position_m?: number[] | null; local_orientation_xyzw?: number[] | null; geom_types?: string[];
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
  time: { quantities?: unknown[]; state_time_quantity_keys?: string[]; recorder_declared?: Record<string, unknown>;
    semantics_rule?: string; same_clock_verified?: boolean; clock_sameness?: Record<string, unknown> };
  mapping: HistoryMappingRowDto[]; status_meaning?: Record<string, string>;
  pose_readiness?: HistoryPoseReadinessDto; model_resource?: HistoryModelResourceDto;
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

// ---- mapping projection --------------------------------------------------------------------------

export interface MappingRow { target: string; recordedField: string; recordedUnit: string; recordedLength: string; targetField: string; status: string; statusMeaning: string; evidence: string; formula: string; noDefault: string; gap: string }
/** The nine mapping rows are shown as the reader wrote them: per-target status, evidence and gap,
 *  with no collapse into one "pose is fine" verdict. */
export function mappingRowsOf(dto: HistoryPoseDto | null): MappingRow[] {
  return (dto?.mapping ?? []).map((row) => ({
    target: row.target,
    recordedField: row.recorded_field ?? '该目标没有记录字段（recorded_field=null）',
    recordedUnit: row.recorded_unit ?? '未声明单位',
    recordedLength: row.recorded_length === null || row.recorded_length === undefined ? 'null' : String(row.recorded_length),
    targetField: row.target_field ?? 'reader 未给出模型侧目标',
    status: row.status,
    statusMeaning: dto?.status_meaning?.[row.status] ?? 'reader 未定义该状态词的含义',
    evidence: JSON.stringify(row.evidence ?? {}),
    formula: row.model_to_user_formula ? JSON.stringify(row.model_to_user_formula) : 'reader 未声明模型↔用户换算',
    noDefault: String(row.no_default_applied),
    gap: row.gap ?? 'reader 未列出缺口',
  }));
}

/**
 * The interface's own driving rule, stated so it can be judged: a recorded value may move the model
 * only when its mapping row reads `verified` — the reader's word for "record and frozen bundle agree
 * and nothing had to be assumed". `partially_verified`, `unverified`, `missing` and
 * `not_required_for_pose` never drive anything; a missing angle is left missing instead of becoming 0.
 * Model radians are passed through as model radians: the user-zero conversion lives in the live
 * Target layer and is deliberately not applied here.
 */
export type DriveGate = 'verified' | 'partially_verified' | 'unverified' | 'missing' | 'not_required_for_pose' | 'unknown_status';
export interface JointDriveDecision { drivable: boolean; gate: DriveGate; jointNames: string[]; values: number[]; reason: string }
export interface PoseDrive { parts: Record<string, JointDriveDecision>; driven: Record<string, number>; withheld: string[]; wholeRobotRebuildable: boolean; summary: string }
const DRIVE_TARGETS: Record<string, { field: string; names: (dto: HistoryPoseDto) => string[] }> = {
  arm_joint_positions: { field: 'arm_model_qpos_rad', names: (dto) => dto.model_resource?.arm_hinge_joints ?? [] },
  gripper_joints: { field: 'gripper_width_m', names: (dto) => dto.model_resource?.gripper_slide_joints ?? [] },
  base_position: { field: 'base_position_world_sim_m', names: () => [] },
  base_orientation: { field: 'base_quaternion_xyzw', names: () => [] },
  tcp_site_position: { field: 'tcp_position_world_m', names: () => [] },
};
const gateOf = (status: string): DriveGate => (status === 'verified' || status === 'partially_verified' || status === 'unverified' || status === 'missing' || status === 'not_required_for_pose') ? status : 'unknown_status';
export function poseDriveOf(dto: HistoryPoseDto | null): PoseDrive {
  const parts: Record<string, JointDriveDecision> = {};
  const driven: Record<string, number> = {};
  const withheld: string[] = [];
  const payload = dto?.state?.recorded_payload ?? null;
  const singleSelected = dto?.state?.single_state_selected;
  (dto?.mapping ?? []).forEach((row) => {
    const rule = DRIVE_TARGETS[row.target];
    if (!rule) { withheld.push(`${row.target}：界面没有该目标的驱动规则，不驱动任何东西。`); return; }
    const gate = gateOf(row.status);
    const names = rule.names(dto as HistoryPoseDto);
    const raw = payload ? (payload as Record<string, unknown>)[rule.field] : undefined;
    const values = Array.isArray(raw) ? raw.filter((value) => typeof value === 'number') as number[] : (typeof raw === 'number' ? [raw] : []);
    let drivable = gate === 'verified';
    let reason: string;
    if (drivable && names.length !== values.length) {
      drivable = false;
      reason = `映射为 verified，但记录值 ${values.length} 个与 bundle 关节名 ${names.length} 个数量不符：不猜测对应关系，不驱动。`;
    } else if (drivable) {
      reason = `status=verified：按 reader 对该状态的定义（${row.status}），按记录原值驱动 ${names.join('/')}（模型弧度，未经用户零位换算）。`;
    } else if (gate === 'partially_verified') {
      reason = `status=partially_verified：只有部分依据已证（${row.gap ?? 'reader 未列缺口'}）；界面规则要求整目标 verified 才驱动，因此保持固定参考。`;
    } else if (gate === 'unverified') {
      reason = `status=unverified：数值有记录但参考系/约定未证（${row.gap ?? 'reader 未列缺口'}），不拿来放置模型。`;
    } else if (gate === 'missing') {
      reason = `status=missing：记录里根本没有渲染需要的值（${row.gap ?? 'reader 未列缺口'}），不补 0、不从别的帧借。`;
    } else if (gate === 'not_required_for_pose') {
      reason = `status=not_required_for_pose：静态姿态不需要这个量，不驱动。`;
    } else {
      reason = `status=${row.status} 不在 reader 的词表里：按原文显示，不驱动。`;
    }
    parts[row.target] = { drivable, gate, jointNames: names, values, reason };
    if (drivable) names.forEach((name, position) => { driven[name] = values[position]; });
    else withheld.push(`${row.target}：${reason}`);
  });
  const readiness = dto?.pose_readiness ?? {};
  return {
    parts, driven, withheld,
    wholeRobotRebuildable: readiness.robot_state_can_be_rebuilt_without_assumptions === true && Object.keys(driven).length > 0,
    summary: dto ? `已驱动 ${Object.keys(driven).length} 个关节值；未驱动 ${withheld.length} 个目标；robot_state_can_be_rebuilt_without_assumptions=${String(readiness.robot_state_can_be_rebuilt_without_assumptions)}（界面规则：只有 status=verified 的目标才驱动，partially_verified 不驱动）。` : '未读取 robot-state：不驱动任何关节。',
  };
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
  return `model_identity=${text(r.model_identity)} · mapping_valid_for_this_episode=${text(r.mapping_valid_for_this_episode)} · 已证/部分已证目标=${text(r.mapped_targets_partially_or_fully_verified)} · robot_state_can_be_rebuilt_without_assumptions=${text(r.robot_state_can_be_rebuilt_without_assumptions)} · blocking_fields=${(r.blocking_fields ?? []).join('/') || '空'} · 下一步归属=${text(r.next_round_owner)} · ${text(r.note)}`;
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
  return `status=${text(m.status)} · bundle_sha256=${text(m.bundle_sha256)} · content_identity_sha256=${text(m.content_identity_sha256)} · model_inputs_sha256=${text(m.model_inputs_sha256)} · compiled_scene_sha256=${text(m.compiled_scene_sha256)} · compiler=${text(m.compiler?.name)}/${text(m.compiler?.version)} · scene_source=${text(m.scene_source)} · link_count=${text(m.link_count)} · tcp_site=${text(m.tcp_site)} · camera_ids=${(m.camera_ids ?? []).join('/')} · 关节清单 arm=${(m.arm_hinge_joints ?? []).join(',')} gripper=${(m.gripper_slide_joints ?? []).join(',')} wheel=${(m.wheel_hinge_joints ?? []).join(',')} · compile_runtime_identity=${m.compile_runtime_identity ? `${m.compile_runtime_identity.run_id}/${m.compile_runtime_identity.episode_id}` : 'null'} · compile_runtime_identity_is_this_episode=${text(m.compile_runtime_identity_is_this_episode)} · live_native_scene_proxied=${text(m.live_native_scene_proxied)} · 资产来源=${text(m.served_via)} · 校验范围=${text(m.verification_scope)} · ${text(m.asset_integrity)}`;
}
/** What the reader says is not proven, per target — never collapsed into a single verdict. */
export function notProvenText(dto: HistoryPoseDto | null): string {
  const rows = dto?.not_proven ?? [];
  return rows.length ? rows.map((row) => `${row.target}[${row.status}]：${row.gap}`).join(' ｜ ') : 'reader 未列出 not_proven';
}
export function poseBoundaryText(dto: HistoryPoseDto | null): string {
  return `能力限制：${(dto?.capability_limits ?? []).join('；') || 'reader 未声明'}。本面板不发命令、不推进物理、不执行回放、不伪造动态物体位姿，也不把在线 scene/snapshot/Actual 当作历史资源。`;
}

const text = (value: unknown) => value === undefined || value === null || value === '' ? 'null' : String(value);
