import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { EpisodeContractError } from '../src/adapters/platform-episodes';
import {
  FRAME_LINK_SCHEMA, ambiguousRoleCount, clockSamenessText, frameAutoLoadRef, frameBoundaryNotice, frameMediaRefs,
  framePageExplanation, framePageKind, frameSelectableBases, frameStopNote, frameWindowGate, linkageScopeText,
  mediaDeclarationText, provenanceRowsOf, quantityRowsOf, readFramesPage, recorderDeclaredOf, roleCoverageText,
  roleRowsOf, selectionRulesText, stateQuantityKeysOf, stateRowsOf, stateSelectionOf, statusPrecedenceText,
  timeSemanticsText, versionMigrationText,
  type FrameDto, type FramePageDto,
} from '../src/adapters/platform-frames';

// The fixtures are shape copies of the `unirobot-mobilecar-frame-link-2` payloads the candidate on
// 18969 actually answered on 2026-10-26 (COMPLETE record page 1, the FAILED record page, the
// sample-filter page at offset=100, and the ambiguity/empty shapes of the isolated fixtures). Only
// fields the reader returned are present; nothing is padded to make a test easier.
const RUN = 'run_0104613ff7364ae78cf2f3946bd45f7b';
const EPISODE = 'episode_27bfed5427684795b361cd2ec21e9aa7';
const SAMPLE = 'rgbd_e3213e6cb64b4cd693c17d485d064d09';
const SOURCE = {
  source_id: 'mobilecar-server-history-20261017', adapter_id: 'mobilecar', robot_id: 'landerpi',
  native_release_id: 'drvfix-20261019T044549Z-0a80415b2577', native_contract_version: 'mobilecar-1.0',
  recording_root: '/home/liaozhengyan/Desktop/mobileCar/var/runs', recording_root_resolved: '/home/liaozhengyan/Desktop/mobileCar/var/runs',
  access: 'read_only_files', platform_writes: false,
  path_boundary: 'every derived path is re-resolved and must stay inside the declared root',
};
const PAGING = {
  limit: 3, offset: 0, returned: 3, has_more: true, next_offset: 3, next_qualifying_anchor_line_index: 3,
  offset_semantics: 'next_offset is the raw line index after the last returned anchor in the anchor file',
  skipped_before_offset: 0, excluded_anchor_identity_mismatch: 0, excluded_stream_mismatch: 0,
  excluded_without_sample_id: 0, excluded_by_sample_id_filter: 0, excluded_outside_time_window: 0,
  records_missing_selected_time_base: 0, anchor_records_examined: 4, post_page_records_examined: 1,
  anchor_lines: { lines_read: 4, blank_lines_skipped: 0, oversize_lines_skipped: 0, unparseable_lines_skipped: 0, non_object_lines_skipped: 0, prefiltered_lines_skipped: 0 },
  scan: { whole_file_scanned: false, stopped_after_full_page_at_line_index: 3, note: 'a full page stops at the first further qualifying anchor' },
};
const quantity = (key: string, extra: Record<string, unknown> = {}) => ({
  key, source_record: 'events state feedback envelope', field: 'backend_monotonic_s', relative_to: 'persisted frame capture_backend_monotonic_s',
  unit: 's', clock: 'named backend_monotonic by the record', meaning: 'fixture meaning', capture_value: 426494.351568496,
  other_value: 426494.348683089, value: -0.0028854069532826543, abs_ms: 2.8854069532826543, direction: 'earlier', line_index: 27, ...extra,
});
const frameFixture = (patch: Partial<FrameDto> = {}): FrameDto => ({
  sample_id: SAMPLE, stream_id: 'rgbd',
  anchor: {
    line_index: 0, relative_path: 'observations/persist.jsonl', persist_sequence: 1,
    identity: { run_id_matches: true, episode_id_matches: true, declared_run_id: RUN, declared_episode_id: EPISODE },
    clocks: { capture_backend_monotonic_s: 426494.351568496, capture_sim_time_s: 0.14, persist_backend_monotonic_s: 426494.451593934, arrival_backend_monotonic_s: 426494.385019665, arrival_to_persist_ms: 66.5742689743638, capture_to_persist_ms: 100.02543800510466 },
    declared_keys: ['capture_backend_monotonic_s', 'depth_uri', 'feedback_sample_id', 'rgb_uri', 'sample_id'],
    reference_keys: { capture_control_tick_id: 'tick_000006551', feedback_sample_id: 'joint_feedback_000006551' },
    profile: { profile_id: 'g2a-rgbd-5hz-original', profile_version: '1.0', profile_sha256: '9'.repeat(64), interface_profile: 'g2a-1.0', kinds: ['rgb', 'depth'] },
  },
  linkage_status: 'matched', primary_roles_matched: ['image_observation', 'camera_transform', 'capture_timing_event', 'state_feedback_event'],
  primary_roles_ambiguous: [], declared_reference_status: 'unresolved_reference',
  media: {
    declared_by: 'the persisted frame record and its observation rows, copied verbatim',
    uri_convention: 'assets/<kind>/<file>, served only from this episode’s assets tree',
    digest_verification: 'declared only; recomputed when the asset endpoint serves the file',
    duplicate_row_rule: 'every candidate row for the kind is listed; none is silently chosen',
    items: [
      { field: 'rgb_uri', uri: `assets/rgb/${SAMPLE}_rgb.png`, observation_row_line_indexes: [8], observation_row_candidates: 1, agrees_with_observation_row: true, declared_sha256_by_row: 'd'.repeat(64), declared_bytes_by_row: 32804, availability: 'present', bytes_on_disk: 32804 },
      { field: 'depth_uri', uri: `assets/depth/${SAMPLE}_depth_m.npy`, observation_row_line_indexes: [9], observation_row_candidates: 1, agrees_with_observation_row: true, declared_sha256_by_row: 'f'.repeat(64), declared_bytes_by_row: 1228928, availability: 'present', bytes_on_disk: 1228928 },
      { field: 'valid_mask_uri', uri: `assets/masks/${SAMPLE}_valid.png`, observation_row_line_indexes: [9], observation_row_candidates: 1, agrees_with_observation_row: true, declared_sha256_by_row: null, declared_bytes_by_row: null, availability: 'present', bytes_on_disk: 1002 },
    ],
  },
  state: {
    status: 'matched', join_key: 'control_tick_id', key_value: 'tick_000006551',
    source: { stream_id: 'events', relative_path: 'events.jsonl', line_index: 27, event_seq: 28, event_type: 'feedback' },
    recorded_fields: { event_seq: 28, control_tick_id: 'tick_000006551', backend_monotonic_s: 426494.348683089, sim_time_s: 0.14, wall_utc: '2026-10-17T16:10:29.833599Z' },
    recorded_state: {
      base_position_world_sim_m: [-0.00023473557897040777, -1.0145992864392481e-6, 0.053540585735473954],
      base_quaternion_xyzw: [-2.027809601592562e-6, 9.433333536306481e-5, -3.230492476047126e-5, 0.9999999950267509],
      base_twist_body_m_s: [-0.001086000533659529, -5.668342660618616e-5, 0.00030122515201245397],
      wheel_velocity_rad_s: [-0.030412442759356704, -0.03446515577793489],
      arm_model_qpos_rad: [4.731963891071609e-5, 0.0016603668666036813, 0.0014384481908740504, -1.5696750090681135, 1.1293487091102144e-6],
      gripper_width_m: 0.024999996765415464, tcp_position_world_m: [0.17753849921383363, 0.002461415763947755, 0.30179180035418635],
      feedback_time_monotonic: 426494.347898655, sim_time_s: 0.14,
    },
    candidate_records: 1, single_state_selected: true, candidates: [{ line_index: 27, record_position: 'events.jsonl#27', event_seq: 28, event_type: 'feedback', backend_monotonic_s: 426494.348683089, sim_time_s: 0.14, payload: {} }],
    declared_reference: { feedback_sample_id: 'joint_feedback_000006551', row_status: 'unresolved_reference' },
    recorder_declared_feedback: { available: true, timing_event_status: 'matched', feedback_time_s: 426494.3479002, feedback_clock: 'backend_monotonic', capture_clocks_declared: { sim: 'sim', backend_monotonic: 'backend_monotonic', wall_utc: 'wall_utc' }, meaning: "the recorder's own declared feedback time for this frame, copied, not re-derived" },
    units: { '*_rad': 'radians', '*_rad_s': 'radians per second', '*_m': 'metres', '*_xyzw': 'quaternion x,y,z,w', '*_s': 'seconds' },
    carried_over_from_another_frame: false, interpolated: false,
    note: "this is the state the recorder placed on the frame's capture tick, not a verified same-instant sample of the scene",
  },
  times: {
    quantities: [
      quantity('state_event_write_minus_frame_capture'),
      quantity('state_payload_feedback_time_minus_frame_capture', { source_record: 'events state feedback payload', field: 'feedback_time_monotonic', abs_ms: 3.669840982183814, value: -0.003669840982183814 }),
      quantity('state_payload_feedback_time_minus_state_event_write', { source_record: 'events state feedback payload and envelope', relative_to: 'the same event record' }),
      quantity('state_sim_time_minus_frame_capture_sim_time', { source_record: 'events state feedback payload', field: 'sim_time_s', clock: 'sim', unit: 's', value: 0, abs_ms: 0, direction: 'equal' }),
      quantity('recorder_declared_feedback_time_minus_frame_capture', { source_record: 'events rgbd_capture_timing payload', field: 'feedback_time_s', line_index: 40, abs_ms: 3.668295976240188 }),
      quantity('observation_arrival_minus_frame_capture', { source_record: 'observations index row', field: 'arrival_time_s', direction: 'later', value: 0.03345116903074086, abs_ms: 33.45116903074086, sensor_kind: 'rgb', line_index: 8 }),
      quantity('persist_minus_capture', { source_record: 'persisted frame', field: 'persist_backend_monotonic_s', direction: 'later', value: 0.10002543800510466, abs_ms: 100.02543800510466, line_index: 0 }),
    ],
    recorder_declared: {
      fields: { observation_age_ms: 33.45116903074086, arrival_to_persist_ms: 66.5742689743638, capture_to_persist_ms: 100.02543800510466, encode_ms: 25.350222014822066 },
      observation_age_ms_note: "the recorder's observation_age_ms is its own capture-to-arrival figure for this frame, not the difference between a state sample and the capture",
      recomputed_arrival_minus_capture_ms: 33.45116903074086, agrees_with_recomputation: true,
    },
    semantics_rule: 'each quantity is one named subtraction of two recorded fields; two records naming the same clock base are not merged into one instant',
    state_time_quantity_keys: ['state_event_write_minus_frame_capture', 'state_payload_feedback_time_minus_frame_capture', 'recorder_declared_feedback_time_minus_frame_capture'],
    removed_in_this_version: { 'times.age_of_state_relative_to_frame': 'read times.quantities keys instead' },
    same_clock_verified: false,
  },
  roles: [
    { role: 'image_observation', join_key: 'sample_id', key_value: SAMPLE, status: 'matched', meaning: 'the rgb and depth observation rows recorded for this frame',
      requirement: { required_kinds: ['rgb', 'depth'], kind_cardinality: 1, rule: 'one row per required sensor_kind' },
      candidate_records: 2, matched_records: 2, identity_mismatched_records: 0, required_kinds: ['rgb', 'depth'], matched_kinds: ['rgb', 'depth'], missing_kinds: [], duplicate_kinds: [], unexpected_kinds: [],
      kind_inventory: { rgb: [8], depth: [9] }, candidate_line_indexes: [8, 9], ambiguous_records: null, reason: null,
      sources: [{ stream_id: 'observations-index', relative_path: 'observations/index.jsonl', line_index: 8, record_position: 'observations/index.jsonl#8', declared_media: [{ uri: `assets/rgb/${SAMPLE}_rgb.png`, declared_sha256: 'd'.repeat(64), declared_bytes: 32804 }] }] },
    { role: 'camera_transform', join_key: 'sample_id', key_value: SAMPLE, status: 'matched', requirement: { exact_records: 1, rule: 'exactly one transform row for this sample_id' }, candidate_records: 1, matched_records: 1,
      kind_inventory: null, candidate_line_indexes: [12], missing_kinds: [], duplicate_kinds: [], unexpected_kinds: [], sources: [{ stream_id: 'transforms', relative_path: 'transforms.jsonl', line_index: 12, record_position: 'transforms.jsonl#12' }] },
    { role: 'capture_timing_event', join_key: 'payload.sample_id', key_value: SAMPLE, status: 'matched', requirement: { exact_records: 1, rule: 'exactly one rgbd_capture_timing event' }, candidate_records: 1, matched_records: 1,
      kind_inventory: null, candidate_line_indexes: [40], missing_kinds: [], duplicate_kinds: [], unexpected_kinds: [], sources: [{ stream_id: 'events', relative_path: 'events.jsonl', line_index: 40, record_position: 'events.jsonl#40' }] },
    { role: 'state_feedback_event', join_key: 'control_tick_id', key_value: 'tick_000006551', status: 'matched', requirement: { exact_records: 1, rule: 'exactly one state event carrying this control_tick_id' }, candidate_records: 1, matched_records: 1,
      kind_inventory: null, candidate_line_indexes: [27], missing_kinds: [], duplicate_kinds: [], unexpected_kinds: [], sources: [{ stream_id: 'events', relative_path: 'events.jsonl', line_index: 27, record_position: 'events.jsonl#27' }] },
    { role: 'feedback_observation_row', join_key: 'sample_id', key_value: 'joint_feedback_000006551', status: 'unresolved_reference', requirement: { exact_records: 1, rule: 'one observation row equal to the declared feedback id' }, candidate_records: 0, matched_records: 0,
      kind_inventory: null, candidate_line_indexes: [], missing_kinds: [], duplicate_kinds: [], unexpected_kinds: [], sources: [] },
  ],
  ...patch,
});
const pageFixture = (patch: Partial<FramePageDto> = {}): FramePageDto => ({
  schema_version: FRAME_LINK_SCHEMA, read_only: true, source: SOURCE, retrieved_at: '2026-10-26T06:15:53.012634Z',
  identity: { run_id: RUN, episode_id: EPISODE, episode_directory: '/x/y', run_directory_identity: 'the run directory was re-validated as itself before this read', native_contract_version: 'mobilecar-1.0' },
  anchor: { stream_id: 'observations-persist', relative_path: 'observations/persist.jsonl', semantics: 'one persisted image frame per record', requested_stream: 'rgbd' },
  paging: PAGING,
  cursor: { order: 'native_append_order_of_the_anchor_stream', line_index_is_not_a_clock: true, persist_sequence_is_the_recorders_own_counter: true, first_line_index: 0, last_line_index: 2, first_persist_sequence: 1, last_persist_sequence: 3 },
  time: { selected_time_base: null, time_from: null, time_to: null, selectable_time_bases: ['capture_backend_monotonic_s', 'capture_sim_time_s', 'persist_backend_monotonic_s'],
    units: { '*_s': 'seconds', '*_ms': 'milliseconds', '*_rad': 'radians', '*_m': 'metres' }, synchronized_across_streams: false, same_clock_verified: false,
    clock_sameness: { fields_that_name_a_shared_base: ['persisted frame clock and capture_clocks', 'state event backend_monotonic_s'], declared_by_recorder: true, verified_by_reader: false,
      verified_claim: 'naming one clock base is not proof that two writers stamped it at one instant',
      writer_version_binding: { recorded: ['run manifest contract_version'], not_recorded: ['the native build or release that wrote the archive'], consequence: 'cannot be cited as proof', synchronized_upgraded_by_numeric_closeness: false } },
    deltas_are_recorded_arithmetic: true, browser_arrival_order_is_not_used: true },
  linkage: {
    roles: { image_observation: { source_stream: 'observations-index', join_key: 'sample_id', meaning: 'the rgb and depth observation rows' }, state_feedback_event: { source_stream: 'events', join_key: 'control_tick_id', meaning: 'recorded robot state feedback' } },
    status_meaning: { matched: 'every record the role requires was found by its recorded key, once', partial: 'some but not all', missing: 'no record carried the key',
      unresolved_reference: 'the frame declares a reference whose target record is not in this Episode', identity_mismatch: 'a candidate named a different run or Episode',
      stream_absent: 'the source stream is not recorded', ambiguous_kind: 'a sensor_kind the role requires was recorded more than once', ambiguous_candidates: 'more than one record claimed this role’s key, so no single record can be reported' },
    status_precedence: ['stream_absent', 'identity_mismatch', 'ambiguous_kind', 'ambiguous_candidates', 'partial', 'missing', 'unresolved_reference', 'matched'],
    primary_roles: ['image_observation', 'camera_transform', 'capture_timing_event', 'state_feedback_event'],
    selection_rules: { joins: 'exact equality of the recorded join key', when_several_match: 'ambiguous_kind or ambiguous_candidates with every candidate line index listed; the first line in the file is not chosen',
      completeness: 'judged by the required sensor_kind set and per-kind cardinality, never by a record count alone', state_hold: 'not applied: a frame never inherits another frame’s state',
      interpolation: 'none', 'nearest_in_time': 'not used; numeric closeness is not treated as identity or as simultaneity', status_precedence: ['stream_absent', 'matched'] },
    role_coverage_on_this_page: { image_observation: { matched: 3 }, state_feedback_event: { matched: 3 }, feedback_observation_row: { unresolved_reference: 3 } },
  },
  summary: { frames_returned: 3, frames_with_all_primary_roles_matched: 3, frames_with_some_primary_roles_missing: 0, frames_with_no_primary_role_matched: 0,
    frames_with_ambiguous_primary_role: 0, frames_without_a_linked_state: 0, frames_with_unresolved_feedback_reference: 3 },
  frames: [frameFixture(), frameFixture({ sample_id: 'rgbd_second' }), frameFixture({ sample_id: 'rgbd_third' })],
  not_proven: ['that two records naming the same clock base were stamped by one writer at one instant'],
  version_migration: { from_schema: 'unirobot-mobilecar-frame-link-1', to_schema: FRAME_LINK_SCHEMA,
    changed: ['paging.has_more is decided by finding the next qualifying anchor line'], removed_fields: { 'times.age_of_state_relative_to_frame': 'it merged the state event’s write stamp with the state sample stamps' },
    compatibility_note: 'consumers must read schema_version: frame-link-1 and frame-link-2 pages are not the same contract' },
  three_d_replay: { this_slice_does_not_enable_3d_replay: true, live_geometry_or_actual_may_be_applied: false, transforms_are_full_per_body_pose_sequences: false, robot_pose_readiness_slice: 'GET /api/v1/episodes/{episode_id}/robot-state' },
  capability_limits: ['no replay execution', 'no control, RESET, recording or physics stepping'],
  ...patch,
});

