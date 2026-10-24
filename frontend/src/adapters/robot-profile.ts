import type { ArmSpec, Capabilities, ResourceIdentity } from './types';
// Reference model metadata, not a captured state or ground truth observation.
// Source: mobileCar compiled_arm_spec; provenance retained in docs/provenance.md.
// The read API does not yet expose this mapping. This profile only enables local
// kinematic candidates for this exact model; it never grants execution eligibility.
export const profileId = 'landerpi-3ca3d6d0-local-kinematics-v1';
export function localKinematicProfile(resource: ResourceIdentity, caps: Capabilities): ArmSpec|null {
 if(resource.model_sha256!=='3ca3d6d0a92a48bbfbce5ac7a04e37a0f7cf7a73297045ae327bf461ad50e280'
   ||caps.arm_joint_names.join(',')!=='joint1,joint2,joint3,joint4,joint5'||caps.tcp_parent_body!=='guide_rod_link')return null;
 return {user_coordinates:{zero_model_rad:[0,0,0,-Math.PI/2,0],direction:[1,1,1,1,1]},
   tcp:{body:'guide_rod_link',position:[-0.0030427614580541846,-0.0007270026737451543,0.01995871637761593]},mimic:{},
   limits:Object.fromEntries(caps.arm_joint_names.map((name,i)=>[name,caps.arm_user_limits_rad[i].map(v=>v+(i===3?-Math.PI/2:0)) as [number,number]]))};
}
