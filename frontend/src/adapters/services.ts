import type { ViewSample, WorkbenchService } from './types';
import { initializeSample, mapSnapshot, readEnvelope, type SceneRead, type CapabilitiesRead, type SnapshotRead } from './mobilecar-read';
async function readJson<T>(url: URL, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal, cache: 'no-store' });
  if (!response.ok) throw new Error(`${url.pathname}: HTTP ${response.status}`);
  return response.json() as Promise<T>;
}
const unsupported = async () => ({ status: 'unsupported' as const, reason: '平台 Session、控制权和命令通路尚未接通；当前只能编辑本地预览。' });
export class FrozenSampleService implements WorkbenchService {
  async load(signal: AbortSignal): Promise<ViewSample> {
    const base = new URL(import.meta.env.BASE_URL, window.location.href);
    const [scene, actual, capabilities, armSpec, source] = await Promise.all([
      readJson<ViewSample['scene']>(new URL('sample/scene.json', base), signal),
      readJson<ViewSample['actual']>(new URL('sample/snapshot.json', base), signal),
      readJson<ViewSample['capabilities']>(new URL('sample/capabilities.json', base), signal),
      readJson<ViewSample['armSpec']>(new URL('sample/arm-spec.json', base), signal),
      readJson<ViewSample['source']>(new URL('sample/provenance.json', base), signal),
    ]);
    if (!scene.links.length || !actual.tcp || !capabilities.arm_joint_names.length) throw new Error('冻结样本缺少 scene / Actual / joints，不能加载工作台。');
    scene.mesh_assets = scene.mesh_assets.map(asset => ({ ...asset, uri: new URL(asset.uri, base).href, coordinate_space:'legacy_raw_stl' as const }));
    return { scene, actual, capabilities, armSpec, source: { ...source, kind: 'frozen', label: '冻结旧样板 · 网格坐标未修正' } };
  }
  submit = unsupported;
  dispose() {}
}
export class PlatformService implements WorkbenchService {
  async load(signal: AbortSignal): Promise<ViewSample> {
    const [scene,caps]=await Promise.all([readEnvelope<SceneRead>('/api/v1/mobilecar/scene',signal),readEnvelope<CapabilitiesRead>('/api/v1/mobilecar/capabilities',signal)]);
    const snapshot=await readEnvelope<SnapshotRead>('/api/v1/mobilecar/snapshot',signal);
    return initializeSample(scene,caps,snapshot);
  }
  async refresh(sample:ViewSample,signal:AbortSignal):Promise<ViewSample>{
    return mapSnapshot(sample,await readEnvelope<SnapshotRead>('/api/v1/mobilecar/snapshot',signal));
  }
  submit = unsupported;
  dispose() {}
}
