/**
 * episode-read-1 client and view projections. Every field name here is copied from the live
 * `unirobot-mobilecar-episode-read-1` payloads of the history candidate; nothing is invented, and a
 * value the reader did not return stays `null`/absent rather than being defaulted. This module owns
 * reads only: there is no write, validate, control or native passthrough call in it.
 */
import { ApiError, describeApiError, parseError } from './platform-config';

export const EPISODE_READ_SCHEMA = 'unirobot-mobilecar-episode-read-1';

/** `detail.time` names these bases; the reader rejects any other with 400 time_base_unsupported. */
export const KNOWN_TIME_BASES = ['wall_utc', 'backend_monotonic_s', 'sim_time_s', 'measurement_time_s', 'arrival_time_s'] as const;
export type TimeBase = (typeof KNOWN_TIME_BASES)[number];
/**
 * The reader answers numeric bounds on these bases only; `wall_utc` is a calendar string and it
 * answers 400 time_base_not_numeric. A page carries the authoritative list in
 * `time.numeric_time_bases`, so that value wins whenever the page is present.
 */
export const DECLARED_NUMERIC_BASES = ['backend_monotonic_s', 'sim_time_s', 'measurement_time_s', 'arrival_time_s'] as const;

export interface EpisodeSource {
  source_id: string; adapter_id: string; robot_id?: string; native_release_id?: string;
  native_contract_version?: string; recording_root: string; recording_root_resolved?: string;
  path_boundary?: string; access: string; platform_writes: boolean;
  declaring_instance?: { base_url: string; config_file?: string; recording_root_in_config?: string; access?: string };
  archive_baseline?: { scope?: string; files_hashed?: number; aggregate_sha256?: string; meaning?: string };
}
export interface EpisodePaging {
  limit: number; offset: number; returned: number; total_matches?: number; next_offset?: number | null;
  order?: string; declared_total_from_native_list?: number;
  scanned_lines?: number; skipped_before_offset?: number; has_more?: boolean;
}
export interface EpisodeListRow {
  run_id: string; episode_id: string; contract_version?: string;
  readable: boolean; read_error: string | null;
  task_language?: string | null; operator_id?: string | null; operator_kind?: string | null;
  view_source?: string | null; map_mode?: string | null;
  created_wall_utc?: string | null; ended_wall_utc?: string | null; segment_count?: number;
  declared?: { recording_status?: string | null; audit_status?: string | null; result?: string | null; termination_reason?: string | null; require_recording?: boolean | null };
  declaration_only?: boolean;
}
export interface EpisodeListDto {
  schema_version: string; read_only: boolean; source: EpisodeSource; retrieved_at: string;
  paging: EpisodePaging; filters: { run_id: string | null; recording_status: string | null; episode_id: string | null };
  episodes: EpisodeListRow[]; integrity_scope?: string; capability_limits?: string[];
}
export interface SegmentDto {
  recording_segment_id: string; previous_recording_segment_id: string | null; status?: string | null;
  reason?: string | null; started_wall_utc?: string | null; ended_wall_utc?: string | null;
  started_backend_monotonic_s?: number | null; termination_reason?: string | null;
}
export interface StreamDto {
  stream_id: string; relative_path: string; format: string; semantics?: string;
  available?: boolean; bytes?: number | null; records?: number | null;
  records_counted?: boolean; records_over_read_size_limit?: number | null;
  reason?: string; parse_error?: string | null; scan_truncated?: boolean;
}
export interface ChecksumEntryDto { relative_path: string; declared_sha256: string; actual_sha256?: string }
export interface AssetSampleDto { relative_path: string; bytes?: number; declared_sha256?: string | null }
export interface EpisodeDetailDto {
  schema_version: string; read_only: boolean; source: EpisodeSource; retrieved_at: string;
  identity: {
    source_id: string; adapter_id: string; recording_root?: string; recording_root_resolved?: string;
    run_id: string; episode_id: string;
    episode_directory?: string; native_contract_version?: string;
    backend_generation?: { available: boolean; reason: string | null; distinct_values?: (number | string)[] | null; values?: (number | string)[] | null; scope?: string };
    segments?: SegmentDto[]; episode_display_name_is_not_a_key?: boolean;
  };
  declared: {
    recording_status?: string | null; audit_status?: string | null; result?: string | null;
    task_result_source?: string | null; termination_reason?: string | null; require_recording?: boolean | null;
    complete_tail_file_present?: boolean | null; declared_checksum_entries?: number | null;
    episode_json_readable?: boolean | null; tail_json_readable?: boolean | null;
  };
  integrity: {
    status: string; scope?: string;
    this_read_evidence?: { episode_json_parsed?: boolean | null; tail_json_parsed?: boolean | null; episode_json_sha256?: string | null; tail_json_sha256?: string | null; files_recomputed_here?: string[] };
    checksum_verification?: { declared_entries?: number | null; matched?: ChecksumEntryDto[]; mismatched?: ChecksumEntryDto[]; verdict?: string | null; meaning?: string };
    not_verified?: string[]; declaration_is_not_verification?: boolean;
  };
  streams: StreamDto[];
  time: {
    record_order_is_native_append_order?: boolean; clocks_declared_by_run_manifest?: string[];
    available_time_bases?: Record<string, { available: boolean; time_bases_in_first_record?: string[] }>;
    units?: Record<string, string>; browser_arrival_order_is_not_used?: boolean; synchronized_across_streams: boolean;
  };
  action_semantics?: { recorded_target?: string[]; command_intent?: string[]; execution_feedback?: string[]; recorded_state?: string[]; lifecycle?: string[]; note?: string; categories_are_by_recorded_event_type?: boolean };
  recorded_model_identity?: { model_id?: string; model_sha256?: string; scene_id?: string; map_mode?: string; truth_access?: string; run_contract_version?: string; source?: string };
  three_d_replay: {
    status: string; recorded_model_sha256?: string | null; reference_model_sha256?: string | null;
    recorded_scene_id?: string | null; reference_scene_id?: string | null;
    model_match?: string | null; scene_match?: string | null; recorded_transforms_available?: boolean | null;
    live_geometry_or_actual_may_be_applied: boolean; reasons?: string[]; still_available?: string[];
  };
  platform_association: { known: boolean; validated_snapshot_ref: string | null; platform_session_id: string | null; reason?: string | null; policy?: string; source?: string; sidecar_error?: string | null };
  training_qualification?: { declared_eligibility_present?: boolean | null; training_qualified?: boolean | null; export_valid?: boolean | null; quality_report_present?: boolean | null; blocks_raw_read?: boolean; note?: string };
  media_summary?: {
    assets_root?: string; uri_convention?: string; declared_sha256_source?: string; verification?: string;
    symlink_or_escape_excluded?: boolean; excluded_count?: number;
    kinds?: Record<string, { count?: number; bytes_total?: number; sample?: AssetSampleDto[]; sample_truncated?: boolean; declared_sha256_coverage?: string }>;
  };
  capability_limits?: string[];
}
export interface EventSeqFilterDto {
  from: number | null; to: number | null; active: boolean; excluded_without_valid_event_seq: number;
  anomalies?: { line_index: number; reason: string; value_type: string }[];
}
export interface RecordPageDto {
  schema_version: string; read_only: boolean; source: EpisodeSource; retrieved_at: string;
  identity: { run_id: string; episode_id: string; native_contract_version?: string };
  stream: { stream_id: string; relative_path: string; format: string; semantics?: string; file_bytes?: number | null };
  paging: EpisodePaging;
  cursor: { order?: string; first_line_index?: number | null; last_line_index?: number | null; first_event_seq?: number | null; last_event_seq?: number | null; line_index_is_not_a_clock: boolean };
  time: { selected_time_base: string | null; time_from?: number | null; time_to?: number | null; units?: string; records_without_the_selected_base?: number | null; numeric_time_bases?: string[]; synchronized_across_streams: boolean };
  filtering?: { event_seq_range?: EventSeqFilterDto; note?: string };
  records: { line_index: number; record: Record<string, unknown> }[];
  integrity: {
    corrupt_lines?: { line_index: number; error?: string; column?: number }[];
    lines_over_read_size_limit?: number[];
    declared_status?: { recording_status?: string | null; audit_status?: string | null; termination_reason?: string | null; declaration_only?: boolean };
    scope?: string; not_verified?: string[];
  };
}

