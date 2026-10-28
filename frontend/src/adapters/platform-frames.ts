/**
 * frame-link-2 client and view projections for the image ↔ linked-robot-state slice of one Episode.
 *
 * Every field name, status word and counter here was read off the live
 * `unirobot-mobilecar-frame-link-2` payloads of the history candidate on 2026-10-26 (route params,
 * the paging counters with the line census and `scan`, the five roles with their kind inventory and
 * candidate lines, `times.quantities` / `times.recorder_declared`, `media.items`, `summary` and
 * `version_migration`). Nothing is invented: a field the reader did not return stays absent rather
 * than defaulted, and a list the reader returned empty is treated as its answer, not as missing data.
 * Reads only — no replay execution, no control, no native passthrough.
 */
import { json, query, type EpisodeSource } from './platform-episodes';

export const FRAME_LINK_SCHEMA = 'unirobot-mobilecar-frame-link-2';

export interface FrameIdentity {
  run_id: string; episode_id: string; episode_directory?: string;
  run_directory_identity?: string; native_contract_version?: string;
}
export interface DeclaredMedia { uri: string; declared_sha256?: string | null; declared_bytes?: number | null }
export interface FrameRecordPosition {
  stream_id: string; relative_path: string; line_index: number; record_position?: string;
  event_seq?: number | null; event_type?: string | null;
  identity?: { run_id_matches?: boolean; episode_id_matches?: boolean; declared_run_id?: string | null; declared_episode_id?: string | null };
  clocks?: Record<string, unknown> | null; projection?: Record<string, unknown> | null;
  metadata_keys?: string[] | null; present_fields?: string[]; declared_media?: DeclaredMedia[] | null;
  payload?: Record<string, unknown> | null;
}
export interface FrameRoleRequirement {
  required_kinds?: string[]; kind_cardinality?: number; exact_records?: number; rule?: string;
}
export interface FrameRoleDto {
  role: string; join_key: string; key_value: string | null; status: string; meaning?: string;
  requirement?: FrameRoleRequirement | null;
  candidate_records?: number | null; matched_records?: number | null; identity_mismatched_records?: number | null;
  required_kinds?: string[] | null; matched_kinds?: string[] | null; missing_kinds?: string[] | null;
  duplicate_kinds?: string[] | null; unexpected_kinds?: string[] | null;
  kind_inventory?: Record<string, number[]> | null;
  candidate_line_indexes?: number[] | null;
  ambiguous_records?: FrameRecordPosition[] | null;
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
  observation_row_line_indexes?: number[]; observation_row_candidates?: number | null;
  observation_rows_conflict?: boolean | null;
  agrees_with_observation_row?: boolean | null;
  declared_sha256_by_row?: string | null; declared_bytes_by_row?: number | null; bytes_on_disk?: number | null;
}
export interface FrameStateCandidateDto {
  line_index: number; record_position?: string; event_seq?: number | null; event_type?: string | null;
  backend_monotonic_s?: number | null; sim_time_s?: number | null; payload?: Record<string, unknown> | null;
}
export interface FrameStateDto {
  status: string; join_key: string; key_value: string | null; source?: FrameRecordPosition | null;
  recorded_fields?: Record<string, unknown>;
  /** Null whenever the role has no single selected record — the reader never picks the first line. */
  recorded_state?: Record<string, unknown> | null;
  candidate_records?: number | null; single_state_selected?: boolean | null;
  multiple_candidates_note?: string | null; candidates?: FrameStateCandidateDto[] | null;
  declared_reference?: { feedback_sample_id: string | null; row_status: string };
  recorder_declared_feedback?: { available: boolean; timing_event_status?: string | null; feedback_time_s?: number | null; feedback_clock?: string | null; capture_clocks_declared?: Record<string, string> | null; meaning?: string };
  units?: Record<string, string>; carried_over_from_another_frame: boolean; interpolated: boolean; note?: string;
}
export interface FrameQuantityDto {
  key: string; source_record: string; field: string; relative_to: string; unit: string;
  clock?: string; meaning?: string; capture_value: number | null; other_value: number | null;
  value: number; abs_ms: number; direction: string; line_index?: number; sensor_kind?: string;
}
export interface FrameRecorderDeclaredDto {
  fields: Record<string, number | null>; observation_age_ms_note?: string;
  recomputed_arrival_minus_capture_ms?: number | null; agrees_with_recomputation?: boolean | null;
}
export interface FrameTimesDto {
  quantities: FrameQuantityDto[]; recorder_declared?: FrameRecorderDeclaredDto | null;
  semantics_rule?: string; state_time_quantity_keys?: string[];
  removed_in_this_version?: Record<string, string> | string | null;
  same_clock_verified: boolean;
}
export interface FrameDto {
  sample_id: string; stream_id: string; anchor: FrameAnchorDto; linkage_status: string;
  primary_roles_matched: string[]; primary_roles_ambiguous: string[];
  declared_reference_status: string;
  media: { declared_by?: string; uri_convention?: string; digest_verification?: string; duplicate_row_rule?: string; items: FrameMediaItemDto[] };
  state: FrameStateDto; times: FrameTimesDto; roles: FrameRoleDto[];
}
export interface FrameAnchorLinesDto {
  lines_read: number; blank_lines_skipped: number; oversize_lines_skipped: number;
  unparseable_lines_skipped: number; non_object_lines_skipped: number; prefiltered_lines_skipped: number;
}
export interface FramePagingDto {
  limit: number; offset: number; returned: number; has_more: boolean; next_offset: number | null;
  next_qualifying_anchor_line_index: number | null; offset_semantics?: string;
  skipped_before_offset: number; excluded_anchor_identity_mismatch: number; excluded_stream_mismatch: number;
  excluded_without_sample_id: number; excluded_by_sample_id_filter: number; excluded_outside_time_window: number;
  records_missing_selected_time_base: number; anchor_records_examined: number; post_page_records_examined: number;
  anchor_lines?: FrameAnchorLinesDto; scan?: { whole_file_scanned?: boolean; stopped_after_full_page_at_line_index?: number | null; note?: string };
}
export interface FrameVersionMigrationDto {
  from_schema?: string; to_schema?: string; changed?: string[];
  removed_fields?: Record<string, string>; compatibility_note?: string;
}
export interface FrameClockSamenessDto {
  fields_that_name_a_shared_base?: string[]; declared_by_recorder?: boolean; verified_by_reader?: boolean;
  verified_claim?: string; note?: string;
  writer_version_binding?: { recorded?: string[]; not_recorded?: string[]; consequence?: string; synchronized_upgraded_by_numeric_closeness?: boolean };
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
    same_clock_verified?: boolean; clock_sameness?: FrameClockSamenessDto;
    deltas_are_recorded_arithmetic?: boolean; browser_arrival_order_is_not_used?: boolean };
  linkage: { roles: Record<string, { source_stream: string; join_key: string; meaning: string; requirement?: FrameRoleRequirement }>;
    status_meaning: Record<string, string>; status_precedence?: string[]; primary_roles: string[];
    selection_rules?: Record<string, string | string[]>; role_coverage_on_this_page?: Record<string, Record<string, number>> };
  summary: { frames_returned: number; frames_with_all_primary_roles_matched: number; frames_with_some_primary_roles_missing: number;
    frames_with_no_primary_role_matched: number; frames_with_ambiguous_primary_role: number;
    frames_without_a_linked_state: number; frames_with_unresolved_feedback_reference: number };
  frames: FrameDto[]; not_proven?: string[];
  version_migration?: FrameVersionMigrationDto | null;
  three_d_replay: { this_slice_does_not_enable_3d_replay: boolean; live_geometry_or_actual_may_be_applied: boolean;
    transforms_are_full_per_body_pose_sequences: boolean; robot_pose_readiness_slice?: string };
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

