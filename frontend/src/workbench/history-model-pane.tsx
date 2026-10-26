/**
 * The fixed model reference for one historical Episode: the frozen geometry bundle's placement tree
 * with the mesh bytes read from the Episode's own history asset endpoint, plus the per-part mapping
 * gate that decides whether any recorded joint value may move the model at all.
 *
 * The pose on screen is the compiled reference layout, not the selected frame's pose, until the
 * backend marks a target's mapping `verified`; the selected frame's numbers stay in the table under
 * the view. Nothing here reads the live snapshot or Actual for historical content, applies a Target
 * or Ghost, or sends a command. The manifest is assembled once per Episode — a frame step only
 * re-reads robot-state and re-applies the joints the gate allowed — and an Episode switch, an
 * unmount or any refused identity releases the surface and its mesh bytes.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Icon } from './Icon';
import { describeHistoryError } from '../adapters/platform-episodes';
import { HistoryReferenceScene, type ReferenceSelection } from '../viewport/history-reference-scene';
import type { MeshAsset, SceneManifest } from '../adapters/types';
import {
  assertHistoryFrameIdentity, comparisonRowsOf, mappingRowsOf, modelAssetRowsOf, modelResourceText, notProvenText,
  poseBoundaryText, poseDriveOf, poseReadinessText, poseStateText, readHistoryModelAsset, readRobotState,
  renderingText, type HistoryAssetDto, type HistoryPoseDto,
} from '../adapters/platform-history-pose';

/** The placement tree comes from the platform's own frozen geometry envelope. */
const GEOMETRY_PATH = '/api/v1/mobilecar/scene';
const GEOMETRY_SCHEMA = 'unirobot-mobilecar-geometry-2';
/** The bundle's own words for "compiled initial layout", which is what a reference pose may be. */
const GEOMETRY_SEMANTICS = 'compiled_initial_layout_not_live_object_state';

interface GeometryEnvelope { schema_version: string; read_only: boolean; world_pose_semantics: string; data: SceneManifest }
interface AssetRow { assetId: string; bundleSha: string; historySha: string; equal: boolean; bytes: string; coordinateSpace: string;
  readState: 'idle' | 'reading' | 'ok' | 'failed'; readDetail: string }

