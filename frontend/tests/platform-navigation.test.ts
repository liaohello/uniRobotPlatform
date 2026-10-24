import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  PlatformNavigationApi, conflictOf, draftDtoToView, mapDtoToMetadata, versionDtoToView, workingToPayload,
  type MapVersionDto, type RouteDraftDto,
} from '../src/adapters/platform-navigation';
import { createOfflineDraft, updateWaypoint, type Waypoint } from '../src/map/route';
import { ApiError, describeApiError } from '../src/adapters/platform-config';

const calls: { url: string; init: RequestInit }[] = [];
function reply(status: number, body: unknown) {
  vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    return { ok: status < 400, status, statusText: 'fixture', json: async () => body, arrayBuffer: async () => new Uint8Array([1, 2, 3]).buffer } as Response;
  }));
}
afterEach(() => { vi.unstubAllGlobals(); calls.length = 0; });

const mapDto: MapVersionDto = {
  schema_version: 'unirobot-map-version-1', map_id: 'map_room_a_g3b_release_v1', version: 'v1', frame: 'map',
  status: 'available', reason: null, source: 'g3b_historical_offline', live: false, test_only: false,
  interface_profile: 'g4a1-1.0', map_frame: 'map', odom_frame: 'odom', base_frame: 'base_link',
  resolution_m: 0.05, width_px: 59, height_px: 47, origin: { x_m: -1.2, y_m: -1.15, yaw_rad: 0 },
  occupied_thresh: 0.65, free_thresh: 0.196, negate: false,
  image: { role: 'occupancy_grid', relative_path: 'map.pgm', sha256: '0'.repeat(64), bytes: 2786, media_type: 'image/x-portable-graymap' },
  assets: [], manifest_sha256: 'a'.repeat(64), assets_verified: true,
  scene_id: 'mobile_pick', model_sha256: 'b'.repeat(64), navigation_profile_sha256: null,
  sensor_profile_sha256: null, scan_config_sha256: null, initial_prior: null,
  coordinate_convention: {
    origin: 'image_lower_left_corner_in_map_frame', image_column: '+X', image_row: '-Y',
    yaw_positive: 'counterclockwise_from_+X_to_+Y', yaw_range: '[-pi,pi)', cell_center: 'col+0.5,row+0.5',
  },
  compatibility: {
    g1_recipe_scene_match: false, g1_recipe_model_match: false, g1_recipe_status: 'failed',
    current_runtime_status: 'not_checked', navigation_eligible: false,
    reasons: ['scene_id differs from the G1 recipe'], unverified: ['deployed runtime'],
  },
};
const validation = {
  checks: [{ key: 'waypoint_pose:wp-a', status: 'passed', detail: 'free cell', waypoint_id: 'wp-a' }],
  pose_checks_passed: true, navigation_eligible: false, adoption_supported: false,
  execution_supported: false, g1_navigation_supported: false, display_supported: true,
  arrival_acceptance: 'not_checked', tolerance_source: null, unsupported_checks: ['footprint'], reasons: [],
};
const draftDto: RouteDraftDto = {
  schema_version: 'unirobot-route-draft-1', route_id: 'route-test', draft_revision: 2, name: '测试路线',
  map_ref: { map_id: 'map_room_a_g3b_release_v1', version: 'v1', frame: 'map' },
  waypoints: [{ id: 'wp-b', order: 1, x_m: -0.825, y_m: 1.075, yaw_rad: 0.5 }, { id: 'wp-a', order: 2, x_m: -0.875, y_m: 1.075, yaw_rad: 0 }],
  content_digest: 'c'.repeat(64), validation, created_at: '2026-10-24T11:00:00+00:00', updated_at: '2026-10-24T11:05:00+00:00',
};

