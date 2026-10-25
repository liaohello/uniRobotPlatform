import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { EpisodeContractError } from '../src/adapters/platform-episodes';
import {
  FRAME_LINK_SCHEMA, declaredLatencyOf, deltaRowsOf, frameAutoLoadRef, frameBoundaryNotice, frameMediaRefs, framePageExplanation,
  framePageKind, frameSelectableBases, frameStopNote, frameWindowGate, linkageScopeText, mediaDeclarationText, provenanceRowsOf,
  readFramesPage, roleRowsOf, stateAgeOf, stateRowsOf, unitForField,
  type FrameDto, type FramePageDto,
} from '../src/adapters/platform-frames';

// The fixtures are shape copies of the `unirobot-mobilecar-frame-link-1` payloads this candidate
// actually answered on 2026-10-25 (COMPLETE record page 1, FAILED record page 1, and the empty-page
// counter sets). Only fields the reader returned are present; nothing is padded to ease a test.
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
  linkage_status: 'matched', primary_roles_matched: 4, declared_reference_status: 'unresolved_reference',
  media: {
    declared_by: 'the persisted frame record and its observation rows, copied verbatim',
    uri_convention: 'assets/<kind>/<file>, served only from this episode’s assets tree',
    digest_verification: 'declared only; recomputed when the asset endpoint serves the file',
    items: [
      { field: 'rgb_uri', uri: `assets/rgb/${SAMPLE}_rgb.png`, row_line_index: 8, agrees_with_observation_row: true, declared_sha256_by_row: 'd'.repeat(64), declared_bytes_by_row: 32804, availability: 'present', bytes_on_disk: 32804 },
      { field: 'depth_uri', uri: `assets/depth/${SAMPLE}_depth_m.npy`, row_line_index: 9, agrees_with_observation_row: true, declared_sha256_by_row: 'f'.repeat(64), declared_bytes_by_row: 1228928, availability: 'present', bytes_on_disk: 1228928 },
      { field: 'valid_mask_uri', uri: `assets/masks/${SAMPLE}_valid.png`, row_line_index: 9, agrees_with_observation_row: true, declared_sha256_by_row: null, declared_bytes_by_row: null, availability: 'present', bytes_on_disk: 1002 },
    ],
  },
  state: {
    status: 'matched', join_key: 'control_tick_id', key_value: 'tick_000006551',
    source: { stream_id: 'events', relative_path: 'events.jsonl', line_index: 27, event_seq: 28, event_type: 'feedback', record_position: 'events.jsonl#27' },
    recorded_fields: { event_seq: 28, event_type: 'feedback', control_tick_id: 'tick_000006551', backend_monotonic_s: 426494.348683089, sim_time_s: 0.14, wall_utc: '2026-10-17T16:10:29.833599Z' },
    recorded_state: {
      feedback_time_monotonic: 426494.347898655, sim_time_s: 0.14,
      base_position_world_sim_m: [-0.00023473557897040777, -1.0145992864392481e-06, 0.053540585735473954],
      base_quaternion_xyzw: [-2.027809601592562e-06, 9.433333536306481e-05, -3.230492476047126e-05, 0.9999999950267509],
      base_twist_body_m_s: [-0.001086000533659529, -5.668342660618616e-05, 0.00030122515201245397],
      wheel_velocity_rad_s: [-0.030412442759356704, -0.03446515577793489, -0.031348075259700646, -0.028323501529422878],
      arm_model_qpos_rad: [4.731963891071609e-05, 0.0016603668666036813, 0.0014384481908740504, -1.5696750090681135, 1.1293487091102144e-06],
      gripper_width_m: 0.024999996765415464, tcp_position_world_m: [0.17753849921383363, 0.002461415763947755, 0.30179180035418635],
    },
    declared_reference: { feedback_sample_id: 'joint_feedback_000006551', row_status: 'unresolved_reference' },
    recorder_declared_feedback: { available: true, feedback_time_s: 426494.3479002, feedback_clock: 'backend_monotonic', capture_clocks_declared: { sim: 'sim', backend_monotonic: 'backend_monotonic', wall_utc: 'wall_utc' }, meaning: 'the recorder’s own declared feedback time for this frame, copied, not re-derived' },
    units: { '*_rad': 'radians', '*_rad_s': 'radians per second', '*_m': 'metres', '*_nm': 'newton metres', '*_xyzw': 'quaternion x,y,z,w', '*_s': 'seconds' },
    carried_over_from_another_frame: false, interpolated: false,
    note: 'this is the state the recorder placed on the frame’s capture tick, not a verified same-instant sample of the scene',
  },
  times: {
    deltas: [
      { label: 'state_event_minus_frame_capture', capture_value: 426494.351568496, other_value: 426494.348683089, value_s: -0.0028854069532826543, abs_value_ms: 2.8854069532826543, direction: 'earlier', basis: 'events record backend_monotonic_s minus persisted frame capture_backend_monotonic_s', meaning: 'recorded minus recorded, seconds', line_index: 27 },
      { label: 'recorder_declared_feedback_time_minus_capture', capture_value: 426494.351568496, other_value: 426494.3479002, value_s: -0.003668295976240188, abs_value_ms: 3.668295976240188, direction: 'earlier', basis: 'rgbd_capture_timing payload feedback_time_s minus capture_backend_monotonic_s', meaning: 'recorded minus recorded, seconds' },
      { label: 'observation_arrival_time_s_minus_frame_capture', capture_value: 426494.351568496, other_value: 426494.385019665, value_s: 0.03345116903074086, abs_value_ms: 33.45116903074086, direction: 'later', basis: 'observations index row arrival_time_s minus frame capture', sensor_kind: 'rgb', line_index: 8, meaning: 'recorded minus recorded, seconds' },
      { label: 'some_future_difference', capture_value: 1, other_value: 2, value_s: 1, abs_value_ms: 1000, direction: 'later', basis: 'not described in the reader’s own words' },
    ],
    declared_latency_ms: { arrival_to_persist_ms: 66.5742689743638, capture_to_persist_ms: 100.02543800510466 },
    age_of_state_relative_to_frame: { abs_ms: 2.8854069532826543, state_recorded_before_capture: true, display_hint: 'show as the age of the state; not a synchronised instant' },
    same_clock_verified: false,
  },
  roles: [
    { role: 'image_observation', join_key: 'sample_id', key_value: SAMPLE, status: 'matched', expected_records: 2, matched_records: 2, identity_mismatched_records: 0, sources: [{ stream_id: 'observations-index', relative_path: 'observations/index.jsonl', line_index: 8, record_position: 'observations/index.jsonl#8' }, { stream_id: 'observations-index', relative_path: 'observations/index.jsonl', line_index: 9, record_position: 'observations/index.jsonl#9' }] },
    { role: 'camera_transform', join_key: 'sample_id', key_value: SAMPLE, status: 'matched', expected_records: 1, matched_records: 1, identity_mismatched_records: 0, sources: [{ stream_id: 'transforms', relative_path: 'transforms.jsonl', line_index: 0, record_position: 'transforms.jsonl#0' }] },
    { role: 'capture_timing_event', join_key: 'payload.sample_id', key_value: SAMPLE, status: 'matched', expected_records: 1, matched_records: 1, identity_mismatched_records: 0, sources: [{ stream_id: 'events', relative_path: 'events.jsonl', line_index: 26, event_seq: 27, record_position: 'events.jsonl#26' }] },
    { role: 'state_feedback_event', join_key: 'control_tick_id', key_value: 'tick_000006551', status: 'matched', expected_records: 1, matched_records: 1, identity_mismatched_records: 0, sources: [{ stream_id: 'events', relative_path: 'events.jsonl', line_index: 27, event_seq: 28, event_type: 'feedback', record_position: 'events.jsonl#27' }] },
    { role: 'feedback_observation_row', join_key: 'sample_id', key_value: 'joint_feedback_000006551', status: 'unresolved_reference', expected_records: 1, matched_records: 0, identity_mismatched_records: 0 },
  ],
  ...patch,
});
const pageFixture = (patch: Partial<FramePageDto> = {}): FramePageDto => ({
  schema_version: FRAME_LINK_SCHEMA, read_only: true, source: SOURCE, retrieved_at: '2026-10-25T08:43:30Z',
  identity: { run_id: RUN, episode_id: EPISODE, episode_directory: `/root/${RUN}/episodes/${EPISODE}`, run_directory_identity: 'the run directory was re-validated as itself before this read', native_contract_version: 'mobilecar-1.0' },
  anchor: { stream_id: 'observations-persist', relative_path: 'observations/persist.jsonl', semantics: 'one persisted image frame per record', requested_stream: 'rgbd' },
  paging: { limit: 1, offset: 0, returned: 1, scanned_anchor_lines: 2, skipped_before_offset: 0, excluded_stream_mismatch: 0, excluded_without_sample_id: 0, excluded_outside_time_window: 0, excluded_anchor_identity_mismatch: 0, records_missing_selected_time_base: 0, next_offset: 1, has_more: true },
  cursor: { order: 'native_append_order_of_the_anchor_stream', line_index_is_not_a_clock: true, persist_sequence_is_the_recorders_own_counter: true, first_line_index: 0, last_line_index: 0, first_persist_sequence: 1, last_persist_sequence: 1 },
  time: {
    selected_time_base: null, time_from: null, time_to: null,
    selectable_time_bases: ['capture_backend_monotonic_s', 'capture_sim_time_s', 'persist_backend_monotonic_s'],
    units: { '*_s': 'seconds', '*_ms': 'milliseconds', '*_rad': 'radians', '*_m': 'metres' },
    synchronized_across_streams: false,
    clock_sameness: { declared_by_recorder: true, verified_by_reader: false, note: 'naming is not verification that two writers shared one clock' },
    deltas_are_recorded_arithmetic: true, browser_arrival_order_is_not_used: true,
  },
  linkage: {
    roles: {
      image_observation: { source_stream: 'observations-index', join_key: 'sample_id', meaning: 'the rgb and depth observation rows recorded for this frame' },
      camera_transform: { source_stream: 'transforms', join_key: 'sample_id', meaning: 'camera extrinsics recorded for this frame; not a per-body pose sequence' },
      capture_timing_event: { source_stream: 'events', join_key: 'payload.sample_id', meaning: 'the recorder’s own capture-timing event for this frame' },
      state_feedback_event: { source_stream: 'events', join_key: 'control_tick_id', meaning: 'recorded robot state feedback carried on the frame’s capture tick' },
      feedback_observation_row: { source_stream: 'observations-index', join_key: 'sample_id', meaning: 'an observation row whose own sample_id equals the frame’s declared feedback_sample_id' },
    },
    status_meaning: {
      matched: 'every expected record for the role was found by its recorded key',
      partial: 'some but not all expected records for the role were found',
      missing: 'no record for this role carried the key',
      unresolved_reference: 'the frame declares a reference whose target record is not in this Episode',
      identity_mismatch: 'a candidate record named a different run or Episode and was excluded',
      stream_absent: 'the source stream is not recorded in this Episode',
    },
    primary_roles: ['image_observation', 'camera_transform', 'capture_timing_event', 'state_feedback_event'],
    selection_rules: { joins: 'exact equality of the recorded join key named on each role', when_nothing_matches: 'the role is reported as missing, unresolved_reference or stream_absent', state_hold: 'not applied', interpolation: 'none', nearest_in_time: 'not used' },
    role_coverage_on_this_page: { image_observation: { matched: 1 }, feedback_observation_row: { unresolved_reference: 1 } },
  },
  summary: { frames_returned: 1, frames_with_all_primary_roles_matched: 1, frames_with_some_primary_roles_missing: 0, frames_with_no_primary_role_matched: 0, frames_without_a_linked_state: 0, frames_with_unresolved_feedback_reference: 1 },
  frames: [frameFixture()],
  not_proven: ['that two records naming the same clock base were stamped at the same instant', 'a cross-stream or cross-episode replay cursor', 'rendered 3D replay', 'archive-wide integrity'],
  three_d_replay: { this_slice_does_not_enable_3d_replay: true, live_geometry_or_actual_may_be_applied: false, transforms_are_full_per_body_pose_sequences: false },
  capability_limits: ['no replay execution', 'no cross-episode cursor', 'no native validate proxy', 'no control, RESET, recording or physics stepping'],
  ...patch,
});

