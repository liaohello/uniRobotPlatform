import { useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';
import {
  MIN_YAW_DRAG_M, directionPixelAngle, mapFromPixel, normalizeRad, pixelFromMap,
  updateWaypoint, waypointFromMap, withOrder,
  type MapMetadata, type Waypoint,
} from './route';

interface Props {
  map: MapMetadata;
  waypoints: Waypoint[];
  selectedId: string | null;
  readOnly?: boolean;
  compact?: boolean;
  onChange?(waypoints: Waypoint[]): void;
  onSelect?(id: string | null): void;
}
interface ViewState { zoom: number; panX: number; panY: number; rotationDeg: number }
type Gesture =
  | { kind: 'pan'; pointerId: number; startX: number; startY: number; panX: number; panY: number; moved: boolean }
  | { kind: 'move'; pointerId: number; id: string }
  | { kind: 'yaw'; pointerId: number; id: string; committed: boolean };

const clampZoom = (value: number) => Math.max(0.35, Math.min(4, value));

export function MapWaypointEditor({ map, waypoints, selectedId, readOnly = false, compact = false, onChange, onSelect }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const groupRef = useRef<SVGGElement>(null);
  const gesture = useRef<Gesture | null>(null);
  const [view, setView] = useState<ViewState>({ zoom: 1, panX: 0, panY: 0, rotationDeg: 0 });
  const W = map.widthPx, H = map.heightPx;
  const pointToPixel = (xM: number, yM: number) => pixelFromMap(map, xM, yM);
  const eventToMap = (event: ReactPointerEvent) => {
    const svg = svgRef.current, group = groupRef.current;
    if (!svg || !group) return null;
    const point = svg.createSVGPoint(); point.x = event.clientX; point.y = event.clientY;
    const local = point.matrixTransform(group.getScreenCTM()!.inverse());
    return mapFromPixel(map, local.x, local.y);
  };
  const update = (next: Waypoint[]) => { if (!readOnly) onChange?.(withOrder(next)); };
  const beginPan = (event: ReactPointerEvent) => {
    if (event.button !== 0) return;
    svgRef.current?.setPointerCapture(event.pointerId);
    gesture.current = { kind: 'pan', pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, panX: view.panX, panY: view.panY, moved: false };
    onSelect?.(null);
  };
  const onBackgroundPointerDown = (event: ReactPointerEvent) => {
    if (event.button !== 0) return;
    event.preventDefault();
    beginPan(event);
  };
  const onPointerMove = (event: ReactPointerEvent) => {
    const current = gesture.current;
    if (!current || current.pointerId !== event.pointerId) return;
    if (current.kind === 'pan') {
      const dx = event.clientX - current.startX, dy = event.clientY - current.startY;
      if (Math.hypot(dx, dy) > 3) current.moved = true;
      setView((state) => ({ ...state, panX: current.panX + dx, panY: current.panY + dy }));
      return;
    }
    const mapPoint = eventToMap(event);
    if (!mapPoint) return;
    if (current.kind === 'move') {
      update(waypoints.map((point) => point.id === current.id ? { ...point, xM: mapPoint.xM, yM: mapPoint.yM } : point));
      return;
    }
    const point = waypoints.find((item) => item.id === current.id);
    if (!point) return;
    const dx = mapPoint.xM - point.xM, dy = mapPoint.yM - point.yM;
    if (Math.hypot(dx, dy) < MIN_YAW_DRAG_M) return;
    current.committed = true;
    update(waypoints.map((item) => item.id === current.id ? { ...item, yawRad: normalizeRad(Math.atan2(dy, dx)) } : item));
  };
  const endGesture = (event: ReactPointerEvent, cancelled = false) => {
    const current = gesture.current;
    if (!current || current.pointerId !== event.pointerId) return;
    if (current.kind === 'pan' && !current.moved && !cancelled && !readOnly) {
      const mapPoint = eventToMap(event);
      if (mapPoint) {
        const point = waypointFromMap(map, mapPoint.xM, mapPoint.yM);
        update([...waypoints, point]);
        onSelect?.(point.id);
      }
    }
    if (current.kind === 'yaw' && !current.committed && !cancelled) onSelect?.(current.id);
    gesture.current = null;
    try { svgRef.current?.releasePointerCapture(event.pointerId); } catch { /* pointer already released */ }
  };
  const onWaypointPointerDown = (event: ReactPointerEvent, id: string) => {
    if (event.button !== 0) return;
    event.stopPropagation(); event.preventDefault();
    onSelect?.(id);
    if (readOnly) return;
    svgRef.current?.setPointerCapture(event.pointerId);
    gesture.current = { kind: 'move', pointerId: event.pointerId, id };
  };
  const onYawPointerDown = (event: ReactPointerEvent, id: string) => {
    if (event.button !== 0 || readOnly) return;
    event.stopPropagation(); event.preventDefault();
    onSelect?.(id);
    svgRef.current?.setPointerCapture(event.pointerId);
    gesture.current = { kind: 'yaw', pointerId: event.pointerId, id, committed: false };
  };
  const rotate = (delta: number) => setView((state) => ({ ...state, rotationDeg: normalizeRad(state.rotationDeg * Math.PI / 180 + delta * Math.PI / 180) * 180 / Math.PI }));
  const zoom = (factor: number) => setView((state) => ({ ...state, zoom: clampZoom(state.zoom * factor) }));
  const resetView = () => setView({ zoom: 1, panX: 0, panY: 0, rotationDeg: 0 });
  const polyline = waypoints.map((point) => { const p = pointToPixel(point.xM, point.yM); return `${p.u},${p.v}`; }).join(' ');
  const stateJson = JSON.stringify({ mapId: map.mapId, version: map.version, frame: map.frame, view, waypoints });
  return <div className={`map-editor ${compact ? 'compact' : ''}`} data-map-editor>
    <div className="map-editor-toolbar" role="toolbar" aria-label="地图视图">
      <span className="map-source-chip" data-map-source={map.source}>{map.source === 'offline_test_fixture' ? '离线测试地图' : '后端地图'}</span>
      <button type="button" aria-label="地图放大" onClick={() => zoom(1.2)}>＋</button>
      <button type="button" aria-label="地图缩小" onClick={() => zoom(1 / 1.2)}>－</button>
      <button type="button" aria-label="地图左旋" onClick={() => rotate(-15)}>↺</button>
      <button type="button" aria-label="地图右旋" onClick={() => rotate(15)}>↻</button>
      <button type="button" aria-label="地图视图归零" onClick={resetView}>0°</button>
      <span className="map-view-readout">{Math.round(view.rotationDeg)}° · {view.zoom.toFixed(2)}×</span>
    </div>
    <svg ref={svgRef} className="map-canvas" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet"
      role="application" aria-label="2D 地图与 Waypoint 编辑器" data-map-width={W} data-map-height={H}
      onPointerDown={onBackgroundPointerDown} onPointerMove={onPointerMove}
      onPointerUp={(event) => endGesture(event)} onPointerCancel={(event) => endGesture(event, true)}
      onLostPointerCapture={(event) => endGesture(event, true)}
      onWheel={(event) => { event.preventDefault(); zoom(event.deltaY < 0 ? 1.1 : 1 / 1.1); }}>
      <g ref={groupRef} transform={`translate(${view.panX} ${view.panY}) rotate(${view.rotationDeg} ${W / 2} ${H / 2}) scale(${view.zoom})`}>
        <image href={map.imageUrl} x={0} y={0} width={W} height={H} preserveAspectRatio="none" style={{ pointerEvents: 'none' }} />
        {waypoints.length > 1 && <polyline points={polyline} fill="none" stroke="#e4b562" strokeWidth={2} strokeDasharray="7 6" opacity={0.85} pointerEvents="none"/>}
        {waypoints.map((point, index) => {
          const p = pointToPixel(point.xM, point.yM);
          const selected = point.id === selectedId;
          const yaw = point.yawRad;
          const direction = yaw !== null ? pixelFromMap(map, point.xM + Math.cos(yaw) * 0.9, point.yM + Math.sin(yaw) * 0.9) : null;
          const handle = direction ?? { u: p.u, v: p.v - 46 };
          const angle = yaw !== null ? directionPixelAngle(map, yaw) : 0;
          const tip = direction ? { u: direction.u + Math.cos(angle) * 13, v: direction.v + Math.sin(angle) * 13 } : null;
          const base = direction ? { u: direction.u - Math.cos(angle) * 11, v: direction.v - Math.sin(angle) * 11 } : null;
          return <g key={point.id} data-waypoint-id={point.id} data-waypoint-order={point.order} data-map-x={point.xM} data-map-y={point.yM}
            data-yaw-rad={point.yawRad ?? ''} className={`map-waypoint ${selected ? 'selected' : ''}`}
            onPointerDown={(event) => onWaypointPointerDown(event, point.id)}>
            <title>{`PointGoal ${index + 1} · ${point.xM.toFixed(2)}, ${point.yM.toFixed(2)} m · yaw ${point.yawRad === null ? '未设置' : `${(point.yawRad * 180 / Math.PI).toFixed(1)}°`}`}</title>
            {direction && <line x1={p.u} y1={p.v} x2={direction.u} y2={direction.v} stroke="#7de0c5" strokeWidth={3} pointerEvents="none"/>}
            {direction && tip && base && <polygon points={`${tip.u},${tip.v} ${base.u + Math.sin(angle) * 5},${base.v - Math.cos(angle) * 5} ${base.u - Math.sin(angle) * 5},${base.v + Math.cos(angle) * 5}`} fill="#7de0c5" pointerEvents="none"/>}
            {yaw === null && <><line x1={p.u} y1={p.v} x2={handle.u} y2={handle.v} stroke="#8b9a86" strokeWidth={1.5} strokeDasharray="4 4" pointerEvents="none"/><text x={handle.u + 4} y={handle.v - 3} fill="#b4b48a" fontSize={12} pointerEvents="none">?</text></>}
            <circle cx={p.u} cy={p.v} r={15} fill="transparent"/>
            <circle cx={p.u} cy={p.v} r={selected ? 8 : 6} className="waypoint-dot"/>
            <text x={p.u + 11} y={p.v - 9} fill="#d9edf2" fontSize={13} pointerEvents="none">{index + 1}</text>
            {!readOnly && <circle cx={handle.u} cy={handle.v} r={10} fill="#1c333b" stroke="#9bd8c5" strokeWidth={2} className="yaw-handle" data-yaw-handle={point.id}
              onPointerDown={(event) => onYawPointerDown(event, point.id)}><title>拖动设置朝向；零长度拖动不会确认</title></circle>}
          </g>;
        })}
      </g>
    </svg>
    <div className="map-editor-hint">{readOnly ? '只读预览：滚轮缩放，拖动平移；方向与位置来自本地草案。' : '点击地图放置 PointGoal；拖动点移动；拖动方向手柄设置朝向；空白拖动平移。'}</div>
    <output hidden data-map-editor-state={stateJson}/>
  </div>;
}