/** The conditions the browser currently holds. The frames response does not echo `sample_id`, but it
 *  does count how many anchor records the sample filter excluded, so an empty page can name the
 *  interface's own condition and the reader's own counter side by side. */
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
        ? '给了边界但没有时间基：frame-link-2 要求 time_base 与 time_from/time_to 同行，界面不替这组秒数猜一个基。'
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
  if (!linesRead(page) && !page.paging.anchor_records_examined) return 'no-anchor-lines';
  if (ctx.sampleId) return 'sample-no-match';
  if (page.paging.excluded_outside_time_window > 0 || ctx.base) return 'window-empty';
  return 'offset-past-end';
}
const linesRead = (page: FramePageDto) => page.paging.anchor_lines?.lines_read ?? 0;

function pagingCensus(p: FramePagingDto): string {
  const l = p.anchor_lines;
  const census = l
    ? ` · 已读行 ${l.lines_read}（空行 ${l.blank_lines_skipped}／超限 ${l.oversize_lines_skipped}／坏行 ${l.unparseable_lines_skipped}／非对象 ${l.non_object_lines_skipped}／预过滤 ${l.prefiltered_lines_skipped}）`
    : '';
  const scan = p.scan ? ` · anchor_records_examined=${p.anchor_records_examined} · post_page_records_examined=${p.post_page_records_examined} · whole_file_scanned=${text(p.scan.whole_file_scanned)}` : '';
  return `limit=${p.limit} · offset=${p.offset} · returned=${p.returned} · skipped_before_offset=${p.skipped_before_offset} · 排除：stream 不符 ${p.excluded_stream_mismatch}／无 sample_id ${p.excluded_without_sample_id}／sample 条件 ${p.excluded_by_sample_id_filter}／窗口外 ${p.excluded_outside_time_window}／身份不符 ${p.excluded_anchor_identity_mismatch}${census}${scan}`;
}

