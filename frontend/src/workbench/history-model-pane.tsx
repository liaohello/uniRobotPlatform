/**
 * The fixed model tree for one historical Episode: the placement tree that arrives inside this Episode's
 * own `robot-state` answer (frozen compiled bundle, opt-in via `include_model_tree`), the mesh bytes read
 * from the Episode's own history asset route, the per-capability `part_readiness`/`mapping` gate that
 * decides what a recorded value may move, and the attribution that says which frame the pixels belong to.
 *
 * Attribution is the point of this component: `sampleId` is what was asked for, `displayedSample` is
 * what is on screen. A frame step clears the posed state before the new read starts, so an in-flight
 * or refused read shows the compiled reference layout rather than the previous frame's pose under the
 * new frame's title. The tree, the camera and the layout survive a frame step — only robot-state is
 * re-read and only the parts the reader allowed are re-posed. The static tree is cached in memory by
 * content identity, so stepping frames asks for the pose alone; a missing, refused or mismatching tree
 * blocks, and the live scene route is never a fallback.
 *
 * Nothing here reads the live snapshot or Actual for historical content, applies a Target or Ghost,
 * synthesises a TCP orientation, or sends a command.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Icon } from './Icon';
import { describeHistoryError } from '../adapters/platform-episodes';
import { HistoryReferenceScene, type PoseAttribution, type ReferenceSelection } from '../viewport/history-reference-scene';
import {
  assertHistoryFrameIdentity, capabilitySummaryText, cachedTree, comparisonRowsOf, drivenValuesOf, fkCrossCheckOf,
  forgetTreeNamespace, historySceneManifestOf, historyTreeBindingRowsOf, historyTreeOf, historyTreeRefusal, linkBindingRowsOf, mappingRowsOf,
  mergeVisitedValues, modelResourceText, modelVsUserText, motionCoverageOf, notProvenText, partReadinessOf,
  poseBoundaryText, poseDriveOf, poseReadinessText, poseStateText, readHistoryModelAsset, readRobotState, rememberTree, renderingText,
  shouldRequestTree, versionBindingText, type HistoryModelTreeDto, type HistoryPoseDto, type TreeBindingRow, type VisitedDrivenValues,
} from '../adapters/platform-history-pose';

/**
 * The static tree arrives inside this Episode's own `robot-state` answer (`include_model_tree=true`), so
 * the history assembly has exactly one source. There is no fallback: a refused, absent or mismatching
 * tree blocks, and the live `/mobilecar/scene` route is never read for historical content.
 */
interface CachedTree { contentIdentity: string; tree: HistoryModelTreeDto }
/** One declared asset. The guard is not two copies of the same list: the tree's own mesh references say
 *  what must resolve, and the byte read carries the declared digest so the server re-computes it. */
interface AssetRow { assetId: string; sha: string; bytes: string; coordinateSpace: string; referenced: boolean;
  readState: 'idle' | 'reading' | 'ok' | 'failed'; readDetail: string }

/** Binding rows: the seven identity comparisons, the tree's own self-consistency, then the nodes. */
const bindingRowsOf = (pose: HistoryPoseDto | null, tree: HistoryModelTreeDto | null): TreeBindingRow[] => {
  const identity = historyTreeBindingRowsOf(pose, tree);
  if (!tree) return identity;
  const nodes = [...(tree.links ?? []), ...(tree.world_links ?? [])];
  return [...identity, ...linkBindingRowsOf(pose, nodes).map((row) => ({
    field: `link ${row.name} · ${row.field}`, history: row.history, tree: row.tree, equal: row.equal,
    note: '记录点名的 link/关节逐节点绑定：相同 mesh 摘要但接错父节点也在这里被拦下',
  }))];
};
const VIEWS = [
  { id: 'front' as const, label: '车头', title: '车头视图：world_sim +X，从车前方看' },
  { id: 'side' as const, label: '车侧', title: '车侧视图：world_sim −Y，从车右方看' },
  { id: 'top' as const, label: '顶视', title: '顶视图：world_sim +Z，从上方看' },
];