export function HistoryModelPane({ episodeId, runId, sampleId }: { episodeId: string; runId: string | null; sampleId: string | null }) {
  const [stage, setStage] = useState<{ status: string; reason: string }>({ status: 'idle', reason: '未选择帧：不读取 robot-state，也不装配模型。' });
  const [pose, setPose] = useState<HistoryPoseDto | null>(null);
  const [geometry, setGeometry] = useState<GeometryEnvelope | null>(null);
  const [assets, setAssets] = useState<AssetRow[]>([]);
  const [selection, setSelection] = useState<ReferenceSelection | null>(null);
  const [notices, setNotices] = useState<string[]>([]);
  const [assetError, setAssetError] = useState('');
  const [inspected, setInspected] = useState('');

  const host = useRef<HTMLDivElement | null>(null);
  const view = useRef<HistoryReferenceScene | null>(null);
  const assemblyKey = useRef('');
  const geometrySerial = useRef(0);
  const poseSerial = useRef(0);
  const geometryControllers = useRef<AbortController[]>([]);
  const poseControllers = useRef<AbortController[]>([]);
  const trackGeometry = (controller: AbortController) => { geometryControllers.current.push(controller); return controller; };
  const trackPose = (controller: AbortController) => { poseControllers.current.push(controller); return controller; };
  const releaseView = useCallback(() => { view.current?.dispose(); view.current = null; assemblyKey.current = ''; setSelection(null); setInspected(''); }, []);

  // The placement tree is one read per Episode/run: stepping frames must not re-download it, and an
  // older answer never replaces the bundle the current Episode was assembled from. Its controllers
  // are separate from the pose read's: a frame step must not cancel the bundle it still needs.
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
    setStage({ status: 'reading', reason: `正在读取所选帧的 robot-state 与冻结 geometry bundle 清单（GET ${GEOMETRY_PATH}；网格字节按摘要走历史资产端点）。` });
    void readRobotState({ episodeId, runId, sampleId }, trackPose(new AbortController()).signal)
      .then((dto) => {
        if (token !== poseSerial.current) return;                      // a late pose never writes a newer frame
        assertHistoryFrameIdentity(dto, { episodeId, runId, sampleId });
        setPose(dto);
      })
      .catch((cause) => {
        if (token !== poseSerial.current) return;
        setPose(null); releaseView();
        setStage({ status: 'failed', reason: `robot-state 读取失败：${describeHistoryError(cause)}` });
      });
    return () => { poseControllers.current.forEach((controller) => controller.abort()); poseControllers.current = []; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [episodeId, runId, sampleId]);

  // Both reads have to agree before anything is drawn: model identity first, then every asset digest.
  useEffect(() => {
    if (!geometry || !pose) return;
    const key = `${episodeId}|${runId ?? ''}`;
    const comparison = comparisonRowsOf(pose);
    const unequal = comparison.filter((row) => row.equal !== 'true');
    if (pose.model_resource?.status !== 'match' || unequal.length) {
      setStage({ status: 'blocked', reason: `模型身份不符：model_resource.status=${String(pose.model_resource?.status)}，比较不等的字段 ${unequal.map((row) => row.key).join('/') || '无'}。不装配参考视图，也不把在线几何当作历史资源。` });
      releaseView(); return;
    }
    const history = new Map<string, HistoryAssetDto>((pose.model_resource?.assets ?? []).map((asset) => [asset.asset_id, asset]));
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
    if (!host.current) { setStage({ status: 'blocked', reason: '装配容器尚未可用：不渲染任何模型。' }); return; }
    // The manifest only rebuilds when the Episode (that is, the history asset namespace) changed.
    if (assemblyKey.current !== key || !view.current) {
      const manifest: SceneManifest = {
        ...geometry.data,
        mesh_assets: bundleAssets.map((asset) => ({
          ...asset,
          // Bytes come only from this Episode's history asset endpoint, with the bundle digest
          // attached so the server re-computes and refuses before any byte leaves the process.
          uri: `${GEOMETRY_PATH ? '' : ''}/api/v1/episodes/${encodeURIComponent(episodeId)}/model/assets/${encodeURIComponent(asset.asset_id)}?${runId ? `run_id=${encodeURIComponent(runId)}&` : ''}sha256=${asset.sha256}`,
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
    const drive = poseDriveOf(pose);
    view.current.applyVerifiedJoints(drive.driven);
    // The status is written on every pass, not only when the bundle is (re)built: a frame step inside
    // the same Episode reuses the assembly, and leaving the stage at “reading” would tell the user the
    // reference is still being fetched when it is already the current one.
    setStage({ status: 'ready', reason: `固定模型参考已装配：放置树来自冻结 geometry bundle（${GEOMETRY_SCHEMA}，${geometry.data.links.length} 条 link、${geometry.data.world_links.length} 条 world link），${rows.length} 个网格字节按声明摘要从历史端点读取。屏幕姿态=${'编译初始布局（reference pose）'}，不是所选帧姿态。` });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geometry, pose]);

  useEffect(() => () => {
    geometryControllers.current.forEach((controller) => controller.abort());
    poseControllers.current.forEach((controller) => controller.abort());
    releaseView();
  }, [releaseView]);

  const drive = poseDriveOf(pose);
  const rows = mappingRowsOf(pose);
  const canRead = Boolean(episodeId) && Boolean(pose?.model_resource);

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
    data-model-episode={episodeId || 'none'} data-model-sample={sampleId ?? 'none'}
    data-reference-pose="compiled-initial-layout" data-frame-pose-verified="false" data-model-live-poll="off">
    <h3>固定模型参考 · 历史姿态按证据门控 <small data-model-current-sample={sampleId ?? '—'}>{sampleId ?? '未绑定帧'}</small></h3>
    <div className="session-blocked history-model-banner" data-model-banner="true" role="note">
      <Icon name="info" size={15}/>
      <div><b>固定模型参考；所选帧姿态尚未验证</b>
        <p>屏幕上的姿态是编译初始布局（reference pose），不是这一帧的历史姿态。历史数值在下面按分部映射原样显示；只有后端把某个目标标为 <code>verified</code> 时，界面才用记录的模型弧度驱动那一部分——不做用户零位换算，不把缺失角度补成 0，也不因某一项可用就声称整车可重建。动态世界物体没有历史记录位姿，因此不显示伪造位置。</p></div>
    </div>
    <p className="session-note" data-model-stage={stage.reason}>{stage.reason}</p>
    {assetError && <p className="session-error" data-model-asset-error="true">网格字节读取失败（历史端点）：{assetError}</p>}
    {notices.length > 0 && <p className="session-note" data-model-notices={notices.join(' | ')}>{notices.join(' | ')}</p>}

    <div className="model-grid">
      <div className="model-canvas" ref={host} data-model-canvas-host="true"></div>
      <div className="model-side">
        <p className="session-note" data-model-drive-summary={drive.summary}>{drive.summary}</p>
        <ul className="model-withheld" data-model-withheld-count={String(drive.withheld.length)}>
          {drive.withheld.map((line, index) => <li key={index} data-model-withheld={index}>{line}</li>)}
          {!drive.withheld.length && <li data-model-withheld-none="true">没有未驱动目标：允许驱动的目标都由 verified 放行。</li>}
        </ul>
        <div className="session-inline">
          <button data-model-fit disabled={!view.current} onClick={() => view.current?.fitView()}>适应视图</button>
          <button data-model-inspect disabled={!view.current} onClick={() => setInspected(JSON.stringify(view.current?.inspect() ?? { error: '尚未装配视图' }))}>读取视图状态</button>
          <span className="chip masked" data-model-control-surface="none">历史参考面不挂 Target/Ghost/工具，也不轮询 live snapshot</span>
        </div>
        <p className="session-note" data-model-selection={selection ? `${selection.linkName} · ${selection.jointType} · ${selection.geoms.length} 个 geom` : '未选中部件'}>
          选择（只读）：{selection ? `${selection.linkName} · joint ${selection.jointName}(${selection.jointType}) · parent ${selection.parentName}` : '点选模型上的部件即可列出 link/geom；不拖拽、不产生 Target、不发命令。'}</p>
        {selection && <table className="frame-record-table" data-model-selection-table="true"><thead><tr><th>geom</th><th>类型</th><th>mesh asset</th></tr></thead>
          <tbody>{selection.geoms.map((geom) => <tr key={geom.name} data-model-geom={geom.name} data-geom-mesh={geom.meshAssetId}><td>{geom.name}</td><td>{geom.geomType}</td><td>{geom.meshAssetId}</td></tr>)}</tbody></table>}
        {inspected && <pre className="session-note" data-model-inspected={inspected}>{inspected}</pre>}
      </div>
    </div>

    {pose && <>
      <h4>分部映射状态（robot-state 原样）</h4>
      <p className="session-note" data-pose-readiness={poseReadinessText(pose)}>{poseReadinessText(pose)}</p>
      <p className="session-note" data-pose-rendering={renderingText(pose)}>{renderingText(pose)}</p>
      <p className="session-note" data-pose-state={poseStateText(pose)}>{poseStateText(pose)}</p>
      <table className="frame-record-table" data-mapping-table="true">
        <thead><tr><th>目标</th><th>记录字段／单位／长度</th><th>模型侧目标</th><th>状态</th><th>依据与换算</th><th>不补默认值</th><th>驱动</th></tr></thead>
        <tbody>{rows.map((row) => <tr key={row.target} data-mapping-row={row.target} data-mapping-status={row.status} data-mapping-no-default={row.noDefault}
          data-mapping-drivable={String(drive.parts[row.target]?.drivable ?? false)}>
          <td>{row.target}</td>
          <td>{row.recordedField}<small>{row.recordedUnit} · 长度 {row.recordedLength}</small></td>
          <td>{row.targetField}</td>
          <td><span className={row.status === 'verified' ? 'ok' : row.status === 'partially_verified' ? 'unknown' : 'bad'}>{row.status}</span><small>{row.statusMeaning}</small></td>
          <td><small>{row.evidence}</small><small>{row.formula}</small></td>
          <td>{row.noDefault}</td>
          <td>{drive.parts[row.target] ? `${drive.parts[row.target].drivable ? '驱动' : '不驱动'}：${drive.parts[row.target].reason}` : '界面没有该目标的驱动规则：不驱动。'}</td></tr>)}</tbody></table>
      <p className="session-note" data-pose-gap-list={rows.map((row) => `${row.target}:${row.gap}`).join(' ｜ ')}>{rows.map((row) => `${row.target}:${row.gap}`).join(' ｜ ')}</p>
      <p className="session-note" data-pose-not-proven={notProvenText(pose)}>{notProvenText(pose)}</p>
      <p className="session-note" data-pose-boundary={poseBoundaryText(pose)}>{poseBoundaryText(pose)}</p>
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
