import {describe,it,expect} from 'vitest';
import sceneData from '../public/sample/scene.json';
import native from '../public/sample/snapshot.json';
import capsData from '../public/sample/capabilities.json';
import {initializeSample,mapSnapshot,readEnvelope,IdentityChanged,type SceneRead,type CapabilitiesRead,type SnapshotRead} from '../src/adapters/mobilecar-read';
import {liveKinematicProfile,unavailableKinematics,type KinematicsRead} from '../src/adapters/robot-profile';
import type {ExecutionRecipe} from '../src/adapters/platform-config';
import {jointTarget} from '../src/app/state';
// Synthetic wire fixtures. Frozen captures below provide geometry only; not live evidence.
const resource={contract_version:sceneData.contract_version,model_id:sceneData.model_id,model_sha256:sceneData.model_sha256,scene_id:sceneData.scene_id};
const runtime={run_id:'fixture-run',backend_generation:1,episode_id:'fixture-episode'};
const envelope={schema_version:'unirobot-mobilecar-read-1',data_source:'live_native_http',adapter_id:'mobilecar',robot_id:'landerpi',read_only:true,session_ready:false,platform_session_id:null,retrieved_at:'fixture',runtime_identity:runtime,resource_identity:resource,interface_profile:'g4a1-1.0'};
const digest='f'.repeat(64);
const recipe={schema_version:'unirobot-execution-recipe-1',recipe_id:'mobilecar.g1.teleop',recipe_revision:2,recipe_fingerprint:'d'.repeat(64),
 expected:{model_id:resource.model_id,model_sha256:resource.model_sha256,scene_id:resource.scene_id},
 required_protocols:{session_binding:'m1-binding-1',recording_begin:'m1-recording-1'},kinematics:{profile_id:'landerpi.kinematics.v1',digest},sources:[],attestation:{}} as ExecutionRecipe;
const kinematics:KinematicsRead={schema_version:'unirobot-mobilecar-kinematics-1',profile_id:'landerpi.kinematics.v1',digest,authority:'platform_reference_not_native_attested',
 profile:{schema_version:1,profile_id:'landerpi.kinematics.v1',robot_id:'landerpi',
  arm:{joint_names:capsData.arm_joint_names,user_direction:[1,1,1,1,1],zero_model_rad:[0,0,0,-Math.PI/2,0],zero_status:'user_defined_photo_pose_not_hardware_500'},
  gripper:{min_width_m:.012,max_width_m:.05,zero_width_m:.025,zero_model_rad:-1.077632656580025,width_per_drive_rad_m:.023199,jaw_origin_correction_m:.000524,source_gap_m:.048951,mimic:{}},
  tcp:{site:'grasp_tcp',parent_body:'guide_rod_link',position_m:[-.0030427614580541846,-.0007270026737451543,.01995871637761593],orientation_xyzw:null,orientation_status:'not_specified_in_source'},
  camera_mount:{parent_body:'link4',status:'source_topology_not_rigid_to_tcp'},limitations:[]},
 sources:[],runtime_identity:runtime,
 consistency:{joint_order_consistent:true,user_limits_consistent:true,tcp_mount_consistent:true,camera_mount_consistent:true,gripper_limits_consistent:true,max_user_limit_error_rad:0},limitations:[]};
