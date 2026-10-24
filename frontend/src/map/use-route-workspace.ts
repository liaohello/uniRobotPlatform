import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ApiError, describeApiError } from '../adapters/platform-config';
import {
  PlatformNavigationApi, conflictOf, draftDtoToView, draftDtoToWorking, mapDtoToMetadata,
  summaryDtoToRef, versionDtoToView, workingToPayload,
  type MapListDto, type MapVersionDto, type RevisionConflict, type RouteDraftDto, type RouteVersionView, type ServerDraftView,
} from '../adapters/platform-navigation';
import { PgmError, assertDims, assertDigest, parsePgm, rasterToPngDataUrl, sha256Hex } from './pgm';
import {
  OFFLINE_MAP, createOfflineDraft, mapRefOf, routeContentEqual, routeErrors,
  type MapMetadata, type RouteDraft,
} from './route';

export type LoadState = 'idle' | 'loading' | 'ready' | 'failed';
export interface ImageEvidence {
  declaredSha256: string; actualSha256: string; declaredBytes: number; receivedBytes: number;
  declaredWidth: number; declaredHeight: number; decodedWidth: number; decodedHeight: number; magic: string; maxval: number;
}
export interface VersionRefView { version: string; contentDigest: string; createdAt: string; waypointCount: number; mapRef: { mapId: string; version: string; frame: 'map' } }

export interface RouteWorkspace {
  working: RouteDraft;
  catalog: MapVersionDto[];
  catalogMeta: { source: string; live: boolean; supported: boolean; reason: string | null; schemaVersion: string } | null;
  catalogState: LoadState; catalogError: string;
  selectedMap: MapMetadata | null; mapState: LoadState; mapError: string;
  imageEvidence: ImageEvidence | null;
  serverDraft: ServerDraftView | null; draftError: string; conflict: RevisionConflict | null;
  versions: VersionRefView[]; versionsError: string;
  viewed: RouteVersionView | null;
  dirty: boolean; mapMismatch: boolean; errors: string[]; busy: string; offlineMode: boolean; publishNote: string;
  useOfflineMap(): void;
  loadCatalog(): void;
  selectMap(mapId: string, version: string): void;
  createRoute(name: string): void;
  saveRoute(): void;
  publishRoute(): void;
  openRoute(routeId: string): void;
  reloadServerDraft(): void;
  retrySaveOnServer(): void;
  refreshVersions(): void;
  viewVersion(version: string): void;
  closeVersionView(): void;
  closeRoute(): void;
  clearPointsForSelectedMap(): void;
  setWorking(draft: RouteDraft): void;
}

