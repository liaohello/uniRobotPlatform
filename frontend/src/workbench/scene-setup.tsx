import { useState } from 'react';
import { Icon } from './Icon';
import { MapWaypointEditor } from '../map/MapWaypointEditor';
import {
  degToRad, loadOfflineSample, moveWaypoint, radToDeg, removeWaypoint, routeErrors,
  updateWaypoint, type RouteDraft, type Waypoint,
} from '../map/route';
import {
  emptyStore, publishVersion, reloadDraft, RouteConflict, saveDraft, versionsOf,
  type RouteStoreState, type StoredDraft,
} from '../map/route-store';

const short = (value: string) => value.length > 18 ? `${value.slice(0, 14)}…` : value;
const yawText = (value: number | null) => value === null ? '未设置' : `${radToDeg(value).toFixed(1)}°`;

export function SceneSetupView({ draft, onChange }: { draft: RouteDraft; onChange(draft: RouteDraft): void }) {
  const [selectedId, setSelectedId] = useState<string | null>(draft.waypoints[0]?.id ?? null);
  const [store, setStore] = useState<RouteStoreState>(emptyStore);
  const [serverRevision, setServerRevision] = useState(0);
  const [conflict, setConflict] = useState<{ message: string; server: StoredDraft | null } | null>(null);
  const [savedAt, setSavedAt] = useState('');
  const selected = draft.waypoints.find((point) => point.id === selectedId) ?? null;
  const errors = routeErrors(draft);
  const versions = versionsOf(store, draft.routeId);
  const savedDraft = store.drafts[draft.routeId] ?? null;
  const setWaypoints = (next: Waypoint[]) => onChange({ ...draft, waypoints: next });
  const select = (id: string | null) => setSelectedId(id);
  const editSelected = (patch: Partial<Pick<Waypoint, 'xM' | 'yM' | 'yawRad'>>) => {
    if (!selected) return;
    onChange(updateWaypoint(draft, selected.id, patch));
  };
  const loadSample = () => {
    const next = loadOfflineSample(draft);
    onChange(next); setSelectedId(next.waypoints[0]?.id ?? null);
  };
  const canSave = draft.waypoints.length > 0 && errors.length === 0;
  const save = () => {
    try {
      const result = saveDraft(store, draft, serverRevision);
      setStore(result.state); setServerRevision(result.saved.draftRevision);
      setConflict(null); setSavedAt(new Date().toISOString());
      onChange({ ...draft, draftRevision: result.saved.draftRevision });
    } catch (error) {
      if (error instanceof RouteConflict) setConflict({ message: error.message, server: store.drafts[draft.routeId] ?? null });
      else throw error;
    }
  };
  const publish = () => setStore(publishVersion(store, draft.routeId).state);
  const reloadServer = () => {
    const server = reloadDraft(store, draft.routeId);
    if (!server) return;
    onChange({ routeId: server.routeId, draftRevision: server.draftRevision, label: server.label, map: server.map, waypoints: server.waypoints });
    setServerRevision(server.draftRevision); setConflict(null);
  };
  return <section className="scene-setup" aria-label="Scene Setup 地图与 Waypoint">
    <header className="scene-setup-header">
      <div><h2>Scene Setup · 地图与 PointGoal 路线</h2><p>位置 + 朝向编辑；保存/发布等待后端 map/route 契约。本轮不执行导航。</p></div>
      <div className="scene-setup-badges"><span className="chip strong">本地草案</span><span className="chip masked">未保存</span><span className="chip masked">导航执行未开放</span></div>
    </header>
    <div className="scene-setup-body">
      <div className="map-editor-column">
        <MapWaypointEditor map={draft.map} waypoints={draft.waypoints} selectedId={selectedId}
          onChange={setWaypoints} onSelect={select}/>
        <div className="scene-setup-legend">
          <span><i className="target-color"/>PointGoal 位置</span>
          <span><i className="ghost-color"/>朝向箭头</span>
          <span><i className="target-color"/>编辑连线 · 非规划安全路径</span>
          <span>地图视图旋转/缩放/平移不改变 map 坐标</span>
        </div>
      </div>
      <aside className="scene-setup-side">
        <section>
          <h3>地图身份</h3>
          <dl className="session-fields" data-map-id={draft.map.mapId} data-map-version={draft.map.version} data-map-frame={draft.map.frame} data-map-source={draft.map.source}>
            <div><dt>map</dt><dd>{draft.map.mapId} · {draft.map.version}</dd></div>
            <div><dt>frame</dt><dd>{draft.map.frame} · 图像 Y {draft.map.imageYAxis}</dd></div>
            <div><dt>分辨率</dt><dd>{draft.map.resolutionMPerPx} m/px · {draft.map.widthPx}×{draft.map.heightPx}</dd></div>
            <div><dt>原点</dt><dd>x={draft.map.origin.xM} m · y={draft.map.origin.yM} m · yaw={radToDeg(draft.map.origin.yawRad).toFixed(1)}°</dd></div>
            <div><dt>来源</dt><dd>{draft.map.source === 'offline_test_fixture' ? '离线测试地图 · 非 SLAM' : draft.map.source}</dd></div>
            <div><dt>兼容</dt><dd data-map-compatibility={draft.map.sceneCompatibility.status}>{draft.map.sceneCompatibility.status} · {draft.map.sceneCompatibility.reason}</dd></div>
          </dl>
        </section>
        <section>
          <h3>路线草案</h3>
          <dl className="session-fields" data-backend-route-api="unavailable" data-local-store-authority={store.authority}>
            <div><dt>route</dt><dd>{draft.routeId} · 工作修订 r{draft.draftRevision} · 存储修订 r{serverRevision}</dd></div>
            <div><dt>PointGoal</dt><dd data-route-waypoint-count={draft.waypoints.length}>{draft.waypoints.length} 个 · 每点必须有位置和朝向</dd></div>
            <div><dt>后端 Route API</dt><dd data-route-saved="false">18949 未提供 map/route 端点 · 后端未保存</dd></div>
            <div><dt>本地存储</dt><dd data-route-local-state={conflict ? 'conflict' : savedDraft ? 'saved' : 'unsaved'}>{savedDraft ? `会话内 r${savedDraft.draftRevision} · ${savedDraft.authority} · ${savedAt}` : '尚无本地保存（刷新即丢失）'}</dd></div>
          </dl>
          <div className="scene-setup-actions">
            <button onClick={loadSample}>载入离线示例</button>
            <button disabled={!draft.waypoints.length} onClick={() => { onChange({ ...draft, waypoints: [] }); setSelectedId(null); }}>清空</button>
          </div>
          <div className="route-backend-blocked" data-route-backend="unavailable">
            <Icon name="info" size={14}/>
            <div><b>后端 Route 保存 / 采用不可用</b><p>18949 OpenAPI 没有 map/route/waypoint 端点。本轮不猜测 wire、不伪造后端保存成功；下面的写入只落在清楚标注的会话内本地存储，刷新后丢失，后端与活动 Session 不受影响。</p></div>
          </div>
          <div className="scene-setup-actions">
            <button data-route-save={canSave ? 'ready' : 'blocked'} disabled={!canSave} title={canSave ? '会话内本地存储，带 draftRevision 条件写' : '需至少一个 PointGoal 且每点位置与朝向有效'} onClick={save}>保存到本地存储</button>
            <button data-route-publish={savedDraft ? 'ready' : 'blocked'} disabled={!savedDraft} title={savedDraft ? '冻结为不可变 Route Version' : '先保存草案'} onClick={publish}>发布 Route Version</button>
            <button disabled data-route-adopt="blocked" title="后端未提供配置采用 API">采用版本</button>
          </div>
          {conflict && <div className="session-blocked" role="alert" data-route-conflict="true"><Icon name="info" size={15}/><div><b>本地修订条件不匹配</b><p>{conflict.message}。本地编辑已保留，未覆盖存储内容。<button disabled={!conflict.server} onClick={reloadServer}>显式重载存储草案</button></p></div></div>}
          <dl className="session-fields" data-route-version-count={versions.length}>
            <div><dt>本地版本</dt><dd>{versions.length ? versions.map((item) => `v${item.version}（r${item.savedDraftRevision} · ${item.contentDigest} · ${item.waypoints.length} 点）`).join(' · ') : '尚无发布版本'}</dd></div>
            <div><dt>采用引用</dt><dd data-route-adopted={store.adoptedRef ? String(store.adoptedRef.version) : 'none'}>{store.adoptedRef ? `v${store.adoptedRef.version}` : '未采用 · 发布不改变已有引用与活动 Session'}</dd></div>
          </dl>
          <p className="session-note" data-route-errors={errors.length}>路线检查：{errors.length ? errors.join('；') : '本地结构有效（不代表后端/导航资格）'}。保存/发布成功只是本地草案与版本事实，不等于导航 Ready；导航执行、目标下发与热重规划本轮未开放。</p>
        </section>
        <section>
          <h3>PointGoal 列表</h3>
          {draft.waypoints.length === 0 ? <p className="session-note">尚无 PointGoal。点击地图放置第一个点，再拖动方向手柄或输入角度。</p> :
            <ol className="route-point-list">
              {draft.waypoints.map((point) => <li key={point.id} data-route-point={point.id} data-route-order={point.order} className={point.id === selectedId ? 'selected' : ''}>
                <button className="route-point-main" onClick={() => select(point.id)}>
                  <b>{point.order}</b><span>{short(point.id)}</span><small>{point.xM.toFixed(2)}, {point.yM.toFixed(2)} m · {yawText(point.yawRad)}</small>
                </button>
                <div className="route-point-actions">
                  <button aria-label={`上移 ${point.id}`} disabled={point.order === 1} onClick={() => onChange(moveWaypoint(draft, point.id, -1))}>↑</button>
                  <button aria-label={`下移 ${point.id}`} disabled={point.order === draft.waypoints.length} onClick={() => onChange(moveWaypoint(draft, point.id, 1))}>↓</button>
                  <button aria-label={`删除 ${point.id}`} onClick={() => { onChange(removeWaypoint(draft, point.id)); if (selectedId === point.id) setSelectedId(null); }}>×</button>
                </div>
              </li>)}
            </ol>}
        </section>
        {selected && <section>
          <h3>选中 PointGoal <small>{short(selected.id)}</small></h3>
          <div className="scene-setup-fields">
            <label>X / m<input aria-label="Waypoint X" type="number" step="0.05" value={Number(selected.xM.toFixed(3))} onChange={(event) => { const value = event.target.valueAsNumber; if (Number.isFinite(value)) editSelected({ xM: value }); }}/></label>
            <label>Y / m<input aria-label="Waypoint Y" type="number" step="0.05" value={Number(selected.yM.toFixed(3))} onChange={(event) => { const value = event.target.valueAsNumber; if (Number.isFinite(value)) editSelected({ yM: value }); }}/></label>
            <label>朝向 / °<input aria-label="Waypoint yaw deg" type="number" step="1" value={selected.yawRad === null ? '' : Number(radToDeg(selected.yawRad).toFixed(2))} placeholder="未设置" onChange={(event) => { const text = event.target.value; if (text === '') { editSelected({ yawRad: null }); return; } const value = event.target.valueAsNumber; if (Number.isFinite(value)) editSelected({ yawRad: degToRad(value) }); }}/></label>
          </div>
          <p className="session-note">wire 角度使用 rad 归一化到 [-π, π)（{selected.yawRad === null ? '当前未设置' : selected.yawRad.toFixed(5)} rad）。朝向 0° 必须由用户显式输入或有效拖动确认，零长度方向拖动不会填入 0°。</p>
        </section>}
        <p className="scene-setup-note">此地图是独立离线测试来源，不是当前 mobile_pick 场景的 3D 地面或 world_sim 真值截图，也不是 SLAM 地图。保存成功也不会等于导航 Ready；导航执行、速度发布、热重规划本轮全部禁用。</p>
      </aside>
    </div>
  </section>;
}