let urls: string[] = [];
beforeEach(() => { urls = []; });
afterEach(() => { vi.restoreAllMocks(); });
function respondWith(payload: unknown, status = 200) {
  globalThis.fetch = vi.fn(async (input: string) => { urls.push(input); return new Response(JSON.stringify(payload), { status, headers: { 'content-type': 'application/json' } }); }) as unknown as typeof fetch;
}

describe('frame-link-2 schema gate', () => {
  it('pins the schema string to the candidate’s own version', () => {
    expect(FRAME_LINK_SCHEMA).toBe('unirobot-mobilecar-frame-link-2');
  });
  it('refuses a frame-link-1 page instead of quietly rendering it as v2', async () => {
    respondWith(pageFixture({ schema_version: 'unirobot-mobilecar-frame-link-1' }));
    await expect(readFramesPage({ episodeId: EPISODE, runId: RUN, limit: 3, offset: 0 }, new AbortController().signal))
      .rejects.toThrow(/frame-link-2/);
  });
  it('refuses an unknown future version with the found value named', async () => {
    respondWith(pageFixture({ schema_version: 'unirobot-mobilecar-frame-link-3' }));
    await expect(readFramesPage({ episodeId: EPISODE, runId: RUN }, new AbortController().signal)).rejects.toBeInstanceOf(EpisodeContractError);
    respondWith(pageFixture({ read_only: false }));
    await expect(readFramesPage({ episodeId: EPISODE, runId: RUN }, new AbortController().signal)).rejects.toThrow(/read_only/);
  });
});

