/**
 * M1.5h/i action basis surface: the current frame's associated records and the Episode's independent
 * command/event tracks.
 *
 * Everything on this pane is read only. The page's `frame_association` is used only for the page that
 * returned it; switching page/Episode/condition drops the whole basis and the raw payloads. Raw records
 * come from the existing events records GET with a bounded window around one `record_position`, and each
 * answer is checked for identity, line, event_type and the frame's capture tick before it is shown.
 */
import { useEffect, useRef, useState } from 'react';
import { actionClassOf, describeHistoryError, type EpisodeDetailDto, type PlatformEpisodeApi, type RecordPageDto } from '../adapters/platform-episodes';
import {
  ACTION_EVENT_ROLES, actionBasisJsonBytes, actionCandidatesOf, actionReadWindow, eventTimeRowsOf,
  payloadRowsOf, type ActionBasisVerdictDto, type ActionEventType, type FrameDto,
  type FramePageDto,
} from '../adapters/platform-frames';

export interface ActionBasisView {
  page: FramePageDto; key: string; reads: number; pageBytes: number; basisBytes: number;
}
export type ActionBasisStatus = 'idle' | 'loading' | 'ready' | 'refused';

interface RawEntry {
  role: ActionEventType; position: string; status: 'loading' | 'ready' | 'failed';
  lineIndex: number | null; record: Record<string, unknown> | null; error: string; bytes: number;
  streamPath: string; windowText: string;
}

const checked = (record: Record<string, unknown>, field: string) => record[field] === undefined ? 'absent' : String(record[field]);
const payloadOf = (record: Record<string, unknown> | null): Record<string, unknown> | null => {
  const payload = record?.payload;
  return payload && typeof payload === 'object' && !Array.isArray(payload) ? payload as Record<string, unknown> : null;
};

