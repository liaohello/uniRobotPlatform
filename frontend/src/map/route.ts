export type MapSource = 'offline_test_fixture' | 'live_backend';
export type MapCompatibility = 'compatible' | 'incompatible' | 'unverified' | 'not_applicable';
export interface MapOrigin { xM: number; yM: number; yawRad: number }
export interface MapRef { mapId: string; version: string; frame: 'map' }
export interface MapAuthority {
  source: string; live: boolean; testOnly: boolean; status: string; reason: string | null;
  interfaceProfile: string | null; manifestSha256: string; assetsVerified: boolean;
  image: { sha256: string; bytes: number; mediaType: string | null; relativePath: string } | null;
  thresholds: { occupied: number; free: number; negate: boolean };
  frames: { map: string; odom: string; base: string };
  coordinateConvention: { origin: string; imageColumn: string; imageRow: string; yawPositive: string; yawRange: string; cellCenter: string };
  compatibility: {
    g1RecipeSceneMatch: boolean | null; g1RecipeModelMatch: boolean | null; g1RecipeStatus: string;
    currentRuntimeStatus: string; navigationEligible: boolean; reasons: string[]; unverified: string[];
  };
  initialPrior: { xM: number; yM: number; yawRad: number } | null;
}
export interface MapMetadata {
  mapId: string; version: string; frame: 'map'; source: MapSource;
  imageUrl: string; widthPx: number; heightPx: number; resolutionMPerPx: number;
  origin: MapOrigin; imageYAxis: 'down';
  sceneCompatibility: { status: MapCompatibility; reason: string };
  authority?: MapAuthority;
}
export interface Waypoint {
  id: string; order: number; mapId: string; mapVersion: string; frame: 'map';
  xM: number; yM: number; yawRad: number | null;
}
export interface RouteDraft {
  routeId: string; draftRevision: number; label: string;
  map: MapMetadata; waypoints: Waypoint[];
}
export interface PixelPoint { u: number; v: number }
export interface MapPoint { xM: number; yM: number }
export const MIN_YAW_DRAG_M = 0.12;

export function normalizeRad(value: number): number {
  if (!Number.isFinite(value)) throw new Error('角度必须是有限数值');
  let angle = (value + Math.PI) % (2 * Math.PI);
  if (angle < 0) angle += 2 * Math.PI;
  return angle - Math.PI;
}
export function degToRad(value: number): number { return normalizeRad(value * Math.PI / 180); }
export function radToDeg(value: number): number { return normalizeRad(value) * 180 / Math.PI; }

