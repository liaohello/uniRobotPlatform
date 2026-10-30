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
import { HistoryFrameCurve } from './history-frame-curve';
import { describeHistoryError, type PlatformEpisodeApi } from '../adapters/platform-episodes';
import {
  CURVE_FRAME_ORDER, NO_FRAME_CONTEXT, ambiguousRoleCount, clockSamenessText, curveXAxesOf, frameActualCurveOf,
  frameAutoLoadRef, frameBoundaryNotice, frameMediaRefs, framePositionKey,
  framePageExplanation, framePageKind, frameSelectableBases, frameStopNote, frameWindowGate, intervalGateOf,
  intervalScheduleOf, intervalStepOf, linkageScopeText, mediaDeclarationText, provenanceRowsOf, quantityRowsOf,
  anchorEchoKey, readFramesPage, recorderDeclaredOf, recordedRangeOf, roleCoverageText, roleRowsOf, selectionRulesText,
  simQuantityKeysOf, stateQuantityKeysOf, stateRowsOf, stateSelectionOf, statusPrecedenceText, timeSemanticsText,
  timeQualitySessionKey, versionMigrationText,
  type FrameDto, type FramePageDto, type FrameReadContext, type IntervalStep,
} from '../adapters/platform-frames';

/** A frame page is bounded by reader's own limit (1–200); 1/5/20 keep a single read cheap. */
const FRAME_PAGE_SIZES = [1, 5, 20] as const;
/**
 * Playback rate is stated as frames shown per second, over frames this page already holds. It is a UI
 * rhythm only: the control is never labelled 原速 or a 真实倍速, and the frames it steps are append-order
 * records, not a clock. It stays available even when the record does not qualify for interval playback.
 */
const CADENCES = [{ fps: 2, label: '每秒 2 帧（界面节奏，不是原速）' }, { fps: 1, label: '每秒 1 帧（界面节奏，不是原速）' }, { fps: 0.5, label: '每秒 0.5 帧（界面节奏，不是原速）' }];
/** The recorded-interval mode is a rate *multiplier* on the recorded gap, never a declared frame rate. */
const SPEEDS = [0.5, 1, 2] as const;
const BASE_MEANING: Record<string, string> = {
  capture_backend_monotonic_s: 'capture_backend_monotonic_s＝采集时刻的原生后端单调钟（记录自己的秒）',
  capture_sim_time_s: 'capture_sim_time_s＝仿真时间，是另一个钟，不与后端单调钟合并解释',
  persist_backend_monotonic_s: 'persist_backend_monotonic_s＝落盘时刻的原生后端单调钟：它含写盘抖动，按它排的是“记录写入的节奏”，不称为机器人运动原速',
};

