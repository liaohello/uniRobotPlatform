/**
 * Frame-linked browsing for one Episode on the frame-link-2 contract: the image, the robot state
 * linked to that same frame, the provenance and the named recorded-time quantities behind both.
 *
 * Reads only (the single `frames` GET plus the existing `assets` GET). The pane owns its serials: an
 * Episode/run switch, a page, filter or time-window change, a frame move or an unmount drops every
 * older response and every older asset decode, and a frame whose media is not `present` never keeps
 * the previous frame's image. Nothing here touches live Actual/Target or control; the model surface
 * below is the fixed reference, whose pose is only ever moved by joints the mapping gate allows.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Icon } from './Icon';
import { HistoryModelPane } from './history-model-pane';
import { describeHistoryError, type PlatformEpisodeApi } from '../adapters/platform-episodes';
import {
  NO_FRAME_CONTEXT, ambiguousRoleCount, clockSamenessText, frameAutoLoadRef, frameBoundaryNotice, frameMediaRefs,
  framePageExplanation, framePageKind, frameSelectableBases, frameStopNote, frameWindowGate, linkageScopeText,
  mediaDeclarationText, provenanceRowsOf, quantityRowsOf, readFramesPage, recorderDeclaredOf, roleCoverageText,
  roleRowsOf, selectionRulesText, simQuantityKeysOf, stateQuantityKeysOf, stateRowsOf, stateSelectionOf, statusPrecedenceText,
  timeSemanticsText, versionMigrationText,
  type FrameDto, type FramePageDto, type FrameReadContext,
} from '../adapters/platform-frames';

/** A frame page is bounded by the reader's own limit (1–200); 1/5/20 keep a single read cheap. */
const FRAME_PAGE_SIZES = [1, 5, 20] as const;
/** UI cadence over frames that were already read; never the recorded capture rate. */
const CADENCES = [{ ms: 500, label: '500 ms/帧' }, { ms: 1000, label: '1 s/帧' }, { ms: 2000, label: '2 s/帧' }];

interface FrameTarget { episodeId: string; runId: string | null }
interface FrameAsset {
  token: number; sampleId: string; field: string; uri: string; availability: string;
  status: 'idle' | 'loading' | 'bytes' | 'failed' | 'not-loaded'; url: string | null; mediaType: string; bytes: number;
  sha: string; declaredSha: string | null; declaredBytes: string; agreesWithRow: string; note: string; error: string;
  decoded: 'unknown' | 'ok' | 'failed';
}
const NO_FRAME_ASSET: FrameAsset = { token: 0, sampleId: '', field: '', uri: '', availability: 'none', status: 'idle', url: null, mediaType: '', bytes: 0, sha: '', declaredSha: null, declaredBytes: 'null', agreesWithRow: 'null', note: '', error: '', decoded: 'unknown' };

