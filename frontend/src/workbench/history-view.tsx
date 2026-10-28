/**
 * History Episode browsing and single-stream read-only playback.
 *
 * The view is rendered outside WorkbenchContext and receives only PlatformEpisodeApi: no live sample,
 * no monitor, no Target/Ghost, no execution service, no polling. Every async result is bound to the
 * episode / stream / cursor selection that issued it, and media decodes are dropped when that
 * selection has already moved on.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Icon } from './Icon';
import { FrameBrowser } from './frame-browser';
import {
  PlatformEpisodeApi, ambiguousRuns, associationNotice, autoLoadRef, checksumFinding, describeHistoryError, emptyListKind,
  integrityFacets, isAmbiguous, mediaRefsOf, pageExplanation, pageKind, parseSeekValue, presentTimeBases, rowViews,
  seekGate, streamViews, threeDNotice, timeFieldOf, trainingNotice, unitOf,
  type EpisodeDetailDto, type EpisodeListDto, type MediaRef, type RecordPageDto, type StreamPageDto, type StreamView,
} from '../adapters/platform-episodes';

const PAGE_SIZES = [10, 25, 50] as const;
const RECORD_PAGE_SIZES = [5, 20, 50] as const;
const STATUS_OPTIONS = ['', 'COMPLETE', 'FAILED', 'INCOMPLETE', 'RECORDING'] as const;
/** Playback is a UI cadence over recorded records; it is never presented as the recorded frame rate. */
const CADENCES = [{ ms: 250, label: '250 ms/记录' }, { ms: 500, label: '500 ms/记录' }, { ms: 1000, label: '1 s/记录' }];
/** The reader's own event_seq range parameters; blank means "do not send the filter". */
interface Range { from: number | null; to: number | null }

interface Selection { episodeId: string; runId: string | null; streamId: string }
const NO_SELECTION: Selection = { episodeId: '', runId: null, streamId: '' };
interface AssetState { token: number; uri: string | null; field: string; role: string; url: string | null; mediaType: string; bytes: number; sha: string; declaredSha: string | null; declaredSource: string; status: 'idle' | 'loading' | 'bytes' | 'failed'; error: string; decoded: 'unknown' | 'ok' | 'failed' }
const NO_ASSET: AssetState = { token: 0, uri: null, field: '', role: '', url: null, mediaType: '', bytes: 0, sha: '', declaredSha: null, declaredSource: '', status: 'idle', error: '', decoded: 'unknown' };