describe('frame-link-2 request shape', () => {
  it('sends the identity, the page and the sample condition together', async () => {
    respondWith(pageFixture());
    await readFramesPage({ episodeId: EPISODE, runId: RUN, limit: 3, offset: 100, sampleId: SAMPLE }, new AbortController().signal);
    const url = new URL(urls[0], 'http://preview.local');
    expect(url.pathname).toBe(`/api/v1/episodes/${EPISODE}/frames`);
    expect(url.searchParams.get('run_id')).toBe(RUN);
    expect(url.searchParams.get('offset')).toBe('100');
    expect(url.searchParams.get('sample_id')).toBe(SAMPLE);
  });
  it('never sends time_base without one of its own bounds', async () => {
    respondWith(pageFixture());
    await readFramesPage({ episodeId: EPISODE, runId: RUN, timeBase: 'capture_sim_time_s' }, new AbortController().signal);
    expect(urls[0]).not.toContain('time_base');
    await readFramesPage({ episodeId: EPISODE, runId: RUN, timeBase: 'capture_sim_time_s', timeTo: 12 }, new AbortController().signal);
    expect(urls[1]).toContain('time_base=capture_sim_time_s');
    expect(urls[1]).toContain('time_to=12');
    expect(urls[1]).not.toContain('time_from');
  });
});