export function HistoryModelPane({ episodeId, runId, sampleId }: { episodeId: string; runId: string | null; sampleId: string | null }) {
  const [stage, setStage] = useState<{ status: string; reason: string }>({ status: 'idle', reason: '未选择帧：不读取 robot-state，也不装配模型。' });
  const [pose, setPose] = useState<HistoryPoseDto | null>(null);
  /** The static tree the pane draws: this Episode's own robot-state answer, keyed by source namespace
   *  and content identity so a late or foreign tree can never be used for the wrong Episode. */
  const [treeState, setTreeState] = useState<{ namespace: string; contentIdentity: string; tree: HistoryModelTreeDto } | null>(null);
  const [assets, setAssets] = useState<AssetRow[]>([]);
  const [selection, setSelection] = useState<ReferenceSelection | null>(null);
  const [notices, setNotices] = useState<string[]>([]);
  const [assetError, setAssetError] = useState('');
  const [inspected, setInspected] = useState('');
  /** Which frame the pixels on screen actually belong to — never inferred from `sampleId`. */
  const [displayed, setDisplayed] = useState<PoseAttribution | null>(null);
  /** Tree fetches this page session issued for the Episode now displayed: first frame or content change
   *  only. A cached Episode reports 0, because returning to it must not re-download static content. */
  const [treeReads, setTreeReads] = useState<{ count: number; episode: string }>({ count: 0, episode: '' });
  /** Bumped when a frame's content identity no longer matches the cached tree, so the next read asks for
   *  that tree again instead of drawing static content that belongs to other bytes. */
  const [treeReread, setTreeReread] = useState(0);
  /** The driven values of every frame this Episode has actually shown, kept only to judge cross-frame
   *  motion coverage. It says nothing about frames that were never read, and never fills an absent value. */
  const [visited, setVisited] = useState<{ key: string; rows: VisitedDrivenValues[] }>({ key: '', rows: [] });

  const host = useRef<HTMLDivElement | null>(null);
  const view = useRef<HistoryReferenceScene | null>(null);
  const assemblyKey = useRef('');
  const poseSerial = useRef(0);
  const poseControllers = useRef<AbortController[]>([]);
  const trackPose = (controller: AbortController) => { poseControllers.current.push(controller); return controller; };
  const releaseView = useCallback(() => { view.current?.dispose(); view.current = null; assemblyKey.current = ''; setSelection(null); setInspected(''); setDisplayed(null); }, []);

  // A frame step, an Episode switch or an unmount drops the older pose read and its model surface.
  useEffect(() => {
    const token = ++poseSerial.current;
    poseControllers.current.forEach((controller) => controller.abort()); poseControllers.current = [];
    setAssetError(''); setNotices([]);
    if (!episodeId || !sampleId) { setPose(null); setAssets([]); releaseView(); setStage({ status: 'idle', reason: '未选择帧：不读取 robot-state，也不装配模型。' }); return; }
    // The requested frame is not the displayed one yet: clear the previous frame's dynamic pose first,
    // so nothing from it can be shown under this frame's identity. The tree, camera and layout stay.
    setPose(null);
    view.current?.applyFramePose(null);
    setDisplayed(view.current?.attribution() ?? null);
    const namespace = `${episodeId}|${runId ?? ''}`;
    const needTree = shouldRequestTree(namespace);
    setStage({ status: 'reading', reason: `正在读取所选帧的 robot-state（sample_id=${sampleId}${needTree ? ' · 并取一次完整静态树' : ' · 静态树沿用按内容身份缓存的那份'}）；画面暂时回到编译初始布局，不使用上一帧的姿态。` });
    if (needTree) setTreeReads((previous) => ({ count: (previous.episode === episodeId ? previous.count : 0) + 1, episode: episodeId }));
    else setTreeReads((previous) => (previous.episode === episodeId ? previous : { count: 0, episode: episodeId }));
    void readRobotState({ episodeId, runId, sampleId, includeModelTree: needTree }, trackPose(new AbortController()).signal)
      .then((dto) => {
        if (token !== poseSerial.current) return;                      // a late pose never writes a newer frame
        assertHistoryFrameIdentity(dto, { episodeId, runId, sampleId });
        const identity = String(dto.model_resource?.content_identity_sha256 ?? '');
        if (needTree) {
          // The tree arrives with this answer only. Absent or refused leaves it null, and the assembly
          // blocks: nothing here ever reaches for the live scene route to keep drawing.
          const tree = historyTreeOf(dto);
          if (tree && identity) {
            rememberTree(namespace, identity, tree);
            setTreeState({ namespace, contentIdentity: identity, tree });
          } else {
            forgetTreeNamespace(namespace);
            setTreeState(null);
          }
        } else if (cachedTree(namespace)?.contentIdentity !== identity) {
          // Content moved under this source: drop what it pointed at and ask again on the next read.
          forgetTreeNamespace(namespace);
          setTreeState(null);
          setTreeReread((previous) => previous + 1);
        } else {
          const cached = cachedTree(namespace);
          setTreeState(cached ? { namespace, contentIdentity: identity, tree: cached.tree } : null);
        }
        setPose(dto);
      })
      .catch((cause) => {
        if (token !== poseSerial.current) return;
        setPose(null);
        view.current?.applyFramePose(null);                            // a refused read shows no pose at all
        setDisplayed(view.current?.attribution() ?? null);
        setStage({ status: 'failed', reason: `robot-state 读取失败：${describeHistoryError(cause)}；画面回到编译初始布局，不沿用任何上一帧姿态。` });
      });
    return () => { poseControllers.current.forEach((controller) => controller.abort()); poseControllers.current = []; };
    // `treeReread` re-enters this effect only when a frame's own content identity moved away from the
    // cached tree: the cache entry was dropped, so this pass asks for that tree again.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [episodeId, runId, sampleId, treeReread]);

  // Everything is drawn from one source now: the record, plus the tree that arrived inside that same
  // answer. Model identity first, then the tree's own content identity/counts/references, then the
  // nodes the record names one by one — a missing or refused tree blocks instead of reaching elsewhere.
  useEffect(() => {
    if (!pose) return;
    const key = `${episodeId}|${runId ?? ''}`;
    const tree = treeState && treeState.namespace === key ? treeState.tree : null;
    if (!tree) {
      setStage({ status: 'blocked', reason: `没有可用的历史静态树：${historyTreeRefusal(pose)}。不装配参考视图，也不改读在线的 /api/v1/mobilecar/scene 或 snapshot 作替代。` });
      releaseView(); return;
    }
    const comparison = comparisonRowsOf(pose);
    const unequal = comparison.filter((row) => row.equal !== 'true');
    if (pose.model_resource?.status !== 'match' || unequal.length) {
      setStage({ status: 'blocked', reason: `模型身份不符：model_resource.status=${String(pose.model_resource?.status)}，比较不等的字段 ${unequal.map((row) => row.key).join('/') || '无'}。不装配参考视图，也不把在线几何当作历史资源。` });
      releaseView(); return;
    }
    const manifest = historySceneManifestOf(pose, tree, episodeId, runId);
    const referenced = new Set(manifest.mesh_assets.map((asset) => asset.asset_id));
    const rows: AssetRow[] = (pose.model_resource?.assets ?? []).map((asset) => ({
      assetId: asset.asset_id, sha: asset.sha256, bytes: String(asset.bytes ?? 'null'),
      coordinateSpace: asset.coordinate_space ?? '未声明', referenced: referenced.has(asset.asset_id),
      readState: 'idle' as const, readDetail: '',
    }));
    setAssets(rows);
    const binding = bindingRowsOf(pose, tree);
    const unbound = binding.filter((row) => row.equal !== 'true');
    if (unbound.length) {
      setStage({ status: 'blocked', reason: `静态树与记录的内容身份不一致：${unbound.map((row) => `${row.field}（记录=${row.history} / 树=${row.tree}）`).join('、')}。相同 mesh 摘要但不同树内容也在这里被拦下：不装配，也不退回在线 Actual。` });
      releaseView(); return;
    }
    if (!host.current) { setStage({ status: 'blocked', reason: '装配容器尚未可用：不渲染任何模型。' }); return; }
    // The manifest only rebuilds when the Episode (that is, the history asset namespace) changed.
    if (assemblyKey.current !== key || !view.current) {
      const scene = view.current ?? new HistoryReferenceScene(host.current, {
        onNotice: (notice) => setNotices((previous) => [...previous.slice(-4), notice]),
        onAssetError: (message) => setAssetError(message),
      });
      view.current = scene;
      scene.mount(host.current, setSelection);
      // Bytes come only from this Episode's history asset endpoint, with the declared digest attached so
      // the server re-computes and refuses before any byte leaves the process.
      scene.setManifest(manifest);
      assemblyKey.current = key;
    }
    // One pass per (tree, pose): the tree and camera stay, and only the parts the reader allowed for
    // THIS frame move.
    const scene = view.current;
    if (!scene) { setStage({ status: 'blocked', reason: '装配视图未能创建：不驱动任何部件，也不宣称已装配。' }); return; }
    const drive = poseDriveOf(pose);
    scene.applyFramePose({ sample: pose.frame.sample_id, joints: drive.joints, base: drive.base, tcp: drive.tcp });
    setDisplayed(scene.attribution());
    // Record what this visit actually moved, keyed by the Episode identity: coverage may only ever be
    // judged over frames that were read and attributed, never over the frames still sitting in the record.
    const applied: VisitedDrivenValues = {
      sample: pose.frame.sample_id,
      values: Object.fromEntries(drivenValuesOf(pose, { joints: drive.joints, baseApplied: Boolean(drive.base), tcpApplied: Boolean(drive.tcp) }).map((row) => [row.name, row.model])),
    };
    setVisited((previous) => ({ key, rows: mergeVisitedValues(previous.key === key ? previous.rows : [], applied) }));
    setStage({ status: 'ready', reason: `固定模型树已装配：放置树来自本 Episode 的 robot-state（include_model_tree），authority=${tree.authority ?? '未声明'} · live_native_scene_proxied=${String(tree.live_native_scene_proxied)}，${(tree.links ?? []).length} 条 link、${(tree.world_links ?? []).length} 条 world link（内容身份与记录一致；world_links 是编译参考布局，不是记录位姿），${manifest.mesh_assets.length}/${rows.length} 个资产被树引用并按声明摘要从历史端点读字节。屏幕姿态归属见“显示帧”。` });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pose, treeState]);

  useEffect(() => () => {
    poseControllers.current.forEach((controller) => controller.abort());
    releaseView();
  }, [releaseView]);

  const drive = poseDriveOf(pose);
  const rows = mappingRowsOf(pose);
  const partRows = partReadinessOf(pose);
  const fk = fkCrossCheckOf(pose);
  const namespace = `${episodeId}|${runId ?? ''}`;
  const cachedForThisSource = treeState && treeState.namespace === namespace ? treeState : null;
  const treeForBinding = cachedForThisSource?.tree ?? null;
  const binding = bindingRowsOf(pose, treeForBinding);
  const canRead = Boolean(episodeId) && Boolean(pose?.model_resource);
  const displayedSample = displayed?.displayedSample ?? '';
  const attributed = Boolean(displayedSample) && displayedSample === sampleId;
  // Readback of what is actually on screen, only when the screen is this frame's: a pending or refused
  // read has no rows, because the picture is the compiled layout and no recorded value moved it.
  const values = pose && attributed && displayed
    ? drivenValuesOf(pose, { joints: displayed.jointValues, baseApplied: Boolean(displayed.baseApplied), tcpApplied: Boolean(displayed.tcpApplied) })
    : [];
  const coverage = motionCoverageOf(visited.rows);

  /** One asset's bytes on demand: the reader re-computes the digest and 409s if the content changed. */
  function readOne(assetId: string) {
    const row = assets.find((item) => item.assetId === assetId);
    if (!row) return;
    const token = poseSerial.current;
    setAssets((previous) => previous.map((item) => item.assetId === assetId ? { ...item, readState: 'reading', readDetail: '正在按声明摘要读取字节…' } : item));
    void readHistoryModelAsset({ episodeId, runId, assetId, sha256: row.sha }, trackPose(new AbortController()).signal)
      .then((value) => {
        if (token !== poseSerial.current) return;                    // a late byte read never rewrites a new episode's table
        const matches = value.digest === row.sha;
        const detail = `${value.bytes.byteLength} 字节 · content-type=${value.mediaType || '未知'} · ETag ${value.etag || '无'} · cache-control=${value.cacheControl || '未声明'} · ${matches ? `服务端重算摘要与 bundle 声明一致（${value.digest.slice(0, 12)}）` : `摘要不符：服务端 ${value.digest.slice(0, 12) || '未在 ETag 里给出'} ≠ bundle ${row.sha.slice(0, 12)}`}`;
        setAssets((previous) => previous.map((item) => item.assetId === assetId ? { ...item, readState: matches ? 'ok' : 'failed', readDetail: detail } : item));
      })
      .catch((cause) => {
        if (token !== poseSerial.current) return;
        setAssets((previous) => previous.map((item) => item.assetId === assetId ? { ...item, readState: 'failed', readDetail: describeHistoryError(cause) } : item));
      });
  }

  return <section className="history-model-pane" data-model-pane="true" data-model-status={stage.status}
    data-model-episode={episodeId || 'none'} data-model-requested-sample={sampleId ?? 'none'}
    data-model-displayed-sample={displayedSample || 'none'} data-model-attribution={attributed ? 'matched' : sampleId ? 'pending' : 'no-frame'}
    data-reference-pose="compiled-initial-layout" data-model-live-poll="off"
    data-frame-pose-verified={String(attributed && Boolean(displayed?.dynamicApplied))}
    data-model-base-applied={String(Boolean(displayed?.baseApplied))} data-model-tcp-applied={String(Boolean(displayed?.tcpApplied))}
    data-model-joints-applied={String(displayed?.jointsApplied ?? 0)}
    data-model-root-height={String(displayed?.rootHeightWorldSimM ?? 'null')}
    data-model-compiled-root-height={String(displayed?.compiledRootHeightWorldSimM ?? 'null')}
    data-model-tree-reads={String(treeReads.count)} data-model-tree-read-episode={treeReads.episode || 'none'}
    data-motion-visited-frames={String(visited.rows.length)} data-motion-visited-key={visited.key || 'none'}
    data-model-tree-source={treeForBinding ? String(treeForBinding.authority ?? '未声明') : 'none'}
    data-model-tree-proxied={treeForBinding ? String(treeForBinding.live_native_scene_proxied) : 'unknown'}
    data-model-tree-content-identity={treeState?.contentIdentity || 'none'}
    data-model-tree-world-semantics={treeForBinding ? String(treeForBinding.semantics?.world_links ?? '未声明') : 'none'}
    data-model-tree-live-scene-fallback="none">
    <h3>固定模型树 · 按部件历史姿态 <small data-model-current-sample={displayedSample || '—'}>{displayedSample ? `显示帧 ${displayedSample}` : '编译初始布局'}</small></h3>
    <p className="session-note" data-model-attribution-line={`请求帧 ${sampleId ?? '无'} · 显示帧 ${displayedSample || '无（当前是编译初始布局）'}`}>
      请求帧 {sampleId ?? '无'} · 显示帧 {displayedSample || '无（画面上是编译初始布局）'}
      {sampleId && !attributed ? ' · 新帧的 robot-state 尚未读回：动态姿态已隐藏，不把上一帧的姿态标给这一帧，也不补 0。' : ''}</p>
    <div className="session-blocked history-model-banner" data-model-banner="true" role="note">
      <Icon name="info" size={15}/>
      <div><b>{attributed && displayed?.dynamicApplied ? '本帧历史姿态（按部件门控）；未驱动部分仍是固定参考' : '固定模型参考；本帧没有可归属的历史姿态'}</b>
        <p>三类内容分得很清楚：<b>静态参考</b>＝冻结 bundle 的编译初始布局；<b>本帧历史姿态</b>＝只有该能力的 <code>part_readiness</code> 被判为可用、对应 <code>mapping</code> 为 <code>verified</code>、且本帧真带值时才驱动（机械臂用 <code>arm_model_qpos_rad</code> 的模型弧度，不做用户零位换算；底盘按记录的世界位姿替换根 free joint，不再叠加初始根偏移；TCP 只画位置点，不合成朝向）；<b>未驱动部分</b>保持编译布局并逐条写明原因。0 是合法数值；没有跨帧运动覆盖证据就不宣称所有轴已验证，<code>writer_identified=false</code> 与非同步声明继续保留。</p></div>
    </div>
    <p className="session-note" data-model-stage={stage.reason}>{stage.reason}</p>
    <p className="session-note" data-model-axis-convention="world_sim：+X=车头，+Y=车左，+Z=上（mujocoRoot 绕 X 轴 −90° 映射到 Three 的 Z-up）；关节轴取 bundle 的 joint_axis（模型弧度），底盘读 base_link 的世界位姿，TCP 只画位置点，不画朝向帧">
      坐标与轴向：<b>world_sim</b> +X=车头、+Y=车左、+Z=上，长度 m、角度 rad；渲染根把 world_sim 映射为 Three 的 Z-up（绕 X 轴 −90°），模型根不为任何视图旋转。
      关节轴取 bundle 的 <code>joint_axis</code>（子体坐标系），底盘用 <code>base_link</code> 的世界位姿，<b>TCP 只画位置点，不画朝向帧</b>。</p>
    {assetError && <p className="session-error" data-model-asset-error="true">网格字节读取失败（历史端点）：{assetError}</p>}
    {notices.length > 0 && <p className="session-note" data-model-notices={notices.join(' | ')}>{notices.join(' | ')}</p>}

    <div className="model-grid">
      <div className="model-canvas" ref={host} data-model-canvas-host="true"></div>
      <div className="model-side">
        <p className="session-note" data-model-drive-summary={drive.summary}>{drive.summary}</p>
        <ul className="model-withheld" data-model-withheld-count={String(drive.withheld.length)}>
          {drive.withheld.map((line, index) => <li key={index} data-model-withheld={index}>{line}</li>)}
          {!drive.withheld.length && <li data-model-withheld-none="true">没有未驱动能力。</li>}
        </ul>
        <p className="session-note" data-model-values-note={`归属显示帧 ${displayedSample || '无'} · 已列 ${values.length} 行`}>
          本帧画面上真正施加的值（逐行对应被驱动的部件；未驱动的部件没有行）。<b>“绘制用的记录原值”就是移动关节/身体的那一份数</b>；
          用户角一栏由 reader 公式在本界面换算，只作对照，绘制路径从未使用它。</p>
        <table className="frame-record-table" data-model-values-table={attributed ? displayedSample || 'none' : 'no-frame'}>
          <thead><tr><th>部件／轴</th><th>绘制用的记录原值</th><th>仅展示：按 reader 公式的用户角</th><th>来源字段</th></tr></thead>
          <tbody>{values.map((row) => <tr key={`${row.kind}:${row.name}`} data-model-value={row.name} data-value-kind={row.kind}
            data-value-model={row.model} data-value-display={row.display} data-value-source={row.source}>
            <td>{row.name}<small>{row.kind}</small></td><td>{row.model}</td><td><small>{row.display}</small></td>
            <td><small>{row.source}</small></td></tr>)}
            {!values.length && <tr data-model-value-none="true"><td colSpan={4}>
              本帧没有可归属的已驱动值：画面是编译初始布局，或该帧的 robot-state 尚未读回／被 reader 拒绝。不从上一帧借值，也不补 0。</td></tr>}
          </tbody></table>
        <p className="session-note" data-motion-summary={`本会话在本 Episode 已归属 ${visited.rows.length} 个访问帧 · 被驱动过的项目 ${coverage.length} 项`}>
          跨帧运动覆盖（第四类说法，与“本帧输入完整”“同帧运动学一致”“硬件标定”互不推出）：只统计<b>本会话真读过并归属过的帧</b>，
          不推断整条记录、也不推断未访问的帧；只见过一个值的轴<b>没有运动覆盖证据</b>，界面不称它已验证。</p>
        <table className="frame-record-table" data-motion-table="true">
          <thead><tr><th>被驱动的部件／轴</th><th>每个不同记录值的来源帧</th><th>覆盖判定</th></tr></thead>
          <tbody>{coverage.map((row) => <tr key={row.name} data-motion-row={row.name} data-motion-distinct={String(row.distinct)} data-motion-visits={String(row.seenCount)}
            data-motion-samples={row.samples.join(',')}>
            <td>{row.name}</td><td><small>{row.samples.join(' / ')}</small></td><td><small>{row.verdict}</small></td></tr>)}
            {!coverage.length && <tr data-motion-none="true"><td colSpan={3}>
              还没有任何被归属的已驱动帧：不宣称任何轴有跨帧运动覆盖证据（装配本身不受影响）。</td></tr>}
          </tbody></table>
        <div className="session-inline">
          <button data-model-fit disabled={!view.current} onClick={() => view.current?.fitView()}>适应视图</button>
          {VIEWS.map((entry) => <button key={entry.id} data-model-view={entry.id} disabled={!view.current} title={entry.title}
            onClick={() => view.current?.standardView(entry.id)}>{entry.label}</button>)}
          <button data-model-inspect disabled={!view.current} onClick={() => setInspected(JSON.stringify(view.current?.inspect() ?? { error: '尚未装配视图' }))}>读取视图状态</button>
          <span className="chip masked" data-model-control-surface="none">历史面不挂 Target/Ghost/工具，也不轮询 live snapshot</span>
        </div>
        <p className="session-note" data-model-selection-link={selection?.linkName ?? 'none'}
          data-model-selection={selection ? `${selection.linkName} · ${selection.jointType} · ${selection.geoms.length} 个 geom` : '未选中部件'}>
          选择（只读）：{selection ? `${selection.linkName} · joint ${selection.jointName}(${selection.jointType}) · parent ${selection.parentName}` : '点选模型上的部件即可列出 link/geom；不拖拽、不产生 Target、不发命令。'}</p>
        {selection && <table className="frame-record-table" data-model-selection-table="true"><thead><tr><th>geom</th><th>类型</th><th>mesh asset</th></tr></thead>
          <tbody>{selection.geoms.map((geom) => <tr key={geom.name} data-model-geom={geom.name} data-geom-mesh={geom.meshAssetId}><td>{geom.name}</td><td>{geom.geomType}</td><td>{geom.meshAssetId}</td></tr>)}</tbody></table>}
        {inspected && <pre className="session-note" data-model-inspected={inspected}>{inspected}</pre>}
      </div>
    </div>

    {pose && <>
      <h4>按部件就绪（robot-state 的 part_readiness 原样）</h4>
      <p className="session-note" data-capability-summary={capabilitySummaryText(pose)}>{capabilitySummaryText(pose)}</p>
      <table className="frame-record-table" data-part-table="true">
        <thead><tr><th>能力</th><th>状态</th><th>该状态的含义</th><th>本帧输入</th><th>frontend_rule（界面必须遵守）</th><th>是否驱动</th></tr></thead>
        <tbody>{partRows.map((row) => {
          const decision = drive.parts.find((part) => part.capability === row.capability);
          return <tr key={row.capability} data-part-row={row.capability} data-part-status={row.status} data-part-drivable={String(Boolean(decision?.allowed))}>
            <td>{row.capability}<small>需要位姿输入={row.poseInput}；前置={row.requires}</small></td>
            <td><span className={row.status === 'ready' ? 'ok' : row.status === 'ready_with_caveats' ? 'unknown' : 'bad'}>{row.status}</span></td>
            <td><small>{row.meaning}</small></td>
            <td><small>{row.inputs}</small></td>
            <td><small>{row.rule}</small>{row.gaps !== '无' && <small>缺口：{row.gaps}</small>}</td>
            <td>{decision ? `${decision.allowed ? '驱动' : '不驱动'}：${decision.reason}` : '界面没有该能力的处理规则：不驱动。'}</td></tr>;
        })}</tbody></table>
      <p className="session-note" data-fk-check={fk ? `${fk.status} · verdict=${fk.verdict} · abs_error_m=${fk.absError} · 容差=${fk.tolerance} · ${fk.toleranceAuthority} · 支持约定=${fk.supported} · 记录 TCP=${fk.recorded} · 后端计算=${fk.computed} · 链=${fk.chain}` : 'reader 未返回 tcp_kinematic_cross_check'}>
        {fk ? `同帧运动学核对：${fk.method}` : 'reader 未返回 tcp_kinematic_cross_check'}</p>
      {fk && <table className="frame-record-table" data-fk-table="true"><thead><tr><th>根坐标约定</th><th>计算结果</th><th>误差 m</th><th>判定</th></tr></thead>
        <tbody>{fk.hypotheses.map((row) => <tr key={row.hypothesis} data-fk-row={row.hypothesis} data-fk-verdict={row.verdict}>
          <td>{row.hypothesis}<small>{row.status}</small></td><td>{row.computed}</td><td>{row.absError}</td><td>{row.verdict}</td></tr>)}</tbody></table>}
      <p className="session-note" data-model-vs-user={modelVsUserText(pose)}>{modelVsUserText(pose)}</p>
      <p className="session-note" data-version-binding={versionBindingText(pose)}>{versionBindingText(pose)}</p>
      <h4>映射行与姿态数值（原样，不换算）</h4>
      <p className="session-note" data-pose-readiness={poseReadinessText(pose)}>{poseReadinessText(pose)}</p>
      <p className="session-note" data-pose-rendering={renderingText(pose)}>{renderingText(pose)}</p>
      <p className="session-note" data-pose-state={poseStateText(pose)}>{poseStateText(pose)}</p>
      <table className="frame-record-table" data-mapping-table="true">
        <thead><tr><th>目标</th><th>记录字段／单位／长度</th><th>模型侧目标</th><th>状态</th><th>verified 依据与绘制来源</th><th>不补默认值</th></tr></thead>
        <tbody>{rows.map((row) => <tr key={row.target} data-mapping-row={row.target} data-mapping-status={row.status} data-mapping-no-default={row.noDefault}>
          <td>{row.target}</td>
          <td>{row.recordedField}<small>{row.recordedUnit} · 长度 {row.recordedLength}</small></td>
          <td>{row.targetField}</td>
          <td><span className={row.status === 'verified' ? 'ok' : row.status === 'partially_verified' ? 'unknown' : 'bad'}>{row.status}</span><small>{row.statusMeaning}</small></td>
          <td><small>{row.basis}</small><small>{row.drawSource} · {row.conversion}</small><small>{row.evidence}</small><small>{row.formula}</small></td>
          <td>{row.noDefault}</td></tr>)}</tbody></table>
      <p className="session-note" data-pose-gap-list={rows.map((row) => `${row.target}:${row.gap}`).join(' ｜ ')}>{rows.map((row) => `${row.target}:${row.gap}`).join(' ｜ ')}</p>
      <p className="session-note" data-pose-not-proven={notProvenText(pose)}>{notProvenText(pose)}</p>
      <p className="session-note" data-pose-boundary={poseBoundaryText(pose)}>{poseBoundaryText(pose)}</p>
      <h4>静态树与记录的内容身份绑定</h4>
      <table className="frame-record-table" data-tree-binding="true"><thead><tr><th>身份字段</th><th>历史记录</th><th>装配用的树</th><th>相等</th><th>说明</th></tr></thead>
        <tbody>{binding.map((row, index) => <tr key={`${row.field}#${index}`} data-tree-binding-row={row.field} data-tree-binding-equal={row.equal}>
          <td>{row.field}</td><td>{row.history}</td><td>{row.tree}</td><td>{row.equal}</td><td>{row.note}</td></tr>)}</tbody></table>
      <p className="session-note" data-tree-source-limit="true">静态树的唯一来源就是本 Episode 的 robot-state（`include_model_tree=true`，authority 与 live_native_scene_proxied 见上一行与本节说明）：历史装配不再读 {`/api/v1/mobilecar/scene`}，也不读 snapshot/Actual；树缺失、被拒或身份不符时界面阻塞而不是改读在线来源。world_links 只表示编译参考布局，不表示 target_cube 等对象在本 Episode 的历史位置。</p>
      <h4>历史模型资源身份</h4>
      <p className="session-note" data-model-resource={modelResourceText(pose)}>{modelResourceText(pose)}</p>
      <table className="frame-record-table" data-comparison-table="true"><thead><tr><th>身份字段</th><th>记录（run 清单）</th><th>冻结 bundle</th><th>相等</th></tr></thead>
        <tbody>{comparisonRowsOf(pose).map((row) => <tr key={row.key} data-comparison-row={row.key} data-comparison-equal={row.equal}>
          <td>{row.key}</td><td>{row.recorded}</td><td>{row.bundle}</td><td>{row.equal}</td></tr>)}</tbody></table>
      <table className="frame-record-table" data-asset-table="true"><thead><tr><th>asset_id</th><th>记录声明摘要</th><th>树是否引用</th><th>字节</th><th>单资产读取（服务端重算摘要）</th></tr></thead>
        <tbody>{assets.map((row) => <tr key={row.assetId} data-asset-row={row.assetId} data-asset-referenced={String(row.referenced)}
          data-asset-sha={row.sha} data-asset-read={row.readState} data-asset-detail={row.readDetail}>
          <td>{row.assetId}</td><td>{shortOr(row.sha)}</td><td>{String(row.referenced)}</td><td>{row.bytes}</td>
          <td><button data-asset-pick={row.assetId} disabled={!canRead || row.readState === 'reading'}
            title="只从历史资产端点按声明摘要读取；服务端先重算，摘要不符则 409 且不给字节"
            onClick={() => readOne(row.assetId)}>{row.readState === 'idle' ? '按摘要读取' : row.readState}</button>
            {row.readDetail && <small>{row.readDetail}</small>}</td></tr>)}</tbody></table>
      <p className="session-note" data-asset-referenced-count={String(assets.filter((row) => row.referenced).length)} data-asset-total={String(assets.length)}>
        {assets.filter((row) => row.referenced).length}/{assets.length} 个声明资产被静态树引用（未被引用的是模型里存在但没有网格几何的资产，如实列出、不要求全部被引用）；被引用的每一个都以声明摘要寻址，字节读取由服务端重算比对，摘要不符则不给内容。单资产一致不推出整条 Episode 完整，也不推出历史姿态可用。</p>
    </>}
    {!sampleId && <p className="session-note" data-model-none="true">未绑定帧：不请求 robot-state（省略 sample_id 时 reader 会返回它自己的第一条记录），因此不装配任何模型。</p>}
  </section>;
}

const shortOr = (value: string | null | undefined) => !value ? 'null' : value.length > 20 ? `${value.slice(0, 16)}…` : value;
