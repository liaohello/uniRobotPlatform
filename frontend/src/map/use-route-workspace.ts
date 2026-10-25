import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ApiError, describeApiError } from '../adapters/platform-config';
import {
  PlatformNavigationApi, conflictOf, draftDtoToView, draftDtoToWorking, mapDtoToMetadata,
  summaryDtoToRef, versionDtoToView, workingToPayload,
  type MapListDto, type MapRefDto, type MapVersionDto, type RevisionConflict, type RouteDraftDto, type RouteVersionView, type ServerDraftView,
} from '../adapters/platform-navigation';
import { PgmError, assertDims, assertDigest, parsePgm, rasterToPngDataUrl, sha256Hex } from './pgm';
import {
  OFFLINE_MAP, createOfflineDraft, mapRefOf, routeContentEqual, routeErrors,
  type MapMetadata, type RouteDraft,
} from './route';

export type LoadState = 'idle' | 'loading' | 'ready' | 'failed';
export interface ImageEvidence {
  mapId: string; mapVersion: string;
  declaredSha256: string; actualSha256: string; declaredBytes: number; receivedBytes: number;
  declaredWidth: number; declaredHeight: number; decodedWidth: number; decodedHeight: number; magic: string; maxval: number;
}
export interface VersionRefView { version: string; contentDigest: string; createdAt: string; waypointCount: number; mapRef: { mapId: string; version: string; frame: 'map' } }
export interface WriteGate { enabled: boolean; reason: string }
export interface PublishInfo { version: string; contentDigest: string; fromRevision: number; reused: boolean; localEditsExcluded: boolean }

export interface RouteWorkspace {
  working: RouteDraft;
  catalog: MapVersionDto[];
  catalogMeta: { source: string; live: boolean; supported: boolean; reason: string | null; schemaVersion: string } | null;
  catalogState: LoadState; catalogError: string;
  selectedMap: MapMetadata | null; mapState: LoadState; mapError: string;
  imageEvidence: ImageEvidence | null;
  serverDraft: ServerDraftView | null; draftError: string; conflict: RevisionConflict | null;
  versions: VersionRefView[]; versionsError: string;
  viewed: RouteVersionView | null; publishInfo: PublishInfo | null;
  dirty: boolean; mapMismatch: boolean; errors: string[]; busy: string; offlineMode: boolean;
  gates: { create: WriteGate; save: WriteGate; publish: WriteGate; retry: WriteGate };
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

const gate = (enabled: boolean, reason: string): WriteGate => ({ enabled, reason });

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
  const [publishInfo, setPublishInfo] = useState<PublishInfo | null>(null);
  const [busy, setBusy] = useState('');
  const [offlineMode, setOfflineMode] = useState(true);
  // One transaction per intent: the same serial and signal cover the version read, the raster
  // bytes and every digest/geometry check, so a superseded choice can never land.
  const mapSerial = useRef(0);
  const routeSerial = useRef(0);
  const versionSerial = useRef(0);
  const catalogSerial = useRef(0);
  const controllers = useRef<AbortController[]>([]);
  const track = (controller: AbortController) => { controllers.current.push(controller); return controller; };

  const errors = useMemo(() => routeErrors(working), [working]);
  const dirty = useMemo(() => !serverDraft
    || !routeContentEqual(working.waypoints, serverDraft.waypoints) || working.label !== serverDraft.name, [working, serverDraft]);
  const mapMismatch = useMemo(() => working.waypoints
    .some((point) => point.mapId !== working.map.mapId || point.mapVersion !== working.map.version), [working]);

  const verifiedMap = useMemo(() => {
    if (!selectedMap?.authority || mapState !== 'ready' || mapError) return null;
    const evidence = imageEvidence;
    const declared = selectedMap.authority.image?.sha256 ?? '';
    if (!evidence || !declared) return null;
    const identityOk = evidence.mapId === selectedMap.mapId && evidence.mapVersion === selectedMap.version;
    const digestOk = evidence.actualSha256 === declared;
    const geometryOk = evidence.decodedWidth === selectedMap.widthPx && evidence.decodedHeight === selectedMap.heightPx;
    return identityOk && digestOk && geometryOk ? evidence : null;
  }, [selectedMap, imageEvidence, mapState, mapError]);