describe('page reading and pagination', () => {
  it('treats an empty selectable_time_bases as the page’s answer', () => {
    expect(frameSelectableBases(pageFixture({ time: { ...pageFixture().time, selectable_time_bases: [] } }))).toEqual([]);
    expect(frameSelectableBases(null)).toEqual([]);
  });
  it('gates the window with the reader’s own reasons', () => {
    const page = pageFixture();
    expect(frameWindowGate(page, '', true).reason).toContain('frame-link-2 要求 time_base');
    expect(frameWindowGate(page, 'wall_utc', true).reason).toContain('不在本页声明的可选时间基里');
    expect(frameWindowGate(page, 'capture_sim_time_s', false).reason).toContain('time_range_required');
    expect(frameWindowGate(page, 'capture_sim_time_s', true).allowed).toBe(true);
  });
  it('reports the line census, the offset semantics and no total on a filled page', () => {
    const text = framePageExplanation(pageFixture(), { sampleId: null, base: null, from: null, to: null });
    expect(text).toContain('已读行 4');
    expect(text).toContain('anchor_records_examined=4');
    expect(text).toContain('next_qualifying_anchor_line_index=3');
    expect(text).toContain('raw line index after the last returned anchor');
    expect(text).not.toMatch(/共\s*\d+\s*帧/);
  });
  it('separates an unscanned anchor stream from a filtered-empty sample lookup', () => {
    const noLines = pageFixture({ frames: [], paging: { ...PAGING, returned: 0, anchor_lines: { ...PAGING.anchor_lines, lines_read: 0 }, anchor_records_examined: 0 } });
    expect(framePageKind(noLines, { sampleId: null, base: null, from: null, to: null })).toBe('no-anchor-lines');
    const filtered = pageFixture({ frames: [], paging: { ...PAGING, offset: 100, returned: 0, has_more: false, next_offset: null, anchor_records_examined: 303, excluded_by_sample_id_filter: 302, anchor_lines: { ...PAGING.anchor_lines, lines_read: 303 } } });
    const text = framePageExplanation(filtered, { sampleId: 'rgbd_missing', base: null, from: null, to: null });
    expect(framePageKind(filtered, { sampleId: 'rgbd_missing', base: null, from: null, to: null })).toBe('sample-no-match');
    expect(text).toContain('sample 条件排除 302');
    expect(text).toContain('由界面持有');
  });
  it('counts a window-empty page as a successful empty read', () => {
    const page = pageFixture({ frames: [], time: { ...pageFixture().time, selected_time_base: 'capture_sim_time_s', time_from: 900, time_to: 901 },
      paging: { ...PAGING, returned: 0, excluded_outside_time_window: 41, has_more: false } });
    const ctx = { sampleId: null, base: 'capture_sim_time_s', from: 900, to: 901 };
    expect(framePageKind(page, ctx)).toBe('window-empty');
    expect(framePageExplanation(page, ctx)).toContain('41 行按窗口排除');
  });
  it('keeps the corrected pagination and never repeats the old candidate’s paging caveat', () => {
    const page = pageFixture({ frames: [], paging: { ...PAGING, offset: 3, returned: 0, has_more: false, next_offset: null, post_page_records_examined: 0, anchor_records_examined: 3 } });
    const note = frameStopNote(page, { sampleId: null, base: 'capture_sim_time_s', from: 1, to: 2 }, true);
    expect(note).toContain('whole_file_scanned=false');
    expect(note).toContain('保留窗口与筛选条件');
    // The v1 wording described a defect this candidate fixed; it must not survive as a fact.
    expect(note).not.toContain('混合了候选行计数与锚点原生行号');
    expect(note).not.toContain('has_more=true 混合');
  });
});

