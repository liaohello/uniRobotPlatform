import * as THREE from 'three';
import type { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { SceneManifest, SceneLink, SceneGeom, MeshAsset, NativeSnapshot } from '../adapters/types';
export function materialFor(rgba: number[], options?: {ghost?:boolean;mesh?:boolean}):THREE.MeshStandardMaterial;
export function applyMeshCoordinateSpace(geometry:THREE.BufferGeometry, asset:MeshAsset, legacyScale:number[]):THREE.BufferGeometry;
export class SceneView {
 constructor(container: HTMLElement, options?: { onNotice?: (notice: string)=>void; onAssetError?: (message:string)=>void; onTargetDrag?: (position: number[])=>void });
 container: HTMLElement; disposed: boolean; manifest: SceneManifest; snapshot: NativeSnapshot;
 scene: THREE.Scene; camera: THREE.PerspectiveCamera; renderer: THREE.WebGLRenderer; controls: OrbitControls;
 mujocoRoot: THREE.Group; worldRoot: THREE.Group; actualRoot: THREE.Group; ghostRoot: THREE.Group;
 targetGroup: THREE.Group; targetCore: THREE.Mesh; actualTcp: THREE.Mesh;
 linkGroups: Map<string,{group: THREE.Group;link: SceneLink}>; worldGroups: Map<string,{group: THREE.Group;link: SceneLink}>; ghostGroups: Map<string,{group: THREE.Group;link: SceneLink}>;
 raycaster: THREE.Raycaster; pointer: THREE.Vector2; planObject: THREE.Line | null;
 pendingLoads: number; failedAssets: Set<string>; renderCount: number; lastFrameCostMs: number | null;
 fitTimer: number | null; userHasNavigated?: boolean;
 _bindPointer(): void; _setPointer(event: PointerEvent): boolean; _requestRender(immediate?: boolean): void;
 _clearPlan(): void; _applyJointValues(joints: Record<string,number>, ghost?: boolean): void;
 _buildGeom(geom:SceneGeom,ghost:boolean):THREE.Group|null;
 setManifest(manifest: SceneManifest): void; updateSnapshot(snapshot: NativeSnapshot): void;
 setTarget(position: number[],visible?: boolean): void; fitView(): void; resize(): boolean;
 configureRendering(options?: Record<string,unknown>): void; dispose(): void;
}