const calls: { url: string; init: RequestInit }[] = [];
beforeEach(() => {
  calls.length = 0;
  globalThis.fetch = vi.fn(async (input: string, init: RequestInit = {}) => {
    calls.push({ url: input, init });
    if (input.includes('/frames')) return new Response(JSON.stringify(pageFixture()), { status: 200, headers: { 'content-type': 'application/json' } });
    return new Response(JSON.stringify({ detail: { code: 'episode_not_found', message: 'no Episode directory', read_only: true } }), { status: 404, headers: { 'content-type': 'application/json' } });
  }) as unknown as typeof fetch;
});
afterEach(() => { vi.restoreAllMocks(); });

describe('frame-link-1 client', () => {
  it('sends exactly one GET on the frames path with run_id kept explicit', async () => {
    await readFramesPage({ episodeId: EPISODE, runId: RUN, limit: 5, offset: 1 }, new AbortController().signal);
    expect(calls[0].url).toBe(`/api/v1/episodes/${EPISODE}/frames?run_id=${RUN}&limit=5&offset=1`);
    expect(calls[0].init.method).toBe('GET');
    expect((calls[0].init.headers as Record<string, string>).Accept).toBe('application/json');
  });
  it('never sends a time bound without its base, nor a base without any bound', async () => {
    await readFramesPage({ episodeId: EPISODE, runId: RUN, timeBase: 'capture_sim_time_s', timeFrom: 0, timeTo: null }, new AbortController().signal);
    expect(calls[0].url).toContain('time_base=capture_sim_time_s');
    expect(calls[0].url).toContain('time_from=0');
    expect(calls[0].url).not.toContain('time_to');
    // An explicit 0 is a value, not an absent one; a base alone would answer 400 time_range_required.
    await readFramesPage({ episodeId: EPISODE, runId: RUN, timeBase: 'capture_sim_time_s' }, new AbortController().signal);
    expect(calls[1].url).not.toContain('time_base');
    expect(calls[1].url).not.toContain('time_from');
    await readFramesPage({ episodeId: EPISODE, runId: RUN, timeFrom: 12, timeTo: 13 }, new AbortController().signal);
    expect(calls[2].url).not.toContain('time_from');
  });
  it('drops a blank sample condition instead of asking for an empty id', async () => {
    await readFramesPage({ episodeId: EPISODE, runId: RUN, sampleId: '' }, new AbortController().signal);
    expect(calls[0].url).not.toContain('sample_id');
    await readFramesPage({ episodeId: EPISODE, runId: RUN, sampleId: SAMPLE }, new AbortController().signal);
    expect(calls[1].url).toContain(`sample_id=${SAMPLE}`);
  });
  it('refuses a payload that is not frame-link-1 instead of rendering it', async () => {
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify({ schema_version: 'unirobot-mobilecar-frame-link-2', read_only: true }), { status: 200, headers: { 'content-type': 'application/json' } })) as unknown as typeof fetch;
    await expect(readFramesPage({ episodeId: EPISODE, runId: RUN }, new AbortController().signal)).rejects.toBeInstanceOf(EpisodeContractError);
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify({ schema_version: FRAME_LINK_SCHEMA, read_only: false }), { status: 200, headers: { 'content-type': 'application/json' } })) as unknown as typeof fetch;
    await expect(readFramesPage({ episodeId: EPISODE, runId: RUN }, new AbortController().signal)).rejects.toThrow(/read_only/);
  });
});

