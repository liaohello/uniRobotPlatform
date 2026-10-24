import { describe, expect, it } from 'vitest';
import {
  OFFLINE_MAP, appendWaypoint, createOfflineDraft, degToRad, directionPixelAngle, loadOfflineSample,
  mapFromPixel, MIN_YAW_DRAG_M, moveWaypoint, normalizeRad, pixelFromMap, radToDeg,
  removeWaypoint, routeErrors, updateWaypoint, withOrder,
} from '../src/map/route';
import {
  RouteConflict, contentDigest, emptyStore, publishVersion, reloadDraft, saveDraft, versionsOf,
} from '../src/map/route-store';

const near = (a: number, b: number) => expect(a).toBeCloseTo(b, 9);

describe('angle normalisation', () => {
  it('wraps into [-pi, pi)', () => {
    near(normalizeRad(0), 0);
    near(normalizeRad(Math.PI), -Math.PI);
    near(normalizeRad(-Math.PI), -Math.PI);
    near(normalizeRad(3 * Math.PI), -Math.PI);
    near(normalizeRad(-3 * Math.PI), -Math.PI);
    near(normalizeRad(2 * Math.PI + 0.5), 0.5);
    near(normalizeRad(-0.5 - 2 * Math.PI), -0.5);
  });
  it('rejects non-finite angles instead of defaulting', () => {
    expect(() => normalizeRad(Number.NaN)).toThrow();
    expect(() => degToRad(Number.POSITIVE_INFINITY)).toThrow();
  });
  it('converts degrees on the wire in radians', () => {
    near(degToRad(180), -Math.PI);
    near(degToRad(-190), 2.9670597283903604);
    near(radToDeg(degToRad(-190)), 170);
    near(radToDeg(degToRad(355)), -5);
  });
});

describe('map raster <-> map frame', () => {
  it('keeps the image Y axis pointing down while map Y points up', () => {
    const topLeft = mapFromPixel(OFFLINE_MAP, 0, 0);
    const bottomLeft = mapFromPixel(OFFLINE_MAP, 0, OFFLINE_MAP.heightPx);
    near(topLeft.xM, OFFLINE_MAP.origin.xM);
    near(topLeft.yM, OFFLINE_MAP.origin.yM + OFFLINE_MAP.heightPx * OFFLINE_MAP.resolutionMPerPx);
    near(bottomLeft.yM, OFFLINE_MAP.origin.yM);
  });
  it('round-trips through a rotated and offset origin', () => {
    const rotated = { ...OFFLINE_MAP, origin: { xM: 3.5, yM: -1.25, yawRad: Math.PI / 3 } };
    for (const [u, v] of [[0, 0], [400, 300], [799, 1], [123, 512]] as const) {
      const map = mapFromPixel(rotated, u, v);
      const pixel = pixelFromMap(rotated, map.xM, map.yM);
      near(pixel.u, u); near(pixel.v, v);
    }
  });
  it('applies the origin pose, not the pixel index alone', () => {
    const unrotated = mapFromPixel({ ...OFFLINE_MAP, origin: { xM: 0, yM: 0, yawRad: 0 } }, 10, 20);
    near(unrotated.xM, 0.5);
    near(unrotated.yM, (OFFLINE_MAP.heightPx - 20) * OFFLINE_MAP.resolutionMPerPx);
    const rotated = mapFromPixel(OFFLINE_MAP, 0, 0);
    expect(rotated.xM).not.toBe(unrotated.xM);
  });
  it('resolves a direction arrow against the map origin rotation', () => {
    near(directionPixelAngle(OFFLINE_MAP, 0), 0);
    near(directionPixelAngle({ ...OFFLINE_MAP, origin: { ...OFFLINE_MAP.origin, yawRad: Math.PI / 2 } }, Math.PI / 2), 0);
    const rotatedMap = { ...OFFLINE_MAP, origin: { ...OFFLINE_MAP.origin, yawRad: Math.PI / 4 } };
    const tip = pixelFromMap(rotatedMap, 1 + Math.cos(0) * 0.9, 1 + Math.sin(0) * 0.9);
    const along = mapFromPixel(rotatedMap, tip.u, tip.v);
    near(along.xM, 1.9); near(along.yM, 1);
    expect(directionPixelAngle(rotatedMap, 0)).toBeCloseTo(Math.PI / 4, 9);
  });
});