describe('map and route wire', () => {
  it('calls only the endpoints 18953 actually exposes', async () => {
    const signal = new AbortController().signal;
    reply(200, { schema_version: 'unirobot-map-catalog-1', source: 'local_map_packages', live: false, supported: true, reason: null, maps: [mapDto] });
    const api = new PlatformNavigationApi();
    await expect(api.listMaps(signal)).resolves.toMatchObject({ source: 'local_map_packages' });
    reply(200, mapDto);
    await api.getMapVersion('map_room_a_g3b_release_v1', 'v1', signal);
    reply(200, draftDto);
    await api.getDraft('route-test', signal);
    reply(200, { route_id: 'route-test', versions: [] });
    await api.listVersions('route-test', signal);
    reply(200, draftDto);
    await api.getVersion('route-test', 'v2', signal);
    expect(calls.map((call) => `${call.init.method} ${call.url}`)).toEqual([
      'GET /api/v1/maps',
      'GET /api/v1/maps/map_room_a_g3b_release_v1/versions/v1?frame=map',
      'GET /api/v1/route-drafts/route-test',
      'GET /api/v1/routes/route-test/versions',
      'GET /api/v1/routes/route-test/versions/v2',
    ]);
  });
  it('reads the raster by declared digest and writes snake_case payloads', async () => {
    const signal = new AbortController().signal;
    reply(200, []);
    await new PlatformNavigationApi().mapImage('map_room_a_g3b_release_v1', 'v1', '0'.repeat(64), signal);
    expect(calls[0].url).toBe('/api/v1/maps/map_room_a_g3b_release_v1/versions/v1/image?sha256=' + '0'.repeat(64));
    reply(201, draftDto);
    await new PlatformNavigationApi().createDraft({
      name: '测试路线', map_ref: { map_id: 'm', version: 'v1', frame: 'map' },
      waypoints: [{ id: 'wp-a', order: 1, x_m: 1, y_m: 2, yaw_rad: 0 }],
    }, signal);
    expect(JSON.parse(calls[1].init.body as string)).toEqual({
      name: '测试路线', map_ref: { map_id: 'm', version: 'v1', frame: 'map' },
      waypoints: [{ id: 'wp-a', order: 1, x_m: 1, y_m: 2, yaw_rad: 0 }],
    });
    reply(200, draftDto);
    await new PlatformNavigationApi().saveDraft('route-test', {
      name: '测试路线', map_ref: { map_id: 'm', version: 'v1', frame: 'map' },
      waypoints: [], base_revision: 2,
    }, signal);
    expect(JSON.parse(calls[2].init.body as string)).toMatchObject({ base_revision: 2 });
    reply(200, { route_version: { ...draftDto, version: 'v3' }, reused: false });
    await new PlatformNavigationApi().publishDraft('route-test', 3, signal);
    expect(calls[3].url).toBe('/api/v1/route-drafts/route-test/publish');
    expect(JSON.parse(calls[3].init.body as string)).toEqual({ base_revision: 3 });
  });
});