interface FrameTarget { episodeId: string; runId: string | null }
interface FrameAsset {
  token: number; sampleId: string; positionKey: string; field: string; uri: string; availability: string;
  status: 'idle' | 'loading' | 'bytes' | 'failed' | 'not-loaded'; url: string | null; mediaType: string; bytes: number;
  sha: string; declaredSha: string | null; declaredBytes: string; agreesWithRow: string; note: string; error: string;
  decoded: 'unknown' | 'ok' | 'failed';
}
const NO_FRAME_ASSET: FrameAsset = { token: 0, sampleId: '', positionKey: 'none', field: '', uri: '', availability: 'none', status: 'idle', url: null, mediaType: '', bytes: 0, sha: '', declaredSha: null, declaredBytes: 'null', agreesWithRow: 'null', note: '', error: '', decoded: 'unknown' };

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
  const [cadenceFps, setCadenceFps] = useState(2);
  /** Two playback modes, chosen explicitly by the operator: a UI rhythm, or the recorded interval. */
  const [playMode, setPlayMode] = useState<'ui_cadence' | 'recorded_interval'>('ui_cadence');
  const [intervalBase, setIntervalBase] = useState('');
  const [speed, setSpeed] = useState<number>(1);
  /** The census is read on demand, once per source/run/episode/stream playback session. */
  const [census, setCensus] = useState<{ page: FramePageDto; key: string } | null>(null);
  const [censusStatus, setCensusStatus] = useState<'idle' | 'loading' | 'ready' | 'refused'>('idle');
  const [censusError, setCensusError] = useState('');
  const [censusReads, setCensusReads] = useState(0);
  /** A page already read but held back until its recorded interval has elapsed. */
  const [held, setHeld] = useState<{ page: FramePageDto; step: IntervalStep; armedAt: number } | null>(null);
  /** What the last armed step planned, what actually happened and how long data took: reported apart. */
  const [plan, setPlan] = useState<{ kind: string; plannedMs: number | null; actualMs: number | null; bufferMs: number | null; gapS: number | null; cross: boolean; note: string } | null>(null);
  /** The x axis of the recorded-Actual curve: frame order by default, a raw clock base only if complete. */
  const [curveX, setCurveX] = useState<string>(CURVE_FRAME_ORDER);
  const playingRef = useRef(false); playingRef.current = playing;
  const playModeRef = useRef(playMode); playModeRef.current = playMode;
  const intervalBaseRef = useRef(intervalBase); intervalBaseRef.current = intervalBase;
  const speedRef = useRef(speed); speedRef.current = speed;
  /**
   * One generation for the whole playback schedule. Every context change that must not be resumed by an
   * old timer — seek, base, speed, mode, Episode, window, page-size, unmount — bumps it, and the timer's
   * callback compares it before doing anything. The browser's monotonic clock is used only to execute a
   * wait and to measure what actually happened; it never stands in for recorded time.
   */
  const playGen = useRef(0);
  const presentedAt = useRef(0);
  const frozenSince = useRef(0);
  const censusSerial = useRef(0);
  const heldSerial = useRef(0);
  const heldReadInFlight = useRef(false);
  const heldArmedAt = useRef(0);

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

  const readPage = useCallback((offset: number, size: number, ctx: FrameReadContext, opts: { advancedFromHasMore?: boolean; landOn?: 'first' | 'last'; notice?: string; keepPlaying?: boolean } = {}) => {
    if (!episodeId) return;
    const target: FrameTarget = { episodeId, runId };
    const token = ++pageSerial.current;
    // A new read is a new playback baseline: any timer armed before this point is stale, and the held
    // page (if one was being waited on) belongs to the generation that no longer exists.
    ++playGen.current; setHeld(null); heldReadInFlight.current = false; frozenSince.current = 0; presentedAt.current = performance.now();
    controllers.current.forEach((controller) => controller.abort()); controllers.current = [];
    setError(''); setNotice(opts.notice ?? ''); if (!opts.keepPlaying) setPlaying(false); clearMedia();
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
        bindFrame(dto.frames[position] ?? null, position, { offset: dto.paging.offset });
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
    // Another Episode is another playback session: the census read for the old one is dropped rather than
    // reused, and this session's own counter starts again at zero.
    setCensus(null); setCensusStatus('idle'); setCensusError(''); setCensusReads(0);
    setHeld(null); setPlan(null); heldReadInFlight.current = false; frozenSince.current = 0;
    ++playGen.current; ++censusSerial.current; ++heldSerial.current;
    clearMedia();
    if (!episodeId) { ++pageSerial.current; setPage(null); return; }
    readPage(0, limitRef.current, NO_FRAME_CONTEXT);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [episodeId, runId]);
  useEffect(() => () => { controllers.current.forEach((controller) => controller.abort()); controllers.current = []; revoke(urlRef.current); }, []);

  /** Image, linked state, provenance and the reference surface all follow this one position on this page. */
  function bindFrame(frame: FrameDto | null, position?: number, opts: { offset?: number; field?: string | null } = {}) {
    if (!frame) { clearMedia(); return; }
    const key = framePositionKey(episodeId, runId, opts.offset ?? page?.paging.offset ?? 0, position ?? index, frame);
    void loadFrameMedia(frame, key, opts.field ?? null);
  }

  function loadFrameMedia(frame: FrameDto, key: string, explicitField: string | null) {
    const target: FrameTarget = { episodeId, runId };
    const refs = frameMediaRefs(frame);
    const ref = explicitField ? refs.find((item) => item.field === explicitField) ?? null : frameAutoLoadRef(refs);
    const token = ++assetSerial.current;
    frameKeyRef.current = key;
    revoke(urlRef.current); urlRef.current = null;
    if (!ref) {
      setAsset({ ...NO_FRAME_ASSET, token, sampleId: frame.sample_id, positionKey: key, field: explicitField ?? '', uri: '', availability: refs.length ? 'not_present' : 'no_items', status: 'not-loaded',
        note: refs.length ? '该帧的引用里没有可按原样读取的 rgb 引用，或所选字段不可读：不显示任何图像，也不保留上一帧的图片冒充当前帧。' : '本帧 media.items 为空：reader 没有给出可读取的引用，界面不按 sample_id 猜文件名。' });
      return;
    }
    if (!ref.loadable) {
      setAsset({ ...NO_FRAME_ASSET, token, sampleId: frame.sample_id, positionKey: key, field: ref.field, uri: ref.uri, availability: ref.availability, status: 'not-loaded', declaredSha: ref.declaredSha256, declaredBytes: ref.declaredBytes, agreesWithRow: ref.agreesWithRow, note: ref.note });
      return;
    }
    setAsset({ ...NO_FRAME_ASSET, token, sampleId: frame.sample_id, positionKey: key, field: ref.field, uri: ref.uri, availability: ref.availability, status: 'loading', declaredSha: ref.declaredSha256, declaredBytes: ref.declaredBytes, agreesWithRow: ref.agreesWithRow, note: ref.note });
    void api.asset(target.episodeId, target.runId, ref.uri, ref.declaredSha256, track(new AbortController()).signal)
      .then((value) => {
        if (token !== assetSerial.current || frameKeyRef.current !== key) return;
        if (target.episodeId !== targetRef.current.episodeId || target.runId !== targetRef.current.runId) return;
        const inline = value.mediaType.startsWith('image/');
        const url = inline ? URL.createObjectURL(new Blob([value.bytes], { type: value.mediaType })) : null;
        urlRef.current = url;
        setAsset({
          token, sampleId: frame.sample_id, positionKey: key, field: ref.field, uri: ref.uri, availability: ref.availability, status: 'bytes', url,
          mediaType: value.mediaType, bytes: value.bytes.byteLength, sha: value.assetSha256, declaredSha: ref.declaredSha256,
          declaredBytes: ref.declaredBytes, agreesWithRow: ref.agreesWithRow, note: ref.note,
          error: inline ? '' : `${value.mediaType || '未知类型'} 不能内联显示：本切片只按字节读取并显示服务端重算摘要，不做 NumPy 数值解码、不生成图像，也不画点云。`,
          decoded: inline ? 'unknown' : 'failed',
        });
      })
      .catch((cause) => {
        if (token !== assetSerial.current || frameKeyRef.current !== key) return;
        setAsset({ ...NO_FRAME_ASSET, token, sampleId: frame.sample_id, positionKey: key, field: ref.field, uri: ref.uri, availability: ref.availability, status: 'failed', error: describeHistoryError(cause), declaredSha: ref.declaredSha256, declaredBytes: ref.declaredBytes, agreesWithRow: ref.agreesWithRow, note: ref.note });
      });
  }

  const step = (delta: number) => {
    // Any manual move is a new scheduling baseline: what was armed before it may not fire, and time spent
    // paused or seeking is never added to the next wait.
    ++playGen.current; setHeld(null); frozenSince.current = 0; presentedAt.current = performance.now();
    if (!page) return;
    const frames = page.frames;
    if (!frames.length) { setPlaying(false); setNotice(framePageExplanation(page, contextRef.current)); return; }
    const next = index + delta;
    if (next >= 0 && next < frames.length) { const frame = frames[next]; setIndex(next); bindFrame(frame, next, { offset: page.paging.offset }); return; }
    const ctx = contextRef.current;
    if (next >= frames.length && page.paging.has_more) {
      // v2 keeps next_offset in the anchor file's own line space and re-tests every condition from there.
      // Crossing into the next page keeps playback running when the advance itself came from playback: the
      // reader's own next_offset is the only way forward, and no page is skipped or invented. A missing
      // next_offset therefore stops the walk instead of letting the interface guess an offset for a file
      // whose layout it was never told.
      if (page.paging.next_offset === null) {
        setPlaying(false);
        setNotice(`has_more=true 但响应没有给 next_offset（offset=${String(page.paging.offset)}、returned=${String(page.paging.returned)}）：界面不自行推算下一页位置，停在这里。`);
        return;
      }
      readPage(page.paging.next_offset, limitRef.current, ctx, { advancedFromHasMore: true, keepPlaying: playingRef.current });
      return;
    }
    if (next >= frames.length) { setPlaying(false); setNotice(`本页最后一帧之后服务端 has_more=${String(page.paging.has_more)}（whole_file_scanned=${String(page.paging.scan?.whole_file_scanned)}）：界面停止推进。这只说明本次读取到此为止，不推断录制结束，也不声称已遍历全部帧。`); return; }
    if (page.paging.offset > 0) {
      readPage(Math.max(0, page.paging.offset - limitRef.current), limitRef.current, ctx, { landOn: 'last', notice: '回到上一页的最后一帧（offset 由服务端分页决定；窗口与筛选条件保持不变）。' });
      return;
    }
    setNotice('已到本次读取的起点（offset=0）：不向前伪造帧，也不循环到最后一页。');
  };

  // ---- recorded-interval scheduling (the reader's mode B) ------------------------------------------

  /** The census belongs to one source/run/episode/anchor-stream session, not to one page or one window. */
  // Keyed on the page's own identity rather than the caller's local run value: a frame opened without a run_id
  // still belongs to one readable Episode, and the adoption guard below compares against that same identity.
  const sessionKey = timeQualitySessionKey({ sourceId: page?.source?.source_id, runId: page?.identity.run_id ?? runId, episodeId: page?.identity.episode_id ?? episodeId, streamId: page?.anchor?.stream_id ?? null });
  const censusPage = census && census.key === sessionKey ? census.page : null;
  const intervalGate = intervalGateOf(censusPage, intervalBase);
  const schedule = intervalScheduleOf(page, intervalBase, speed);
  const range = recordedRangeOf(page, intervalBase, censusPage);

  /** One on-demand census read: a normal frame page never carries it, and it is not a content-versioned cache. */
  const readCensus = () => {
    if (!episodeId) return;
    const target: FrameTarget = { episodeId, runId };
    const token = ++censusSerial.current;
    setCensusStatus('loading'); setCensusError('');
    void readFramesPage({ episodeId, runId, limit: 1, offset: 0, includeTimeQuality: true }, track(new AbortController()).signal)
      .then((dto) => {
        if (token !== censusSerial.current) return;
        if (dto.identity.episode_id !== target.episodeId || (target.runId !== null && dto.identity.run_id !== target.runId)) {
          // Refusing is a finished state, not a pending one: leaving this at 'loading' would disable the only
          // button that could retry and leave the operator with no explanation.
          setCensusStatus('refused');
          setCensusError(`census 的响应身份与本会话要看的 Episode 不符（响应 ${dto.identity.episode_id}/${dto.identity.run_id}，本会话 ${target.episodeId}/${target.runId ?? '未带 run_id'}）：不采用别人的资格，也不自动重试。`);
          return;
        }
        setCensusReads((previous) => previous + 1);
        setCensus({ page: dto, key: timeQualitySessionKey({ sourceId: dto.source.source_id, runId: dto.identity.run_id, episodeId: dto.identity.episode_id, streamId: dto.anchor.stream_id }) });
        setCensusStatus('ready');
      })
      .catch((cause) => {
        if (token !== censusSerial.current) return;
        setCensusStatus('refused'); setCensusError(describeHistoryError(cause));
      });
  };

  /** The next page is read ahead of time and then held back until its own recorded interval has elapsed. */
  const readAhead = () => {
    if (!page) return;
    const frames = page.frames;
    const fromFrame = frames[frames.length - 1];
    if (!fromFrame || heldReadInFlight.current) return;
    const target: FrameTarget = { episodeId, runId };
    const token = ++heldSerial.current;
    const gen = playGen.current;
    // Only the reader's own forward offset may carry the walk into the next page. Computing `offset + returned`
    // here would be the interface inventing a position in a file it has not been told the layout of.
    const offset = page.paging.next_offset;
    if (offset === null) {
      setPlaying(false);
      setNotice(`本页之后 has_more=${String(page.paging.has_more)}，但响应没有给 next_offset：界面不用 offset+returned 自行推算下一页，停在这里。`);
      return;
    }
    heldReadInFlight.current = true;
    heldArmedAt.current = performance.now();
    void readFramesPage({
      episodeId, runId, limit: limitRef.current, offset,
      ...(contextRef.current.sampleId ? { sampleId: contextRef.current.sampleId } : {}),
      ...(contextRef.current.base ? { timeBase: contextRef.current.base, ...(contextRef.current.from !== null ? { timeFrom: contextRef.current.from } : {}), ...(contextRef.current.to !== null ? { timeTo: contextRef.current.to } : {})} : {}),
    }, track(new AbortController()).signal)
      .then((dto) => {
        heldReadInFlight.current = false;
        if (token !== heldSerial.current || gen !== playGen.current) return;
        if (dto.identity.episode_id !== target.episodeId) {
          setPlaying(false); setError(`跨页预读到的页不属于本 Episode（响应身份 ${dto.identity.episode_id}）：不呈现、不采用。`); return;
        }
        if (!dto.frames.length) {
          // An empty page after has_more=true is a real answer from the reader; saying nothing here would leave
          // the interface looking like it is still playing with nothing armed.
          setPlaying(false); setNotice(frameStopNote(dto, contextRef.current, true)); return;
        }
        setHeld({ page: dto, armedAt: heldArmedAt.current,
          step: intervalStepOf({ from: fromFrame, to: dto.frames[0], base: intervalBaseRef.current, speed: speedRef.current, crossPage: true, fromPosition: frames.length - 1, toPosition: 0 }) });
      })
      .catch((cause) => {
        heldReadInFlight.current = false;
        if (token !== heldSerial.current || gen !== playGen.current) return;
        setPlaying(false); setError(`跨页预读失败：${describeHistoryError(cause)}（停在当前帧，不跳过、不伪造下一页）。`);
      });
  };

  /** Land one frame and report the three timings apart: planned interval, actual presentation, buffering. */
  const landFrame = (position: number, source: FramePageDto, planned: IntervalStep | null) => {
    const actualMs = Math.round(performance.now() - presentedAt.current);
    const bufferMs = frozenSince.current ? Math.round(performance.now() - frozenSince.current) : null;
    ++playGen.current;
    frozenSince.current = 0;
    presentedAt.current = performance.now();
    if (source !== page) setPage(source);
    setIndex(position);
    bindFrame(source.frames[position] ?? null, position, { offset: source.paging.offset });
    setPlan({ kind: planned?.kind ?? 'unknown', plannedMs: planned?.waitMs ?? null, actualMs, bufferMs,
      gapS: planned?.gapS ?? null, cross: planned?.crossPage ?? false, note: planned?.note ?? '' });
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

  /** Mode A — the interface rhythm. It only ever runs while that mode is the one the operator chose. */
  useEffect(() => {
    if (!playing || !page || playMode !== 'ui_cadence') return;
    const gen = playGen.current;
    const timer = setTimeout(() => { if (gen === playGen.current) step(1); }, Math.round(1000 / cadenceFps));
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, cadenceFps, page, index, playMode]);

  /**
   * Mode B — one step per real recorded gap on the chosen base, divided by the speed. The plan is armed
   * again from scratch whenever it is (re)started, so a pause never leaves accumulated record progress
   * behind, and every armed callback checks the playback generation before touching the cursor.
   */
  useEffect(() => {
    if (!playing || !page || playMode !== 'recorded_interval') return;
    if (!intervalBase) {
      setPlaying(false);
      setNotice('记录间隔模式还没有选定时间基：界面不替你挑一个基，也不静默退回帧节奏模式——模式由你显式选择。');
      return;
    }
    if (!censusPage) {
      setPlaying(false);
      setNotice(intervalGate.reasons[0] ?? '没有读到 census 就不排程：请先显式读取一次本 Episode 的时间资格。');
      return;
    }
    if (!intervalGate.allowed) {
      setPlaying(false);
      setPlan({ kind: 'refused', plannedMs: null, actualMs: null, bufferMs: null, gapS: null, cross: false, note: intervalGate.reasons[0] ?? '' });
      setNotice(`记录间隔调度不可用：${intervalGate.reasons[0]} 帧节奏模式仍然可用，但界面不自动切过去。`);
      return;
    }
    if (asset.status === 'loading') {
      if (!frozenSince.current) frozenSince.current = performance.now();
      // The elapsed buffer has to keep growing while the operator is watching a frozen cursor: without this
      // tick the chip would stay at the first sample (0 ms) and a 900 ms stall on slow bytes would be
      // displayed as though nothing was buffering at all.
      const showFreeze = () => setPlan((previous) => ({ kind: 'buffering', plannedMs: previous?.plannedMs ?? null, actualMs: previous?.actualMs ?? null,
        bufferMs: Math.round(performance.now() - frozenSince.current), gapS: previous?.gapS ?? null, cross: previous?.cross ?? false, note: previous?.note ?? '' }));
      showFreeze();
      const ticker = setInterval(showFreeze, 100);
      return () => clearInterval(ticker);
    }
    // Coming out of buffering rebuilds the scheduling baseline. The held cross-page step is the one wait measured
    // from when its page was issued rather than from a landing, so without this it would keep elapsing while the
    // operator watched a buffer and would present a slow client as if the record had advanced. `presentedAt`
    // deliberately does not move: the reported actual presentation time must still include the buffering.
    const resumedFromBuffer = frozenSince.current !== 0;
    frozenSince.current = 0;
    if (resumedFromBuffer && held) { setHeld({ ...held, armedAt: performance.now() }); return; }
    const frames = page.frames;
    const nextStep = index + 1 < frames.length ? schedule[index] ?? null : null;
    if (nextStep) {
      if (nextStep.kind === 'backwards' || nextStep.kind === 'missing') {
        setPlaying(false);
        setPlan({ kind: nextStep.kind, plannedMs: null, actualMs: null, bufferMs: null, gapS: nextStep.gapS, cross: nextStep.crossPage, note: nextStep.note });
        setNotice(`这一段不排程：${nextStep.note} 界面停在当前帧——不跳帧、不重排、不用别的钟补齐这一段。`);
        return;
      }
      const gen = playGen.current;
      const timer = setTimeout(() => { if (gen === playGen.current) landFrame(nextStep.toPosition, page, nextStep); }, Math.max(0, Math.round(nextStep.waitMs ?? 0)));
      return () => clearTimeout(timer);
    }
    if (held) {
      if (held.step.kind === 'backwards' || held.step.kind === 'missing') {
        setPlaying(false);
        setPlan({ kind: held.step.kind, plannedMs: null, actualMs: null, bufferMs: null, gapS: held.step.gapS, cross: held.step.crossPage, note: held.step.note });
        setNotice(`跨页那一步的真实间隔不可用：${held.step.note} 已读到的下一页保持不呈现，界面不重排也不丢弃记录顺序。`);
        return;
      }
      const remaining = Math.max(0, Math.round((held.step.waitMs ?? 0) - (performance.now() - held.armedAt)));
      const gen = playGen.current;
      const timer = setTimeout(() => {
        if (gen !== playGen.current) return;
        setHeld(null);
        landFrame(0, held.page, held.step);
      }, remaining);
      return () => clearTimeout(timer);
    }
    if (page.paging.has_more) { readAhead(); return; }
    setPlaying(false);
    setNotice(`本页之后 has_more=${String(page.paging.has_more)}（whole_file_scanned=${String(page.paging.scan?.whole_file_scanned)}）：记录间隔播放在此停止。不循环、不伪造后续帧，也不声称已遍历完整归档。`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, page, index, playMode, intervalBase, speed, asset.status, held, censusPage]);

  const frames = page?.frames ?? [];
  const frame = frames[index] ?? null;
  const cadenceMs = Math.round(1000 / cadenceFps);
  const curve = frameActualCurveOf(page, curveX);
  const xAxes = curveXAxesOf(page);
  const buffering = asset.status === 'loading';
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
  // One anchor identity, echoed by every history consumer: state, time, media, curve and 3D all answer for
  // the same concrete anchor (page offset + page position + the anchor's own line_index), not just a sample_id
  // that a page may repeat.
  const cursorAnchor = anchorEchoKey(paged?.offset ?? 0, index, frame);
  const episodeScopeLabel = range.episodeScope === 'proven' ? '整个 Episode（census 已扫完整份锚点文件）'
    : range.episodeScope === 'scan-only' ? '本次扫描范围（coverage 未覆盖整份锚点文件，界面不把它称作整个 Episode 的跨度）'
      : '整段范围未知（没有该基的 census 行，不猜）';
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
          onClick={() => {
            if (playing) { ++playGen.current; setHeld(null); frozenSince.current = 0; setPlaying(false); setNotice('已暂停：停在当前帧。恢复时按同一个记录间隔重新起算等待，暂停期间不累计记录进度。'); return; }
            if (playMode === 'recorded_interval' && !intervalGate.allowed) { setNotice(`不能开始记录间隔播放：${intervalGate.reasons[0] ?? '还没选定合格的时间基并读到 census'}。可以显式改用帧节奏模式，界面不自动切换。`); return; }
            ++playGen.current; heldReadInFlight.current = false; frozenSince.current = 0; presentedAt.current = performance.now();
            setPlaying(true);
            setNotice(playMode === 'recorded_interval'
              ? `记录间隔播放开始：下一步等待＝相邻锚点在 ${intervalBase} 上的真实差 ÷ ${speed}×；数据未就绪时冻结并显示缓冲，到页末按 reader 的 next_offset 预读下一页、再按跨页两帧的真实间隔呈现首帧。不发命令、不推进物理，也不宣称跨流同步。`
              : '播放只按界面节奏在本页已读取的帧上前进（到页末按 next_offset 继续）；不发命令、不推进物理，也不宣称录制帧率或跨流同步。');
          }}>{playing ? '⏸ 暂停' : '▶ 播放'}</button>
        <button data-frame-prev onClick={() => step(-1)}>◀ 上一帧</button>
        <button data-frame-next onClick={() => step(1)}>下一帧 ▶</button>
        <label>每页帧数<select aria-label="帧分页大小" value={limit} onChange={(event) => { const size = Number(event.target.value); setLimit(size); limitRef.current = size; readPage(0, size, contextRef.current, { notice: '改变每页帧数后从 offset=0 重读（保持 sample_id 与时间窗口条件）。' }); }}>{FRAME_PAGE_SIZES.map((size) => <option key={size} value={size}>{size}</option>)}</select></label>
        <label>播放模式<select aria-label="播放模式" data-frame-play-mode={playMode} value={playMode} onChange={(event) => { const mode = event.target.value as 'ui_cadence' | 'recorded_interval'; ++playGen.current; setHeld(null); frozenSince.current = 0; presentedAt.current = performance.now(); setPlaying(false); setPlan(null); setPlayMode(mode); setNotice(mode === 'recorded_interval' ? '已切到记录间隔模式：等待时间由相邻锚点在所选时间基上的真实差值除以倍速决定；先读本 Episode 的时间资格，再选一个合格的基。切换模式本身不自动开始播放。' : '已切到帧节奏模式：等待只是界面节奏（不称原速/真实倍速，也不等于录制帧率）。界面不会替你切回记录间隔模式。'); }}>
          <option value="ui_cadence">帧节奏（每秒展示 N 帧，界面节奏）</option>
          <option value="recorded_interval">记录间隔（按相邻锚点的真实时间差 ÷ 倍速）</option>
        </select></label>
        <label>播放节奏（每秒展示帧数）<select aria-label="播放节奏（每秒展示帧数，界面节奏）" value={cadenceFps} onChange={(event) => setCadenceFps(Number(event.target.value))}>{CADENCES.map((option) => <option key={option.fps} value={option.fps}>{option.label}</option>)}</select></label>
        <span className="chip masked" data-frame-playback-cadence-ui-only="true" data-frame-playback-not-realtime="true" data-frame-playback-rate-ms={String(cadenceMs)}>{playMode === 'ui_cadence' ? `每秒展示帧数只是界面推进节奏（${cadenceMs} ms/帧）：不称“原速/真实倍速”，也不等于录制帧率` : `帧节奏控件当前没有驱动播放（现在是记录间隔模式）：${cadenceMs} ms/帧只是这一模式的节奏值，界面不自动切回。`}</span>
        <span className="chip masked" data-time-quality-status={censusStatus} data-time-quality-reads={String(censusReads)} data-time-quality-session={sessionKey}>时间资格 census：{censusStatus === 'ready' ? `已读 ${censusReads} 次（本会话按 source|run|episode|stream 复用，普通帧页不携带）` : censusStatus === 'loading' ? '正在读取…' : censusStatus === 'refused' ? `读取失败：${censusError}` : '未读取（记录间隔模式需要它）'}</span>
        <button data-frame-read-census disabled={!episodeId || censusStatus === 'loading'} title="只发一次 GET …/frames?limit=1&offset=0&include_time_quality=true：census 描述整个 Episode 的锚点扫描，普通帧页不带它" onClick={() => readCensus()}>读取本 Episode 时间资格（一次）</button>
        <label>记录间隔时间基<select aria-label="记录间隔时间基" data-frame-interval-base={intervalBase || 'none'} value={intervalBase} onChange={(event) => { const base = event.target.value; ++playGen.current; setHeld(null); frozenSince.current = 0; presentedAt.current = performance.now(); setPlaying(false); setPlan(null); setIntervalBase(base); setNotice(`已选时间基 ${base || '（空）'}：${BASE_MEANING[base] ?? 'reader 未描述该基'}。换基不自动续播，旧定时器已作废。`); }}>
          <option value="">未选择（不代你挑基）</option>
          {Object.keys(censusPage?.time_quality?.time_bases ?? {}).map((base) => <option key={base} value={base}>{base}（{intervalGateOf(censusPage, base).allowed ? '整集合格' : '不合格：见下方原因'}）· {censusPage?.time_quality?.time_bases?.[base]?.clock ?? '—'}</option>)}
        </select></label>
        <label>记录间隔倍速<select aria-label="记录间隔倍速" data-frame-interval-speed={String(speed)} value={speed} onChange={(event) => { const value = Number(event.target.value); ++playGen.current; setHeld(null); frozenSince.current = 0; presentedAt.current = performance.now(); setSpeed(value); setNotice(`倍速改为 ${value}×：等待＝相邻锚点真实差 ÷ ${value}。改倍速不自动续播，旧的这一段作废。`); }}>{SPEEDS.map((value) => <option key={value} value={value}>{value}× 记录间隔（不是原速宣称）</option>)}</select></label>
        <span className="chip masked" data-frame-interval-allowed={String(intervalGate.allowed)} data-frame-interval-reasons={intervalGate.reasons.join(' | ') || 'none'}>{playMode !== 'recorded_interval' ? '当前由帧节奏模式驱动；记录间隔模式的资格判定见下，界面不自动切换' : intervalGate.allowed ? `记录间隔可用：${intervalBase} · ${intervalGate.unit} · ${intervalGate.clock}` : `记录间隔不可用：${intervalGate.reasons[0] ?? '还没选定时间基或没读到 census'}`}</span>
        <span className="chip masked" data-frame-plan-kind={plan?.kind ?? 'none'} data-frame-plan-planned-ms={text(plan?.plannedMs)} data-frame-plan-actual-ms={text(plan?.actualMs)} data-frame-plan-buffer-ms={text(plan?.bufferMs)} data-frame-plan-gap-s={text(round6(plan?.gapS))} data-frame-plan-cross={String(Boolean(plan?.cross))} data-frame-held-pending={String(Boolean(held))}>计划间隔 {text(plan?.plannedMs)} ms · 实际呈现 {text(plan?.actualMs)} ms · 缓冲 {text(plan?.bufferMs)} ms{held ? ' · 下一页已预读，按跨页真实间隔等待中' : ''}（浏览器单调钟只用于执行等待与测量，不替代记录时间；慢客户端不等于严格实时 1×）</span>
        <label>本页定位<select aria-label="本页帧定位" value={index} disabled={!frames.length} onChange={(event) => { const position = Number(event.target.value); const target = frames[position]; if (!target) return; ++playGen.current; setHeld(null); frozenSince.current = 0; presentedAt.current = performance.now(); setPlaying(false); setIndex(position); bindFrame(target, position); }}>{frames.map((item, position) => <option key={`${item.sample_id}-${position}`} value={position}>第 {position + 1}/{frames.length} 帧 · line {item.anchor.line_index} · {item.sample_id}</option>)}</select></label>
        <button data-frame-seek-first disabled={!frames.length} title="跳到本页第一帧（offset 由服务端分页决定，不跨页猜测）" onClick={() => { ++playGen.current; setHeld(null); frozenSince.current = 0; presentedAt.current = performance.now(); setPlaying(false); bindFrame(frames[0] ?? null, 0); setIndex(0); }}>本页首帧</button>
        <button data-frame-seek-last disabled={!frames.length} title="跳到本页最后一帧" onClick={() => { const last = frames.length - 1; ++playGen.current; setHeld(null); frozenSince.current = 0; presentedAt.current = performance.now(); setPlaying(false); bindFrame(frames[last] ?? null, last); setIndex(last); }}>本页末帧</button>
        <span className="chip masked" data-frame-seek-scope={String(frames.length)}>定位范围＝本页已读取的 {frames.length} 帧：响应不给总帧数，界面不显示总时长或全局进度百分比</span>
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

      <section className="session-fields frame-intervals" data-interval-pane="true"
        data-interval-mode={playMode} data-interval-base={intervalBase || 'none'} data-interval-unit={range.unit} data-interval-clock={intervalGate.clock} data-interval-coverage={`anchors_in_this_scan=${text(censusPage?.time_quality?.coverage?.anchors_in_this_scan)}／covers_whole_episode=${text(censusPage?.time_quality?.coverage?.covers_whole_episode)}／whole_anchor_file_scanned=${text(censusPage?.time_quality?.coverage?.whole_anchor_file_scanned)}／stopped_at_line_index=${text(censusPage?.time_quality?.coverage?.stopped_at_line_index)}`} data-interval-episode-scope={range.episodeScope}
        data-interval-speed={String(speed)} data-interval-allowed={String(intervalGate.allowed)}
        data-interval-eligible={text(intervalGate.eligibility?.eligible_for_whole_episode)}
        data-interval-scan-eligible={text(intervalGate.eligibility?.eligible_within_this_scan)}
        data-interval-blocking={JSON.stringify(intervalGate.eligibility?.blocking_reasons ?? [])}
        data-interval-page-first={text(range.pageFirst)} data-interval-page-last={text(range.pageLast)}
        data-interval-page-min={text(range.pageMin)} data-interval-page-max={text(range.pageMax)}
        data-interval-page-incomplete={String(range.pageIncomplete)}
        data-interval-episode-first={text(range.episodeFirst)} data-interval-episode-last={text(range.episodeLast)}
        data-interval-episode-min={text(range.episodeMin)} data-interval-episode-max={text(range.episodeMax)}
        data-interval-window={context.base ? `${text(range.windowFrom)}–${text(range.windowTo)}` : 'none'}
        data-interval-duplicates={text(censusPage?.time_quality?.identity?.duplicate_sample_id_groups)}
        data-interval-current-value={intervalBase ? text(frame?.anchor.clocks?.[intervalBase]) : 'no-base'}
        data-interval-steps={String(schedule.length)}
        data-interval-next-planned-ms={text(schedule[index]?.waitMs)}
        data-interval-total-forbidden="true">
        <h4>记录间隔与时间资格（census 描述的是整个 Episode 的锚点扫描）</h4>
        <p className="session-note" data-interval-mode-line={`模式＝${playMode === 'recorded_interval' ? '记录间隔（相邻锚点真实差 ÷ 倍速）' : '帧节奏（界面节奏，不称原速）'} · 时间基＝${intervalBase || '未选'} · 单位＝${range.unit} · 倍速＝${speed}× · 本帧记录值＝${text(frame?.anchor.clocks?.[intervalBase])} · 下一步计划等待＝${text(schedule[index]?.waitMs)} ms`}>
          当前模式＝<b>{playMode === 'recorded_interval' ? '记录间隔（相邻锚点真实差 ÷ 倍速）' : '帧节奏（界面节奏，不称原速）'}</b> · 时间基＝{intervalBase || '未选'} · 单位＝{range.unit}（来自 census 的 unit 与响应 time.units） · 倍速＝{speed}× · 本帧在该基上的记录值＝{text(frame?.anchor.clocks?.[intervalBase])} · 下一步计划等待＝{text(schedule[index]?.waitMs)} ms（本页 {schedule.length} 段）。这里不显示总时长、总帧数或全局进度：进度控件不为此下载全量帧。
        </p>
        <p className="session-note" data-interval-meaning={`capture＝采集时刻（${BASE_MEANING.capture_backend_monotonic_s}／${BASE_MEANING.capture_sim_time_s}）；persist＝${BASE_MEANING.persist_backend_monotonic_s}。三个钟含义分别标明，界面不把其中一个叫作另一个，也不合并成一个“真实时间”。等待只用相邻锚点的真实差值，不使用 profile 名（${censusPage?.time_quality?.profile?.profile_ids_seen?.join('、') || '未读'}）或名义帧率，median 只作 census 描述、绝不排程。`}>
          <b>capture / sim / persist 各自是什么</b>：{BASE_MEANING.capture_backend_monotonic_s}；{BASE_MEANING.capture_sim_time_s}；{BASE_MEANING.persist_backend_monotonic_s}。<b>按 persist 排的是写入节奏，不称为机器人运动原速</b>；等待也不使用 profile 名（如 {censusPage?.time_quality?.profile?.profile_ids_seen?.join('、') || '未读'}）或名义帧率，median 只作为 census 的描述值显示，绝不用于排程。
        </p>
        <p className="session-note" data-interval-episode-scope={range.episodeScope} data-interval-scopes={`本页首/末 ${text(range.pageFirst)}→${text(range.pageLast)} · 本页最小/最大 ${text(range.pageMin)}/${text(range.pageMax)} · 当前窗口 ${context.base ? `${text(range.windowFrom)}–${text(range.windowTo)}` : '未设（窗口只筛帧页）'} · ${episodeScopeLabel} 首/末 ${text(range.episodeFirst)}→${text(range.episodeLast)} · 最小/最大 ${text(range.episodeMin)}/${text(range.episodeMax)} · ${range.note}`}>
          <b>范围分开表达</b>：本页首/末 {text(range.pageFirst)}→{text(range.pageLast)}；本页最小/最大 {text(range.pageMin)}/{text(range.pageMax)}；当前窗口 {context.base ? `${text(range.windowFrom)}–${text(range.windowTo)}` : '未设'}（<b>窗口只筛帧页，census 仍描述整份锚点扫描</b>）；{episodeScopeLabel} 首/末 {text(range.episodeFirst)}→{text(range.episodeLast)}、最小/最大 {text(range.episodeMin)}/{text(range.episodeMax)}。{range.note}
          {range.pageIncomplete ? <b data-interval-incomplete="true"> 本页有帧缺该基的有限数值：这些段不排程、不补值、不借用别的基。</b> : null}
        </p>
        <table className="frame-record-table" data-interval-table="true"><thead><tr><th>段（本页位置）</th><th>line_index 对</th><th>记录值对</th><th>真实差（s）</th><th>÷ 倍速后等待（ms）</th><th>判定</th></tr></thead>
          <tbody>{schedule.map((step) => <tr key={`${step.fromPosition}-${step.toPosition}`} data-interval-row={String(step.fromPosition)} data-interval-row-kind={step.kind}
            data-interval-row-gap={text(round6(step.gapS))} data-interval-row-wait={text(step.waitMs)} data-interval-row-lines={`${frames[step.fromPosition]?.anchor.line_index ?? '—'}→${frames[step.toPosition]?.anchor.line_index ?? '—'}`}
            data-interval-row-values={`${text(round6(step.fromValue))}→${text(round6(step.toValue))}`} className={step.fromPosition === index ? 'selected' : ''}>
            <td>{step.fromPosition + 1}→{step.toPosition + 1}{step.crossPage ? '（跨页）' : ''}</td><td>{frames[step.fromPosition]?.anchor.line_index ?? '—'}→{frames[step.toPosition]?.anchor.line_index ?? '—'}</td>
            <td><code>{text(round6(step.fromValue))}→{text(round6(step.toValue))}</code></td><td>{text(round6(step.gapS))}</td><td>{text(step.waitMs)}</td>
            <td>{step.kind}<small>{step.note}</small></td></tr>)}</tbody></table>
        {held && <p className="session-note" data-interval-held={`${held.step.kind}|${text(round6(held.step.gapS))}|${text(held.step.waitMs)}`}>下一页已按 reader 的 next_offset 预读到（{held.page.frames.length} 帧）：跨页这一步用<b>上一页末帧与下一页首帧</b>在该基上的真实差 {text(held.step.gapS)}s ÷ {speed}× = {text(held.step.waitMs)} ms 呈现，界面停在当前帧等待，不跳帧也不提前显示。</p>}
        {intervalGate.reasons.length > 0 && <ul className="receipt-layers" data-interval-reasons="true">{intervalGate.reasons.map((reason, position) => <li key={`${position}-${reason.slice(0, 24)}`} data-interval-reason={String(position)}><b>不开放记录间隔播放</b> {reason}</li>)}</ul>}
        <ul className="receipt-layers" data-interval-disclosures="true">{intervalGate.disclosures.map((line, position) => <li key={`${position}-${line.slice(0, 24)}`} data-interval-disclosure={String(position)}>{line}</li>)}</ul>
        {!censusPage && <p className="session-note" data-interval-census-absent="true">本会话还没有 census：普通帧页不带 time_quality，所以记录间隔模式先禁用。点上面的按钮读取一次（按 source|run|episode|stream 在本会话内复用）；它不是有内容版本保证的持久缓存，换 Episode 就作废。</p>}
      </section>

      <div className="frame-grid">
        <section className="history-stream-pane" data-frame-list="true">
          <h4>本页帧与角色状态</h4>
          <div className="history-cursor" data-frame-index={index} data-frame-sample={frame?.sample_id ?? 'none'}
            data-frame-line={text(frame?.anchor.line_index)} data-frame-persist-seq={text(frame?.anchor.persist_sequence)}
            data-frame-linkage-status={frame?.linkage_status ?? 'none'} data-frame-primary-matched={(frame?.primary_roles_matched ?? []).join('|')}
            data-frame-primary-ambiguous={(frame?.primary_roles_ambiguous ?? []).join('|')} data-frame-ambiguous-count={String(ambiguous)}
            data-frame-declared-ref={frame?.declared_reference_status ?? 'none'} data-frame-state-status={text(frame?.state?.status)}
            data-frame-single-state={text(frame?.state?.single_state_selected)} data-frame-state-candidates={text(frame?.state?.candidate_records)}
            data-frame-cursor-selection={`${text(paged?.offset)}|${index}|${frame?.sample_id ?? 'none'}`}
            data-frame-cursor-position={String(index)}
            data-cursor-position-key={frame ? framePositionKey(episodeId, runId, paged?.offset ?? 0, index, frame) : 'none'}
            data-cursor-anchor={cursorAnchor}
            data-frame-cursor-pending={String(buffering)} data-frame-buffering={String(buffering)}
            data-cursor-selected-sample={frame?.sample_id ?? 'none'}
            data-cursor-recorded-value={intervalBase ? text(frame?.anchor.clocks?.[intervalBase]) : 'no-base'}
            data-cursor-recorded-base={intervalBase || 'none'}>
            当前：本页第 {frames.length ? index + 1 : 0}/{frames.length} 帧（不是全局序号）{buffering ? ' · 本帧媒体仍在读取/解码：显示缓冲，不拿上一帧的图像顶替' : ''}· line_index={text(frame?.anchor.line_index)} · persist_sequence={text(frame?.anchor.persist_sequence)} · linkage_status={text(frame?.linkage_status)} · primary_roles_matched=[{(frame?.primary_roles_matched ?? []).join(',') || '空'}] · primary_roles_ambiguous=[{(frame?.primary_roles_ambiguous ?? []).join(',') || '空'}] · declared_reference_status={text(frame?.declared_reference_status)} · state single={text(frame?.state?.single_state_selected)}/{text(frame?.state?.candidate_records)} 候选{intervalBase ? ` · 本帧记录值 ${intervalBase}=${text(frame?.anchor.clocks?.[intervalBase])} ${range.unit}` : ''}
          </div>
          <table className="frame-record-table"><thead><tr><th>line</th><th>persist_seq</th><th>sample_id</th><th>关联</th><th>feedback 引用</th><th>媒体 availability</th></tr></thead>
            <tbody>{frames.map((item, position) => <tr key={`${item.sample_id}-${item.anchor.line_index}`} data-frame-row={item.sample_id} className={position === index ? 'selected' : ''}
              data-row-line={String(item.anchor.line_index)} data-row-persist-seq={text(item.anchor.persist_sequence)} data-row-status={item.linkage_status}
              data-row-primary={(item.primary_roles_matched ?? []).join('|')} data-row-ambiguous={(item.primary_roles_ambiguous ?? []).join('|') || 'none'}
              data-row-declared-ref={item.declared_reference_status} data-row-identity={String(item.anchor.identity?.run_id_matches) + '/' + String(item.anchor.identity?.episode_id_matches)}
              data-row-single-state={text(item.state?.single_state_selected)} data-row-candidates={text(item.state?.candidate_records)}
              data-row-media={item.media.items.map((media) => `${media.field}:${media.availability}`).join('|')}>
              <td>{item.anchor.line_index}</td><td>{text(item.anchor.persist_sequence)}</td>
              <td><button data-frame-pick={item.sample_id} data-pick-position={String(position)} data-pick-line={String(item.anchor.line_index)} onClick={() => { ++playGen.current; setHeld(null); frozenSince.current = 0; presentedAt.current = performance.now(); setPlaying(false); setIndex(position); bindFrame(item, position); }}>{item.sample_id}</button></td>
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

        <section className="history-stream-pane" data-frame-state-pane="true" data-frame-displayed-sample={frame?.sample_id ?? 'none'} data-frame-displayed-anchor={cursorAnchor}>
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

        <section className="history-stream-pane" data-frame-time-pane="true" data-frame-displayed-sample={frame?.sample_id ?? 'none'} data-frame-displayed-anchor={cursorAnchor}>
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

        <section className="history-stream-pane" data-frame-media-pane="true" data-frame-displayed-sample={frame?.sample_id ?? 'none'} data-frame-displayed-anchor={cursorAnchor}>
          <h4>媒体（只按本帧 media.items 的引用读取）</h4>
          <p className="session-note" data-media-declaration={mediaDeclarationText(frame)}>{mediaDeclarationText(frame)}</p>
          {!refs.length && <p className="session-note" data-frame-media-none="true">{frame ? '本帧 media.items 没有引用：不显示图像，也不按 sample_id 拼文件名。' : '未绑定帧。'}</p>}
          {refs.map((ref) => <div key={`${ref.field}-${ref.uri}`} className="media-ref" data-frame-media-ref={ref.uri} data-media-field={ref.field} data-media-availability={ref.availability}
            data-media-declared-sha={ref.declaredSha256 ?? 'null'} data-media-declared-bytes={ref.declaredBytes} data-media-bytes-on-disk={ref.bytesOnDisk}
            data-media-agrees-with-row={ref.agreesWithRow} data-media-row-lines={ref.rowLines} data-media-row-candidates={ref.rowCandidates} data-media-rows-conflict={ref.rowsConflict}>
            <b>{ref.field} · {ref.kind}</b><span>{ref.uri}</span>
            <small>声明摘要：{ref.declaredSha256 ? shortOr(ref.declaredSha256) : 'null'}（来自观测行，记录声明而非本次重算）· 声明字节={ref.declaredBytes} · 磁盘字节={ref.bytesOnDisk} · 与观测行 uri 一致={ref.agreesWithRow}（候选 {ref.rowCandidates} 条，行 {ref.rowLines}，行间冲突={ref.rowsConflict}）</small>
            <small>{ref.note}</small>
            <button data-frame-media-pick={ref.field} disabled={!ref.loadable || (asset.status === 'loading' && asset.uri === ref.uri)} title={ref.loadable ? '按该引用读取字节' : '该引用不可读取，界面不绕过'} onClick={() => bindFrame(frame, index, { field: ref.field })}>按此引用读取</button>
          </div>)}
          {asset.uri || asset.status !== 'idle' ? <div className="asset-frame" data-frame-asset-sample={asset.sampleId} data-frame-asset-position-key={asset.positionKey} data-frame-asset-field={asset.field || '—'} data-frame-asset-uri={asset.uri || 'none'}
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

      <div className="session-inline" data-frame-curve-controls="true">
        <label>曲线横轴<select aria-label="曲线横轴" value={curveX} onChange={(event) => setCurveX(event.target.value)}>{xAxes.map((axis) => <option key={axis.key} value={axis.key}>{axis.label}</option>)}</select></label>
        <span className="chip masked" data-frame-curve-scope="true">曲线只用本页已读取的 {frames.length} 帧记录值；点曲线即定位当前帧，不发新请求、不下载整份归档</span>
      </div>
      <HistoryFrameCurve curve={curve} selectedPosition={index} selectedAnchor={cursorAnchor}
        onPick={(position) => { const target = frames[position]; if (!target) return; ++playGen.current; setHeld(null); frozenSince.current = 0; presentedAt.current = performance.now(); setPlaying(false); setIndex(position); bindFrame(target, position); }}/>

      <HistoryModelPane episodeId={episodeId} runId={runId} sampleId={frame?.sample_id ?? null}
        anchor={frame ? { position: index, lineIndex: frame.anchor.line_index, offset: paged?.offset ?? 0 } : null}/>

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
/** Record values are shown as the reader wrote them; only float noise in a derived difference is rounded. */
const round6 = (value: number | null | undefined) => typeof value === 'number' && Number.isFinite(value) ? Math.round(value * 1e6) / 1e6 : null;
const shortOr = (value: string | null | undefined) => !value ? 'null' : value.length > 20 ? `${value.slice(0, 16)}…` : value;
