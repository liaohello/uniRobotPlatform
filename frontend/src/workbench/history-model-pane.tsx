/**
 * The fixed model tree for one historical Episode: the frozen geometry bundle's placement tree with
 * the mesh bytes read from the Episode's own history asset route, the per-capability
 * `part_readiness`/`mapping` gate that decides what a recorded value may move, and the attribution
 * that says which frame the pixels belong to.
 *
 * Attribution is the point of this component: `sampleId` is what was asked for, `displayedSample` is
 * what is on screen. A frame step clears the posed state before the new read starts, so an in-flight
 * or refused read shows the compiled reference layout rather than the previous frame's pose under the
 * new frame's title. The tree, the camera and the layout survive a frame step — only robot-state is
 * re-read and only the parts the reader allowed are re-posed.
 *
 * Nothing here reads the live snapshot or Actual for historical content, applies a Target or Ghost,
 * synthesises a TCP orientation, or sends a command.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Icon } from './Icon';
import { describeHistoryError } from '../adapters/platform-episodes';
import { HistoryReferenceScene, type PoseAttribution, type ReferenceSelection } from '../viewport/history-reference-scene';
import type { MeshAsset, SceneManifest } from '../adapters/types';
import {
  assertHistoryFrameIdentity, capabilitySummaryText, comparisonRowsOf, fkCrossCheckOf, mappingRowsOf, modelResourceText,
  modelVsUserText, notProvenText, partReadinessOf, poseBoundaryText, poseDriveOf, poseReadinessText, poseStateText,
  readHistoryModelAsset, readRobotState, renderingText, treeBindingRowsOf, versionBindingText, type HistoryPoseDto,
} from '../adapters/platform-history-pose';

/** The placement tree comes from the platform's own frozen geometry envelope. */
const GEOMETRY_PATH = '/api/v1/mobilecar/scene';
const GEOMETRY_SCHEMA = 'unirobot-mobilecar-geometry-2';
/** The bundle's own words for "compiled initial layout", which is what a reference pose may be. */
const GEOMETRY_SEMANTICS = 'compiled_initial_layout_not_live_object_state';

interface GeometryEnvelope {
  schema_version: string; read_only: boolean; world_pose_semantics: string;
  geometry_binding?: { bundle_sha256?: string; content_identity_sha256?: string; exported_runtime_identity?: Record<string, unknown> | null } | null;
  geometry_provenance?: { model_inputs_sha256?: string; compiled_scene_sha256?: string; resource_identity?: Record<string, unknown> | null } | null;
  data: SceneManifest;
}
interface AssetRow { assetId: string; bundleSha: string; historySha: string; equal: boolean; bytes: string; coordinateSpace: string;
  readState: 'idle' | 'reading' | 'ok' | 'failed'; readDetail: string }
/** What the tree the pane is about to draw says it is, so it can be bound to the record, not trusted.
 *  The arm hinges are picked out of the full link list by name pattern, in document order. */
const treeIdentityOf = (geometry: GeometryEnvelope | null) => (geometry ? {
  bundle_sha256: geometry.geometry_binding?.bundle_sha256 ?? null,
  content_identity_sha256: geometry.geometry_binding?.content_identity_sha256 ?? null,
  model_inputs_sha256: geometry.geometry_provenance?.model_inputs_sha256 ?? null,
  compiled_scene_sha256: geometry.geometry_provenance?.compiled_scene_sha256 ?? null,
  link_count: geometry.data.links?.length ?? null,
  world_link_count: geometry.data.world_links?.length ?? null,
  arm_hinge_joints: (geometry.data.links ?? []).filter((link) => link.joint_type === 'hinge' && /^joint\d$/.test(link.joint_name ?? '')).map((link) => link.joint_name ?? ''),
} : null);
const VIEWS = [
  { id: 'front' as const, label: '车头', title: '车头视图：world_sim +X，从车前方看' },
  { id: 'side' as const, label: '车侧', title: '车侧视图：world_sim −Y，从车右方看' },
  { id: 'top' as const, label: '顶视', title: '顶视图：world_sim +Z，从上方看' },
];