  const posesValid = working.waypoints.length > 0 && errors.length === 0 && !mapMismatch;
  const mapWriteReason = mapError ? `地图读取或校验失败：${mapError}`
    : mapState === 'loading' ? '地图版本与栅格正在读取，写入等待本次选择完成'
      : offlineMode ? '当前是离线测试地图，不是后端资源；先读取并选择真实地图版本'
        : !verifiedMap ? '真实地图栅格尚未通过摘要与尺寸校验（或校验对象不是当前地图）'
          : mapMismatch ? 'PointGoal 仍绑定旧地图，需显式清空后改用此地图' : '';
  const gates = useMemo(() => {
    const ready = posesValid && !mapWriteReason && busy === '';
    const blockedReason = busy !== '' ? `${busy} 正在进行` : mapWriteReason || (posesValid ? '' : '需要至少一个 PointGoal，且每点位置与朝向有效');
    return {
      create: gate(ready && !serverDraft, serverDraft ? '已打开服务端 Route Draft' : blockedReason),
      save: gate(ready && Boolean(serverDraft), serverDraft ? blockedReason : '先创建或按 route_id 打开服务端草案'),
      publish: gate(ready && Boolean(serverDraft), serverDraft ? blockedReason : '先创建或按 route_id 打开服务端草案'),
      retry: gate(Boolean(conflict) && conflict?.serverRevision !== null && posesValid && !mapWriteReason && busy === '',
        conflict?.serverRevision === null ? '服务器未返回 current_revision' : blockedReason),
    };
  }, [busy, conflict, mapWriteReason, posesValid, serverDraft]);

  const loadCatalog = useCallback(() => {
    const serial = ++catalogSerial.current;
    const controller = track(new AbortController());
    setCatalogState('loading'); setCatalogError('');
    void api.listMaps(controller.signal).then((value: MapListDto) => {
      if (serial !== catalogSerial.current) return;
      setCatalog(value.maps);
      setCatalogMeta({ source: value.source, live: value.live, supported: value.supported, reason: value.reason, schemaVersion: value.schema_version });
      setCatalogState('ready');
    }).catch((cause) => {
      if (serial !== catalogSerial.current) return;
      setCatalogError(describeApiError(cause)); setCatalogState('failed');
    });
  }, [api]);

  /** The whole map read for one selection; resolves false when the selection was superseded or failed. */
  const applyMap = useCallback((dto: MapVersionDto, serial: number, signal: AbortSignal): Promise<boolean> => {
    const live = () => serial === mapSerial.current;
    let metadata: MapMetadata;
    try {
      metadata = mapDtoToMetadata(dto);
    } catch (cause) {
      if (live()) { setMapError(cause instanceof Error ? `${cause.name} · ${cause.message}` : String(cause)); setMapState('failed'); }
      return Promise.resolve(false);
    }
    if (!dto.image) { if (live()) { setMapError('image_missing · 该地图版本未声明 image 资产'); setMapState('failed'); } return Promise.resolve(false); }
    return api.mapImage(dto.map_id, dto.version, dto.image.sha256, signal).then(async (raw) => {
      const actual = await sha256Hex(raw);
      assertDigest(actual, dto.image?.sha256 ?? '');
      const raster = parsePgm(raw);
      assertDims(raster, dto.width_px, dto.height_px);
      if (!live()) return false;
      const next: MapMetadata = { ...metadata, imageUrl: rasterToPngDataUrl(raster), widthPx: raster.width, heightPx: raster.height };
      setSelectedMap(next);
      setWorking((previous) => ({ ...previous, map: next }));
      setImageEvidence({
        mapId: dto.map_id, mapVersion: dto.version,
        declaredSha256: dto.image?.sha256 ?? '', actualSha256: actual, declaredBytes: dto.image?.bytes ?? 0,
        receivedBytes: raw.length, declaredWidth: dto.width_px, declaredHeight: dto.height_px,
        decodedWidth: raster.width, decodedHeight: raster.height, magic: raster.magic, maxval: raster.maxval,
      });
      setMapError(''); setMapState('ready'); setOfflineMode(false);
      return true;
    }).catch((cause) => {
      if (!live()) return false;
      setMapError(cause instanceof PgmError ? `${cause.code} · ${cause.message}` : describeApiError(cause));
      setImageEvidence(null); setMapState('failed');
      return false;
    });
  }, [api]);

