import { useEffect, useState } from 'react';
import { Icon } from './Icon';
import { MapWaypointEditor } from '../map/MapWaypointEditor';
import { degToRad, moveWaypoint, radToDeg, removeWaypoint, updateWaypoint } from '../map/route';
import type { RouteWorkspace } from '../map/use-route-workspace';

const short = (value: string, size = 14) => value.length > size + 4 ? `${value.slice(0, size)}…` : value;
const yawText = (value: number | null) => value === null ? '未设置' : `${radToDeg(value).toFixed(1)}°`;

export function SceneSetupView({ workspace }: { workspace: RouteWorkspace }) {
  const [selectedId, setSelectedId] = useState<string | null>(workspace.working.waypoints[0]?.id ?? null);
  const [name, setName] = useState('前端 M1.3 路线草案');
  const [openId, setOpenId] = useState('');
  const draft = workspace.working;
  const map = draft.map;
  const authority = map.authority;
  const selected = draft.waypoints.find((point) => point.id === selectedId) ?? null;
  const server = workspace.serverDraft;
  const viewed = workspace.viewed;
  const publish = workspace.publishInfo;
  const evidence = workspace.imageEvidence;
  const verifiedThisMap = Boolean(evidence && workspace.mapState === 'ready' && !workspace.mapError
    && authority && evidence.mapId === map.mapId && evidence.mapVersion === map.version);
  const gates = workspace.gates;

  useEffect(() => { workspace.loadCatalog(); }, []);

  const editSelected = (patch: Parameters<typeof updateWaypoint>[2]) => {
    if (!selected) return;
    workspace.setWorking(updateWaypoint(draft, selected.id, patch));
  };
  const selectPoint = (id: string | null) => setSelectedId(id);

  return <section className="scene-setup" aria-label="Scene Setup 地图与 Waypoint">
    <header className="scene-setup-header">
      <div><h2>Scene Setup · 真实地图与 PointGoal 路线</h2>
        <p>地图来自 GET /api/v1/maps（G3B 历史离线包）；路线读写走 route-drafts / routes·versions。位置与朝向都必填，本轮不采用、不执行导航。</p></div>
      <div className="scene-setup-badges">
        <span className="chip strong" data-scene-map-mode={workspace.offlineMode ? 'offline-test' : 'backend'}>{workspace.offlineMode ? '离线测试地图' : '后端地图资源'}</span>
        <span className="chip masked" data-route-dirty={String(workspace.dirty)}>{server ? (workspace.dirty ? '本地未保存编辑' : '与服务端草案一致') : '未绑定服务端草案'}</span>
        <span className="chip masked" data-edits-after-save={String(workspace.editsAfterSave)}>{workspace.editsAfterSave ? `保存后又有编辑 · 服务器已存 r${server?.draftRevision ?? 0}` : '无保存后遗留编辑'}</span>
        <span className="chip masked">导航执行未开放</span>
      </div>
    </header>
    <div className="scene-setup-body">
      <div className="map-editor-column">
        <MapWaypointEditor map={map} waypoints={draft.waypoints} selectedId={selectedId}
          onChange={(points) => workspace.setWorking({ ...draft, waypoints: points })} onSelect={selectPoint}/>
        <div className="scene-setup-legend">
          <span><i className="target-color"/>PointGoal 位置</span>
          <span><i className="ghost-color"/>朝向箭头</span>
          <span><i className="target-color"/>编辑连线 · 非规划安全路径</span>
          <span>视图旋转/缩放/平移不改变 map 坐标</span>
        </div>
      </div>
      <aside className="scene-setup-side">
        <section data-map-catalog={workspace.catalogState}>
          <h3>地图目录 <small data-map-catalog-count={workspace.catalog.length}>{workspace.catalog.length} 个版本</small></h3>
          <div className="session-inline">
            <button disabled={workspace.catalogState === 'loading'} onClick={workspace.loadCatalog}>{workspace.catalogState === 'loading' ? '读取中…' : '重新读取地图目录'}</button>
            <button onClick={workspace.useOfflineMap} data-map-offline-switch>改用离线测试地图</button>
          </div>
          {workspace.catalogError && <div className="session-error" role="alert" data-map-catalog-error>地图目录读取失败：{workspace.catalogError}</div>}
          {workspace.catalogMeta && <dl className="session-fields" data-map-catalog-source={workspace.catalogMeta.source} data-map-catalog-live={String(workspace.catalogMeta.live)} data-map-catalog-supported={String(workspace.catalogMeta.supported)}>
            <div><dt>来源</dt><dd>{workspace.catalogMeta.source} · live={String(workspace.catalogMeta.live)} · {workspace.catalogMeta.schemaVersion}</dd></div>
            <div><dt>原因</dt><dd>{workspace.catalogMeta.reason ?? 'catalog 可用'}</dd></div>
          </dl>}
          <div className="session-state-list">{workspace.catalog.map((item) => <button key={`${item.map_id}/${item.version}`} data-map-option={`${item.map_id}/${item.version}`} data-map-nav-eligible={String(item.compatibility.navigation_eligible)}
            aria-pressed={`${map.mapId}/${map.version}` === `${item.map_id}/${item.version}`} disabled={workspace.busy === 'map'}
            onClick={() => workspace.selectMap(item.map_id, item.version)}><b>{item.version}</b><span>{item.map_id}</span></button>)}</div>
          {workspace.catalog.length === 0 && workspace.catalogState === 'ready' && <p className="session-note">目录为空：没有可读地图版本，路线编辑不可用。</p>}
        </section>

        <section>
          <h3>地图身份与校验</h3>
          <dl className="session-fields" data-map-id={map.mapId} data-map-version={map.version} data-map-frame={map.frame} data-map-source={map.source}>
            <div><dt>map</dt><dd>{map.mapId} · {map.version} · {map.frame}</dd></div>
            <div><dt>栅格</dt><dd data-map-dims={`${map.widthPx}x${map.heightPx}`}>{map.widthPx}×{map.heightPx} · {map.resolutionMPerPx} m/px · 图像行 {map.imageYAxis}</dd></div>
            <div><dt>origin</dt><dd>x={map.origin.xM} m · y={map.origin.yM} m · yaw={radToDeg(map.origin.yawRad).toFixed(1)}°（图像左下角在 map frame 的位姿）</dd></div>
            {authority ? <>
              <div><dt>provenance</dt><dd data-map-authority-source={authority.source} data-map-live={String(authority.live)} data-map-test-only={String(authority.testOnly)}>{authority.source} · live={String(authority.live)} · test_only={String(authority.testOnly)} · {authority.status}</dd></div>
              <div><dt>兼容</dt><dd data-map-compatibility={map.sceneCompatibility.status} data-map-g1-status={authority.compatibility.g1RecipeStatus} data-map-navigation-eligible={String(authority.compatibility.navigationEligible)}>{authority.compatibility.g1RecipeStatus} · navigation_eligible={String(authority.compatibility.navigationEligible)} · {map.sceneCompatibility.reason}</dd></div>
              <div><dt>未核验</dt><dd data-map-current-runtime={authority.compatibility.currentRuntimeStatus}>{authority.compatibility.currentRuntimeStatus} · runtime/profile 未在本切片核验；unverified={authority.compatibility.unverified.join(', ') || '[]'}</dd></div>
              <div><dt>资产</dt><dd data-map-assets-verified={String(authority.assetsVerified)} data-manifest-sha={authority.manifestSha256}>assets_verified={String(authority.assetsVerified)}（仅表示 manifest 声明的 YAML/PGM/posegraph 摘要逐字节核验；不等于 live SLAM、不等于整包全部校验通过）</dd></div>
              <div><dt>阈值</dt><dd>occupied={authority.thresholds.occupied} · free={authority.thresholds.free} · negate={String(authority.thresholds.negate)}</dd></div>
              <div><dt>frames</dt><dd>{authority.frames.map}/{authority.frames.odom}/{authority.frames.base} · interface={authority.interfaceProfile ?? 'null'}</dd></div>
              <div><dt>坐标约定</dt><dd data-map-convention={authority.coordinateConvention.cellCenter}>{authority.coordinateConvention.origin} · col {authority.coordinateConvention.imageColumn} · row {authority.coordinateConvention.imageRow} · yaw {authority.coordinateConvention.yawPositive} {authority.coordinateConvention.yawRange}</dd></div>
              <div><dt>声明图像</dt><dd data-map-image-sha={authority.image?.sha256 ?? ''}>{authority.image ? `${short(authority.image.sha256, 16)} · ${authority.image.bytes} B · ${authority.image.mediaType ?? '—'}` : '未声明'}</dd></div>
              <div><dt>实际图像</dt><dd data-image-verified={String(verifiedThisMap)} data-image-sha={evidence?.actualSha256 ?? ''}
                data-image-map={evidence ? `${evidence.mapId}/${evidence.mapVersion}` : ''} data-image-matches={evidence ? String(evidence.mapId === map.mapId && evidence.mapVersion === map.version) : 'false'}>
                {evidence ? `${short(evidence.actualSha256, 16)} · ${evidence.receivedBytes} B · ${evidence.magic}/maxval ${evidence.maxval} · ${evidence.decodedWidth}×${evidence.decodedHeight} · 属于 ${evidence.mapId}/${evidence.mapVersion}` : '尚未读取或未通过校验'}
              </dd></div>
            </> : <div><dt>来源</dt><dd data-map-offline="true">离线测试来源（非 SLAM、非导航地图，不写入后端路线）</dd></div>}
          </dl>
          {workspace.mapError && <div className="session-error" role="alert" data-map-error>{workspace.mapError}</div>}
          {workspace.mapState === 'loading' && <p className="session-note" data-map-state="loading">本次地图选择（版本详情 + 栅格 + 摘要/尺寸校验）仍在进行，写入已禁用。</p>}
          {!workspace.offlineMode && !verifiedThisMap && !workspace.mapError && workspace.mapState !== 'loading' && <div className="session-blocked" data-map-unavailable="true"><Icon name="info" size={15}/><div><b>该地图栅格未通过校验</b><p>{workspace.gates.create.reason}；显示与路线写入保持禁用，不会静默回退到离线测试地图。</p></div></div>}
        </section>

        <section>
          <h3>服务端 Route Draft</h3>
          <dl className="session-fields" data-draft-bound={String(Boolean(server))}>
            <div><dt>route_id</dt><dd data-route-id={server?.routeId ?? ''}>{server?.routeId ?? '尚未创建或未打开'}</dd></div>
            <div><dt>draft_revision</dt><dd data-draft-revision={String(server?.draftRevision ?? 0)}>{server ? `r${server.draftRevision} · updated ${server.updatedAt}` : '—'}</dd></div>
            <div><dt>content_digest</dt><dd data-content-digest={server?.contentDigest ?? ''}>{server ? server.contentDigest : '无服务端摘要（本地不生成摘要冒充）'}</dd></div>
            <div><dt>map_ref</dt><dd data-map-ref={server ? `${server.mapRef.mapId}/${server.mapRef.version}/${server.mapRef.frame}` : ''}>{server ? `${server.mapRef.mapId} · ${server.mapRef.version} · ${server.mapRef.frame}` : '—'}</dd></div>
            {server && <div><dt>validation</dt><dd data-pose-checks={String(server.validation.poseChecksPassed)} data-arrival={server.validation.arrivalAcceptance}>
              pose_checks_passed={String(server.validation.poseChecksPassed)} · arrival_acceptance={server.validation.arrivalAcceptance} · unsupported={server.validation.unsupportedChecks.join(', ') || '[]'}
            </dd></div>}
          </dl>
          <div className="scene-setup-actions">
            <label className="grow">路线名称<input aria-label="路线名称" value={name} onChange={(event) => setName(event.target.value)} disabled={workspace.busy !== ''}/></label>
            <button className="primary" data-route-create={gates.create.enabled ? 'ready' : 'blocked'} data-route-create-reason={gates.create.reason}
              disabled={!gates.create.enabled} title={gates.create.reason || 'POST /api/v1/route-drafts'} onClick={() => void workspace.createRoute(name)}>{workspace.busy === 'route-create' ? '创建中…' : '创建 Route Draft'}</button>
          </div>
          {workspace.mapMismatch && <div className="session-blocked" role="alert" data-map-mismatch="true"><Icon name="info" size={15}/><div><b>PointGoal 仍绑定旧地图</b><p>{draft.waypoints.filter((point) => point.mapId !== map.mapId || point.mapVersion !== map.version).length} 个点的 mapId/mapVersion 与当前地图不一致；不会隐式套用，写入已禁用。<button disabled={workspace.busy !== ''} onClick={workspace.clearPointsForSelectedMap}>清空 PointGoal 以改用此地图</button></p></div></div>}
          <div className="scene-setup-actions">
            <button data-route-save={gates.save.enabled ? 'ready' : 'blocked'} data-route-save-reason={gates.save.reason} disabled={!gates.save.enabled}
              title={server ? `PUT base_revision=r${server.draftRevision}${gates.save.reason ? ` · ${gates.save.reason}` : ''}` : gates.save.reason} onClick={workspace.saveRoute}>{workspace.busy === 'route-save' ? '保存中…' : '保存草案（条件写）'}</button>
            <button data-route-publish={gates.publish.enabled ? 'ready' : 'blocked'} data-route-publish-reason={gates.publish.reason} disabled={!gates.publish.enabled}
              title={server ? `POST publish base_revision=r${server.draftRevision}${gates.publish.reason ? ` · ${gates.publish.reason}` : ''}` : gates.publish.reason} onClick={workspace.publishRoute}>{workspace.busy === 'route-publish' ? '发布中…' : '发布 Route Version'}</button>
            <button disabled={workspace.busy !== '' || !server} onClick={workspace.refreshVersions}>刷新版本列表</button>
          </div>
          {workspace.conflict && <div className="session-blocked" role="alert" data-route-conflict={workspace.conflict.code}>
            <Icon name="info" size={15}/><div><b>修订条件不匹配（真实 409）</b><p>code={workspace.conflict.code} · current_revision={String(workspace.conflict.serverRevision)} · {workspace.conflict.message}。本地编辑仍保留，服务器内容未被覆盖。
              <button disabled={workspace.busy !== ''} onClick={workspace.reloadServerDraft} data-reload-server>重载服务器草案（放弃本地编辑）</button>
              <button disabled={!gates.retry.enabled} data-retry-server={gates.retry.enabled ? 'ready' : 'blocked'} data-retry-reason={gates.retry.reason} onClick={workspace.retrySaveOnServer}>以服务器修订重试（用本地内容写入）</button></p></div></div>}
          {workspace.draftError && <div className="session-error" role="alert" data-route-error>{workspace.draftError}</div>}
          {workspace.busy === 'route-save' && <p className="session-note" data-saving="true">PUT 进行中：这期间对 PointGoal 的修改不会被服务器响应覆盖，响应只更新已保存的 draft_revision 与 content_digest。</p>}
          {workspace.editsAfterSave && server && <div className="session-blocked" role="status" data-after-save-edits="true">
            <Icon name="info" size={15}/><div><b>服务器已保存 r{server.draftRevision}，提交之后的本地编辑仍未保存</b>
              <p>本次写入受理的是提交瞬间的快照；此后在界面上继续做的编辑既没有被响应覆盖，也没有被丢弃（data-route-dirty 仍为 true，本地共 {draft.waypoints.length} 点）。再点“保存草案（条件写）”会以 base_revision=r{server.draftRevision} 提交当前本地内容。</p></div></div>}
          {workspace.staleWriteHint && <div className="session-blocked" role="status" data-stale-write="true"><Icon name="info" size={15}/><div><b>迟到的路线写入结果已被忽略</b><p>{workspace.staleWriteHint}</p></div></div>}
          <div className="session-inline">
            <input aria-label="按 route_id 打开" placeholder="route-…" value={openId} onChange={(event) => setOpenId(event.target.value)} disabled={workspace.busy !== ''}/>
            <button disabled={workspace.busy !== '' || !openId.trim()} data-route-open onClick={() => workspace.openRoute(openId.trim())}>打开服务端草案</button>
            <button disabled={!server} onClick={workspace.closeRoute}>解除绑定</button>
          </div>
          <p className="session-note">后端没有路线目录 GET，因此只能凭 route_id 打开；创建后地址栏会带上 ?route=…，刷新页面即重新读取服务端草案与版本列表。</p>
          {publish && <p className="session-note" data-publish-note={publish.reused ? 'reused' : 'published'} data-publish-revision={String(publish.fromRevision)}
            data-publish-version={publish.version} data-publish-digest={publish.contentDigest} data-publish-dirty={String(publish.localEditsExcluded)}>
            {`发布结果对应服务端草案修订 r${publish.fromRevision} → 固定版本 ${publish.version}（content_digest ${short(publish.contentDigest, 16)}）${publish.reused ? ' · 服务器复用了已存在的该版本' : ''}。`}
            {publish.localEditsExcluded
              ? '注意：本地还有未保存的编辑，它们没有被包含在本次发布里；先“保存草案（条件写）”再重新发布。'
              : '发布时本地内容与服务端草案一致。'}
          </p>}
          <p className="session-note" data-route-errors={workspace.errors.length}>提交前检查：{workspace.errors.length ? workspace.errors.join('；') : '每点位置与朝向有效（不代表后端预检已通过；以 validation 为准）'}。</p>
        </section>

        <section>
          <h3>不可变 Route Version <small data-route-version-count={workspace.versions.length}>{workspace.versions.length} 个</small></h3>
          {workspace.versionsError && <div className="session-error" role="alert" data-versions-error>版本列表读取失败：{workspace.versionsError}</div>}
          {workspace.versions.length === 0 ? <p className="session-note">尚无发布版本。发布只产生固定 vN 与后端 content_digest；查看版本不等于采用，也不等于导航 Ready。</p>
            : <div className="session-state-list">{workspace.versions.map((item) => <button key={item.version} data-version-option={item.version} data-version-digest={item.contentDigest} aria-pressed={viewed?.version === item.version}
              disabled={workspace.busy === 'version-view'} onClick={() => workspace.viewVersion(item.version)}><b>{item.version}</b><span>{item.waypointCount} 点 · {short(item.contentDigest, 12)}</span></button>)}</div>}
          {viewed ? <article className="session-card" data-version-view={viewed.version} data-version-digest={viewed.contentDigest} data-nav-eligible={String(viewed.navigationEligible)} data-adoption-supported={String(viewed.adoptionSupported)} data-execution-supported={String(viewed.executionSupported)}>
            <div className="session-card-head"><b>固定版本 {viewed.version}</b><span>{short(viewed.routeId, 16)}</span></div>
            <dl className="session-fields">
              <div><dt>content_digest</dt><dd>{viewed.contentDigest}</dd></div>
              <div><dt>created_at</dt><dd>{viewed.createdAt} · {viewed.waypoints.length} 点</dd></div>
              <div><dt>资格</dt><dd>navigation_eligible={String(viewed.navigationEligible)} · adoption_supported={String(viewed.adoptionSupported)} · execution_supported={String(viewed.executionSupported)} · display_supported={String(viewed.displaySupported)}</dd></div>
              <div><dt>map_ref</dt><dd>{viewed.mapRef.mapId} · {viewed.mapRef.version} · {viewed.mapRef.frame}</dd></div>
              <div><dt>点位</dt><dd>{viewed.waypoints.map((point) => `${point.order}·${short(point.id, 8)}·${yawText(point.yawRad)}`).join(' ')}</dd></div>
            </dl>
            <div className="scene-setup-actions">
              <button disabled data-route-adopt="blocked" title="后端 validation.adoption_supported=false；当前 G1 没有导航采用能力">采用此版本</button>
              <button disabled data-route-execute="blocked" title="后端 execution_supported=false；本轮不下发目标">执行路线</button>
              <button onClick={workspace.closeVersionView}>回到本地草案</button>
            </div>
            <p className="session-note">这是 GET /api/v1/routes/{"{route_id}"}/versions/{"{version}"} 的固定文档，不替代本地草案，也不修改任何 Session 或配置引用。</p>
          </article> : <p className="session-note">{server ? '未选中固定版本。点击上方 vN 读取该版本。' : '未绑定服务端草案，无版本可读。'}</p>}
        </section>

        <section>
          <h3>PointGoal 列表 <small data-route-waypoint-count={draft.waypoints.length}>{draft.waypoints.length} 个</small></h3>
          <div className="scene-setup-actions">
            <button disabled={!draft.waypoints.length} onClick={() => { workspace.setWorking({ ...draft, waypoints: [] }); setSelectedId(null); }}>清空</button>
          </div>
          {draft.waypoints.length === 0 ? <p className="session-note">尚无 PointGoal。在地图上点击放置，再拖方向手柄或输入角度；新点默认“朝向未设置”，不会静默写入 0°。</p> :
            <ol className="route-point-list">{draft.waypoints.map((point) => <li key={point.id} data-route-point={point.id} data-route-order={point.order} className={point.id === selectedId ? 'selected' : ''}>
              <button className="route-point-main" onClick={() => selectPoint(point.id)}>
                <b>{point.order}</b><span>{short(point.id)}</span><small>{point.xM.toFixed(2)}, {point.yM.toFixed(2)} m · {yawText(point.yawRad)}</small>
              </button>
              <div className="route-point-actions">
                <button aria-label={`上移 ${point.id}`} disabled={point.order === 1} onClick={() => workspace.setWorking(moveWaypoint(draft, point.id, -1))}>↑</button>
                <button aria-label={`下移 ${point.id}`} disabled={point.order === draft.waypoints.length} onClick={() => workspace.setWorking(moveWaypoint(draft, point.id, 1))}>↓</button>
                <button aria-label={`删除 ${point.id}`} onClick={() => { workspace.setWorking(removeWaypoint(draft, point.id)); if (selectedId === point.id) selectPoint(null); }}>×</button>
              </div>
            </li>)}</ol>}
        </section>
        {selected && <section>
          <h3>选中 PointGoal <small>{short(selected.id)}</small></h3>
          <div className="scene-setup-fields">
            <label>X / m<input aria-label="Waypoint X" type="number" step="0.025" value={Number(selected.xM.toFixed(3))} onChange={(event) => { const value = event.target.valueAsNumber; if (Number.isFinite(value)) editSelected({ xM: value }); }}/></label>
            <label>Y / m<input aria-label="Waypoint Y" type="number" step="0.025" value={Number(selected.yM.toFixed(3))} onChange={(event) => { const value = event.target.valueAsNumber; if (Number.isFinite(value)) editSelected({ yM: value }); }}/></label>
            <label>朝向 / °<input aria-label="Waypoint yaw deg" type="number" step="1" value={selected.yawRad === null ? '' : Number(radToDeg(selected.yawRad).toFixed(2))} placeholder="未设置" onChange={(event) => { const text = event.target.value; if (text === '') { editSelected({ yawRad: null }); return; } const value = event.target.valueAsNumber; if (Number.isFinite(value)) editSelected({ yawRad: degToRad(value) }); }}/></label>
          </div>
          <p className="session-note">wire 字段是 x_m/y_m/yaw_rad（rad，后端归一化到 [-π, π)；当前 {selected.yawRad === null ? '未设置' : selected.yawRad.toFixed(5)} rad）。显式 0° 合法；零长度方向拖动不会写入 0°。稳定 ID 不随重排改变。</p>
        </section>}
        <p className="scene-setup-note">保存/发布只操作路线资源；后端 validation 固定 navigation_eligible=false、adoption_supported=false、execution_supported=false、arrival_acceptance=not_checked。点间连线只是编辑连线，不是已规划安全路径。</p>
      </aside>
    </div>
  </section>;
}