/** Reads only. The six GET paths of the history candidates, exactly the ones they declare. */
export class PlatformEpisodeApi {
  async listEpisodes(params: { limit?: number; offset?: number; run_id?: string; recording_status?: string; episode_id?: string }, signal: AbortSignal) {
    return json<EpisodeListDto>(`/api/v1/episodes${query(params)}`, signal, EPISODE_READ_SCHEMA);
  }
  async getEpisode(episodeId: string, runId: string | null, signal: AbortSignal) {
    return json<EpisodeDetailDto>(`/api/v1/episodes/${enc(episodeId)}${runId ? `?run_id=${enc(runId)}` : ''}`, signal, EPISODE_READ_SCHEMA);
  }
  async listStreams(episodeId: string, runId: string | null, signal: AbortSignal) {
    return json<EpisodeDetailDto | StreamPageDto>(`/api/v1/episodes/${enc(episodeId)}/streams${runId ? `?run_id=${enc(runId)}` : ''}`, signal, EPISODE_READ_SCHEMA);
  }
  async readRecords(input: { episodeId: string; runId: string | null; streamId: string; limit?: number; offset?: number; eventSeqFrom?: number; eventSeqTo?: number; timeBase?: string; timeFrom?: number; timeTo?: number }, signal: AbortSignal) {
    const params: Record<string, string | number> = {};
    if (input.runId) params.run_id = input.runId;
    if (input.limit !== undefined) params.limit = input.limit;
    if (input.offset !== undefined) params.offset = input.offset;
    if (input.eventSeqFrom !== undefined) params.event_seq_from = input.eventSeqFrom;
    if (input.eventSeqTo !== undefined) params.event_seq_to = input.eventSeqTo;
    if (input.timeBase) params.time_base = input.timeBase;
    if (input.timeFrom !== undefined) params.time_from = input.timeFrom;
    if (input.timeTo !== undefined) params.time_to = input.timeTo;
    return json<RecordPageDto>(`/api/v1/episodes/${enc(input.episodeId)}/streams/${enc(input.streamId)}/records${query(params)}`, signal, EPISODE_READ_SCHEMA);
  }
  /** Media bytes. `sha256` makes the server verify before it returns anything. */
  async asset(episodeId: string, runId: string | null, assetPath: string, sha256: string | null, signal: AbortSignal) {
    const params: Record<string, string> = {};
    if (runId) params.run_id = runId;
    if (sha256) params.sha256 = sha256;
    const response = await fetch(`/api/v1/episodes/${enc(episodeId)}/assets/${assetPath.split('/').map(enc).join('/')}${query(params)}`, { method: 'GET', signal, cache: 'no-store' });
    const body = await response.arrayBuffer();
    if (!response.ok) throw parseError(response.status, response.statusText, await errorBody(body));
    return { bytes: body, mediaType: response.headers.get('content-type') ?? '', assetSha256: response.headers.get('x-episode-asset-sha256') ?? '', runHeader: response.headers.get('x-episode-run-id') ?? '' };
  }
}
export interface StreamPageDto {
  schema_version: string; read_only: boolean; source: EpisodeSource; retrieved_at: string;
  identity: { source_id: string; adapter_id: string; recording_root?: string; run_id: string; episode_id: string; episode_directory?: string; native_contract_version?: string };
  declared_status: { recording_status?: string | null; audit_status?: string | null; termination_reason?: string | null; declaration_only?: boolean };
  streams: StreamDto[]; media_summary?: EpisodeDetailDto['media_summary']; capability_limits?: string[];
}