describe('waypoint editing', () => {
  const draft = () => loadOfflineSample(createOfflineDraft());

  it('requires a position and an orientation on every PointGoal', () => {
    const empty = createOfflineDraft();
    expect(routeErrors(empty)).toContain('路线至少需要一个 PointGoal');
    const withYaw = draft();
    expect(routeErrors(withYaw)).toEqual([]);
    const missing = updateWaypoint(withYaw, withYaw.waypoints[1].id, { yawRad: null });
    expect(routeErrors(missing).join()).toContain('未设置朝向');
  });
  it('keeps stable IDs across reorder and renumbers order only', () => {
    const source = draft();
    const ids = source.waypoints.map((point) => point.id);
    const moved = moveWaypoint(source, ids[2], -1);
    expect(moved.waypoints.map((point) => point.id)).toEqual([ids[0], ids[2], ids[1]]);
    expect(moved.waypoints.map((point) => point.order)).toEqual([1, 2, 3]);
    expect(removeWaypoint(moved, ids[1]).waypoints.map((point) => point.id)).toEqual([ids[0], ids[2]]);
  });
  it('bounds the first and last reorder', () => {
    const source = draft();
    expect(moveWaypoint(source, source.waypoints[0].id, -1).waypoints[0].id).toBe(source.waypoints[0].id);
  });
  it('binds new points to the current map identity and version', () => {
    const added = appendWaypoint(createOfflineDraft(), 1, 2);
    expect(added.waypoints[0]).toMatchObject({ mapId: OFFLINE_MAP.mapId, mapVersion: OFFLINE_MAP.version, frame: 'map', yawRad: null });
    const staleMap = { ...added, waypoints: [{ ...added.waypoints[0], mapVersion: 'v0' }] };
    expect(routeErrors(staleMap).join()).toContain('地图绑定不一致');
  });
  it('treats an out-of-map placement check as structural only', () => {
    const outside = withOrder([{ id: 'wp-out', order: 1, mapId: OFFLINE_MAP.mapId, mapVersion: OFFLINE_MAP.version, frame: 'map', xM: 1e3, yM: 1e3, yawRad: 0 }]);
    expect(routeErrors({ ...createOfflineDraft(), waypoints: outside })).toEqual([]);
  });
  it('does not accept a zero-length yaw drag', () => {
    expect(MIN_YAW_DRAG_M).toBeGreaterThan(0);
  });
});

describe('local route store', () => {
  const valid = loadOfflineSample(createOfflineDraft());
  const empty = emptyStore();

  it('saves with a revision condition and refuses a stale base revision', () => {
    const first = saveDraft(empty, valid, 0);
    expect(first.saved).toMatchObject({ draftRevision: 1, authority: 'local_session_only' });
    expect(() => saveDraft(first.state, valid, 0)).toThrow(RouteConflict);
    try {
      saveDraft(first.state, valid, 0);
    } catch (error) {
      expect((error as RouteConflict).current.draftRevision).toBe(1);
    }
    const second = saveDraft(first.state, { ...valid, draftRevision: 1 }, 1);
    expect(second.saved.draftRevision).toBe(2);
  });
  it('publishes immutable versions without rewriting older ones', () => {
    const saved = saveDraft(empty, valid, 0).state;
    const v1 = publishVersion(saved, valid.routeId);
    const moved = moveWaypoint(valid, valid.waypoints[1].id, 1);
    const saved2 = saveDraft(v1.state, { ...moved, draftRevision: 1 }, 1).state;
    const v2 = publishVersion(saved2, valid.routeId);
    const versions = versionsOf(v2.state, valid.routeId);
    expect(versions.map((item) => item.version)).toEqual([1, 2]);
    expect(versions[0].waypoints.map((point) => point.id)).toEqual(valid.waypoints.map((point) => point.id));
    expect(versions[0].contentDigest).not.toBe(versions[1].contentDigest);
    expect(v2.state.adoptedRef).toBeNull();
    expect(reloadDraft(v2.state, valid.routeId)?.draftRevision).toBe(2);
  });
  it('treats a yaw edit as a content change', () => {
    const base = valid.waypoints;
    const yawed = updateWaypoint(valid, base[0].id, { yawRad: degToRad(90) }).waypoints;
    expect(contentDigest(base)).not.toBe(contentDigest(yawed));
    expect(contentDigest(base)).toBe(contentDigest(withOrder(base)));
    expect(contentDigest(base)).toBe(contentDigest(base.map((point) => ({ ...point, yawRad: normalizeRad(point.yawRad ?? 0) + 2 * Math.PI }))));
  });
  it('refuses to publish an unsaved draft', () => {
    expect(() => publishVersion(empty, valid.routeId)).toThrow('尚未保存');
  });
});
