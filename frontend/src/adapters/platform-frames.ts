/**
 * frame-link-1 client and view projections for the image ↔ linked-robot-state slice of one Episode.
 *
 * Every field name, status word and counter here was read off the live
 * `unirobot-mobilecar-frame-link-1` payloads of the history candidate on 2026-10-25 (route params,
 * the twelve `paging` counters, the five roles, `state.recorded_state`, `times.deltas` and
 * `media.items`). Nothing is invented: a field the reader did not return stays absent rather than
 * defaulted, and a list the reader returned empty is treated as its answer, not as missing data.
 * Reads only — no replay execution, no control, no native passthrough.
 */
import { json, query, type EpisodeSource } from './platform-episodes';

export const FRAME_LINK_SCHEMA = 'unirobot-mobilecar-frame-link-1';

export interface FrameIdentity {
  run_id: string; episode_id: string; episode_directory?: string;
  run_directory_identity?: string; native_contract_version?: string;
}
export interface FrameRecordPosition {
  stream_id: string; relative_path: string; line_index: number; record_position?: string;
  event_seq?: number | null; event_type?: string | null;
  identity?: { run_id_matches?: boolean; episode_id_matches?: boolean; declared_run_id?: string | null; declared_episode_id?: string | null };
  clocks?: Record<string, unknown> | null; projection?: Record<string, unknown> | null;
  metadata_keys?: string[] | null; present_fields?: string[]; payload?: Record<string, unknown> | null;
}
export interface FrameRoleDto {
  role: string; join_key: string; key_value: string | null; status: string;
  expected_records: number; matched_records: number; identity_mismatched_records?: number;
  reason?: string | null; sources?: FrameRecordPosition[];
}
export interface FrameAnchorDto {
  line_index: number; relative_path: string; persist_sequence: number | null;
  identity?: { run_id_matches?: boolean; episode_id_matches?: boolean; declared_run_id?: string | null; declared_episode_id?: string | null };
  clocks?: Record<string, unknown>; declared_keys?: string[];
  reference_keys?: Record<string, string | null>; profile?: Record<string, unknown>;
}
export interface FrameMediaItemDto {
  field: string; uri: string; availability: string; refusal_code?: string | null;
  row_line_index?: number | null; agrees_with_observation_row?: boolean | null;
  declared_sha256_by_row?: string | null; declared_bytes_by_row?: number | null; bytes_on_disk?: number | null;
}
export interface FrameStateDto {
  status: string; join_key: string; key_value: string | null; source?: FrameRecordPosition | null;
  recorded_fields?: Record<string, unknown>; recorded_state?: Record<string, unknown>;
  declared_reference?: { feedback_sample_id: string | null; row_status: string };
  recorder_declared_feedback?: { available: boolean; feedback_time_s?: number | null; feedback_clock?: string | null; capture_clocks_declared?: Record<string, string> | null; meaning?: string };
  units?: Record<string, string>; carried_over_from_another_frame: boolean; interpolated: boolean; note?: string;
}
export interface FrameDeltaDto {
  label: string; capture_value: number | null; other_value: number | null; value_s: number; abs_value_ms: number;
  direction: string; basis: string; meaning?: string; line_index?: number; sensor_kind?: string; event_seq?: number;
}
export interface FrameTimesDto {
  deltas: FrameDeltaDto[]; declared_latency_ms?: Record<string, number | null>;
  age_of_state_relative_to_frame?: { abs_ms: number; state_recorded_before_capture: boolean; display_hint?: string } | null;
  same_clock_verified: boolean;
}
export interface FrameDto {
  sample_id: string; stream_id: string; anchor: FrameAnchorDto; linkage_status: string;
  primary_roles_matched: number; declared_reference_status: string;
  media: { declared_by?: string; uri_convention?: string; digest_verification?: string; items: FrameMediaItemDto[] };
  state: FrameStateDto; times: FrameTimesDto; roles: FrameRoleDto[];
}
export interface FramePagingDto {
  limit: number; offset: number; returned: number; scanned_anchor_lines: number; skipped_before_offset: number;
  excluded_stream_mismatch: number; excluded_without_sample_id: number; excluded_outside_time_window: number;
  excluded_anchor_identity_mismatch: number; records_missing_selected_time_base: number;
  next_offset: number | null; has_more: boolean;
}
export interface FramePageDto {
  schema_version: string; read_only: boolean; source: EpisodeSource; retrieved_at: string;
  identity: FrameIdentity;
  anchor: { stream_id: string; relative_path: string; semantics?: string; requested_stream?: string };
  paging: FramePagingDto;
  cursor: { order?: string; line_index_is_not_a_clock: boolean; persist_sequence_is_the_recorders_own_counter?: boolean;
    first_line_index?: number | null; last_line_index?: number | null; first_persist_sequence?: number | null; last_persist_sequence?: number | null };
  time: { selected_time_base: string | null; time_from: number | null; time_to: number | null;
    selectable_time_bases: string[]; units?: Record<string, string>; synchronized_across_streams: boolean;
    clock_sameness?: { declared_by_recorder?: boolean; verified_by_reader?: boolean; note?: string };
    deltas_are_recorded_arithmetic?: boolean; browser_arrival_order_is_not_used?: boolean };
  linkage: { roles: Record<string, { source_stream: string; join_key: string; meaning: string }>;
    status_meaning: Record<string, string>; primary_roles: string[];
    selection_rules?: Record<string, string>; role_coverage_on_this_page?: Record<string, Record<string, number>> };
  summary: { frames_returned: number; frames_with_all_primary_roles_matched: number; frames_with_some_primary_roles_missing: number;
    frames_with_no_primary_role_matched: number; frames_without_a_linked_state: number; frames_with_unresolved_feedback_reference: number };
  frames: FrameDto[]; not_proven?: string[];
  three_d_replay: { this_slice_does_not_enable_3d_replay: boolean; live_geometry_or_actual_may_be_applied: boolean; transforms_are_full_per_body_pose_sequences: boolean };
  capability_limits?: string[];
}

