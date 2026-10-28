// Same-origin client for the M1.2b platform configuration API.
// Draft create/save/validate, snapshot and Session reads, Session prepare/start, and the
// explicit recording lifecycle actions (begin, robot STOP, recording end). Motion, RESET,
// teleop and native command endpoints are never called from here.
export type CheckStatus = 'passed' | 'failed' | 'unsupported' | 'not_checked' | 'warning';
export interface Check { key: string; status: CheckStatus; phase: 'configuration' | 'readiness'; scope: string; detail: string }
export interface BlockingReason { key: string; scope: string; message: string }
export interface ValidationResult {
  validation_id: string; execution_revision: number; fingerprint: string; recipe_fingerprint: string;
  checked_at: string; snapshot_id: string; snapshot_sha256: string; status: 'passed' | 'failed';
  checks: Check[]; execution_eligible: boolean; blocking_reasons: BlockingReason[];
  validated_snapshot_id: string | null; reused: boolean;
}
export interface DraftValidation { status: 'unvalidated' | 'stale' | 'passed' | 'failed'; result: ValidationResult | null }
export interface DraftRecord {
  draft_id: string; draft_revision: number; execution_revision: number;
  fingerprint: string; recipe_fingerprint: string;
  preset: { preset_id: string; native_commit: string; manifest_sha256: string; recipe: Record<string, unknown>; expected: Record<string, unknown> };
  name: string; description: string; validation: DraftValidation;
  created_at: string; updated_at: string;
}
export interface SourceRef { role: string; path: string; sha256: string }
export interface KinematicsEvidence {
  profile_id: string; digest: string; authority: string;
  joint_order_consistent: boolean; user_limits_consistent: boolean; tcp_mount_consistent: boolean;
  camera_mount_consistent: boolean; gripper_limits_consistent: boolean;
  max_user_limit_error_rad: number; limitations: string[];
}
export interface SnapshotRecord {
  schema_version: string; snapshot_id: string; snapshot_sha256: string; created_at: string;
  draft_id: string; draft_revision: number; execution_revision: number;
  fingerprint: string; recipe_fingerprint: string;
  recipe: { recipe_id?: string; recipe_revision?: number; sources?: SourceRef[]; [key: string]: unknown };
  observation: Record<string, unknown>; kinematics: KinematicsEvidence;
  checks: Check[]; validation_status: 'passed' | 'failed'; validation_scope: string;
  execution_eligible: boolean; validated_snapshot_id: string | null; blocking_reasons: BlockingReason[];
}
export interface NativeBinding {
  status: 'unverified' | 'verified' | 'unsupported'; protocol: string | null; binding_id: string | null;
  native_session_id: string | null; config_fingerprint: string | null;
  expires_at_backend_monotonic_s: number | null; verified_at: string | null;
  readback_sha256: string | null; reason: string | null;
}
export interface StartBlock { key: string; scope: 'platform' | 'native' | 'recording'; message: string }
export interface OwnerLease {
  state: 'not_acquired' | 'held' | 'unknown'; session_id: string | null;
  lease_expires_at_backend_monotonic_s: number | null;
}
export interface SessionExecution {
  control_scope_granted: string[]; owner: OwnerLease;
  recording_required_for_motion: boolean; recording_begin_required: boolean;
  recording_ready: boolean; motion_ready: boolean; motion_blockers: string[];
  observed_at: string; source: 'prepared' | 'native_start' | 'native_recording_begin';
}
export interface StartReceipt {
  binding_id: string; native_session_id: string; run_id: string; backend_generation: number; episode_id: string;
  config_fingerprint: string; started_at_backend_monotonic_s: number;
  control_scope_granted: string[]; recording_required_for_motion: boolean; recording_begin_required: boolean;
  owner_state: string; owner_session_id: string | null; lease_expires_at_backend_monotonic_s: number | null;
  recording_ready: boolean; motion_ready: boolean; motion_blockers: string[];
}
export interface StartAttempt { at: string; result: 'refused' | 'started' | 'failed'; blocking: StartBlock[]; detail?: string }
export interface RecordingAttempt { at: string; result: 'begun' | 'refused' | 'failed'; reason?: string }
export interface RecordingBeginReceipt {
  binding_id: string; native_session_id: string; run_id: string; backend_generation: number; episode_id: string;
  config_fingerprint: string; recording_segment_id: string; recording_status: string;
  command_capture_ready: boolean; recording_start_event_seq: number;
  initial_snapshot_sha256: string; durable_start_records: boolean; started_at_backend_monotonic_s: number;
}
export interface CurrentBinding {
  binding_id: string | null; state: string; matches: boolean; readback_sha256: string | null; error: string | null;
}
export interface CurrentRecording {
  status: string; episode_id: string | null; segment_id: string | null;
  command_capture_ready: boolean; error: string | null; ready: boolean;
}
export interface CurrentOwner {
  state: string; session_id: string | null;
  lease_expires_at_backend_monotonic_s: number | null; lease_exposed: boolean;
}
export interface SessionCurrent {
  source: 'live_native_read_only'; observed_at: string; valid: boolean; status: string; error: string | null;
  runtime_identity: { run_id: string; backend_generation: number; episode_id: string };
  runtime_identity_matches: boolean; binding: CurrentBinding;
  snapshot_id: string; snapshot_eligible: boolean; recipe_fingerprint_matches: boolean;
  control_scope_granted: string[]; recording_required_for_motion: boolean; recording_begin_required: boolean;
  recording: CurrentRecording; owner: CurrentOwner; safety_latched: boolean;
  recording_ready: boolean; motion_ready: boolean; start_available: boolean; recording_begin_available: boolean;
  stop_available: boolean; recording_end_available: boolean;
  session_stop_protocol: string | null; recording_end_protocol: string | null;
  last_stop_code: string | null; last_end_code: string | null; recording_integrity: string | null;
  blockers: StartBlock[];
}
export interface StopDispatchEvidence { dispatched: boolean; command_id: string | null; status: string; status_detail: string }
export interface ParkingEvidence {
  confirmed: boolean; waited_ms: number; timeout_ms: number; base_stopped: boolean | null; base_stop_latched: boolean | null;
  base_velocity_m_s: number[]; arm_max_joint_velocity_rad_s: number | null; control_tick_id: string | null;
  observed_at_backend_monotonic_s: number | null; scope_coverage: Record<string, string>;
  observed_confirmed: boolean; coverage_complete: boolean; coverage_note: string;
}
export interface RecordingDrainEvidence { completed: boolean; fanout_drained: boolean; recorder_queue_empty: boolean; queued_events: number; dropped_events: number }
export interface RecordingFinalizeEvidence {
  completed: boolean; error: string | null; terminal_event_written: boolean; complete_tail: boolean;
  recording_status: string; audit_status: string; event_count: number | null; dropped_events: number | null;
  storage_ref: string | null; episode_complete_sha256: string | null; checksummed_artifacts: number; preserved_records: boolean;
}
export interface StopReceipt {
  accepted: boolean; code: string; reason: string; protocol: string; request_id: string; replayed: boolean;
  binding_id: string | null; session_id: string | null; config_fingerprint: string | null;
  run_id: string; backend_generation: number; episode_id: string;
  dispatch: StopDispatchEvidence; parking: ParkingEvidence;
  owner_cleared_after_stop: boolean; safety_latched: boolean; recording_status: string; recording_segment_id: string | null;
  recording_touched: boolean; motion_restored: boolean; observed_at: string;
}
export interface RecordingEndReceipt {
  accepted: boolean; code: string; reason: string; protocol: string; request_id: string; replayed: boolean;
  binding_id: string; session_id: string; config_fingerprint: string;
  run_id: string; backend_generation: number; episode_id: string;
  dispatch: StopDispatchEvidence; parking: ParkingEvidence;
  recording_status: string; recording_segment_id: string | null; active_segment_id: string | null; binding_state: string;
  drain: RecordingDrainEvidence; finalize: RecordingFinalizeEvidence;
  integrity: 'complete' | 'incomplete_terminal_recorded' | 'finalize_failed_missing_tail' | 'unknown' | string;
  owner_cleared_after_stop: boolean; safety_latched: boolean; recording_touched: boolean; motion_restored: boolean;
  reset_issued: boolean; safety_cleared: boolean; owner_acquired: boolean; observed_at: string;
}
export interface LifecycleAttempt { at: string; request_id: string; result: string; code?: string; reason?: string }
export interface SessionRecord {
  schema_version: string; session_id: string; state: 'prepared' | 'active' | 'closed' | 'failed';
  created_at: string; updated_at: string; snapshot_id: string;
  recipe_fingerprint: string; execution_revision: number; fingerprint: string;
  native_identity: { run_id: string; backend_generation: number; episode_id: string };
  native_binding: NativeBinding; execution_eligible: boolean; start_available: boolean;
  execution?: SessionExecution;
  blocking_reasons: BlockingReason[]; start_attempts?: StartAttempt[];
  started_at: string | null; start_receipt?: StartReceipt | null;
  recording_begin_attempts?: RecordingAttempt[]; recording_begin_receipt?: RecordingBeginReceipt | null;
  stop_receipt?: StopReceipt | null; stop_attempts?: LifecycleAttempt[];
  recording_end_receipt?: RecordingEndReceipt | null; recording_end_attempts?: LifecycleAttempt[];
  current?: SessionCurrent | null;
}
export interface SessionList { source: 'stored'; live: false; retrieved_at: string; sessions: SessionRecord[] }
export interface SessionEnvelope { session: SessionRecord; replayed: boolean }
export interface CreateSessionRequest {
  execution_revision: number; fingerprint: string; validated_snapshot_id: string; idempotency_key: string;
}
export interface PreflightCheck { key: string; status: string; detail: string }
export interface PreflightRecord {
  schema_version: string; task_id: string; checked_at: string; read_only: boolean;
  session_ready: boolean; read_contract_compatible: boolean; verification_scope: string; transport: string;
  runtime_identity: { run_id: string; backend_generation: number; episode_id: string };
  native_resource_identity: { model_id: string; model_sha256: string; scene_id: string; backend_kind: string; interface_profile: string };
  recording: { status: string; command_capture_ready: boolean; recording_segment_id: string | null };
  checks: PreflightCheck[];
}
export interface ExecutionRecipe {
  schema_version: string; recipe_id: string; recipe_revision: number; recipe_fingerprint: string;
  expected: Record<string, unknown>; required_protocols: Record<string, string>;
  kinematics: { profile_id: string; digest: string };
  sources: SourceRef[]; attestation: Record<string, unknown>;
}
export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public detail: unknown) { super(message); }
}
export function parseError(status: number, statusText: string, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const value = detail as Record<string, unknown>;
    return new ApiError(status, String(value.code ?? `HTTP_${status}`), String(value.message ?? statusText), value);
  }
  if (Array.isArray(detail)) {
    const message = detail.map((item) => {
      const entry = item as { loc?: unknown[]; msg?: string };
      return `${(entry.loc ?? []).join('.')}: ${entry.msg ?? 'invalid'}`;
    }).join('; ');
    return new ApiError(status, 'validation_error', message || `HTTP ${status}`, detail);
  }
  return new ApiError(status, `HTTP_${status}`, statusText || `HTTP ${status}`, body);
}
async function request<T>(path: string, init: RequestInit, signal: AbortSignal): Promise<T> {
  const response = await fetch(path, { ...init, signal, cache: 'no-store', headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...(init.headers ?? {}) } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw parseError(response.status, response.statusText, body);
  return body as T;
}
export class PlatformConfigApi {
  listDrafts(signal: AbortSignal) { return request<DraftRecord[]>('/api/v1/experiment-drafts', { method: 'GET' }, signal); }
  getDraft(draftId: string, signal: AbortSignal) { return request<DraftRecord>(`/api/v1/experiment-drafts/${encodeURIComponent(draftId)}`, { method: 'GET' }, signal); }
  createDraft(name: string, description: string, signal: AbortSignal) {
    return request<DraftRecord>('/api/v1/experiment-drafts', { method: 'POST', body: JSON.stringify({ name, description }) }, signal);
  }
  saveDraft(draftId: string, baseRevision: number, name: string, description: string, signal: AbortSignal) {
    return request<DraftRecord>(`/api/v1/experiment-drafts/${encodeURIComponent(draftId)}`, { method: 'PUT', body: JSON.stringify({ base_revision: baseRevision, name, description }) }, signal);
  }
  validateDraft(draftId: string, executionRevision: number, fingerprint: string, signal: AbortSignal) {
    return request<DraftRecord>(`/api/v1/experiment-drafts/${encodeURIComponent(draftId)}/validate`, { method: 'POST', body: JSON.stringify({ execution_revision: executionRevision, fingerprint }) }, signal);
  }
  listSnapshots(signal: AbortSignal) { return request<SnapshotRecord[]>('/api/v1/config-snapshots', { method: 'GET' }, signal); }
  getSnapshot(snapshotId: string, signal: AbortSignal) { return request<SnapshotRecord>(`/api/v1/config-snapshots/${encodeURIComponent(snapshotId)}`, { method: 'GET' }, signal); }
  listSessions(signal: AbortSignal) { return request<SessionList>('/api/v1/sessions', { method: 'GET' }, signal); }
  getSession(sessionId: string, signal: AbortSignal) { return request<SessionRecord>(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, { method: 'GET' }, signal); }
  createSession(body: CreateSessionRequest, signal: AbortSignal) {
    return request<SessionEnvelope>('/api/v1/sessions', { method: 'POST', body: JSON.stringify(body) }, signal);
  }
  startSession(sessionId: string, signal: AbortSignal) {
    return request<SessionRecord>(`/api/v1/sessions/${encodeURIComponent(sessionId)}/start`, { method: 'POST' }, signal);
  }
  beginRecording(sessionId: string, operatorId: string, viewSource: string, signal: AbortSignal) {
    return request<SessionEnvelope>(`/api/v1/sessions/${encodeURIComponent(sessionId)}/recording/begin`,
      { method: 'POST', body: JSON.stringify({ operator_id: operatorId, view_source: viewSource }) }, signal);
  }
  stopSession(sessionId: string, requestId: string, signal: AbortSignal) {
    return request<SessionEnvelope>(`/api/v1/sessions/${encodeURIComponent(sessionId)}/stop`,
      { method: 'POST', body: JSON.stringify({ request_id: requestId, reason: 'OPERATOR_STOP' }) }, signal);
  }
  endRecording(sessionId: string, requestId: string, signal: AbortSignal) {
    return request<SessionEnvelope>(`/api/v1/sessions/${encodeURIComponent(sessionId)}/recording/end`,
      { method: 'POST', body: JSON.stringify({ request_id: requestId, reason: 'OPERATOR_FINISHED' }) }, signal);
  }
  executionRecipe(signal: AbortSignal) { return request<ExecutionRecipe>('/api/v1/mobilecar/execution-recipe', { method: 'GET' }, signal); }
  preflight(signal: AbortSignal) { return request<PreflightRecord>('/api/v1/mobilecar/preflight', { method: 'GET' }, signal); }
}
export function describeApiError(error: unknown): string {
  if (error instanceof ApiError) return `${error.code} · ${error.message}`;
  return (error as Error)?.message ?? String(error);
}
export function blockingReasonsOf(error: unknown): BlockingReason[] {
  if (!(error instanceof ApiError) || !error.detail || typeof error.detail !== 'object') return [];
  const reasons = (error.detail as { blocking_reasons?: unknown }).blocking_reasons;
  return Array.isArray(reasons) ? reasons as BlockingReason[] : [];
}
export function isAbort(error: unknown): boolean {
  return (error as Error)?.name === 'AbortError';
}
export function isTimeout(error: unknown): boolean {
  return (error as Error)?.name === 'TimeoutError';
}
