// Private wire projections of backend mobilecar_read.py, unirobot-mobilecar-read-1.
// Shared contracts remain owned by the backend. No panel consumes these types.
import type { BackendTarget, Capabilities, LiveMetadata, NativeSnapshot, ResourceIdentity, RuntimeIdentity, SceneManifest, ViewSample } from './types';
import { localKinematicProfile, profileId } from './robot-profile';
export interface Envelope<T> {
 schema_version: string; data_source: string; adapter_id: string; robot_id: string;
 read_only: boolean; session_ready: boolean; platform_session_id: null;
 retrieved_at: string; runtime_identity: RuntimeIdentity; resource_identity: ResourceIdentity; interface_profile: string;
 data: T;
}
export interface SceneRead extends Envelope<SceneManifest> { objects: LiveMetadata['objects']; world_pose_semantics: string; geometry_provenance:Record<string,unknown> }
export interface CapabilitiesRead extends Envelope<Capabilities & ResourceIdentity> {
 platform_commands_available: boolean; platform_recording_available: boolean; platform_replay_available: boolean;
}
export interface SnapshotRead extends Envelope<{
 time: {sim_time_s:number;backend_monotonic_s:number;feedback_time_s:number;wall_utc:string;clock_id:string;control_tick_id:string};
 arm_joint_names:string[]; actual: Pick<NativeSnapshot,'base'|'arm'|'tcp'|'gripper'|'model_joint_positions_rad'>;
 target:BackendTarget; authority:LiveMetadata['authority']; recording:LiveMetadata['recording']; sensors:LiveMetadata['sensors'];
}> {}
export class IdentityChanged extends Error {}
export class ReadError extends Error { constructor(public code:string,message:string){super(message);} }
export function identityKey(e: Envelope<unknown>): string {
 const r=e.runtime_identity,s=e.resource_identity;
 return JSON.stringify([e.adapter_id,e.robot_id,r.run_id,r.backend_generation,r.episode_id,s.contract_version,s.model_id,s.model_sha256,s.scene_id,e.interface_profile]);
}
export async function readEnvelope<T extends Envelope<unknown>>(path:string,signal:AbortSignal):Promise<T> {
 const response=await fetch(path,{signal,cache:'no-store'});
 const body=await response.json();
 if(!response.ok){const code=body.detail?.code??`HTTP_${response.status}`;if(code==='native_identity_changed'||code==='geometry_source_changed')throw new IdentityChanged(`${code}: ${body.detail?.message??''}`);throw new ReadError(code,`${code}: ${body.detail?.message??response.statusText}`);}
 const e=body as T;
 const scene=path==='/api/v1/mobilecar/scene';
 const compatible=scene?e.schema_version==='unirobot-mobilecar-geometry-1'&&e.data_source==='live_native_http_with_verified_compiled_geometry':e.schema_version==='unirobot-mobilecar-read-1'&&e.data_source==='live_native_http';
 if(!compatible||e.read_only!==true||e.session_ready!==false||e.platform_session_id!==null
   ||!e.runtime_identity?.run_id||!e.resource_identity?.model_sha256||!e.data)throw new ReadError('incompatible_envelope','只读 envelope 缺少身份或版本不兼容');
 return e;
}
function sameIdentity(...envelopes:Envelope<unknown>[]){if(envelopes.some(e=>identityKey(e)!==identityKey(envelopes[0])))throw new IdentityChanged('跨请求运行 / 资源身份已变化，旧目标作废');}
export function mapSnapshot(sample:ViewSample, snapshot:SnapshotRead):ViewSample {
 if(identityKey(snapshot)!==sample.live!.identityKey)throw new IdentityChanged('运行 / 资源身份已变化，旧目标作废');
 const d=snapshot.data,names=sample.capabilities.arm_joint_names;
 if(names.join(',')!==d.arm_joint_names.join(',')||names.some(n=>!Number.isFinite(d.actual.model_joint_positions_rad[n]))
   ||d.actual.arm.user_joint_positions_rad.length!==names.length||d.target.user_joint_positions_rad.length!==names.length
   ||d.actual.tcp.frame_id!=='world_sim')throw new ReadError('incompatible_snapshot','snapshot 的关节映射 / Frame 不兼容');
 // Explicit projection: never merge diagnostics or frozen data into live Actual.
 const actual:NativeSnapshot={...snapshot.runtime_identity,sim_time_s:d.time.sim_time_s,backend_monotonic_s:d.time.backend_monotonic_s,wall_utc:d.time.wall_utc,clock_id:d.time.clock_id,control_tick_id:d.time.control_tick_id,base:d.actual.base,arm:d.actual.arm,tcp:d.actual.tcp,gripper:d.actual.gripper,
   model_joint_positions_rad:d.actual.model_joint_positions_rad,diagnostics:{}};
 return {...sample,actual,source:{...sample.source,captured_at_utc:d.time.wall_utc},live:{...sample.live!,retrievedAt:snapshot.retrieved_at,
   feedbackTimeS:d.time.feedback_time_s,target:d.target,authority:d.authority,recording:d.recording,sensors:d.sensors}};
}
export function initializeSample(scene:SceneRead,caps:CapabilitiesRead,snapshot:SnapshotRead):ViewSample {
 sameIdentity(scene,caps,snapshot);
 if(scene.schema_version!=='unirobot-mobilecar-geometry-1'||scene.data_source!=='live_native_http_with_verified_compiled_geometry'||!scene.geometry_provenance)throw new ReadError('mesh_coordinates_unavailable','此读取服务未提供已验证编译网格；不能用旧原始 STL 配编译 geom 位姿');
 if(scene.data.links.concat(scene.data.world_links).some(l=>l.geoms.some(g=>g.geom_type==='mesh'&&(g.size_m.length!==3||g.size_m.some(v=>v!==1)))))throw new ReadError('mesh_scale_ambiguous','编译网格必须明确不再应用 mesh scale');
 if(caps.platform_commands_available!==false||caps.platform_recording_available!==false||caps.platform_replay_available!==false
  ||scene.world_pose_semantics!=='compiled_initial_layout_not_live_object_state')throw new ReadError('incompatible_capabilities','只读能力 / 场景语义不兼容');
 if(JSON.stringify([scene.data.model_id,scene.data.model_sha256,scene.data.scene_id])!==JSON.stringify([scene.resource_identity.model_id,scene.resource_identity.model_sha256,scene.resource_identity.scene_id]))throw new ReadError('scene_identity','场景内容身份与 envelope 不一致');
 const assets=scene.data.mesh_assets.map(a=>{
   if(a.coordinate_space!=='mujoco_compiled_mesh'||a.units!=='m'||a.mesh_preprocessing_applied!==true||!a.source_sha256||!a.source_mesh_name)throw new ReadError('mesh_coordinates_unavailable','资产缺少编译网格坐标约定 / 源身份');
   const url=new URL(a.uri,window.location.origin);
   if(url.origin!==window.location.origin||url.pathname!==`/api/v1/mobilecar/scene/assets/${encodeURIComponent(a.asset_id)}`||url.searchParams.get('sha256')!==a.sha256)throw new ReadError('asset_uri','资产 URI / 摘要不符合平台场景清单');
   return {...a,uri:url.href};});
 const armSpec=localKinematicProfile(scene.resource_identity,caps.data);
 const sample={scene:{...scene.data,mesh_assets:assets},capabilities:caps.data,armSpec,
   source:{kind:'live' as const,label:'真实只读监控',captured_at_utc:'',identity:scene.runtime_identity,interface_profile:scene.interface_profile,is_platform_session:false,is_episode_replay:false},
   live:{identityKey:identityKey(scene),resource:scene.resource_identity,objects:scene.objects,worldPoseSemantics:scene.world_pose_semantics,
    geometryProvenance:scene.geometry_provenance,kinematicProfile:armSpec?profileId:'unsupported',retrievedAt:'',feedbackTimeS:0,target:snapshot.data.target,authority:snapshot.data.authority,recording:snapshot.data.recording,sensors:[]},actual:null as unknown as NativeSnapshot};
 return mapSnapshot(sample,snapshot);
}
