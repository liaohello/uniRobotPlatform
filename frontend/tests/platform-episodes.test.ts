import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../src/adapters/platform-config';
import {
  EpisodeContractError, PlatformEpisodeApi, ambiguousRuns, associationNotice, checksumFinding, describeHistoryError,
  emptyListKind, integrityFacets, isAmbiguous, mediaRefsOf, presentTimeBases, rowViews, streamViews, threeDNotice, timeFieldOf, unitOf,
  type EpisodeDetailDto, type EpisodeListDto, type RecordPageDto,
} from '../src/adapters/platform-episodes';

// Fixtures are shape copies of the real `unirobot-mobilecar-episode-read-1` payloads read from the
// history candidate on the server (COMPLETE record + FAILED record). Only what the reader returned
// is present; nothing is added to make a test easier.
const SOURCE = {
  source_id: 'mobilecar-server-history-20261017', adapter_id: 'mobilecar', robot_id: 'landerpi',
  native_release_id: 'drvfix-20261019T044549Z-0a80415b2577', native_contract_version: 'mobilecar-1.0',
  recording_root: '/home/liaozhengyan/Desktop/mobileCar/var/runs', access: 'read_only_files', platform_writes: false,
  declaring_instance: { base_url: 'http://127.0.0.1:8792', config_file: 'configs/g4a2_server.yaml', recording_root_in_config: '../../var/runs', access: 'GET_only' },
  archive_baseline: { scope: 'aggregate', files_hashed: 696, aggregate_sha256: '6'.repeat(64), meaning: 'change detection reference' },
};
const RUN = 'run_0104613ff7364ae78cf2f3946bd45f7b';
const EPISODE = 'episode_27bfed5427684795b361cd2ec21e9aa7';
const listFixture = {
  schema_version: 'unirobot-mobilecar-episode-read-1', read_only: true, source: SOURCE, retrieved_at: '2026-10-25T05:25:40Z',
  paging: { limit: 2, offset: 0, returned: 2, total_matches: 348, next_offset: 2, order: 'run_id_then_episode_id', declared_total_from_native_list: 348 },
  filters: { run_id: null, recording_status: null, episode_id: null },
  integrity_scope: 'statuses are as declared by the native record files; this list opened episode.json only',
  capability_limits: ['no replay execution', 'no native validate proxy'],
  episodes: [{
    run_id: RUN, episode_id: EPISODE, contract_version: 'mobilecar-1.0', readable: true, read_error: null,
    task_language: 'G2A server RGB-D profile validation', operator_id: 'g2a_server_acceptance', operator_kind: 'agent_ui',
    view_source: 'third_person_3d', map_mode: 'unavailable', created_wall_utc: '2026-10-17T16:10:29Z', ended_wall_utc: '2026-10-17T16:11:31Z',
    segment_count: 1, declared: { recording_status: 'COMPLETE', audit_status: 'COMPLETE', result: 'failure', termination_reason: 'G2A_MOTION_ARM_COMPLETE', require_recording: true },
    declaration_only: true,
  }],
};
const mediaSample = { relative_path: 'assets/rgb/rgbd_e3213e6cb64b4cd693c17d485d064d09_rgb.png', bytes: 36001, declared_sha256: 'c'.repeat(64) };
const detailFixture = (patch: Record<string, unknown> = {}): EpisodeDetailDto => ({
  schema_version: 'unirobot-mobilecar-episode-read-1', read_only: true, source: SOURCE, retrieved_at: '2026-10-25T05:25:40Z',
  identity: {
    source_id: SOURCE.source_id, adapter_id: 'mobilecar', recording_root: SOURCE.recording_root, run_id: RUN, episode_id: EPISODE,
    episode_directory: `/x/${RUN}/episodes/${EPISODE}`, native_contract_version: 'mobilecar-1.0',
    backend_generation: { available: true, reason: null, distinct_values: [1], scope: 'sampled recorded payloads, not a per-record field' },
    segments: [{ recording_segment_id: 'seg_001_d9ba710d3f', previous_recording_segment_id: null, status: 'COMPLETE', reason: 'G2A_MOTION_ARM_COMPLETE', started_wall_utc: 'a', ended_wall_utc: 'b', started_backend_monotonic_s: 426494.22, termination_reason: 'G2A_MOTION_ARM_COMPLETE' }],
    episode_display_name_is_not_a_key: true,
  },
  declared: {
    recording_status: 'COMPLETE', audit_status: 'COMPLETE', result: 'failure', task_result_source: 'oracle', termination_reason: 'G2A_MOTION_ARM_COMPLETE',
    require_recording: true, complete_tail_file_present: true, declared_checksum_entries: 924, episode_json_readable: true, tail_json_readable: true,
  },
  integrity: {
    status: 'complete', scope: 'this episode, as read by this request',
    this_read_evidence: { episode_json_parsed: true, tail_json_parsed: true, episode_json_sha256: '0d'.padEnd(64, '0'), tail_json_sha256: 'b2'.padEnd(64, '0'), files_recomputed_here: ['episode.json', 'episode_complete.json'] },
    checksum_verification: {
      declared_entries: 924, matched: [],
      mismatched: [{ relative_path: 'episode.json', declared_sha256: '5e'.padEnd(64, '0'), actual_sha256: '0d'.padEnd(64, '0') }],
      verdict: 'mismatch_present', meaning: 'a tail checksum is the recorder’s own declaration',
    },
    not_verified: ['files not opened by this request', 'asset payloads except the ones actually served'],
    declaration_is_not_verification: true,
  },
  streams: [
    { stream_id: 'events', relative_path: 'events.jsonl', format: 'jsonl', semantics: 'native event append order', available: true, bytes: 12472413, records: 12561, records_counted: true, records_over_read_size_limit: 0 },
    { stream_id: 'tail', relative_path: 'episode_complete.json', format: 'json', available: false, bytes: null, records: null },
  ],
  time: {
    record_order_is_native_append_order: true, clocks_declared_by_run_manifest: ['sim', 'backend_monotonic', 'device', 'wall_utc'],
    available_time_bases: { events: { available: true, time_bases_in_first_record: ['backend_monotonic_s', 'sim_time_s', 'wall_utc'] } },
    units: { '*_s': 'seconds', '*_ms': 'milliseconds' }, browser_arrival_order_is_not_used: true, synchronized_across_streams: false,
  },
  action_semantics: { recorded_target: ['actuator_reference'], command_intent: ['requested'], execution_feedback: ['feedback'], recorded_state: ['feedback_initial'], lifecycle: ['recording_start'], note: 'never promotes one into another', categories_are_by_recorded_event_type: true },
  recorded_model_identity: { model_id: 'landerpi_mecanum_dynamic_5dof_3ca3d6d0a92a', model_sha256: '3ca3'.padEnd(64, '0'), scene_id: 'mobile_pick', map_mode: 'unavailable', truth_access: 'GT_DEBUG', run_contract_version: 'mobilecar-1.0', source: 'run manifest.json as recorded' },
  three_d_replay: {
    status: 'identity_verified_rendering_unverified', recorded_model_sha256: '3ca3'.padEnd(64, '0'), reference_model_sha256: '3ca3'.padEnd(64, '0'),
    recorded_scene_id: 'mobile_pick', reference_scene_id: 'mobile_pick', model_match: 'match', scene_match: 'match',
    recorded_transforms_available: true, live_geometry_or_actual_may_be_applied: false, reasons: ['mesh identity can be reused'], still_available: ['metadata', 'events'],
  },
  platform_association: { known: false, validated_snapshot_ref: null, platform_session_id: null, reason: 'legacy_native_record_without_platform_sidecar', policy: 'no platform configuration association is invented' },
  training_qualification: { declared_eligibility_present: true, training_qualified: null, export_valid: null, quality_report_present: true, blocks_raw_read: false, note: 'training_qualified=false never blocks a qualified raw read' },
  media_summary: { assets_root: 'assets/', uri_convention: 'assets/<kind>/<file>', declared_sha256_source: 'episode_complete.json checksums when present', verification: 'digests recomputed only for served assets', kinds: { rgb: { count: 303, bytes_total: 10862481, sample: [mediaSample], sample_truncated: true, declared_sha256_coverage: '20/20' } } },
  capability_limits: ['no replay execution'],
  ...patch,
});
const pageFixture = (records: RecordPageDto['records'], patch: Partial<RecordPageDto> = {}): RecordPageDto => ({
  schema_version: 'unirobot-mobilecar-episode-read-1', read_only: true, source: SOURCE, retrieved_at: '2026-10-25T05:25:58Z',
  identity: { run_id: RUN, episode_id: EPISODE, native_contract_version: 'mobilecar-1.0' },
  stream: { stream_id: 'events', relative_path: 'events.jsonl', format: 'jsonl', file_bytes: 12472413 },
  paging: { limit: 2, offset: 0, returned: records.length, scanned_lines: 3, skipped_before_offset: 0, next_offset: 2, has_more: true },
  cursor: { order: 'native_append_order', first_line_index: 0, last_line_index: 1, first_event_seq: 1, last_event_seq: 2, line_index_is_not_a_clock: true },
  time: { selected_time_base: null, time_from: null, time_to: null, units: 'seconds for *_s', records_without_the_selected_base: 0, synchronized_across_streams: false },
  records,
  integrity: { corrupt_lines: [], lines_over_read_size_limit: [], declared_status: { recording_status: 'COMPLETE', audit_status: 'COMPLETE', termination_reason: 'x', declaration_only: true }, scope: 'records returned by this page only', not_verified: ['records outside this page'] },
  ...patch,
});

