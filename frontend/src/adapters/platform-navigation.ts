import { ApiError, parseError } from './platform-config';
import { mapRefOf, normalizeRad, waypointsOf, type MapMetadata, type MapRef, type RouteDraft, type Waypoint } from '../map/route';

export interface MapAssetRefDto { role: string; relative_path: string; sha256: string; bytes: number; media_type: string | null }
export interface MapOriginDto { x_m: number; y_m: number; yaw_rad: number }
export interface MapConventionDto {
  origin: string; image_column: string; image_row: string;
  yaw_positive: string; yaw_range: string; cell_center: string;
}
export interface MapCompatibilityDto {
  g1_recipe_scene_match: boolean | null; g1_recipe_model_match: boolean | null;
  g1_recipe_status: string; current_runtime_status: string;
  navigation_eligible: boolean; reasons: string[]; unverified: string[];
}
export interface MapVersionDto {
  schema_version: string; map_id: string; version: string; frame: string;
  status: string; reason: string | null; source: string; live: boolean; test_only: boolean;
  interface_profile: string | null; map_frame: string; odom_frame: string; base_frame: string;
  resolution_m: number; width_px: number; height_px: number; origin: MapOriginDto;
  occupied_thresh: number; free_thresh: number; negate: boolean;
  image: MapAssetRefDto | null; assets: MapAssetRefDto[];
  manifest_sha256: string; assets_verified: boolean;
  scene_id: string | null; model_sha256: string | null;
  navigation_profile_sha256: string | null; sensor_profile_sha256: string | null; scan_config_sha256: string | null;
  initial_prior: (MapOriginDto & { covariance?: number[] }) | null;
  coordinate_convention: MapConventionDto; compatibility: MapCompatibilityDto;
}
export interface MapListDto {
  schema_version: string; source: string; live: boolean; supported: boolean;
  reason: string | null; maps: MapVersionDto[];
}
export interface MapRefDto { map_id: string; version: string; frame: string }
export interface WaypointDto { id: string; order: number; x_m: number; y_m: number; yaw_rad: number }
export interface RouteCheckDto { key: string; status: string; detail: string; waypoint_id: string | null }
export interface RouteValidationDto {
  checks: RouteCheckDto[]; pose_checks_passed: boolean;
  navigation_eligible: boolean; adoption_supported: boolean; execution_supported: boolean;
  g1_navigation_supported: boolean; display_supported: boolean;
  arrival_acceptance: string; tolerance_source: string | null;
  unsupported_checks: string[]; reasons: string[];
}
export interface RouteDraftDto {
  schema_version: string; route_id: string; draft_revision: number; name: string;
  map_ref: MapRefDto; waypoints: WaypointDto[]; content_digest: string;
  validation: RouteValidationDto; created_at: string; updated_at: string;
}
export interface RouteVersionDto {
  schema_version: string; route_id: string; version: string; name: string;
  map_ref: MapRefDto; waypoints: WaypointDto[]; content_digest: string;
  validation: RouteValidationDto; created_at: string; updated_at: string;
}
export interface RouteVersionSummaryDto {
  route_id: string; version: string; content_digest: string;
  created_at: string; waypoint_count: number; map_ref: MapRefDto;
}
export interface RouteVersionListDto { route_id: string; versions: RouteVersionSummaryDto[] }
export interface PublishResultDto { route_version: RouteVersionDto; reused: boolean }
export interface CreateRouteDraftDto { name: string; map_ref: MapRefDto; waypoints: WaypointDto[] }
export interface SaveRouteDraftDto extends CreateRouteDraftDto { base_revision: number }

export interface RouteValidationView {
  checks: RouteCheckDto[]; poseChecksPassed: boolean; navigationEligible: boolean;
  adoptionSupported: boolean; executionSupported: boolean; g1NavigationSupported: boolean;
  displaySupported: boolean; arrivalAcceptance: string; toleranceSource: string | null;
  unsupportedChecks: string[]; reasons: string[];
}
export interface ServerDraftView {
  routeId: string; draftRevision: number; name: string; mapRef: MapRef; waypoints: Waypoint[];
  contentDigest: string; validation: RouteValidationView; createdAt: string; updatedAt: string;
}
export interface RouteVersionView {
  routeId: string; version: string; name: string; mapRef: MapRef; waypoints: Waypoint[];
  contentDigest: string; createdAt: string; validation: RouteValidationView;
  navigationEligible: boolean; adoptionSupported: boolean; executionSupported: boolean; displaySupported: boolean;
}
export class MapContractError extends Error {
  constructor(readonly code: 'frame_mismatch' | 'convention_unsupported' | 'image_missing', message: string) { super(message); this.name = 'MapContractError'; }
}
export class RevisionConflict {
  constructor(readonly code: string, readonly serverRevision: number | null, readonly message: string) {}
}