async function errorBody(buffer: ArrayBuffer) {
  try { return JSON.parse(new TextDecoder().decode(buffer)); } catch { return null; }
}
/** Exported so the frame-link-1 client shares exactly one schema gate: no payload is rendered optimistically. */
export async function json<T>(path: string, signal: AbortSignal, expectSchema: string): Promise<T> {
  const response = await fetch(path, { method: 'GET', signal, cache: 'no-store', headers: { Accept: 'application/json' } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw parseError(response.status, response.statusText, body);
  const value = body as { schema_version?: string; read_only?: boolean } | null;
  if (!value || value.schema_version !== expectSchema) throw new EpisodeContractError(`响应不是 ${expectSchema}`, value?.schema_version ?? 'missing');
  if (value.read_only !== true) throw new EpisodeContractError('历史读取响应未声明 read_only=true', String((value as { read_only?: unknown }).read_only));
  return body as T;
}
/** A payload that is not the declared read contract is a finding, not something to render optimistically. */
export class EpisodeContractError extends Error {
  constructor(message: string, public readonly found: string) { super(`${message}（实际 schema_version=${found}）`); this.name = 'EpisodeContractError'; }
}
const enc = (value: string) => encodeURIComponent(value);
export function query(params: Record<string, string | number | undefined>) {
  const parts: string[] = [];
  Object.entries(params).forEach(([key, value]) => { if (value !== undefined && value !== '') parts.push(`${key}=${enc(String(value))}`); });
  return parts.length ? `?${parts.join('&')}` : '';
}

// ---- view projections ---------------------------------------------------------------------------

export type Tone = 'ok' | 'bad' | 'unknown';
export interface Facet { key: string; label: string; tone: Tone; value: string; note: string }

/** The five integrity layers stay separate; the function never collapses them into one verdict. */
export function integrityFacets(detail: EpisodeDetailDto): Facet[] {
  const declared = detail.declared ?? {};
  const integrity = detail.integrity ?? {};
  const check = integrity.checksum_verification ?? {};
  const mismatched = check.mismatched ?? [];
  const matched = check.matched ?? [];
  const recomputed = integrity.this_read_evidence?.files_recomputed_here ?? [];
  const tailPresent = declared.complete_tail_file_present;
  const finding = checksumFinding(detail);
  return [
    { key: 'declared', label: '录制声明（record 自身写的）', tone: 'unknown',
      value: `recording_status=${text(declared.recording_status)} · audit_status=${text(declared.audit_status)} · result=${text(declared.result)} · termination_reason=${text(declared.termination_reason)}`,
      note: `声明的 checksum 条目 ${text(declared.declared_checksum_entries)}；require_recording=${text(declared.require_recording)}；episode.json 可读=${text(declared.episode_json_readable)}；tail 可读=${text(declared.tail_json_readable)}。声明只是 record 的自述，不是本次验证。` },
    { key: 'lifecycle', label: '本次读取的生命周期闭合状态', tone: integrity.status === 'complete' ? 'ok' : integrity.status === 'unknown' ? 'unknown' : 'bad',
      value: `integrity.status=${text(integrity.status)}`,
      note: `${text(integrity.scope)}；词表只描述终态是否闭合（complete / incomplete_terminal_recorded / finalize_failed_missing_tail / unknown），不等于内容已验证。` },
    { key: 'tail', label: 'tail 文件存在性', tone: tailPresent === true ? 'ok' : tailPresent === false ? 'bad' : 'unknown',
      value: `complete_tail_file_present=${text(tailPresent)}`,
      note: '尾标记存在只说明尾部文件在，不推出录制完整，也不推出内容正确。' },
    { key: 'checksum', label: '本次重算校验明细', tone: mismatched.length ? 'bad' : matched.length && recomputed.length ? 'ok' : 'unknown',
      value: finding.verdictText,
      note: finding.note },
    { key: 'uncovered', label: '本切片未覆盖的范围', tone: 'unknown',
      value: `${(integrity.not_verified ?? []).length} 项未验证`,
      note: (integrity.not_verified ?? []).join(' · ') || 'reader 未声明未覆盖范围（不能因此假定已全覆盖）' },
  ];
}
/**
 * The backend documents one known cause (the recorder writes the tail before finalising
 * episode.json), but that explanation is only allowed when the mismatch is confined to those
 * lifecycle files on a record declared COMPLETE. Anything else is reported without a cause.
 */
export function checksumFinding(detail: EpisodeDetailDto): { verdict: string; verdictText: string; note: string; pattern: 'known_stale_self_check' | 'unexplained' | 'verified' | 'none'; mismatched: ChecksumEntryDto[]; allCompleteClaimForbidden: true } {
  const check = detail.integrity?.checksum_verification ?? {};
  const mismatched = check.mismatched ?? [];
  const matched = check.matched ?? [];
  const declaredEntries = check.declared_entries ?? null;
  const recomputed = detail.integrity?.this_read_evidence?.files_recomputed_here ?? [];
  const verdict = text(check.verdict);
  const scopeNote = `tail 声明 ${text(declaredEntries)} 条摘要，本次只重算了 ${recomputed.length ? recomputed.join(', ') : '（无文件）'}；matched=${matched.length} mismatched=${mismatched.length}。`;
  if (verdict === 'none' || (!mismatched.length && !matched.length)) {
    return { verdict, verdictText: `本次未重算出可比对的条目（verdict=${verdict || '未声明'}）`, note: `${scopeNote}不能称任何文件已验证。`, pattern: 'none', mismatched, allCompleteClaimForbidden: true };
  }
  if (!mismatched.length) {
    return { verdict, verdictText: `本次重算的 ${matched.length} 个文件与声明一致（verdict=${verdict}）`, note: `${scopeNote}一致只覆盖列出的文件。`, pattern: 'verified', mismatched, allCompleteClaimForbidden: true };
  }
  const confinedToLifecycleFiles = mismatched.every((entry) => entry.relative_path === 'episode.json' || entry.relative_path === 'episode_complete.json');
  const known = confinedToLifecycleFiles && detail.declared?.recording_status === 'COMPLETE';
  const detailText = mismatched.map((entry) => `${entry.relative_path}: 声明 ${short(entry.declared_sha256)} · 本次 ${short(entry.actual_sha256 ?? '未返回')}`).join('；');
  return {
    verdict,
    verdictText: `发现 ${mismatched.length} 条与声明不符（verdict=${verdict}）— 不得读作“全部完整”`,
    note: `${scopeNote}${detailText}。${known
      ? '这与后端记录的过期自校验模式一致（recorder 先写 tail、后定稿 episode.json，tail 内保存的是定稿前的摘要）；仍是推断级说明，未改写记录、不称已验证。'
      : '不符范围超出该已知过期自校验模式，原因未证明，不归因于同一历史问题。'}${text(check.meaning) ? ` 原文：${check.meaning}` : ''}`,
    pattern: known ? 'known_stale_self_check' : 'unexplained', mismatched, allCompleteClaimForbidden: true,
  };
}

export interface StreamView { streamId: string; relativePath: string; format: string; available: boolean; bytes: number | null; records: number | null; recordsOverLimit: number | null; semantics: string; declaredBases: string[] | null; reason: string | null; parseError: string | null; scanTruncated: boolean }
export function streamViews(payload: StreamPageDto | EpisodeDetailDto): StreamView[] {
  const declared = (payload as EpisodeDetailDto).time?.available_time_bases;
  return (payload.streams ?? []).map((s) => ({
    streamId: s.stream_id, relativePath: s.relative_path, format: s.format,
    available: s.available !== false, bytes: s.bytes ?? null, records: s.records ?? null,
    recordsOverLimit: s.records_over_read_size_limit ?? null, semantics: s.semantics ?? '',
    reason: s.reason ?? null, parseError: s.parse_error ?? null, scanTruncated: s.scan_truncated === true,
    declaredBases: declared?.[s.stream_id]?.available ? declared?.[s.stream_id]?.time_bases_in_first_record ?? [] : null,
  }));
}

export interface TimeField { base: string; present: boolean; display: string; unit: string; clockId: string | null }
/** A record without the selected base reads as missing; it is never padded to 0 and never re-timed. */
export function timeFieldOf(record: Record<string, unknown>, base: string): TimeField {
  const raw = record[base];
  const clock = typeof record.clock_id === 'string' ? record.clock_id : null;
  if (raw === undefined || raw === null) return { base, present: false, display: `此记录无 ${base} 字段`, unit: '—', clockId: clock };
  if (base === 'wall_utc') return { base, present: true, display: String(raw), unit: 'ISO-8601 Z（UTC）', clockId: clock };
  if (typeof raw !== 'number') return { base, present: false, display: `此记录的 ${base} 不是数值（${typeof raw}），不显示为时间`, unit: '—', clockId: clock };
  return { base, present: true, display: raw.toFixed(6), unit: base.endsWith('_ms') ? '毫秒' : base.endsWith('_s') ? '秒' : '未声明单位', clockId: clock };
}
export function unitOf(base: string) { return base === 'wall_utc' ? 'ISO-8601 Z（UTC）' : base.endsWith('_ms') ? '毫秒' : base.endsWith('_s') ? '秒' : '未声明单位'; }
/** The reader's own answer about which bases accept numeric bounds. An explicit empty array is a
 *  statement, not a missing one: once a page has answered, that answer is authoritative and the
 *  declared set is only used before any page exists. Falling back after `[]` would let the view
 *  offer bounds the reader just said it does not accept. */
export function numericBasesOf(page: RecordPageDto | null): string[] {
  const declared = page?.time?.numeric_time_bases;
  if (Array.isArray(declared)) return declared;
  return [...DECLARED_NUMERIC_BASES];
}
/**
 * Whether the current selection can seek numerically. The reason text is what the view shows, so a
 * non-numeric base is refused with the reader's list instead of an invented calendar format.
 */
export function seekGate(page: RecordPageDto | null, base: string): { allowed: boolean; reason: string; numericBases: string[] } {
  const numeric = numericBasesOf(page);
  if (!base) return { allowed: false, reason: '该流没有已声明的命名时间基：不能按时间定位（行号不是时间）。', numericBases: numeric };
  if (!numeric.includes(base)) {
    return { allowed: false, reason: `${base} 不是该 reader 接受的数值时间基（numeric_time_bases=${numeric.join(', ') || '空'}）：日历字符串的区间格式未在契约中声明，界面不猜格式。`, numericBases: numeric };
  }
  return { allowed: true, reason: '', numericBases: numeric };
}
/** Parse the seek box without ever turning a blank into 0. */
export function parseSeekValue(text: string): { value: number | null; error: string | null } {
  const trimmed = text.trim();
  if (!trimmed) return { value: null, error: '定位值为空：不发送请求。要定位到 0 请显式输入 0。' };
  const value = Number(trimmed);
  if (!Number.isFinite(value)) return { value: null, error: `定位值必须是数值（当前 ${trimmed.slice(0, 24)} 不是有限数值）：不发送请求，也不代替为 0。` };
  return { value, error: null };
}
export type PageKind = 'records' | 'filtered-out-without-event-seq' | 'window-empty' | 'offset-past-end' | 'unavailable';
/**
 * An empty page is not one statement. Under an active event_seq range the reader says the stream
 * legitimately has no such field (observations-index/persist/transforms) and counts the excluded
 * lines; that is a successful read, not a load failure.
 */
export function pageKind(page: RecordPageDto | null): PageKind {
  if (!page) return 'unavailable';
  if (page.records.length) return 'records';
  const range = page.filtering?.event_seq_range;
  if (range?.active && range.excluded_without_valid_event_seq > 0) return 'filtered-out-without-event-seq';
  if (range?.active) return 'window-empty';
  return 'offset-past-end';
}
export function pageExplanation(page: RecordPageDto): string {
  const range = page.filtering?.event_seq_range;
  const scanned = text(page.paging.scanned_lines);
  switch (pageKind(page)) {
    case 'filtered-out-without-event-seq':
      return `event_seq 区间 ${text(range?.from)}–${text(range?.to)} 内没有合格记录：该流合法地没有 event_seq（原生 SensorObservation 不带该字段，persist 用 persist_sequence），${range?.excluded_without_valid_event_seq} 行因缺失/非整数/布尔被排除并计数（anomalies 示例 ${range?.anomalies?.length ?? 0} 条），不补造序号，也不判为读取失败。扫描行数 ${scanned}。`;
    case 'window-empty':
      return `event_seq 区间 ${text(range?.from)}–${text(range?.to)} 内没有匹配行（排除计数 ${text(range?.excluded_without_valid_event_seq)}，扫描 ${scanned} 行）：这是空结果页，不是错误。`;
    case 'offset-past-end':
      return `offset=${page.paging.offset} 之后没有返回记录（扫描 ${scanned} 行，has_more=${text(page.paging.has_more)}）：到数据末尾或 offset 越过末尾，不推断录制结束。`;
    default:
      return `本页返回 ${page.records.length} 条记录（扫描 ${scanned} 行）。`;
  }
}
/** Which bases this page can actually seek on: the record's own fields, not an assumed clock. */
export function presentTimeBases(records: Record<string, unknown>[]): string[] {
  const found = new Set<string>();
  records.forEach((record) => KNOWN_TIME_BASES.forEach((base) => { if (record[base] !== undefined && record[base] !== null) found.add(base); }));
  return [...found];
}

export interface MediaRef { uri: string; kind: string; role: 'primary' | 'rgb' | 'depth' | 'valid_mask'; field: string; sampleId: string | null; declaredSha256: string | null; declaredShaSource: string; autoLoad: boolean }
/**
 * Media comes only from reference fields the record itself carries. The archive uses two shapes:
 * `observations-index` writes `asset_uri` (null for sensors with no asset), while
 * `observations-persist` writes `rgb_uri` / `depth_uri` / `valid_mask_uri` and no `asset_uri` at
 * all. Nothing here synthesises a path from a sample id.
 */
const MEDIA_FIELDS: [string, MediaRef['role'], boolean][] = [
  ['asset_uri', 'primary', true], ['rgb_uri', 'rgb', true], ['depth_uri', 'depth', false], ['valid_mask_uri', 'valid_mask', false],
];
const DECLARED_SHA_FIELDS: Record<string, string> = { asset_uri: 'asset_sha256', rgb_uri: 'rgb_sha256', depth_uri: 'depth_sha256', valid_mask_uri: 'valid_mask_sha256' };
export function mediaRefsOf(record: Record<string, unknown>, payload: StreamPageDto | EpisodeDetailDto | null): MediaRef[] {
  const sampleId = typeof record.sample_id === 'string' ? record.sample_id : null;
  const refs: MediaRef[] = [];
  MEDIA_FIELDS.forEach(([field, role, autoLoad]) => {
    const uri = record[field];
    if (typeof uri !== 'string' || !uri) return;
    const fromRecord = typeof record[DECLARED_SHA_FIELDS[field]] === 'string' ? String(record[DECLARED_SHA_FIELDS[field]]) : null;
    const fromSummary = declaredDigestOf(payload, uri);
    refs.push({
      uri, kind: kindOf(uri), role, field, sampleId, autoLoad,
      declaredSha256: fromRecord ?? fromSummary,
      declaredShaSource: fromRecord ? `记录自带 ${DECLARED_SHA_FIELDS[field]}` : fromSummary ? 'media_summary 样本清单' : '本条无声明摘要',
    });
  });
  return refs;
}
/** The reference the cursor loads by default: the record's own primary image, never another record's. */
export function autoLoadRef(refs: MediaRef[]): MediaRef | null { return refs.find((ref) => ref.autoLoad) ?? null; }
function kindOf(uri: string) { const parts = uri.split('/'); return parts.length >= 2 ? parts[parts.length - 2] : 'asset'; }
export function declaredDigestOf(payload: StreamPageDto | EpisodeDetailDto | null, uri: string): string | null {
  const kinds = payload?.media_summary?.kinds ?? {};
  for (const kind of Object.keys(kinds)) {
    const hit = (kinds[kind]?.sample ?? []).find((sample) => sample.relative_path === uri);
    if (hit?.declared_sha256) return hit.declared_sha256;
  }
  return null;
}

/** Event classes come from the record's own type, matched against detail.action_semantics. */
export function actionClassOf(eventType: string | null, semantics: EpisodeDetailDto['action_semantics']): { cls: string; note: string } {
  if (!eventType) return { cls: 'unknown', note: '记录没有 event_type，不推断动作类别' };
  const maps: [string, string[] | undefined][] = [
    ['recorded_target', semantics?.recorded_target], ['command_intent', semantics?.command_intent],
    ['execution_feedback', semantics?.execution_feedback], ['recorded_state', semantics?.recorded_state],
    ['lifecycle', semantics?.lifecycle],
  ];
  const hit = maps.find(([, list]) => (list ?? []).includes(eventType));
  if (hit) return { cls: hit[0], note: `record 的 event_type=${eventType} 属于 reader 声明的 ${hit[0]} 类` };
  return { cls: 'other_recorded_event', note: `event_type=${eventType} 不在 reader 声明的动作类别里；只按原文显示，不归类为 Target 或 Actual` };
}

export interface RowView { runId: string; episodeId: string; identityText: string; readable: boolean; readError: string | null; declaredStatus: string; auditStatus: string; result: string; created: string; ended: string; segments: string; title: string; operator: string; mapMode: string }
/** An empty page under a filter is not the same statement as an archive with nothing readable in it. */
export function emptyListKind(dto: EpisodeListDto): 'no-match' | 'no-records' {
  const filters = dto.filters ?? { run_id: null, recording_status: null, episode_id: null };
  return filters.run_id || filters.recording_status || filters.episode_id ? 'no-match' : 'no-records';
}
export function rowViews(dto: EpisodeListDto): RowView[] {
  return dto.episodes.map((row) => ({
    runId: row.run_id, episodeId: row.episode_id,
    identityText: `${dto.source.source_id} · ${row.run_id} · ${row.episode_id}`,
    readable: row.readable !== false, readError: row.read_error ?? null,
    declaredStatus: text(row.declared?.recording_status), auditStatus: text(row.declared?.audit_status), result: text(row.declared?.result),
    created: text(row.created_wall_utc), ended: text(row.ended_wall_utc), segments: text(row.segment_count),
    title: row.task_language ?? '（无 task_language）', operator: `${text(row.operator_id)}/${text(row.operator_kind)}/${text(row.view_source)}`, mapMode: text(row.map_mode),
  }));
}

const CODE_HINTS: Record<string, string> = {
  episode_not_found: '该身份在本 source 下没有 Episode 目录',
  episode_id_invalid: 'episode_id 不符合 reader 接受的身份字符集，未打开任何目录',
  run_id_invalid: 'run_id 不符合 reader 接受的身份字符集，未打开任何目录',
  episode_id_ambiguous: '同一 episode_id 出现在多个 run 下：显示名不是唯一键，必须带 run_id 才能读',
  episode_stream_unsupported: '该 stream 不由 reader 提供（supported 见响应）',
  episode_stream_unavailable: '该流名受支持但此记录没有对应文件：按缺失显示，不生成替代内容',
  time_base_unsupported: '该时间基不是记录声明的命名时间基（supported 见响应）',
  time_base_not_numeric: '该时间基是日历字符串，不接受数值区间：改用响应列出的数值基，界面不猜日历格式',
  time_range_required: '给了 time_base 就必须给 time_from 或 time_to',
  sample_id_invalid: 'sample_id 不是原生 id token（frame-link-1 拒绝含非法字符的 id，未扫描归档）',
  episode_asset_path_invalid: '资产路径必须是该 Episode 内的相对路径',
  episode_asset_missing: '该媒体在记录中不存在',
  episode_asset_escape: '解析后的路径离开了允许的范围，拒绝读取',
  episode_path_escape: 'Episode 目录解析后不在声明的 recording_root 内，拒绝读取',
  episode_asset_type_unsupported: '该后缀不在 reader 提供的类型内',
  episode_asset_too_large: '资产超过单文件读取上限',
  episode_asset_digest_mismatch: '服务端重算摘要与请求声明的 sha256 不符，字节未返回',
  history_path_escape: 'Episode/manifest 路径不在声明的 recording_root 内',
  history_source_invalid: '平台侧历史来源配置无效（500），未打开任何归档',
  history_source_unavailable: '平台侧历史来源不可用（503）',
  history_source_not_configured: '该候选未配置历史来源：没有 episode 读取路径可用',
  episode_record_corrupt: 'reader 无法解析该记录页（502），界面不显示部分结果',
  validation_error: '参数超出 reader 允许的边界（如 limit>200、offset<0、sha256 非 64 位小写十六进制），请求未被执行',
  gateway_unavailable: '只读代理无法连接上游：本地拒绝，未转发',
};
/** Codes are shown with the server's own words; supported lists are echoed from the payload. */
export function describeHistoryError(cause: unknown): string {
  if (cause instanceof EpisodeContractError) return cause.message;
  if (!(cause instanceof ApiError)) return describeApiError(cause);
  const detail = cause.detail as Record<string, unknown> | null;
  const supported = Array.isArray(detail?.supported) ? ` · supported=${(detail?.supported as unknown[]).join(',')}` : '';
  const runs = Array.isArray(detail?.runs) ? ` · 候选 run=${(detail?.runs as unknown[]).join(',')}` : '';
  const numeric = Array.isArray(detail?.numeric_bases) ? ` · numeric_bases=${(detail?.numeric_bases as unknown[]).join(',')}` : '';
  const actual = typeof detail?.actual === 'string' ? ` · 实际摘要 ${short(detail.actual)}` : '';
  const expected = typeof detail?.expected === 'string' ? ` · 声明摘要 ${short(detail.expected)}` : '';
  const suffix = typeof detail?.suffix === 'string' ? ` · 后缀 ${detail.suffix}` : '';
  const relative = typeof detail?.relative_path === 'string' ? ` · 路径 ${detail.relative_path}` : '';
  return `${cause.code} · ${cause.message}${supported}${runs}${numeric}${actual}${expected}${suffix}${relative}${CODE_HINTS[cause.code] ? ` · ${CODE_HINTS[cause.code]}` : ''}`;
}
export function isAmbiguous(cause: unknown) { return cause instanceof ApiError && cause.code === 'episode_id_ambiguous'; }
export function ambiguousRuns(cause: unknown): string[] {
  if (!(cause instanceof ApiError) || !Array.isArray((cause.detail as Record<string, unknown> | null)?.runs)) return [];
  return ((cause.detail as Record<string, unknown>).runs as unknown[]).map(String);
}
/** The page never asks the reader to re-derive state: there is no validate call in this module. */
export function threeDNotice(detail: EpisodeDetailDto): { status: string; text: string; blocked: true } {
  const replay = detail.three_d_replay;
  const applied = replay.live_geometry_or_actual_may_be_applied;
  const reasons = (replay.reasons ?? []).join(' ');
  return {
    status: replay.status, blocked: true,
    text: `three_d_replay.status=${replay.status} · model ${text(replay.model_match)} / scene ${text(replay.scene_match)}（recorded ${short(replay.recorded_model_sha256)} vs reference ${short(replay.reference_model_sha256)}）；`
      + `recorded_transforms_available=${text(replay.recorded_transforms_available)}。身份摘要匹配不等于渲染正确性已验证，`
      + `live_geometry_or_actual_may_be_applied=${text(applied)}：本切片不套在线 geometry、Actual 或当前世界姿态，也不声称同步 3D 回放可用。`
      + '后端已更正 transforms 的语义：它是带 frame/时钟标记的变换观测，不是逐 body 位姿序列，因此不能据此复原历史姿态。'
      + `${replay.still_available?.length ? ` 仍可提供：${replay.still_available.join('、')}。` : ''}${reasons ? ` 服务端原文：${reasons}` : ''}`,
  };
}
export function trainingNotice(detail: EpisodeDetailDto): string {
  const q = detail.training_qualification ?? {};
  return `declared_eligibility_present=${text(q.declared_eligibility_present)} · training_qualified=${text(q.training_qualified)} · export_valid=${text(q.export_valid)} · quality_report_present=${text(q.quality_report_present)} · blocks_raw_read=${text(q.blocks_raw_read)}；${q.note ?? 'reader 未说明资格与读取的关系'}`;
}
export function associationNotice(detail: EpisodeDetailDto): string {
  const a = detail.platform_association ?? {};
  return `platform_association.known=${text(a.known)} · validated_snapshot_ref=${text(a.validated_snapshot_ref ?? null)} · platform_session_id=${text(a.platform_session_id ?? null)} · reason=${text(a.reason)} · 依据=${text(a.source)}${a.sidecar_error ? ` · sidecar 读取错误=${a.sidecar_error}` : ''}；${a.policy ?? 'reader 未声明关联策略'}`;
}
const text = (value: unknown) => value === undefined || value === null || value === '' ? 'null' : String(value);
const short = (value: string | null | undefined) => !value ? 'null' : value.length > 16 ? `${value.slice(0, 12)}…` : value;
