import { describe, expect, it } from 'vitest';
import {
  beginAvailability, codeHint, endAvailability, endLayers, lastAttempt, newRequestId,
  parkingVerdict, recordingVerdict, stopAvailability, stopLayers,
} from '../src/workbench/lifecycle';
import type { ParkingEvidence, RecordingEndReceipt, SessionCurrent, StopReceipt } from '../src/adapters/platform-config';

const current = (patch: Partial<SessionCurrent> = {}): SessionCurrent => ({
  source: 'live_native_read_only', observed_at: '2026-10-24T09:00:00+00:00', valid: true, status: 'started', error: null,
  runtime_identity: { run_id: 'run-1', backend_generation: 3, episode_id: 'ep-1' }, runtime_identity_matches: true,
  binding: { binding_id: 'bind-1', state: 'verified', matches: true, readback_sha256: 'd-1', error: null },
  snapshot_id: 'cs-1', snapshot_eligible: true, recipe_fingerprint_matches: true,
  control_scope_granted: ['base', 'arm'], recording_required_for_motion: true, recording_begin_required: true,
  recording: { status: 'ARMED', episode_id: 'ep-1', segment_id: 'seg-1', command_capture_ready: true, error: null, ready: true },
  owner: { state: 'held', session_id: 'ps-1', lease_expires_at_backend_monotonic_s: 100, lease_exposed: true },
  safety_latched: false, recording_ready: true, motion_ready: true, start_available: false, recording_begin_available: true,
  stop_available: true, recording_end_available: true, session_stop_protocol: 'm1-stop-1', recording_end_protocol: 'm1-end-1',
  last_stop_code: null, last_end_code: null, recording_integrity: null, blockers: [], ...patch,
});
const parking = (patch: Partial<ParkingEvidence> = {}): ParkingEvidence => ({
  confirmed: true, waited_ms: 120, timeout_ms: 5000, base_stopped: true, base_stop_latched: true,
  base_velocity_m_s: [0, 0, 0], arm_max_joint_velocity_rad_s: 0.001, control_tick_id: 'tick-1',
  observed_at_backend_monotonic_s: 1234.5, scope_coverage: { base: 'confirmed', arm: 'confirmed', gripper: 'not_observed' },
  observed_confirmed: true, coverage_complete: false, coverage_note: 'gripper 无独立反馈', ...patch,
});
const stopReceipt = (patch: Partial<StopReceipt> = {}): StopReceipt => ({
  accepted: true, code: 'stopped', reason: 'OPERATOR_STOP', protocol: 'm1-stop-1', request_id: 'front-stop-1', replayed: false,
  binding_id: 'bind-1', session_id: 'ps-1', config_fingerprint: 'fp-1', run_id: 'run-1', backend_generation: 3, episode_id: 'ep-1',
  dispatch: { dispatched: true, command_id: 'cmd-1', status: 'DISPATCHED', status_detail: 'queued' }, parking: parking(),
  owner_cleared_after_stop: false, safety_latched: false, recording_status: 'ARMED', recording_segment_id: 'seg-1',
  recording_touched: false, motion_restored: false, observed_at: '2026-10-24T09:00:01+00:00', ...patch,
});
const finalize = (patch: Partial<RecordingEndReceipt['finalize']> = {}): RecordingEndReceipt['finalize'] => ({
  completed: true, error: null, terminal_event_written: true, complete_tail: true, recording_status: 'IDLE', audit_status: 'COMPLETE',
  event_count: 12, dropped_events: 0, storage_ref: 'var/episodes/ep-1', episode_complete_sha256: 'a'.repeat(64),
  checksummed_artifacts: 5, preserved_records: true, ...patch,
});
const endReceipt = (patch: Partial<RecordingEndReceipt> = {}): RecordingEndReceipt => ({
  accepted: true, code: 'ended', reason: 'OPERATOR_FINISHED', protocol: 'm1-end-1', request_id: 'front-end-1', replayed: false,
  binding_id: 'bind-1', session_id: 'ps-1', config_fingerprint: 'fp-1', run_id: 'run-1', backend_generation: 3, episode_id: 'ep-1',
  dispatch: { dispatched: true, command_id: 'cmd-1', status: 'DISPATCHED', status_detail: 'queued' }, parking: parking(),
  recording_status: 'IDLE', recording_segment_id: 'seg-1', active_segment_id: null, binding_state: 'verified',
  drain: { completed: true, fanout_drained: true, recorder_queue_empty: true, queued_events: 0, dropped_events: 0 },
  finalize: finalize(), integrity: 'complete', owner_cleared_after_stop: false, safety_latched: false,
  recording_touched: true, motion_restored: false, reset_issued: false, safety_cleared: false, owner_acquired: false,
  observed_at: '2026-10-24T09:00:02+00:00', ...patch,
});
const layer = (layers: ReturnType<typeof stopLayers> | ReturnType<typeof endLayers>, key: string) => layers.find((item) => item.key === key)!;