describe('times: named quantities instead of one merged age', () => {
  const rows = quantityRowsOf(frameFixture());
  it('keeps the three state stamps as three separate rows with their own sources', () => {
    const keys = rows.map((row) => row.key);
    expect(keys).toContain('state_event_write_minus_frame_capture');
    expect(keys).toContain('state_payload_feedback_time_minus_frame_capture');
    expect(keys).toContain('recorder_declared_feedback_time_minus_frame_capture');
    expect(rows.find((row) => row.key === 'state_event_write_minus_frame_capture')?.display).toContain('写入');
    expect(rows.find((row) => row.key === 'state_payload_feedback_time_minus_frame_capture')?.display).toContain('采样');
    expect(rows.find((row) => row.key === 'state_event_write_minus_frame_capture')?.absMs).toBe('2.8854069532826543');
    expect(rows.find((row) => row.key === 'recorder_declared_feedback_time_minus_frame_capture')?.absMs).toBe('3.668295976240188');
  });
  it('marks the sim quantity as another clock and the persist row as pipeline latency', () => {
    expect(rows.find((row) => row.key === 'state_sim_time_minus_frame_capture_sim_time')?.clock).toBe('sim');
    expect(rows.find((row) => row.key === 'persist_minus_capture')?.display).toContain('落盘');
    expect(rows.find((row) => row.key === 'observation_arrival_minus_frame_capture')?.note).toContain('管线');
  });
  it('does not invent a display for a key the reader did not name', () => {
    const row = quantityRowsOf(frameFixture({ times: { ...frameFixture().times, quantities: [quantity('brand_new_difference')] } }))[0];
    expect(row.display).toContain('brand_new_difference');
    expect(row.note).toContain('不解释成延迟、帧率或同时刻');
  });
  it('copies the recorder’s own latency fields and never re-derives them', () => {
    const declared = recorderDeclaredOf(frameFixture());
    expect(declared.text).toContain('observation_age_ms=33.45116903074086');
    expect(declared.text).toContain('agrees_with_recomputation=true');
    expect(declared.note).toContain('not the difference between a state sample and the capture');
    expect(recorderDeclaredOf(null).text).toContain('不自行推断录制器时延');
  });
  it('lists the three state time keys and the removed field', () => {
    expect(stateQuantityKeysOf(frameFixture())).toContain('state_payload_feedback_time_minus_frame_capture');
    expect(timeSemanticsText(frameFixture())).toContain('age_of_state_relative_to_frame');
    const migration = versionMigrationText(pageFixture());
    expect(migration.head).toBe('unirobot-mobilecar-frame-link-1 → unirobot-mobilecar-frame-link-2');
    expect(migration.removed[0]).toContain('merged the state event’s write stamp');
    expect(migration.note).toContain('not the same contract');
    expect(versionMigrationText(null).head).toContain('未返回 version_migration');
  });
});