export function HistoryModelPane({ episodeId, runId, sampleId }: { episodeId: string; runId: string | null; sampleId: string | null }) {
  const [stage, setStage] = useState<{ status: string; reason: string }>({ status: 'idle', reason: '未选择帧：不读取 robot-state，也不装配模型。' });
  const [pose, setPose] = useState<HistoryPoseDto | null>(null);
  const [geometry, setGeometry] = useState<GeometryEnvelope | null>(null);
  const [assets, setAssets] = useState<AssetRow[]>([]);
  const [selection, setSelection] = useState<ReferenceSelection | null>(null);
  const [notices, setNotices] = useState<string[]>([]);
  const [assetError, setAssetError] = useState('');
  const [inspected, setInspected] = useState('');
  /** Which frame the pixels on screen actually belong to — never inferred from `sampleId`. */
  const [displayed, setDisplayed] = useState<PoseAttribution | null>(null);

  const host = useRef<HTMLDivElement | null>(null);
  const view = useRef<HistoryReferenceScene | null>(null);
  const assemblyKey = useRef('');
  const geometrySerial = useRef(0);
  const poseSerial = useRef(0);
  const geometryControllers = useRef<AbortController[]>([]);
  const poseControllers = useRef<AbortController[]>([]);
  const trackGeometry = (controller: AbortController) => { geometryControllers.current.push(controller); return controller; };
  const trackPose = (controller: AbortController) => { poseControllers.current.push(controller); return controller; };
  const releaseView = useCallback(() => { view.current?.dispose(); view.current = null; assemblyKey.current = ''; setSelection(null); setInspected(''); setDisplayed(null); }, []);

  // The placement tree is one read per Episode/run: stepping frames must not re-download it, and an
  // older answer never replaces the bundle the current Episode was assembled from. Its controllers are
  // separate from the pose read's: a frame step must not cancel the bundle it still needs.
  useEffect(() => {
    const token = ++geometrySerial.current;
    geometryControllers.current.forEach((controller) => controller.abort()); geometryControllers.current = [];
    if (!episodeId) { setGeometry(null); return; }
    void fetch(GEOMETRY_PATH, { method: 'GET', signal: trackGeometry(new AbortController()).signal, cache: 'no-store', headers: { Accept: 'application/json' } })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(`${String(body?.detail?.code ?? `HTTP_${response.status}`)} · ${String(body?.detail?.message ?? response.statusText)}`);
        if (body?.schema_version !== GEOMETRY_SCHEMA || body?.read_only !== true) throw new Error(`清单版本不是 ${GEOMETRY_SCHEMA} 或未声明 read_only（实际 schema=${String(body?.schema_version)} read_only=${String(body?.read_only)}）`);
        if (body?.world_pose_semantics !== GEOMETRY_SEMANTICS) throw new Error(`bundle 语义不是编译初始布局（实际 ${String(body?.world_pose_semantics)}）：不用它装配历史参考。`);
        return body as GeometryEnvelope;
      })
      .then((envelope) => { if (token === geometrySerial.current) setGeometry(envelope); })
      .catch((cause) => {
        if (token !== geometrySerial.current) return;
        setGeometry(null); releaseView();
        setStage({ status: 'failed', reason: `geometry bundle 清单读取失败：${describeHistoryError(cause) || String(cause)}` });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [episodeId, runId]);

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
    setStage({ status: 'reading', reason: `正在读取所选帧的 robot-state（sample_id=${sampleId}）；画面暂时回到编译初始布局，不使用上一帧的姿态。` });
    void readRobotState({ episodeId, runId, sampleId }, trackPose(new AbortController()).signal)
      .then((dto) => {
        if (token !== poseSerial.current) return;                      // a late pose never writes a newer frame
        assertHistoryFrameIdentity(dto, { episodeId, runId, sampleId });
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [episodeId, runId, sampleId]);

  // Both reads have to agree before anything is drawn: model identity, then every asset digest, then
  // the content identity of the very tree that is about to be drawn.
  useEffect(() => {
    if (!geometry || !pose) return;
    const key = `${episodeId}|${runId ?? ''}`;
    const comparison = comparisonRowsOf(pose);
    const unequal = comparison.filter((row) => row.equal !== 'true');
    if (pose.model_resource?.status !== 'match' || unequal.length) {
      setStage({ status: 'blocked', reason: `模型身份不符：model_resource.status=${String(pose.model_resource?.status)}，比较不等的字段 ${unequal.map((row) => row.key).join('/') || '无'}。不装配参考视图，也不把在线几何当作历史资源。` });
      releaseView(); return;
    }
    const history = new Map((pose.model_resource?.assets ?? []).map((asset) => [asset.asset_id, asset]));
    const bundleAssets: MeshAsset[] = geometry.data.mesh_assets ?? [];
    const rows: AssetRow[] = bundleAssets.map((asset) => {
      const declared = history.get(asset.asset_id);
      return { assetId: asset.asset_id, bundleSha: asset.sha256, historySha: declared?.sha256 ?? 'missing',
        equal: declared?.sha256 === asset.sha256, bytes: String(declared?.bytes ?? 'null'),
        coordinateSpace: declared?.coordinate_space ?? '未声明', readState: 'idle' as const, readDetail: '' };
    });
    setAssets(rows);
    const mismatched = rows.filter((row) => !row.equal);
    if (mismatched.length) {
      setStage({ status: 'blocked', reason: `资产摘要不一致：${mismatched.length}/${rows.length} 个资产在冻结 bundle 与历史清单之间摘要不同（${mismatched.slice(0, 4).map((row) => row.assetId).join(', ')}${mismatched.length > 4 ? '…' : ''}）：不按字节装配模型，也不降级为占位几何。` });
      releaseView(); return;
    }
    // Mesh digests alone cannot tell two different trees built from the same meshes apart.
    const binding = treeBindingRowsOf(pose, treeIdentityOf(geometry));
    const unbound = binding.filter((row) => row.equal !== 'true');
    if (unbound.length) {
      setStage({ status: 'blocked', reason: `静态树与记录的内容身份不一致：${unbound.map((row) => `${row.field}（历史=${row.history} / 树=${row.tree}）`).join('、')}。相同 mesh 摘要但不同树内容也在这里被拦下：不装配，也不退回在线 Actual。` });
      releaseView(); return;
    }
    if (!host.current) { setStage({ status: 'blocked', reason: '装配容器尚未可用：不渲染任何模型。' }); return; }
    // The manifest only rebuilds when the Episode (that is, the history asset namespace) changed.
    if (assemblyKey.current !== key || !view.current) {
      const manifest: SceneManifest = {
        ...geometry.data,
        mesh_assets: bundleAssets.map((asset) => ({
          ...asset,
          // Bytes come only from this Episode's history asset endpoint, with the bundle digest
          // attached so the server re-computes and refuses before any byte leaves the process.
          uri: `/api/v1/episodes/${encodeURIComponent(episodeId)}/model/assets/${encodeURIComponent(asset.asset_id)}?${runId ? `run_id=${encodeURIComponent(runId)}&` : ''}sha256=${asset.sha256}`,
        })),
      };
      const scene = view.current ?? new HistoryReferenceScene(host.current, {
        onNotice: (notice) => setNotices((previous) => [...previous.slice(-4), notice]),
        onAssetError: (message) => setAssetError(message),
      });
      view.current = scene;
      scene.mount(host.current, setSelection);
      scene.setManifest(manifest);
      assemblyKey.current = key;
    }
    // One pass per (geometry, pose): the tree and camera stay, and only the parts the reader allowed
    // for THIS frame move.
    const scene = view.current;
    if (!scene) { setStage({ status: 'blocked', reason: '装配视图未能创建：不驱动任何部件，也不宣称已装配。' }); return; }
    const drive = poseDriveOf(pose);
    scene.applyFramePose({ sample: pose.frame.sample_id, joints: drive.joints, base: drive.base, tcp: drive.tcp });
    setDisplayed(scene.attribution());
    setStage({ status: 'ready', reason: `固定模型树已装配：放置树来自冻结 geometry bundle（${GEOMETRY_SCHEMA}，${geometry.data.links.length} 条 link、${geometry.data.world_links.length} 条 world link），${rows.length} 个网格字节按声明摘要从历史端点读取，内容身份与记录一致。屏幕姿态归属见“显示帧”。` });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geometry, pose]);

  useEffect(() => () => {
    geometryControllers.current.forEach((controller) => controller.abort());
    poseControllers.current.forEach((controller) => controller.abort());
    releaseView();
  }, [releaseView]);

  const drive = poseDriveOf(pose);
  const rows = mappingRowsOf(pose);
  const partRows = partReadinessOf(pose);
  const fk = fkCrossCheckOf(pose);
  const binding = treeBindingRowsOf(pose, treeIdentityOf(geometry));
  const canRead = Boolean(episodeId) && Boolean(pose?.model_resource);
  const displayedSample = displayed?.displayedSample ?? '';
  const attributed = Boolean(displayedSample) && displayedSample === sampleId;

  /** One asset's bytes on demand: the reader re-computes the digest and 409s if the content changed. */
  function readOne(assetId: string) {
    const row = assets.find((item) => item.assetId === assetId);
    if (!row) return;
    const token = poseSerial.current;
    setAssets((previous) => previous.map((item) => item.assetId === assetId ? { ...item, readState: 'reading', readDetail: '正在按声明摘要读取字节…' } : item));
    void readHistoryModelAsset({ episodeId, runId, assetId, sha256: row.bundleSha }, trackPose(new AbortController()).signal)
      .then((value) => {
        if (token !== poseSerial.current) return;                    // a late byte read never rewrites a new episode's table
        const matches = value.digest === row.bundleSha;
        const detail = `${value.bytes.byteLength} 字节 · content-type=${value.mediaType || '未知'} · ETag ${value.etag || '无'} · cache-control=${value.cacheControl || '未声明'} · ${matches ? `服务端重算摘要与 bundle 声明一致（${value.digest.slice(0, 12)}）` : `摘要不符：服务端 ${value.digest.slice(0, 12) || '未在 ETag 里给出'} ≠ bundle ${row.bundleSha.slice(0, 12)}`}`;
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
    data-model-compiled-root-height={String(displayed?.compiledRootHeightWorldSimM ?? 'null')}>
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
        <tbody>{binding.map((row) => <tr key={row.field} data-tree-binding-row={row.field} data-tree-binding-equal={row.equal}>
          <td>{row.field}</td><td>{row.history}</td><td>{row.tree}</td><td>{row.equal}</td><td>{row.note}</td></tr>)}</tbody></table>
      <p className="session-note" data-tree-source-limit="true">仍需后端补齐：Episode 作用域的静态模型 manifest 尚未发布（历史面目前只有 8 条 GET，模型侧只有字节端点），因此放置树暂时取自 {GEOMETRY_PATH} 的冻结清单并按上表内容与记录绑定；该读取的 runtime 身份属于当前在线会话（{JSON.stringify(geometry?.geometry_binding?.exported_runtime_identity ?? '无')}），不是本 Episode。历史装配最终应只依赖那份 manifest。</p>
      <h4>历史模型资源身份</h4>
      <p className="session-note" data-model-resource={modelResourceText(pose)}>{modelResourceText(pose)}</p>
      <table className="frame-record-table" data-comparison-table="true"><thead><tr><th>身份字段</th><th>记录（run 清单）</th><th>冻结 bundle</th><th>相等</th></tr></thead>
        <tbody>{comparisonRowsOf(pose).map((row) => <tr key={row.key} data-comparison-row={row.key} data-comparison-equal={row.equal}>
          <td>{row.key}</td><td>{row.recorded}</td><td>{row.bundle}</td><td>{row.equal}</td></tr>)}</tbody></table>
      <table className="frame-record-table" data-asset-table="true"><thead><tr><th>asset_id</th><th>bundle 摘要</th><th>历史声明摘要</th><th>相等</th><th>字节</th><th>单资产读取</th></tr></thead>
        <tbody>{assets.map((row) => <tr key={row.assetId} data-asset-row={row.assetId} data-asset-equal={String(row.equal)}
          data-asset-read={row.readState} data-asset-detail={row.readDetail}>
          <td>{row.assetId}</td><td>{shortOr(row.bundleSha)}</td><td>{shortOr(row.historySha)}</td><td>{String(row.equal)}</td><td>{row.bytes}</td>
          <td><button data-asset-pick={row.assetId} disabled={!canRead || row.readState === 'reading'}
            title="只从历史资产端点按声明摘要读取；服务端先重算，摘要不符则 409 且不给字节"
            onClick={() => readOne(row.assetId)}>{row.readState === 'idle' ? '按摘要读取' : row.readState}</button>
            {row.readDetail && <small>{row.readDetail}</small>}</td></tr>)}</tbody></table>
      <p className="session-note" data-asset-equal-count={String(assets.filter((row) => row.equal).length)} data-asset-total={String(assets.length)}>
        {assets.filter((row) => row.equal).length}/{assets.length} 个资产的历史声明摘要与冻结 bundle 相等；字节只在点击或渲染时按该摘要校验读取，摘要不符不返回内容。单资产一致不推出整条 Episode 完整，也不推出历史姿态可用。</p>
    </>}
    {!sampleId && <p className="session-note" data-model-none="true">未绑定帧：不请求 robot-state（省略 sample_id 时 reader 会返回它自己的第一条记录），因此不装配任何模型。</p>}
  </section>;
}

const shortOr = (value: string | null | undefined) => !value ? 'null' : value.length > 20 ? `${value.slice(0, 16)}…` : value;