/** The single GET of this contract. `stream` is left to the reader's own default (`rgbd`). */
export async function readFramesPage(input: { episodeId: string; runId: string | null; limit?: number; offset?: number; timeBase?: string | null; timeFrom?: number | null; timeTo?: number | null; sampleId?: string | null }, signal: AbortSignal): Promise<FramePageDto> {
  const params: Record<string, string | number | undefined> = {
    run_id: input.runId ?? undefined, limit: input.limit, offset: input.offset, sample_id: input.sampleId || undefined,
  };
  // The reader answers 400 time_range_required for a base with no bound, so a base is sent only
  // together with at least one bound of its own: the client never issues a request it knows the
  // contract rejects, and never drops a bound the caller asked for.
  if (input.timeBase && (typeof input.timeFrom === 'number' || typeof input.timeTo === 'number')) {
    params.time_base = input.timeBase;
    if (typeof input.timeFrom === 'number') params.time_from = input.timeFrom;
    if (typeof input.timeTo === 'number') params.time_to = input.timeTo;
  }
  return json<FramePageDto>(`/api/v1/episodes/${encodeURIComponent(input.episodeId)}/frames${query(params)}`, signal, FRAME_LINK_SCHEMA);
}

// ---- selection context -------------------------------------------------------------------------

/** The conditions the browser currently holds. The frames response does not echo `sample_id`, so
 *  an explanation of an empty page has to name the interface's own filter, marked as such. */
export interface FrameReadContext { sampleId: string | null; base: string | null; from: number | null; to: number | null }
export const NO_FRAME_CONTEXT: FrameReadContext = { sampleId: null, base: null, from: null, to: null };