describe('frame page reading without invented totals', () => {
  it('takes the selectable bases from the page only, and an empty list is the page’s answer', () => {
    expect(frameSelectableBases(pageFixture())).toEqual(['capture_backend_monotonic_s', 'capture_sim_time_s', 'persist_backend_monotonic_s']);
    expect(frameSelectableBases(null)).toEqual([]);
    const none = pageFixture({ time: { ...pageFixture().time, selectable_time_bases: [] } });
    expect(frameSelectableBases(none)).toEqual([]);
    expect(frameWindowGate(none, 'capture_sim_time_s', true).allowed).toBe(false);
    expect(frameWindowGate(none, 'capture_sim_time_s', true).reason).toContain('selectable_time_bases=空');
  });
  it('refuses a window that the contract cannot carry', () => {
    const page = pageFixture();
    expect(frameWindowGate(page, '', false).allowed).toBe(false);
    expect(frameWindowGate(page, '', true).reason).toContain('不替这组秒数猜一个基');
    expect(frameWindowGate(page, 'wall_utc', true).allowed).toBe(false);
    expect(frameWindowGate(page, 'wall_utc', true).reason).toContain('不在本页声明的可选时间基里');
    expect(frameWindowGate(page, 'capture_sim_time_s', false).reason).toContain('time_range_required');
    expect(frameWindowGate(page, 'capture_sim_time_s', true).allowed).toBe(true);
  });
  it('explains each empty page by its own counters and never states a total', () => {
    const base = { limit: 2, offset: 1, returned: 0, scanned_anchor_lines: 303, skipped_before_offset: 1, excluded_stream_mismatch: 0, excluded_without_sample_id: 0, excluded_outside_time_window: 0, excluded_anchor_identity_mismatch: 0, records_missing_selected_time_base: 0, next_offset: null, has_more: false };
    const empty = (patch: Partial<FramePageDto['paging']>, frames: FrameDto[] = []) => pageFixture({ paging: { ...base, ...patch }, frames });
    expect(framePageKind(null, { sampleId: null, base: null, from: null, to: null })).toBe('unavailable');
    expect(framePageKind(empty({ scanned_anchor_lines: 0 }), { sampleId: null, base: null, from: null, to: null })).toBe('no-anchor-lines');
    expect(framePageExplanation(empty({ scanned_anchor_lines: 0 }), { sampleId: null, base: null, from: null, to: null })).toContain('不推断该 Episode 没有录制');
    expect(framePageKind(empty({ excluded_outside_time_window: 302 }), { sampleId: null, base: 'capture_backend_monotonic_s', from: 1, to: 2 })).toBe('window-empty');
    expect(framePageExplanation(empty({ excluded_outside_time_window: 302 }), { sampleId: null, base: 'capture_backend_monotonic_s', from: 1, to: 2 })).toContain('空结果页，不是读取错误');
    expect(framePageKind(empty({}), { sampleId: 'rgbd_nope', base: null, from: null, to: null })).toBe('sample-no-match');
    expect(framePageExplanation(empty({}), { sampleId: 'rgbd_nope', base: null, from: null, to: null })).toContain('由界面持有');
    expect(framePageKind(empty({ offset: 303, skipped_before_offset: 303 }), { sampleId: null, base: null, from: null, to: null })).toBe('offset-past-end');
    expect(framePageExplanation(empty({ offset: 303, skipped_before_offset: 303 }), { sampleId: null, base: null, from: null, to: null })).toContain('不推断录制结束');
    const counted = pageFixture({ paging: { ...base, records_missing_selected_time_base: 7 }, frames: [] });
    expect(framePageExplanation(counted, { sampleId: null, base: 'capture_sim_time_s', from: 1, to: 2 })).toContain('records_missing_selected_time_base=7');
    expect(framePageExplanation(counted, { sampleId: null, base: 'capture_sim_time_s', from: 1, to: 2 })).toContain('不补值');
    // A non-empty page says how many frames it returned and forbids any total count wording.
    const words = framePageExplanation(pageFixture(), { sampleId: null, base: null, from: null, to: null });
    expect(words).toContain('本页返回 1 帧');
    expect(words).toContain('响应不提供总帧数');
    expect(words).toContain('line_index_is_not_a_clock=true');
  });
  it('names the has_more/next_offset gap instead of pretending more frames exist', () => {
    const stopped = pageFixture({ paging: { ...pageFixture().paging, offset: 1, returned: 0, scanned_anchor_lines: 303, skipped_before_offset: 1, excluded_outside_time_window: 302, next_offset: null, has_more: false }, frames: [] });
    const note = frameStopNote(stopped, { sampleId: null, base: 'capture_backend_monotonic_s', from: 1, to: 2 }, true);
    expect(note).toContain('返回 0 帧');
    expect(note).toContain('混合了候选行计数与锚点原生行号');
    expect(note).toContain('不伪造分页结果');
    expect(frameStopNote(pageFixture(), { sampleId: null, base: null, from: null, to: null }, true)).toBe('');
  });
});

