import { useEffect, useMemo, useRef, useState } from 'react';
import { useWorkbench } from '../app/context';
import { Icon } from './Icon';
import {
  PlatformConfigApi, ApiError, blockingReasonsOf, describeApiError, isAbort,
  type BlockingReason, type Check, type DraftRecord, type ExecutionRecipe,
  type SessionRecord, type SnapshotRecord,
} from '../adapters/platform-config';

type Busy = '' | 'load' | 'create' | 'save' | 'validate' | 'snapshot';
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
  const [sessionsError, setSessionsError] = useState('');
  const [recipe, setRecipe] = useState<ExecutionRecipe | null>(null);
  const [recipeError, setRecipeError] = useState('');
  const [busy, setBusy] = useState<Busy>('');
  const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const [conflict, setConflict] = useState(false);
  const serial = useRef(0); const controller = useRef<AbortController | null>(null);
  const sessionSerial = useRef(0); const sessionController = useRef<AbortController | null>(null);
  const selectedRef = useRef<string | null>(null); selectedRef.current = selectedId;
  const editorRef = useRef({ name, description }); editorRef.current = { name, description };
  const dirty = Boolean(draft && (name !== draft.name || description !== draft.description));
  const result = draft?.validation.result ?? null;
  const checks = snapshot?.checks ?? result?.checks ?? [];
  const reasons = snapshot?.blocking_reasons ?? result?.blocking_reasons ?? [];
  const recipeFingerprint = snapshot?.recipe_fingerprint ?? draft?.recipe_fingerprint ?? recipe?.recipe_fingerprint ?? '';

  function begin() {
    controller.current?.abort(); const next = new AbortController(); controller.current = next;
    return { id: ++serial.current, signal: next.signal };
  }
  function beginSessions() {
    sessionController.current?.abort(); const next = new AbortController(); sessionController.current = next;
    return { id: ++sessionSerial.current, signal: next.signal };
  }
  function current(id: number) { return id === serial.current; }

  async function refreshSessions() {
    if (!live) return;
    const task = beginSessions();
    try {
      const list = await api.listSessions(task.signal);
      if (task.id !== sessionSerial.current) return;
      setSessions(list); setSessionsError('');
    } catch (cause) {
      if (isAbort(cause) || task.id !== sessionSerial.current) return;
      setSessionsError(describeApiError(cause));
    }
  }
  async function openDraft(id: string, explicit = false) {
    const task = begin(); setBusy('load'); setError(''); setConflict(false); setSnapshotError('');
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
          if (!isAbort(cause) && current(task.id)) setSnapshotError(`快照读取失败：${describeApiError(cause)}`);
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
      setError(describeApiError(cause));
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
  }
  useEffect(() => {
    if (!live) return;
    void bootstrap();
    return () => { controller.current?.abort(); sessionController.current?.abort(); };
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
      setDraft(next);
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
        setConflict(true); setError('校验引用的执行修订或指纹已过期。请重新读取草案后再校验。');
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
          <h4><span className="step">4</span>prepared Session <small data-session-count={sessions.length}>{sessions.length} 个</small></h4>
          {sessionsError && <div className="session-error" role="alert">Session 读取失败：{sessionsError}</div>}
          {sessions.length === 0 ? <div className="session-blocked neutral"><Icon name="info" size={15}/><div><b>空 Session 列表</b><p>GET /api/v1/sessions 返回空数组。这不是 Ready，也不代表 Start 可用。当前真实环境没有 prepared/active/failed Session；Start、运动、RESET、录制继续禁用。</p></div></div>
            : sessions.map((session) => <article className="session-card" key={session.session_id} data-session-id={session.session_id} data-session-state={session.state}>
              <div className="session-card-head"><b>{session.state}</b><span>{short(session.session_id, 16)}</span></div>
              <dl className="session-fields">
                <div><dt>eligible</dt><dd>{String(session.execution_eligible)} · start_available={String(session.start_available)}</dd></div>
                <div><dt>binding</dt><dd>{session.native_binding.status} · {session.native_binding.protocol ?? 'no protocol'}{session.native_binding.reason ? ` · ${session.native_binding.reason}` : ''}</dd></div>
                <div><dt>snapshot</dt><dd title={session.snapshot_id}>{short(session.snapshot_id, 18)}</dd></div>
              </dl>
              <ReasonList reasons={session.blocking_reasons}/>
              {session.start_attempts.length > 0 && <p className="session-note">最近 Start 尝试：{session.start_attempts.at(-1)?.result} · {session.start_attempts.at(-1)?.blocking ?? session.start_attempts.at(-1)?.detail ?? '—'}</p>}
            </article>)}
          <div className="session-blocked neutral"><Icon name="info" size={15}/><div><b>Session 创建与 Start 仍被门控</b><p>{snapshotEligible ? '当前快照声明 execution_eligible=true，但本轮未代理 POST /api/v1/sessions 或 start，不能显示 Ready。' : '当前快照 execution_eligible=false；后端会以 409 validation_incomplete 拒绝创建。本轮不发送该请求，也不以 health、Owner 或本地目标提升资格。'}</p></div></div>
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