export function FrameBrowser({ api, episodeId, runId }: { api: PlatformEpisodeApi; episodeId: string; runId: string | null }) {
  const [page, setPage] = useState<FramePageDto | null>(null);
  const [error, setError] = useState('');
  const [index, setIndex] = useState(0);
  const [limit, setLimit] = useState<number>(5);
  const [context, setContext] = useState<FrameReadContext>(NO_FRAME_CONTEXT);
  const [sampleText, setSampleText] = useState('');
  const [windowText, setWindowText] = useState<{ base: string; from: string; to: string }>({ base: '', from: '', to: '' });
  const [windowError, setWindowError] = useState('');
  const [asset, setAsset] = useState<FrameAsset>(NO_FRAME_ASSET);
  const [notice, setNotice] = useState('');
  const [playing, setPlaying] = useState(false);
  const [cadence, setCadence] = useState(500);

  // One guard chain: the read must be the newest one AND still belong to the episode/run that asked.
  const contextRef = useRef(context); contextRef.current = context;
  const limitRef = useRef(limit); limitRef.current = limit;
  const targetRef = useRef<FrameTarget>({ episodeId, runId });
  const pageSerial = useRef(0);
  const assetSerial = useRef(0);
  const frameKeyRef = useRef('');
  const urlRef = useRef<string | null>(null);
  const controllers = useRef<AbortController[]>([]);
  const track = (controller: AbortController) => { controllers.current.push(controller); return controller; };
  const live = (token: number, target: FrameTarget) => token === pageSerial.current
    && target.episodeId === targetRef.current.episodeId && target.runId === targetRef.current.runId;
  const clearMedia = () => { ++assetSerial.current; frameKeyRef.current = ''; revoke(urlRef.current); urlRef.current = null; setAsset(NO_FRAME_ASSET); };

  const readPage = useCallback((offset: number, size: number, ctx: FrameReadContext, opts: { advancedFromHasMore?: boolean; landOn?: 'first' | 'last'; notice?: string } = {}) => {
    if (!episodeId) return;
    const target: FrameTarget = { episodeId, runId };
    const token = ++pageSerial.current;
    controllers.current.forEach((controller) => controller.abort()); controllers.current = [];
    setError(''); setNotice(opts.notice ?? ''); setPlaying(false); clearMedia();
    void readFramesPage({
      episodeId, runId, limit: size, offset,
      ...(ctx.sampleId ? { sampleId: ctx.sampleId } : {}),
      ...(ctx.base ? { timeBase: ctx.base, ...(ctx.from !== null ? { timeFrom: ctx.from } : {}), ...(ctx.to !== null ? { timeTo: ctx.to } : {})} : {}),
    }, track(new AbortController()).signal)
      .then((dto) => {
        if (!live(token, target)) return;
        setPage(dto);
        const position = opts.landOn === 'last' ? Math.max(0, dto.frames.length - 1) : 0;
        setIndex(position);
        bindFrame(dto.frames[position] ?? null);
        if (!dto.frames.length) setNotice(frameStopNote(dto, ctx, Boolean(opts.advancedFromHasMore)));
      })
      .catch((cause) => {
        if (!live(token, target)) return;
        setError(describeHistoryError(cause)); setPage(null); setNotice(''); clearMedia();
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, episodeId, runId]);

  // Opening another Episode is a new identity: the window, the sample condition, the page and the
  // bound image all drop, so no number typed for one Episode is ever reused for another.
  useEffect(() => {
    targetRef.current = { episodeId, runId };
    setIndex(0); setContext(NO_FRAME_CONTEXT); contextRef.current = NO_FRAME_CONTEXT;
    setSampleText(''); setWindowText({ base: '', from: '', to: '' }); setWindowError(''); setNotice(''); setError('');
    clearMedia();
    if (!episodeId) { ++pageSerial.current; setPage(null); return; }
    readPage(0, limitRef.current, NO_FRAME_CONTEXT);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [episodeId, runId]);
  useEffect(() => () => { controllers.current.forEach((controller) => controller.abort()); controllers.current = []; revoke(urlRef.current); }, []);

  /** Image, linked state, provenance and the reference surface all follow this one frame object. */
  function bindFrame(frame: FrameDto | null, explicitField?: string | null) {
    if (!frame) { clearMedia(); return; }
    void loadFrameMedia(frame, explicitField ?? null);
  }

  function loadFrameMedia(frame: FrameDto, explicitField: string | null) {
    const target: FrameTarget = { episodeId, runId };
    const refs = frameMediaRefs(frame);
    const ref = explicitField ? refs.find((item) => item.field === explicitField) ?? null : frameAutoLoadRef(refs);
    const token = ++assetSerial.current;
    const key = `${episodeId}|${runId ?? ''}|${frame.sample_id}`;
    frameKeyRef.current = key;
    revoke(urlRef.current); urlRef.current = null;
    if (!ref) {
      setAsset({ ...NO_FRAME_ASSET, token, sampleId: frame.sample_id, field: explicitField ?? '', uri: '', availability: refs.length ? 'not_present' : 'no_items', status: 'not-loaded',
        note: refs.length ? '该帧的引用里没有可按原样读取的 rgb 引用，或所选字段不可读：不显示任何图像，也不保留上一帧的图片冒充当前帧。' : '本帧 media.items 为空：reader 没有给出可读取的引用，界面不按 sample_id 猜文件名。' });
      return;
    }
    if (!ref.loadable) {
      setAsset({ ...NO_FRAME_ASSET, token, sampleId: frame.sample_id, field: ref.field, uri: ref.uri, availability: ref.availability, status: 'not-loaded', declaredSha: ref.declaredSha256, declaredBytes: ref.declaredBytes, agreesWithRow: ref.agreesWithRow, note: ref.note });
      return;
    }
    setAsset({ ...NO_FRAME_ASSET, token, sampleId: frame.sample_id, field: ref.field, uri: ref.uri, availability: ref.availability, status: 'loading', declaredSha: ref.declaredSha256, declaredBytes: ref.declaredBytes, agreesWithRow: ref.agreesWithRow, note: ref.note });
    void api.asset(target.episodeId, target.runId, ref.uri, ref.declaredSha256, track(new AbortController()).signal)
      .then((value) => {
        if (token !== assetSerial.current || frameKeyRef.current !== key) return;
        if (target.episodeId !== targetRef.current.episodeId || target.runId !== targetRef.current.runId) return;
        const inline = value.mediaType.startsWith('image/');
        const url = inline ? URL.createObjectURL(new Blob([value.bytes], { type: value.mediaType })) : null;
        urlRef.current = url;
        setAsset({
          token, sampleId: frame.sample_id, field: ref.field, uri: ref.uri, availability: ref.availability, status: 'bytes', url,
          mediaType: value.mediaType, bytes: value.bytes.byteLength, sha: value.assetSha256, declaredSha: ref.declaredSha256,
          declaredBytes: ref.declaredBytes, agreesWithRow: ref.agreesWithRow, note: ref.note,
          error: inline ? '' : `${value.mediaType || '未知类型'} 不能内联显示：本切片只按字节读取并显示服务端重算摘要，不做 NumPy 数值解码、不生成图像，也不画点云。`,
          decoded: inline ? 'unknown' : 'failed',
        });
      })
      .catch((cause) => {
        if (token !== assetSerial.current || frameKeyRef.current !== key) return;
        setAsset({ ...NO_FRAME_ASSET, token, sampleId: frame.sample_id, field: ref.field, uri: ref.uri, availability: ref.availability, status: 'failed', error: describeHistoryError(cause), declaredSha: ref.declaredSha256, declaredBytes: ref.declaredBytes, agreesWithRow: ref.agreesWithRow, note: ref.note });
      });
  }

  const step = (delta: number) => {
    if (!page) return;
    const frames = page.frames;
    if (!frames.length) { setPlaying(false); setNotice(framePageExplanation(page, contextRef.current)); return; }
    const next = index + delta;
    if (next >= 0 && next < frames.length) { const frame = frames[next]; setIndex(next); bindFrame(frame); return; }
    const ctx = contextRef.current;
    if (next >= frames.length && page.paging.has_more) {
      // v2 keeps next_offset in the anchor file's own line space and re-tests every condition from there.
      readPage(page.paging.next_offset ?? page.paging.offset + page.paging.returned, limitRef.current, ctx, { advancedFromHasMore: true });
      return;
    }
    if (next >= frames.length) { setPlaying(false); setNotice(`本页最后一帧之后服务端 has_more=${String(page.paging.has_more)}（whole_file_scanned=${String(page.paging.scan?.whole_file_scanned)}）：界面停止推进。这只说明本次读取到此为止，不推断录制结束，也不声称已遍历全部帧。`); return; }
    if (page.paging.offset > 0) {
      readPage(Math.max(0, page.paging.offset - limitRef.current), limitRef.current, ctx, { landOn: 'last', notice: '回到上一页的最后一帧（offset 由服务端分页决定；窗口与筛选条件保持不变）。' });
      return;
    }
    setNotice('已到本次读取的起点（offset=0）：不向前伪造帧，也不循环到最后一页。');
  };

  const openSample = (value: string | null) => {
    const next: FrameReadContext = { ...contextRef.current, sampleId: value };
    setContext(next); contextRef.current = next; setWindowError('');
    readPage(0, limitRef.current, next);
  };

  /** Applying a time window: a blank side is "not sent", an invalid side refuses the request. */
  const applyWindow = () => {
    const hasBounds = Boolean(windowText.from.trim() || windowText.to.trim());
    const gate = frameWindowGate(page, windowText.base, hasBounds);
    if (!gate.allowed) { setWindowError(gate.reason); return; }
    const parsed: { from: number | null; to: number | null } = { from: null, to: null };
    for (const side of ['from', 'to'] as const) {
      const raw = windowText[side].trim();
      if (!raw) continue;
      const value = Number(raw);
      if (!Number.isFinite(value)) { setWindowError(`${side === 'from' ? '起点' : '终点'}必须是数值秒（当前 ${raw.slice(0, 24)} 不是有限数值）：不发送请求，也不代替为 0。`); return; }
      parsed[side] = value;
    }
    if (parsed.from !== null && parsed.to !== null && parsed.from > parsed.to) { setWindowError(`起点 ${parsed.from} 大于终点 ${parsed.to}：不自行交换两端，请改正后重试。`); return; }
    const next: FrameReadContext = { ...contextRef.current, base: windowText.base, from: parsed.from, to: parsed.to };
    setWindowError(''); setContext(next); contextRef.current = next;
    readPage(0, limitRef.current, next, { notice: `窗口已生效（${next.base} ${text(next.from)}–${text(next.to)}）：从 offset=0 重读，后续翻页保持该窗口。窗口边界是数值秒，单位按响应 time.units 显示。` });
  };
  const clearWindow = () => {
    const next: FrameReadContext = { ...contextRef.current, base: null, from: null, to: null };
    setWindowText((previous) => ({ ...previous, from: '', to: '' })); setWindowError(''); setContext(next); contextRef.current = next;
    readPage(0, limitRef.current, next, { notice: '已清除时间窗口：回到不带 time_base 的 offset 浏览（reader 要求 time_base 必须伴随边界，所以不带窗口时不发送基）。' });
  };

  useEffect(() => {
    if (!playing || !page) return;
    const timer = setTimeout(() => step(1), cadence);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, cadence, page, index]);

  const frames = page?.frames ?? [];
  const frame = frames[index] ?? null;
  const rows = stateRowsOf(frame);
  const stateSelection = stateSelectionOf(frame);
  const quantities = quantityRowsOf(frame);
  const recorder = recorderDeclaredOf(frame);
  const roles = roleRowsOf(frame, page?.linkage);
  const refs = frameMediaRefs(frame);
  const gate = frameWindowGate(page, windowText.base, Boolean(windowText.from.trim() || windowText.to.trim()));
  const selectable = frameSelectableBases(page);
  const kind = framePageKind(page, context);
  const paged = page?.paging;
  const feedback = frame?.state?.recorder_declared_feedback;
  const activeWindow = context.base ? `${context.base} ${text(context.from)}–${text(context.to)}` : 'none';
  const migration = versionMigrationText(page);
  const ambiguous = ambiguousRoleCount(frame);

  return <section className="history-frame-pane" aria-label="历史帧关联浏览" data-frame-view="true" data-read-only="true"
    data-frame-bound={String(Boolean(page))} data-frame-schema={page?.schema_version ?? 'unread'}
    data-frame-episode={episodeId || 'none'} data-frame-run={runId ?? 'null'}>
    <h3>帧关联浏览 · 图像 — 关联机器人状态 — 来源与时间 <small data-frame-current-sample={frame?.sample_id ?? '—'}>{frame ? frame.sample_id : '未绑定帧'}</small></h3>
    <p className="session-note">一条锚点记录 = 一个持久化图像帧；图像、状态、来源与下面的模型参考都由这同一帧驱动。这里不执行回放、不推进物理、不发送控制，也不做跨流同步。</p>
    {!episodeId && <p className="session-note" data-frame-empty="true">未选择 Episode：先在上方打开一个 Episode，本面板按详情返回的身份（source/run/episode）读取帧页。</p>}
    {error && <div className="session-error" role="alert" data-frame-error>{error}</div>}

    {page && <>
      <dl className="session-fields frame-summary" data-frame-page-kind={kind} data-frame-returned={String(paged?.returned)}
        data-frame-offset={String(paged?.offset)} data-frame-limit={String(paged?.limit)} data-frame-next-offset={text(paged?.next_offset)}
        data-frame-has-more={String(paged?.has_more)} data-frame-next-qualifying={text(paged?.next_qualifying_anchor_line_index)}
        data-frame-examined={String(paged?.anchor_records_examined)} data-frame-post-examined={String(paged?.post_page_records_examined)}
        data-frame-lines-read={String(paged?.anchor_lines?.lines_read)} data-frame-lines-blank={String(paged?.anchor_lines?.blank_lines_skipped)}
        data-frame-lines-oversize={String(paged?.anchor_lines?.oversize_lines_skipped)} data-frame-lines-unparseable={String(paged?.anchor_lines?.unparseable_lines_skipped)}
        data-frame-lines-nonobject={String(paged?.anchor_lines?.non_object_lines_skipped)} data-frame-lines-prefiltered={String(paged?.anchor_lines?.prefiltered_lines_skipped)}
        data-frame-whole-file-scanned={String(paged?.scan?.whole_file_scanned)}
        data-frame-excluded-window={String(paged?.excluded_outside_time_window)} data-frame-excluded-stream={String(paged?.excluded_stream_mismatch)}
        data-frame-excluded-identity={String(paged?.excluded_anchor_identity_mismatch)} data-frame-missing-time-base={String(paged?.records_missing_selected_time_base)}
        data-frame-skipped-before={String(paged?.skipped_before_offset)} data-frame-excluded-no-sample={String(paged?.excluded_without_sample_id)}
        data-frame-excluded-by-sample={String(paged?.excluded_by_sample_id_filter)}
        data-frame-no-total="true" data-frame-window-base={text(page.time.selected_time_base)} data-frame-window-from={text(page.time.time_from)} data-frame-window-to={text(page.time.time_to)}
        data-frame-context-sample={context.sampleId ?? 'none'} data-frame-context-window={activeWindow}
        data-frame-cursor-order={text(page.cursor.order)} data-frame-line-index-clock={String(page.cursor.line_index_is_not_a_clock)}
        data-frame-persist-counter={String(page.cursor.persist_sequence_is_the_recorders_own_counter)}
        data-frame-sync-streams={String(page.time.synchronized_across_streams)} data-frame-deltas-arithmetic={String(page.time.deltas_are_recorded_arithmetic)}
        data-frame-arrival-order-unused={String(page.time.browser_arrival_order_is_not_used)}
        data-frame-migration-from={text(page.version_migration?.from_schema)} data-frame-migration-to={text(page.version_migration?.to_schema)}
        data-frame-anchor={page.anchor.relative_path} data-frame-anchor-stream={page.anchor.stream_id} data-frame-requested-stream={text(page.anchor.requested_stream)}>
        <div><dt>版本迁移（响应原文）</dt><dd data-frame-version-migration={`${migration.head}；移除：${migration.removed.join('；') || 'reader 未列出'}；${migration.note}`}>
          {migration.head}
          <ul>{migration.changed.map((line) => <li key={line}>{line}</li>)}</ul>
          {migration.removed.map((line) => <li key={line} data-frame-removed-field="true"><b>已移除字段</b> {line}</li>)}
          {migration.corrections.map((line) => <li key={line} data-frame-correction="true"><b>本版标注更正</b> {line}</li>)}
          <em>{migration.note}</em></dd></div>
        <div><dt>锚点与游标</dt><dd>锚点流={page.anchor.stream_id} → {page.anchor.relative_path}（requested_stream={text(page.anchor.requested_stream)}）· {text(page.anchor.semantics)} · 顺序={text(page.cursor.order)} · <b>line_index 不是时钟（{String(page.cursor.line_index_is_not_a_clock)}）</b> · persist_sequence 是记录者自己的计数器 · 本页 {frames.length ? `首/末行 ${text(page.cursor.first_line_index)}/${text(page.cursor.last_line_index)} · 首/末 persist_sequence ${text(page.cursor.first_persist_sequence)}/${text(page.cursor.last_persist_sequence)}` : '无行'}</dd></div>
        <div><dt>分页与读到的行（响应原样）</dt><dd>limit={paged?.limit} · offset={paged?.offset} · returned={paged?.returned} · has_more={String(paged?.has_more)} · next_offset={text(paged?.next_offset)} · next_qualifying_anchor_line_index={text(paged?.next_qualifying_anchor_line_index)} · anchor_records_examined={paged?.anchor_records_examined} · post_page_records_examined={paged?.post_page_records_examined} · whole_file_scanned={text(paged?.scan?.whole_file_scanned)}<br/>
          已读行 {paged?.anchor_lines?.lines_read}（空行 {paged?.anchor_lines?.blank_lines_skipped}／超限 {paged?.anchor_lines?.oversize_lines_skipped}／坏行 {paged?.anchor_lines?.unparseable_lines_skipped}／非对象 {paged?.anchor_lines?.non_object_lines_skipped}／预过滤 {paged?.anchor_lines?.prefiltered_lines_skipped}）· skipped_before_offset={paged?.skipped_before_offset} · 排除：stream 不符 {paged?.excluded_stream_mismatch}／无 sample_id {paged?.excluded_without_sample_id}／sample 条件 {paged?.excluded_by_sample_id_filter}／窗口外 {paged?.excluded_outside_time_window}／身份不符 {paged?.excluded_anchor_identity_mismatch} · 缺所选时间基 {paged?.records_missing_selected_time_base} 条<br/>
          <span data-frame-offset-semantics={text(paged?.offset_semantics)}>{text(paged?.offset_semantics)}</span> · <span data-frame-scan-note={text(paged?.scan?.note)}>{text(paged?.scan?.note)}</span> · <b data-frame-total-forbidden="true">响应不提供总帧数，界面不显示也不推算“共 N 帧”</b></dd></div>
        <div><dt>时间基与单位</dt><dd data-frame-selectable-bases={selectable.join(',')} data-frame-units={Object.entries(page.time.units ?? {}).map(([k, v]) => `${k}:${v}`).join(',')}
          >可选数值基（只来自本页）={selectable.join('、') || 'reader 未声明（空数组就是本页的答案，不回退默认基）'} · 本次 selected_time_base={text(page.time.selected_time_base)} · 窗口 {text(page.time.time_from)}–{text(page.time.time_to)} · 单位约定 {Object.entries(page.time.units ?? {}).map(([k, v]) => `${k}→${v}`).join('，') || '未声明'} · synchronized_across_streams={String(page.time.synchronized_across_streams)} · same_clock_verified={text(page.time.same_clock_verified)}</dd></div>
        <div><dt>同钟声明与能证明什么</dt><dd data-frame-clock-sameness={clockSamenessText(page)}>{clockSamenessText(page)}</dd></div>
        <div><dt>关联口径（本页）</dt><dd data-frame-linkage-scope={linkageScopeText(page, frame)}>{linkageScopeText(page, frame)}</dd></div>
        <div><dt>角色覆盖（本页）与状态优先级</dt><dd data-frame-role-coverage={roleCoverageText(page)}>{roleCoverageText(page)}</dd><dd data-frame-status-precedence={statusPrecedenceText(page)}>{statusPrecedenceText(page)}</dd></div>
        <div><dt>选样规则（响应原文）</dt><dd data-frame-selection-rules={selectionRulesText(page)}>{selectionRulesText(page)}</dd></div>
        <div><dt>本页结果</dt><dd data-frame-page-explanation={framePageExplanation(page, context)}>{framePageExplanation(page, context)}</dd></div>
      </dl>

      <div className="session-inline history-controls">
        <button data-frame-play={playing ? 'pause' : 'play'} aria-pressed={playing} disabled={!frames.length}
          onClick={() => { setPlaying(!playing); if (!playing) setNotice('播放只按界面节奏在本页已读取的帧上前进（到页末按 next_offset 继续）；不发命令、不推进物理，也不宣称录制帧率或跨流同步。'); }}>{playing ? '⏸ 暂停' : '▶ 播放'}</button>
        <button data-frame-prev onClick={() => step(-1)}>◀ 上一帧</button>
        <button data-frame-next onClick={() => step(1)}>下一帧 ▶</button>
        <label>每页帧数<select aria-label="帧分页大小" value={limit} onChange={(event) => { const size = Number(event.target.value); setLimit(size); limitRef.current = size; readPage(0, size, contextRef.current, { notice: '改变每页帧数后从 offset=0 重读（保持 sample_id 与时间窗口条件）。' }); }}>{FRAME_PAGE_SIZES.map((size) => <option key={size} value={size}>{size}</option>)}</select></label>
        <label>节奏<select aria-label="界面帧步进节奏" value={cadence} onChange={(event) => setCadence(Number(event.target.value))}>{CADENCES.map((option) => <option key={option.ms} value={option.ms}>{option.label}</option>)}</select></label>
        <span className="chip masked" data-frame-playback-cadence-ui-only="true">节奏只控制界面推进，不是录制帧率</span>
      </div>
      <div className="session-inline">
        <label>按 sample_id 打开<input aria-label="sample_id 精确打开" value={sampleText} placeholder="rgbd_…（精确相等匹配）" onChange={(event) => setSampleText(event.target.value)}/></label>
        <button data-frame-open-sample disabled={!sampleText.trim()} title="只按记录里的 sample_id 精确相等匹配；不做相近匹配，也不按行号或到达顺序" onClick={() => openSample(sampleText.trim() || null)}>打开该帧</button>
        <button data-frame-sample-clear disabled={!context.sampleId} onClick={() => { setSampleText(''); openSample(null); }}>清除 sample 条件</button>
        <span className="chip masked" data-frame-sample-active={context.sampleId ?? 'none'}>sample 条件：{context.sampleId ?? '未设置'}</span>
      </div>
      <div className="session-inline">
        <label>时间基<select aria-label="帧时间基" value={windowText.base} onChange={(event) => { setWindowText((previous) => ({ ...previous, base: event.target.value })); setWindowError(''); }}>
          <option value="">不带窗口（按 offset/sample 浏览）</option>
          {selectable.map((base) => <option key={base} value={base}>{base}</option>)}
        </select></label>
        <label>起点<input aria-label="时间窗口起点" value={windowText.from} placeholder={gate.allowed || windowText.base ? '数值秒（留空=不发送该端）' : '先选时间基'} disabled={!windowText.base} onChange={(event) => setWindowText((previous) => ({ ...previous, from: event.target.value }))}/></label>
        <label>终点<input aria-label="时间窗口终点" value={windowText.to} placeholder={gate.allowed || windowText.base ? '数值秒（留空=不发送该端）' : '先选时间基'} disabled={!windowText.base} onChange={(event) => setWindowText((previous) => ({ ...previous, to: event.target.value }))}/></label>
        <button data-frame-window-apply disabled={!gate.allowed} title={gate.allowed ? '' : gate.reason} onClick={applyWindow}>应用窗口（offset 归零）</button>
        <button data-frame-window-clear disabled={!context.base} onClick={clearWindow}>清除窗口</button>
        <span className="chip masked" data-frame-window-gate={gate.allowed ? 'ready' : 'refused'} data-frame-window-selectable={selectable.join(',')}>{gate.allowed ? `窗口就绪：${windowText.base}` : '窗口不可用（见下方原因）'}</span>
      </div>
      {(windowError || gate.reason) && <p className="session-note" data-frame-window-reason={windowError || gate.reason}>{windowError || gate.reason}</p>}
      {notice && <p className="session-note" role="status" data-frame-notice="true">{notice}</p>}

      <div className="frame-grid">
        <section className="history-stream-pane" data-frame-list="true">
          <h4>本页帧与角色状态</h4>
          <div className="history-cursor" data-frame-index={index} data-frame-sample={frame?.sample_id ?? 'none'}
            data-frame-line={text(frame?.anchor.line_index)} data-frame-persist-seq={text(frame?.anchor.persist_sequence)}
            data-frame-linkage-status={frame?.linkage_status ?? 'none'} data-frame-primary-matched={(frame?.primary_roles_matched ?? []).join('|')}
            data-frame-primary-ambiguous={(frame?.primary_roles_ambiguous ?? []).join('|')} data-frame-ambiguous-count={String(ambiguous)}
            data-frame-declared-ref={frame?.declared_reference_status ?? 'none'} data-frame-state-status={text(frame?.state?.status)}
            data-frame-single-state={text(frame?.state?.single_state_selected)} data-frame-state-candidates={text(frame?.state?.candidate_records)}>
            当前：本页第 {frames.length ? index + 1 : 0}/{frames.length} 帧（不是全局序号）· line_index={text(frame?.anchor.line_index)} · persist_sequence={text(frame?.anchor.persist_sequence)} · linkage_status={text(frame?.linkage_status)} · primary_roles_matched=[{(frame?.primary_roles_matched ?? []).join(',') || '空'}] · primary_roles_ambiguous=[{(frame?.primary_roles_ambiguous ?? []).join(',') || '空'}] · declared_reference_status={text(frame?.declared_reference_status)} · state single={text(frame?.state?.single_state_selected)}/{text(frame?.state?.candidate_records)} 候选
          </div>
          <table className="frame-record-table"><thead><tr><th>line</th><th>persist_seq</th><th>sample_id</th><th>关联</th><th>feedback 引用</th><th>媒体 availability</th></tr></thead>
            <tbody>{frames.map((item, position) => <tr key={`${item.sample_id}-${item.anchor.line_index}`} data-frame-row={item.sample_id} className={position === index ? 'selected' : ''}
              data-row-line={String(item.anchor.line_index)} data-row-persist-seq={text(item.anchor.persist_sequence)} data-row-status={item.linkage_status}
              data-row-primary={(item.primary_roles_matched ?? []).join('|')} data-row-ambiguous={(item.primary_roles_ambiguous ?? []).join('|') || 'none'}
              data-row-declared-ref={item.declared_reference_status} data-row-identity={String(item.anchor.identity?.run_id_matches) + '/' + String(item.anchor.identity?.episode_id_matches)}
              data-row-single-state={text(item.state?.single_state_selected)} data-row-candidates={text(item.state?.candidate_records)}
              data-row-media={item.media.items.map((media) => `${media.field}:${media.availability}`).join('|')}>
              <td>{item.anchor.line_index}</td><td>{text(item.anchor.persist_sequence)}</td>
              <td><button data-frame-pick={item.sample_id} onClick={() => { setIndex(position); bindFrame(item); }}>{item.sample_id}</button></td>
              <td>{item.linkage_status}<small>{item.roles.map((role) => `${role.role}=${role.status}`).join(' · ')}</small></td>
              <td>{item.declared_reference_status}</td>
              <td>{item.media.items.map((media) => `${media.availability}`).join('/')}</td>
            </tr>)}</tbody></table>
          {!frames.length && <p className="session-note" data-frame-list-empty="true">本页没有帧：表格不显示任何行，图像面板保持空，不用上一页的帧填充。</p>}
          <ul className="receipt-layers" data-role-layers="true">{roles.map((role) => <li key={role.role} data-frame-role={role.role} data-role-primary={String(role.primary)} data-role-status={role.status}>
            <b>{role.role}{role.primary ? '（主角色）' : '（帧声明的引用，不计入主角色）'}</b>
            <span className={role.status === 'matched' ? 'ok' : role.status === 'unresolved_reference' || role.status === 'partial' || role.status.startsWith('ambiguous') ? 'unknown' : 'bad'}>{role.status}</span>
            <p>join_key={role.joinKey} · key_value={role.keyValue} · 候选={role.candidates} / matched={role.matched} / 身份不符={role.mismatched} · 命中位置 {role.positions}</p>
            <p data-role-requirement={role.requirement}>完整性要求：{role.requirement}</p>
            <p data-role-kinds={role.kinds} data-role-inventory={role.inventory}>kind 判定：{role.kinds} · 清单 {role.inventory}</p>
            <p data-role-ambiguous={role.ambiguous}>歧义候选：{role.ambiguous}</p>
            <p>角色定义：{role.semantics}</p>
            <p>{role.statusMeaning}{role.reason ? ` ${role.reason}` : ''}</p></li>)}</ul>
          {page.time.clock_sameness && <p className="session-note" data-clock-sameness-verified={String(page.time.clock_sameness.verified_by_reader)} data-clock-sameness-declared={String(page.time.clock_sameness.declared_by_recorder)}>
            clock_sameness：declared_by_recorder={text(page.time.clock_sameness.declared_by_recorder)} · verified_by_reader={text(page.time.clock_sameness.verified_by_reader)} · {page.time.clock_sameness.verified_claim ?? 'reader 未说明'}</p>}
        </section>

        <section className="history-stream-pane" data-frame-state-pane="true">
          <h4>关联机器人状态（该帧的 feedback 记录）</h4>
          {!frame && <p className="session-note" data-frame-state-empty="true">未绑定帧：没有状态可显示。</p>}
          {frame && <>
            <p className="session-note" data-frame-state-join={frame.state.join_key} data-frame-state-key={text(frame.state.key_value)}
              data-frame-state-status={frame.state.status} data-frame-carried-over={String(frame.state.carried_over_from_another_frame)}
              data-frame-interpolated={String(frame.state.interpolated)} data-frame-event-seq={text(frame.state.source?.event_seq)}
              data-frame-single-state={text(frame.state.single_state_selected)} data-frame-state-candidates={text(frame.state.candidate_records)}
              data-frame-state-empty-payload={String(!frame.state.recorded_state)}
              data-frame-record-position={frame.state.source ? `${frame.state.source.relative_path}#${frame.state.source.line_index}` : 'none'}>
              join_key={frame.state.join_key} · key_value={text(frame.state.key_value)} · status={frame.state.status} · candidate_records={text(frame.state.candidate_records)} · single_state_selected={text(frame.state.single_state_selected)} · event_seq={text(frame.state.source?.event_seq)} · 记录位置={frame.state.source ? `${frame.state.source.relative_path}#${frame.state.source.line_index}` : '无命中记录'} · carried_over_from_another_frame={String(frame.state.carried_over_from_another_frame)}（不继承别的帧）· interpolated={String(frame.state.interpolated)}（不插值）<br/>{frame.state.note ?? 'reader 未声明该状态的含义'}</p>
            {stateSelection && !stateSelection.hasRecordedState && <p className="session-blocked" role="note" data-frame-state-none-selected="true">
              <Icon name="info" size={15}/><span>本帧没有单一选中的状态记录（single_state_selected={stateSelection.singleSelected}，候选 {stateSelection.candidateRecords} 条）：界面不挑第一条、不补 0、不沿用上一帧状态，下面的数值面板保持空。{stateSelection.note}</span></p>}
            {stateSelection && stateSelection.candidates.length > 0 && <ul className="receipt-layers" data-state-candidates="true">{stateSelection.candidates.map((candidate, position) => <li key={`${candidate.position}-${position}`} data-state-candidate={candidate.position}>
              <b>候选 {candidate.position}</b><span>{candidate.identity}</span><small>payload 字段：{candidate.payload || 'reader 未返回'}</small></li>)}</ul>}
            <table className="frame-record-table"><thead><tr><th>字段（recorded_state 原值）</th><th>值</th><th>单位</th></tr></thead>
              <tbody>{rows.map((row) => <tr key={row.key} data-state-row={row.key} data-state-unit={row.unit} data-state-declared-unit={String(!row.unit.startsWith('未在 units 表'))}>
                <td>{row.label}<small>{row.note}</small></td><td><code>{row.value}</code></td><td>{row.unit}</td></tr>)}</tbody></table>
            {!rows.length && <p className="session-note" data-state-none="true">{`状态记录 status=${text(frame.state.status)} · single_state_selected=${text(frame.state.single_state_selected)}：本帧没有可显示的 recorded_state 字段（缺失原因见上面的角色口径），不补 0、不用别的帧的状态顶替。`}</p>}
            <p className="session-note" data-declared-reference={text(frame.state.declared_reference?.row_status)}>帧声明的 feedback 引用：feedback_sample_id={text(frame.state.declared_reference?.feedback_sample_id)} · row_status={text(frame.state.declared_reference?.row_status)}。这与上面四个主角色是否 matched 分开显示：引用未解析不等于完全没有状态。</p>
            <p className="session-note" data-feedback-declared-available={String(Boolean(feedback?.available))} data-feedback-declared-time={text(feedback?.feedback_time_s ?? null)} data-feedback-declared-clock={text(feedback?.feedback_clock)} data-feedback-timing-status={text(feedback?.timing_event_status)}>
              原始反馈时间（另列，不与时间差合并）：available={text(feedback?.available)} · timing_event_status={text(feedback?.timing_event_status)} · feedback_time_s={text(feedback?.feedback_time_s ?? null)} · feedback_clock={text(feedback?.feedback_clock)} · 记录者声明的采集钟={feedback?.capture_clocks_declared ? Object.entries(feedback.capture_clocks_declared).map(([k, v]) => `${k}=${v}`).join(',') : '未声明'} · {feedback?.meaning ?? 'reader 未说明其含义'}</p>
          </>}
        </section>

        <section className="history-stream-pane" data-frame-time-pane="true" data-frame-displayed-sample={frame?.sample_id ?? 'none'}>
          <h4>时间与来源（每条都是两个记录字段之差）</h4>
          {!frame && <p className="session-note" data-frame-time-empty="true">未绑定帧：没有时间量可显示。</p>}
          {frame && <>
            <p className="session-note" data-time-semantics={timeSemanticsText(frame)}>{timeSemanticsText(frame)}</p>
            <p className="session-note" data-state-quantity-keys={stateQuantityKeysOf(frame)}>{stateQuantityKeysOf(frame)}</p>
            <p className="session-note" data-sim-quantity-keys={simQuantityKeysOf(frame)}>{simQuantityKeysOf(frame)}</p>
            <p className="session-note" data-recorder-declared={recorder.text} data-recorder-agrees={recorder.agrees}>
              录制器自述的时延字段（原样复制，界面不重测、不折算成状态年龄）：{recorder.text}<br/><em>{recorder.note}</em></p>
            <table className="frame-record-table"><thead><tr><th>时间量（显示口径）</th><th>值</th><th>来源记录／字段／相对什么／单位／钟</th></tr></thead>
              <tbody>{quantities.map((row, position) => <tr key={`${row.key}-${position}`} data-quantity-row={row.key} data-quantity-abs-ms={row.absMs} data-quantity-direction={row.direction}
                data-quantity-unit={row.unit} data-quantity-position={row.position || 'none'} data-quantity-capture={row.captureValue ?? ''} data-quantity-clock={row.clock}>
                <td>{row.display}<small>{row.meaning}</small><small>{row.note}</small></td>
                <td>{row.value} {row.unit}（绝对值 {row.absMs} ms · {row.direction}）</td>
                <td><small>{row.sourceRecord} · field={row.field} · relative_to={row.relativeTo} · {row.position || '无行号'}</small></td></tr>)}</tbody></table>
            {!quantities.length && <p className="session-note" data-quantity-none="true">本帧没有 times.quantities 条目：不自行相减，也不显示推断的时间差。</p>}
          </>}
          <dl className="session-fields">{provenanceRowsOf(page, frame).map((row) => <div key={row.key} data-provenance-row={row.key}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}</dl>
        </section>

        <section className="history-stream-pane" data-frame-media-pane="true" data-frame-displayed-sample={frame?.sample_id ?? 'none'}>
          <h4>媒体（只按本帧 media.items 的引用读取）</h4>
          <p className="session-note" data-media-declaration={mediaDeclarationText(frame)}>{mediaDeclarationText(frame)}</p>
          {!refs.length && <p className="session-note" data-frame-media-none="true">{frame ? '本帧 media.items 没有引用：不显示图像，也不按 sample_id 拼文件名。' : '未绑定帧。'}</p>}
          {refs.map((ref) => <div key={`${ref.field}-${ref.uri}`} className="media-ref" data-frame-media-ref={ref.uri} data-media-field={ref.field} data-media-availability={ref.availability}
            data-media-declared-sha={ref.declaredSha256 ?? 'null'} data-media-declared-bytes={ref.declaredBytes} data-media-bytes-on-disk={ref.bytesOnDisk}
            data-media-agrees-with-row={ref.agreesWithRow} data-media-row-lines={ref.rowLines} data-media-row-candidates={ref.rowCandidates} data-media-rows-conflict={ref.rowsConflict}>
            <b>{ref.field} · {ref.kind}</b><span>{ref.uri}</span>
            <small>声明摘要：{ref.declaredSha256 ? shortOr(ref.declaredSha256) : 'null'}（来自观测行，记录声明而非本次重算）· 声明字节={ref.declaredBytes} · 磁盘字节={ref.bytesOnDisk} · 与观测行 uri 一致={ref.agreesWithRow}（候选 {ref.rowCandidates} 条，行 {ref.rowLines}，行间冲突={ref.rowsConflict}）</small>
            <small>{ref.note}</small>
            <button data-frame-media-pick={ref.field} disabled={!ref.loadable || (asset.status === 'loading' && asset.uri === ref.uri)} title={ref.loadable ? '按该引用读取字节' : '该引用不可读取，界面不绕过'} onClick={() => bindFrame(frame, ref.field)}>按此引用读取</button>
          </div>)}
          {asset.uri || asset.status !== 'idle' ? <div className="asset-frame" data-frame-asset-sample={asset.sampleId} data-frame-asset-field={asset.field || '—'} data-frame-asset-uri={asset.uri || 'none'}
            data-frame-asset-availability={asset.availability} data-frame-asset-status={asset.status} data-frame-asset-media-type={asset.mediaType || '—'}
            data-frame-asset-bytes={String(asset.bytes)} data-frame-asset-sha={asset.sha || 'none'} data-frame-asset-declared={asset.declaredSha ?? 'null'}
            data-frame-asset-declared-bytes={asset.declaredBytes} data-frame-asset-agrees={asset.agreesWithRow}
            data-frame-asset-digest-match={asset.declaredSha && asset.sha ? String(asset.declaredSha === asset.sha) : 'unknown'} data-frame-asset-decoded={asset.decoded}>
            {asset.status === 'loading' && <p className="session-note">正在按 GET …/assets/{asset.uri} 读取字节（带声明摘要时服务端先校验再返回）…</p>}
            {asset.status === 'not-loaded' && <div className="session-blocked" data-frame-asset-unavailable="true"><Icon name="info" size={15}/><span>{asset.note || '该引用不可读取'}（availability={asset.availability}）</span></div>}
            {asset.status === 'failed' && <div className="session-error" role="alert" data-frame-asset-error>{asset.error}</div>}
            {asset.status === 'bytes' && <>
              <p className="session-note" data-frame-declared-line="true">摘要声明：{asset.declaredSha ? `${shortOr(asset.declaredSha)}（media.items.declared_sha256_by_row；请求已带 sha256，服务端不符则不返回字节）` : '该观测行未声明 sha256：请求未带 sha256，本次只能显示服务端算出的摘要'} · 声明字节={asset.declaredBytes}。</p>
              <p className="session-note" data-frame-verified-line="true">本次读取：{asset.bytes} 字节 · content-type={asset.mediaType || '未知'} · 服务端重算 sha256={shortOr(asset.sha)} · 与声明一致={asset.declaredSha && asset.sha ? String(asset.declaredSha === asset.sha) : '无法比较（无声明）'} · 与帧记录的磁盘字节数对照见上面的 availability 行。</p>
              <p className="session-note" data-frame-integrity-line="true">完整性结论：以上两行分别说明“记录声明了什么”和“本次读到了什么”；单帧媒体一致不推出整条 Episode 完整，也不推出录制内容正确，Episode 层完整性仍由上方详情面板的五层单独表达。</p>
              {asset.mediaType.startsWith('image/') && asset.url
                ? <img data-frame-asset-image="true" src={asset.url} alt={`历史帧 ${asset.uri}`} onLoad={() => setAsset((previous) => previous.token === asset.token && previous.uri === asset.uri ? { ...previous, decoded: 'ok' } : previous)}
                  onError={() => setAsset((previous) => previous.token === asset.token && previous.uri === asset.uri ? { ...previous, decoded: 'failed', error: '浏览器解码失败：字节已读取但不产生图像。' } : previous)}/>
                : <div className="session-blocked" data-frame-asset-not-inline="true"><Icon name="info" size={15}/><span>{asset.error || `${asset.mediaType || '未知类型'} 不在可内联显示的类型内；只按字节读取，不伪造图像，也不做 NumPy 数值解码或点云。`}</span></div>}
              {asset.decoded === 'failed' && asset.mediaType.startsWith('image/') && <p className="session-error" data-frame-asset-decode-error="true">图像解码失败：字节存在但未解出图像，界面不显示占位图。</p>}
            </>}
            <p className="session-note">图像与所选帧绑定（sample={asset.sampleId || '—'} · token={asset.token}）：切换 Episode、翻页、改条件或换帧后，迟到的字节与迟到的解码都不会写入新帧，旧图同时清空。</p>
          </div> : null}
        </section>
      </div>

      <HistoryModelPane episodeId={episodeId} runId={runId} sampleId={frame?.sample_id ?? null}/>

      <div className="history-frame-boundary" data-frame-boundary="true" data-3d-disabled={String(page.three_d_replay.this_slice_does_not_enable_3d_replay)}
        data-live-geometry-applied={String(page.three_d_replay.live_geometry_or_actual_may_be_applied)} data-transforms-full-pose={String(page.three_d_replay.transforms_are_full_per_body_pose_sequences)}
        data-pose-slice={text(page.three_d_replay.robot_pose_readiness_slice)}
        data-not-proven={JSON.stringify(page.not_proven ?? [])} data-capability-limits={(page.capability_limits ?? []).join('|')}>
        <Icon name="info" size={15}/><div><b>这一片段的边界（先说这个）</b><p>{frameBoundaryNotice(page)}</p></div></div>
    </>}
  </section>;
}

function revoke(url: string | null) { if (url) URL.revokeObjectURL(url); }
const text = (value: unknown) => value === undefined || value === null || value === '' ? 'null' : String(value);
const shortOr = (value: string | null | undefined) => !value ? 'null' : value.length > 20 ? `${value.slice(0, 16)}…` : value;
