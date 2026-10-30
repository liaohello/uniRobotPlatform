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
  semantics_rule?: string; state_time_quantity_keys?: string[]; sim_time_quantity_keys?: string[];
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
  from_schema?: string; to_schema?: string; changed?: string[]; corrections?: string[];
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
  /** Present only when this page was read with `include_time_quality=true`; absent on a normal page. */
  time_quality?: FrameTimeQualityDto | null;
  version_migration?: FrameVersionMigrationDto | null;
  three_d_replay: { this_slice_does_not_enable_3d_replay: boolean; live_geometry_or_actual_may_be_applied: boolean;
    transforms_are_full_per_body_pose_sequences: boolean; robot_pose_readiness_slice?: string };
  capability_limits?: string[];
}

/** The single GET of this contract. `stream` is left to the reader's own default (`rgbd`). */
export async function readFramesPage(input: { episodeId: string; runId: string | null; limit?: number; offset?: number; timeBase?: string | null; timeFrom?: number | null; timeTo?: number | null; sampleId?: string | null; includeTimeQuality?: boolean }, signal: AbortSignal): Promise<FramePageDto> {
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
  // Only this literal spelling: the reader's 422 for a non-boolean value is FastAPI's own `bool_parsing`
  // body rather than the project's `{detail:{code}}` shape, so the client never sends anything else.
  if (input.includeTimeQuality) params.include_time_quality = 'true';
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
/** M1.5e splits the simulator-time quantity in two: the payload's own stamp and the event envelope's
 *  stamp are different records, and the payload quantity is absent rather than filled from the
 *  envelope. The list is the reader's, so an absent key is reported as absent. */
export function simQuantityKeysOf(frame: FrameDto | null): string {
  const keys = frame?.times?.sim_time_quantity_keys ?? [];
  return keys.length ? `${keys.join(' / ')}（负载量与信封量各一条，缺就是缺，不互相回填）` : 'reader 未声明 sim 时间量清单（本版无该键）';
}
export function timeSemanticsText(frame: FrameDto | null): string {
  const parts = [frame?.times?.semantics_rule ? `规则：${frame.times.semantics_rule}` : '',
    frame?.times?.removed_in_this_version ? `本版移除字段：${JSON.stringify(frame.times.removed_in_this_version)}` : '',
    `same_clock_verified=${text(frame?.times?.same_clock_verified)}`].filter(Boolean);
  return parts.join(' ｜ ');
}
export function versionMigrationText(page: FramePageDto | null): { head: string; changed: string[]; removed: string[]; corrections: string[]; note: string } {
  const m = page?.version_migration;
  if (!m) return { head: 'reader 未返回 version_migration。', changed: [], removed: [], corrections: [], note: '' };
  return {
    head: `${text(m.from_schema)} → ${text(m.to_schema)}`,
    changed: m.changed ?? [],
    removed: Object.entries(m.removed_fields ?? {}).map(([key, why]) => `${key}：${why}`),
    // M1.5e keeps the schema at frame-link-2 and records its labelling fix here instead.
    corrections: m.corrections ?? [],
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


/**
 * The bounded recorded-Actual curve. It reads only what this page already carries: each frame's own
 * `state.recorded_state` with its single selected state record. Nothing here fetches the archive, and a
 * frame without a selected state is a break in the line, never a zero and never a carried-over value.
 *
 * The x axis is either the frame's order within this loaded page (the reader's append order, which is a
 * file order and explicitly not a clock) or one raw recorded time base taken from the anchor's own
 * `clocks`, offered only when every frame of the page carries a finite value for it. A decrease in that
 * base is reported and left where it is: the curve never silently re-sorts the record.
 */
export const ARM_ACTUAL_FIELD = 'arm_model_qpos_rad';
export const CURVE_FRAME_ORDER = 'frame_order';
export interface CurveAxisLabel { key: string; label: string; origin: string; unit: string; note: string }
export interface CurvePoint { position: number; sampleId: string; lineIndex: number; persistSequence: number | null; x: number | null; value: number | null; missing: string }
export interface CurveAxisSeries { field: string; label: string; points: CurvePoint[]; segments: CurvePoint[][]; missing: number; min: number | null; max: number | null }
export interface FrameCurve {
  xBase: string; xLabel: string; origin: string; unit: string;
  series: CurveAxisSeries[]; joints: string[]; outOfOrder: { position: number; sampleId: string; from: number; to: number }[];
  frames: number; withSelectedState: number; withoutValue: number; target: string; note: string;
}

/** Which x axes this page can honestly offer: frame order always, a raw clock base only when complete. */
export function curveXAxesOf(page: FramePageDto | null): CurveAxisLabel[] {
  const frames = page?.frames ?? [];
  const axes: CurveAxisLabel[] = [{ key: CURVE_FRAME_ORDER, label: '帧顺序（本页第 N 帧，reader 的追加顺序）', origin: `cursor.order=${page?.cursor.order ?? '未声明'}`, unit: '帧序号（不是时钟）',
    note: `line_index 不是时钟（${String(page?.cursor.line_index_is_not_a_clock ?? '未声明')}）：这条轴只表示本页内的先后，不换算成秒。` }];
  const keys = ['capture_backend_monotonic_s', 'persist_backend_monotonic_s', 'capture_sim_time_s'];
  // With no frames on the page there is nothing to judge a base by: only frame order is offered.
  if (!frames.length) return axes;
  keys.forEach((key) => {
    const values = frames.map((frame) => numeric(frame.anchor.clocks?.[key]));
    if (frames.length && values.every((value) => value !== null)) {
      axes.push({ key: `anchor.clocks.${key}`, label: `原始记录时间基 ${key}`, origin: `锚点 ${frames[0].anchor.relative_path} 的 anchor.clocks`,
        unit: page?.time.units?.['*_s'] ?? 'seconds（按 time.units 原样）',
        note: `本页 ${frames.length} 帧全部带 ${key} 的有限数值，所以可以用作横轴；它是记录自己的一个钟，不声称与别的流同源。` });
    } else {
      axes.push({ key: `anchor.clocks.${key}`, label: `原始记录时间基 ${key}（本页不完整，不可选）`, origin: 'anchor.clocks', unit: '—',
        note: `本页有帧缺 ${key} 或非数值：不提供该轴，也不补值、不裁剪到部分帧。` });
    }
  });
  return axes;
}

/** The five arm values of the frames on this page. `joints` are array indexes, because the page carries
 *  no per-frame joint names: the name↔index correspondence is attested only for the frame whose
 *  robot-state was read, so the curve keeps the record's own array labelling. */
export function frameActualCurveOf(page: FramePageDto | null, xBase: string): FrameCurve {
  const frames = page?.frames ?? [];
  const clockKey = xBase.startsWith('anchor.clocks.') ? xBase.slice('anchor.clocks.'.length) : null;
  const joints = [`[${0}]`, `[${1}]`, `[2]`, `[3]`, `[4]`].map((suffix) => `${ARM_ACTUAL_FIELD}${suffix}`);
  let outOfOrder: FrameCurve['outOfOrder'] = [];
  let previous: number | null = null;
  const points: { x: number | null; values: (number | null)[]; missing: string }[] = frames.map((frame, position) => {
    const x = clockKey ? numeric(frame.anchor.clocks?.[clockKey]) : position + 1;
    if (x !== null && previous !== null && x < previous) outOfOrder.push({ position, sampleId: frame.sample_id, from: previous, to: x });
    if (x !== null) previous = x;
    const state = frame.state.recorded_state;
    const arm = Array.isArray(state?.[ARM_ACTUAL_FIELD]) ? (state![ARM_ACTUAL_FIELD] as unknown[]) : null;
    const missing = !frame.state.single_state_selected || !state
      ? `single_state_selected=${String(frame.state.single_state_selected)} · status=${frame.state.status}：本帧没有单一选中的状态记录，断口不补值`
      : !arm ? `recorded_state 里没有 ${ARM_ACTUAL_FIELD}`
        : arm.length < 5 ? `${ARM_ACTUAL_FIELD} 长度 ${arm.length} < 5：不按顺序猜缺的轴` : '';
    return { x, values: joints.map((_, index) => numeric(arm?.[index])), missing };
  });
  const series: CurveAxisSeries[] = joints.map((field, axis) => {
    const list: CurvePoint[] = frames.map((frame, position) => ({
      position, sampleId: frame.sample_id, lineIndex: frame.anchor.line_index, persistSequence: frame.anchor.persist_sequence ?? null,
      x: points[position].x, value: points[position].values[axis], missing: points[position].missing,
    }));
    const segments: CurvePoint[][] = [];
    let open: CurvePoint[] = [];
    list.forEach((point) => {
      if (point.value === null || point.x === null) { if (open.length) segments.push(open); open = []; return; }
      open.push(point);
    });
    if (open.length) segments.push(open);
    const finite = list.filter((point) => point.value !== null).map((point) => point.value as number);
    return { field, label: field, points: list, segments, missing: list.filter((point) => point.value === null).length,
      min: finite.length ? Math.min(...finite) : null, max: finite.length ? Math.max(...finite) : null };
  });
  const withSelectedState = frames.filter((frame) => frame.state.single_state_selected && frame.state.recorded_state).length;
  const axis = curveXAxesOf(page).find((item) => item.key === xBase) ?? curveXAxesOf(page)[0];
  const keyFields = new Set(frames.flatMap((frame) => Object.keys(frame.state.recorded_state ?? {})));
  const targetFields = [...keyFields].filter((key) => /target|command|desired|setpoint/i.test(key));
  return {
    xBase: axis.key, xLabel: axis.label, origin: axis.origin, unit: axis.unit, series,
    joints: [`0`, `1`, `2`, `3`, `4`], outOfOrder,
    frames: frames.length, withSelectedState, withoutValue: series[0]?.missing ?? 0,
    target: targetFields.length
      ? `本帧记录里出现的可能目标字段：${targetFields.join(', ')}（逐个仍需来源与语义明确才画；本页不猜）`
      : `recorded_state 的键集合（${[...keyFields].sort().join(', ') || '空'}）里没有语义明确的位置目标：不画记录 Target。` +
        ` wheel_velocity_rad_s 与 base_twist_body_m_s 是速度/旋量，不是关节目标；命令意图更不等于 Actual。`,
    note: axis.note,
  };
}

const numeric = (value: unknown): number | null => typeof value === 'number' && Number.isFinite(value) ? value : null;

// ---- M1.5g anchor time quality (the interval census) -------------------------------------------------

/**
 * `time_quality` exactly as the 18979 candidate answers it (read off the live payload of
 * `GET …/frames?include_time_quality=true` on 2026-10-30; `schema_version` is still
 * `unirobot-mobilecar-frame-link-2` and the flag is absent from a normal page by design). A census is a
 * statement about the whole anchor file scan, so nothing here reads it as a per-page or per-window answer,
 * and a base the census does not name stays unqualified instead of being guessed.
 */
export interface TimeQualityCoverageDto {
  run_id: string; episode_id: string; stream_id: string; anchor_relative_path: string;
  anchors_in_this_scan: number; unique_sample_ids: number;
  rejected_anchors: { excluded_identity_mismatch: number; excluded_stream_mismatch: number; excluded_without_sample_id: number };
  anchor_lines: FrameAnchorLinesDto;
  first_anchor_line_index: number | null; last_anchor_line_index: number | null;
  whole_anchor_file_scanned: boolean; anchor_limit: number; stopped_at_line_index: number | null;
  covers_whole_episode: boolean; not_a_whole_archive_sweep: boolean; scope_note?: string;
  page_filter_context?: { time_base: string | null; time_from: number | null; time_to: number | null;
    sample_id: string | null; offset: number; limit: number; returned: number; note?: string };
}
export interface TimeQualityBaseDto {
  field: string; unit: string; clock?: string; source_record?: string;
  anchors_scanned: number; numeric_count: number;
  missing_count: number; missing_line_indexes?: number[]; missing_line_indexes_truncated?: boolean;
  non_numeric_count: number; non_numeric_samples?: string[]; non_numeric_samples_truncated?: boolean;
  first_in_file_order: number | null; last_in_file_order: number | null;
  first_line_index?: number | null; last_line_index?: number | null;
  min_recorded_value: number | null; max_recorded_value: number | null; first_minus_last_s?: number | null;
  recorded_gaps?: { count: number; min_s: number | null; max_s: number | null; median_s?: number | null; mean_s?: number | null; total_s?: number | null };
  equal_adjacent_gaps?: { count: number; line_index_pairs?: number[][]; line_index_pairs_truncated?: boolean };
  backwards_gaps?: { count: number; steps?: unknown[]; steps_truncated?: boolean };
  monotonic_non_decreasing_in_file_order?: boolean; file_order_matches_value_order?: boolean; description?: string;
}
export interface TimeQualityDuplicateDto { sample_id: string; occurrences: number; line_indexes: number[]; record_positions?: string[] }
export interface TimeQualityIdentityDto {
  duplicate_sample_id_groups: number; duplicates?: TimeQualityDuplicateDto[]; duplicates_truncated?: boolean;
  every_anchor_position_is_reported?: boolean; effect_on_this_route?: string; effect_on_robot_state?: string;
}
export interface IntervalEligibilityDto {
  eligible_for_whole_episode: boolean; eligible_within_this_scan: boolean; blocking_reasons: string[];
  zero_interval_ties_present?: boolean; implied_rate_hz_from_median_recorded_gap?: number | null; implied_rate_note?: string;
}
export interface FrameTimeQualityDto {
  requested: boolean; coverage: TimeQualityCoverageDto; time_bases: Record<string, TimeQualityBaseDto>;
  identity?: TimeQualityIdentityDto; recorder_counters?: Record<string, unknown>;
  profile?: { profile_ids_seen?: string[]; anchor_fields_declaring_a_numeric_rate?: string[]; note?: string };
  playback_eligibility?: {
    modes?: Record<string, string>;
    append_order_display?: { mode?: string; eligible?: boolean; basis?: string; does_not_require?: string[]; anchor_position_never_reordered_by_time?: boolean };
    recorded_interval_schedule?: {
      mode?: string; eligible_by_base?: Record<string, IntervalEligibilityDto>; any_base_eligible_for_whole_episode?: boolean;
      rules_when_unqualified?: Record<string, string>; never_assumed?: Record<string, unknown>
    };
    cross_stream_synchronized?: { mode?: string; eligible?: boolean; reason?: string; not_derivable_from?: string[]; same_page_evidence?: Record<string, unknown> };
  };
  not_proven?: string[];
}

/** The census namespace: one session per source/run/episode/anchor-stream, never a content-versioned store. */
export function timeQualitySessionKey(input: { sourceId?: string; runId: string | null; episodeId: string; streamId: string | null }): string {
  return `${input.sourceId ?? 'source?'}|${input.runId ?? 'run?'}|${input.episodeId}|${input.streamId ?? 'stream?'}`;
}

export type IntervalStepKind = 'interval' | 'tie' | 'backwards' | 'missing';
export interface IntervalStep {
  kind: IntervalStepKind; fromPosition: number; toPosition: number; crossPage: boolean;
  fromValue: number | null; toValue: number | null; gapS: number | null; waitMs: number | null; note: string;
}
export interface IntervalGate {
  base: string; present: boolean; allowed: boolean; reasons: string[]; disclosures: string[];
  eligibility: IntervalEligibilityDto | null; baseRow: TimeQualityBaseDto | null;
  unit: string; clock: string; description: string;
}

const UNJUDGEABLE_ANCHOR_LINES = ['unparseable_lines_skipped', 'oversize_lines_skipped', 'non_object_lines_skipped'] as const;
const REJECTED_ANCHOR_KEYS = ['excluded_identity_mismatch', 'excluded_stream_mismatch', 'excluded_without_sample_id'] as const;

/**
 * Whether this Episode's census qualifies `base` for scheduling a step by its recorded gap. Each refusal is
 * stated in the reader's own terms, and the whole-episode claim is only ever taken from
 * `eligible_for_whole_episode` — `eligible_within_this_scan` is shown beside it, never as "this window's
 * eligibility", because the window filters the page while the census still describes the whole scan.
 */
export function intervalGateOf(censusPage: FramePageDto | null, base: string): IntervalGate {
  const page = censusPage;
  const tq = page?.time_quality ?? null;
  const row = tq?.time_bases?.[base] ?? null;
  const eligibility = tq?.playback_eligibility?.recorded_interval_schedule?.eligible_by_base?.[base] ?? null;
  const reasons: string[] = [];
  const disclosures: string[] = [];
  const gate: Omit<IntervalGate, 'allowed' | 'reasons' | 'disclosures'> = {
    base, present: Boolean(tq?.requested), eligibility, baseRow: row,
    unit: row?.unit ?? '—', clock: row?.clock ?? '未声明', description: row?.description ?? 'reader 未描述这个基',
  };
  if (!tq) return { ...gate, allowed: false, reasons: ['本会话还没有读到 census（普通帧页不带 time_quality）：记录间隔模式需要一次 `include_time_quality=true` 的读取，界面不据缺数据开放。'], disclosures };
  if (tq.requested !== true) reasons.push(`census 自述 requested=${String(tq.requested)}：这份响应不是带资格判定的读取结果，不据此排程。`);
  const cov = tq.coverage;
  if (cov) {
    if (page && (cov.run_id !== page.identity.run_id || cov.episode_id !== page.identity.episode_id)) {
      reasons.push(`census 身份与本帧页不符（coverage ${cov.episode_id}/${cov.run_id} vs 页面 ${page.identity.episode_id}/${page.identity.run_id}）：不用别的来源的资格开放播放。`);
    }
    if (page && cov.stream_id !== page.anchor.requested_stream && cov.stream_id !== page.anchor.stream_id) {
      // The census names the requested stream (`rgbd`), while `anchor.stream_id` names the file the anchors
      // were read from (`observations-persist`); those are the reader's own two words for one source, so a
      // match on either is one stream. Anchors of a genuinely different stream are still refused.
      reasons.push(`census 的 stream_id 是 ${cov.stream_id}，本页的流是 ${text(page.anchor.requested_stream)}／锚点文件流是 ${text(page.anchor.stream_id)}：不同流的锚点序列不能互相当作同一份节奏。`);
    }
    if (cov.whole_anchor_file_scanned !== true || cov.covers_whole_episode !== true || cov.stopped_at_line_index !== null) {
      reasons.push(`本次 census 没有扫完整份锚点文件（whole_anchor_file_scanned=${String(cov.whole_anchor_file_scanned)}、covers_whole_episode=${String(cov.covers_whole_episode)}、stopped_at_line_index=${text(cov.stopped_at_line_index)}、anchor_limit=${text(cov.anchor_limit)}）：截断扫描不支持整集资格，界面不排程。${cov.scope_note ?? ''}`);
    }
    const unjudgeable = UNJUDGEABLE_ANCHOR_LINES.map((key) => `${key}=${cov.anchor_lines?.[key] ?? '未报'}`).join('／');
    const unjudgeableCount = UNJUDGEABLE_ANCHOR_LINES.reduce((sum, key) => sum + (cov.anchor_lines?.[key] ?? 0), 0);
    const rejectedCount = REJECTED_ANCHOR_KEYS.reduce((sum, key) => sum + (cov.rejected_anchors?.[key] ?? 0), 0);
    if (unjudgeableCount + rejectedCount > 0) {
      reasons.push(`本次扫描里有无法判定时刻的锚点行被跳过（${unjudgeable}；身份/流/无 sample_id 排除 ${REJECTED_ANCHOR_KEYS.map((key) => `${key}=${cov.rejected_anchors?.[key] ?? 0}`).join('／')}）。18979 的整集资格只看扫描是否截断，并没有把这些行写进 blocking_reasons，所以界面不据该资格开放整集记录间隔播放：锚点序列在时间上是否有洞，这份 census 没有回答。空行（blank_lines_skipped=${text(cov.anchor_lines?.blank_lines_skipped)}）与预过滤行（prefiltered_lines_skipped=${text(cov.anchor_lines?.prefiltered_lines_skipped)}）属于 reader 自己声明的正常排除，不在此拒绝之列，也不把“任何计数非零”一律当成拒绝。`);
    }
    disclosures.push(`扫描：anchors_in_this_scan=${cov.anchors_in_this_scan} · unique_sample_ids=${cov.unique_sample_ids} · 行号范围 ${text(cov.first_anchor_line_index)}–${text(cov.last_anchor_line_index)} · 已读行 ${text(cov.anchor_lines?.lines_read)}（空行 ${text(cov.anchor_lines?.blank_lines_skipped)}／超限 ${text(cov.anchor_lines?.oversize_lines_skipped)}／坏行 ${text(cov.anchor_lines?.unparseable_lines_skipped)}／非对象 ${text(cov.anchor_lines?.non_object_lines_skipped)}／预过滤 ${text(cov.anchor_lines?.prefiltered_lines_skipped)}）`);
    // The scope clause is read straight after the census, before any base is chosen, so it may not depend on a
    // per-base eligibility row: the page's own filters narrow the frame page, never this judgement.
    disclosures.push(`范围口径：窗口与分页只筛帧页，这份 census 判定的是它自己那次锚点扫描（是否覆盖整个 Episode 由 coverage 的 whole_anchor_file_scanned／covers_whole_episode 自己说）。page_filter_context 回显本页条件（time_base=${text(cov.page_filter_context?.time_base)}／time_from=${text(cov.page_filter_context?.time_from)}／time_to=${text(cov.page_filter_context?.time_to)}／sample_id=${text(cov.page_filter_context?.sample_id)}／offset=${text(cov.page_filter_context?.offset)}／limit=${text(cov.page_filter_context?.limit)}／returned=${text(cov.page_filter_context?.returned)}），reader 自述：${cov.page_filter_context?.note ?? cov.scope_note ?? 'reader 未复述范围口径'}`);
  }
  const dupes = tq.identity?.duplicate_sample_id_groups ?? 0;
  if (dupes > 0) {
    disclosures.push(`重复 sample_id：${dupes} 组（${(tq.identity?.duplicates ?? []).slice(0, 3).map((d) => `${d.sample_id}×${d.occurrences}@[${d.line_indexes.join(',')}]`).join('；') || '未列出'}${tq.identity?.duplicates_truncated ? '，列表被截断' : ''}）。${tq.identity?.effect_on_this_route ?? ''} ${tq.identity?.effect_on_robot_state ?? ''}`);
  } else if (tq.identity) {
    disclosures.push(`重复 sample_id：${dupes} 组（every_anchor_position_is_reported=${text(tq.identity.every_anchor_position_is_reported)}）。${tq.identity.effect_on_robot_state ?? ''}`);
  }
  if (!row) reasons.push(`census 的 time_bases 里没有 ${base}（现有：${Object.keys(tq.time_bases ?? {}).join('、') || '空'}）：没有该基的记录数值就没有间隔可算。`);
  if (!eligibility) reasons.push(`census 的 recorded_interval_schedule.eligible_by_base 里没有 ${base} 的资格判定：界面不替 reader 宣布合格。`);
  if (eligibility && eligibility.eligible_for_whole_episode !== true) {
    reasons.push(`${base} 整集不合格（eligible_for_whole_episode=${String(eligibility.eligible_for_whole_episode)}）：blocking_reasons=${(eligibility.blocking_reasons ?? []).join('；') || 'reader 未列'}。`);
    const rules = tq.playback_eligibility?.recorded_interval_schedule?.rules_when_unqualified ?? {};
    (eligibility.blocking_reasons ?? []).forEach((reason) => {
      const hit = Object.entries(rules).find(([key]) => reason.includes(key));
      if (hit) reasons.push(`reader 对该情形的规则：${hit[1]}`);
    });
  }
  if (eligibility) {
    disclosures.push(`eligible_within_this_scan=${String(eligibility.eligible_within_this_scan)}：这是“本次扫描内”的判定，不是“当前时间窗口内”的资格——窗口只筛帧页，census 描述的是它自己那次锚点扫描（${cov?.page_filter_context?.note ?? cov?.scope_note ?? 'reader 未复述'}）。`);
    if (eligibility.zero_interval_ties_present) disclosures.push(`该基存在相等相邻值（zero_interval_ties_present=true）：按并列处理，不除零、不插值。`);
    disclosures.push(`implied_rate_hz_from_median_recorded_gap=${text(eligibility.implied_rate_hz_from_median_recorded_gap)} 只是本次扫描的中位数换算，${eligibility.implied_rate_note ?? '它不是记录者声明的速率，也不是播放保证'}——排程不使用中位数，只用相邻锚点的真实差值。`);
  }
  const never = tq.playback_eligibility?.recorded_interval_schedule?.never_assumed;
  if (never) disclosures.push(`never_assumed：default_rate_hz_applied=${text(never.default_rate_hz_applied)} · browser_arrival_time_used=${text(never.browser_arrival_time_used)} · clock_stitched_across_reset=${text(never.clock_stitched_across_reset)} · ${text(never.why)}`);
  const profile = tq.profile;
  if (profile) disclosures.push(`profile_ids_seen=${(profile.profile_ids_seen ?? []).join('、') || '无'} · 声明数值速率的锚点字段=${(profile.anchor_fields_declaring_a_numeric_rate ?? []).join('、') || '无'} · ${profile.note ?? ''}`);
  const cross = tq.playback_eligibility?.cross_stream_synchronized;
  if (cross) disclosures.push(`模式 C（跨流同刻）eligible=${String(cross.eligible)}：${cross.reason ?? 'reader 未说明'}（不由 A/B 推出：${(cross.not_derivable_from ?? []).join('、') || '未列'}）。`);
  return { ...gate, allowed: reasons.length === 0, reasons, disclosures };
}

/**
 * One step of the schedule: the real recorded difference between two adjacent anchors on the selected
 * base, divided by the speed factor. Equal values are ties (wait 0, never a division by zero), a negative
 * difference refuses that segment instead of sorting it away, and a missing or non-numeric value refuses
 * it instead of borrowing the neighbouring frame's clock.
 */
export function intervalStepOf(input: { from: FrameDto | null; to: FrameDto | null; base: string; speed: number; crossPage?: boolean; fromPosition?: number; toPosition?: number }): IntervalStep {
  const { from, to, base, speed } = input;
  const fromPosition = input.fromPosition ?? 0;
  const toPosition = input.toPosition ?? 0;
  const crossPage = Boolean(input.crossPage);
  const fromValue = from ? numeric(from.anchor.clocks?.[base]) : null;
  const toValue = to ? numeric(to.anchor.clocks?.[base]) : null;
  const voidStep = (kind: IntervalStep['kind'], note: string): IntervalStep =>
    ({ kind, fromPosition, toPosition, crossPage, fromValue, toValue, gapS: null, waitMs: null, note });
  if (!from || !to) return voidStep('missing', '相邻锚点不完整：本页或下一页没有可比较的锚点，界面不猜下一帧的时间。');
  if (fromValue === null || toValue === null) {
    return voidStep('missing', `该基在锚点 ${from.sample_id}/${to.sample_id} 上没有有限数值（anchor.clocks.${base}=${text(from.anchor.clocks?.[base])}→${text(to.anchor.clocks?.[base])}）：这一段不排程，帧仍按 reader 的追加顺序显示，不借用别的基或别的记录的钟。`);
  }
  const gapS = toValue - fromValue;
  if (gapS === 0) return { kind: 'tie', fromPosition, toPosition, crossPage, fromValue, toValue, gapS, waitMs: 0,
    note: `相邻两条记录在该基上相等（${fromValue}→${toValue}）：按并列处理，等待 0 ms，不除零、不插值、不算速率。` };
  if (gapS < 0) return { kind: 'backwards', fromPosition, toPosition, crossPage, fromValue, toValue, gapS, waitMs: null,
    note: `记录时间回退（${fromValue}→${toValue}，差 ${gapS}s）：一个连续钟没有被记录证明，界面拒绝这一段调度，不排序、不丢弃、不把它当 0。` };
  return { kind: 'interval', fromPosition, toPosition, crossPage, fromValue, toValue, gapS,
    waitMs: Math.max(0, Math.round((gapS * 1000) / speed)),
    note: `相邻锚点真实差 ${gapS}s ÷ 倍速 ${speed}× = ${Math.round((gapS * 1000) / speed)} ms 等待（浏览器单调钟只用于执行这段等待，不替代记录时间）。` };
}

/** The whole visible schedule of one page, plus the step that crosses into the next page. */
export function intervalScheduleOf(page: FramePageDto | null, base: string, speed: number): IntervalStep[] {
  const frames = page?.frames ?? [];
  const steps: IntervalStep[] = [];
  for (let position = 0; position + 1 < frames.length; position += 1) {
    steps.push({ ...intervalStepOf({ from: frames[position], to: frames[position + 1], base, speed }), fromPosition: position, toPosition: position + 1 });
  }
  return steps;
}

export interface RecordedRange {
  base: string; unit: string; present: boolean;
  pageFirst: number | null; pageLast: number | null; pageMin: number | null; pageMax: number | null;
  pageIncomplete: boolean;
  episodeScope: 'proven' | 'scan-only' | 'unknown';
  episodeFirst: number | null; episodeLast: number | null; episodeMin: number | null; episodeMax: number | null;
  windowFrom: number | null; windowTo: number | null; note: string;
}

/** Page range from the frames this page holds, Episode range from the census scan, window from the page's
 *  own echo — three different scopes, stated separately, with no total frame count anywhere.
 *
 *  The Episode-wide span is only claimed when the census's own coverage says the scan covered the whole
 *  anchor file; a truncated or absent scan keeps the same numbers but labels them as this scan, because a
 *  prefix of a file says nothing about the Episode's first and last recorded value. */
export function recordedRangeOf(page: FramePageDto | null, base: string, censusPage: FramePageDto | null = null): RecordedRange {
  const frames = page?.frames ?? [];
  const values = frames.map((frame) => numeric(frame.anchor.clocks?.[base])).filter((value): value is number => value !== null);
  const tq = censusPage?.time_quality ?? null;
  const row = tq?.time_bases?.[base] ?? page?.time_quality?.time_bases?.[base] ?? null;
  const cov = tq?.coverage ?? null;
  const episodeScope: RecordedRange['episodeScope'] = !row ? 'unknown'
    : (cov && cov.whole_anchor_file_scanned === true && cov.covers_whole_episode === true && cov.stopped_at_line_index === null) ? 'proven' : 'scan-only';
  const coverageWords = cov ? `whole_anchor_file_scanned=${String(cov.whole_anchor_file_scanned)}／covers_whole_episode=${String(cov.covers_whole_episode)}／stopped_at_line_index=${text(cov.stopped_at_line_index)}／anchor_limit=${text(cov.anchor_limit)}` : 'census 没有 coverage';
  return {
    base, unit: row?.unit ?? page?.time?.units?.['*_s'] ?? '—', present: values.length === frames.length && frames.length > 0,
    pageFirst: frames.length ? values.length === frames.length ? values[0] : null : null,
    pageLast: frames.length ? values.length === frames.length ? values[values.length - 1] : null : null,
    pageMin: values.length ? Math.min(...values) : null, pageMax: values.length ? Math.max(...values) : null,
    pageIncomplete: frames.length > values.length,
    episodeScope,
    episodeFirst: row?.first_in_file_order ?? null, episodeLast: row?.last_in_file_order ?? null,
    episodeMin: row?.min_recorded_value ?? null, episodeMax: row?.max_recorded_value ?? null,
    windowFrom: page?.time?.time_from ?? null, windowTo: page?.time?.time_to ?? null,
    note: episodeScope === 'proven'
      ? `整段范围来自 census 本次扫描（${row?.source_record ?? 'reader 未说明来源记录'}，${row?.description ?? 'reader 未描述该钟'}）：首/末 ${text(row?.first_in_file_order)}→${text(row?.last_in_file_order)}，最小/最大 ${text(row?.min_recorded_value)}/${text(row?.max_recorded_value)}，记录间隔 ${text(row?.recorded_gaps?.count)} 段（min ${text(row?.recorded_gaps?.min_s)}／max ${text(row?.recorded_gaps?.max_s)}s）。coverage 自述已扫完整份锚点文件，所以这可以是整个 Episode 的跨度——它不是本页，也不是当前窗口。`
      : episodeScope === 'scan-only'
        ? `这些数字只描述本次 census 扫描到的锚点段（${coverageWords}）：扫描没有覆盖整份锚点文件，界面不把它称作整个 Episode 的首末或最小最大，也不据此给出整集跨度。`
        : `整段范围未知（不猜）：${coverageWords}。本页读到 ${frames.length} 帧，其中 ${values.length} 帧带 ${base} 的有限数值。`,
  };
}

/** The cursor's page-local identity. A sample_id alone cannot name a row when one page repeats an id. */
export function framePositionKey(episodeId: string, runId: string | null, offset: number, position: number, frame: FrameDto | null): string {
  if (!frame) return `${episodeId}|${runId ?? ''}|none`;
  return `${episodeId}|${runId ?? ''}|${offset}+${position}|line ${frame.anchor.line_index}|${frame.sample_id}`;
}

/**
 * The anchor identity every history panel echoes for the one selection: page offset + page position plus the
 * anchor's own `line_index`. It is the same string in the state, time, media, curve and 3D panes, so a page
 * that repeats a `sample_id` still shows which concrete anchor each panel is answering for.
 */
export function anchorEchoKey(offset: number, position: number, frame: FrameDto | null): string {
  if (!frame) return 'none';
  return `${offset}+${position}|line ${frame.anchor.line_index}`;
}
