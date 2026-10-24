import type { ViewSample, WorkbenchService } from './types';
import { IdentityChanged, initializeSample, mapSnapshot, readEnvelope, readKinematics, resourceIdentityKey, runtimeIdentityKey, sceneContentKey, type SceneRead, type CapabilitiesRead, type SnapshotRead } from './mobilecar-read';
import { PlatformConfigApi, type ExecutionRecipe } from './platform-config';
import { frozenKinematicProfile, liveKinematicProfile, unavailableKinematics, type KinematicsMapping } from './robot-profile';
async function readJson<T>(url: URL, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal, cache: 'no-store' });
  if (!response.ok) throw new Error(`${url.pathname}: HTTP ${response.status}`);
  return response.json() as Promise<T>;
}
async function readRecipe(signal: AbortSignal): Promise<ExecutionRecipe | null> {
  try { return await new PlatformConfigApi().executionRecipe(signal); }
  catch (error) { if (signal.aborted) throw error; return null; }
}
async function liveMapping(scene: SceneRead, caps: CapabilitiesRead, signal: AbortSignal): Promise<KinematicsMapping> {
  const [kinematics, recipe] = await Promise.allSettled([readKinematics(signal), readRecipe(signal)]);
  if (kinematics.status === 'rejected') {
    if (signal.aborted) throw kinematics.reason;
    return { armSpec: null, report: unavailableKinematics((kinematics.reason as Error).message) };
  }
  return liveKinematicProfile(kinematics.value, scene.robot_id, caps.data, scene.data, recipe.status === 'fulfilled' ? recipe.value : null);
}
const unsupported = async () => ({ status: 'unsupported' as const, reason: '平台 Session、控制权和命令通路尚未接通；当前只能编辑本地预览。' });
export class FrozenSampleService implements WorkbenchService {
  async load(signal: AbortSignal): Promise<ViewSample> {
    const base = new URL(import.meta.env.BASE_URL, window.location.href);
    const [scene, actual, capabilities, armSpecFile, source] = await Promise.all([
      readJson<ViewSample['scene']>(new URL('sample/scene.json', base), signal),
      readJson<ViewSample['actual']>(new URL('sample/snapshot.json', base), signal),
      readJson<ViewSample['capabilities']>(new URL('sample/capabilities.json', base), signal),
      readJson<ViewSample['armSpec']>(new URL('sample/arm-spec.json', base), signal),
      readJson<ViewSample['source']>(new URL('sample/provenance.json', base), signal),
    ]);
    if (!scene.links.length || !actual.tcp || !capabilities.arm_joint_names.length || !armSpecFile) throw new Error('冻结样本缺少 scene / Actual / joints / arm-spec，不能加载工作台。');
    scene.mesh_assets = scene.mesh_assets.map(asset => ({ ...asset, uri: new URL(asset.uri, base).href, coordinate_space:'legacy_raw_stl' as const }));
    const mapping = frozenKinematicProfile(armSpecFile);
    return { scene, actual, capabilities, armSpec: mapping.armSpec, source: { ...source, kind: 'frozen', label: '冻结旧样板 · 网格坐标未修正' } };
  }
  submit = unsupported;
  dispose() {}
}
export class PlatformService implements WorkbenchService {
  async load(signal: AbortSignal): Promise<ViewSample> {
    const [scene,caps]=await Promise.all([readEnvelope<SceneRead>('/api/v1/mobilecar/scene',signal),readEnvelope<CapabilitiesRead>('/api/v1/mobilecar/capabilities',signal)]);
    const snapshot=await readEnvelope<SnapshotRead>('/api/v1/mobilecar/snapshot',signal);
    const mapping=await liveMapping(scene,caps,signal);
    return initializeSample(scene,caps,snapshot,mapping);
  }
  async refresh(sample:ViewSample,signal:AbortSignal):Promise<ViewSample>{
    const snapshot=await readEnvelope<SnapshotRead>('/api/v1/mobilecar/snapshot',signal);
    if(resourceIdentityKey(snapshot)!==sample.live!.resourceKey)throw new IdentityChanged('后端资源 / 内容身份已变化，旧网格与本地目标作废');
    if(runtimeIdentityKey(snapshot.runtime_identity)===sample.live!.runtimeKey)return mapSnapshot(sample,snapshot);
    // Runtime identity changed: re-read content identity and metadata, but
    // preserve the loaded scene object when the compiled content still matches.
    const [scene,caps]=await Promise.all([readEnvelope<SceneRead>('/api/v1/mobilecar/scene',signal),readEnvelope<CapabilitiesRead>('/api/v1/mobilecar/capabilities',signal)]);
    if(sceneContentKey(scene)!==sample.live!.contentKey)throw new IdentityChanged('编译几何内容身份已变化；不能沿用旧网格，请重新加载来源');
    const mapping=await liveMapping(scene,caps,signal);
    const next=initializeSample(scene,caps,snapshot,mapping);
    return {...next,scene:sample.scene};
  }
  submit = unsupported;
  dispose() {}
}