describe('state without a single selected record', () => {
  it('produces no rows and no invented value when recorded_state is null', () => {
    const frame = frameFixture({ state: { ...frameFixture().state, recorded_state: null, single_state_selected: false, candidate_records: 2, status: 'ambiguous_candidates', multiple_candidates_note: 'two records claimed this control_tick_id; none is chosen' } });
    expect(stateRowsOf(frame)).toEqual([]);
    const selection = stateSelectionOf(frame);
    expect(selection?.hasRecordedState).toBe(false);
    expect(selection?.singleSelected).toBe('false');
    expect(selection?.candidateRecords).toBe('2');
    expect(selection?.note).toContain('none is chosen');
    expect(selection?.candidates[0].position).toBe('events.jsonl#27');
  });
  it('shows the recorded values verbatim with the reader’s units', () => {
    const rows = stateRowsOf(frameFixture());
    const arm = rows.find((row) => row.key === 'arm_model_qpos_rad');
    expect(arm?.value).toContain('5 个分量，原样');
    expect(arm?.note).toContain('不是用户控制角');
    expect(rows.find((row) => row.key === 'wheel_velocity_rad_s')?.unit).toContain('radians per second');
    expect(rows.find((row) => row.key === 'feedback_time_monotonic')?.unit).toContain('未在 units 表里声明');
    expect(stateRowsOf(null)).toEqual([]);
  });
});

