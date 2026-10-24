import {describe,it,expect} from 'vitest';
import sceneData from '../public/sample/scene.json';
import native from '../public/sample/snapshot.json';
import capsData from '../public/sample/capabilities.json';
import {initializeSample,mapSnapshot,IdentityChanged,type SceneRead,type CapabilitiesRead,type SnapshotRead} from '../src/adapters/mobilecar-read';
import {jointTarget} from '../src/app/state';
// Synthetic wire fixtures. Frozen captures below provide geometry only; not live evidence.
const resource={contract_version:sceneData.contract_version,model_id:sceneData.model_id,model_sha256:sceneData.model_sha256,scene_id:sceneData.scene_id};
const envelope={schema_version:'unirobot-mobilecar-read-1',data_source:'live_native_http',adapter_id:'mobilecar',robot_id:'landerpi',read_only:true,session_ready:false,platform_session_id:null,retrieved_at:'fixture',runtime_identity:{run_id:'fixture',backend_generation:1,episode_id:'fixture-episode'},resource_identity:resource,interface_profile:'g4a1-1.0'};
function fixtures(){
 Object.assign(globalThis,{window:{location:{origin:'http://fixture'}}});
 const scene={...envelope,schema_version:'unirobot-mobilecar-geometry-1',data_source:'live_native_http_with_verified_compiled_geometry',geometry_provenance:{synthetic_fixture:true},data:{...sceneData,mesh_assets:sceneData.mesh_assets.map(a=>({...a,uri:`/api/v1/mobilecar/scene/assets/${a.asset_id}?sha256=${a.sha256}`,coordinate_space:'mujoco_compiled_mesh',units:'m',mesh_preprocessing_applied:true,source_sha256:a.sha256,source_mesh_name:a.asset_id+'_mesh'}))},objects:[],world_pose_semantics:'compiled_initial_layout_not_live_object_state'} as unknown as SceneRead;
 const caps={...envelope,data:{...capsData,...resource},platform_commands_available:false,platform_recording_available:false,platform_replay_available:false} as unknown as CapabilitiesRead;
 const snapshot={...envelope,data:{time:{...native,feedback_time_s:10},arm_joint_names:capsData.arm_joint_names,actual:native,target:{base_velocity:{frame_id:'base_link',vx_m_s:0,vy_m_s:0,wz_rad_s:0},user_joint_positions_rad:[.2,0,0,0,0],model_joint_positions_rad:[.2,0,0,-Math.PI/2,0],gripper_width_m:.025,gripper_model_drive_position_rad:-1.07,command_id:null,tcp:null},authority:{base_owner_session_id:null,arm_owner_session_id:null,authorizes_caller:false,lease_status:'not_exposed'},recording:{status:'IDLE',command_capture_ready:false,recording_segment_id:null},sensors:[]}} as unknown as SnapshotRead;
 return {scene,caps,snapshot};
}
describe('read wire boundary',()=>{
 it('maps actual, backend target and local target separately without diagnostics or readiness',()=>{
  const {scene,caps,snapshot}=fixtures();const v=initializeSample(scene,caps,snapshot);const t=jointTarget(v,null,'joint1',.3);
  expect(v.actual.diagnostics).toEqual({});expect(v.source.is_platform_session).toBe(false);
  expect(v.actual.model_joint_positions_rad).toEqual(native.model_joint_positions_rad);expect(v.live!.target.user_joint_positions_rad[0]).toBe(.2);expect(t.jointModelRad.joint1).toBe(.3);
  expect(v.actual.arm.model_joint_positions_rad[3]).toBeCloseTo(-Math.PI/2);
 });
 it('retains scene identity for renderer reuse during snapshot updates',()=>{
  const {scene,caps,snapshot}=fixtures();const v=initializeSample(scene,caps,snapshot);const next=mapSnapshot(v,{...snapshot,data:{...snapshot.data,time:{...snapshot.data.time,sim_time_s:99}}});
  expect(next.scene).toBe(v.scene);expect(next.actual.sim_time_s).toBe(99);expect(v.actual.sim_time_s).not.toBe(99);
 });
 it.each(['run','resource','profile'])('rejects changed %s identity before updating actual',kind=>{
  const {scene,caps,snapshot}=fixtures();const v=initializeSample(scene,caps,snapshot);
  const changed=structuredClone(snapshot);
  if(kind==='run')changed.runtime_identity.episode_id='other';else if(kind==='resource')changed.resource_identity.scene_id='other';else changed.interface_profile='other';
  expect(()=>mapSnapshot(v,changed)).toThrow(IdentityChanged);
  expect(()=>initializeSample(scene,caps,changed)).toThrow(IdentityChanged);
 });
 it('does not guess zero mapping for a different model',()=>{
  const {scene,caps,snapshot}=fixtures();for(const e of [scene,caps,snapshot])e.resource_identity={...e.resource_identity,model_sha256:'f'.repeat(64)};
  scene.data={...scene.data,model_sha256:'f'.repeat(64)};
  const v=initializeSample(scene,caps,snapshot);expect(v.armSpec).toBeNull();expect(()=>jointTarget(v,null,'joint1',0)).toThrow('映射');
 });
 it('rejects asset URLs that omit or change the requested digest',()=>{
  const {scene,caps,snapshot}=fixtures();scene.data.mesh_assets[0].uri='/api/v1/mobilecar/scene/assets/base_link';
  expect(()=>initializeSample(scene,caps,snapshot)).toThrow('摘要');
 });
});

describe('compiled mesh coordinates at the service boundary',()=>{
 it('rejects the old raw-STL scene instead of labeling it a corrected live model',()=>{
  const {scene,caps,snapshot}=fixtures();scene.schema_version='unirobot-mobilecar-read-1';scene.data_source='live_native_http';
  expect(()=>initializeSample(scene,caps,snapshot)).toThrow('编译网格');
 });
 it('retains mesh provenance and refuses ambiguous coordinates or double scaling',()=>{
  const {scene,caps,snapshot}=fixtures();const v=initializeSample(scene,caps,snapshot);
  expect(v.scene.mesh_assets[0].coordinate_space).toBe('mujoco_compiled_mesh');expect(v.live!.geometryProvenance).toEqual({synthetic_fixture:true});
  scene.data.mesh_assets[0].mesh_preprocessing_applied=false;expect(()=>initializeSample(scene,caps,snapshot)).toThrow('坐标约定');
 });
});
