import type { LifecycleAttempt, ParkingEvidence, RecordingEndReceipt, SessionCurrent, StopReceipt } from '../adapters/platform-config';

export type LifecycleAction = 'begin' | 'stop' | 'end';
export type Tone = 'ok' | 'bad' | 'unknown';
export interface Availability { available: boolean; reason: string }
export interface Layer { key: string; label: string; tone: Tone; text: string }

const keys = (current: SessionCurrent) => (current.blockers || []).map((item) => item.key).join(', ') || '[]';

/** Availability comes only from the platform's read-only current; nothing here infers it from other flags. */
export function stopAvailability(current: SessionCurrent | null | undefined): Availability {
  if (!current) return { available: false, reason: '尚未读取 current：不能推断机器人 STOP 可用' };
  if (!current.valid) return { available: false, reason: `current.valid=false · status=${current.status}${current.error ? ` · ${current.error}` : ''}` };
  if (!current.session_stop_protocol) return { available: false, reason: 'native 未声明 session_stop_protocol，当前运行实例不支持机器人 STOP' };
  if (!current.stop_available) return { available: false, reason: `current.stop_available=false · status=${current.status} · blockers=${keys(current)}` };
  return { available: true, reason: `协议 ${current.session_stop_protocol}` };
}

export function beginAvailability(current: SessionCurrent | null | undefined): Availability {
  if (!current) return { available: false, reason: '尚未读取 current：不能推断开始录制可用' };
  if (!current.valid) return { available: false, reason: `current.valid=false · status=${current.status}` };
  if (!current.recording_begin_available) return { available: false, reason: `current.recording_begin_available=false · status=${current.status} · blockers=${keys(current)}` };
  return { available: true, reason: 'current.recording_begin_available=true' };
}

export function endAvailability(current: SessionCurrent | null | undefined): Availability {
  if (!current) return { available: false, reason: '尚未读取 current：不能推断结束录制可用' };
  if (!current.valid) return { available: false, reason: `current.valid=false · status=${current.status}${current.error ? ` · ${current.error}` : ''}` };
  if (!current.recording_end_protocol) return { available: false, reason: 'native 未声明 recording_end_protocol，当前运行实例不支持结束录制' };
  if (!current.recording_end_available) return { available: false, reason: `current.recording_end_available=false · status=${current.status} · 本 Session 可能没有 begun segment · blockers=${keys(current)}` };
  return { available: true, reason: `协议 ${current.recording_end_protocol}` };
}

export function newRequestId(action: LifecycleAction): string {
  const uuid = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `front-${action}-${uuid}`;
}

export function codeHint(code: string): string {
  switch (code) {
    case 'stopped': return '机器人 STOP 已受理并下发';
    case 'ended': return '录制已结束并 finalize';
    case 'begun': return '录制已开始（本 Session 自己的 segment）';
    case 'ended_parking_unconfirmed': return '收尾完成，但停稳证据不足：不能当作已整机停稳';
    case 'ended_incomplete_terminal': return '已写尾记录，但审计为 INCOMPLETE：录制不完整';
    case 'end_finalize_failed': return 'finalize 失败，可能缺尾记录：录制完整性未成立';
    case 'end_already_finalized': return '该 segment 已 finalize：本次为磁盘重放，未产生第二个终态';
    case 'end_segment_mismatch': return '目标 segment 与当前活动 segment 不一致：未执行';
    case 'end_binding_not_found': case 'end_binding_mismatch': return 'Session binding 不匹配：未执行';
    case 'stop_runtime_identity_mismatch': return 'native 身份与请求身份不一致：未下发';
    case 'stop_unsupported': return '当前运行实例不支持机器人 STOP（recipe/native 未声明协议）';
    case 'recording_end_unsupported': return '当前运行实例不支持结束录制（recipe/native 未声明协议）';
    case 'session_not_stoppable': return 'Session 已关闭：平台拒绝该动作，未产生副作用';
    case 'recording_not_begun': return '本 Session 尚未 begin 录制：不能结束';
    case 'result_unknown': return '结果未知：传输失败或超时，需回读存档与 current，不自动重发';
    default: return code || '无 code';
  }
}

function parkingLayer(parking: ParkingEvidence): Layer {
  const coverage = Object.entries(parking.scope_coverage || {}).map(([scope, state]) => `${scope}=${state}`).join(' · ') || '无逐项反馈';
  const speed = parking.arm_max_joint_velocity_rad_s === null ? '未观测' : `${parking.arm_max_joint_velocity_rad_s.toFixed(4)} rad/s`;
  const text = `confirmed=${String(parking.confirmed)} · base_stopped=${String(parking.base_stopped)} · base_stop_latched=${String(parking.base_stop_latched)}`
    + ` · arm_max_v=${speed} · waited=${parking.waited_ms}ms/${parking.timeout_ms}ms · observed_confirmed=${String(parking.observed_confirmed)}`
    + ` · coverage_complete=${String(parking.coverage_complete)} · ${coverage} · ${parking.coverage_note}`;
  const tone: Tone = parking.confirmed && parking.coverage_complete ? 'ok' : parking.confirmed ? 'unknown' : 'bad';
  return { key: 'parking', label: '停车反馈与覆盖', tone, text };
}

export function parkingVerdict(parking: ParkingEvidence): Layer {
  if (parking.confirmed && parking.coverage_complete) return { key: 'parking-verdict', label: '停车结论', tone: 'ok', text: '已确认停稳，且所有作用域均有反馈' };
  if (parking.confirmed) return { key: 'parking-verdict', label: '停车结论', tone: 'unknown', text: `已观测到停稳证据，但覆盖不完整（${parking.coverage_note}）：不宣称整机停稳` };
  return { key: 'parking-verdict', label: '停车结论', tone: 'bad', text: '停车未确认：反馈缺失或超时，不推断已停稳' };
}