describe('roles, ambiguity and coverage', () => {
  it('carries the kind requirement, inventory and candidate lines per role', () => {
    const roles = roleRowsOf(frameFixture(), pageFixture().linkage);
    const image = roles.find((row) => row.role === 'image_observation');
    expect(image?.requirement).toContain('required_kinds=rgb/depth ×1');
    expect(image?.inventory).toContain('rgb→[8]');
    expect(image?.kinds).toContain('missing_kinds=空');
    expect(roles.find((row) => row.role === 'camera_transform')?.requirement).toContain('exact_records=1');
    expect(roles.find((row) => row.role === 'feedback_observation_row')?.reason).toContain('引用未解析');
    expect(ambiguousRoleCount(frameFixture())).toBe(0);
  });
  it('names ambiguity instead of silently picking a candidate', () => {
    const frame = frameFixture({ primary_roles_ambiguous: ['image_observation'],
      roles: [{ ...frameFixture().roles[0], status: 'ambiguous_kind', duplicate_kinds: ['rgb'], kind_inventory: { rgb: [8, 9], depth: [10] }, matched_kinds: ['depth'],
        ambiguous_records: [{ stream_id: 'observations-index', relative_path: 'observations/index.jsonl', line_index: 8 }, { stream_id: 'observations-index', relative_path: 'observations/index.jsonl', line_index: 9 }] }] });
    const row = roleRowsOf(frame, pageFixture().linkage)[0];
    expect(row.status).toBe('ambiguous_kind');
    expect(row.statusMeaning).toContain('recorded more than once');
    expect(row.ambiguous).toContain('2 条候选记录冲突');
    expect(row.inventory).toContain('rgb→[8,9]');
    expect(ambiguousRoleCount(frame)).toBe(1);
    expect(linkageScopeText(pageFixture(), frame)).toContain('primary_roles_ambiguous=[image_observation]');
  });
  it('reports coverage and precedence exactly as the page words them', () => {
    expect(roleCoverageText(pageFixture())).toContain('image_observation: matched=3');
    expect(statusPrecedenceText(pageFixture())).toContain('stream_absent > identity_mismatch > ambiguous_kind');
    expect(selectionRulesText(pageFixture())).toContain('the first line in the file is not chosen');
    expect(selectionRulesText(pageFixture())).toContain('numeric closeness is not treated as identity');
    expect(roleCoverageText(null)).toContain('未给本页角色覆盖统计');
  });
  it('summarises the page scope with the frame’s own list fields', () => {
    const text = linkageScopeText(pageFixture(), frameFixture());
    expect(text).toContain('primary_roles_matched=[image_observation,camera_transform,capture_timing_event,state_feedback_event]');
    expect(text).toContain('feedback 引用未解析=3');
    expect(linkageScopeText(null, null)).toContain('未读取帧页');
  });
});