export function FrameActionPane({ api, episodeId, runId, page, position, frame, semantics, basis, basisStatus, basisError, onReadBasis }: {
  api: PlatformEpisodeApi; episodeId: string; runId: string | null; page: FramePageDto | null;
  position: number; frame: FrameDto | null; semantics?: EpisodeDetailDto['action_semantics'];
  basis: ActionBasisView | null; basisStatus: ActionBasisStatus; basisError: string; onReadBasis: () => void;
}) {
  const candidates = basis ? actionCandidatesOf(basis.page, position) : null;
  const selectionKey = `${episodeId}|${runId ?? ''}|${page?.paging.offset ?? 'none'}|${position}|${frame?.anchor.line_index ?? 'none'}|${frame?.sample_id ?? 'none'}`;
  const [entries, setEntries] = useState<Record<string, RawEntry>>({});
  const [recordReads, setRecordReads] = useState(0);
  const [recordBytes, setRecordBytes] = useState(0);
  const [track, setTrack] = useState<{ position: string; status: 'loading' | 'ready' | 'failed'; record: Record<string, unknown> | null; error: string; streamPath: string; windowText: string } | null>(null);
  const [trackReads, setTrackReads] = useState(0);
  const rawSerial = useRef(0);
  const trackSerial = useRef(0);
  const rawControllers = useRef<AbortController[]>([]);
  const trackController = useRef<AbortController | null>(null);
  // The exact values this pane is answering for; every late read compares them before writing.
  const live = useRef({ selectionKey, episodeId, runId, offset: page?.paging.offset ?? null, line: frame?.anchor.line_index ?? null });
  live.current = { selectionKey, episodeId, runId, offset: page?.paging.offset ?? null, line: frame?.anchor.line_index ?? null };

  useEffect(() => {
    rawControllers.current.forEach((controller) => controller.abort());
    rawControllers.current = [];
    trackController.current?.abort(); trackController.current = null;
    const token = ++rawSerial.current;
    ++trackSerial.current;
    setEntries({}); setRecordReads(0); setRecordBytes(0); setTrack(null); setTrackReads(0);
    if (!frame || !candidates) return;
    const target = { episodeId, runId, offset: page?.paging.offset ?? null, line: frame.anchor.line_index };
    const started: Record<string, RawEntry> = {};
    const jobs: Promise<void>[] = [];
    ACTION_EVENT_ROLES.forEach((role) => {
      const verdict: ActionBasisVerdictDto | undefined = candidates.by_event_type[role.type];
      if (!verdict || verdict.status === 'missing' || !verdict.record_positions?.length) return;
      verdict.record_positions.forEach((recordPosition) => {
        const key = `${role.type}|${recordPosition}`;
        started[key] = { role: role.type, position: recordPosition, status: 'loading', lineIndex: null, record: null, error: '', bytes: 0, streamPath: 'events', windowText: '' };
        jobs.push(readOne(role.type, recordPosition, key, target));
      });
    });
    if (Object.keys(started).length) setEntries(started);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectionKey, candidateSignature(candidates)]);

  useEffect(() => () => {
    rawControllers.current.forEach((controller) => controller.abort());
    rawControllers.current = [];
    trackController.current?.abort();
  }, []);

  async function readOne(role: ActionEventType, recordPosition: string, key: string, target: { episodeId: string; runId: string | null; offset: number | null; line: number }) {
    const window = actionReadWindow(recordPosition);
    if (!window) {
      setEntries((previous) => ({ ...previous, [key]: { ...previous[key], status: 'failed', error: `record_position=${recordPosition} 不是可解析的 events.jsonl#<line_index>` } }));
      return;
    }
    const controller = new AbortController(); rawControllers.current.push(controller);
    const token = rawSerial.current;
    setRecordReads((value) => value + 1);
    try {
      const dto = await api.readRecords({ episodeId: target.episodeId, runId: target.runId, streamId: window.streamId, limit: window.limit, offset: window.offset }, controller.signal);
      if (token !== rawSerial.current || target.episodeId !== live.current.episodeId || target.runId !== live.current.runId
        || target.offset !== live.current.offset || target.line !== live.current.line) return;
      const problem = identityProblem(dto, target);
      const hit = dto.records.find((row) => row.line_index === window.lineIndex);
      if (problem || !hit) {
        const reason = problem ?? `有界窗口 offset=${window.offset}&limit=${window.limit} 没有 line_index=${window.lineIndex} 的记录（返回 ${dto.records.map((row) => row.line_index).join(',') || '空'}）：界面不扩大扫描、不借用相邻行。`;
        setEntries((previous) => ({ ...previous, [key]: { ...previous[key], status: 'failed', lineIndex: null, error: reason, streamPath: dto.stream.relative_path, windowText: `offset=${window.offset}&limit=${window.limit}` } }));
        return;
      }
      const record = hit.record;
      const tick = frame?.anchor.reference_keys?.capture_control_tick_id ?? null;
      const recordTick = record.control_tick_id === undefined || record.control_tick_id === null ? null : String(record.control_tick_id);
      if (String(record.event_type ?? '') !== role) {
        setEntries((previous) => ({ ...previous, [key]: { ...previous[key], status: 'failed', lineIndex: hit.line_index, error: `该行 event_type=${checked(record, 'event_type')}，候选声明的是 ${role}：不把它当作 ${role} 显示。`, streamPath: dto.stream.relative_path, windowText: `offset=${window.offset}&limit=${window.limit}` } }));
        return;
      }
      if (tick && recordTick !== tick) {
        setEntries((previous) => ({ ...previous, [key]: { ...previous[key], status: 'failed', lineIndex: hit.line_index, error: `该行 control_tick_id=${recordTick ?? 'null'} 与帧的 capture_control_tick_id=${tick} 不等：不把它挂到这一帧。`, streamPath: dto.stream.relative_path, windowText: `offset=${window.offset}&limit=${window.limit}` } }));
        return;
      }
      const bytes = jsonBytes(record);
      setRecordBytes((value) => value + bytes);
      setEntries((previous) => ({ ...previous, [key]: { role, position: recordPosition, status: 'ready', lineIndex: hit.line_index, record, error: '', bytes, streamPath: dto.stream.relative_path, windowText: `offset=${window.offset}&limit=${window.limit}` } }));
    } catch (cause) {
      if (controller.signal.aborted || token !== rawSerial.current) return;
      setEntries((previous) => ({ ...previous, [key]: { ...previous[key], status: 'failed', error: describeHistoryError(cause), streamPath: 'events', windowText: `offset=${window.offset}&limit=${window.limit}` } }));
    }
  }

  function readTrackEvent(eventType: string, recordPosition: string) {
    if (!episodeId) return;
    const window = actionReadWindow(recordPosition);
    const controller = new AbortController();
    trackController.current?.abort(); trackController.current = controller;
    const token = ++trackSerial.current;
    const targetEpisode = episodeId; const targetRun = runId;
    if (!window) { setTrack({ position: recordPosition, status: 'failed', record: null, error: '位置不可解析', streamPath: 'events', windowText: '' }); return; }
    setTrack({ position: recordPosition, status: 'loading', record: null, error: '', streamPath: 'events', windowText: `offset=${window.offset}&limit=${window.limit}` });
    setTrackReads((value) => value + 1);
    void (async () => {
      try {
        const dto = await api.readRecords({ episodeId: targetEpisode, runId: targetRun, streamId: window.streamId, limit: window.limit, offset: window.offset }, controller.signal);
        if (token !== trackSerial.current) return;
        const problem = identityProblem(dto, { episodeId: targetEpisode, runId: targetRun });
        const hit = dto.records.find((row) => row.line_index === window.lineIndex);
        if (problem || !hit) {
          setTrack({ position: recordPosition, status: 'failed', record: null, error: problem ?? `有界窗口没有 line_index=${window.lineIndex} 的记录：不扫描更多行。`, streamPath: dto.stream.relative_path, windowText: `offset=${window.offset}&limit=${window.limit}` });
          return;
        }
        if (String(hit.record.event_type ?? '') !== eventType) {
          setTrack({ position: recordPosition, status: 'failed', record: null, error: `该行 event_type=${checked(hit.record, 'event_type')}，与轨上的 ${eventType} 不符。`, streamPath: dto.stream.relative_path, windowText: `offset=${window.offset}&limit=${window.limit}` });
          return;
        }
        setTrack({ position: recordPosition, status: 'ready', record: hit.record, error: '', streamPath: dto.stream.relative_path, windowText: `offset=${window.offset}&limit=${window.limit}` });
      } catch (cause) {
        if (controller.signal.aborted || token !== trackSerial.current) return;
        setTrack({ position: recordPosition, status: 'failed', record: null, error: describeHistoryError(cause), streamPath: 'events', windowText: `offset=${window.offset}&limit=${window.limit}` });
      }
    })();
  }

  const basisPage = basis?.page ?? null;
  const association = basisPage?.action_basis?.frame_association ?? null;
  const chain = basisPage?.action_basis?.command_chain ?? null;
  const control = basisPage?.action_basis?.control_source ?? null;
  const categories = basisPage?.action_basis?.categories ?? {};
  const vocabulary = basisPage?.action_basis?.vocabulary ?? {};
  const scope = basisPage?.action_basis?.scope ?? null;
  const basisCoordinates = cursorOf(basisPage, position);
  const currentMatches = Boolean(basis && page && basis.page.paging.offset === page.paging.offset && basisCoordinates === position);

  return <section className="history-stream-pane frame-action-pane" aria-label="动作与命令事件" data-action-pane="true" data-read-only="true"
    data-action-episode={episodeId || 'none'} data-action-run={runId ?? 'null'} data-action-status={basisStatus}
    data-action-selection={selectionKey} data-action-anchor={frame ? `${page?.paging.offset ?? 0}+${position}|line ${frame.anchor.line_index}` : 'none'}
    data-action-basis-key={basis?.key ?? 'none'} data-action-basis-page-offset={basisPage ? String(basisPage.paging.offset) : 'none'}
    data-action-basis-frames={basisPage ? String(basisPage.action_basis?.frame_association.candidate_positions_per_frame.length ?? 0) : 'none'}
    data-action-page-matches={String(currentMatches)} data-action-basis-reads={basis ? String(basis.reads) : '0'}
    data-action-basis-bytes={basis ? String(basis.basisBytes) : '0'} data-action-page-bytes={basis ? String(basis.pageBytes) : '0'}
    data-action-record-reads={String(recordReads)} data-action-record-bytes={String(recordBytes)}
    data-action-record-window="one-bounded-window-per-position">
    <h4>动作／命令事件（本页候选只属于本页）</h4>
    <p className="session-note">
      Actual、记录 Target、dispatch 与命令意图是不同类别：Target 不代表已达到，dispatch 不代表执行成功，requested/approved 不是执行结果。
      本面板只读原记录并按原字段名显示；不推进物理、不发命令、不生成历史 3D Ghost，也不把六项参考数组套成五轴 Actual。
    </p>
    <div className="session-inline">
      <button data-action-read-basis disabled={!page || basisStatus === 'loading'} title="同一 frames GET 加 include_action_basis=true：整趟扫描 events 的类别、命令链与本页逐帧候选"
        onClick={onReadBasis}>{basisStatus === 'loading' ? '正在读取本页动作依据…' : basis ? '重新读取本页动作依据' : '读取本页动作依据（一次）'}</button>
      <span className="chip masked" data-action-basis-status={basisStatus} data-action-basis-error={basisError || 'none'}>
        {basisStatus === 'ready' && basis ? `已读：本页 ${basisCoordinates === null ? '?' : '候选'} · 本页页偏移 ${basis.page.paging.offset} · action_basis 约 ${basis.basisBytes} B（客户端 JSON 长度）· 整个响应约 ${basis.pageBytes} B`
          : basisStatus === 'loading' ? '正在读取：会整趟扫描本 Episode 的 events 文件'
            : basisStatus === 'refused' ? `读取失败：${basisError}` : '未读取（普通帧页不带 action_basis；跨页不沿用上一页候选）'}
      </span>
    </div>
    {basisStatus === 'refused' && <div className="session-error" role="alert" data-action-basis-refused>{basisError}</div>}
    {!page && <p className="session-note" data-action-no-page="true">未绑定帧页：没有可读取的 action_basis。</p>}
    {page && !basis && <p className="session-note" data-action-basis-absent="true">本页还没有动作依据。该读取会整趟扫描本 Episode 的 events 文件（实测约 100 KB 级），因此按页显式读取、不在每次翻页时自动携带；换页后旧候选作废。</p>}
    {basis && !currentMatches && <p className="session-blocked" data-action-basis-mismatch="true">动作依据不属于当前页/当前帧：界面不套用，避免把上一页候选挂到这一帧。</p>}

    {basis && currentMatches && frame && <div data-action-current-frame="true" data-action-current-line={String(frame.anchor.line_index)} data-action-current-tick={frame.anchor.reference_keys?.capture_control_tick_id ?? 'null'}>
      <p className="session-note" data-action-association-key={association?.key ?? 'none'}>
        本页 frame_association：key={association?.key ?? 'reader 未声明'} · 候选上限 {association?.candidate_list_limit ?? '—'} 条/类 · 截断={String(association?.candidate_lists_truncated)}
        {association?.rules?.clock_parity ? <><br/><em>clock_parity：{association.rules.clock_parity}</em></> : null}
      </p>
      {ACTION_EVENT_ROLES.map((role) => {
        const verdict = candidates?.by_event_type?.[role.type] ?? null;
        const roleEntries = Object.values(entries).filter((entry) => entry.role === role.type);
        return <div key={role.type} className="action-role" data-action-role={role.type} data-action-verdict={verdict?.status ?? 'not-returned'}
          data-action-candidate-count={verdict?.candidate_count ?? 0} data-action-positions={(verdict?.record_positions ?? []).join('|') || 'none'}>
          <h5>{role.label}</h5>
          {!verdict && <p className="session-note" data-action-role-absent="true">reader 没有给该类型的候选：界面不补一条。</p>}
          {verdict?.status === 'missing' && <p className="session-blocked" role="note" data-action-missing={role.type}>
            本帧没有该类型的关联记录：{verdict.reason ?? 'reader 未说明'} · looked_for={JSON.stringify(verdict.looked_for ?? {})}。
            <b>不补零、不沿用上一 tick、不借用相邻帧。</b>
          </p>}
          {verdict?.status === 'ambiguous_candidates' && <p className="session-blocked" role="note" data-action-ambiguous={role.type}>
            本帧有 {verdict.candidate_count} 个候选：全部列在下面，界面不选第一项。{verdict.note ?? ''}
          </p>}
          {roleEntries.map((entry) => <div key={`${role.type}-${entry.position}`} data-action-record={entry.position} data-action-record-status={entry.status}
            data-action-record-line={entry.lineIndex === null ? 'none' : String(entry.lineIndex)} data-action-record-stream={entry.streamPath}
            data-action-record-window-text={entry.windowText} data-action-record-bytes={String(entry.bytes)}>
            {entry.status === 'loading' && <p className="session-note">正在按 {entry.position} 做有界读取（{entry.windowText || '窗口待定'}）…</p>}
            {entry.status === 'failed' && <div className="session-error" role="alert" data-action-record-error>{entry.error}</div>}
            {entry.status === 'ready' && entry.record && <RecordDetail role={role.type} entry={entry}/>}
          </div>)}
        </div>;
      })}
      <p className="session-note" data-action-read-cost={`读取成本：本次选择发起 ${recordReads} 条 events records GET，原始记录合计约 ${recordBytes} B（客户端 JSON 长度，不含头部/压缩）；每条只读一个 ±1 行窗口，不逐帧重扫、不扩大范围。`}>
        读取成本：本次选择发起 {recordReads} 条 events records GET，原始记录约 {recordBytes} B（客户端 JSON 长度）；每条一个有界窗口。
      </p>
    </div>}

    {basis && <div className="frame-action-track" data-action-track="true" data-action-track-episode={basisPage?.identity.episode_id ?? 'none'}>
      <h4>独立命令／事件轨（Episode 词表与命令链；不挂到“最近帧”）</h4>
      <p className="session-note" data-action-track-scope>
        范围：records_scanned={scope?.records_scanned ?? '—'} · reached_end_of_file={String(scope?.reached_end_of_file)} · record_limit={scope?.record_limit ?? '—'} · events_stream_present={String(scope?.events_stream_present)} · records_without_event_type={scope?.records_without_an_event_type ?? '—'}。
        {scope?.scope_note ?? 'reader 未说明范围'}
      </p>
      <p className="session-note">这里的类别状态属于当前 Episode（{basisPage?.identity.episode_id ?? 'none'}）：切 Episode 后整块作废并按新响应重判，不跨 Episode 固定缓存。</p>
      <table className="frame-record-table" data-action-categories="true"><thead><tr><th>类别</th><th>状态</th><th>事件类型 / 条数</th><th>含义</th></tr></thead>
        <tbody>{Object.entries(categories).map(([key, category]) => <tr key={key} data-action-category={key} data-action-category-status={category.status}>
          <td>{key}</td><td>{category.status}</td>
          <td>{Object.entries(category.counts).map(([type, count]) => `${type}=${count}`).join('；') || '无'}{category.absent_event_types?.length ? <small>未记录：{category.absent_event_types.join('、')}</small> : null}</td>
          <td>{category.meaning ?? ''}{category.status_note ? <small>{category.status_note}</small> : null}</td></tr>)}</tbody></table>

      {chain && <div data-action-command-chain="true" data-action-command-count={String(chain.commands.length)} data-action-command-truncated={String(chain.commands_truncated)}>
        <h5>命令链（按 command_id）</h5>
        <p className="session-note" data-action-command-note>requested 是命令意图、approved 是受理回执、rejected 是拒绝回执；三者都不等于执行结果。dispatch 是下发记录，也不等于执行成功。{chain.note ?? ''}</p>
        <table className="frame-record-table"><thead><tr><th>command_id</th><th>requested</th><th>approved</th><th>rejected</th><th>dispatch</th><th>control_tick_id</th></tr></thead>
          <tbody>{chain.commands.map((command) => <tr key={command.command_id} data-action-command={command.command_id}
            data-action-command-stages={`requested=${command.stages.requested ?? 0},approved=${command.stages.approved ?? 0},rejected=${command.stages.rejected ?? 0},dispatch=${command.stages.dispatch ?? 0}`}
            data-action-command-positions={Object.entries(command.positions).map(([type, positions]) => `${type}:${positions.join('|')}`).join('；')}>
            <td><code>{command.command_id}</code></td>
            {(['requested', 'approved', 'rejected', 'dispatch'] as const).map((stage) => <td key={stage} data-action-command-stage={stage}
              data-action-stage-count={String(command.stages[stage] ?? 0)} data-action-stage-positions={(command.positions[stage] ?? []).join('|') || 'none'}>
              {stage === 'rejected' && (command.stages.rejected ?? 0) > 0 ? `回执（未执行）${command.positions.rejected?.length ? ` · ${command.positions.rejected.join('、')}` : ''}` : (command.stages[stage] ?? 0)}
            </td>)}
            <td>{command.control_tick_id_present}</td></tr>)}</tbody></table>
      </div>}

      <div data-action-control-source="true" data-action-control-status={control?.status ?? 'not-returned'} data-action-takeover-recorded={String(control?.takeover_event_type_recorded)}>
        <h5>控制来源</h5>
        <p className="session-note">status={control?.status ?? 'reader 未返回'} · takeover_event_type_recorded={String(control?.takeover_event_type_recorded)} · lease_evidence={JSON.stringify(control?.lease_evidence ?? {})}<br/>{control?.note ?? 'reader 未说明控制来源'}。{!control?.fields_observed || !Object.keys(control.fields_observed).length ? '没有记录控制来源字段：界面不默认 Human。' : `记录中出现来源字段：${Object.entries(control.fields_observed).map(([type, fields]) => `${type}→${fields.join(',')}`).join('；')}；缺失仍然显示为缺失，不默认 Human。`}</p>
      </div>

      <div data-action-vocabulary="true">
        <h5>词表与采样位置（Episode 级）</h5>
        <table className="frame-record-table"><thead><tr><th>event_type</th><th>条数</th><th>行号首/末</th><th>采样位置</th><th>关联键 present/null</th><th>时间字段（有证据的单位）</th><th>reader 动作类别</th></tr></thead>
          <tbody>{Object.entries(vocabulary).map(([type, entry]) => {
            const actionClass = actionClassOf(type, semantics);
            return <tr key={type} data-action-vocab-type={type} data-action-vocab-count={String(entry.count)} data-action-vocab-class={actionClass.cls} data-action-vocab-positions={(entry.record_positions ?? []).join('|')}>
            <td>{type}</td><td>{entry.count}</td><td>{entry.first_line_index}/{entry.last_line_index}</td>
            <td>{(entry.record_positions ?? []).join('、') || '未列'}</td>
            <td>{Object.entries(entry.join_keys ?? {}).map(([key, value]) => `${key}: envelope ${value.envelope.present}/${value.envelope.null} · payload ${value.payload.present}/${value.payload.null}`).join('；') || '无'}</td>
            <td>{Object.entries(entry.time_fields ?? {}).map(([field, value]) => `${field}=${value.unit}（numeric ${value.numeric}/null ${value.null}/other ${value.other}）`).join('；') || '无'}</td>
            <td><small>{actionClass.cls}：{actionClass.note}</small></td></tr>;
          })}</tbody></table>
      </div>

      <div data-action-independent-tracks="true" data-action-independent-list={(basisPage?.action_basis?.independent_tracks ?? []).join('|') || 'none'}>
        <h5>独立事件（按 event_seq／命名时间基定位，不按“最近帧”）</h5>
        <p className="session-note">{basisPage?.action_basis?.independent_track_reason ?? 'reader 未说明'}</p>
        {(basisPage?.action_basis?.independent_tracks ?? []).map((trackName) => {
          const types = categories[trackName]?.event_types_recorded ?? [];
          return <div key={trackName} data-action-independent={trackName}>
            <b>{trackName}</b>：{types.join('、') || '无类型'}
            {types.map((type) => <span key={type}> · {(vocabulary[type]?.record_positions ?? []).slice(0, 3).map((recordPosition) =>
              <button key={recordPosition} data-action-track-read={recordPosition} data-action-track-type={type}
                onClick={() => readTrackEvent(type, recordPosition)}>读取 {recordPosition}</button>)}</span>)}
          </div>;
        })}
        {track && <div data-action-track-detail={track.position} data-action-track-status={track.status} data-action-track-stream={track.streamPath} data-action-track-window={track.windowText}>
          {track.status === 'loading' && <p className="session-note">正在有界读取 {track.position}…</p>}
          {track.status === 'failed' && <div className="session-error" role="alert" data-action-track-error>{track.error}</div>}
          {track.status === 'ready' && track.record && <TrackRecordDetail record={track.record} position={track.position} streamPath={track.streamPath}/>}
          <p className="session-note">本次轨详情读取累计 {trackReads} 条 GET；该选择不改变上面的帧游标。</p>
        </div>}
      </div>

      {basisPage?.action_basis?.not_proven?.length ? <ul className="receipt-layers" data-action-not-proven="true">{basisPage.action_basis.not_proven.map((line) => <li key={line}>{line}</li>)}</ul> : null}
    </div>}
  </section>;
}