export function useRouteWorkspace(): RouteWorkspace {
  const api = useMemo(() => new PlatformNavigationApi(), []);
  const [working, setWorking] = useState<RouteDraft>(() => createOfflineDraft());
  const [catalog, setCatalog] = useState<MapVersionDto[]>([]);
  const [catalogMeta, setCatalogMeta] = useState<RouteWorkspace['catalogMeta']>(null);
  const [catalogState, setCatalogState] = useState<LoadState>('idle');
  const [catalogError, setCatalogError] = useState('');
  const [selectedMap, setSelectedMap] = useState<MapMetadata | null>(OFFLINE_MAP);
  const [mapState, setMapState] = useState<LoadState>('idle');
  const [mapError, setMapError] = useState('');
  const [imageEvidence, setImageEvidence] = useState<ImageEvidence | null>(null);
  const [serverDraft, setServerDraft] = useState<ServerDraftView | null>(null);
  const [draftError, setDraftError] = useState('');
  const [conflict, setConflict] = useState<RevisionConflict | null>(null);
  const [versions, setVersions] = useState<VersionRefView[]>([]);
  const [versionsError, setVersionsError] = useState('');
  const [viewed, setViewed] = useState<RouteVersionView | null>(null);
  const [busy, setBusy] = useState('');
  const [publishNote, setPublishNote] = useState('');
  const [offlineMode, setOfflineMode] = useState(true);
  const mapSerial = useRef(0);
  const routeSerial = useRef(0);
  const versionSerial = useRef(0);
  const mapController = useRef<AbortController | null>(null);
  const routeController = useRef<AbortController | null>(null);
  const versionController = useRef<AbortController | null>(null);

  const errors = useMemo(() => routeErrors(working), [working]);
  const dirty = useMemo(() => !serverDraft
    || !routeContentEqual(working.waypoints, serverDraft.waypoints) || working.label !== serverDraft.name, [working, serverDraft]);
  const mapMismatch = useMemo(() => working.waypoints
    .some((point) => point.mapId !== working.map.mapId || point.mapVersion !== working.map.version), [working]);

  const loadCatalog = useCallback(() => {
    const controller = new AbortController();
    setCatalogState('loading'); setCatalogError('');
    void api.listMaps(controller.signal).then((value: MapListDto) => {
      setCatalog(value.maps);
      setCatalogMeta({ source: value.source, live: value.live, supported: value.supported, reason: value.reason, schemaVersion: value.schema_version });
      setCatalogState('ready');
    }).catch((cause) => { setCatalogError(describeApiError(cause)); setCatalogState('failed'); });
  }, [api]);

  const readMap = useCallback((dto: MapVersionDto) => {
    const serial = ++mapSerial.current;
    mapController.current?.abort();
    const controller = new AbortController();
    mapController.current = controller;
    setMapState('loading'); setMapError(''); setImageEvidence(null);
    const metadata = mapDtoToMetadata(dto);
    if (!dto.image) { setMapError('image_missing · 该地图版本未声明 image 资产'); setMapState('failed'); return; }
    void api.mapImage(dto.map_id, dto.version, dto.image.sha256, controller.signal).then(async (raw) => {
      const actual = await sha256Hex(raw);
      assertDigest(actual, dto.image?.sha256 ?? '');
      const raster = parsePgm(raw);
      assertDims(raster, dto.width_px, dto.height_px);
      if (serial !== mapSerial.current) return;
      const next: MapMetadata = { ...metadata, imageUrl: rasterToPngDataUrl(raster), widthPx: raster.width, heightPx: raster.height };
      setSelectedMap(next);
      setWorking((previous) => ({ ...previous, map: next }));
      setImageEvidence({
        declaredSha256: dto.image?.sha256 ?? '', actualSha256: actual, declaredBytes: dto.image?.bytes ?? 0,
        receivedBytes: raw.length, declaredWidth: dto.width_px, declaredHeight: dto.height_px,
        decodedWidth: raster.width, decodedHeight: raster.height, magic: raster.magic, maxval: raster.maxval,
      });
      setMapState('ready'); setOfflineMode(false);
    }).catch((cause) => {
      if (serial !== mapSerial.current) return;
      setMapError(cause instanceof PgmError ? `${cause.code} · ${cause.message}` : describeApiError(cause));
      setMapState('failed');
    });
  }, [api]);

  const selectMap = useCallback((mapId: string, version: string) => {
    setBusy('map');
    void api.getMapVersion(mapId, version, new AbortController().signal)
      .then((dto) => { readMap(dto); setBusy(''); })
      .catch((cause) => { setMapError(describeApiError(cause)); setMapState('failed'); setBusy(''); });
  }, [api, readMap]);

  const useOfflineMap = useCallback(() => {
    mapSerial.current += 1; mapController.current?.abort();
    setSelectedMap(OFFLINE_MAP); setWorking((previous) => ({ ...previous, map: OFFLINE_MAP }));
    setMapState('idle'); setMapError(''); setImageEvidence(null); setOfflineMode(true);
  }, []);

  const rememberRoute = (routeId: string | null) => {
    const url = new URL(window.location.href);
    if (routeId) url.searchParams.set('route', routeId); else url.searchParams.delete('route');
    window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`);
  };

  const refreshVersionsOf = useCallback((routeId: string) => {
    const serial = ++versionSerial.current;
    versionController.current?.abort();
    const controller = new AbortController();
    versionController.current = controller;
    setVersionsError('');
    void api.listVersions(routeId, controller.signal).then((value) => {
      if (serial !== versionSerial.current) return;
      setVersions(value.versions.map(summaryDtoToRef));
    }).catch((cause) => {
      if (serial !== versionSerial.current) return;
      // The candidate answers "no published versions yet" with 404 route_version_not_found.
      if (cause instanceof ApiError && cause.code === 'route_version_not_found') { setVersions([]); return; }
      setVersionsError(describeApiError(cause));
    });
  }, [api]);

  const openRoute = useCallback((routeId: string) => {
    const serial = ++routeSerial.current;
    routeController.current?.abort();
    const controller = new AbortController();
    routeController.current = controller;
    setBusy('route-open'); setDraftError(''); setConflict(null);
    void api.getDraft(routeId, controller.signal).then(async (dto: RouteDraftDto) => {
      if (serial !== routeSerial.current) return;
      const bound = mapRefOf(selectedMap ?? OFFLINE_MAP);
      if (dto.map_ref.map_id !== bound.mapId || dto.map_ref.version !== bound.version) {
        const mapDto = await api.getMapVersion(dto.map_ref.map_id, dto.map_ref.version, controller.signal);
        if (serial !== routeSerial.current) return;
        readMap(mapDto);
        setWorking(draftDtoToWorking(dto, mapDtoToMetadata(mapDto)));
      } else {
        setWorking(draftDtoToWorking(dto, selectedMap ?? OFFLINE_MAP));
      }
      if (serial !== routeSerial.current) return;
      setServerDraft(draftDtoToView(dto)); setBusy('');
      rememberRoute(dto.route_id);
      refreshVersionsOf(dto.route_id);
    }).catch((cause) => { if (serial === routeSerial.current) { setDraftError(describeApiError(cause)); setBusy(''); } });
  }, [api, refreshVersionsOf, readMap, selectedMap]);

  const createRoute = useCallback((name: string) => {
    if (offlineMode) { setDraftError('离线测试地图不是后端资源；先读取并选择真实地图版本'); return; }
    setBusy('route-create'); setDraftError('');
    void api.createDraft(workingToPayload(working, name), new AbortController().signal).then((dto) => {
      setWorking(draftDtoToWorking(dto, working.map)); setServerDraft(draftDtoToView(dto));
      setConflict(null); setBusy(''); rememberRoute(dto.route_id); refreshVersionsOf(dto.route_id);
    }).catch((cause) => { setDraftError(describeApiError(cause)); setBusy(''); });
  }, [api, offlineMode, refreshVersionsOf, working]);

  const writeSave = useCallback((baseRevision: number) => {
    if (!serverDraft) return;
    setBusy('route-save'); setDraftError('');
    void api.saveDraft(serverDraft.routeId, { ...workingToPayload(working, working.label), base_revision: baseRevision }, new AbortController().signal)
      .then((dto) => {
        setWorking(draftDtoToWorking(dto, working.map)); setServerDraft(draftDtoToView(dto));
        setConflict(null); setBusy('');
      })
      .catch((cause) => {
        const clash = conflictOf(cause);
        if (clash) {
          setConflict(clash);
          setDraftError(`${clash.code}${clash.serverRevision === null ? '' : ` · current_revision=${clash.serverRevision}`} · ${clash.message}（本地编辑仍保留，未覆盖）`);
        } else setDraftError(describeApiError(cause));
        setBusy('');
      });
  }, [api, serverDraft, working]);

  const saveRoute = useCallback(() => { if (serverDraft) writeSave(serverDraft.draftRevision); }, [serverDraft, writeSave]);
  const retrySaveOnServer = useCallback(() => { if (conflict && conflict.serverRevision !== null) writeSave(conflict.serverRevision); }, [conflict, writeSave]);

  const reloadServerDraft = useCallback(() => {
    if (!serverDraft) return;
    setBusy('route-reload'); setDraftError('');
    void api.getDraft(serverDraft.routeId, new AbortController().signal).then((dto) => {
      setWorking(draftDtoToWorking(dto, working.map)); setServerDraft(draftDtoToView(dto)); setConflict(null); setBusy('');
    }).catch((cause) => { setDraftError(describeApiError(cause)); setBusy(''); });
  }, [api, serverDraft, working.map]);

  const publishRoute = useCallback(() => {
    if (!serverDraft) return;
    setBusy('route-publish'); setDraftError('');
    void api.publishDraft(serverDraft.routeId, serverDraft.draftRevision, new AbortController().signal).then((result) => {
      setViewed(versionDtoToView(result.route_version));
      setPublishNote(result.reused ? 'reused · 内容与已发布版本相同，后端未新建版本' : 'published · 后端新建了不可变版本');
      setBusy('');
      refreshVersionsOf(serverDraft.routeId);
    }).catch((cause) => {
      const clash = conflictOf(cause);
      setDraftError(clash ? `${clash.code} · ${clash.message}` : describeApiError(cause)); setBusy('');
    });
  }, [api, refreshVersionsOf, serverDraft]);

  const viewVersion = useCallback((version: string) => {
    if (!serverDraft) return;
    const serial = ++versionSerial.current;
    versionController.current?.abort();
    const controller = new AbortController();
    versionController.current = controller;
    setBusy('version-view'); setVersionsError('');
    void api.getVersion(serverDraft.routeId, version, controller.signal).then((dto) => {
      if (serial !== versionSerial.current) return;
      setViewed(versionDtoToView(dto)); setBusy('');
    }).catch((cause) => { if (serial === versionSerial.current) { setVersionsError(describeApiError(cause)); setBusy(''); } });
  }, [api, serverDraft]);

  const closeVersionView = useCallback(() => { versionSerial.current += 1; versionController.current?.abort(); setViewed(null); }, []);
  const closeRoute = useCallback(() => {
    routeSerial.current += 1; routeController.current?.abort();
    versionSerial.current += 1; versionController.current?.abort();
    setServerDraft(null); setViewed(null); setVersions([]); setConflict(null); setDraftError(''); setPublishNote('');
    setWorking((previous) => ({ ...previous, routeId: 'route-local-draft', draftRevision: 1 }));
    rememberRoute(null);
  }, []);
  const clearPointsForSelectedMap = useCallback(() => setWorking((previous) => ({ ...previous, waypoints: [] })), []);

  const openedFromUrl = useRef(false);
  useEffect(() => {
    if (openedFromUrl.current) return;
    const routeId = new URL(window.location.href).searchParams.get('route');
    if (!routeId) return;
    openedFromUrl.current = true;
    openRoute(routeId);
  }, [openRoute]);

  useEffect(() => () => {
    mapSerial.current += 1; routeSerial.current += 1; versionSerial.current += 1;
    mapController.current?.abort(); routeController.current?.abort(); versionController.current?.abort();
  }, []);

  return {
    working, catalog, catalogMeta, catalogState, catalogError, selectedMap, mapState, mapError, imageEvidence,
    serverDraft, draftError, conflict, versions, versionsError, viewed, dirty, mapMismatch, errors, busy, offlineMode, publishNote,
    useOfflineMap, loadCatalog, selectMap, createRoute, saveRoute, publishRoute, openRoute, reloadServerDraft,
    retrySaveOnServer, refreshVersions: () => (serverDraft ? refreshVersionsOf(serverDraft.routeId) : undefined),
    viewVersion, closeVersionView, closeRoute, clearPointsForSelectedMap, setWorking,
  };
}