export function HistoryView({ api, onLeave }: { api: PlatformEpisodeApi; onLeave: () => void }) {
  const [filterStatus, setFilterStatus] = useState('');
  const [filterRun, setFilterRun] = useState('');
  const [limit, setLimit] = useState<number>(10);
  const [offset, setOffset] = useState(0);
  const [list, setList] = useState<EpisodeListDto | null>(null);
  const [listError, setListError] = useState('');
  const [listState, setListState] = useState<'idle' | 'loading' | 'ready' | 'failed'>('idle');
  const [selection, setSelection] = useState<Selection>(NO_SELECTION);
  const [detail, setDetail] = useState<EpisodeDetailDto | null>(null);
  const [detailError, setDetailError] = useState('');
  const [streamPayload, setStreamPayload] = useState<StreamPageDto | null>(null);
  const [records, setRecords] = useState<RecordPageDto | null>(null);
  const [recordsError, setRecordsError] = useState('');
  const [index, setIndex] = useState(0);
  const [timeBase, setTimeBase] = useState<string>('');
  const [seekText, setSeekText] = useState('');
  const [seekError, setSeekError] = useState('');
  const [rangeText, setRangeText] = useState<{ from: string; to: string }>({ from: '', to: '' });
  const [range, setRange] = useState<Range>({ from: null, to: null });
  const [rangeError, setRangeError] = useState('');
  const [playing, setPlaying] = useState(false);
  const [cadence, setCadence] = useState(500);
  const [pageLimit, setPageLimit] = useState<number>(5);
  const [asset, setAsset] = useState<AssetState>(NO_ASSET);
  const [notice, setNotice] = useState('');
  const [ambiguousRunIds, setAmbiguousRunIds] = useState<string[]>([]);
  const [openEpisodeId, setOpenEpisodeId] = useState('');
  const [openRunId, setOpenRunId] = useState('');

  // One guard for every read: a response or an image decode may only land while the selection that
  // produced it is still the current one.
  const selectionRef = useRef(selection); selectionRef.current = selection;
  const rangeRef = useRef(range); rangeRef.current = range;
  const listSerial = useRef(0);
  const detailSerial = useRef(0);
  const recordsSerial = useRef(0);
  const assetSerial = useRef(0);
  const controllers = useRef<AbortController[]>([]);
  const track = (c: AbortController) => { controllers.current.push(c); return c; };
  const sameSelection = (a: Selection, b: Selection) => a.episodeId === b.episodeId && a.runId === b.runId && a.streamId === b.streamId;
  const liveDetail = (token: number, target: Selection) => token === detailSerial.current && sameSelection(target, selectionRef.current);
  const liveRecords = (token: number, target: Selection) => token === recordsSerial.current && sameSelection(target, selectionRef.current);
  const latestUrl = useRef<string | null>(null);
  const clearAsset = () => { ++assetSerial.current; revoke(latestUrl.current); latestUrl.current = null; setAsset(NO_ASSET); };
  /**
   * A seek value and its error belong to one episode + stream + time base. Anything that changes
   * that context drops both, so a number typed in seconds is never reinterpreted as another
   * stream's unit and an old refusal never reads as a new finding.
   */
  const clearSeek = () => { setSeekText(''); setSeekError(''); };

  const loadList = useCallback((want: { offset: number; limit: number; status: string; run: string }) => {
    const token = ++listSerial.current;
    controllers.current.forEach((c) => c.abort()); controllers.current = [];
    setListState('loading'); setListError('');
    void api.listEpisodes({ limit: want.limit, offset: want.offset, ...(want.status ? { recording_status: want.status } : {}), ...(want.run ? { run_id: want.run } : {}) }, track(new AbortController()).signal)
      .then((dto) => { if (token !== listSerial.current) return; setList(dto); setListState('ready'); })
      .catch((cause) => { if (token !== listSerial.current) return; setListError(describeHistoryError(cause)); setListState('failed'); });
  }, [api]);
  useEffect(() => { loadList({ offset, limit, status: filterStatus, run: filterRun.trim() }); }, []);
  useEffect(() => () => { controllers.current.forEach((c) => c.abort()); controllers.current = []; revoke(latestUrl.current); }, []);

  const openEpisode = (runId: string | null, episodeId: string) => {
    const next: Selection = { episodeId, runId, streamId: '' };
    const token = ++detailSerial.current;
    // Bind the context at intent time, not at render time: a fixture-fast response can otherwise
    // resolve before React commits and be mistaken for a stale result.
    selectionRef.current = next;
    setSelection(next); setDetail(null); setStreamPayload(null); setRecords(null); setRecordsError('');
    setDetailError(''); setIndex(0); setTimeBase(''); setPlaying(false); setAmbiguousRunIds([]); setNotice('');
    clearSeek(); setRangeText({ from: '', to: '' }); setRange({ from: null, to: null }); setRangeError('');
    clearAsset();
    const controller = track(new AbortController());
    void api.getEpisode(episodeId, runId, controller.signal).then((dto) => {
      if (!liveDetail(token, next)) return;
      setDetail(dto);
      void api.listStreams(episodeId, runId, track(new AbortController()).signal)
        .then((catalog) => { if (liveDetail(token, next) && 'declared_status' in catalog) setStreamPayload(catalog); })
        .catch(() => { /* the detail already carries the same stream rows; the catalogue is additive */ });
      const first = (dto.streams ?? [])[0]?.stream_id ?? '';
      if (first) void openStream(next.episodeId, next.runId, first, baseHint(dto, dto.time?.available_time_bases, first));
    }).catch((cause) => {
      if (!liveDetail(token, next)) return;
      if (isAmbiguous(cause)) { setAmbiguousRunIds(ambiguousRuns(cause)); setDetailError(`${describeHistoryError(cause)}；请在下方 run_id 中输入其一后重试`); }
      else setDetailError(describeHistoryError(cause));
    });
  };
  /** Choosing a stream is a new cursor context: the previous page, seek box, filter, media and playback all stop. */
  const openStream = (episodeId: string, runId: string | null, streamId: string, base: string) => {
    const next: Selection = { episodeId, runId, streamId };
    const token = ++recordsSerial.current;
    selectionRef.current = next;
    setSelection(next); setTimeBase(base); setIndex(0); setPlaying(false); setRecordsError(''); setRecords(null);
    clearSeek(); setNotice('');
    clearAsset();
    return readPage(next, 0, pageLimit, base, token);
  };
  const readPage = (target: Selection, pageOffset: number, size: number, base: string, token: number) => {
    // A page read carries no time_base: the reader requires a range with every base
    // (400 time_range_required), so browsing stays on offset pages and only seek sends base+from.
    void api.readRecords({
      episodeId: target.episodeId, runId: target.runId, streamId: target.streamId, limit: size, offset: pageOffset,
      ...(rangeRef.current.from !== null ? { eventSeqFrom: rangeRef.current.from } : {}),
      ...(rangeRef.current.to !== null ? { eventSeqTo: rangeRef.current.to } : {}),
    }, track(new AbortController()).signal)
      .then((dto) => {
        if (!liveRecords(token, target)) return;
        setRecords(dto); setIndex(0); setRecordsError('');
        if (!base) {
          const present = presentTimeBases(dto.records.map((r) => r.record));
          if (present.length) setTimeBase(present[0]);
        }
        bindMedia(dto.records.length ? dto.records[0].record : null, target);
      })
      .catch((cause) => { if (!liveRecords(token, target)) return; setRecordsError(describeHistoryError(cause)); setRecords(null); clearAsset(); });
  };
  /** Records and media move together: a page with nothing in it must not keep the previous record's asset. */
  function bindMedia(record: Record<string, unknown> | null, target: Selection, explicitUri?: string | null) {
    if (!record || !target.streamId) { clearAsset(); return; }
    void loadMediaFor(target, record, explicitUri);
  }

  const step = (delta: number) => {
    if (!records) return;
    if (!records.records.length) { setPlaying(false); setNotice(pageExplanation(records)); return; }
    const next = index + delta;
    if (next >= 0 && next < records.records.length) {
      const entry = records.records[next];
      setIndex(next);
      // Media follows the cursor: the record now in view carries its own asset reference.
      bindMedia(entry.record, selectionRef.current);
      return;
    }
    const target = selectionRef.current;
    if (next >= records.records.length && records.paging.has_more) {
      const token = ++recordsSerial.current;
      readPage(target, records.paging.next_offset ?? records.paging.offset + records.paging.returned, pageLimit, timeBase, token);
      setNotice('本页已到末尾：按 offset 读取下一页后从首条继续（行号连续，但不是时间轴）。');
      return;
    }
    if (next < 0 && records.paging.offset > 0) {
      const token = ++recordsSerial.current;
      const back = Math.max(0, records.paging.offset - pageLimit);
      void api.readRecords({
        episodeId: target.episodeId, runId: target.runId, streamId: target.streamId, limit: pageLimit, offset: back,
        ...(range.from !== null ? { eventSeqFrom: range.from } : {}), ...(range.to !== null ? { eventSeqTo: range.to } : {}),
      }, track(new AbortController()).signal)
        .then((dto) => {
          if (!liveRecords(token, target)) return;
          setRecords(dto); setIndex(Math.max(0, dto.records.length - 1)); setRecordsError('');
          bindMedia(dto.records.length ? dto.records[dto.records.length - 1].record : null, target);
        })
        .catch((cause) => { if (liveRecords(token, target)) setRecordsError(describeHistoryError(cause)); });
      setNotice('回到上一页的最后一条（offset 由服务端分页决定）。');
      return;
    }
    setPlaying(false);
    setNotice(delta > 0 ? '已到本页末尾且服务端 has_more=false：播放停止。这不代表录制结束，也不推导任何终态。' : '已到本次读取起点。');
  };

  const seek = () => {
    if (!selection.episodeId) { setSeekError('未选择 Episode：没有可定位的记录时间。'); return; }
    const gate = seekGate(records, timeBase);
    if (!gate.allowed) { setSeekError(gate.reason); return; }
    const parsed = parseSeekValue(seekText);
    if (parsed.error) { setSeekError(parsed.error); return; }
    const target = selectionRef.current;
    const token = ++recordsSerial.current;
    setSeekError(''); setPlaying(false); setRecordsError('');
    void api.readRecords({
      episodeId: target.episodeId, runId: target.runId, streamId: target.streamId, limit: pageLimit, offset: 0,
      timeBase, timeFrom: parsed.value as number,
      ...(range.from !== null ? { eventSeqFrom: range.from } : {}), ...(range.to !== null ? { eventSeqTo: range.to } : {}),
    }, track(new AbortController()).signal)
      .then((dto) => {
        if (!liveRecords(token, target)) return;
        setRecords(dto); setIndex(0);
        const missing = dto.time.records_without_the_selected_base ?? 0;
        setNotice(dto.records.length
          ? `已定位到 ${timeBase} ≥ ${parsed.value} 的首条（line_index=${dto.records[0].line_index}）；本次扫描中 ${missing} 条记录没有该时间基，未补成 0。`
          : `${timeBase} ≥ ${parsed.value} 在本流无记录（返回 ${dto.records.length} 条）：${pageExplanation(dto)}`);
        bindMedia(dto.records.length ? dto.records[0].record : null, target);
      })
      .catch((cause) => { if (liveRecords(token, target)) setSeekError(describeHistoryError(cause)); });
  };

  /** Applying an event_seq range is a new read intent on the same stream: it re-reads from offset 0. */
  const applyRange = () => {
    const parsed: Range = { from: null, to: null };
    for (const side of ['from', 'to'] as const) {
      const raw = rangeText[side].trim();
      if (!raw) continue;
      const value = Number(raw);
      if (!Number.isInteger(value)) { setRangeError(`${side === 'from' ? '起点' : '终点'}必须是整数 event_seq（当前 ${raw.slice(0, 24)} 不是）：不发送请求。`); return; }
      parsed[side] = value;
    }
    setRangeError(''); setRange(parsed); rangeRef.current = parsed;
    if (!selection.streamId) return;
    const token = ++recordsSerial.current;
    selectionRef.current = { ...selection };
    setRecords(null); setRecordsError(''); setIndex(0); setNotice(''); clearAsset();
    readPage({ ...selection }, 0, pageLimit, timeBase, token);
  };
  const clearRange = () => {
    const empty: Range = { from: null, to: null };
    setRangeText({ from: '', to: '' }); setRange(empty); rangeRef.current = empty; setRangeError('');
    if (!selection.streamId) return;
    const token = ++recordsSerial.current;
    selectionRef.current = { ...selection };
    setRecords(null); setRecordsError(''); setIndex(0); setNotice(''); clearAsset();
    readPage({ ...selection }, 0, pageLimit, timeBase, token);
  };

  const current = records?.records[index] ?? null;
  const refs: MediaRef[] = useMemo(() => (current ? mediaRefsOf(current.record, streamPayload ?? detail) : []), [current, streamPayload, detail]);
  const primary = autoLoadRef(refs);

  /** Media follows the record's own reference. Bytes are bounded and a stale decode never lands. */
  function loadMediaFor(target: Selection, record: Record<string, unknown>, explicitUri?: string | null) {
    const list = mediaRefsOf(record, streamPayload ?? detail);
    const ref = (explicitUri ? list.find((item) => item.uri === explicitUri) : null) ?? autoLoadRef(list);
    const token = ++assetSerial.current;
    revoke(latestUrl.current); latestUrl.current = null;
    if (!ref) { setAsset({ ...NO_ASSET, token }); return; }
    setAsset({ ...NO_ASSET, token, uri: ref.uri, field: ref.field, role: ref.role, declaredSha: ref.declaredSha256, declaredSource: ref.declaredShaSource, status: 'loading' });
    void api.asset(target.episodeId, target.runId, ref.uri, ref.declaredSha256, track(new AbortController()).signal)
      .then((value) => {
        if (token !== assetSerial.current || !sameSelection(target, selectionRef.current)) return;
        const inline = value.mediaType.startsWith('image/');
        const url = inline ? URL.createObjectURL(new Blob([value.bytes], { type: value.mediaType })) : null;
        latestUrl.current = url;
        setAsset({
          token, uri: ref.uri, field: ref.field, role: ref.role, url, mediaType: value.mediaType, bytes: value.bytes.byteLength,
          sha: value.assetSha256, declaredSha: ref.declaredSha256, declaredSource: ref.declaredShaSource, status: 'bytes',
          decoded: inline ? 'unknown' : 'failed',
          error: inline ? '' : `${value.mediaType || '未知类型'} 不能内联显示：本切片只按字节读取并显示服务端重算摘要，不把它渲染成图像。`,
        });
      })
      .catch((cause) => {
        if (token !== assetSerial.current || !sameSelection(target, selectionRef.current)) return;
        setAsset({ ...NO_ASSET, token, uri: ref.uri, field: ref.field, role: ref.role, declaredSha: ref.declaredSha256, declaredSource: ref.declaredShaSource, status: 'failed', error: describeHistoryError(cause) });
      });
  }
  // The image element itself decides "decoded": a decode that finishes after the cursor moved is dropped.
  const onImageLoad = (token: number, uri: string | null) => () => setAsset((previous) => previous.token === token && previous.uri === uri ? { ...previous, decoded: 'ok', error: '' } : previous);
  const onImageError = (token: number, uri: string | null) => () => setAsset((previous) => previous.token === token && previous.uri === uri ? { ...previous, decoded: 'failed', error: '浏览器解码失败：字节已读取但不产生图像。' } : previous);

  useEffect(() => {
    if (!playing || !records) return;
    const timer = setTimeout(() => step(1), cadence);
    return () => clearTimeout(timer);
  }, [playing, cadence, records, index]);

  const rows = list ? rowViews(list) : [];
  const facets = detail ? integrityFacets(detail) : [];
  const finding = detail ? checksumFinding(detail) : null;
  const streamRows = streamViews(streamPayload ?? detail ?? { streams: [] } as unknown as StreamPageDto);
  const gate = seekGate(records, timeBase);
  const baseOptions = useMemo(() => {
    const declared = selection.streamId ? detail?.time?.available_time_bases?.[selection.streamId] : undefined;
    const inRecords = records ? presentTimeBases(records.records.map((r) => r.record)) : [];
    return [...new Set([...(declared?.time_bases_in_first_record ?? []), ...inRecords])];
  }, [detail, records, selection.streamId]);
  const filteredEmpty = Boolean(list && list.episodes.length === 0);
  const pageField = current ? timeFieldOf(current.record, timeBase || 'wall_utc') : null;
  const eventSeq = typeof current?.record.event_seq === 'number' ? current.record.event_seq : null;
  const kind = pageKind(records);
  const rangeInfo = records?.filtering?.event_seq_range;

  return <section className="history-view" aria-label="历史 Episode 只读浏览" data-history-view="true" data-read-only="true">
    <header className="scene-setup-header">
      <div><h2>历史 Episode · 只读浏览、单流播放与帧关联</h2>
        <p>来源固定为历史读取候选：记录浏览走 episode-read-1，下方帧面板走 frame-link-2（一条锚点记录=一个持久化图像帧），模型面板走 history-pose-1（固定模型树 + 按部件 part_readiness 门控的历史姿态）。这里只读录制事实，不发送动作、不推进在线物理、不改写原始记录，也不提供跨流同步、整车重建、已验证的 3D 历史回放或统一时间游标。</p></div>
      <div className="scene-setup-badges">
        <span className="chip strong" data-history-source={list?.source.source_id ?? detail?.source.source_id ?? 'unread'}>source {list?.source.source_id ?? detail?.source.source_id ?? '未读取'}</span>
        <span className="chip masked" data-cross-stream={records ? (records.time.synchronized_across_streams ? 'synchronised' : 'unsynchronised') : 'unknown'}>跨流未同步{synchronizedSuffix(records)}</span>
        <button onClick={() => { setPlaying(false); onLeave(); }}>返回实时视图</button>
      </div>
    </header>
    <div className="history-body">
      <section className="history-list-pane" data-list-state={listState}>
        <h3>Episode 列表</h3>
        <div className="session-inline">
          <label>状态筛选<select aria-label="录制状态筛选" value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value); setOffset(0); loadList({ offset: 0, limit, status: e.target.value, run: filterRun.trim() }); }}>
            {STATUS_OPTIONS.map((value) => <option key={value || 'any'} value={value}>{value || '不限（read 返回全部声明）'}</option>)}
          </select></label>
          <label>limit<select aria-label="分页大小" value={limit} onChange={(e) => { const next = Number(e.target.value); setLimit(next); setOffset(0); loadList({ offset: 0, limit: next, status: filterStatus, run: filterRun.trim() }); }}>
            {PAGE_SIZES.map((size) => <option key={size} value={size}>{size}</option>)}
          </select></label>
          <label>run_id（精确）<input aria-label="run_id 筛选" value={filterRun} placeholder="run_…" onChange={(e) => setFilterRun(e.target.value)}/></label>
          <button onClick={() => { setOffset(0); loadList({ offset: 0, limit, status: filterStatus, run: filterRun.trim() }); }}>重新读取首页</button>
        </div>
        {list && <p className="session-note" data-paging-limit={String(list.paging.limit)} data-paging-offset={String(list.paging.offset)} data-paging-returned={String(list.paging.returned)} data-paging-total={String(list.paging.total_matches ?? -1)} data-paging-order={list.paging.order ?? ''}>
          offset={list.paging.offset} · returned={list.paging.returned} · total_matches={text(list.paging.total_matches)} · next_offset={text(list.paging.next_offset)} · order={text(list.paging.order)}（native 列表声明 {text(list.paging.declared_total_from_native_list)} 条）· filters run={text(list.filters.run_id)} status={text(list.filters.recording_status)} episode={text(list.filters.episode_id)}
        </p>}
        {list && <p className="session-note" data-integrity-scope={list.integrity_scope ?? ''} data-capability-limits={(list.capability_limits ?? []).join('|')}>
          列表口径：{text(list.integrity_scope)} · 限制：{(list.capability_limits ?? []).join('；') || 'reader 未声明'}
        </p>}
        {listError && <div className="session-error" role="alert" data-list-error>{listError}</div>}
        {filteredEmpty && !listError && <div className="session-blocked neutral" data-list-empty={emptyListKind(list!)}>
          <Icon name="info" size={15}/><div><b>{emptyListKind(list!) === 'no-records' ? '该 source 下没有可读 Episode 目录' : '筛选无匹配（该 source 仍有其他记录）'}</b>
            <p>total_matches={text(list?.paging.total_matches)} · filters run={text(list?.filters.run_id)} status={text(list?.filters.recording_status)} episode={text(list?.filters.episode_id)}；这是列表读取的结果，不推断录制是否曾经发生过。</p></div></div>}
        <ul className="history-episode-list">{rows.map((row) => <li key={row.identityText} data-episode-row={row.episodeId} data-row-run={row.runId} data-row-source={list?.source.source_id ?? ''}
          data-row-status={row.declaredStatus} data-row-audit={row.auditStatus} data-row-result={row.result} data-row-segments={row.segments} data-row-readable={String(row.readable)}>
          <button data-episode-open={row.episodeId} disabled={!row.runId} onClick={() => openEpisode(row.runId, row.episodeId)}>
            <b>{row.declaredStatus} · {row.episodeId}</b>
            <span>{row.runId}</span>
            <small>{list?.source.source_id ?? '—'} · 身份含 source/run/episode；创建 {row.created} → 结束 {row.ended} · segments={row.segments} · result={row.result} · audit={row.auditStatus}</small>
            <small>{row.title}</small>
            {!row.readable && <small data-row-read-error>{row.readError ?? 'readable=false 且无 read_error 说明'}</small>}
          </button>
        </li>)}</ul>
        <div className="session-inline">
          <button disabled={offset <= 0 || listState === 'loading'} onClick={() => { const next = Math.max(0, offset - limit); setOffset(next); loadList({ offset: next, limit, status: filterStatus, run: filterRun.trim() }); }}>上一页</button>
          <button disabled={list?.paging.next_offset == null || listState === 'loading'} onClick={() => { const next = list?.paging.next_offset ?? 0; setOffset(next); loadList({ offset: next, limit, status: filterStatus, run: filterRun.trim() }); }}>下一页（offset={text(list?.paging.next_offset)}）</button>
        </div>
        <p className="session-note">请求始终带 run_id；task_language 只是显示名，data-episode-open 与 data-row-run 一起才构成身份。</p>
        <div className="session-inline">
          <input aria-label="按 episode_id 打开" placeholder="episode_…" value={openEpisodeId} onChange={(event) => setOpenEpisodeId(event.target.value)}/>
          <input aria-label="按 run_id 打开（可留空）" placeholder="run_…（留空=不带 run_id）" value={openRunId} onChange={(event) => setOpenRunId(event.target.value)}/>
          <button data-history-open disabled={!openEpisodeId.trim()} title="不带 run_id 时，服务端会把重复 episode_id 判为歧义并拒绝跨 run 读取"
            onClick={() => openEpisode(openRunId.trim() || null, openEpisodeId.trim())}>按身份打开</button>
        </div>
        <p className="session-note">这一入口只为验证身份规则：episode_id 单独不构成键。缺 run_id 时界面不猜测，也不合并多个 run 的数据。</p>
      </section>

      <section className="history-detail-pane" data-detail-bound={String(Boolean(detail))}>
        <h3>详情 · 身份 / segment / 可用流 / 完整性</h3>
        {!detail && <p className="session-note" data-detail-empty="true">{detailError ? '详情读取失败，未套用任何缓存身份。' : '未选择 Episode：左侧任选一行即按 run_id + episode_id 读取。'}</p>}
        {detailError && <div className="session-error" role="alert" data-detail-error>{detailError}</div>}
        {ambiguousRunIds.length > 0 && <div className="session-blocked" data-ambiguous-runs={ambiguousRunIds.join(',')}><Icon name="info" size={15}/><div><b>episode_id 在多个 run 下存在（409 episode_id_ambiguous）</b>
          <p>候选 run：{ambiguousRunIds.join(' · ')}。显示名不是唯一键，需显式选择其一后重读，绝不跨 run 串读。</p>
          {ambiguousRunIds.map((run) => <button key={run} data-ambiguous-pick={run} onClick={() => openEpisode(run, selection.episodeId)}>用 {run} 重读</button>)}</div></div>}
        {detail && <>
          <dl className="session-fields" data-detail-run={detail.identity.run_id} data-detail-episode={detail.identity.episode_id} data-detail-source={detail.identity.source_id}
            data-display-name-not-key={String(detail.identity.episode_display_name_is_not_a_key === true)}>
            <div><dt>身份</dt><dd data-identity-triple={`${detail.identity.source_id}|${detail.identity.run_id}|${detail.identity.episode_id}`}>{detail.identity.source_id} · {detail.identity.adapter_id} · {detail.identity.run_id} · {detail.identity.episode_id} · contract={text(detail.identity.native_contract_version)}</dd></div>
            <div><dt>backend_generation</dt><dd data-generation-available={String(Boolean(detail.identity.backend_generation?.available))} data-generation-values={(generationValues(detail.identity.backend_generation)).join(',')}>
              available={text(detail.identity.backend_generation?.available)} · values={text(generationValues(detail.identity.backend_generation).join(','))} · reason={text(detail.identity.backend_generation?.reason)} · scope={text(detail.identity.backend_generation?.scope)}</dd></div>
            <div><dt>目录引用</dt><dd>{text(detail.identity.episode_directory)}</dd></div>
            <div><dt>segments</dt><dd data-segment-count={String((detail.identity.segments ?? []).length)}>{(detail.identity.segments ?? []).map((s) => `${s.recording_segment_id}${s.previous_recording_segment_id ? ` ← ${s.previous_recording_segment_id}` : ''} · ${text(s.status)}/${text(s.termination_reason)} · ${text(s.started_wall_utc)}→${text(s.ended_wall_utc)}`).join(' ｜ ') || 'reader 未返回 segment 列表'}</dd></div>
            <div><dt>可用流</dt><dd data-stream-count={String(streamRows.length)}>{streamRows.map((s) => `${s.streamId}${s.available ? '' : '（不可用）'}`).join(' · ')}</dd></div>
            <div><dt>平台配置关联</dt><dd data-association-known={String(Boolean(detail.platform_association?.known))} data-association-reason={text(detail.platform_association?.reason)}>{associationNotice(detail)}</dd></div>
            <div><dt>训练资格</dt><dd data-training-blocks-read={String(detail.training_qualification?.blocks_raw_read)}>{trainingNotice(detail)}</dd></div>
            <div><dt>录制内模型身份</dt><dd data-recorded-model={text(detail.recorded_model_identity?.model_sha256)} data-recorded-scene={text(detail.recorded_model_identity?.scene_id)}>{text(detail.recorded_model_identity?.model_id)} · {shortOr(detail.recorded_model_identity?.model_sha256)} · scene={text(detail.recorded_model_identity?.scene_id)} · map_mode={text(detail.recorded_model_identity?.map_mode)} · 来源：{text(detail.recorded_model_identity?.source)}</dd></div>
            <div><dt>时间声明</dt><dd data-units={Object.keys(detail.time.units ?? {}).join(',')} data-clocks={(detail.time.clocks_declared_by_run_manifest ?? []).join(',')}>
              clocks={(detail.time.clocks_declared_by_run_manifest ?? []).join('、') || '未声明'} · 记录顺序={text(detail.time.record_order_is_native_append_order)}（native append order）· 浏览器收包顺序不参与={String(detail.time.browser_arrival_order_is_not_used === true)} · 单位约定 {JSON.stringify(detail.time.units ?? {})} · synchronized_across_streams={String(detail.time.synchronized_across_streams)}</dd></div>
            <div><dt>动作类别</dt><dd data-action-classes={Object.entries(detail.action_semantics ?? {}).filter(([k]) => k !== 'note' && k !== 'categories_are_by_recorded_event_type').map(([k, v]) => `${k}:${(v as string[]).join('/')}`).join(' · ')}>{detail.action_semantics?.note ?? 'reader 未声明动作语义分层'}</dd></div>
            <div><dt>媒体摘要</dt><dd data-media-kinds={Object.entries(detail.media_summary?.kinds ?? {}).map(([k, v]) => `${k}:${text(v.count)}`).join(',')} data-media-sha-coverage={Object.entries(detail.media_summary?.kinds ?? {}).map(([k, v]) => `${k}:${text(v.declared_sha256_coverage)}`).join(',')}
              data-media-excluded-count={text(detail.media_summary?.excluded_count)} data-media-symlink-excluded={text(detail.media_summary?.symlink_or_escape_excluded)}>
              {detail.media_summary?.uri_convention ?? 'reader 未声明 URI 约定'} · 声明摘要来源：{text(detail.media_summary?.declared_sha256_source)} · 校验口径：{text(detail.media_summary?.verification)} · 每类样本截断：{Object.entries(detail.media_summary?.kinds ?? {}).map(([k, v]) => `${k} ${text(v.sample?.length)}/${text(v.count)}${v.sample_truncated ? '（截断）' : ''}`).join(' · ') || '无'} · 软链/越界排除：{text(detail.media_summary?.symlink_or_escape_excluded)}（{text(detail.media_summary?.excluded_count)} 项）</dd></div>
            <div><dt>来源身份</dt><dd data-source-release={text(detail.source.native_release_id)} data-source-access={detail.source.access} data-source-root={detail.source.recording_root}
              data-source-root-resolved={text(detail.source.recording_root_resolved ?? detail.identity.recording_root_resolved)} data-source-path-boundary={text(detail.source.path_boundary)}
              data-archive-sha={detail.source.archive_baseline?.aggregate_sha256 ?? ''} data-platform-writes={String(detail.source.platform_writes)}>
              {detail.source.source_id} · {text(detail.source.adapter_id)} · release {text(detail.source.native_release_id)} · access={detail.source.access} · platform_writes={String(detail.source.platform_writes)} · root={detail.source.recording_root}
              {detail.source.path_boundary ? ` · 边界规则：${detail.source.path_boundary}` : ''}
              {detail.source.archive_baseline ? ` · 归档基线 ${shortOr(detail.source.archive_baseline.aggregate_sha256)}（${text(detail.source.archive_baseline.files_hashed)} 文件，仅变更检测参考：${text(detail.source.archive_baseline.meaning)}）` : ''}</dd></div>
            <div><dt>能力限制</dt><dd data-capability-limits={(detail.capability_limits ?? []).join('|')}>{(detail.capability_limits ?? []).join('；') || 'reader 未声明限制'}</dd></div>
          </dl>
          <div className="history-3d-notice" data-three-d-status={detail.three_d_replay.status} data-live-geometry-applied={String(detail.three_d_replay.live_geometry_or_actual_may_be_applied)}>
            <Icon name="info" size={15}/><div><b>历史 3D 限制（先说这个）</b><p>{threeDNotice(detail).text}</p></div></div>
          <p className="session-note" data-integrity-note="true">每层只说明自己，不合并成“全部完整”：下面五行分别来自记录声明、本次生命周期判读、tail 存在性、本次重算明细与未覆盖范围。</p>
          <ul className="receipt-layers" data-integrity-layers="true">
            {facets.map((facet) => <li key={facet.key} data-integrity-layer={facet.key}>
              <b>{facet.label}</b><span className={facet.tone} data-layer-tone={facet.tone}>{facet.tone === 'ok' ? '成立' : facet.tone === 'bad' ? '不成立' : '未证明'}</span>
              <p>{facet.value} · {facet.note}</p></li>)}
          </ul>
          {finding && <p className="session-note" data-checksum-pattern={finding.pattern} data-all-complete-forbidden={String(finding.allCompleteClaimForbidden)}>
            校验结论口径：pattern={finding.pattern}（known_stale_self_check 只适用于被限定在这两个生命周期文件且声明 COMPLETE 的情形）；界面不使用“全部完整”“已验证完整”这类说法。</p>}
          <div className="session-inline">{streamRows.map((s) => <button key={s.streamId} data-stream-option={s.streamId} data-stream-available={String(s.available)} data-stream-records={text(s.records)} data-stream-bytes={text(s.bytes)}
            data-stream-declared-bases={(s.declaredBases ?? []).join(',')} data-stream-reason={text(s.reason)} data-stream-parse-error={text(s.parseError)} data-stream-scan-truncated={String(s.scanTruncated)}
            disabled={!s.available} title={streamTitle(s)}
            aria-pressed={selection.streamId === s.streamId} onClick={() => void openStream(selection.episodeId, selection.runId, s.streamId, baseHint(detail, detail.time?.available_time_bases, s.streamId))}>
            <b>{s.streamId}</b><span>{text(s.records)} 条 · {text(s.bytes)} B · 声明基 {(s.declaredBases ?? []).join(',') || '未声明'}</span></button>)}</div>
          {streamRows.some((s) => !s.available) && <p className="session-blocked" data-missing-stream="true"><Icon name="info" size={15}/><span>不可用的流按原样列出并标明 reason，不静默丢弃，也不生成替代内容。</span></p>}
        </>}
      </section>

      <section className="history-stream-pane" data-stream-bound={String(Boolean(records))}>
        <h3>单流分页与播放 · <small data-current-stream={selection.streamId || '—'}>{selection.streamId || '未选择流'}</small></h3>
        {!records && <p className="session-note" data-records-empty="true">{recordsError ? '本次流读取失败：未显示任何记录，也不回退到其他流。' : '选择一个可用流以按 offset 读取记录。'}</p>}
        {recordsError && <div className="session-error" role="alert" data-records-error>{recordsError}</div>}
        {records && <>
          <dl className="session-fields" data-stream-path={records.stream.relative_path} data-stream-format={records.stream.format} data-stream-file-bytes={text(records.stream.file_bytes)}
            data-cursor-order={text(records.cursor.order)} data-cursor-line-index-clock={String(records.cursor.line_index_is_not_a_clock)}
            data-selected-time-base={records.time.selected_time_base ?? 'none'} data-display-time-base={timeBase || 'none'} data-records-without-base={text(records.time.records_without_the_selected_base)}
            data-numeric-time-bases={(records.time.numeric_time_bases ?? []).join(',')}
            data-corrupt-lines={String((records.integrity.corrupt_lines ?? []).length)} data-over-size-lines={String((records.integrity.lines_over_read_size_limit ?? []).length)}
            data-page-kind={kind} data-page-returned={String(records.paging.returned)}>
            <div><dt>流</dt><dd>{records.stream.stream_id} → {records.stream.relative_path}（{records.stream.format}）· {text(records.stream.file_bytes)} B · {records.stream.semantics}</dd></div>
            <div><dt>游标</dt><dd>order={text(records.cursor.order)} · line_index {text(records.cursor.first_line_index)}–{text(records.cursor.last_line_index)} · event_seq {text(records.cursor.first_event_seq)}–{text(records.cursor.last_event_seq)} · <b>line_index_is_not_a_clock={String(records.cursor.line_index_is_not_a_clock)}：行号只是文件内位置，不换算成时间</b></dd></div>
            <div><dt>本页时间口径</dt><dd data-numeric-bases={(records.time.numeric_time_bases ?? []).join(',')}>selected_time_base={text(records.time.selected_time_base)} · 数值可定位基 {(records.time.numeric_time_bases ?? []).join('、') || 'reader 未声明'} · 单位 {text(records.time.units)} · 无该基的记录 {text(records.time.records_without_the_selected_base)} 条（保持缺失，不补 0）· synchronized_across_streams={String(records.time.synchronized_across_streams)}</dd></div>
            <div><dt>event_seq 区间过滤</dt><dd data-filtering-active={String(Boolean(rangeInfo?.active))} data-filtering-range={rangeInfo ? `${text(rangeInfo.from)}..${text(rangeInfo.to)}` : 'none'}
              data-filtering-excluded={text(rangeInfo?.excluded_without_valid_event_seq)} data-filtering-anomalies={String(rangeInfo?.anomalies?.length ?? 0)}
              data-filtering-anomaly-reasons={(rangeInfo?.anomalies ?? []).map((a) => a.reason).join(',')}>
              active={text(rangeInfo?.active)} · 区间 {text(rangeInfo?.from)}–{text(rangeInfo?.to)} · 因缺失/非整数/布尔 event_seq 被排除 {text(rangeInfo?.excluded_without_valid_event_seq)} 行 · 示例异常 {rangeInfo?.anomalies?.length ? `${rangeInfo.anomalies.length} 条（${rangeInfo.anomalies[0].reason}/${rangeInfo.anomalies[0].value_type}）` : '无'}；不补造序号。{records.filtering?.note ? ` 原文：${records.filtering.note}` : ''}</dd></div>
            <div><dt>本页结果</dt><dd data-page-explanation={pageExplanation(records)}>{pageExplanation(records)}</dd></div>
            <div><dt>本页完整性</dt><dd data-page-scope={records.integrity.scope ?? ''}>损坏行 {text((records.integrity.corrupt_lines ?? []).map((l) => `${l.line_index}${l.column !== undefined ? `@列 ${l.column}` : ''}`).join(','))} · 超限行 {text((records.integrity.lines_over_read_size_limit ?? []).join(','))}（行号）· 声明状态 {text(records.integrity.declared_status?.recording_status)}/{text(records.integrity.declared_status?.audit_status)}（declaration_only={String(records.integrity.declared_status?.declaration_only)}）· 未覆盖：{(records.integrity.not_verified ?? []).join(' · ') || 'reader 未声明'}</dd></div>
          </dl>
          <div className="session-inline history-controls">
            <button data-history-play={playing ? 'pause' : 'play'} aria-pressed={playing} disabled={!records.records.length} onClick={() => { setPlaying(!playing); if (!playing) setNotice('播放只在本流已读取的记录上按界面节奏前进；不发命令、不推进物理、不预测未读取的记录。'); }}>{playing ? '⏸ 暂停' : '▶ 播放'}</button>
            <button data-history-prev onClick={() => step(-1)}>◀ 上一条</button>
            <button data-history-next onClick={() => step(1)}>下一条 ▶</button>
            <label>节奏<select aria-label="界面步进节奏" value={cadence} onChange={(e) => setCadence(Number(e.target.value))}>{CADENCES.map((c) => <option key={c.ms} value={c.ms}>{c.label}</option>)}</select></label>
            <label>每页<select aria-label="记录分页大小" value={pageLimit} onChange={(e) => setPageLimit(Number(e.target.value))}>{RECORD_PAGE_SIZES.map((size) => <option key={size} value={size}>{size}</option>)}</select></label>
            <span className="chip masked" data-playback-cadence-ui-only="true">节奏只控制界面推进，不是录制帧率</span>
          </div>
          <div className="session-inline">
            <label>event_seq 起点<input aria-label="event_seq 起点" value={rangeText.from} placeholder="整数（留空=不筛）" onChange={(e) => setRangeText((p) => ({ ...p, from: e.target.value }))}/></label>
            <label>event_seq 终点<input aria-label="event_seq 终点" value={rangeText.to} placeholder="整数（留空=不筛）" onChange={(e) => setRangeText((p) => ({ ...p, to: e.target.value }))}/></label>
            <button data-history-filter={range.from === null && range.to === null ? 'none' : `${range.from}-${range.to}`} onClick={applyRange}>应用区间（offset 归零重读）</button>
            <button data-history-filter-clear onClick={clearRange}>清除区间</button>
          </div>
          {rangeError && <div className="session-error" role="alert" data-filter-error>{rangeError}</div>}
          <div className="session-inline">
            <label>时间基<select aria-label="时间基" value={timeBase} onChange={(e) => { const base = e.target.value; clearSeek(); setTimeBase(base); if (selection.streamId) void openStream(selection.episodeId, selection.runId, selection.streamId, base); }}>
              <option value="">不按时间基（按行号/序号浏览）</option>
              {baseOptions.map((base) => <option key={base} value={base}>{base} · {unitOf(base)}{gate.allowed || base === '' ? '' : '（非数值基：不能按时间定位）'}</option>)}
            </select></label>
            <label>定位到<input aria-label="定位时间值" value={seekText} placeholder={gate.allowed ? `≥ 数值（${unitOf(timeBase)}），0 合法` : '需要数值时间基'} disabled={!gate.allowed} onChange={(e) => setSeekText(e.target.value)}/></label>
            <button data-history-seek disabled={!gate.allowed} title={gate.allowed ? '' : gate.reason} onClick={seek}>定位</button>
            <span className="chip masked" data-seek-gate={gate.allowed ? 'numeric' : 'refused'} data-seek-numeric-bases={gate.numericBases.join(',')}>{gate.allowed ? `数值基 ${unitOf(timeBase)}` : '本流无可数值定位的基'}</span>
          </div>
          {seekError && <div className="session-error" role="alert" data-seek-error>{seekError}</div>}
          {notice && <p className="session-note" role="status" data-history-notice="true">{notice}</p>}
          <div className="history-cursor" data-cursor-index={index} data-cursor-line={text(current?.line_index)} data-cursor-seq={text(eventSeq)}
            data-cursor-time={pageField?.present ? pageField.display : 'none'} data-cursor-time-unit={pageField?.unit ?? '—'} data-cursor-clock={pageField?.clockId ?? 'null'} data-cursor-time-base={timeBase || 'none'}>
            当前位置：第 {records.records.length ? index + 1 : 0}/{records.records.length} 条本页记录 · line_index={text(current?.line_index)} · event_seq={text(eventSeq)} · {timeBase ? `${timeBase}=` : '无时间基 · '}{pageField ? pageField.display : '—'}{pageField && pageField.present ? `（${pageField.unit}${pageField.clockId ? ` · clock_id=${pageField.clockId}` : ''}）` : ''} · offset={records.paging.offset} · 单位 {text(records.time.units)}
          </div>
          <table className="history-record-table"><thead><tr><th>line</th><th>seq</th><th>类型 / 类别</th><th>时间（所选基）</th><th>sample / 媒体引用（记录自带字段）</th><th>字段</th></tr></thead>
            <tbody>{records.records.map((item, position) => {
              const field = timeFieldOf(item.record, timeBase || 'wall_utc');
              const media = mediaRefsOf(item.record, streamPayload ?? detail);
              const type = typeof item.record.event_type === 'string' ? item.record.event_type : (typeof item.record.sensor_kind === 'string' ? item.record.sensor_kind : null);
              const cls = actionClass(type, detail?.action_semantics);
              return <tr key={item.line_index} data-record-row={String(item.line_index)} className={position === index ? 'selected' : ''} data-record-time-base={field.base} data-record-time-present={String(field.present)} data-record-class={cls}
                data-record-media-fields={media.map((m) => m.field).join('|') || 'none'}>
                <td>{item.line_index}</td><td>{text(item.record.event_seq)}</td>
                <td>{type ?? '—'}<small>{cls}</small></td>
                <td>{field.present ? `${field.display} ${field.unit}` : '无该时间字段'}</td>
                <td>{text(item.record.sample_id)}{media.length ? media.map((m) => <span key={m.uri} data-record-media-ref={`${m.field}=${m.uri}`}>{` · ${m.field}:${m.uri.split('/').pop()}`}</span>) : ' · 无媒体引用'}</td>
                <td><code>{preview(item.record)}</code></td>
              </tr>;
            })}</tbody></table>
          <div className="history-media" data-media-bound={String(Boolean(primary))}>
            <h4>媒体（按记录自带引用读取，有界）</h4>
            {!refs.length && <p className="session-note" data-media-none="true">{current ? '该记录没有 asset_uri / rgb_uri / depth_uri / valid_mask_uri 中的任何引用（部分 sensor_kind 的记录确实为 null）；不用别的记录的图片顶替，也不按 sample_id 猜文件名。' : '未选择记录。'}</p>}
            {refs.map((ref) => <div key={ref.uri} className="media-ref" data-media-ref={ref.uri} data-media-field={ref.field} data-media-role={ref.role} data-media-sample={ref.sampleId ?? 'null'} data-media-declared-sha={ref.declaredSha256 ?? 'null'} data-media-declared-source={ref.declaredShaSource}>
              <b>{ref.field} · {ref.role} · {ref.kind}</b><span>{ref.uri}</span>
              <small>声明摘要：{ref.declaredSha256 ? `${shortOr(ref.declaredSha256)}（来源：${ref.declaredShaSource}）` : `本条无声明摘要（${ref.declaredShaSource}；media_summary 每类只带 20 条样本，覆盖 ` + text(detail?.media_summary?.kinds?.[ref.kind]?.declared_sha256_coverage) + '）'}</small>
              <button data-media-pick={ref.uri} disabled={!gateMedia(ref, asset)} onClick={() => bindMedia(current?.record ?? null, selectionRef.current, ref.uri)}>按此引用读取</button>
            </div>)}
            {asset.uri && <div className="asset-frame" data-asset-uri={asset.uri} data-asset-field={asset.field} data-asset-role={asset.role} data-asset-status={asset.status} data-asset-media-type={asset.mediaType || '—'} data-asset-bytes={String(asset.bytes)}
              data-asset-sha={asset.sha} data-asset-declared={asset.declaredSha ?? 'null'} data-asset-declared-source={asset.declaredSource} data-asset-digest-match={asset.declaredSha && asset.sha ? String(asset.declaredSha === asset.sha) : 'unknown'} data-asset-decoded={asset.decoded}>
              {asset.status === 'loading' && <p className="session-note">正在按 GET …/assets/{asset.uri} 读取字节（带声明摘要时服务端先校验再返回）…</p>}
              {asset.status === 'failed' && <div className="session-error" role="alert" data-asset-error>{asset.error}</div>}
              {asset.status === 'bytes' && <>
                <p className="session-note" data-asset-declared-line="true">摘要声明：{asset.declaredSha ? `${shortOr(asset.declaredSha)}（${asset.declaredSource || '来源未声明'}）· 请求已带 sha256，服务端不符则不返回字节` : `本条记录与 media_summary 都未给出该文件的声明摘要（${asset.declaredSource || '无来源'}）· 请求未带 sha256`}</p>
                <p className="session-note" data-asset-verified-line="true">本次读取：{asset.bytes} 字节 · content-type={asset.mediaType || '未知'} · 服务端重算 sha256={shortOr(asset.sha)} · 与声明一致={asset.declaredSha && asset.sha ? String(asset.declaredSha === asset.sha) : '无法比较（无声明）'}</p>
                <p className="session-note" data-asset-integrity-line="true">完整性结论：只看上面两行，媒体一致不推出整条 Episode 完整，也不推出录制内容正确；Episode 层的完整性仍由详情的五个分层单独表达。</p>
                {asset.mediaType.startsWith('image/') && asset.url
                  ? <img data-asset-image="true" src={asset.url} alt={`历史媒体 ${asset.uri}`} onLoad={onImageLoad(asset.token, asset.uri)} onError={onImageError(asset.token, asset.uri)}/>
                  : <div className="session-blocked" data-asset-not-inline="true"><Icon name="info" size={15}/><span>{asset.error || `${asset.mediaType || '未知类型'} 不在可内联显示的类型内；只按字节读取，不伪造图像。`}</span></div>}
                {asset.decoded === 'failed' && asset.mediaType.startsWith('image/') && <p className="session-error" data-asset-decode-error="true">图像解码失败：字节存在但浏览器未解出图像，界面不显示占位图。</p>}
              </>}
              <p className="session-note">读取引用与当前游标绑定（token={asset.token} · field={asset.field || '—'}）；切换 Episode、流、游标或得到空页后，迟到的字节与迟到的解码都不会写入新上下文。</p>
            </div>}
          </div>
        </>}
        <p className="session-note history-footer">历史视图不挂载 3D 视口、不订阅 live 快照、没有 Target/Ghost，也不发送命令或物理步进；本页所有 GET 都由前端只读代理精确放行。</p>
      </section>
    </div>
    <FrameBrowser api={api} episodeId={detail?.identity.episode_id ?? ''} runId={detail?.identity.run_id ?? null}/>
  </section>;
}