/** The selectable bases come only from the page itself: there is no declared fallback for frames. */
export function frameSelectableBases(page: FramePageDto | null): string[] {
  const bases = page?.time?.selectable_time_bases;
  return Array.isArray(bases) ? bases : [];
}
export interface FrameWindowGate { allowed: boolean; reason: string; selectableBases: string[] }
export function frameWindowGate(page: FramePageDto | null, base: string, hasBounds: boolean): FrameWindowGate {
  const selectable = frameSelectableBases(page);
  if (!base) {
    return { allowed: false, selectableBases: selectable,
      reason: hasBounds
        ? '给了边界但没有时间基：frame-link-1 要求 time_base 与 time_from/time_to 同行，界面不替这组秒数猜一个基。'
        : '未选择时间基：现在只按 offset 与 sample_id 浏览，不发送任何时间边界。' };
  }
  if (!selectable.includes(base)) {
    return { allowed: false, selectableBases: selectable,
      reason: `${base} 不在本页声明的可选时间基里（selectable_time_bases=${selectable.join(', ') || '空'}）：不发送它，也不换成数值看起来相近的另一个基。` };
  }
  if (!hasBounds) {
    return { allowed: false, selectableBases: selectable,
      reason: `${base} 已选但没有边界：reader 对只有 time_base 的请求回 400 time_range_required。空白不等于“无界”，要 0 请显式输入 0。` };
  }
  return { allowed: true, reason: '', selectableBases: selectable };
}

// ---- page reading ------------------------------------------------------------------------------

export type FramePageKind = 'frames' | 'no-anchor-lines' | 'sample-no-match' | 'window-empty' | 'offset-past-end' | 'unavailable';
export function framePageKind(page: FramePageDto | null, ctx: FrameReadContext): FramePageKind {
  if (!page) return 'unavailable';
  if (page.frames.length) return 'frames';
  if (!page.paging.scanned_anchor_lines) return 'no-anchor-lines';
  if (ctx.sampleId) return 'sample-no-match';
  if (page.paging.excluded_outside_time_window > 0 || ctx.base) return 'window-empty';
  return 'offset-past-end';
}
/** An empty frame page is never collapsed into one sentence, and no page ever states a total. */
export function framePageExplanation(page: FramePageDto, ctx: FrameReadContext): string {
  const p = page.paging;
  const counters = `offset=${p.offset} · returned=${p.returned} · 扫描锚点行=${p.scanned_anchor_lines} · skipped_before_offset=${p.skipped_before_offset} · excluded_stream_mismatch=${p.excluded_stream_mismatch} · excluded_without_sample_id=${p.excluded_without_sample_id} · excluded_outside_time_window=${p.excluded_outside_time_window} · excluded_anchor_identity_mismatch=${p.excluded_anchor_identity_mismatch} · records_missing_selected_time_base=${p.records_missing_selected_time_base} · next_offset=${text(p.next_offset)} · has_more=${text(p.has_more)}`;
  const missing = p.records_missing_selected_time_base > 0
    ? ` 其中 ${p.records_missing_selected_time_base} 条锚点记录没有所选时间基（${text(page.time.selected_time_base)}）：按计数显示，不补值。` : '';
  if (page.frames.length) {
    return `本页返回 ${page.frames.length} 帧（${counters}）。锚点=${page.anchor.relative_path}（一条记录=一个持久化图像帧），游标顺序=${text(page.cursor.order)}；line_index_is_not_a_clock=${String(page.cursor.line_index_is_not_a_clock)}，行号不是时间轴。响应不提供总帧数，界面也不推算总数。`;
  }
  switch (framePageKind(page, ctx)) {
    case 'no-anchor-lines':
      return `锚点流没有可扫描的行（requested_stream=${text(page.anchor.requested_stream)}，锚点=${page.anchor.relative_path}，${counters}）：这是空读取结果，不推断该 Episode 没有录制，也不切换到别的流凑帧。${missing}`;
    case 'sample-no-match':
      return `界面当前的 sample_id 条件（${ctx.sampleId}，由界面持有：本响应不回显该参数）在扫描的 ${p.scanned_anchor_lines} 行锚点里没有精确命中（${counters}）：只按记录键相等匹配，不取相近 id，也不退回首页。${missing}`;
    case 'window-empty':
      return `时间窗口 ${text(page.time.selected_time_base)} ${text(page.time.time_from)}–${text(page.time.time_to)} 内没有帧：${p.excluded_outside_time_window} 行按窗口排除并计数（${counters}）。这是空结果页，不是读取错误，也不换基重试。${missing}`;
    default:
      return `offset=${p.offset} 之后没有返回帧（扫描 ${p.scanned_anchor_lines} 行，has_more=${text(p.has_more)}，${counters}）：到本次扫描的末尾或 offset 越过锚点行末尾，不推断录制结束。${missing}`;
  }
}
/**
 * The candidate's own documented gap: `has_more`/`next_offset` mix the candidate-line count with the
 * native anchor index, so `has_more=true` can point at a page that legitimately returns nothing under
 * the current condition. The view says that instead of inventing frames or pretending it scanned all.
 */