function RecordDetail({ role, entry }: { role: ActionEventType; entry: RawEntry }) {
  const payload = payloadOf(entry.record);
  const rows = payloadRowsOf(payload);
  const targetNote = role === 'actuator_reference'
    ? 'Target：记录里的目标参考，不代表已达到；数组按原字段与索引显示，未声明维度/顺序映射时不套到五轴 Actual。'
    : role === 'feedback' ? 'Actual：记录的测量状态，不是 Target，也不是命令执行结果。'
      : 'dispatch：记录的是下发，不是执行成功；本条记录没有执行结果字段。';
  return <>
    <p className="session-note" data-action-record-meaning={role}>{targetNote}</p>
    <p className="session-note" data-action-record-identity>
      line_index={entry.lineIndex} · position={entry.position} · event_seq={checked(entry.record ?? {}, 'event_seq')} · event_type={checked(entry.record ?? {}, 'event_type')}
      {' '}· control_tick_id={checked(entry.record ?? {}, 'control_tick_id')} · command_id={checked(entry.record ?? {}, 'command_id')} · wall_utc={checked(entry.record ?? {}, 'wall_utc')}
    </p>
    <table className="frame-record-table"><thead><tr><th>原字段名</th><th>索引</th><th>值</th><th>单位</th><th>单位依据</th><th>说明</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={`${row.field}-${row.index ?? 'x'}`} data-action-payload-field={row.field} data-action-payload-index={row.index === null ? 'none' : String(row.index)}
        data-action-payload-unit={row.unit} data-action-payload-value={row.value}>
        <td><code>{row.field}</code></td><td>{row.index === null ? '—' : row.index}</td>
        <td><code>{row.value}</code></td><td>{row.unit}</td><td><small>{row.unitBasis}</small></td><td><small>{row.note}</small></td></tr>)}</tbody></table>
    {!rows.length && <p className="session-note" data-action-payload-empty="true">该记录没有 payload 字段：显示为空，不补零。</p>}
  </>;
}