describe('DTO to view model conversion', () => {
  it('maps the declared coordinate convention into editor metadata', () => {
    const map = mapDtoToMetadata(mapDto);
    expect(map).toMatchObject({ mapId: 'map_room_a_g3b_release_v1', version: 'v1', frame: 'map', source: 'live_backend', widthPx: 59, heightPx: 47, resolutionMPerPx: 0.05, imageYAxis: 'down' });
    expect(map.origin).toEqual({ xM: -1.2, yM: -1.15, yawRad: 0 });
    expect(map.sceneCompatibility.status).toBe('incompatible');
    expect(map.authority).toMatchObject({ source: 'g3b_historical_offline', live: false, testOnly: false, assetsVerified: true, manifestSha256: 'a'.repeat(64) });
    expect(map.authority?.compatibility.navigationEligible).toBe(false);
    expect(map.authority?.coordinateConvention.cellCenter).toBe('col+0.5,row+0.5');
    expect(map.imageUrl).toBe('');
  });
  it('refuses frames and row directions it cannot convert', () => {
    expect(() => mapDtoToMetadata({ ...mapDto, frame: 'odom' })).toThrowError(/map frame/);
    expect(() => mapDtoToMetadata({ ...mapDto, coordinate_convention: { ...mapDto.coordinate_convention, image_row: '+Y' } })).toThrowError(/图像行方向/);
  });
  it('converts drafts with backend authority for revision and digest', () => {
    const view = draftDtoToView(draftDto);
    expect(view).toMatchObject({ routeId: 'route-test', draftRevision: 2, name: '测试路线', contentDigest: 'c'.repeat(64) });
    expect(view.mapRef).toEqual({ mapId: 'map_room_a_g3b_release_v1', version: 'v1', frame: 'map' });
    expect(view.waypoints[0]).toMatchObject({ id: 'wp-b', order: 1, xM: -0.825, yM: 1.075, mapId: 'map_room_a_g3b_release_v1' });
    expect(view.waypoints[1].yawRad).toBe(0);
    expect(view.validation).toMatchObject({ poseChecksPassed: true, navigationEligible: false, adoptionSupported: false, executionSupported: false, arrivalAcceptance: 'not_checked', unsupportedChecks: ['footprint'] });
    expect(() => draftDtoToView({ ...draftDto, map_ref: { map_id: 'm', version: 'v1', frame: 'odom' } })).toThrowError(/map frame/);
  });
  it('keeps version documents fixed and eligibility false', () => {
    const version = versionDtoToView({ ...draftDto, version: 'v2' });
    expect(version).toMatchObject({ version: 'v2', contentDigest: 'c'.repeat(64), navigationEligible: false, adoptionSupported: false, executionSupported: false, displaySupported: true });
    expect(version.waypoints.map((point) => point.id)).toEqual(['wp-b', 'wp-a']);
  });
  it('rejects unset orientation on the way out and normalises yaw radians', () => {
    const base = createOfflineDraft();
    const point: Waypoint = { id: 'wp-a', order: 1, mapId: base.map.mapId, mapVersion: base.map.version, frame: 'map', xM: 1.23456789, yM: 0.5, yawRad: null };
    const withPoint = { ...base, waypoints: [point] };
    expect(() => workingToPayload(withPoint, 'x')).toThrowError(/缺少朝向/);
    const yawed = { ...withPoint, waypoints: [{ ...point, yawRad: 2 * Math.PI + 0.5 }] };
    const payload = workingToPayload(yawed, 'x');
    expect(payload.waypoints[0]).toMatchObject({ id: 'wp-a', order: 1, x_m: 1.234568, y_m: 0.5, yaw_rad: 0.5 });
    expect(payload.map_ref).toEqual({ map_id: base.map.mapId, version: base.map.version, frame: 'map' });
    const explicitZero = { ...withPoint, waypoints: [{ ...point, yawRad: 0 }] };
    expect(workingToPayload(explicitZero, 'x').waypoints[0].yaw_rad).toBe(0);
    const negativePole = { ...withPoint, waypoints: [{ ...point, yawRad: Math.PI }] };
    expect(workingToPayload(negativePole, 'x').waypoints[0].yaw_rad).toBe(-Math.PI);
    expect(() => workingToPayload({ ...base, waypoints: [] }, 'x')).toThrowError(/至少需要一个 PointGoal/);
  });
});

describe('route error envelopes', () => {
  it('reads the real 409 revision conflict', async () => {
    reply(409, { detail: { code: 'route_draft_revision_conflict', message: 'route draft changed in another host; reload before saving/publishing', current_revision: 7 } });
    const error = await new PlatformNavigationApi().getDraft('route-test', new AbortController().signal).catch((cause) => cause);
    expect(error).toBeInstanceOf(ApiError);
    const clash = conflictOf(error);
    expect(clash).toMatchObject({ code: 'route_draft_revision_conflict', serverRevision: 7 });
    expect(describeApiError(error)).toContain('route_draft_revision_conflict');
  });
  it('keeps missing map and route resources explicit', async () => {
    reply(404, { detail: { code: 'map_version_not_found', message: 'map nope version 999 is not declared' } });
    await expect(new PlatformNavigationApi().getMapVersion('nope', 'v999', new AbortController().signal)).rejects.toMatchObject({ code: 'map_version_not_found' });
    reply(422, { detail: [{ loc: ['body', 'waypoints', 0, 'yaw_rad'], msg: 'field required — yaw_rad is required for every waypoint', type: 'missing' }] });
    const error = await new PlatformNavigationApi().createDraft({ name: 'x', map_ref: { map_id: 'm', version: 'v1', frame: 'map' }, waypoints: [] }, new AbortController().signal).catch((cause) => cause);
    expect(conflictOf(error)).toBeNull();
    expect(describeApiError(error)).toContain('yaw_rad');
  });
});