describe('lifecycle availability comes only from current', () => {
  it('keeps robot STOP available without motion_ready or recording_ready', () => {
    const gate = stopAvailability(current({ motion_ready: false, recording_ready: false, status: 'started' }));
    expect(gate.available).toBe(true);
  });
  it('blocks STOP when the platform has not declared the stop protocol', () => {
    const gate = stopAvailability(current({ session_stop_protocol: null, stop_available: false }));
    expect(gate.available).toBe(false);
    expect(gate.reason).toContain('session_stop_protocol');
  });
  it('never infers availability from a missing or invalid current', () => {
    expect(stopAvailability(undefined).available).toBe(false);
    expect(stopAvailability(current({ valid: false, error: 'native_unreachable' })).reason).toContain('current.valid=false');
    expect(endAvailability(current({ recording_end_available: false })).reason).toContain('recording_end_available=false');
    expect(beginAvailability(current({ recording_begin_available: false })).available).toBe(false);
  });
  it('reads begin availability without inventing a protocol field', () => {
    expect(beginAvailability(current()).available).toBe(true);
    expect(beginAvailability(current({ valid: false })).available).toBe(false);
  });
});

describe('request identity per intent', () => {
  it('gives every action a distinct request id and keeps the action prefix', () => {
    const stop = newRequestId('stop'); const again = newRequestId('stop'); const end = newRequestId('end');
    expect(stop).not.toBe(again);
    expect(stop.startsWith('front-stop-')).toBe(true);
    expect(end.startsWith('front-end-')).toBe(true);
    expect(stop.length).toBeLessThanOrEqual(128);
  });
  it('keeps refused, unknown and replayed codes separately explainable', () => {
    expect(codeHint('stop_unsupported')).toContain('不支持');
    expect(codeHint('session_not_stoppable')).toContain('已关闭');
    expect(codeHint('result_unknown')).toContain('不自动重发');
    expect(codeHint('end_already_finalized')).toContain('重放');
    expect(codeHint('end_finalize_failed')).not.toBe(codeHint('ended_incomplete_terminal'));
  });
});

describe('receipts stay layered', () => {
  it('does not read accepted or base_stopped as whole-machine stop', () => {
    const layers = stopLayers(stopReceipt({ accepted: true, code: 'stopped' }));
    expect(layer(layers, 'accepted').tone).toBe('ok');
    expect(layer(layers, 'parking-verdict').tone).toBe('unknown');
    expect(layer(layers, 'parking-verdict').text).toContain('不宣称整机停稳');
    expect(layer(layers, 'side-effects').text).toContain('recording_touched=false');
    expect(parkingVerdict(parking({ confirmed: false })).tone).toBe('bad');
    expect(parkingVerdict(parking({ confirmed: true, coverage_complete: true })).tone).toBe('ok');
  });
  it('separates dispatch, parking and finalize failure modes', () => {
    const notSent = stopLayers(stopReceipt({ code: 'submit_failed', dispatch: { dispatched: false, command_id: null, status: 'submit_failed', status_detail: 'queue full' } }));
    expect(layer(notSent, 'dispatch').tone).toBe('bad');
    const unfinalized = endLayers(endReceipt({ code: 'end_finalize_failed', integrity: 'finalize_failed_missing_tail', accepted: true,
      finalize: finalize({ completed: false, error: 'synthetic disk fault', complete_tail: false, terminal_event_written: false, audit_status: 'UNKNOWN', episode_complete_sha256: null }) }));
    expect(layer(unfinalized, 'finalize').tone).toBe('bad');
    expect(layer(unfinalized, 'recording-verdict').text).toContain('缺尾记录');
    expect(layer(unfinalized, 'task-verdict').text).toContain('finalize 失败');
  });
  it('keeps tail-but-incomplete different from a complete recording', () => {
    const incomplete = endLayers(endReceipt({ code: 'ended_incomplete_terminal', integrity: 'incomplete_terminal_recorded' }));
    expect(layer(incomplete, 'parking-verdict').key).toBe('parking-verdict');
    expect(layer(incomplete, 'recording-verdict').tone).toBe('bad');
    expect(layer(incomplete, 'recording-verdict').text).toContain('INCOMPLETE');
    expect(layer(incomplete, 'task-verdict').tone).toBe('unknown');
    expect(recordingVerdict(endReceipt()).tone).toBe('ok');
  });
  it('shows an already-finalized replay without claiming a second dispatch', () => {
    const replay = endLayers(endReceipt({ code: 'end_already_finalized', replayed: true,
      dispatch: { dispatched: false, command_id: null, status: 'not_sent', status_detail: 'segment already finalized' } }));
    expect(layer(replay, 'dispatch').text).toContain('dispatched=false');
    expect(layer(replay, 'accepted').text).toContain('replayed=true');
    expect(layer(replay, 'task-verdict').text).toContain('磁盘重放');
  });
  it('reports fanout lag without letting it gate the drain layer', () => {
    const layers = endLayers(endReceipt({ drain: { completed: true, fanout_drained: false, recorder_queue_empty: true, queued_events: 0, dropped_events: 0 } }));
    expect(layer(layers, 'drain').tone).toBe('ok');
    expect(layer(layers, 'drain').text).toContain('不参与门控');
  });
  it('keeps the last attempt visible for unknown results', () => {
    expect(lastAttempt([{ at: '1', request_id: 'r1', result: 'result_unknown' }, { at: '2', request_id: 'r2', result: 'stopped' }])?.request_id).toBe('r2');
    expect(lastAttempt(undefined)).toBeNull();
  });
});