function TrackRecordDetail({ record, position, streamPath }: { record: Record<string, unknown>; position: string; streamPath: string }) {
  const times = eventTimeRowsOf(record);
  const numeric = times.filter((row) => row.numeric);
  return <div data-action-track-record="true" data-action-track-event-seq={checked(record, 'event_seq')} data-action-track-event-type={checked(record, 'event_type')} data-action-track-line={position}>
    <p className="session-note">位置 {streamPath}#{position.split('#')[1] ?? '?'} · event_seq={checked(record, 'event_seq')} · event_type={checked(record, 'event_type')} · control_tick_id={checked(record, 'control_tick_id')} · command_id={checked(record, 'command_id')}</p>
    <table className="frame-record-table"><thead><tr><th>自身时间字段</th><th>值</th><th>单位</th><th>是否数值时刻</th><th>依据</th></tr></thead>
      <tbody>{times.map((row) => <tr key={row.field} data-action-event-time={row.field} data-action-event-numeric={String(row.numeric)}>
        <td>{row.field}</td><td><code>{row.value}</code></td><td>{row.unit}</td><td>{String(row.numeric)}</td><td><small>{row.basis}</small></td></tr>)}</tbody></table>
    {!numeric.length && <p className="session-blocked" data-action-no-numeric-time="true">该事件只有 wall_utc 或没有数值时间字段：界面不补数值时刻，也不借用帧的钟。</p>}
    <details><summary>原始 payload</summary><pre data-action-track-payload>{JSON.stringify(record.payload ?? {}, null, 1)}</pre></details>
  </div>;
}