  const selectMap = useCallback((mapId: string, version: string) => {
    const serial = ++mapSerial.current;
    controllers.current.forEach((controller) => controller.abort());
    controllers.current = [];
    const controller = track(new AbortController());
    setMapState('loading'); setMapError(''); setImageEvidence(null); setBusy('map');
    void api.getMapVersion(mapId, version, controller.signal)
      .then((dto) => (serial === mapSerial.current ? applyMap(dto, serial, controller.signal) : Promise.resolve(false)))
      .catch((cause) => {
        if (serial !== mapSerial.current) return;
        setMapError(describeApiError(cause)); setImageEvidence(null); setMapState('failed');
      })
      .finally(() => { if (serial === mapSerial.current) setBusy(''); });
  }, [api, applyMap]);

  const useOfflineMap = useCallback(() => {
    mapSerial.current += 1; routeSerial.current += 1; versionSerial.current += 1;
    controllers.current.forEach((controller) => controller.abort());
    controllers.current = [];
    setSelectedMap(OFFLINE_MAP);
    setWorking((previous) => ({ ...previous, map: OFFLINE_MAP }));
    setMapState('idle'); setMapError(''); setImageEvidence(null); setOfflineMode(true); setBusy('');
  }, []);

  const rememberRoute = (routeId: string | null) => {
    const url = new URL(window.location.href);
    if (routeId) url.searchParams.set('route', routeId); else url.searchParams.delete('route');
    window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`);
  };

  const refreshVersionsOf = useCallback((routeId: string) => {
    const serial = ++versionSerial.current;
    const controller = track(new AbortController());
    setVersionsError('');
    void api.listVersions(routeId, controller.signal).then((value) => {
      if (serial !== versionSerial.current) return;
      setVersions(value.versions.map(summaryDtoToRef));
    }).catch((cause) => {
      if (serial !== versionSerial.current) return;
      if (cause instanceof ApiError && cause.code === 'route_version_not_found') { setVersions([]); return; }
      setVersionsError(describeApiError(cause));
    });
  }, [api]);

  const openRoute = useCallback((routeId: string) => {
    const serial = ++routeSerial.current;
    const controller = track(new AbortController());
    setBusy('route-open'); setDraftError(''); setConflict(null);
    void api.getDraft(routeId, controller.signal).then(async (dto: RouteDraftDto) => {
      if (serial !== routeSerial.current) return;
      const ref: MapRefDto = dto.map_ref;
      const current = mapRefOf(selectedMap ?? OFFLINE_MAP);
      if (ref.map_id !== current.mapId || ref.version !== current.version) {
        const mapSerialForRoute = ++mapSerial.current;
        const mapDto = await api.getMapVersion(ref.map_id, ref.version, controller.signal);
        if (serial !== routeSerial.current || mapSerialForRoute !== mapSerial.current) return;
        const ok = await applyMap(mapDto, mapSerialForRoute, controller.signal);
        if (!ok) {
          if (serial === routeSerial.current) { setDraftError(`路线绑定的地图 ${ref.map_id}/${ref.version} 读取或校验失败；不回退到其他地图`); setBusy(''); }
          return;
        }
        if (serial !== routeSerial.current) return;
        setWorking(draftDtoToWorking(dto, mapDtoToMetadata(mapDto)));
      } else {
        setWorking(draftDtoToWorking(dto, selectedMap ?? OFFLINE_MAP));
      }
      setServerDraft(draftDtoToView(dto));
      setPublishInfo(null); setBusy('');
      rememberRoute(dto.route_id);
      refreshVersionsOf(dto.route_id);
    }).catch((cause) => { if (serial === routeSerial.current) { setDraftError(describeApiError(cause)); setBusy(''); } });
  }, [api, applyMap, refreshVersionsOf, selectedMap]);

  const refuse = (reason: string) => setDraftError(`${reason}；写入未发出`);

  const createRoute = useCallback((name: string) => {
    if (!gates.create.enabled) { refuse(gates.create.reason); return; }
    setBusy('route-create'); setDraftError('');
    void api.createDraft(workingToPayload(working, name), new AbortController().signal).then((dto) => {
      setWorking(draftDtoToWorking(dto, working.map)); setServerDraft(draftDtoToView(dto));
      setConflict(null); setPublishInfo(null); setBusy(''); rememberRoute(dto.route_id); refreshVersionsOf(dto.route_id);
    }).catch((cause) => { setDraftError(describeApiError(cause)); setBusy(''); });
  }, [api, gates.create, refreshVersionsOf, working]);

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
          setDraftError(`${clash.code}${clash.serverRevision === null ? '' : ` · current_revision=${clash.serverRevision}`} · ${clash.message}（本地编辑仍保留，未覆盖服务器内容）`);
        } else setDraftError(describeApiError(cause));
        setBusy('');
      });
  }, [api, serverDraft, working]);

  const saveRoute = useCallback(() => {
    if (!gates.save.enabled) { refuse(gates.save.reason); return; }
    if (serverDraft) writeSave(serverDraft.draftRevision);
  }, [gates.save, serverDraft, writeSave]);

  const retrySaveOnServer = useCallback(() => {
    if (!gates.retry.enabled || !conflict || conflict.serverRevision === null) { refuse(gates.retry.reason); return; }
    writeSave(conflict.serverRevision);
  }, [conflict, gates.retry, writeSave]);

  const reloadServerDraft = useCallback(() => {
    if (!serverDraft) return;
    setBusy('route-reload'); setDraftError('');
    void api.getDraft(serverDraft.routeId, new AbortController().signal).then((dto) => {
      setWorking(draftDtoToWorking(dto, working.map)); setServerDraft(draftDtoToView(dto)); setConflict(null); setBusy('');
    }).catch((cause) => { setDraftError(describeApiError(cause)); setBusy(''); });
  }, [api, serverDraft, working.map]);

  const publishRoute = useCallback(() => {
    if (!serverDraft || !gates.publish.enabled) { refuse(gates.publish.reason); return; }
    const fromRevision = serverDraft.draftRevision;
    const localEditsExcluded = dirty;
    setBusy('route-publish'); setDraftError('');
    void api.publishDraft(serverDraft.routeId, fromRevision, new AbortController().signal).then((result) => {
      const view = versionDtoToView(result.route_version);
      setViewed(view);
      setPublishInfo({ version: view.version, contentDigest: view.contentDigest, fromRevision, reused: result.reused, localEditsExcluded });
      setBusy('');
      refreshVersionsOf(serverDraft.routeId);
    }).catch((cause) => {
      const clash = conflictOf(cause);
      setDraftError(clash ? `${clash.code} · ${clash.message}` : describeApiError(cause)); setBusy('');
    });
  }, [api, dirty, gates.publish, refreshVersionsOf, serverDraft]);

  const viewVersion = useCallback((version: string) => {
    if (!serverDraft) return;
    const serial = ++versionSerial.current;
    const controller = track(new AbortController());
    setBusy('version-view'); setVersionsError('');
    void api.getVersion(serverDraft.routeId, version, controller.signal).then((dto) => {
      if (serial !== versionSerial.current) return;
      setViewed(versionDtoToView(dto)); setBusy('');
    }).catch((cause) => { if (serial === versionSerial.current) { setVersionsError(describeApiError(cause)); setBusy(''); } });
  }, [api, serverDraft]);

  const closeVersionView = useCallback(() => { versionSerial.current += 1; setViewed(null); }, []);
  const closeRoute = useCallback(() => {
    routeSerial.current += 1; versionSerial.current += 1;
    setServerDraft(null); setViewed(null); setVersions([]); setConflict(null); setDraftError(''); setPublishInfo(null);
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
    mapSerial.current += 1; routeSerial.current += 1; versionSerial.current += 1; catalogSerial.current += 1;
    controllers.current.forEach((controller) => controller.abort());
    controllers.current = [];
  }, []);

  return {
    working, catalog, catalogMeta, catalogState, catalogError, selectedMap, mapState, mapError, imageEvidence,
    serverDraft, draftError, conflict, versions, versionsError, viewed, publishInfo,
    dirty, mapMismatch, errors, busy, offlineMode, gates,
    useOfflineMap, loadCatalog, selectMap, createRoute, saveRoute, publishRoute, openRoute, reloadServerDraft,
    retrySaveOnServer, refreshVersions: () => (serverDraft ? refreshVersionsOf(serverDraft.routeId) : undefined),
    viewVersion, closeVersionView, closeRoute, clearPointsForSelectedMap, setWorking,
  };
}
