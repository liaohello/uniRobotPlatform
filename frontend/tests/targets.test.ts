import { describe,it,expect } from 'vitest';
import scene from '../public/sample/scene.json';
import actual from '../public/sample/snapshot.json';
import capabilities from '../public/sample/capabilities.json';
import armSpec from '../public/sample/arm-spec.json';
import source from '../public/sample/provenance.json';
import type { ViewSample } from '../src/adapters/types';
import {jointTarget,tcpTarget,userJoint} from '../src/app/state';
import {PreviewKinematics} from '../src/viewport/kinematics';
const sample={scene,actual,capabilities,armSpec,source:{...source,kind:'frozen',label:'frozen test'}} as unknown as ViewSample;
describe('frozen native geometry and local target boundary',()=>{
 it('matches native frozen TCP with model joints and Z-up FK',()=>{
  const p=new PreviewKinematics(sample.scene,sample.actual,sample.armSpec!).forward(sample.actual.model_joint_positions_rad);
  expect(Math.hypot(...p.map((v,i)=>v-sample.actual.tcp.position_m[i]))).toBeLessThan(0.00001);
 });
 it('edits one joint while preserving prior other targets and immutable Actual',()=>{
  const before=JSON.stringify(sample.actual);const first=jointTarget(sample,null,'joint1',0.2);const second=jointTarget(sample,first,'joint2',0.1);
  expect(userJoint(sample,second,'joint1')).toBeCloseTo(0.2);expect(userJoint(sample,second,'joint2')).toBeCloseTo(0.1);
  expect(second.revision).toBe(2);expect(JSON.stringify(sample.actual)).toBe(before);
 });
 it('maps joint4 user zero to model -pi/2 without changing units',()=>{
  const target=jointTarget(sample,null,'joint4',0);expect(target.jointModelRad.joint4).toBeCloseTo(-Math.PI/2);
  expect(userJoint(sample,target,'joint4')).toBeCloseTo(0);
 });
 it('rejects out-of-limit and invalid target values',()=>{
  expect(()=>jointTarget(sample,null,'joint1',20)).toThrow('限位');expect(()=>tcpTarget(sample,null,[NaN,0,0])).toThrow('有限');
 });
 it('derives a local position-only IK candidate without mutating source or granting readiness',()=>{
  const before=JSON.stringify(sample);const seed=jointTarget(sample,null,'joint2',0.06);const next=tcpTarget(sample,null,seed.tcpWorldM);
  expect(next.preview).toBe('local-position-ik');expect(next.residualM).toBeLessThan(0.002);expect(JSON.stringify(sample)).toBe(before);
  expect(sample.source.is_platform_session).toBe(false);
 });
 it('preserves an unreachable Target but does not label its ghost as valid',()=>{
  const next=tcpTarget(sample,null,[3,3,3]);expect(next.preview).toBe('unreachable');expect(next.residualM).toBeGreaterThan(1);
  expect(next.tcpWorldM).toEqual([3,3,3]);
 });
});
