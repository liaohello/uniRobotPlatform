import type { ViewSample, WorkbenchService, SceneManifest } from './types';
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
    scene.mesh_assets = scene.mesh_assets.map(asset => ({ ...asset, uri: new URL(asset.uri, base).href }));
    return { scene, actual, capabilities, armSpec, source: { ...source, kind: 'frozen', label: '冻结原生样本 · 非实时' } };
  }
  submit = unsupported;
  dispose() {}
}
// Real transport is deliberately confined to this adapter. The backend dialogue owns wire schemas.
// No guessed endpoint or native POST is issued while the platform feed is unavailable.
export class PlatformService implements WorkbenchService {
  constructor(private readonly feedUrl: string) {}
  async load(signal: AbortSignal): Promise<ViewSample> {
    if (!this.feedUrl) throw new Error('平台 scene/state feed 尚未配置；可显式切回冻结样本，不自动回退。');
    const url = new URL(this.feedUrl, window.location.href);
    const data = await readJson<ViewSample>(url, signal);
    if (data.source.kind !== 'live' || !data.source.is_platform_session) throw new Error('平台 feed 缺少真实来源/Session 标识，拒绝标为实时。');
    const scene: SceneManifest = { ...data.scene, mesh_assets: data.scene.mesh_assets.map(a => ({ ...a, uri: new URL(a.uri, url).href })) };
    return { ...data, scene };
  }
  submit = unsupported;
  dispose() {}
}