describe('frame state, time and role wording', () => {
  it('labels a recorded model joint angle as a model joint angle, never a command or calibration', () => {
    const rows = stateRowsOf(frameFixture());
    const qpos = rows.find((row) => row.key === 'arm_model_qpos_rad')!;
    expect(qpos.label).toContain('机械臂模型关节角');
    expect(qpos.note).toContain('不是用户控制角');
    expect(qpos.note).toContain('不是标定结果');
    expect(qpos.unit).toContain('radians');
    const gripper = rows.find((row) => row.key === 'gripper_width_m')!;
    expect(gripper.value).toBe('0.024999996765415464');
    expect(gripper.unit).toContain('metres');
    const base = rows.find((row) => row.key === 'base_position_world_sim_m')!;
    // JS prints this magnitude in fixed notation; the digits, not the exponent form, are the point.
    expect(base.value).toBe('[-0.00023473557897040777, -0.0000010145992864392481, 0.053540585735473954]（3 个分量，原样）');
    expect(base.note).toContain('不是发送过的指令位置');
    // A field the reader did not describe keeps its own name and says the unit is undeclared.
    const unknown = stateRowsOf(frameFixture({ state: { ...frameFixture().state, recorded_state: { mystery_joint_nm: 1.5 } } }))[0];
    expect(unknown.label).toContain('mystery_joint_nm');
    expect(unknown.note).toContain('不翻译成关节/控制/标定等类别');
    expect(stateRowsOf(null)).toEqual([]);
  });
  it('matches units by the longest declared suffix and says when nothing matches', () => {
    const units = { '*_rad': 'radians', '*_rad_s': 'radians per second', '*_m': 'metres', '*_nm': 'newton metres' };
    expect(unitForField(units, 'joint_torques_nm').unit).toContain('newton metres');
    expect(unitForField(units, 'wheel_velocity_rad_s').unit).toContain('radians per second');
    expect(unitForField(units, 'feedback_time_monotonic').declared).toBe(false);
    expect(unitForField(units, 'feedback_time_monotonic').unit).toContain('未在 units 表里声明');
  });
  it('calls the millisecond numbers linkage time differences, keeps raw times, and does not infer one clock', () => {
    const rows = deltaRowsOf(frameFixture());
    const state = rows.find((row) => row.label === 'state_event_minus_frame_capture')!;
    expect(state.display).toContain('关联状态事件时间差');
    expect(state.note).toContain('不是物理状态采样延迟');
    expect(state.absMs).toBe('2.8854069532826543');
    expect(state.captureValue).toBe('426494.351568496');
    expect(state.otherValue).toBe('426494.348683089');
    expect(state.position).toContain('line_index=27');
    const arrival = rows.find((row) => row.label === 'observation_arrival_time_s_minus_frame_capture')!;
    expect(arrival.position).toContain('sensor_kind=rgb');
    // An unlabelled difference is shown with the reader's basis only: no invented meaning.
    const future = rows.find((row) => row.label === 'some_future_difference')!;
    expect(future.display).toBe('some_future_difference');
    expect(future.note).toContain('不解释成延迟、帧率或同时刻');
    const age = stateAgeOf(frameFixture(), pageFixture())!;
    expect(age.absMs).toBe('2.8854069532826543');
    expect(age.beforeCapture).toBe('true');
    expect(age.sameClock).toBe('false');
    expect(age.clockSameness).toContain('verified_by_reader=false');
    expect(declaredLatencyOf(frameFixture())).toContain('记录者自己');
    expect(declaredLatencyOf(frameFixture({ times: { ...frameFixture().times, declared_latency_ms: {} } }))).toContain('没有记录自述的延迟字段');
  });
  it('keeps the four primary roles and the declared feedback reference as two separate statements', () => {
    const rows = roleRowsOf(frameFixture(), pageFixture().linkage);
    expect(rows.filter((row) => row.primary)).toHaveLength(4);
    const feedback = rows.find((row) => row.role === 'feedback_observation_row')!;
    expect(feedback.primary).toBe(false);
    expect(feedback.status).toBe('unresolved_reference');
    expect(feedback.statusMeaning).toContain('target record is not in this Episode');
    expect(feedback.reason).toContain('不等于完全没有机器人状态');
    expect(feedback.reason).toContain('state_feedback_event（status=matched）');
    expect(rows.find((row) => row.role === 'image_observation')!.positions).toBe('observations/index.jsonl#8 , observations/index.jsonl#9');
    const scope = linkageScopeText(pageFixture(), frameFixture());
    expect(scope).toContain('linkage_status=matched');
    expect(scope).toContain('declared_reference_status=unresolved_reference');
    expect(scope).toContain('feedback 引用未解析=1');
    expect(linkageScopeText(null, null)).toContain('不声明任何关联结论');
  });
});