export function frameStopNote(page: FramePageDto, ctx: FrameReadContext, advancedFromHasMore: boolean): string {
  if (page.frames.length) return '';
  const head = `按 next_offset 推进到的这一页返回 0 帧（offset=${page.paging.offset}，扫描 ${page.paging.scanned_anchor_lines} 行，窗口排除 ${page.paging.excluded_outside_time_window} 行，has_more=${text(page.paging.has_more)}，next_offset=${text(page.paging.next_offset)}）。`;
  if (!advancedFromHasMore) return `${head}${framePageExplanation(page, ctx)}`;
  return `${head}上一页的 has_more=true 混合了候选行计数与锚点原生行号（后端在 m1.5c 记录里列为待修正的分页语义）：它不等于“还有匹配当前条件的帧”。界面停在这一页并保留窗口与筛选条件，不伪造分页结果，也不声称已遍历全部帧。`;
}

// ---- state of the linked record -----------------------------------------------------------------

export interface StateRow { key: string; label: string; value: string; unit: string; note: string }
/**
 * Labels are for the field names this archive actually carries. The wording deliberately keeps a
 * recorded model joint angle a model joint angle: it is not a user command angle and not a
 * calibration result, and the reader declares no mapping between them.
 */
const STATE_FIELDS: Record<string, [string, string]> = {
  base_position_world_sim_m: ['底盘位置 base_position_world_sim_m（世界/仿真坐标）', 'feedback 事件 payload 原值：是录制到的模型状态，不是发送过的指令位置，也不是标定输出。'],
  base_quaternion_xyzw: ['底盘姿态四元数 base_quaternion_xyzw', '分量顺序按字段名声明的 x,y,z,w；界面不重排、不归一化、不换算成欧拉角。'],
  base_twist_body_m_s: ['底盘机体系速度 base_twist_body_m_s', '记录自带的 twist 观测；未与命令速度对比，不读作“执行到了目标速度”。'],
  wheel_velocity_rad_s: ['轮速 wheel_velocity_rad_s（逐轮数组）', '按数组顺序原样显示；reader 未声明轮序与具体车轮的对应表，界面不标注左前/右后。'],
  arm_model_qpos_rad: ['机械臂模型关节角 arm_model_qpos_rad（qpos）', '录制到的模型关节坐标值。它不是用户控制角，也不是标定结果；契约未声明它与命令的对应关系，界面不做换算或映射。'],
  gripper_width_m: ['夹爪开口宽度 gripper_width_m', 'recorded_state 原值。'],
  tcp_position_world_m: ['TCP 位置 tcp_position_world_m（世界坐标）', '记录里自带的 tcp 字段，按原值显示；本切片不做正运动学校验，也不把它套到在线 3D 几何上。'],
  feedback_time_monotonic: ['原始反馈时间 feedback_time_monotonic（记录者自己的计数）', '字段名没有单位后缀，units 表也未覆盖：按原值显示，不换算成秒或毫秒，不与帧采集时间混为一谈。'],
  sim_time_s: ['仿真时间 sim_time_s', '记录自带字段；与 backend_monotonic 的关系只是记录里的命名，reader 未验证同钟。'],
};
/** Units come from the page's own wildcard table (`*_rad` → radians), longest suffix first. */
export function unitForField(units: Record<string, string> | undefined, field: string): { unit: string; declared: boolean } {
  const hits = Object.entries(units ?? {}).filter(([pattern]) => pattern.startsWith('*') && field.endsWith(pattern.slice(1)));
  if (!hits.length) return { unit: '未在 units 表里声明（不自行推断单位）', declared: false };
  hits.sort((a, b) => b[0].length - a[0].length);
  return { unit: `${hits[0][1]}（units 表 ${hits[0][0]} 匹配该字段名）`, declared: true };
}
export function stateRowsOf(frame: FrameDto | null): StateRow[] {
  const state = frame?.state?.recorded_state;
  if (!state) return [];
  return Object.entries(state).map(([key, value]) => {
    const [label, note] = STATE_FIELDS[key] ?? [`${key}（reader 未声明该字段的含义）`, '按记录原值显示，不翻译成关节/控制/标定等类别。'];
    return { key, label, value: formatValue(value), unit: unitForField(frame?.state.units, key).unit, note };
  });
}
function formatValue(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (Array.isArray(value)) return `[${value.map((item) => String(item)).join(', ')}]（${value.length} 个分量，原样）`;
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

// ---- recorded times and their differences --------------------------------------------------------

export interface DeltaRow { label: string; display: string; valueS: string; absMs: string; direction: string; basis: string; captureValue: string; otherValue: string; position: string; note: string }
/**
 * A millisecond number in this response is the difference between two written record fields. It is
 * never a sampling latency, a frame rate, or proof that two writers shared a clock.
 */
const DELTA_LABELS: Record<string, [string, string]> = {
  state_event_minus_frame_capture: ['关联状态事件时间差（状态事件记录 − 本帧采集）', '两条记录字段相减的关联时间差（time.deltas_are_recorded_arithmetic=true）：不是物理状态采样延迟，不是同步证明，也不推导帧率。'],
  recorder_declared_feedback_time_minus_capture: ['记录者声明的反馈时间与采集之差（原始反馈时间另行显示）', 'feedback_time_s 由 rgbd_capture_timing 事件自己写入；它与状态事件的记录时间是否同源，契约未定义，界面不下结论。'],
  timing_event_capture_clock_minus_anchor_capture: ['采集时间事件与锚点记录的采集时钟之差', '两条记录同名字段相减；相等只说明写入的值相等，不说明两个写入者共享时钟。'],
  observation_measurement_time_s_minus_frame_capture: ['观测行 measurement_time_s 与本帧采集之差', '观测行自己的字段，逐条显示；不据此对齐多条流。'],
  observation_arrival_time_s_minus_frame_capture: ['观测行 arrival_time_s 与本帧采集之差', '到达时间是记录者写的字段，不是浏览器收包顺序（browser_arrival_order_is_not_used）。'],
  persist_minus_capture: ['落盘时间减采集时间', '同一条锚点记录内两个字段之差；是记录者的写入间隔，不是采集频率。'],
};
export function deltaRowsOf(frame: FrameDto | null): DeltaRow[] {
  return (frame?.times?.deltas ?? []).map((delta) => {
    const [display, note] = DELTA_LABELS[delta.label] ?? [delta.label, 'reader 未给该差的显示定义：只按 basis 原文显示，不解释成延迟、帧率或同时刻。'];
    const position = [typeof delta.line_index === 'number' ? `line_index=${delta.line_index}` : '', delta.sensor_kind ? `sensor_kind=${delta.sensor_kind}` : ''].filter(Boolean).join(' · ');
    return { label: delta.label, display, valueS: String(delta.value_s), absMs: String(delta.abs_value_ms), direction: delta.direction, basis: delta.basis, captureValue: text(delta.capture_value), otherValue: text(delta.other_value), position, note };
  });
}
export function stateAgeOf(frame: FrameDto | null, page: FramePageDto | null): { absMs: string; beforeCapture: string; hint: string; sameClock: string; clockSameness: string } | null {
  const age = frame?.times?.age_of_state_relative_to_frame;
  if (!age) return null;
  const sameness = page?.time?.clock_sameness;
  return {
    absMs: String(age.abs_ms), beforeCapture: String(age.state_recorded_before_capture), hint: age.display_hint ?? 'reader 未给显示提示',
    sameClock: String(frame?.times?.same_clock_verified),
    clockSameness: sameness ? `declared_by_recorder=${text(sameness.declared_by_recorder)} · verified_by_reader=${text(sameness.verified_by_reader)}；${sameness.note ?? 'reader 未说明'}` : 'reader 未声明 clock_sameness',
  };
}
export function declaredLatencyOf(frame: FrameDto | null): string {
  const latency = frame?.times?.declared_latency_ms;
  if (!latency || !Object.keys(latency).length) return '本帧没有记录自述的延迟字段';
  return `${Object.entries(latency).map(([key, value]) => `${key}=${text(value)}`).join(' · ')}（写入记录的是记录者自己，界面不重测、不当作采样延迟）`;
}

// ---- roles and the declared reference -------------------------------------------------------------

export interface RoleRow { role: string; joinKey: string; keyValue: string; status: string; statusMeaning: string; semantics: string; expected: string; matched: string; mismatched: string; primary: boolean; positions: string; reason: string }
/** The four primary roles and the frame's declared feedback reference are reported separately: a
 *  reference with no target row is not the same statement as a frame that has no state. */
export function roleRowsOf(frame: FrameDto | null, linkage: FramePageDto['linkage'] | undefined): RoleRow[] {
  if (!frame || !linkage) return [];
  return (frame.roles ?? []).map((role) => {
    const semantics = linkage.roles?.[role.role];
    const source = role.sources?.[0];
    return {
      role: role.role, joinKey: role.join_key, keyValue: text(role.key_value), status: role.status,
      statusMeaning: linkage.status_meaning?.[role.status] ?? 'reader 未定义该状态词的含义',
      semantics: semantics ? `${semantics.source_stream} · ${semantics.join_key} · ${semantics.meaning}` : 'reader 未在 linkage.roles 里声明该角色',
      expected: text(role.expected_records), matched: text(role.matched_records), mismatched: text(role.identity_mismatched_records),
      primary: (linkage.primary_roles ?? []).includes(role.role),
      positions: (role.sources ?? []).map((item) => item.record_position ?? `${item.relative_path}#${item.line_index}`).join(' , ') || '无命中记录位置',
      reason: role.reason ?? (role.role === 'feedback_observation_row' && role.status === 'unresolved_reference'
        ? `帧声明的 feedback_sample_id=${text(frame.state?.declared_reference?.feedback_sample_id)} 在该 Episode 的观测行里没有对应记录：这是引用未解析，不等于完全没有机器人状态——本帧的关联状态来自 state_feedback_event（status=${text(frame.state?.status)}）。` : ''),
    };
  });
}
export function linkageScopeText(page: FramePageDto | null, frame: FrameDto | null): string {
  if (!page || !frame) return '未读取帧页：不声明任何关联结论。';
  const s = page.summary;
  return `本页口径：frames_returned=${s.frames_returned} · 四主角色全 matched=${s.frames_with_all_primary_roles_matched} · 部分缺失=${s.frames_with_some_primary_roles_missing} · 全无命中=${s.frames_with_no_primary_role_matched} · 无关联状态=${s.frames_without_a_linked_state} · feedback 引用未解析=${s.frames_with_unresolved_feedback_reference}。本帧 linkage_status=${frame.linkage_status}（只统计 ${page.linkage.primary_roles.join('/')} 四个主角色），primary_roles_matched=${frame.primary_roles_matched}，declared_reference_status=${frame.declared_reference_status}：两个词分别说明“关联到没关联上”和“声明的引用解析没解析开”，不合并成一个结论。`;
}
export function selectionRulesText(page: FramePageDto | null): string {
  const rules = page?.linkage?.selection_rules ?? {};
  const keys = Object.keys(rules);
  if (!keys.length) return 'reader 未声明选样规则。';
  return keys.map((key) => `${key}：${rules[key]}`).join(' ｜ ');
}

// ---- media of the selected frame -------------------------------------------------------------------

export interface FrameMediaRef {
  field: string; uri: string; kind: string; availability: string; loadable: boolean; refusalCode: string;
  declaredSha256: string | null; declaredBytes: string; bytesOnDisk: string; agreesWithRow: string; rowLineIndex: string; note: string;
}
const MEDIA_ROLES: Record<string, string> = { rgb_uri: 'rgb', depth_uri: 'depth', valid_mask_uri: 'valid_mask' };
/** Media comes only from this frame's own `media.items`; a path is never guessed from a sample id. */
export function frameMediaRefs(frame: FrameDto | null): FrameMediaRef[] {
  return (frame?.media?.items ?? []).map((item) => {
    const parts = item.uri.split('/');
    return {
      field: item.field, uri: item.uri, kind: MEDIA_ROLES[item.field] ?? (parts.length >= 2 ? parts[parts.length - 2] : 'asset'),
      availability: item.availability, loadable: item.availability === 'present' && Boolean(item.uri),
      refusalCode: item.refusal_code ?? '', declaredSha256: item.declared_sha256_by_row ?? null,
      declaredBytes: text(item.declared_bytes_by_row), bytesOnDisk: text(item.bytes_on_disk),
      agreesWithRow: text(item.agrees_with_observation_row), rowLineIndex: text(item.row_line_index),
      note: availabilityMeaning(item.availability, item.refusal_code),
    };
  });
}
function availabilityMeaning(availability: string, refusalCode?: string | null) {
  switch (availability) {
    case 'present': return '该引用在归档里存在，可按 assets 端点读取字节。';
    case 'absent': return '记录声明了该引用，但归档里没有这个文件：显示缺帧，不按文件名推测内容，也不显示占位图。';
    case 'refused': return `reader 拒绝该引用${refusalCode ? `（refusal_code=${refusalCode}）` : ''}：路径不在该 Episode 的 assets 范围内，界面不绕过这个拒绝。`;
    case 'not_recorded_on_this_frame': return '该帧没有记录这个引用：不拿别的帧的图片顶替。';
    default: return `availability=${text(availability)} 不在 reader 声明的词表里：按原文显示，不推断可读或不可读。`;
  }
}
/** The default image of a frame is its own rgb reference; nothing else is auto-loaded. */
export function frameAutoLoadRef(refs: FrameMediaRef[]): FrameMediaRef | null {
  return refs.find((ref) => ref.field === 'rgb_uri' && ref.loadable) ?? null;
}
export function mediaDeclarationText(frame: FrameDto | null): string {
  if (!frame) return '未选择帧。';
  return `声明来源：${frame.media.declared_by ?? 'reader 未声明'} · URI 约定：${frame.media.uri_convention ?? 'reader 未声明'} · 摘要校验口径：${frame.media.digest_verification ?? 'reader 未声明'}`;
}

// ---- provenance and boundaries ----------------------------------------------------------------------

export interface ProvenanceRow { key: string; label: string; value: string }
/** Source / run / episode / sample plus the record positions the linkage was read from. */
export function provenanceRowsOf(page: FramePageDto | null, frame: FrameDto | null): ProvenanceRow[] {
  if (!page) return [];
  const anchor = frame?.anchor;
  const state = frame?.state;
  return [
    { key: 'source', label: '来源身份', value: `${page.source.source_id} · ${text(page.source.adapter_id)} · release ${text(page.source.native_release_id)} · access=${page.source.access} · platform_writes=${String(page.source.platform_writes)}` },
    { key: 'root', label: '归档根与边界', value: `recording_root=${text(page.source.recording_root)} · resolved=${text(page.source.recording_root_resolved)} · ${text(page.source.path_boundary)}` },
    { key: 'identity', label: '本次读取的身份', value: `run=${page.identity.run_id} · episode=${page.identity.episode_id} · contract=${text(page.identity.native_contract_version)} · ${text(page.identity.run_directory_identity)}` },
    { key: 'directory', label: 'Episode 目录（由 reader 返回）', value: text(page.identity.episode_directory) },
    { key: 'anchor', label: '帧锚点记录', value: anchor ? `${anchor.relative_path} # line_index=${anchor.line_index} · persist_sequence=${text(anchor.persist_sequence)}（记录者自己的计数器）· 声明身份 run 匹配=${text(anchor.identity?.run_id_matches)} episode 匹配=${text(anchor.identity?.episode_id_matches)}` : '本帧没有锚点记录' },
    { key: 'sample', label: 'sample_id（关联键）', value: frame ? `${frame.sample_id} · stream_id=${frame.stream_id} · 锚点声明的引用键 capture_control_tick_id=${text(anchor?.reference_keys?.capture_control_tick_id)} feedback_sample_id=${text(anchor?.reference_keys?.feedback_sample_id)}` : '未选择帧' },
    { key: 'clocks', label: '锚点记录自带的钟/计数', value: anchor?.clocks ? Object.entries(anchor.clocks).map(([key, value]) => `${key}=${text(value)}`).join(' · ') : '锚点记录未返回 clock 字段' },
    { key: 'profile', label: '采集配置（记录声明）', value: anchor?.profile ? Object.entries(anchor.profile).map(([key, value]) => `${key}=${Array.isArray(value) ? value.join('/') : text(value)}`).join(' · ') : '锚点记录未声明 profile' },
    { key: 'state_position', label: '关联状态的记录位置', value: state?.source ? `${state.source.relative_path}#${state.source.line_index}（stream=${state.source.stream_id}）· event_seq=${text(state.source.event_seq)} · event_type=${text(state.source.event_type)} · join ${state.join_key}=${text(state.key_value)}` : `状态未命中（status=${text(state?.status)}）：没有记录位置可显示，不补造` },
    { key: 'recorded_fields', label: '状态记录行的字段（原样投影）', value: state?.recorded_fields ? Object.entries(state.recorded_fields).map(([key, value]) => `${key}=${text(value)}`).join(' · ') : 'reader 未返回该记录行的字段' },
    { key: 'role_positions', label: '各角色的命中位置', value: frame ? (frame.roles ?? []).map((role) => `${role.role}:${(role.sources ?? []).map((item) => item.record_position ?? `${item.relative_path}#${item.line_index}`).join(',') || '无'}`).join(' ｜ ') : '未选择帧' },
    { key: 'page', label: '本次读取时间（服务端）', value: `retrieved_at=${text(page.retrieved_at)} · schema_version=${page.schema_version} · read_only=${String(page.read_only)}` },
  ];
}
/** The three booleans plus the reader's own not_proven list, passed through unchanged. */
export function frameBoundaryNotice(page: FramePageDto | null): string {
  if (!page) return '未读取帧页：不声明 3D 或未证明范围。';
  const three = page.three_d_replay;
  return `this_slice_does_not_enable_3d_replay=${String(three.this_slice_does_not_enable_3d_replay)} · live_geometry_or_actual_may_be_applied=${String(three.live_geometry_or_actual_may_be_applied)} · transforms_are_full_per_body_pose_sequences=${String(three.transforms_are_full_per_body_pose_sequences)}：本切片不启用历史 3D，不套在线几何或 Actual，transform 行也不是逐 body 位姿序列。未证明：${(page.not_proven ?? []).join('；') || 'reader 未列出'}。限制：${(page.capability_limits ?? []).join('；') || 'reader 未声明'}。synchronized_across_streams=${String(page.time.synchronized_across_streams)}。`;
}

const text = (value: unknown) => value === undefined || value === null || value === '' ? 'null' : String(value);