describe('media refs of the selected frame', () => {
  it('lists every candidate row and keeps an absent digest absent', () => {
    const refs = frameMediaRefs(frameFixture());
    expect(refs).toHaveLength(3);
    expect(refs[0].rowLines).toBe('8');
    expect(refs[2].declaredSha256).toBeNull();
    expect(refs[2].rowsConflict).toBe('null');
    expect(frameAutoLoadRef(refs)?.field).toBe('rgb_uri');
    expect(mediaDeclarationText(frameFixture())).toContain('every candidate row for the kind is listed');
  });
  it('marks conflicting duplicate rows without choosing one', () => {
    const refs = frameMediaRefs(frameFixture({ media: { ...frameFixture().media, items: [{ field: 'rgb_uri', uri: 'assets/rgb/a.png', availability: 'present', observation_row_line_indexes: [8, 12], observation_row_candidates: 2, observation_rows_conflict: true, agrees_with_observation_row: true }] } }));
    expect(refs[0].rowLines).toBe('8,12');
    expect(refs[0].rowsConflict).toBe('true');
    expect(refs[0].note).toContain('可按 assets 端点读取字节');
  });
  it('refuses to read a reference the reader did not mark present', () => {
    const refs = frameMediaRefs(frameFixture({ media: { ...frameFixture().media, items: [
      { field: 'rgb_uri', uri: 'assets/rgb/a.png', availability: 'absent', observation_row_line_indexes: [8] },
      { field: 'depth_uri', uri: 'assets/depth/a.npy', availability: 'refused', refusal_code: 'episode_asset_escape', observation_row_line_indexes: [] }] } }));
    expect(refs[0].loadable).toBe(false);
    expect(refs[0].note).toContain('不按文件名推测内容');
    expect(refs[1].note).toContain('不绕过这个拒绝');
    expect(frameAutoLoadRef(refs)).toBeNull();
  });
});

describe('provenance and boundaries', () => {
  it('keeps record positions and declared identity in the provenance rows', () => {
    const rows = provenanceRowsOf(pageFixture(), frameFixture());
    const map = Object.fromEntries(rows.map((row) => [row.key, row.value]));
    expect(map.identity).toContain('the run directory was re-validated as itself');
    expect(map.state_position).toContain('events.jsonl#27');
    expect(map.role_positions).toContain('capture_timing_event:events.jsonl#40');
    expect(map.sample).toContain('tick_000006551');
  });
  it('states the 3D boundary and points at the pose slice that owns the model', () => {
    const text = frameBoundaryNotice(pageFixture());
    expect(text).toContain('this_slice_does_not_enable_3d_replay=true');
    expect(text).toContain('robot_pose_readiness_slice=GET /api/v1/episodes/{episode_id}/robot-state');
    expect(text).toContain('no replay execution');
  });
  it('separates what records name from what the reader can verify', () => {
    const text = clockSamenessText(pageFixture());
    expect(text).toContain('verified_by_reader=false');
    expect(text).toContain('the native build or release that wrote the archive');
    expect(text).toContain('synchronized_upgraded_by_numeric_closeness=false');
    expect(clockSamenessText(null)).toContain('未声明 clock_sameness');
  });
});