function identityProblem(dto: RecordPageDto, target: { episodeId: string; runId: string | null }): string {
  if (dto.identity.episode_id !== target.episodeId) return `响应 episode_id=${dto.identity.episode_id} 与本面板 ${target.episodeId} 不符：不采用。`;
  if (target.runId && dto.identity.run_id !== target.runId) return `响应 run_id=${dto.identity.run_id} 与本面板 ${target.runId} 不符：不采用。`;
  if (dto.stream.stream_id !== 'events') return `records 读取落在流 ${dto.stream.stream_id}（${dto.stream.relative_path}），不是 events：不采用。`;
  return '';
}
function candidateSignature(candidates: ReturnType<typeof actionCandidatesOf>): string {
  if (!candidates) return 'none';
  return ACTION_EVENT_ROLES.map((role) => `${role.type}:${candidates.by_event_type?.[role.type]?.status ?? '-'}:${(candidates.by_event_type?.[role.type]?.record_positions ?? []).join(',')}`).join('|');
}
function cursorOf(page: FramePageDto | null, position: number): number | null {
  const count = page?.action_basis?.frame_association.candidate_positions_per_frame.length ?? 0;
  return page && position >= 0 && position < count ? position : null;
}
function jsonBytes(value: unknown): number {
  try { return new Blob([JSON.stringify(value)]).size; } catch { return JSON.stringify(value).length; }
}
