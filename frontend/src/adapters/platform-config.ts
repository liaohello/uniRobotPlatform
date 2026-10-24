// Same-origin client for the M1.2b platform configuration API.
// Draft creation/save/validate and snapshot/Session reads only. No Session
// create/start, motion, RESET, recording or native command endpoint is called.
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
}
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
function parseError(status: number, statusText: string, body: unknown): ApiError {
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
  listSessions(signal: AbortSignal) { return request<SessionRecord[]>('/api/v1/sessions', { method: 'GET' }, signal); }
  getSession(sessionId: string, signal: AbortSignal) { return request<SessionRecord>(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, { method: 'GET' }, signal); }
  createSession(body: CreateSessionRequest, signal: AbortSignal) {
    return request<SessionEnvelope>('/api/v1/sessions', { method: 'POST', body: JSON.stringify(body) }, signal);
  }
  startSession(sessionId: string, signal: AbortSignal) {
    return request<SessionRecord>(`/api/v1/sessions/${encodeURIComponent(sessionId)}/start`, { method: 'POST' }, signal);
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
