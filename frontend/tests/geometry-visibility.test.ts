import {describe,it,expect} from 'vitest';
import * as THREE from 'three';
import {SceneView,materialFor,applyMeshCoordinateSpace} from '../src/viewport/native-scene-view.js';
import type {SceneGeom} from '../src/adapters/types';
function geom(alpha:number,collision=false,group=0):SceneGeom{return {name:'fixture',geom_type:'box',size_m:[.1,.05,.02],local_transform:{position_m:[0,0,0],orientation_xyzw:[0,0,0,1]},rgba:[.2,.3,.4,alpha],mesh_asset_id:null,collision,group};}
describe('authored visibility and transparent surfaces',()=>{
 it('never builds zero-alpha geometry, including incorrectly exported collision flags',()=>{
   for(const ghost of [false,true])expect(SceneView.prototype._buildGeom.call({} as SceneView,geom(0),ghost)).toBeNull();
 });
 it('keeps visible basic geometry even when it can collide or has a non-visual group',()=>{
   const group=SceneView.prototype._buildGeom.call({} as SceneView,geom(1,true,3),false)!;
   const mesh=group.children[0] as THREE.Mesh<THREE.BoxGeometry,THREE.MeshStandardMaterial>;
   expect(mesh.isMesh).toBe(true);expect(mesh.geometry.parameters.width).toBe(.2);expect(mesh.material.opacity).toBe(1);expect(mesh.material.transparent).toBe(false);
   mesh.geometry.dispose();mesh.material.dispose();
 });
 it('blends semitransparent Actual without opaque depth occlusion',()=>{
   const material=materialFor([.2,.3,.4,.35]);expect(material.transparent).toBe(true);expect(material.opacity).toBe(.35);expect(material.depthWrite).toBe(false);material.dispose();
 });
 it('preserves visible Ghost candidates while respecting the source alpha',()=>{
   const opaque=materialFor([.2,.3,.4,1],{ghost:true});const translucent=materialFor([.2,.3,.4,.5],{ghost:true});
   expect(opaque.opacity).toBe(.26);expect(translucent.opacity).toBe(.13);expect(translucent.transparent).toBe(true);expect(translucent.depthWrite).toBe(false);opaque.dispose();translucent.dispose();
 });
});

describe('mesh coordinate conventions',()=>{
 it('never re-scales compiled vertices',()=>{
  const geometry=new THREE.BoxGeometry(2,4,6);applyMeshCoordinateSpace(geometry,{asset_id:'fixture',uri:'fixture',sha256:'fixture',coordinate_space:'mujoco_compiled_mesh'},[2,3,4]);
  geometry.computeBoundingBox();expect(geometry.boundingBox!.getSize(new THREE.Vector3()).toArray()).toEqual([2,4,6]);geometry.dispose();
 });
 it('rejects unspecified mesh coordinates instead of guessing a transform',()=>{
  const geometry=new THREE.BufferGeometry();expect(()=>applyMeshCoordinateSpace(geometry,{asset_id:'fixture',uri:'fixture',sha256:'fixture'},[1,1,1])).toThrow('mesh_coordinates_unavailable');geometry.dispose();
 });
});