function fixtures(){
 Object.assign(globalThis,{window:{location:{origin:'http://fixture'}}});
 const binding={bundle_sha256:'b'.repeat(64),content_identity_sha256:'c'.repeat(64),exported_runtime_identity:{...runtime},observed_runtime_identity:{...runtime},content_matches:true as const,runtime_identity_matches:true,association:'content_matches_export_identity' as const,revalidated_at:'fixture'};
 const scene={...envelope,schema_version:'unirobot-mobilecar-geometry-2',data_source:'live_native_http_with_verified_compiled_geometry',geometry_provenance:{bundle_sha256:'b'.repeat(64),runtime_identity:{...runtime}},geometry_binding:binding,data:{...sceneData,mesh_assets:sceneData.mesh_assets.map(a=>({...a,uri:`/api/v1/mobilecar/scene/assets/${a.asset_id}?sha256=${a.sha256}`,coordinate_space:'mujoco_compiled_mesh',units:'m',mesh_preprocessing_applied:true,source_sha256:a.sha256,source_mesh_name:a.asset_id+'_mesh'}))},objects:[],world_pose_semantics:'compiled_initial_layout_not_live_object_state'} as unknown as SceneRead;
 const caps={...envelope,data:{...capsData,...resource},platform_commands_available:false,platform_recording_available:false,platform_replay_available:false} as unknown as CapabilitiesRead;
 const snapshot={...envelope,data:{time:{...native,feedback_time_s:10},arm_joint_names:capsData.arm_joint_names,actual:native,target:{base_velocity:{frame_id:'base_link',vx_m_s:0,vy_m_s:0,wz_rad_s:0},user_joint_positions_rad:[.2,0,0,0,0],model_joint_positions_rad:[.2,0,0,-Math.PI/2,0],gripper_width_m:.025,gripper_model_drive_position_rad:-1.07,command_id:null,tcp:null},authority:{base_owner_session_id:null,arm_owner_session_id:null,authorizes_caller:false,lease_status:'not_exposed'},recording:{status:'IDLE',command_capture_ready:false,recording_segment_id:null},sensors:[]}} as unknown as SnapshotRead;
 const mapping=liveKinematicProfile(kinematics,scene.robot_id,caps.data,scene.data,recipe);
 return {scene,caps,snapshot,mapping,binding};
}
describe('read wire boundary',()=>{
 it('maps actual, backend target, versioned kinematics and local target separately',()=>{
  const {scene,caps,snapshot,mapping}=fixtures();const v=initializeSample(scene,caps,snapshot,mapping);const t=jointTarget(v,null,'joint1',.3);
  expect(v.actual.diagnostics).toEqual({});expect(v.source.is_platform_session).toBe(false);
  expect(v.actual.model_joint_positions_rad).toEqual(native.model_joint_positions_rad);expect(v.live!.target.user_joint_positions_rad[0]).toBe(.2);expect(t.jointModelRad.joint1).toBe(.3);
  expect(v.armSpec!.profileId).toBe('landerpi.kinematics.v1');expect(v.live!.kinematics.status).toBe('verified');
  expect(v.actual.arm.model_joint_positions_rad[3]).toBeCloseTo(-Math.PI/2);
 });
 it('retains scene identity for renderer reuse during snapshot updates',()=>{
  const {scene,caps,snapshot,mapping}=fixtures();const v=initializeSample(scene,caps,snapshot,mapping);const next=mapSnapshot(v,{...snapshot,data:{...snapshot.data,time:{...snapshot.data.time,sim_time_s:99}}});
  expect(next.scene).toBe(v.scene);expect(next.actual.sim_time_s).toBe(99);expect(v.actual.sim_time_s).not.toBe(99);
 });
 it('treats a run identity change as runtime-only while content stays verified',()=>{
  const {scene,caps,snapshot,mapping}=fixtures();const v=initializeSample(scene,caps,snapshot,mapping);
  const changed=structuredClone(snapshot);changed.runtime_identity={...runtime,episode_id:'next-episode',backend_generation:2};
  const next=mapSnapshot(v,changed);
  expect(next.scene).toBe(v.scene);expect(next.live!.contentKey).toBe(v.live!.contentKey);
  expect(next.source.identity.episode_id).toBe('next-episode');expect(next.actual.backend_generation).toBe(2);
 });
 it.each(['resource','profile'])('rejects changed %s identity before updating actual',kind=>{
  const {scene,caps,snapshot,mapping}=fixtures();const v=initializeSample(scene,caps,snapshot,mapping);
  const changed=structuredClone(snapshot);
  if(kind==='resource')changed.resource_identity.scene_id='other';else changed.interface_profile='other';
  expect(()=>mapSnapshot(v,changed)).toThrow(IdentityChanged);
 });
 it('accepts a scene/snapshot runtime mismatch only when resource content matches',()=>{
  const {scene,caps,snapshot,mapping}=fixtures();const changed=structuredClone(snapshot);changed.runtime_identity={...runtime,episode_id:'later-episode'};
  const v=initializeSample(scene,caps,changed,mapping);
  expect(v.live!.runtimeMismatchAtInit).toBe(true);expect(v.source.identity.episode_id).toBe('later-episode');
 });
 it('rejects a geometry-2 binding that does not describe the envelope runtime',()=>{
  const {scene,caps,snapshot,mapping}=fixtures();scene.geometry_binding={...scene.geometry_binding!,observed_runtime_identity:{...runtime,episode_id:'other'}};
  expect(()=>initializeSample(scene,caps,snapshot,mapping)).toThrow('geometry-2');
 });
 it('still accepts geometry-1 without inventing a content digest',()=>{
  const {scene,caps,snapshot,mapping}=fixtures();scene.schema_version='unirobot-mobilecar-geometry-1';scene.geometry_binding=undefined;
  const v=initializeSample(scene,caps,snapshot,mapping);expect(v.live!.geometryBinding).toBeUndefined();expect(v.live!.contentKey).toContain('geometry-1');
 });
 it('does not guess a mapping when compatible kinematics metadata is absent',()=>{
  const {scene,caps,snapshot}=fixtures();const v=initializeSample(scene,caps,snapshot,null);
  expect(v.armSpec).toBeNull();expect(v.live!.kinematics.status).toBe('unavailable');expect(()=>jointTarget(v,null,'joint1',0)).toThrow('映射');
 });
 it('rejects asset URLs that omit or change the requested digest',()=>{
  const {scene,caps,snapshot,mapping}=fixtures();scene.data.mesh_assets[0].uri='/api/v1/mobilecar/scene/assets/base_link';
  expect(()=>initializeSample(scene,caps,snapshot,mapping)).toThrow('摘要');
 });
 it('projects envelope capability flags without promoting them to readiness',()=>{
  const {scene,caps,snapshot,mapping}=fixtures();caps.resource_matches_pin=true;caps.deployed_content_verified=true;caps.recording_required_for_motion=true;
  const v=initializeSample(scene,caps,snapshot,mapping);
  expect(v.live!.session).toEqual({ready:false,platformSessionId:null,commandsAvailable:false,recordingAvailable:false,replayAvailable:false,
   resourceMatchesPin:true,deployedContentVerified:true,recordingRequiredForMotion:true,contractVersion:resource.contract_version});
 });
 it('rejects an envelope that claims a platform session it cannot own',async()=>{
  const {caps}=fixtures();
  Object.assign(globalThis,{fetch:async()=>({ok:true,json:async()=>({...caps,session_ready:true})})});
  await expect(readEnvelope('/api/v1/mobilecar/capabilities',new AbortController().signal)).rejects.toThrow('envelope');
 });
});
describe('versioned kinematics metadata',()=>{
 it('maps zero/direction, TCP site, limits and orientation=null without inventing a pose',()=>{
  const {scene,caps,mapping}=fixtures();const spec=mapping.armSpec!;
  expect(mapping.report.status).toBe('verified');expect(spec.tcp.site).toBe('grasp_tcp');expect(spec.tcp.orientation_xyzw).toBeNull();
  expect(spec.tcp.orientation_status).toBe('not_specified_in_source');expect(spec.user_coordinates.zero_model_rad[3]).toBeCloseTo(-Math.PI/2);
  expect(spec.limits.joint4[0]).toBeCloseTo(-2.09);expect(spec.limits.joint4[1]).toBeCloseTo(2.09);
  expect(liveKinematicProfile(kinematics,scene.robot_id,caps.data,scene.data,recipe).report.checks.find(c=>c.key==='tcp_mount')?.status).toBe('passed');
 });
 it('disables local preview when the recipe pin or live consistency disagrees',()=>{
  const {scene,caps}=fixtures();
  const wrongModel=liveKinematicProfile(kinematics,scene.robot_id,caps.data,scene.data,{...recipe,expected:{...recipe.expected,model_sha256:'0'.repeat(64)}});
  expect(wrongModel.armSpec).toBeNull();expect(wrongModel.report.status).toBe('mismatch');expect(wrongModel.report.reason).toContain('模型');
  const inconsistent=liveKinematicProfile({...kinematics,consistency:{...kinematics.consistency,user_limits_consistent:false}},scene.robot_id,caps.data,scene.data,recipe);
  expect(inconsistent.armSpec).toBeNull();expect(inconsistent.report.reason).toContain('一致性');
 });
 it('reports missing metadata instead of falling back to a fixed profile',()=>{
  const report=unavailableKinematics('kinematics HTTP 503');expect(report.status).toBe('unavailable');expect(report.reason).toContain('503');
 });
});
describe('compiled mesh coordinates at the service boundary',()=>{
 it('rejects the old raw-STL scene instead of labeling it a corrected live model',()=>{
  const {scene,caps,snapshot,mapping}=fixtures();scene.schema_version='unirobot-mobilecar-read-1';scene.data_source='live_native_http';
  expect(()=>initializeSample(scene,caps,snapshot,mapping)).toThrow('编译网格');
 });
 it('retains mesh provenance and refuses ambiguous coordinates or double scaling',()=>{
  const {scene,caps,snapshot,mapping}=fixtures();const v=initializeSample(scene,caps,snapshot,mapping);
  expect(v.scene.mesh_assets[0].coordinate_space).toBe('mujoco_compiled_mesh');expect(v.live!.geometryProvenance).toEqual({bundle_sha256:'b'.repeat(64),runtime_identity:runtime});
  scene.data.mesh_assets[0].mesh_preprocessing_applied=false;expect(()=>initializeSample(scene,caps,snapshot,mapping)).toThrow('坐标约定');
 });
});