function baseHint(detail: EpisodeDetailDto | null, declared: EpisodeDetailDto['time']['available_time_bases'] | undefined, streamId: string): string {
  const hit = declared?.[streamId];
  if (hit?.available && hit.time_bases_in_first_record?.length) return hit.time_bases_in_first_record[0];
  return '';
}
function streamTitle(s: StreamView) {
  const flags = [s.reason ? `reason=${s.reason}` : '', s.parseError ? `parse_error=${s.parseError}` : '', s.scanTruncated ? 'scan_truncated=true（计数被扫描上限截断，不是总数）' : ''].filter(Boolean).join(' · ');
  return `${s.relativePath} · ${s.semantics}${flags ? ` · ${flags}` : ''}`;
}
function generationValues(generation: EpisodeDetailDto['identity']['backend_generation']): (number | string)[] {
  return generation?.distinct_values ?? generation?.values ?? [];
}
/** A pick is only meaningful for a reference the current record actually declares. */
function gateMedia(ref: MediaRef, asset: AssetState) { return Boolean(ref.uri) && !(asset.status === 'loading' && asset.uri === ref.uri); }
function synchronizedSuffix(records: RecordPageDto | null) {
  if (!records) return '（reader 声明 synchronized_across_streams=false；未读取流时也不声称同步）';
  return records.time.synchronized_across_streams ? '' : '：每条流各自的分页游标互不对齐，界面不把多条流合并成一条时间轴';
}
function actionClass(type: string | null, semantics: EpisodeDetailDto['action_semantics']) {
  if (!type) return 'untyped';
  const maps: [string, readonly string[] | undefined][] = [
    ['recorded_target', semantics?.recorded_target], ['command_intent', semantics?.command_intent],
    ['execution_feedback', semantics?.execution_feedback], ['recorded_state', semantics?.recorded_state], ['lifecycle', semantics?.lifecycle]];
  const hit = maps.find(([, list]) => (list ?? []).includes(type));
  return hit ? hit[0] : 'other_recorded_event';
}
function preview(record: Record<string, unknown>) {
  const keys = Object.keys(record).filter((key) => !['contract_version', 'run_id', 'episode_id'].includes(key));
  return keys.slice(0, 6).map((key) => {
    const value = record[key];
    if (value === null) return `${key}=null`;
    if (typeof value === 'object') return `${key}={${Object.keys(value as object).length} 字段}`;
    return `${key}=${String(value).slice(0, 24)}`;
  }).join(' · ');
}
function revoke(url: string | null) { if (url) URL.revokeObjectURL(url); }
const text = (value: unknown) => value === undefined || value === null || value === '' ? 'null' : String(value);
const shortOr = (value: string | null | undefined) => !value ? 'null' : value.length > 20 ? `${value.slice(0, 16)}…` : value;
