import * as THREE from 'three';
import { TransformControls } from 'three/addons/controls/TransformControls.js';
import { SceneView } from './native-scene-view.js';
import type { LocalTarget, Vec3, ViewSample } from '../adapters/types';
export type Tool = 'select' | 'joint' | 'tcp';
export interface SceneCallbacks {
 select(id: string | null): void; joint(name: string, userRad: number): void;
 tcp(position: Vec3): void; notice(message: string): void; interaction(active: boolean): void; assetError(message:string):void;
}
export const rendererLifecycle = { created: 0, disposed: 0, active: 0 };
export class WorkbenchScene extends SceneView {
 private events!: AbortController;
 private gizmo!: TransformControls;
 private proxy = new THREE.Object3D();
 private selectionBox = new THREE.Box3Helper(new THREE.Box3(), 0x6bd9e7);
 private sample: ViewSample;
 private callbacks: SceneCallbacks;
 private target: LocalTarget | null = null;
 private selected: string | null = 'arm';
 private tool: Tool = 'select';
 private pointerDown: {x: number;y: number; id: number; gizmo: boolean; hit: string | null} | null = null;
 private jointDrag: { name: string; value: number; start: THREE.Quaternion; axis: THREE.Vector3 } | null = null;
 private hovered: string | null = null;
 constructor(container: HTMLElement, sample: ViewSample, callbacks: SceneCallbacks) {
   super(container,{ onNotice: callbacks.notice, onAssetError: callbacks.assetError });
   this.sample=sample; this.callbacks=callbacks;
   rendererLifecycle.created++;rendererLifecycle.active++;
   this.scene.background=new THREE.Color('#14202b');this.scene.fog=null;
   this.scene.traverse(node=>{if(node instanceof THREE.DirectionalLight){node.position.set(1.4,2.2,1.0);node.intensity=2.2;}if(node instanceof THREE.HemisphereLight)node.intensity=1.6;});
   this.scene.add(this.selectionBox);this.selectionBox.visible=false;
   this.mujocoRoot.add(this.proxy);
   this.gizmo=new TransformControls(this.camera,this.renderer.domElement);
   this.gizmo.setSize(0.78);this.gizmo.setSpace('local');
   this.scene.add(this.gizmo.getHelper());
   this.gizmo.addEventListener('dragging-changed',event=>{
     this.controls.enabled=!event.value;
     this.callbacks.interaction(Boolean(event.value));
     if (!event.value) { this.jointDrag=null;this.updateGizmo(); }
   });
   this.gizmo.addEventListener('mouseDown',()=>{
     if (this.tool==='joint') {
       const link=this.manifest.links.find(l=>l.name===this.selected);
       if (link?.joint_name) this.jointDrag={name:link.joint_name,value:this.userJointValue(link.joint_name),start:this.proxy.quaternion.clone(),axis:new THREE.Vector3(...link.joint_axis).normalize()};
     }
   });
   this.gizmo.addEventListener('objectChange',()=>this.onGizmoChange());
   this.gizmo.addEventListener('change',()=>this._requestRender(true));
   this.bindWorkbenchPointer();
   this.setManifest(sample.scene);this.updateSnapshot(sample.actual);
   this.worldRoot.traverse(node=>{if(node instanceof THREE.Mesh && node.userData.geom?.geom_type==='plane')(node.material as THREE.MeshStandardMaterial).color.set('#233744');});
   this.setSelection('arm');this.updateGizmo();
   this.configureRendering({preferred_pixel_ratio:1,max_pixel_ratio:1.5,adaptive_rendering:true});
   this.renderer.shadowMap.enabled=false;
   const canvas=this.renderer.domElement; canvas.tabIndex=0;canvas.setAttribute('aria-label','机器人三维视口');canvas.setAttribute('role','application');
   const finish=()=>this.cancelGesture();
   window.addEventListener('blur',finish,{signal:this.events.signal});
   document.addEventListener('visibilitychange',()=>{if(document.hidden)finish();},{signal:this.events.signal});
 }
 // Replaces only native's screen-plane target-ball input; TransformControls owns target handles.
 override _bindPointer() {}
 private bindWorkbenchPointer() {
   this.events=new AbortController();const canvas=this.renderer.domElement;const signal=this.events.signal;
   canvas.addEventListener('pointerdown',event=>{
     if(event.button!==0)return;
     canvas.focus({preventScroll:true});
     const isGizmo=Boolean(this.gizmo?.axis && this.gizmo.enabled);
     const hit=isGizmo?null:this.pick(event);
     this.pointerDown={x:event.clientX,y:event.clientY,id:event.pointerId,gizmo:isGizmo,hit};
     if(hit && !isGizmo)this.controls.enabled=false;
   },{capture:true,signal});
   canvas.addEventListener('pointerup',event=>{
     const down=this.pointerDown;this.pointerDown=null;
     if(down && !down.gizmo && Math.hypot(event.clientX-down.x,event.clientY-down.y)<5) this.callbacks.select(down.hit);
     if(!this.gizmo?.dragging)this.controls.enabled=true;
   },{signal});
   canvas.addEventListener('pointercancel',()=>this.cancelGesture(),{signal});
   canvas.addEventListener('lostpointercapture',()=>{if(this.gizmo?.dragging)this.cancelGesture();},{signal});
   canvas.addEventListener('dblclick',event=>{
     const hit=this.pick(event);
     if(hit && this.isArmLink(hit))this.callbacks.select('arm');
   },{signal});
   canvas.addEventListener('pointermove',event=>{
     if(this.pointerDown || this.gizmo?.dragging)return;
     const id=this.pick(event);
     if(id!==this.hovered){this.hovered=id;canvas.style.cursor=id?'pointer':'grab';this.highlight();}
   },{signal});
   canvas.addEventListener('pointerleave',()=>{this.hovered=null;this.highlight();},{signal});
 }
 private pick(event: PointerEvent | MouseEvent) {
   this._setPointer(event as PointerEvent);this.raycaster.setFromCamera(this.pointer,this.camera);
   this.scene.updateMatrixWorld(true);
   const hits=this.raycaster.intersectObjects([this.actualRoot,this.worldRoot],true);
   for(const hit of hits){
     let object:THREE.Object3D|null=hit.object;let visible=true;
     for(let n:THREE.Object3D|null=object;n;n=n.parent)if(!n.visible)visible=false;
     if(!visible || hit.object.userData.meshPending)continue;
     while(object){if(object.userData.sceneLink)return String(object.userData.sceneLink.name);object=object.parent;}
   }
   return null;
 }
 private isArmLink(id:string) {
   let link=this.manifest.links.find(l=>l.name===id);
   while(link){if(link.joint_name==='joint1')return true;link=this.manifest.links.find(l=>l.name===link!.parent_name);}
   return false;
 }
 private highlight() {
   for(const [id,{group}] of [...this.linkGroups,...this.worldGroups]){
     const chosen=id===this.selected || (this.selected==='arm' && this.isArmLink(id));
     group.traverse(node=>{
       if(!(node instanceof THREE.Mesh))return;
       const materials=Array.isArray(node.material)?node.material:[node.material];
       for(const material of materials)if(material instanceof THREE.MeshStandardMaterial){material.emissive.set(chosen?'#114e63':id===this.hovered?'#293548':'#000000');material.emissiveIntensity=chosen?0.7:0.35;}
     });
   }
   const entry=this.linkGroups.get(this.selected??'')??this.worldGroups.get(this.selected??'');
   this.selectionBox.visible=Boolean(entry);
   if(entry)this.selectionBox.box.setFromObject(entry.group);
   this._requestRender(true);
 }
 updateActual(sample:ViewSample){
   this.sample=sample;this.updateSnapshot(sample.actual);this.syncTarget(this.target);this.highlight();
 }
 setSelection(id:string|null) {this.selected=id;this.highlight();this.updateGizmo();}
 setTool(tool:Tool){this.cancelGesture();this.tool=tool;this.updateGizmo();}
 syncTarget(target:LocalTarget|null){
   this.target=target;this._clearPlan();
   this.setTarget(target?.tcpWorldM??this.sample.actual.tcp.position_m,Boolean(target));
   if(target){
     if(target.preview!=='unreachable'){
       const base=this.ghostGroups.get('base_link')?.group;const actualBase=this.linkGroups.get('base_link')?.group;
       if(base && actualBase){base.position.copy(actualBase.position);base.quaternion.copy(actualBase.quaternion);}
       this._applyJointValues(target.jointModelRad,true);this.ghostRoot.visible=true;
       this.ghostRoot.traverse(node=>{if(node instanceof THREE.Mesh){
         let parent:THREE.Object3D|null=node;let linkName='';
         while(parent){if(parent.userData.sceneLink){linkName=parent.userData.sceneLink.name;break;}parent=parent.parent;}
         node.visible=this.isArmLink(linkName);const m=node.material as THREE.MeshStandardMaterial;m.color.set('#58c5fa');m.opacity=0.30*(node.userData.geom?.rgba?.[3]??1);
       }});
     }
     const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(...this.sample.actual.tcp.position_m),new THREE.Vector3(...target.tcpWorldM)]),new THREE.LineDashedMaterial({color:0xf4bc60,dashSize:0.009,gapSize:0.006,transparent:true,opacity:0.8}));
     line.computeLineDistances();this.planObject=line;this.mujocoRoot.add(line);
   }
   if(!this.gizmo.dragging)this.updateGizmo();
   this._requestRender(true);
 }
 private userJointValue(name:string){const i=this.sample.capabilities.arm_joint_names.indexOf(name);return this.target?(this.target.jointModelRad[name]-this.sample.armSpec!.user_coordinates.zero_model_rad[i])/this.sample.armSpec!.user_coordinates.direction[i]:this.sample.actual.arm.user_joint_positions_rad[i];}
 private updateGizmo(){
   if(!this.gizmo)return;
   this.gizmo.detach();this.gizmo.enabled=false;
   if(this.tool==='select'||!this.sample.armSpec)return;
   this.proxy.quaternion.identity();
   this.gizmo.showX=true;this.gizmo.showY=true;this.gizmo.showZ=true;
   if(this.tool==='tcp'){
     this.proxy.position.fromArray(this.target?.tcpWorldM??this.sample.actual.tcp.position_m);this.gizmo.setMode('translate');
   }else{
     const entry=(this.target?this.ghostGroups:this.linkGroups).get(this.selected??'');
     if(!entry?.link.joint_name || !this.sample.capabilities.arm_joint_names.includes(entry.link.joint_name))return;
     this.scene.updateMatrixWorld(true);
     const position=entry.group.getWorldPosition(new THREE.Vector3());this.proxy.position.copy(this.mujocoRoot.worldToLocal(position));
     const parentQuat=this.mujocoRoot.getWorldQuaternion(new THREE.Quaternion()).invert();
     this.proxy.quaternion.copy(parentQuat.multiply(entry.group.getWorldQuaternion(new THREE.Quaternion())));
     const axis=entry.link.joint_axis;const dominant=axis.map(Math.abs).indexOf(Math.max(...axis.map(Math.abs)));
     this.gizmo.showX=dominant===0;this.gizmo.showY=dominant===1;this.gizmo.showZ=dominant===2;this.gizmo.setMode('rotate');
   }
   this.gizmo.attach(this.proxy);this.gizmo.enabled=true;this._requestRender(true);
 }
 private onGizmoChange(){
   if(!this.gizmo.dragging)return;
   if(this.tool==='tcp')this.callbacks.tcp(this.proxy.position.toArray() as Vec3);
   else if(this.jointDrag){
     const d=this.jointDrag;const relative=d.start.clone().invert().multiply(this.proxy.quaternion).normalize();
     let angle=2*Math.atan2(new THREE.Vector3(relative.x,relative.y,relative.z).dot(d.axis),relative.w);
     if(angle>Math.PI)angle-=2*Math.PI;if(angle< -Math.PI)angle+=2*Math.PI;
     const i=this.sample.capabilities.arm_joint_names.indexOf(d.name);const [min,max]=this.sample.capabilities.arm_user_limits_rad[i];
     this.callbacks.joint(d.name,Math.max(min,Math.min(max,d.value+angle/this.sample.armSpec!.user_coordinates.direction[i])));
   }
 }
 cancelGesture(){
   this.pointerDown=null;
   if(this.gizmo?.dragging){this.gizmo.dragging=false;this.jointDrag=null;}
   this.controls.enabled=true;
 }
 override fitView(){
   const box=new THREE.Box3().setFromObject(this.actualRoot);
   if(box.isEmpty())return;
   const center=box.getCenter(new THREE.Vector3());const d=Math.max(box.getSize(new THREE.Vector3()).length()*1.2,0.75);
   this.controls.target.copy(center);this.camera.position.copy(center).addScaledVector(new THREE.Vector3(0.95,0.65,0.95).normalize(),d);this.camera.near=0.005;this.camera.far=30;this.camera.updateProjectionMatrix();this.controls.update();this._requestRender(true);
 }
 standardView(view:'front'|'side'|'top'){
   const d=this.camera.position.distanceTo(this.controls.target);
   const direction=view==='top'?new THREE.Vector3(0,1,0.0001):view==='front'?new THREE.Vector3(0,0,1):new THREE.Vector3(1,0,0);
   this.camera.position.copy(this.controls.target).addScaledVector(direction,d);this.controls.update();this._requestRender(true);
 }
 focusSelection(){
   const entry=this.linkGroups.get(this.selected??'')??this.worldGroups.get(this.selected??'');
   if(!entry){this.fitView();return;}
   const box=new THREE.Box3().setFromObject(entry.group);const center=box.getCenter(new THREE.Vector3());const delta=this.camera.position.clone().sub(this.controls.target).normalize();
   this.controls.target.copy(center);this.camera.position.copy(center).addScaledVector(delta,Math.max(box.getSize(new THREE.Vector3()).length()*1.8,0.25));this.controls.update();this._requestRender(true);
 }
 setLayers(ghost:boolean,world:boolean){this.ghostRoot.visible=ghost && Boolean(this.target) && this.target!.preview!=='unreachable';this.worldRoot.visible=world;this._requestRender(true);}
 inspect(){
   this.scene.updateMatrixWorld(true);
   const rect=this.renderer.domElement.getBoundingClientRect();
   const project=(v:THREE.Vector3)=>{const p=v.clone().project(this.camera);return {x:rect.left+(p.x+1)*rect.width/2,y:rect.top+(1-p.y)*rect.height/2};};
   const linkPoints:Record<string,{x:number;y:number}>={};
   for(const [id,{group}] of this.linkGroups){const box=new THREE.Box3().setFromObject(group);if(!box.isEmpty())linkPoints[id]=project(box.getCenter(new THREE.Vector3()));}
   const origin=this.proxy.getWorldPosition(new THREE.Vector3());const handles:Record<string,{x:number;y:number}>={};
   for(const [name,axis] of [['x',new THREE.Vector3(1,0,0)],['y',new THREE.Vector3(0,1,0)],['z',new THREE.Vector3(0,0,1)]] as const){
     axis.applyQuaternion(this.proxy.getWorldQuaternion(new THREE.Quaternion()));handles[name]=project(origin.clone().addScaledVector(axis,this.camera.position.distanceTo(origin)*Math.min(1.9*Math.tan(Math.PI*this.camera.fov/360),7)*0.78/4*0.45));
   }
   const rings:Record<string,{x:number;y:number}[]>={};
   const visible=(node:THREE.Object3D)=>{for(let n:THREE.Object3D|null=node;n;n=n.parent)if(!n.visible)return false;return true;};
   this.gizmo.getHelper().traverse(node=>{
     if((node instanceof THREE.Line || (node instanceof THREE.Mesh && this.tool==='joint')) && /^[XYZ]$/.test(node.name) && visible(node)){
       const positions=node.geometry.getAttribute('position');
       rings[node.name]=[];
       for(let i=0;i<positions.count;i+=Math.max(1,Math.floor(positions.count/12)))rings[node.name].push(project(node.localToWorld(new THREE.Vector3().fromBufferAttribute(positions,i))));
     }
     if(node instanceof THREE.Mesh && /^[XYZ]$/.test(node.name) && visible(node)){
       const box=new THREE.Box3().setFromObject(node);
       if(!box.isEmpty())handles[node.name.toLowerCase()]=project(box.getCenter(new THREE.Vector3()));
     }
   });
   const gl=this.renderer.getContext();
   const debug=gl.getExtension('WEBGL_debug_renderer_info');
   // Read-only diagnostics, only exposed by the host with ?inspect. Local AABBs
   // describe the loaded vertices; world bounds are transformed local AABBs.
   const inverseRoot=this.mujocoRoot.matrixWorld.clone().invert();
   const geoms:Record<string,unknown>={};
   this.actualRoot.traverse(node=>{
     if(!(node instanceof THREE.Mesh)||node.userData.meshPending||!node.userData.geom)return;
     let link:THREE.Object3D|null=node;
     while(link&&!link.userData.sceneLink)link=link.parent;
     if(!link)return;
     node.geometry.computeBoundingBox();const local=node.geometry.boundingBox!;
     const worldSim=inverseRoot.clone().multiply(node.matrixWorld);const bounds=local.clone().applyMatrix4(worldSim);
     const material=node.material as THREE.MeshStandardMaterial;const geom=node.userData.geom;
     geoms[`${link.name}/${geom.name}`]={link:link.name,name:geom.name,asset:node.userData.assetId??null,
       localBounds:{min:local.min.toArray(),max:local.max.toArray()},worldSimBounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},
       matrixWorldSim:worldSim.elements,visible:visible(node),alpha:material.opacity,transparent:material.transparent,depthWrite:material.depthWrite,
       vertices:node.geometry.getAttribute('position').count};
   });
   const marker=this.actualTcp.getWorldPosition(new THREE.Vector3()).applyMatrix4(inverseRoot);
   const tip=this.sample.armSpec&&this.linkGroups.get(this.sample.armSpec.tcp.body)?.group;
   const fk=tip&&tip.localToWorld(new THREE.Vector3(...this.sample.armSpec!.tcp.position)).applyMatrix4(inverseRoot);
   return {gizmoAxis:this.gizmo.axis,pendingLoads:this.pendingLoads,failedAssets:[...this.failedAssets],renderCount:this.renderCount,lastFrameCostMs:this.lastFrameCostMs,selected:this.selected,tool:this.tool,ghost:this.ghostRoot.visible,dragging:this.gizmo.dragging,orbitEnabled:this.controls.enabled,linkPoints,handles,rings,geoms,
     tcp:{markerWorldSim:marker.toArray(),fkWorldSim:fk?fk.toArray():null,errorM:fk?fk.distanceTo(marker):null},
     viewport:{width:rect.width,height:rect.height},camera:this.camera.position.toArray(),cameraTarget:this.controls.target.toArray(),renderer:debug?gl.getParameter(debug.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),lifecycle:{...rendererLifecycle}};
 }
 override dispose(){
   if(this.disposed)return;
   this.cancelGesture();this.events.abort();this.gizmo.detach();this.gizmo.dispose();this.selectionBox.geometry.dispose();(this.selectionBox.material as THREE.Material).dispose();
   rendererLifecycle.disposed++;rendererLifecycle.active--;super.dispose();
 }
}