describe('frame media and provenance', () => {
  it('reads only this frame’s own references and marks a non-present one unreadable', () => {
    const refs = frameMediaRefs(frameFixture());
    expect(refs.map((ref) => ref.field)).toEqual(['rgb_uri', 'depth_uri', 'valid_mask_uri']);
    expect(refs.every((ref) => ref.loadable)).toBe(true);
    expect(frameAutoLoadRef(refs)!.uri).toBe(`assets/rgb/${SAMPLE}_rgb.png`);
    expect(mediaDeclarationText(frameFixture())).toContain('declared only; recomputed when the asset endpoint serves the file');
    const broken = frameMediaRefs(frameFixture({
      media: { items: [
        { field: 'rgb_uri', uri: 'assets/rgb/gone_rgb.png', availability: 'absent', bytes_on_disk: null, declared_sha256_by_row: 'd'.repeat(64), declared_bytes_by_row: 1, agrees_with_observation_row: false, row_line_index: 3 },
        { field: 'depth_uri', uri: 'assets/depth/escape.npy', availability: 'refused', refusal_code: 'episode_asset_escape' },
        { field: 'valid_mask_uri', uri: '', availability: 'not_recorded_on_this_frame' },
      ] },
    }));
    expect(frameAutoLoadRef(broken)).toBeNull();
    expect(broken[0].loadable).toBe(false);
    expect(broken[0].note).toContain('不按文件名推测内容');
    expect(broken[1].note).toContain('refusal_code=episode_asset_escape');
    expect(broken[1].note).toContain('界面不绕过这个拒绝');
    expect(broken[2].note).toContain('不拿别的帧的图片顶替');
    expect(frameMediaRefs(null)).toEqual([]);
  });
  it('proves where every displayed value came from', () => {
    const rows = provenanceRowsOf(pageFixture(), frameFixture());
    const value = (key: string) => rows.find((row) => row.key === key)!.value;
    expect(value('source')).toContain(SOURCE.source_id);
    expect(value('identity')).toContain(RUN);
    expect(value('anchor')).toContain('observations/persist.jsonl # line_index=0');
    expect(value('sample')).toContain(`capture_control_tick_id=tick_000006551 feedback_sample_id=joint_feedback_000006551`);
    expect(value('state_position')).toContain('events.jsonl#27');
    expect(value('state_position')).toContain('event_seq=28');
    expect(value('role_positions')).toContain('camera_transform:transforms.jsonl#0');
    expect(value('profile')).toContain('profile_id=g2a-rgbd-5hz-original');
    expect(value('clocks')).toContain('persist_backend_monotonic_s=426494.451593934');
    expect(provenanceRowsOf(pageFixture(), frameFixture({ state: { ...frameFixture().state, status: 'missing', source: null } })).find((row) => row.key === 'state_position')!.value)
      .toContain('状态未命中（status=missing）');
    expect(provenanceRowsOf(null, null)).toEqual([]);
  });
  it('keeps the 3D and cross-stream refusal in the reader’s own words', () => {
    const notice = frameBoundaryNotice(pageFixture());
    expect(notice).toContain('this_slice_does_not_enable_3d_replay=true');
    expect(notice).toContain('live_geometry_or_actual_may_be_applied=false');
    expect(notice).toContain('transforms_are_full_per_body_pose_sequences=false');
    expect(notice).toContain('no control, RESET, recording or physics stepping');
    expect(notice).toContain('cross-stream or cross-episode replay cursor');
    expect(frameBoundaryNotice(null)).toContain('不声明 3D 或未证明范围');
  });
});