let calls: { url: string; init: RequestInit }[] = [];
beforeEach(() => {
  calls = [];
  globalThis.fetch = vi.fn(async (input: string, init: RequestInit = {}) => {
    calls.push({ url: input, init });
    if (input.includes('/assets/assets/rgb/missing')) return new Response(JSON.stringify({ detail: { code: 'episode_asset_missing', message: 'asset is not present in the record', read_only: true } }), { status: 404, headers: { 'content-type': 'application/json' } });
    if (input.includes('/assets/assets/rgb/')) {
      return new Response(new Uint8Array([1, 2, 3]), { status: 200, headers: { 'content-type': 'image/png', 'x-episode-asset-sha256': 'a'.repeat(64), 'x-episode-run-id': RUN } });
    }
    if (input.startsWith('/api/v1/episodes/')) return new Response(JSON.stringify(detailFixture()), { status: 200, headers: { 'content-type': 'application/json' } });
    return new Response(JSON.stringify(listFixture), { status: 200, headers: { 'content-type': 'application/json' } });
  }) as unknown as typeof fetch;
});
afterEach(() => { vi.restoreAllMocks(); });

describe('episode-read-1 client', () => {
  it('is GET-only, carries run_id and never invents one', async () => {
    const api = new PlatformEpisodeApi();
    await api.listEpisodes({ limit: 2, offset: 0, recording_status: 'FAILED' }, new AbortController().signal);
    expect(calls[0].url).toBe('/api/v1/episodes?limit=2&offset=0&recording_status=FAILED');
    expect(calls[0].init.method).toBe('GET');
    await api.getEpisode(EPISODE, RUN, new AbortController().signal);
    expect(calls[1].url).toBe(`/api/v1/episodes/${encodeURIComponent(EPISODE)}?run_id=${encodeURIComponent(RUN)}`);
    await api.getEpisode(EPISODE, null, new AbortController().signal);
    expect(calls[2].url).not.toContain('run_id');
    await api.readRecords({ episodeId: EPISODE, runId: RUN, streamId: 'events', limit: 3, offset: 6, timeBase: 'sim_time_s', timeFrom: 1.5 }, new AbortController().signal);
    expect(calls[3].url).toContain('/streams/events/records?run_id=');
    expect(calls[3].url).toContain('time_base=sim_time_s&time_from=1.5');
    const value = await api.asset(EPISODE, RUN, 'assets/rgb/episode_x.png', null, new AbortController().signal);
    expect(value.mediaType).toBe('image/png');
    expect(value.assetSha256).toBe('a'.repeat(64));
    expect(value.runHeader).toBe(RUN);
  });
  it('refuses a payload that is not the declared read contract', async () => {
    const api = new PlatformEpisodeApi();
    await expect(api.listEpisodes({ limit: 1 }, new AbortController().signal)).resolves.toBeDefined();
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify({ schema_version: 'other', read_only: true }), { status: 200, headers: { 'content-type': 'application/json' } })) as unknown as typeof fetch;
    await expect(api.listEpisodes({}, new AbortController().signal)).rejects.toBeInstanceOf(EpisodeContractError);
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify({ schema_version: 'unirobot-mobilecar-episode-read-1', read_only: false }), { status: 200, headers: { 'content-type': 'application/json' } })) as unknown as typeof fetch;
    await expect(api.listEpisodes({}, new AbortController().signal)).rejects.toThrow(/read_only/);
  });
  it('surfaces the reader’s own error codes without substituting data', async () => {
    const api = new PlatformEpisodeApi();
    await expect(api.asset(EPISODE, RUN, 'assets/rgb/missing.png', null, new AbortController().signal)).rejects.toBeInstanceOf(ApiError);
  });
});