function toRef(dto: MapRefDto): MapRef {
  if (dto.frame !== 'map') throw new MapContractError('frame_mismatch', `map_ref.frame=${dto.frame}，编辑器只按 map frame 换算`);
  return { mapId: dto.map_id, version: dto.version, frame: 'map' };
}
function toWaypoints(list: WaypointDto[], ref: MapRef): Waypoint[] {
  return list.map((item) => ({
    id: item.id, order: item.order, mapId: ref.mapId, mapVersion: ref.version, frame: ref.frame,
    xM: item.x_m, yM: item.y_m, yawRad: normalizeRad(item.yaw_rad),
  }));
}
function toValidation(dto: RouteValidationDto): RouteValidationView {
  return {
    checks: dto.checks, poseChecksPassed: dto.pose_checks_passed, navigationEligible: dto.navigation_eligible,
    adoptionSupported: dto.adoption_supported, executionSupported: dto.execution_supported,
    g1NavigationSupported: dto.g1_navigation_supported, displaySupported: dto.display_supported,
    arrivalAcceptance: dto.arrival_acceptance, toleranceSource: dto.tolerance_source,
    unsupportedChecks: dto.unsupported_checks, reasons: dto.reasons,
  };
}

export function mapDtoToMetadata(dto: MapVersionDto): MapMetadata {
  if (dto.frame !== 'map') throw new MapContractError('frame_mismatch', `地图 frame=${dto.frame}，本编辑器只接受 map frame`);
  if (dto.coordinate_convention.image_row !== '-Y') {
    throw new MapContractError('convention_unsupported', `图像行方向 ${dto.coordinate_convention.image_row} 不是 -Y，不能假定行序`);
  }
  const status = dto.compatibility.g1_recipe_status === 'passed' ? 'compatible'
    : dto.compatibility.g1_recipe_status === 'failed' ? 'incompatible' : 'unverified';
  return {
    mapId: dto.map_id, version: dto.version, frame: 'map', source: 'live_backend',
    imageUrl: '', widthPx: dto.width_px, heightPx: dto.height_px, resolutionMPerPx: dto.resolution_m,
    origin: { xM: dto.origin.x_m, yM: dto.origin.y_m, yawRad: dto.origin.yaw_rad }, imageYAxis: 'down',
    sceneCompatibility: { status, reason: dto.compatibility.reasons.join('；') || dto.reason || '未给出原因' },
    authority: {
      source: dto.source, live: dto.live, testOnly: dto.test_only, status: dto.status, reason: dto.reason,
      interfaceProfile: dto.interface_profile, manifestSha256: dto.manifest_sha256, assetsVerified: dto.assets_verified,
      image: dto.image ? { sha256: dto.image.sha256, bytes: dto.image.bytes, mediaType: dto.image.media_type, relativePath: dto.image.relative_path } : null,
      thresholds: { occupied: dto.occupied_thresh, free: dto.free_thresh, negate: dto.negate },
      frames: { map: dto.map_frame, odom: dto.odom_frame, base: dto.base_frame },
      coordinateConvention: {
        origin: dto.coordinate_convention.origin, imageColumn: dto.coordinate_convention.image_column,
        imageRow: dto.coordinate_convention.image_row, yawPositive: dto.coordinate_convention.yaw_positive,
        yawRange: dto.coordinate_convention.yaw_range, cellCenter: dto.coordinate_convention.cell_center,
      },
      compatibility: {
        g1RecipeSceneMatch: dto.compatibility.g1_recipe_scene_match, g1RecipeModelMatch: dto.compatibility.g1_recipe_model_match,
        g1RecipeStatus: dto.compatibility.g1_recipe_status, currentRuntimeStatus: dto.compatibility.current_runtime_status,
        navigationEligible: dto.compatibility.navigation_eligible, reasons: dto.compatibility.reasons, unverified: dto.compatibility.unverified,
      },
      initialPrior: dto.initial_prior ? { xM: dto.initial_prior.x_m, yM: dto.initial_prior.y_m, yawRad: dto.initial_prior.yaw_rad } : null,
    },
  };
}

