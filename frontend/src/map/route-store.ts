import type { RouteDraft, Waypoint } from './route';
import { normalizeRad, withOrder } from './route';

export type StoreAuthority = 'local_session_only';
export interface MapRef { mapId: string; mapVersion: string; frame: 'map' }
export interface StoredDraft {
  routeId: string; draftRevision: number; label: string;
  map: RouteDraft['map']; waypoints: Waypoint[]; authority: StoreAuthority;
}
export interface RouteVersion {
  routeId: string; version: number; contentDigest: string; savedDraftRevision: number;
  mapRef: MapRef; waypoints: Waypoint[]; created_at: string; authority: StoreAuthority;
}
export interface RouteStoreState {
  authority: StoreAuthority;
  drafts: Record<string, StoredDraft>;
  versions: RouteVersion[];
  adoptedRef: { routeId: string; version: number } | null;
}
export interface RouteSaveResult { state: RouteStoreState; saved: StoredDraft }
export interface RoutePublishResult { state: RouteStoreState; saved: RouteVersion }

export function emptyStore(): RouteStoreState {
  return { authority: 'local_session_only', drafts: {}, versions: [], adoptedRef: null };
}

export class RouteConflict extends Error {
  constructor(readonly expected: number, readonly current: StoredDraft) {
    super(`draftRevision 条件不匹配：期望 ${expected}，服务端为 ${current.draftRevision}`);
    this.name = 'RouteConflict';
  }
}

function canonical(waypoints: Waypoint[]): string {
  return JSON.stringify(waypoints.map((point) => [
    point.id, point.order, point.mapId, point.mapVersion, point.frame,
    Number(point.xM.toFixed(6)), Number(point.yM.toFixed(6)),
    point.yawRad === null ? null : Number(normalizeRad(point.yawRad).toFixed(6)),
  ]));
}

export function contentDigest(waypoints: Waypoint[]): string {
  let a = 0x811c9dc5, b = 0x01000193;
  const text = canonical(waypoints);
  for (let i = 0; i < text.length; i += 1) {
    a = Math.imul(a ^ text.charCodeAt(i), 16777619) >>> 0;
    b = Math.imul(b + text.charCodeAt(i) + i, 2246822519) >>> 0;
  }
  return `local-${a.toString(16).padStart(8, '0')}${b.toString(16).padStart(8, '0')}`;
}

function bound(draft: RouteDraft): StoredDraft {
  return {
    routeId: draft.routeId, draftRevision: draft.draftRevision, label: draft.label,
    map: draft.map, waypoints: withOrder(draft.waypoints), authority: 'local_session_only',
  };
}

/** Saving is a revision-conditioned write: a stale baseRevision is refused and the local edit is kept by the caller. */
export function saveDraft(state: RouteStoreState, draft: RouteDraft, baseRevision: number): RouteSaveResult {
  const existing = state.drafts[draft.routeId];
  const current = existing?.draftRevision ?? 0;
  if (current !== baseRevision) throw new RouteConflict(baseRevision, existing ?? bound(draft));
  const saved = { ...bound(draft), draftRevision: current + 1 };
  return { state: { ...state, drafts: { ...state.drafts, [saved.routeId]: saved } }, saved };
}

/** Publishing freezes an immutable version; it never rewrites older versions and never changes the adopted reference. */
export function publishVersion(state: RouteStoreState, routeId: string): RoutePublishResult {
  const draft = state.drafts[routeId];
  if (!draft) throw new Error('路线草案尚未保存，不能发布 Route Version');
  const version: RouteVersion = {
    routeId, version: state.versions.filter((item) => item.routeId === routeId).length + 1,
    contentDigest: contentDigest(draft.waypoints), savedDraftRevision: draft.draftRevision,
    mapRef: { mapId: draft.map.mapId, mapVersion: draft.map.version, frame: draft.map.frame },
    waypoints: withOrder(draft.waypoints), created_at: new Date().toISOString(), authority: 'local_session_only',
  };
  return { state: { ...state, versions: [...state.versions, version] }, saved: version };
}

export function reloadDraft(state: RouteStoreState, routeId: string): StoredDraft | null {
  return state.drafts[routeId] ?? null;
}
export function versionsOf(state: RouteStoreState, routeId: string): RouteVersion[] {
  return state.versions.filter((item) => item.routeId === routeId);
}
export function isStoreEmpty(state: RouteStoreState): boolean {
  return Object.keys(state.drafts).length === 0 && state.versions.length === 0;
}