describe('integrity layering', () => {
  it('keeps the five layers separate and never says everything is complete', () => {
    const facets = integrityFacets(detailFixture());
    expect(facets.map((facet) => facet.key)).toEqual(['declared', 'lifecycle', 'tail', 'checksum', 'uncovered']);
    const checksum = facets.find((facet) => facet.key === 'checksum');
    expect(checksum?.tone).toBe('bad');
    expect(checksum?.value).toContain('不得读作');
    expect(checksum?.value).not.toContain('已验证完整');
    expect(facets.find((facet) => facet.key === 'uncovered')?.note).toContain('files not opened by this request');
    expect(facets.find((facet) => facet.key === 'tail')?.tone).toBe('ok');
    expect(facets.find((facet) => facet.key === 'lifecycle')?.value).toContain('complete');
  });
  it('explains the known stale self-check only inside its evidence scope', () => {
    expect(checksumFinding(detailFixture()).pattern).toBe('known_stale_self_check');
    const failed = detailFixture({ declared: { ...detailFixture().declared, recording_status: 'FAILED', audit_status: 'INCOMPLETE' } });
    expect(checksumFinding(failed).pattern).toBe('unexplained');
    expect(checksumFinding(failed).note).toContain('不归因于同一历史问题');
    const otherFile = detailFixture();
    otherFile.integrity.checksum_verification!.mismatched = [{ relative_path: 'events.jsonl', declared_sha256: 'x', actual_sha256: 'y' }];
    expect(checksumFinding(otherFile).pattern).toBe('unexplained');
    const clean = detailFixture();
    clean.integrity.checksum_verification = { declared_entries: 2, matched: [{ relative_path: 'episode.json', declared_sha256: 'a', actual_sha256: 'a' }], mismatched: [], verdict: 'all_matched' };
    expect(checksumFinding(clean).pattern).toBe('verified');
    const nothing = detailFixture();
    nothing.integrity.checksum_verification = { declared_entries: 0, matched: [], mismatched: [], verdict: 'none' };
    expect(checksumFinding(nothing).pattern).toBe('none');
    expect(checksumFinding(nothing).allCompleteClaimForbidden).toBe(true);
  });
  it('reports a FAILED record with a present tail as incomplete, not broken or complete', () => {
    const failed = detailFixture({
      declared: { ...detailFixture().declared, recording_status: 'FAILED', audit_status: 'INCOMPLETE', termination_reason: 'RECORDING_FAILED', complete_tail_file_present: true },
    });
    failed.integrity.status = 'incomplete_terminal_recorded';
    const facets = integrityFacets(failed);
    expect(facets.find((facet) => facet.key === 'lifecycle')?.tone).toBe('bad');
    expect(facets.find((facet) => facet.key === 'lifecycle')?.value).toContain('incomplete_terminal_recorded');
    expect(facets.find((facet) => facet.key === 'tail')?.tone).toBe('ok');
  });
});