export function draftDtoToView(dto: RouteDraftDto): ServerDraftView {
  const mapRef = toRef(dto.map_ref);
  return {
    routeId: dto.route_id, draftRevision: dto.draft_revision, name: dto.name, mapRef,
    waypoints: toWaypoints(dto.waypoints, mapRef), contentDigest: dto.content_digest,
    validation: toValidation(dto.validation), createdAt: dto.created_at, updatedAt: dto.updated_at,
  };
}
export function versionDtoToView(dto: RouteVersionDto): RouteVersionView {
  const mapRef = toRef(dto.map_ref);
  return {
    routeId: dto.route_id, version: dto.version, name: dto.name, mapRef,
    waypoints: toWaypoints(dto.waypoints, mapRef), contentDigest: dto.content_digest, createdAt: dto.created_at,
    validation: toValidation(dto.validation), navigationEligible: dto.validation.navigation_eligible,
    adoptionSupported: dto.validation.adoption_supported, executionSupported: dto.validation.execution_supported,
    displaySupported: dto.validation.display_supported,
  };
}
export function summaryDtoToRef(dto: RouteVersionSummaryDto): { version: string; contentDigest: string; createdAt: string; waypointCount: number; mapRef: MapRef } {
  return { version: dto.version, contentDigest: dto.content_digest, createdAt: dto.created_at, waypointCount: dto.waypoint_count, mapRef: toRef(dto.map_ref) };
}
/** Server draft into an editable working copy bound to the map identity it was created against. */
export function draftDtoToWorking(dto: RouteDraftDto, map: MapMetadata): RouteDraft {
  const ref = toRef(dto.map_ref);
  return { routeId: dto.route_id, draftRevision: dto.draft_revision, label: dto.name, map, waypoints: toWaypoints(dto.waypoints, ref) };
}
export function workingToPayload(draft: RouteDraft, name: string): CreateRouteDraftDto {
  const missing = draft.waypoints.filter((point) => point.yawRad === null || !Number.isFinite(point.yawRad));
  if (missing.length) throw new Error(`${missing.length} 个 PointGoal 缺少朝向，后端要求 yaw_rad 必填`);
  if (!draft.waypoints.length) throw new Error('路线至少需要一个 PointGoal');
  return {
    name, map_ref: { map_id: draft.map.mapId, version: draft.map.version, frame: draft.map.frame },
    waypoints: waypointsOf(draft.map, draft.waypoints).map((point) => ({
      id: point.id, order: point.order, x_m: Number(point.xM.toFixed(6)), y_m: Number(point.yM.toFixed(6)),
      yaw_rad: normalizeRad(point.yawRad as number),
    })),
  };
}
export function conflictOf(error: unknown): RevisionConflict | null {
  if (!(error instanceof ApiError) || error.status !== 409) return null;
  const detail = error.detail as { code?: string; message?: string; current_revision?: number } | null;
  return new RevisionConflict(String(detail?.code ?? error.code), typeof detail?.current_revision === 'number' ? detail.current_revision : null,
    String(detail?.message ?? error.message));
}

async function json<T>(path: string, init: RequestInit, signal: AbortSignal): Promise<T> {
  const response = await fetch(path, { ...init, signal, cache: 'no-store', headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...(init.headers ?? {}) } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw parseError(response.status, response.statusText, body);
  return body as T;
}
/** The map raster is bytes, not JSON: only a non-OK response carries the platform error envelope. */
async function bytes(path: string, signal: AbortSignal): Promise<Uint8Array> {
  const response = await fetch(path, { method: 'GET', signal, cache: 'no-store' });
  if (!response.ok) throw parseError(response.status, response.statusText, await response.json().catch(() => null));
  return new Uint8Array(await response.arrayBuffer());
}
const segment = (value: string) => encodeURIComponent(value);

export class PlatformNavigationApi {
  listMaps(signal: AbortSignal) { return json<MapListDto>('/api/v1/maps', { method: 'GET' }, signal); }
  getMapVersion(mapId: string, version: string, signal: AbortSignal) {
    return json<MapVersionDto>(`/api/v1/maps/${segment(mapId)}/versions/${segment(version)}?frame=map`, { method: 'GET' }, signal);
  }
  mapImage(path: string, version: string, sha256: string, signal: AbortSignal) {
    return bytes(`/api/v1/maps/${segment(path)}/versions/${segment(version)}/image?sha256=${encodeURIComponent(sha256)}`, signal);
  }
  createDraft(body: CreateRouteDraftDto, signal: AbortSignal) {
    return json<RouteDraftDto>('/api/v1/route-drafts', { method: 'POST', body: JSON.stringify(body) }, signal);
  }
  getDraft(routeId: string, signal: AbortSignal) {
    return json<RouteDraftDto>(`/api/v1/route-drafts/${segment(routeId)}`, { method: 'GET' }, signal);
  }
  saveDraft(routeId: string, body: SaveRouteDraftDto, signal: AbortSignal) {
    return json<RouteDraftDto>(`/api/v1/route-drafts/${segment(routeId)}`, { method: 'PUT', body: JSON.stringify(body) }, signal);
  }
  publishDraft(routeId: string, baseRevision: number, signal: AbortSignal) {
    return json<PublishResultDto>(`/api/v1/route-drafts/${segment(routeId)}/publish`, { method: 'POST', body: JSON.stringify({ base_revision: baseRevision }) }, signal);
  }
  listVersions(routeId: string, signal: AbortSignal) {
    return json<RouteVersionListDto>(`/api/v1/routes/${segment(routeId)}/versions`, { method: 'GET' }, signal);
  }
  getVersion(routeId: string, version: string, signal: AbortSignal) {
    return json<RouteVersionDto>(`/api/v1/routes/${segment(routeId)}/versions/${segment(version)}`, { method: 'GET' }, signal);
  }
}
export function mapRefOfMetadata(map: MapMetadata): MapRef { return mapRefOf(map); }