export function recordingVerdict(receipt: RecordingEndReceipt): Layer {
  const finalize = receipt.finalize;
  const facts = `integrity=${receipt.integrity} · terminal_event_written=${String(finalize.terminal_event_written)}`
    + ` · complete_tail=${String(finalize.complete_tail)} · audit=${finalize.audit_status} · events=${String(finalize.event_count)}`
    + ` · artifacts=${finalize.checksummed_artifacts} · preserved=${String(finalize.preserved_records)}`
    + ` · sha256=${finalize.episode_complete_sha256 ?? 'null'} · storage=${finalize.storage_ref ?? 'null'}`
    + (finalize.error ? ` · error=${finalize.error}` : '');
  if (receipt.integrity === 'complete') return { key: 'recording-verdict', label: '录制完整性', tone: 'ok', text: `录制完整（有尾且摘要一致）· ${facts}` };
  if (receipt.integrity === 'incomplete_terminal_recorded') return { key: 'recording-verdict', label: '录制完整性', tone: 'bad', text: `有尾记录但审计 INCOMPLETE，不能称录制完整 · ${facts}` };
  if (receipt.integrity === 'finalize_failed_missing_tail') return { key: 'recording-verdict', label: '录制完整性', tone: 'bad', text: `收尾失败且缺尾记录 · ${facts}` };
  return { key: 'recording-verdict', label: '录制完整性', tone: 'unknown', text: `完整性未知（complete_tail 单独不构成成功）· ${facts}` };
}

export function stopLayers(receipt: StopReceipt): Layer[] {
  return [
    { key: 'accepted', label: '受理', tone: receipt.accepted ? 'ok' : 'bad',
      text: `accepted=${String(receipt.accepted)} · code=${receipt.code} · replayed=${String(receipt.replayed)} · request_id=${receipt.request_id} · protocol=${receipt.protocol}` },
    { key: 'dispatch', label: 'STOP 下发', tone: receipt.dispatch.dispatched ? 'ok' : 'bad',
      text: `dispatched=${String(receipt.dispatch.dispatched)} · status=${receipt.dispatch.status} · command_id=${receipt.dispatch.command_id ?? 'null'} · ${receipt.dispatch.status_detail}` },
    parkingLayer(receipt.parking),
    { key: 'side-effects', label: '副作用边界', tone: 'unknown',
      text: `recording_touched=${String(receipt.recording_touched)}（STOP 不结束录制） · motion_restored=${String(receipt.motion_restored)} · safety_latched=${String(receipt.safety_latched)} · owner_cleared_after_stop=${String(receipt.owner_cleared_after_stop)} · recording_status=${receipt.recording_status} · segment=${receipt.recording_segment_id ?? 'null'}` },
    { key: 'identity', label: '身份（平台组装）', tone: 'unknown',
      text: `run=${receipt.run_id} · gen=${receipt.backend_generation} · episode=${receipt.episode_id} · binding=${receipt.binding_id ?? 'null'} · config=${receipt.config_fingerprint ?? 'null'} · observed_at=${receipt.observed_at}` },
    parkingVerdict(receipt.parking),
  ];
}

export function endLayers(receipt: RecordingEndReceipt): Layer[] {
  return [
    { key: 'accepted', label: '受理', tone: receipt.accepted ? 'ok' : 'bad',
      text: `accepted=${String(receipt.accepted)} · code=${receipt.code} · replayed=${String(receipt.replayed)} · request_id=${receipt.request_id} · protocol=${receipt.protocol}` },
    { key: 'dispatch', label: 'STOP 下发', tone: receipt.dispatch.dispatched ? 'ok' : 'unknown',
      text: `dispatched=${String(receipt.dispatch.dispatched)} · status=${receipt.dispatch.status} · ${receipt.dispatch.status_detail}` },
    parkingLayer(receipt.parking),
    parkingVerdict(receipt.parking),
    { key: 'drain', label: 'Recorder 排空', tone: receipt.drain.completed && receipt.drain.recorder_queue_empty ? 'ok' : 'bad',
      text: `completed=${String(receipt.drain.completed)} · queue_empty=${String(receipt.drain.recorder_queue_empty)} · queued=${receipt.drain.queued_events} · dropped=${receipt.drain.dropped_events} · fanout_drained=${String(receipt.drain.fanout_drained)}（仅广播滞后，不参与门控）` },
    { key: 'finalize', label: 'finalize 落盘', tone: receipt.finalize.completed ? 'ok' : 'bad',
      text: `completed=${String(receipt.finalize.completed)} · recording_status=${receipt.finalize.recording_status} · segment=${receipt.recording_segment_id ?? 'null'} · active_segment=${receipt.active_segment_id ?? 'null'} · binding_state=${receipt.binding_state}` },
    recordingVerdict(receipt),
    { key: 'task-verdict', label: '动作结论', tone: receipt.code === 'ended' ? 'ok' : receipt.accepted ? 'unknown' : 'bad',
      text: codeHint(receipt.code) },
    { key: 'side-effects', label: '副作用边界', tone: 'unknown',
      text: `reset_issued=${String(receipt.reset_issued)} · safety_cleared=${String(receipt.safety_cleared)} · owner_acquired=${String(receipt.owner_acquired)} · motion_restored=${String(receipt.motion_restored)} · 任务结果不由本界面宣称` },
  ];
}

export function lastAttempt(attempts: LifecycleAttempt[] | undefined): LifecycleAttempt | null {
  return attempts && attempts.length ? attempts[attempts.length - 1] : null;
}