// Map raster pixels: u grows right, v grows down. Map frame: x right, y up.
// The raster lower-left is at origin, rotated by origin.yawRad.
export function mapFromPixel(map: MapMetadata, u: number, v: number): MapPoint {
  const localX = u * map.resolutionMPerPx;
  const localY = (map.heightPx - v) * map.resolutionMPerPx;
  const c = Math.cos(map.origin.yawRad), s = Math.sin(map.origin.yawRad);
  return { xM: map.origin.xM + c * localX - s * localY, yM: map.origin.yM + s * localX + c * localY };
}
export function pixelFromMap(map: MapMetadata, xM: number, yM: number): PixelPoint {
  const dx = xM - map.origin.xM, dy = yM - map.origin.yM;
  const c = Math.cos(-map.origin.yawRad), s = Math.sin(-map.origin.yawRad);
  const localX = c * dx - s * dy, localY = s * dx + c * dy;
  return { u: localX / map.resolutionMPerPx, v: map.heightPx - localY / map.resolutionMPerPx };
}
export function directionPixelAngle(map: MapMetadata, yawRad: number): number {
  return -normalizeRad(yawRad - map.origin.yawRad);
}
export function waypointFromMap(map: MapMetadata, xM: number, yM: number): Waypoint {
  return { id: newWaypointId(), order: 0, mapId: map.mapId, mapVersion: map.version, frame: 'map', xM, yM, yawRad: null };
}
export function newWaypointId(): string {
  return `wp-${globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`}`;
}
export function withOrder(waypoints: Waypoint[]): Waypoint[] {
  return waypoints.map((point, index) => ({ ...point, order: index + 1 }));
}
export function appendWaypoint(draft: RouteDraft, xM: number, yM: number): RouteDraft {
  return { ...draft, waypoints: withOrder([...draft.waypoints, waypointFromMap(draft.map, xM, yM)]) };
}
export function updateWaypoint(draft: RouteDraft, id: string, patch: Partial<Pick<Waypoint, 'xM' | 'yM' | 'yawRad'>>): RouteDraft {
  return { ...draft, waypoints: draft.waypoints.map((point) => point.id === id ? { ...point, ...patch } : point) };
}
export function removeWaypoint(draft: RouteDraft, id: string): RouteDraft {
  return { ...draft, waypoints: withOrder(draft.waypoints.filter((point) => point.id !== id)) };
}
export function moveWaypoint(draft: RouteDraft, id: string, delta: -1 | 1): RouteDraft {
  const index = draft.waypoints.findIndex((point) => point.id === id);
  const next = index + delta;
  if (index < 0 || next < 0 || next >= draft.waypoints.length) return draft;
  const waypoints = [...draft.waypoints];
  [waypoints[index], waypoints[next]] = [waypoints[next], waypoints[index]];
  return { ...draft, waypoints: withOrder(waypoints) };
}
export function routeErrors(draft: RouteDraft): string[] {
  const errors: string[] = [];
  if (!draft.map) errors.push('地图不可用');
  const ids = new Set<string>();
  draft.waypoints.forEach((point, index) => {
    if (ids.has(point.id)) errors.push(`重复 waypoint ID ${point.id}`);
    ids.add(point.id);
    if (point.order !== index + 1) errors.push(`waypoint ${point.id} 顺序不连续`);
    if (point.mapId !== draft.map.mapId || point.mapVersion !== draft.map.version || point.frame !== draft.map.frame) errors.push(`waypoint ${point.id} 地图绑定不一致`);
    if (!Number.isFinite(point.xM) || !Number.isFinite(point.yM)) errors.push(`waypoint ${point.id} 坐标无效`);
    if (point.yawRad === null || !Number.isFinite(point.yawRad)) errors.push(`waypoint ${point.id} 未设置朝向`);
  });
  if (!draft.waypoints.length) errors.push('路线至少需要一个 PointGoal');
  return errors;
}
export const OFFLINE_MAP: MapMetadata = {
  mapId: 'offline-test-map',
  version: 'v1',
  frame: 'map',
  source: 'offline_test_fixture',
  imageUrl: './sample/offline-map.svg',
  widthPx: 800,
  heightPx: 600,
  resolutionMPerPx: 0.05,
  origin: { xM: -20, yM: -15, yawRad: 0 },
  imageYAxis: 'down',
  sceneCompatibility: { status: 'not_applicable', reason: '离线测试地图未绑定当前 mobile_pick 场景；不是 SLAM/导航地图' },
};
export function createOfflineDraft(): RouteDraft {
  return { routeId: 'route-local-draft', draftRevision: 1, label: '本地路线草案', map: OFFLINE_MAP, waypoints: [] };
}
export function loadOfflineSample(draft: RouteDraft): RouteDraft {
  const sample: Array<[number, number, number]> = [[-6, -3, 0.4], [-1, 2, 1.2], [5, 4, 2.4]];
  return { ...draft, waypoints: withOrder(sample.map(([xM, yM, yawRad]) => ({ ...waypointFromMap(draft.map, xM, yM), yawRad: normalizeRad(yawRad) }))) };
}
export function mapRefOf(map: MapMetadata): MapRef { return { mapId: map.mapId, version: map.version, frame: map.frame }; }
export function waypointsOf(map: MapMetadata, points: Waypoint[]): Waypoint[] {
  return withOrder(points.map((point) => ({ ...point, mapId: map.mapId, mapVersion: map.version, frame: map.frame })));
}
/** Content identity only: name, revisions and timestamps are excluded, matching the server digest inputs. */
export function routeContentEqual(a: Waypoint[], b: Waypoint[]): boolean {
  if (a.length !== b.length) return false;
  return a.every((point, index) => {
    const other = b[index];
    return point.id === other.id && point.order === other.order && point.mapId === other.mapId
      && point.mapVersion === other.mapVersion && point.frame === other.frame
      && Number(point.xM.toFixed(6)) === Number(other.xM.toFixed(6))
      && Number(point.yM.toFixed(6)) === Number(other.yM.toFixed(6))
      && Number((point.yawRad === null ? NaN : normalizeRad(point.yawRad)).toFixed(6))
        === Number((other.yawRad === null ? NaN : normalizeRad(other.yawRad)).toFixed(6));
  });
}
