import { useEffect, useMemo, useRef, useState } from 'react';
import { useWorkbench } from '../app/context';
import { Icon } from './Icon';
import {
  PlatformConfigApi, ApiError, blockingReasonsOf, describeApiError, isAbort, isTimeout,
  type BlockingReason, type Check, type DraftRecord, type ExecutionRecipe,
  type PreflightRecord, type SessionList, type SessionRecord, type SnapshotRecord,
} from '../adapters/platform-config';

type Busy = '' | 'load' | 'create' | 'save' | 'validate' | 'snapshot' | 'session-create' | 'session-start';
type CreateIntent = { key: string; snapshotId: string; executionRevision: number; fingerprint: string };
const ACTION_TIMEOUT_MS = 8000;
const executionSourceText: Record<string, string> = { prepared: 'prepare 动作', native_start: '显式 Start', native_recording_begin: 'recording begin' };
function idempotencyKey(): string {
  return globalThis.crypto?.randomUUID?.() ?? `idem-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
function upsertSession(list: SessionRecord[], next: SessionRecord): SessionRecord[] {
  const index = list.findIndex((item) => item.session_id === next.session_id);
  if (index < 0) return [next, ...list];
  const copy = [...list]; copy[index] = next; return copy;
}
const short = (value: string | null | undefined, head = 10) => !value ? '—' : value.length > head + 6 ? `${value.slice(0, head)}…${value.slice(-4)}` : value;
const statusText: Record<string, string> = { passed: '通过', failed: '失败', unsupported: '不支持', not_checked: '未检查', warning: '警告' };
const phaseText: Record<string, string> = { configuration: 'Configuration', readiness: 'Readiness' };
function upsertDraft(list: DraftRecord[], next: DraftRecord): DraftRecord[] {
  const index = list.findIndex((item) => item.draft_id === next.draft_id);
  if (index < 0) return [next, ...list];
  const copy = [...list]; copy[index] = next; return copy;
}
function upsertSnapshot(list: SnapshotRecord[], next: SnapshotRecord): SnapshotRecord[] {
  const merged = [next, ...list.filter((item) => item.snapshot_id !== next.snapshot_id)];
  return merged.sort((a, b) => b.created_at.localeCompare(a.created_at));
}
function CheckList({ checks }: { checks: Check[] }) {
  if (!checks.length) return <p className="session-note">没有返回检查项。</p>;
  return <div className="session-check-groups">
    {(['configuration', 'readiness'] as const).map((phase) => {
      const items = checks.filter((check) => check.phase === phase);
      if (!items.length) return null;
      const passed = items.filter((check) => check.status === 'passed').length;
      return <div key={phase} className="session-check-group">
        <div className="session-group-head"><b>{phaseText[phase]}</b><span>{passed}/{items.length} 通过</span></div>
        <ul className="session-checks">{items.map((check) => <li key={check.key} data-check-key={check.key} data-check-status={check.status} data-check-phase={check.phase}
          className={check.status === 'passed' ? 'pass' : check.status === 'failed' ? 'blocked' : 'unknown'}>
          <Icon name={check.status === 'passed' ? 'check' : 'info'} size={13}/>
          <div><b>{check.key}</b><small title={check.detail}>{check.scope}</small><small className="check-detail">{check.detail}</small></div>
          <span>{statusText[check.status] ?? check.status}</span>
        </li>)}</ul>
      </div>;
    })}
  </div>;
}
function ReasonList({ reasons }: { reasons: BlockingReason[] }) {
  if (!reasons.length) return null;
  return <ul className="session-reasons">{reasons.map((reason) => <li key={`${reason.scope}:${reason.key}`} data-blocking-key={reason.key} data-blocking-scope={reason.scope}>
    <b>{reason.key}</b><span>{reason.scope}</span><p>{reason.message}</p>
  </li>)}</ul>;
}
function KinematicsBlock() {
  const w = useWorkbench(); const report = w.sample.live?.kinematics;
  if (!report) return <div className="session-blocked neutral"><Icon name="info" size={15}/><div><b>冻结独立参考 profile</b><p>此来源不请求 live kinematics，也不把冻结 arm-spec 当作 live 回退。</p></div></div>;
  return <div className="session-kinematics" data-kinematics-status={report.status}>
    <dl className="session-fields">
      <div><dt>profile</dt><dd title={report.profileId}>{report.profileId || '不可用'} · {report.status}</dd></div>
      <div><dt>digest</dt><dd title={report.digest}>{short(report.digest, 16)}</dd></div>
      <div><dt>authority</dt><dd>{report.authority || '—'}</dd></div>
      <div><dt>TCP 姿态</dt><dd>{report.tcpOrientation === 'not-specified' ? `未声明 · ${report.tcpOrientationStatus}` : `已声明 · ${report.tcpOrientationStatus}`}</dd></div>
      {report.consistency && <div><dt>一致性</dt><dd>{['joint_order_consistent','user_limits_consistent','tcp_mount_consistent','camera_mount_consistent','gripper_limits_consistent'].map((key) => `${key.replace('_consistent','')}=${String(report.consistency![key])}`).join(' · ')} · err={String(report.consistency.max_user_limit_error_rad)}</dd></div>}
    </dl>
    {report.reason && <div className="session-blocked"><Icon name="info" size={15}/><div><b>元数据缺失或不匹配</b><p>{report.reason}</p></div></div>}
    <details className="session-details"><summary>运动学核对项（{report.checks.length}）</summary>
      <ul className="session-checks compact">{report.checks.map((check) => <li key={check.key} className={check.status === 'passed' ? 'pass' : check.status === 'failed' ? 'blocked' : 'unknown'}>
        <Icon name={check.status === 'passed' ? 'check' : 'info'} size={12}/><div><b>{check.label}</b><small>{check.detail}</small></div><span>{check.status === 'passed' ? '通过' : check.status === 'failed' ? '失败' : '参考'}</span>
      </li>)}</ul>
    </details>
    {report.limitations.length > 0 && <p className="session-note">限制：{report.limitations.join('；')}</p>}
  </div>;
}
export function SessionPanel() {
  const w = useWorkbench(); const live = Boolean(w.sample.live);
  const api = useMemo(() => new PlatformConfigApi(), []);
  const [drafts, setDrafts] = useState<DraftRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftRecord | null>(null);
  const [name, setName] = useState(''); const [description, setDescription] = useState('');
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('LanderPi 人工遥操作'); const [newDescription, setNewDescription] = useState('');
  const [snapshot, setSnapshot] = useState<SnapshotRecord | null>(null);
  const [snapshots, setSnapshots] = useState<SnapshotRecord[]>([]);
  const [snapshotChoice, setSnapshotChoice] = useState('');
  const [snapshotError, setSnapshotError] = useState('');
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [sessionsSource, setSessionsSource] = useState<'stored' | ''>('');
  const [sessionsLive, setSessionsLive] = useState<boolean | null>(null);
  const [sessionsError, setSessionsError] = useState('');
  const [sessionsFetchedAt, setSessionsFetchedAt] = useState('');
  const [sessionRefreshing, setSessionRefreshing] = useState(false);
  const [currentBusy, setCurrentBusy] = useState(false);
  const [currentError, setCurrentError] = useState('');
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessionUnknown, setSessionUnknown] = useState<{ kind: 'create' | 'start'; message: string } | null>(null);
  const [needsRevalidate, setNeedsRevalidate] = useState(false);
  const [preflight, setPreflight] = useState<PreflightRecord | null>(null);
  const [preflightError, setPreflightError] = useState('');
  const [preflightBusy, setPreflightBusy] = useState(false);
  const [recipe, setRecipe] = useState<ExecutionRecipe | null>(null);
  const [recipeError, setRecipeError] = useState('');
  const [busy, setBusy] = useState<Busy>('');
  const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const [conflict, setConflict] = useState(false);
  const serial = useRef(0); const controller = useRef<AbortController | null>(null);
  const sessionSerial = useRef(0); const sessionController = useRef<AbortController | null>(null);
  const currentSerial = useRef(0); const currentController = useRef<AbortController | null>(null);
  const preflightSerial = useRef(0); const preflightController = useRef<AbortController | null>(null);
  const selectedRef = useRef<string | null>(null); selectedRef.current = selectedId;
  const editorRef = useRef({ name, description }); editorRef.current = { name, description };
  const createIntentRef = useRef<CreateIntent | null>(null);
  const invalidatedRef = useRef<string | null>(null);
  const dirty = Boolean(draft && (name !== draft.name || description !== draft.description));
  const result = draft?.validation.result ?? null;
  const checks = snapshot?.checks ?? result?.checks ?? [];
  const reasons = snapshot?.blocking_reasons ?? result?.blocking_reasons ?? [];
  const recipeFingerprint = snapshot?.recipe_fingerprint ?? draft?.recipe_fingerprint ?? recipe?.recipe_fingerprint ?? '';
  const selectedSession = sessions.find((item) => item.session_id === selectedSessionId) ?? null;
  const selectedCurrent = selectedSession?.current ?? null;
  const existingForSnapshot = snapshot ? sessions.find((item) => item.snapshot_id === snapshot.snapshot_id && (item.state === 'prepared' || item.state === 'active')) : undefined;
  const currentInvalid = Boolean(selectedSession && selectedCurrent && (!selectedCurrent.valid
    || !selectedCurrent.runtime_identity_matches || !selectedCurrent.binding.matches
    || (selectedCurrent.status !== 'prepared' && selectedCurrent.status !== 'started')));
  const snapshotValidated = Boolean(snapshot?.execution_eligible && snapshot.validated_snapshot_id);
  const createBlockedReason = !live ? '冻结来源不连接平台'
    : !snapshot ? '尚未读取配置快照'
      : !snapshot.execution_eligible ? '快照 execution_eligible=false'
        : !snapshot.validated_snapshot_id ? '后端未签发 ValidatedSnapshot'
          : needsRevalidate ? '快照可能已过期或来自其他数据库，请重新校验'
            : existingForSnapshot ? `该快照已有 ${existingForSnapshot.state} Session`
              : '';
  const createReady = Boolean(live && snapshotValidated && !needsRevalidate && !existingForSnapshot);
  const canCreate = createReady && busy === '';
  const startable = Boolean(selectedSession && selectedCurrent?.valid && selectedCurrent.status === 'prepared'
    && selectedCurrent.start_available && !currentError && w.monitor.state !== 'stale');
  const canStart = startable && busy === '';
  const startBlockedReason = !selectedSession ? '未选择 Session'
    : !selectedCurrent ? '正在读取 Session current；不能使用存档 ready 判断'
      : !selectedCurrent.valid ? `current invalid：${selectedCurrent.status}${selectedCurrent.error ? ` · ${selectedCurrent.error}` : ''}`
        : selectedCurrent.status === 'started' ? 'Session 已 started；close/end 未定义，Start 不可用'
          : selectedCurrent.status !== 'prepared' ? `current 状态为 ${selectedCurrent.status}`
            : !selectedCurrent.start_available ? 'current.start_available=false'
              : currentInvalid ? '运行身份或 binding 失效'
                : currentError ? 'current 读取失败，已暂停 Start' : '';
  const selectedExecution = selectedSession?.execution;
  const ownerState = selectedCurrent?.owner.state ?? 'unknown';

  function begin() {
    controller.current?.abort(); const next = new AbortController(); controller.current = next;
    return { id: ++serial.current, signal: next.signal };
  }
  function beginSessions() {
    sessionController.current?.abort(); const next = new AbortController(); sessionController.current = next;
    return { id: ++sessionSerial.current, signal: next.signal };
  }
  function beginCurrent() {
    currentController.current?.abort(); const next = new AbortController(); currentController.current = next;
    return { id: ++currentSerial.current, signal: next.signal };
  }
  function beginPreflight() {
    preflightController.current?.abort(); const next = new AbortController(); preflightController.current = next;
    return { id: ++preflightSerial.current, signal: next.signal };
  }
  function current(id: number) { return id === serial.current; }
  function applySessionList(envelope: SessionList) {
    setSessions((previous) => {
      const byId = new Map(previous.map((item) => [item.session_id, item]));
      return envelope.sessions.map((item) => ({ ...item, current: item.current ?? byId.get(item.session_id)?.current ?? null }));
    });
    setSessionsSource(envelope.source); setSessionsLive(envelope.live); setSessionsFetchedAt(envelope.retrieved_at);
    setSelectedSessionId((previous) => previous && envelope.sessions.some((item) => item.session_id === previous)
      ? previous : envelope.sessions.find((item) => item.state === 'prepared' || item.state === 'active')?.session_id ?? envelope.sessions[0]?.session_id ?? null);
  }
  function applySession(next: SessionRecord) {
    setSessions((list) => upsertSession(list, next));
    setSelectedSessionId(next.session_id);
  }
  async function refreshCurrent(sessionId: string) {
    if (!live) return;
    const task = beginCurrent(); setCurrentBusy(true); setCurrentError('');
    try {
      const value = await api.getSession(sessionId, task.signal);
      if (task.id !== currentSerial.current) return;
      applySession(value);
    } catch (cause) {
      if (isAbort(cause) || task.id !== currentSerial.current) return;
      setCurrentError(describeApiError(cause));
    } finally {
      if (task.id === currentSerial.current) setCurrentBusy(false);
    }
  }
  async function refreshSessions() {
    if (!live) return;
    const task = beginSessions(); setSessionRefreshing(true);
    try {
      const envelope = await api.listSessions(task.signal);
      if (task.id !== sessionSerial.current) return;
      applySessionList(envelope); setSessionsError('');
      const selected = selectedRef.current;
      if (selected && envelope.sessions.some((item) => item.session_id === selected)) void refreshCurrent(selected);
    } catch (cause) {
      if (isAbort(cause) || task.id !== sessionSerial.current) return;
      setSessionsError(describeApiError(cause));
    } finally {
      if (task.id === sessionSerial.current) setSessionRefreshing(false);
    }
  }
  async function refreshPreflight() {
    if (!live) return;
    const task = beginPreflight(); setPreflightBusy(true); setPreflightError('');
    try {
      const value = await api.preflight(task.signal);
      if (task.id !== preflightSerial.current) return;
      setPreflight(value);
    } catch (cause) {
      if (isAbort(cause) || task.id !== preflightSerial.current) return;
      setPreflightError(describeApiError(cause));
    } finally {
      if (task.id === preflightSerial.current) setPreflightBusy(false);
    }
  }
  function intentFor(snap: SnapshotRecord): CreateIntent {
    const existing = createIntentRef.current;
    if (existing && existing.snapshotId === snap.snapshot_id && existing.executionRevision === snap.execution_revision && existing.fingerprint === snap.fingerprint) return existing;
    const next = { key: idempotencyKey(), snapshotId: snap.snapshot_id, executionRevision: snap.execution_revision, fingerprint: snap.fingerprint };
    createIntentRef.current = next; return next;
  }
  async function recoverOne(sessionId: string, signal: AbortSignal): Promise<SessionRecord | null> {
    try {
      const value = await api.getSession(sessionId, signal);
      applySession(value); return value;
    } catch (cause) {
      if (!isAbort(cause)) setSessionsError(`Session 回读失败：${describeApiError(cause)}`);
      return null;
    }
  }
  async function createPreparedSession() {
    if (!snapshot || !canCreate && !(sessionUnknown?.kind === 'create' && snapshotValidated)) {
      setError(createBlockedReason || '当前不满足创建条件'); return;
    }
    const target = snapshot; const intent = intentFor(target);
    const task = begin(); setBusy('session-create'); setError(''); setNotice(''); setSessionUnknown(null);
    const actionSignal = AbortSignal.any([task.signal, AbortSignal.timeout(ACTION_TIMEOUT_MS)]);
    try {
      const envelope = await api.createSession({
        execution_revision: target.execution_revision, fingerprint: target.fingerprint,
        validated_snapshot_id: target.validated_snapshot_id!, idempotency_key: intent.key,
      }, actionSignal);
      if (!current(task.id)) return;
      applySession(envelope.session);
      await refreshCurrent(envelope.session.session_id);
      setNotice(`prepared Session 已${envelope.replayed ? '通过幂等重放恢复' : '创建'}；不会自动 Start。`);
    } catch (cause) {
      if (task.signal.aborted) return;
      if (isTimeout(cause) || isAbort(cause)) {
        setSessionUnknown({ kind: 'create', message: '创建请求超时，结果未知；正在通过 GET /sessions 回读恢复。' });
        try {
          const list = await api.listSessions(task.signal);
          if (!current(task.id)) return;
          applySessionList(list);
          const found = list.sessions.find((item) => item.snapshot_id === intent.snapshotId && item.fingerprint === intent.fingerprint && item.execution_revision === intent.executionRevision);
          if (found) {
            setSelectedSessionId(found.session_id); setSessionUnknown(null);
            setNotice('创建超时后通过存档回读恢复；未自动 Start。');
          } else setSessionUnknown({ kind: 'create', message: '创建超时，存档中尚未看到结果。可稍后刷新；重试会复用同一幂等键。' });
        } catch (recoverCause) {
          if (!isAbort(recoverCause) && current(task.id)) setSessionUnknown({ kind: 'create', message: `创建超时且回读失败，结果未知：${describeApiError(recoverCause)}` });
        }
        return;
      }
      if (cause instanceof ApiError) {
        const detail = cause.detail as { session_id?: unknown } | null;
        const extra = blockingReasonsOf(cause);
        if (cause.code === 'session_conflict' && typeof detail?.session_id === 'string') {
          await recoverOne(detail.session_id, task.signal);
          setNotice('该 runtime 已有 Session；已读取现有 Session，未自动 Start。');
        } else if (['snapshot_not_found', 'stale_execution_reference', 'recipe_changed', 'validation_incomplete'].includes(cause.code)) {
          setNeedsRevalidate(true);
        }
        setError(`${describeApiError(cause)}${extra.length ? ` · ${extra.map((reason) => reason.message).join('；')}` : ''}`);
      } else setError(describeApiError(cause));
    } finally {
      if (current(task.id)) setBusy('');
    }
  }
  async function startPreparedSession() {
    if (!selectedSession) return;
    if (!canStart && !(sessionUnknown?.kind === 'start' && selectedSession.state === 'prepared')) {
      setError(startBlockedReason || '当前不满足 Start 条件'); return;
    }
    const target = selectedSession;
    const task = begin(); setBusy('session-start'); setError(''); setNotice(''); setSessionUnknown(null);
    const actionSignal = AbortSignal.any([task.signal, AbortSignal.timeout(ACTION_TIMEOUT_MS)]);
    try {
      const next = await api.startSession(target.session_id, actionSignal);
      if (!current(task.id)) return;
      applySession(next);
      await refreshCurrent(next.session_id);
      setNotice(`Start 已确认（${next.state}）；active/started 不代表取得 owner、正在录制或 motion_ready。`);
    } catch (cause) {
      if (task.signal.aborted) return;
      if (isTimeout(cause) || isAbort(cause)) {
        setSessionUnknown({ kind: 'start', message: 'Start 请求超时，结果未知；正在回读 Session 存档。' });
        const recovered = await recoverOne(target.session_id, task.signal);
        if (!current(task.id)) return;
        if (recovered?.state === 'active') { setSessionUnknown(null); setNotice('Start 超时后回读为 active；未自动重发。'); }
        else setSessionUnknown({ kind: 'start', message: `Start 超时，回读状态为 ${recovered?.state ?? '不可用'}；未确认成功，也未自动重发。` });
        return;
      }
      if (cause instanceof ApiError) {
        const extra = blockingReasonsOf(cause);
        setError(`${describeApiError(cause)}${extra.length ? ` · ${extra.map((reason) => reason.message).join('；')}` : ''}`);
        await recoverOne(target.session_id, task.signal);
      } else {
        setError(describeApiError(cause));
        await recoverOne(target.session_id, task.signal);
      }
    } finally {
      if (current(task.id)) setBusy('');
    }
  }
  useEffect(() => {
    if (!live || !selectedSessionId) return;
    void refreshCurrent(selectedSessionId);
    return () => { currentController.current?.abort(); };
    // Selection drives a single current read; archive list refreshes do not.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live, selectedSessionId]);
  useEffect(() => {
    if (!selectedSession) { invalidatedRef.current = null; return; }
    const key = `${selectedSession.session_id}:${selectedCurrent?.status ?? 'none'}:${selectedCurrent?.binding.state ?? 'none'}:${String(selectedCurrent?.valid)}`;
    if (currentInvalid && invalidatedRef.current !== key) {
      invalidatedRef.current = key;
      if (w.target || w.interacting) w.cancelTarget();
      else w.view.current?.cancelGesture('session-current-invalid');
      w.setNotice('Session current 无效或 binding 失效；旧本地目标与手势已取消，模型、相机与布局保留。');
    } else if (!currentInvalid && invalidatedRef.current === key) invalidatedRef.current = null;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSession?.session_id, selectedCurrent?.status, selectedCurrent?.binding.state, selectedCurrent?.valid, currentInvalid]);
  async function openDraft(id: string, explicit = false) {
    const task = begin(); setBusy('load'); setError(''); setConflict(false); setSnapshotError('');
    setNeedsRevalidate(false); setSessionUnknown(null);
    setSelectedId(id); setDraft(null); setSnapshot(null); setSnapshotChoice('');
    if (explicit) { /* reload keeps the editor replaced only after the server responds */ }
    try {
      const next = await api.getDraft(id, task.signal);
      if (!current(task.id)) return;
      let loadedSnapshot: SnapshotRecord | null = null;
      const snapshotId = next.validation.result?.snapshot_id;
      if (snapshotId) {
        try {
          loadedSnapshot = await api.getSnapshot(snapshotId, task.signal);
        } catch (cause) {
          if (!isAbort(cause) && current(task.id)) {
            setSnapshotError(`快照读取失败：${describeApiError(cause)}`);
            setNeedsRevalidate(true);
          }
        }
      }
      if (!current(task.id) || selectedRef.current !== id) return;
      setDraft(next); setName(next.name); setDescription(next.description);
      setDrafts((list) => upsertDraft(list, next));
      if (loadedSnapshot) {
        setSnapshot(loadedSnapshot); setSnapshotChoice(loadedSnapshot.snapshot_id);
        setSnapshots((list) => upsertSnapshot(list, loadedSnapshot!));
      }
    } catch (cause) {
      if (isAbort(cause) || !current(task.id)) return;
      if (cause instanceof ApiError && cause.code === 'draft_not_found') {
        setError('草案不在当前后端数据库（可能来自其他候选或数据库）；请新建草案或刷新列表。');
        setDraft(null); setSnapshot(null); setSnapshotChoice(''); setNeedsRevalidate(true);
      } else setError(describeApiError(cause));
    } finally {
      if (current(task.id)) setBusy('');
    }
  }
  async function refreshDraftList(openFirst = false) {
    const task = begin(); setBusy('load'); setError('');
    try {
      const list = await api.listDrafts(task.signal);
      if (!current(task.id)) return;
      setDrafts(list);
      const selected = selectedRef.current;
      if (openFirst || !selected || !list.some((item) => item.draft_id === selected)) {
        if (list.length) await openDraft(list[0].draft_id);
        else {
          setSelectedId(null); setDraft(null); setSnapshot(null); setSnapshotChoice('');
          setNeedsRevalidate(true); setNotice('当前后端草案列表为空；请新建草案。');
        }
      }
    } catch (cause) {
      if (isAbort(cause) || !current(task.id)) return;
      setError(describeApiError(cause));
    } finally {
      if (current(task.id)) setBusy('');
    }
  }
  async function bootstrap() {
    const task = begin();
    setBusy('load'); setError(''); setSessionsError(''); setRecipeError('');
    try {
      const [draftResult, recipeResult, snapshotResult] = await Promise.allSettled([
        api.listDrafts(task.signal), api.executionRecipe(task.signal), api.listSnapshots(task.signal),
      ]);
      if (!current(task.id)) return;
      if (snapshotResult.status === 'fulfilled') setSnapshots(snapshotResult.value);
      else if (!isAbort(snapshotResult.reason)) setSnapshotError(describeApiError(snapshotResult.reason));
      if (recipeResult.status === 'fulfilled') setRecipe(recipeResult.value);
      else if (!isAbort(recipeResult.reason)) setRecipeError(describeApiError(recipeResult.reason));
      if (draftResult.status === 'rejected') throw draftResult.reason;
      setDrafts(draftResult.value);
      if (draftResult.value.length) await openDraft(draftResult.value[0].draft_id);
    } catch (cause) {
      if (isAbort(cause) || !current(task.id)) return;
      setError(describeApiError(cause));
    } finally {
      if (current(task.id)) setBusy('');
    }
    void refreshSessions();
    void refreshPreflight();
  }
  useEffect(() => {
    if (!live) return;
    void bootstrap();
    return () => { controller.current?.abort(); sessionController.current?.abort(); currentController.current?.abort(); preflightController.current?.abort(); };
    // The drawer is mounted per open; the polling sample must not restart the
    // configuration requests on every Actual tick.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live]);
  async function createDraft() {
    const task = begin(); setBusy('create'); setError(''); setConflict(false);
    try {
      const next = await api.createDraft(newName.trim() || 'LanderPi 人工遥操作', newDescription, task.signal);
      if (!current(task.id)) return;
      setDrafts((list) => upsertDraft(list, next)); setCreating(false); setNewDescription('');
      setSelectedId(next.draft_id); setDraft(next); setName(next.name); setDescription(next.description);
      setSnapshot(null); setSnapshotChoice('');
      setNotice('草案已创建；仅名称/描述可编辑，执行修订由后端维护。');
    } catch (cause) {
      if (isAbort(cause) || !current(task.id)) return;
      setError(describeApiError(cause));
    } finally { if (current(task.id)) setBusy(''); }
  }
  async function saveDraft() {
    if (!draft) return;
    const targetId = draft.draft_id; const baseRevision = draft.draft_revision;
    const submittedName = name; const submittedDescription = description;
    const task = begin(); setBusy('save'); setError(''); setConflict(false); setNotice('');
    try {
      const next = await api.saveDraft(targetId, baseRevision, submittedName, submittedDescription, task.signal);
      if (!current(task.id)) return;
      setDrafts((list) => upsertDraft(list, next));
      if (selectedRef.current !== targetId) return;
      setDraft(next);
      const editedSince = editorRef.current.name !== submittedName || editorRef.current.description !== submittedDescription;
      if (editedSince) setNotice('已保存提交时的内容；此后的本地编辑仍未保存。');
      else { setName(next.name); setDescription(next.description); setNotice(`草案已保存到后端 · draft_revision=${next.draft_revision} · execution_revision=${next.execution_revision}`); }
      setConflict(false);
    } catch (cause) {
      if (isAbort(cause) || !current(task.id)) return;
      if (cause instanceof ApiError && cause.code === 'conflict') {
        setConflict(true);
        setError('保存冲突：草案已在其他宿主更新。本地编辑未被覆盖，也未静默重试；请读取服务器版本后合并。');
      } else setError(describeApiError(cause));
    } finally { if (current(task.id)) setBusy(''); }
  }
  async function validateDraft() {
    if (!draft) return;
    const targetId = draft.draft_id; const executionRevision = draft.execution_revision; const fingerprint = draft.fingerprint;
    const task = begin(); setBusy('validate'); setError(''); setConflict(false); setNotice(''); setSnapshotError('');
    try {
      const next = await api.validateDraft(targetId, executionRevision, fingerprint, task.signal);
      if (!current(task.id)) return;
      setDrafts((list) => upsertDraft(list, next));
      if (selectedRef.current !== targetId) return;
      setDraft(next); setNeedsRevalidate(false); setSessionUnknown(null);
      const snapshotId = next.validation.result?.snapshot_id;
      if (snapshotId) {
        try {
          const loaded = await api.getSnapshot(snapshotId, task.signal);
          if (!current(task.id)) return;
          setSnapshot(loaded); setSnapshotChoice(loaded.snapshot_id);
          setSnapshots((list) => upsertSnapshot(list, loaded));
        } catch (cause) {
          if (!isAbort(cause) && current(task.id)) setSnapshotError(`校验完成，但不可变快照读取失败：${describeApiError(cause)}`);
        }
      }
      setNotice(`校验完成 · ${next.validation.status} · execution_eligible=${String(next.validation.result?.execution_eligible ?? false)}`);
      void refreshSessions();
    } catch (cause) {
      if (isAbort(cause) || !current(task.id)) return;
      if (cause instanceof ApiError && cause.code === 'conflict') {
        setConflict(true); setNeedsRevalidate(true); setError('校验引用的执行修订或指纹已过期。请重新读取草案后再校验。');
      } else {
        const reasonsNow = blockingReasonsOf(cause);
        setError(reasonsNow.length ? `${describeApiError(cause)} · ${reasonsNow.map((reason) => reason.message).join('；')}` : describeApiError(cause));
      }
    } finally { if (current(task.id)) setBusy(''); }
  }
  async function readSnapshot(id: string) {
    if (!id) return;
    const task = begin(); setBusy('snapshot'); setSnapshotError(''); setError('');
    try {
      const loaded = await api.getSnapshot(id, task.signal);
      if (!current(task.id)) return;
      setSnapshot(loaded); setSnapshotChoice(loaded.snapshot_id);
      setSnapshots((list) => upsertSnapshot(list, loaded));
    } catch (cause) {
      if (isAbort(cause) || !current(task.id)) return;
      setSnapshotError(`快照读取失败：${describeApiError(cause)}`);
    } finally { if (current(task.id)) setBusy(''); }
  }
  const snapshotEligible = snapshot?.execution_eligible ?? result?.execution_eligible ?? false;
  const draftStatus = draft?.validation.status ?? 'unvalidated';
  return <aside className="session-drawer" aria-label="Session 准备">
    <header><div><b>Session 准备</b><small>草案 · 校验 · 快照 · prepared Session</small></div><button aria-label="关闭 Session 准备" title="关闭" onClick={() => w.setDrawer('none')}><Icon name="close" size={14}/></button></header>
    <div className="session-body">
      {!live ? <div className="session-blocked neutral"><Icon name="info" size={15}/><div><b>冻结来源不连接平台</b><p>Draft、配置快照和 Session 都来自平台 API；冻结样本只提供 3D 观察与本地目标预览。切回“真实后端 · 只读监控”后可使用。</p></div></div> : <>
        {error && <div className="session-error" role="alert" data-session-error>{error}{conflict && draft && <button onClick={() => { void openDraft(draft.draft_id, true); }}>读取服务器版本</button>}</div>}
        {notice && <p className="session-notice" role="status">{notice}</p>}
        <section>
          <h4><span className="step">1</span>草案 Draft <small>{busy === 'load' ? '读取中…' : dirty ? '未保存' : draft ? '已保存' : '—'}</small></h4>
          <div className="session-inline">
            <select aria-label="选择草案" value={selectedId ?? ''} disabled={busy !== ''} onChange={(event) => { if (event.target.value && event.target.value !== selectedId) void openDraft(event.target.value); }}>
              <option value="">选择草案</option>
              {drafts.map((item) => <option key={item.draft_id} value={item.draft_id}>{item.name} · {short(item.draft_id, 12)}</option>)}
            </select>
            <button disabled={busy !== ''} onClick={() => { setCreating(!creating); setError(''); }}>新建草案</button>
            <button disabled={busy !== ''} onClick={() => void refreshDraftList(false)}>刷新列表</button>
          </div>
          {creating && <div className="session-create">
            <label>新草案名称<input aria-label="新草案名称" maxLength={200} value={newName} onChange={(event) => setNewName(event.target.value)}/></label>
            <label>描述<input aria-label="新草案描述" maxLength={4000} value={newDescription} onChange={(event) => setNewDescription(event.target.value)}/></label>
            <div><button className="primary" disabled={busy !== '' || !newName.trim()} onClick={() => void createDraft()}>创建草案</button><button disabled={busy !== ''} onClick={() => setCreating(false)}>取消</button></div>
          </div>}
          {draft ? <>
            <dl className="session-fields" data-draft-id={draft.draft_id} data-draft-revision={draft.draft_revision} data-execution-revision={draft.execution_revision}>
              <div><dt>草案 ID</dt><dd title={draft.draft_id}>{draft.draft_id}</dd></div>
              <div><dt>修订</dt><dd>draft {draft.draft_revision} · execution {draft.execution_revision}</dd></div>
              <div><dt>preset</dt><dd>{draft.preset.preset_id} · {short(draft.preset.native_commit, 12)}</dd></div>
              <div><dt>fingerprint</dt><dd title={draft.fingerprint}>{short(draft.fingerprint, 16)}</dd></div>
              <div><dt>校验状态</dt><dd data-validation-status={draftStatus}>{draftStatus} · {draft.validation.status === 'unvalidated' ? '尚未校验' : '最后一轮结果'}</dd></div>
            </dl>
            <div className="session-edit">
              <label>名称<input aria-label="草案名称" maxLength={200} value={name} onChange={(event) => setName(event.target.value)}/></label>
              <label>描述<textarea aria-label="草案描述" maxLength={4000} rows={2} value={description} onChange={(event) => setDescription(event.target.value)}/></label>
              <div className="session-actions">
                <button className="primary" disabled={busy !== '' || !dirty} onClick={() => void saveDraft()}>{busy === 'save' ? '保存中…' : '保存草案'}</button>
                <button disabled={busy !== '' || !dirty} onClick={() => { setName(draft.name); setDescription(draft.description); }}>撤销编辑</button>
                <span>只编辑后端支持的 name / description；没有任意初态或机器人配置写入。</span>
              </div>
            </div>
          </> : drafts.length === 0 && !creating ? <p className="session-note">后端草案列表为空。可创建一份草案；执行修订与指纹由服务端固定。</p> : null}
        </section>

        <section>
          <h4><span className="step">2</span>校验 Validation <small>{checks.length ? `${checks.filter((check) => check.status === 'passed').length}/${checks.length} 通过` : '—'}</small></h4>
          <div className="session-inline">
            <button className="primary" disabled={busy !== '' || !draft} onClick={() => void validateDraft()}>{busy === 'validate' ? '校验中…' : '运行校验'}</button>
            <span className="session-inline-note">绑定 execution_revision {draft?.execution_revision ?? '—'} · fingerprint {short(draft?.fingerprint, 12)}</span>
          </div>
          {result ? <>
            <div className="session-verdicts">
              <span className={result.status === 'passed' ? 'ok' : 'bad'} data-result-status={result.status}>validation status · {result.status}</span>
              <span className={result.execution_eligible ? 'ok' : 'bad'} data-execution-eligible={String(result.execution_eligible)}>execution_eligible · {String(result.execution_eligible)}</span>
              <span data-validated-snapshot={result.validated_snapshot_id ?? ''}>validated_snapshot · {result.validated_snapshot_id ?? 'null'}</span>
              <span data-recipe-fingerprint={result.recipe_fingerprint}>recipe · {short(result.recipe_fingerprint, 16)}</span>
            </div>
            <p className="session-note">“通过几项”只是摘要，不能替代 execution_eligible 或 Session 资格。必需项 unsupported / not_checked 不会显示为通过。reused={String(result.reused)} · checked_at={result.checked_at}</p>
            {!snapshot && <CheckList checks={checks}/>}
            <ReasonList reasons={reasons}/>
          </> : <p className="session-note">尚无服务端校验结果。保存草案后运行 validate；不在这里本地伪造 Passed 或 ValidatedSnapshot。</p>}
        </section>

        <section>
          <h4><span className="step">3</span>不可变配置快照 <small>{snapshot ? snapshot.validation_status : '未读取'}</small></h4>
          <div className="session-inline">
            <select aria-label="选择配置快照" value={snapshotChoice} onChange={(event) => setSnapshotChoice(event.target.value)}>
              <option value="">选择最近快照</option>
              {snapshots.slice(0, 8).map((item) => <option key={item.snapshot_id} value={item.snapshot_id}>{short(item.snapshot_id, 14)} · {item.validation_status}</option>)}
            </select>
            <button disabled={busy !== '' || !snapshotChoice} onClick={() => void readSnapshot(snapshotChoice)}>{busy === 'snapshot' ? '读取中…' : '读取快照'}</button>
          </div>
          {snapshotError && <div className="session-error" role="alert">{snapshotError}</div>}
          {snapshot ? <>
            <dl className="session-fields" data-snapshot-id={snapshot.snapshot_id} data-snapshot-sha={snapshot.snapshot_sha256} data-snapshot-eligible={String(snapshot.execution_eligible)}>
              <div><dt>snapshot</dt><dd title={snapshot.snapshot_id}>{snapshot.snapshot_id}</dd></div>
              <div><dt>sha256</dt><dd title={snapshot.snapshot_sha256}>{short(snapshot.snapshot_sha256, 18)}</dd></div>
              <div><dt>created</dt><dd>{snapshot.created_at}</dd></div>
              <div><dt>草案 / 执行</dt><dd>draft {snapshot.draft_revision} · execution {snapshot.execution_revision}</dd></div>
              <div><dt>scope</dt><dd>{snapshot.validation_scope}</dd></div>
              <div><dt>eligibility</dt><dd data-snapshot-status={snapshot.validation_status}>{snapshot.validation_status} · execution_eligible={String(snapshot.execution_eligible)} · validated={snapshot.validated_snapshot_id ?? 'null'}</dd></div>
              <div><dt>recipe</dt><dd title={snapshot.recipe_fingerprint}>{short(snapshot.recipe_fingerprint, 18)}</dd></div>
            </dl>
            <p className="session-note">快照由服务端只 INSERT；重复校验返回同一 snapshot_id / sha256。以下逐项结果来自该不可变快照。</p>
            <CheckList checks={snapshot.checks}/>
            <ReasonList reasons={snapshot.blocking_reasons}/>
            <details className="session-details"><summary>执行配方与证据来源</summary>
              <dl className="session-fields">
                <div><dt>recipe fingerprint</dt><dd title={snapshot.recipe_fingerprint}>{snapshot.recipe_fingerprint}</dd></div>
                <div><dt>required</dt><dd>{recipe ? Object.entries(recipe.required_protocols).map(([key, value]) => `${key}=${value}`).join(' · ') : 'recipe 读取失败或未返回'}</dd></div>
                <div><dt>kinematics</dt><dd>{snapshot.kinematics.profile_id} · {short(snapshot.kinematics.digest, 16)} · {snapshot.kinematics.authority}</dd></div>
              </dl>
              {(snapshot.recipe.sources ?? recipe?.sources ?? []).map((source) => <p key={`${source.role}:${source.path}`} className="source-row"><b>{source.role}</b><code>{source.path}</code><span>{short(source.sha256, 12)}</span></p>)}
              <p className="session-note">这些是配方来源摘要，不是 native 部署内容或标定的独立证明。</p>
            </details>
          </> : <p className="session-note">校验完成后自动读取快照；也可在此读取后端历史快照。快照不可编辑。</p>}
        </section>

        <section>
          <h4><span className="step">4</span>新鲜度与当前观测 <small data-preflight-checked-at={preflight?.checked_at ?? ''}>{preflight?.checked_at ?? '未读取'}</small></h4>
          <div className="session-inline">
            <button disabled={preflightBusy} onClick={() => void refreshPreflight()}>{preflightBusy ? '读取中…' : '刷新 native 观测（只读）'}</button>
            <span className="session-inline-note">GET /mobilecar/preflight；只读核对四个 native GET，不刷新 Session 存档或资格</span>
          </div>
          {preflightError && <div className="session-error" role="alert">preflight 读取失败：{preflightError}</div>}
          {preflight ? <>
            <dl className="session-fields" data-preflight-compatible={String(preflight.read_contract_compatible)}>
              <div><dt>checked_at</dt><dd>{preflight.checked_at}</dd></div>
              <div><dt>契约</dt><dd>read_contract_compatible={String(preflight.read_contract_compatible)} · session_ready={String(preflight.session_ready)} · {preflight.transport}</dd></div>
              <div><dt>runtime</dt><dd title={`${preflight.runtime_identity.run_id} / ${preflight.runtime_identity.episode_id}`}>{short(preflight.runtime_identity.run_id, 16)} · gen {preflight.runtime_identity.backend_generation} · {short(preflight.runtime_identity.episode_id, 14)}</dd></div>
              <div><dt>native</dt><dd>{preflight.native_resource_identity.interface_profile} · {preflight.native_resource_identity.backend_kind} · {preflight.native_resource_identity.scene_id}</dd></div>
              <div><dt>recording</dt><dd>{preflight.recording.status} · capture_ready={String(preflight.recording.command_capture_ready)}</dd></div>
              <div><dt>scope</dt><dd>{preflight.verification_scope}</dd></div>
            </dl>
            <details className="session-details"><summary>当前观测检查（{preflight.checks.length}）</summary>
              <ul className="session-checks compact">{preflight.checks.map((item) => <li key={item.key} data-preflight-check={item.key} data-preflight-check-status={item.status} className={item.status === 'passed' ? 'pass' : item.status === 'failed' ? 'blocked' : 'unknown'}>
                <Icon name={item.status === 'passed' ? 'check' : 'info'} size={12}/><div><b>{item.key}</b><small className="check-detail">{item.detail}</small></div><span>{statusText[item.status] ?? item.status}</span>
              </li>)}</ul>
            </details>
            <p className="session-note">这是 {preflight.checked_at} 的全局 native 诊断，不是 Session current 的刷新；Session 是否可 Start 只以下方单 Session current 为准。</p>
          </> : <p className="session-note">尚未读取 preflight。GET /sessions 只返回上次平台动作的存档视图，不能当作持续实时状态。</p>}
        </section>

        <section>
          <h4><span className="step">5</span>prepared Session <small data-session-count={sessions.length}>{sessions.length} 个</small></h4>
          {sessionsError && <div className="session-error" role="alert">Session 读取失败：{sessionsError}</div>}
          <div className="session-inline">
            <select aria-label="选择 Session" value={selectedSessionId ?? ''} onChange={(event) => setSelectedSessionId(event.target.value || null)}>
              <option value="">选择 Session</option>
              {sessions.map((item) => <option key={item.session_id} value={item.session_id}>{item.state} · {short(item.session_id, 14)}</option>)}
            </select>
            <button disabled={sessionRefreshing} onClick={() => void refreshSessions()}>{sessionRefreshing ? '读取中…' : '刷新存档（不调用 native）'}</button>
          </div>
          <p className="session-note" data-sessions-source={sessionsSource} data-sessions-live={String(sessionsLive)}>列表 source={sessionsSource || '—'} · live={String(sessionsLive)} · retrieved_at={sessionsFetchedAt || '—'}。它是存档列表，不是 current；选中 Session 后单独读取 current。</p>
          <div className="session-inline">
            <button className="primary" data-session-create={createReady ? 'ready' : 'blocked'} disabled={busy !== '' || !canCreate} title={createBlockedReason || '创建 prepared Session；不会自动 Start'} onClick={() => void createPreparedSession()}>{busy === 'session-create' ? '创建中…' : '创建 prepared Session'}</button>
            <span className="session-inline-note">{createBlockedReason || '只创建 prepared；不会因 validate 成功或创建成功自动 Start'}</span>
          </div>
          {sessionUnknown && <div className="session-unknown" role="status" data-session-unknown={sessionUnknown.kind}><b>结果未知</b><p>{sessionUnknown.message}</p></div>}
          {needsRevalidate && <div className="session-blocked" role="alert" data-needs-revalidate="true"><Icon name="info" size={15}/><div><b>请重新校验或新建草案</b><p>当前草案/快照可能不在这个后端数据库、已被配方变更或未签发；不要复用旧 Draft / 快照 ID。{draft && <button disabled={busy !== ''} onClick={() => void validateDraft()}>重新校验当前草案</button>}</p></div></div>}
          {sessions.length === 0 ? <div className="session-blocked neutral"><Icon name="info" size={15}/><div><b>空 Session 列表</b><p>GET /api/v1/sessions 返回 <code>source=stored, live=false, sessions=[]</code>。这不是 Ready，也不代表 Start 可用。当前真实环境没有 prepared/started Session；Start、运动、RESET、录制继续禁用。</p></div></div>
            : <>
              <div className="session-state-list">{sessions.map((item) => <button key={item.session_id} aria-pressed={item.session_id === selectedSessionId} data-session-id={item.session_id} data-session-state={item.state} onClick={() => setSelectedSessionId(item.session_id)}><b>{item.state}</b><span>{short(item.session_id, 10)}</span></button>)}</div>
              {selectedSession ? <article className="session-card" data-session-id={selectedSession.session_id} data-session-state={selectedSession.state} data-session-current-valid={String(selectedCurrent?.valid ?? false)} data-session-current-status={selectedCurrent?.status ?? 'unread'} data-session-current-error={selectedCurrent?.error ?? ''} data-session-invalidated={String(currentInvalid)} data-session-startable={String(startable)} data-session-owner={ownerState} data-session-recording-ready={String(selectedCurrent?.recording_ready ?? false)} data-session-motion-ready={String(selectedCurrent?.motion_ready ?? false)} data-session-execution-source={selectedCurrent?.source ?? ''} data-session-observed-at={selectedCurrent?.observed_at ?? ''} data-session-current-blockers={String(selectedCurrent?.blockers.length ?? 0)}>
                <div className="session-card-head"><b>{selectedSession.state}</b><span>{short(selectedSession.session_id, 16)}</span></div>
                <div className="session-lifecycle">
                  <span className={selectedCurrent?.snapshot_eligible && selectedCurrent?.recipe_fingerprint_matches ? 'ok' : 'bad'}>配置合格 {String(Boolean(selectedCurrent?.snapshot_eligible && selectedCurrent?.recipe_fingerprint_matches))}</span>
                  <span className={selectedCurrent?.status === 'prepared' ? 'ok' : 'unknown'}>prepared {String(selectedCurrent?.status === 'prepared')}</span>
                  <span className={startable ? 'ok' : 'bad'}>可Start {String(startable)}</span>
                  <span className={selectedCurrent?.status === 'started' ? 'ok' : 'unknown'}>started/active {String(selectedCurrent?.status === 'started')}</span>
                  <span className={ownerState === 'held' ? 'ok' : 'bad'}>Owner {ownerState}</span>
                  <span className={selectedCurrent?.recording_ready ? 'ok' : 'bad'}>Recording {String(selectedCurrent?.recording_ready ?? false)}</span>
                  <span className={selectedCurrent?.motion_ready ? 'ok' : 'bad'}>Motion {String(selectedCurrent?.motion_ready ?? false)}</span>
                </div>
                {currentInvalid && <div className="session-blocked" data-session-binding-invalid="true"><Icon name="info" size={15}/><div><b>current 无效或 binding 失效</b><p>current.status={selectedCurrent?.status}; valid={String(selectedCurrent?.valid)}; binding={selectedCurrent?.binding.state}; binding_matches={String(selectedCurrent?.binding.matches)}; runtime_matches={String(selectedCurrent?.runtime_identity_matches)}。Start 已禁用；旧手势和待提交目标已取消；同内容模型、相机与布局保留。不会自动重绑或重发。</p></div></div>}
                <div className="session-current" data-session-current-valid={String(selectedCurrent?.valid ?? false)} data-session-current-status={selectedCurrent?.status ?? 'unread'} data-current-error={currentError}>
                  <div className="session-current-head"><b>current 观测</b><span>{currentBusy ? '读取中…' : currentError ? `读取失败：${currentError}` : selectedCurrent ? `${selectedCurrent.source} · ${selectedCurrent.observed_at}` : '未读取'}</span><button disabled={currentBusy} onClick={() => void refreshCurrent(selectedSession.session_id)}>刷新 current（只读）</button></div>
                  {selectedCurrent ? <>
                    <dl className="session-fields">
                      <div><dt>valid / status</dt><dd>valid={String(selectedCurrent.valid)} · status={selectedCurrent.status} · error={selectedCurrent.error ?? 'null'}</dd></div>
                      <div><dt>runtime</dt><dd>{short(selectedCurrent.runtime_identity.run_id, 16)} · gen {selectedCurrent.runtime_identity.backend_generation} · matches={String(selectedCurrent.runtime_identity_matches)}</dd></div>
                      <div><dt>binding</dt><dd>state={selectedCurrent.binding.state} · matches={String(selectedCurrent.binding.matches)} · id={selectedCurrent.binding.binding_id ?? 'null'}</dd></div>
                      <div><dt>binding 校验</dt><dd>readback={short(selectedCurrent.binding.readback_sha256, 16)} · error={selectedCurrent.binding.error ?? 'null'}</dd></div>
                      <div><dt>snapshot</dt><dd title={selectedCurrent.snapshot_id}>{short(selectedCurrent.snapshot_id, 18)} · eligible={String(selectedCurrent.snapshot_eligible)} · recipe_match={String(selectedCurrent.recipe_fingerprint_matches)}</dd></div>
                      <div><dt>授权范围</dt><dd>{selectedCurrent.control_scope_granted.length ? selectedCurrent.control_scope_granted.join(', ') : '[]'}</dd></div>
                      <div><dt>录制</dt><dd>required={String(selectedCurrent.recording_required_for_motion)} · begin_required={String(selectedCurrent.recording_begin_required)} · status={selectedCurrent.recording.status} · capture_ready={String(selectedCurrent.recording.command_capture_ready)} · ready={String(selectedCurrent.recording_ready)}</dd></div>
                      <div><dt>recording 细节</dt><dd>episode={selectedCurrent.recording.episode_id ?? 'null'} · segment={selectedCurrent.recording.segment_id ?? 'null'} · error={selectedCurrent.recording.error ?? 'null'}</dd></div>
                      <div><dt>Owner / lease</dt><dd>{selectedCurrent.owner.state} · session={selectedCurrent.owner.session_id ?? 'null'} · lease_native_monotonic_s={String(selectedCurrent.owner.lease_expires_at_backend_monotonic_s)} · lease_exposed={String(selectedCurrent.owner.lease_exposed)}</dd></div>
                      <div><dt>safety</dt><dd>safety_latched={String(selectedCurrent.safety_latched)}</dd></div>
                      <div><dt>ready/available</dt><dd>recording_ready={String(selectedCurrent.recording_ready)} · motion_ready={String(selectedCurrent.motion_ready)} · start_available={String(selectedCurrent.start_available)} · recording_begin_available={String(selectedCurrent.recording_begin_available)}</dd></div>
                    </dl>
                    <ReasonList reasons={selectedCurrent.blockers}/>
                  </> : <p className="session-note">current 尚未读取。不能使用存档 execution、start_available 或 binding status 代替 current ready。</p>}
                  <p className="session-note">current 只执行 native 只读 GET；不续租、不重绑、不 Start、不清锁、不启停录制。prepared TTL 与 started 生命周期由后端 current.status 判定，前端不按本地时钟计算。</p>
                </div>
                <div className="session-inline">
                  <button className="primary" data-session-start={startable ? 'ready' : 'blocked'} disabled={busy !== '' || !canStart} title={startBlockedReason || '显式 Start；不会自动获取 owner 或开始录制'} onClick={() => void startPreparedSession()}>{busy === 'session-start' ? 'Start 请求中…' : '显式 Start'}</button>
                  <button disabled={currentBusy} onClick={() => void refreshCurrent(selectedSession.session_id)}>刷新 current</button>
                  <span className="session-inline-note">{startBlockedReason || 'Start 只建立 active 与授权范围；不获取 owner、不开始录制、不等于 motion_ready'}</span>
                </div>
                <details className="session-details"><summary>历史 / 存档字段（不代表 current）</summary>
                  <dl className="session-fields">
                    <div><dt>存档身份</dt><dd title={`${selectedSession.native_identity.run_id} / ${selectedSession.native_identity.episode_id}`}>{short(selectedSession.native_identity.run_id, 16)} · gen {selectedSession.native_identity.backend_generation} · {short(selectedSession.native_identity.episode_id, 14)}</dd></div>
                    <div><dt>存档 binding</dt><dd>{selectedSession.native_binding.status} · {selectedSession.native_binding.protocol ?? 'no protocol'} · {selectedSession.native_binding.binding_id ?? 'binding_id=null'}</dd></div>
                    <div><dt>存档 binding 身份</dt><dd>native_session={selectedSession.native_binding.native_session_id ?? 'null'} · config={short(selectedSession.native_binding.config_fingerprint, 16)}</dd></div>
                    <div><dt>存档 binding 时间</dt><dd>verified_at={selectedSession.native_binding.verified_at ?? 'null'} · expires_native_monotonic_s={String(selectedSession.native_binding.expires_at_backend_monotonic_s)}（仅 prepared TTL，当前以后端 current 为准）</dd></div>
                    <div><dt>存档 readback</dt><dd title={selectedSession.native_binding.readback_sha256 ?? ''}>{short(selectedSession.native_binding.readback_sha256, 18)} {selectedSession.native_binding.reason ? `· ${selectedSession.native_binding.reason}` : ''}</dd></div>
                    <div><dt>存档授权范围</dt><dd>{selectedExecution?.control_scope_granted?.length ? selectedExecution.control_scope_granted.join(', ') : '[]'}</dd></div>
                    <div><dt>存档 Owner</dt><dd>{selectedExecution?.owner.state ?? 'unknown'} · session={selectedExecution?.owner.session_id ?? 'null'} · lease_native_monotonic_s={String(selectedExecution?.owner.lease_expires_at_backend_monotonic_s ?? null)}</dd></div>
                    <div><dt>存档录制</dt><dd>required_for_motion={String(selectedExecution?.recording_required_for_motion ?? false)} · begin_required={String(selectedExecution?.recording_begin_required ?? false)} · ready={String(selectedExecution?.recording_ready ?? false)}</dd></div>
                    <div><dt>存档 motion</dt><dd>ready={String(selectedExecution?.motion_ready ?? false)} · blockers={selectedExecution?.motion_blockers?.length ? selectedExecution.motion_blockers.join(', ') : '[]'}</dd></div>
                    <div><dt>存档 execution</dt><dd>{selectedExecution ? `${executionSourceText[selectedExecution.source] ?? selectedExecution.source} · observed_at=${selectedExecution.observed_at}` : '旧 Session 文档缺少 execution；请重建'}</dd></div>
                    <div><dt>快照</dt><dd title={selectedSession.snapshot_id}>{short(selectedSession.snapshot_id, 18)} · execution_revision {selectedSession.execution_revision} · fingerprint {short(selectedSession.fingerprint, 12)}</dd></div>
                  </dl>
                  {selectedSession.blocking_reasons.length > 0 && <ReasonList reasons={selectedSession.blocking_reasons}/>}
                </details>
                <details className="session-details"><summary>生命周期、回执与尝试</summary>
                  <dl className="session-fields">
                    <div><dt>created</dt><dd>{selectedSession.created_at} · updated {selectedSession.updated_at}</dd></div>
                    <div><dt>started_at</dt><dd>{selectedSession.started_at ?? 'null'}</dd></div>
                    <div><dt>start_receipt</dt><dd>{selectedSession.start_receipt ? `binding=${selectedSession.start_receipt.binding_id} · scope=${selectedSession.start_receipt.control_scope_granted.join(',')} · owner=${selectedSession.start_receipt.owner_state} · recording_ready=${String(selectedSession.start_receipt.recording_ready)} · motion_ready=${String(selectedSession.start_receipt.motion_ready)}` : 'null'}</dd></div>
                    <div><dt>recording begin</dt><dd>{selectedSession.recording_begin_receipt ? `${selectedSession.recording_begin_receipt.recording_status} · segment=${selectedSession.recording_begin_receipt.recording_segment_id} · durable=${String(selectedSession.recording_begin_receipt.durable_start_records)}` : 'null（本轮不调用 begin）'}</dd></div>
                  </dl>
                  {(selectedSession.start_attempts ?? []).length > 0 && <ul className="session-attempts">{selectedSession.start_attempts!.map((attempt, index) => <li key={`${attempt.at}:${index}`} data-start-attempt={attempt.result}><b>{attempt.result}</b><span>{attempt.at}</span><p>{attempt.blocking.map((item) => item.key).join(', ') || attempt.detail || '—'}</p></li>)}</ul>}
                  {(selectedSession.recording_begin_attempts ?? []).length > 0 && <ul className="session-attempts">{selectedSession.recording_begin_attempts!.map((attempt, index) => <li key={`${attempt.at}:${index}`} data-recording-attempt={attempt.result}><b>{attempt.result}</b><span>{attempt.at}</span><p>{attempt.reason || '—'}</p></li>)}</ul>}
                </details>
                <p className="session-note">active 不表示取得 Owner、正在录制或允许运动；这些分别看 Owner/lease、recording_ready、motion_ready。当前界面不会发送运动、STOP、RESET、recording begin/finalize。</p>
              </article> : <p className="session-note">请选择一个 Session 查看生命周期与回执。</p>}
            </>}
        </section>

        <section>
          <h4>运动学元数据 <small>{w.sample.live?.kinematics.status ?? '—'}</small></h4>
          <KinematicsBlock/>
          {recipeError && <p className="session-note">execution-recipe 读取失败：{recipeError}</p>}
          <p className="session-note">TCP orientation=null 保留“未声明”语义；本地位置 IK 只是预览，不是标定姿态、规划或执行许可。</p>
        </section>
        <p className="session-note">本轮仅允许平台草案创建/保存/校验及只读快照、Session。禁止运动、RESET、录制、回放和 native 命令。</p>
      </>}
    </div>
  </aside>;
}