describe('time, identity, media and 3D semantics', () => {
  it('never pads a missing time to zero and keeps the declared unit and clock', () => {
    const missing = timeFieldOf({ event_seq: 4 }, 'sim_time_s');
    expect(missing.present).toBe(false);
    expect(missing.display).toContain('无 sim_time_s');
    expect(missing.display).not.toBe('0');
    const seconds = timeFieldOf({ sim_time_s: 0.01, clock_id: 'sim' }, 'sim_time_s');
    expect(seconds).toMatchObject({ present: true, unit: '秒', clockId: 'sim' });
    const wall = timeFieldOf({ wall_utc: '2026-10-17T16:10:29Z' }, 'wall_utc');
    expect(wall.unit).toContain('ISO-8601');
    expect(timeFieldOf({ measurement_time_s: 426494.2 }, 'measurement_time_s').display).toBe('426494.200000');
    expect(unitOf('arrival_time_s')).toBe('秒');
    expect(presentTimeBases([{ sim_time_s: 1 }, { arrival_time_s: 2 }, {}])).toEqual(['sim_time_s', 'arrival_time_s']);
  });
  it('keeps identity composite and never uses the display name as a key', () => {
    const row = rowViews(listFixture as unknown as EpisodeListDto)[0];
    expect(row.identityText).toBe(`${SOURCE.source_id} · ${RUN} · ${EPISODE}`);
    expect(row.title).toBe('G2A server RGB-D profile validation');
    expect(row.runId).toBe(RUN);
    const streams = streamViews(detailFixture());
    expect(streams[1]).toMatchObject({ streamId: 'tail', available: false, declaredBases: null });
    expect(streams[0].declaredBases).toContain('sim_time_s');
  });
  it('separates an empty filtered page from an archive with nothing readable', () => {
    const unfiltered = { ...listFixture, episodes: [], paging: { ...listFixture.paging, returned: 0, total_matches: 0, next_offset: null } } as unknown as EpisodeListDto;
    expect(emptyListKind(unfiltered)).toBe('no-records');
    expect(emptyListKind({ ...unfiltered, filters: { run_id: null, recording_status: 'FAILED', episode_id: null } })).toBe('no-match');
    expect(emptyListKind({ ...unfiltered, filters: { run_id: 'run_x', recording_status: null, episode_id: null } })).toBe('no-match');
    expect(emptyListKind({ ...unfiltered, filters: { run_id: null, recording_status: null, episode_id: 'episode_x' } })).toBe('no-match');
  });
  it('reads media only from the record reference and only claims a declared digest when carried', () => {
    const record = { sample_id: 'rgbd_e3213e6cb64b4cd693c17d485d064d09', sensor_kind: 'rgb', asset_uri: mediaSample.relative_path, valid_mask_uri: 'assets/masks/other_valid.png' };
    const refs = mediaRefsOf(record, detailFixture());
    expect(refs.map((ref) => ref.role)).toEqual(['primary', 'valid_mask']);
    expect(refs[0].declaredSha256).toBe('c'.repeat(64));
    expect(refs[0].kind).toBe('rgb');
    expect(refs[1].hasDeclaredSha).toBe(false);
    expect(mediaRefsOf({ sample_id: 'laser_1' }, detailFixture())).toEqual([]);
  });
  it('states the history 3D limitation and the unknown legacy association', () => {
    const notice = threeDNotice(detailFixture());
    expect(notice.blocked).toBe(true);
    expect(notice.text).toContain('不等于渲染正确性已验证');
    expect(notice.text).toContain('live_geometry_or_actual_may_be_applied=false');
    expect(associationNotice(detailFixture())).toContain('legacy_native_record_without_platform_sidecar');
  });
  it('echoes server-declared supported lists and candidate runs instead of guessing', () => {
    const badBase = new ApiError(400, 'time_base_unsupported', 'unknown time base: browser_arrival', { code: 'time_base_unsupported', supported: ['sim_time_s', 'wall_utc'] });
    expect(describeHistoryError(badBase)).toContain('supported=sim_time_s,wall_utc');
    const digest = new ApiError(409, 'episode_asset_digest_mismatch', 'asset digest does not match', { code: 'episode_asset_digest_mismatch', actual: 'a'.repeat(64) });
    expect(describeHistoryError(digest)).toContain('实际摘要');
    const ambiguous = new ApiError(409, 'episode_id_ambiguous', 'episode id exists under multiple runs', { code: 'episode_id_ambiguous', runs: ['run_a', 'run_b'] });
    expect(isAmbiguous(ambiguous)).toBe(true);
    expect(ambiguousRuns(ambiguous)).toEqual(['run_a', 'run_b']);
    expect(describeHistoryError(ambiguous)).toContain('显示名不是唯一键');
  });
  it('shows the record page integrity without promoting anything', () => {
    const page = pageFixture([
      { line_index: 0, record: { event_seq: 1, event_type: 'recording_start', backend_monotonic_s: 426494.22, wall_utc: '2026-10-17T16:10:29Z' } },
      { line_index: 1, record: { event_seq: 2, sensor_kind: 'rgb', sample_id: 'rgbd_x', asset_uri: mediaSample.relative_path } },
    ]);
    expect(page.records).toHaveLength(2);
    expect(page.cursor.line_index_is_not_a_clock).toBe(true);
    expect(page.time.synchronized_across_streams).toBe(false);
    expect(page.integrity.declared_status?.declaration_only).toBe(true);
    expect(page.integrity.not_verified).toContain('records outside this page');
    expect(presentTimeBases(page.records.map((item) => item.record))).toEqual(['wall_utc', 'backend_monotonic_s']);
  });
});