/** An empty frame page is never collapsed into one sentence, and no page ever states a total. */
export function framePageExplanation(page: FramePageDto, ctx: FrameReadContext): string {
  const p = page.paging;
  const counters = pagingCensus(p);
  const missing = p.records_missing_selected_time_base > 0
    ? ` 其中 ${p.records_missing_selected_time_base} 条锚点记录没有所选时间基（${text(page.time.selected_time_base)}）：按计数显示，不补值。` : '';
  if (page.frames.length) {
    return `本页返回 ${page.frames.length} 帧（${counters} · next_offset=${text(p.next_offset)} · next_qualifying_anchor_line_index=${text(p.next_qualifying_anchor_line_index)} · has_more=${text(p.has_more)}）。锚点=${page.anchor.relative_path}（一条记录=一个持久化图像帧），游标顺序=${text(page.cursor.order)}；line_index_is_not_a_clock=${String(page.cursor.line_index_is_not_a_clock)}，行号不是时间轴。${text(p.offset_semantics)} 响应不提供总帧数，界面也不推算总数。`;
  }
  switch (framePageKind(page, ctx)) {
    case 'no-anchor-lines':
      return `锚点流本次没有读到任何行（requested_stream=${text(page.anchor.requested_stream)}，锚点=${page.anchor.relative_path}，${counters}）：这是空读取结果，不推断该 Episode 没有录制，也不切换到别的流凑帧。${missing}`;
    case 'sample-no-match':
      return `界面当前的 sample_id 条件（${ctx.sampleId}，由界面持有：本响应不回显该参数）在本次读到的 ${linesRead(page)} 行锚点里没有精确命中，reader 按 sample 条件排除 ${p.excluded_by_sample_id_filter} 条并计数（${counters}）：只按记录键相等匹配，不取相近 id，也不退回首页。${missing}`;
    case 'window-empty':
      return `时间窗口 ${text(page.time.selected_time_base)} ${text(page.time.time_from)}–${text(page.time.time_to)} 内没有帧：${p.excluded_outside_time_window} 行按窗口排除并计数（${counters}）。这是空结果页，不是读取错误，也不换基重试。${missing}`;
    default:
      return `offset=${p.offset} 之后没有返回帧（扫描 ${linesRead(page)} 行，has_more=${text(p.has_more)}，next_offset=${text(p.next_offset)}，${counters}）：${text(p.scan?.note)} 不推断录制结束。${missing}`;
  }
}
/**
 * v2 decides `has_more` by looking for one further qualifying anchor after a full page and reports
 * how far it actually read, so the view states what this page proves and what it does not: an empty
 * page after `has_more=true` is honoured as the reader's own answer, never patched with invented
 * frames, and never widened into a claim of having traversed the whole recording.
 */
export function frameStopNote(page: FramePageDto, ctx: FrameReadContext, advancedFromHasMore: boolean): string {
  if (page.frames.length) return '';
  const p = page.paging;
  const head = `按 next_offset 推进到的这一页返回 0 帧（offset=${p.offset}，扫描 ${linesRead(p && page)} 行，窗口排除 ${p.excluded_outside_time_window} 行，sample 条件排除 ${p.excluded_by_sample_id_filter} 行，has_more=${text(p.has_more)}，next_offset=${text(p.next_offset)}，whole_file_scanned=${text(p.scan?.whole_file_scanned)}）。`;
  if (!advancedFromHasMore) return `${head}${framePageExplanation(page, ctx)}`;
  return `${head}上一页给出 has_more=true，即整页装满后又找到一条合格锚点；本页按 offset_semantics 从该行起重测所有条件，结果为空就是这一条件下读到末尾${p.scan?.whole_file_scanned === false ? '（本次没有扫描整份文件，因此不声称已遍历全部行）' : ''}。界面停在这一页并保留窗口与筛选条件，不伪造分页结果，也不声称已遍历全部帧。`;
}

// ---- state of the linked record -----------------------------------------------------------------

export interface StateRow { key: string; label: string; value: string; unit: string; note: string }
/**
 * Labels are for the field names this archive actually carries. The wording deliberately keeps a
 * recorded model joint angle a model joint angle: it is not a user command angle and not a
 * calibration result, and the frames reader declares no mapping between them — the mapping table
 * with its per-target attestation status comes from the robot-state endpoint.
 */
const STATE_FIELDS: Record<string, [string, string]> = {
  base_position_world_sim_m: ['底盘位置 base_position_world_sim_m（世界/仿真坐标）', 'feedback 事件 payload 原值：是录制到的模型状态，不是发送过的指令位置，也不是标定输出。是否可用于放置底盘由 robot-state 的映射状态决定。'],
  base_quaternion_xyzw: ['底盘姿态四元数 base_quaternion_xyzw', '分量顺序按字段名声明的 x,y,z,w；界面不重排、不归一化、不换算成欧拉角。所旋 body 与参考系由 robot-state 声明是否已证。'],
  base_twist_body_m_s: ['底盘机体系速度 base_twist_body_m_s', '记录自带的 twist 观测；未与命令速度对比，不读作“执行到了目标速度”。静态姿态不需要它。'],
  wheel_velocity_rad_s: ['轮速 wheel_velocity_rad_s（逐轮数组）', '按数组顺序原样显示；reader 未声明轮序与具体车轮的对应表，界面不标注左前/右后。'],
  arm_model_qpos_rad: ['机械臂模型关节角 arm_model_qpos_rad（qpos）', '录制到的模型关节坐标值。它不是用户控制角；robot-state 明确 positions_are_model_radians_not_user_radians=true，界面不套用户零位换算，只做模型角展示。'],
  gripper_width_m: ['夹爪开口宽度 gripper_width_m', 'recorded_state 原值。宽度→夹爪关节值没有已证规则时，界面不折算成关节角。'],
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
/** Nothing is produced when the reader did not select a single state record: no first-candidate pick,
 *  no zero fill, no carry-over from the previous frame. */
export function stateRowsOf(frame: FrameDto | null): StateRow[] {
  const state = frame?.state?.recorded_state;
  if (!state) return [];
  return Object.entries(state).map(([key, value]) => {
    const [label, note] = STATE_FIELDS[key] ?? [`${key}（reader 未声明该字段的含义）`, '按记录原值显示，不翻译成关节/控制/标定等类别。'];
    return { key, label, value: formatValue(value), unit: unitForField(frame?.state.units, key).unit, note };
  });
}
export interface StateSelection { singleSelected: string; candidateRecords: string; hasRecordedState: boolean; note: string; candidates: { position: string; identity: string; payload: string }[] }
/** `single_state_selected` and `recorded_state=null` are reported as the reader's own answer. */
export function stateSelectionOf(frame: FrameDto | null): StateSelection | null {
  const state = frame?.state;
  if (!state) return null;
  return {
    singleSelected: text(state.single_state_selected), candidateRecords: text(state.candidate_records),
    hasRecordedState: Boolean(state.recorded_state),
    note: state.multiple_candidates_note ?? state.note ?? 'reader 未声明该状态的选择口径',
    candidates: (state.candidates ?? []).map((item) => ({
      position: item.record_position ?? `${'events.jsonl'}#${item.line_index}`,
      identity: `event_seq=${text(item.event_seq)} · event_type=${text(item.event_type)} · backend_monotonic_s=${text(item.backend_monotonic_s)} · sim_time_s=${text(item.sim_time_s)}`,
      payload: Object.keys(item.payload ?? {}).join(','),
    })),
  };
}
function formatValue(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (Array.isArray(value)) return `[${value.map((item) => String(item)).join(', ')}]（${value.length} 个分量，原样）`;
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

// ---- recorded times and their differences --------------------------------------------------------

export interface QuantityRow { key: string; display: string; value: string; absMs: string; direction: string; unit: string; sourceRecord: string; field: string; relativeTo: string; clock: string; meaning: string; position: string; captureValue: string; otherValue: string; note: string }
/**
 * Each row is one named subtraction of two recorded fields, and the reader names the record, the
 * field, the unit, the clock and the meaning of every one of them. A millisecond number here is
 * never a sampling latency, a frame rate, or proof that two writers shared a clock; the frame's
 * pipeline latencies stay in `recorder_declared`, where they were written by the recorder itself.
 */
const QUANTITY_LABELS: Record<string, [string, string]> = {
  state_event_write_minus_frame_capture: ['状态事件写入时刻 − 本帧采集', '这是录制器把状态事件写进记录的时刻与帧采集时刻之差：不是状态被采样的瞬间（v1 的 age 字段把两者混在一起，本版已移除）。'],
  state_payload_feedback_time_minus_frame_capture: ['状态负载自述采样时刻 − 本帧采集', '状态 payload 自己声明的 as-of 时间与帧采集之差：与上一条是两个不同的量，不合并、不取平均。'],
  state_payload_feedback_time_minus_state_event_write: ['状态负载采样 − 状态事件写入（同一条记录内）', '同一条事件记录内两个字段之差：说明负载声称的采样比写入早多少，不是跨记录的同钟比较。'],
  state_sim_time_minus_frame_capture_sim_time: ['sim 钟上的状态与帧之差', '另一套钟（sim）上的差值，与上面所有 backend_monotonic 量不同钟；数值为 0 不等于两个写入者同时刻。'],
  recorder_declared_feedback_time_minus_frame_capture: ['录制器声明的反馈时间 − 本帧采集', 'rgbd_capture_timing 事件里录制器自己写的 feedback 时间：第三个独立标记，界面不与上面两个折算成一个值。'],
  timing_payload_capture_minus_anchor_capture: ['采集时间事件的采集戳 − 锚点的采集戳', '两条记录同名字段相减的交叉核对：相等只说明写入的值相等，不说明两个写入者共享时钟。'],
  observation_measurement_minus_frame_capture: ['观测行 measurement_time_s − 本帧采集', '观测行自己的测量戳，逐条显示；不据此对齐多条流。'],
  observation_arrival_minus_frame_capture: ['观测行 arrival_time_s − 本帧采集', '桥接声明的到达时间，是管线环节；到达时间是记录里写的字段，不是浏览器收包顺序。'],
  persist_minus_capture: ['落盘时刻 − 采集时刻（同一条锚点记录）', '录制器自己的采集→写盘间隔，属于管线延迟一类：不是采集频率，也不是状态年龄。'],
};
export function quantityRowsOf(frame: FrameDto | null): QuantityRow[] {
  return (frame?.times?.quantities ?? []).map((q) => {
    const [display, note] = QUANTITY_LABELS[q.key] ?? [`按记录键 ${q.key} 显示（reader 未给该量的显示定义）`, '只按记录给出的 source_record/field/relative_to 原文显示，不解释成延迟、帧率或同时刻。'];
    const position = [typeof q.line_index === 'number' ? `line_index=${q.line_index}` : '', q.sensor_kind ? `sensor_kind=${q.sensor_kind}` : ''].filter(Boolean).join(' · ');
    return { key: q.key, display, value: String(q.value), absMs: String(q.abs_ms), direction: q.direction, unit: q.unit,
      sourceRecord: q.source_record, field: q.field, relativeTo: q.relative_to, clock: q.clock ?? '记录未命名该量的钟',
      meaning: q.meaning ?? 'reader 未声明该量的含义', position, captureValue: text(q.capture_value), otherValue: text(q.other_value), note };
  });
}
/** The recorder's own latency fields, copied: the view never re-derives them into a state age. */
export function recorderDeclaredOf(frame: FrameDto | null): { text: string; fields: { key: string; value: string }[]; note: string; agrees: string } {
  const declared = frame?.times?.recorder_declared;
  if (!declared) return { text: '本帧没有 times.recorder_declared：不自行推断录制器时延。', fields: [], note: 'reader 未声明', agrees: 'unknown' };
  return {
    text: `${Object.entries(declared.fields).map(([key, value]) => `${key}=${text(value)}`).join(' · ')} ｜ 重算 arrival−capture=${text(declared.recomputed_arrival_minus_capture_ms)} · agrees_with_recomputation=${text(declared.agrees_with_recomputation)}`,
    fields: Object.entries(declared.fields).map(([key, value]) => ({ key, value: text(value) })),
    note: declared.observation_age_ms_note ?? 'reader 未说明 observation_age_ms 的含义',
    agrees: text(declared.agrees_with_recomputation),
  };
}
export function stateQuantityKeysOf(frame: FrameDto | null): string {
  const keys = frame?.times?.state_time_quantity_keys ?? [];
  return keys.length ? `${keys.join(' / ')}（这三个量各自独立显示，不合并成单一“年龄”）` : 'reader 未声明 state 相关时间量清单';
}
export function timeSemanticsText(frame: FrameDto | null): string {
  const parts = [frame?.times?.semantics_rule ? `规则：${frame.times.semantics_rule}` : '',
    frame?.times?.removed_in_this_version ? `本版移除字段：${JSON.stringify(frame.times.removed_in_this_version)}` : '',
    `same_clock_verified=${text(frame?.times?.same_clock_verified)}`].filter(Boolean);
  return parts.join(' ｜ ');
}
export function versionMigrationText(page: FramePageDto | null): { head: string; changed: string[]; removed: string[]; note: string } {
  const m = page?.version_migration;
  if (!m) return { head: 'reader 未返回 version_migration。', changed: [], removed: [], note: '' };
  return {
    head: `${text(m.from_schema)} → ${text(m.to_schema)}`,
    changed: m.changed ?? [],
    removed: Object.entries(m.removed_fields ?? {}).map(([key, why]) => `${key}：${why}`),
    note: m.compatibility_note ?? '',
  };
}

// ---- roles and the declared reference -------------------------------------------------------------

export interface RoleRow { role: string; joinKey: string; keyValue: string; status: string; statusMeaning: string; semantics: string; requirement: string; candidates: string; matched: string; mismatched: string; kinds: string; inventory: string; ambiguous: string; primary: boolean; positions: string; reason: string }
const positionText = (sources: FrameRecordPosition[] | undefined) => (sources ?? [])
  .map((item) => item.record_position ?? `${item.relative_path}#${item.line_index}`).join(' , ') || '无命中记录位置';
/** The four primary roles and the frame's declared feedback reference are reported separately: a
 *  reference with no target row is not the same statement as a frame that has no state. Ambiguity
 *  keeps every candidate line: the view never resolves a repeated kind by choosing one. */
export function roleRowsOf(frame: FrameDto | null, linkage: FramePageDto['linkage'] | undefined): RoleRow[] {
  if (!frame || !linkage) return [];
  return (frame.roles ?? []).map((role) => {
    const semantics = linkage.roles?.[role.role];
    const requirement = role.requirement ?? {};
    const requirementText = [
      requirement.required_kinds ? `required_kinds=${requirement.required_kinds.join('/')} ×${text(requirement.kind_cardinality)}` : '',
      typeof requirement.exact_records === 'number' ? `exact_records=${requirement.exact_records}` : '',
      requirement.rule ?? '',
    ].filter(Boolean).join(' ｜ ') || 'reader 未声明该角色的完整性要求';
    return {
      role: role.role, joinKey: role.join_key, keyValue: text(role.key_value), status: role.status,
      statusMeaning: linkage.status_meaning?.[role.status] ?? 'reader 未定义该状态词的含义',
      semantics: semantics ? `${semantics.source_stream} · ${semantics.join_key} · ${semantics.meaning}` : 'reader 未在 linkage.roles 里声明该角色',
      requirement: requirementText,
      candidates: text(role.candidate_records), matched: text(role.matched_records), mismatched: text(role.identity_mismatched_records),
      kinds: `missing_kinds=${(role.missing_kinds ?? []).join('/') || '空'} · duplicate_kinds=${(role.duplicate_kinds ?? []).join('/') || '空'} · unexpected_kinds=${(role.unexpected_kinds ?? []).join('/') || '空'}`,
      inventory: role.kind_inventory ? Object.entries(role.kind_inventory).map(([kind, lines]) => `${kind}→[${lines.join(',')}]`).join(' ') : 'reader 未给 kind 清单',
      ambiguous: (role.ambiguous_records ?? []).length ? `${(role.ambiguous_records ?? []).length} 条候选记录冲突（逐条列出，见下）` : (role.status === 'ambiguous_kind' || role.status === 'ambiguous_candidates' ? '状态为歧义，但 reader 未列候选记录' : '无歧义候选'),
      primary: (linkage.primary_roles ?? []).includes(role.role),
      positions: positionText(role.sources),
      reason: role.reason ?? (role.role === 'feedback_observation_row' && role.status === 'unresolved_reference'
        ? `帧声明的 feedback_sample_id=${text(frame.state?.declared_reference?.feedback_sample_id)} 在该 Episode 的观测行里没有对应记录：这是引用未解析，不等于完全没有机器人状态——本帧的关联状态来自 state_feedback_event（status=${text(frame.state?.status)}）。` : ''),
    };
  });
}
export function ambiguousRoleCount(frame: FrameDto | null): number {
  return (frame?.roles ?? []).filter((role) => role.status === 'ambiguous_kind' || role.status === 'ambiguous_candidates').length;
}
export function linkageScopeText(page: FramePageDto | null, frame: FrameDto | null): string {
  if (!page || !frame) return '未读取帧页：不声明任何关联结论。';
  const s = page.summary;
  return `本页口径：frames_returned=${s.frames_returned} · 四主角色全 matched=${s.frames_with_all_primary_roles_matched} · 部分缺失=${s.frames_with_some_primary_roles_missing} · 全无命中=${s.frames_with_no_primary_role_matched} · 主角色歧义=${s.frames_with_ambiguous_primary_role} · 无关联状态=${s.frames_without_a_linked_state} · feedback 引用未解析=${s.frames_with_unresolved_feedback_reference}。本帧 linkage_status=${frame.linkage_status}（只统计 ${page.linkage.primary_roles.join('/')} 四个主角色），primary_roles_matched=[${(frame.primary_roles_matched ?? []).join(',')||'空'}] · primary_roles_ambiguous=[${(frame.primary_roles_ambiguous ?? []).join(',')||'空'}]，declared_reference_status=${frame.declared_reference_status}：这些词分别说明“关联到没关联上”“有没有多候选歧义”和“声明的引用解析没解析开”，不合并成一个结论。`;
}
export function statusPrecedenceText(page: FramePageDto | null): string {
  const list = page?.linkage?.status_precedence ?? [];
  return list.length ? `状态优先级（响应原文，从高到低）：${list.join(' > ')}` : 'reader 未声明状态优先级';
}
export function selectionRulesText(page: FramePageDto | null): string {
  const rules = page?.linkage?.selection_rules ?? {};
  const keys = Object.keys(rules);
  if (!keys.length) return 'reader 未声明选样规则。';
  return keys.map((key) => `${key}：${typeof rules[key] === 'string' ? rules[key] : JSON.stringify(rules[key])}`).join(' ｜ ');
}
export function roleCoverageText(page: FramePageDto | null): string {
  const coverage = page?.linkage?.role_coverage_on_this_page ?? {};
  const keys = Object.keys(coverage);
  if (!keys.length) return 'reader 未给本页角色覆盖统计。';
  return keys.map((role) => `${role}: ${Object.entries(coverage[role]).map(([status, count]) => `${status}=${count}`).join(' ')}`).join(' ｜ ');
}

// ---- media of the selected frame -------------------------------------------------------------------

export interface FrameMediaRef {
  field: string; uri: string; kind: string; availability: string; loadable: boolean; refusalCode: string;
  declaredSha256: string | null; declaredBytes: string; bytesOnDisk: string; agreesWithRow: string;
  rowLines: string; rowCandidates: string; rowsConflict: string; note: string;
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
      agreesWithRow: text(item.agrees_with_observation_row),
      rowLines: (item.observation_row_line_indexes ?? []).join(',') || 'null',
      rowCandidates: text(item.observation_row_candidates),
      rowsConflict: text(item.observation_rows_conflict),
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
  return `声明来源：${frame.media.declared_by ?? 'reader 未声明'} · URI 约定：${frame.media.uri_convention ?? 'reader 未声明'} · 摘要校验口径：${frame.media.digest_verification ?? 'reader 未声明'} · 重复行规则：${frame.media.duplicate_row_rule ?? 'reader 未声明'}`;
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
    { key: 'role_positions', label: '各角色的命中位置', value: frame ? (frame.roles ?? []).map((role) => `${role.role}:${positionText(role.sources)}`).join(' ｜ ') : '未选择帧' },
    { key: 'page', label: '本次读取时间（服务端）', value: `retrieved_at=${text(page.retrieved_at)} · schema_version=${page.schema_version} · read_only=${String(page.read_only)}` },
  ];
}
/** The four booleans plus the reader's own not_proven list, passed through unchanged. */
export function frameBoundaryNotice(page: FramePageDto | null): string {
  if (!page) return '未读取帧页：不声明 3D 或未证明范围。';
  const three = page.three_d_replay;
  return `this_slice_does_not_enable_3d_replay=${String(three.this_slice_does_not_enable_3d_replay)} · live_geometry_or_actual_may_be_applied=${String(three.live_geometry_or_actual_may_be_applied)} · transforms_are_full_per_body_pose_sequences=${String(three.transforms_are_full_per_body_pose_sequences)}：本切片不启用历史 3D，不套在线几何或 Actual，transform 行也不是逐 body 位姿序列。robot_pose_readiness_slice=${text(three.robot_pose_readiness_slice)}（固定模型参考与该帧姿态由那边单独判定）。未证明：${(page.not_proven ?? []).join('；') || 'reader 未列出'}。限制：${(page.capability_limits ?? []).join('；') || 'reader 未声明'}。synchronized_across_streams=${String(page.time.synchronized_across_streams)}。`;
}
export function clockSamenessText(page: FramePageDto | null): string {
  const s = page?.time?.clock_sameness;
  if (!s) return 'reader 未声明 clock_sameness。';
  const binding = s.writer_version_binding ?? {};
  return `命名共享钟基的字段：${(s.fields_that_name_a_shared_base ?? []).join('；') || 'reader 未列出'} · declared_by_recorder=${text(s.declared_by_recorder)} · verified_by_reader=${text(s.verified_by_reader)} · ${s.verified_claim ?? 'reader 未说明该声明的含义'} ｜ 写入版本可绑定到：${(binding.recorded ?? []).join('；') || 'reader 未列出'}；未记录：${(binding.not_recorded ?? []).join('；') || 'reader 未列出'}；后果=${text(binding.consequence)}；数值接近不升级为 synchronized_upgraded_by_numeric_closeness=${text(binding.synchronized_upgraded_by_numeric_closeness)}`;
}

const text = (value: unknown) => value === undefined || value === null || value === '' ? 'null' : String(value);
