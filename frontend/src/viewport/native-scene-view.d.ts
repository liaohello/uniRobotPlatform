import * as THREE from 'three';
import type { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { SceneManifest, SceneLink, NativeSnapshot } from '../adapters/types';
export class SceneView {
 constructor(container: HTMLElement, options?: { onNotice?: (notice: string)=>void; onTargetDrag?: (position: number[])=>void });
 container: HTMLElement; disposed: boolean; manifest: SceneManifest; snapshot: NativeSnapshot;
 scene: THREE.Scene; camera: THREE.PerspectiveCamera; renderer: THREE.WebGLRenderer; controls: OrbitControls;
 mujocoRoot: THREE.Group; worldRoot: THREE.Group; actualRoot: THREE.Group; ghostRoot: THREE.Group;
 targetGroup: THREE.Group; targetCore: THREE.Mesh; actualTcp: THREE.Mesh;
 linkGroups: Map<string,{group: THREE.Group;link: SceneLink}>; worldGroups: Map<string,{group: THREE.Group;link: SceneLink}>; ghostGroups: Map<string,{group: THREE.Group;link: SceneLink}>;
 raycaster: THREE.Raycaster; pointer: THREE.Vector2; planObject: THREE.Line | null;
 pendingLoads: number; failedAssets: Set<string>; renderCount: number; lastFrameCostMs: number | null;
 _bindPointer(): void; _setPointer(event: PointerEvent): void; _requestRender(immediate?: boolean): void;
 _clearPlan(): void; _applyJointValues(joints: Record<string,number>, ghost?: boolean): void;
 setManifest(manifest: SceneManifest): void; updateSnapshot(snapshot: NativeSnapshot): void;
 setTarget(position: number[],visible?: boolean): void; fitView(): void; resize(): void;
 configureRendering(options?: Record<string,unknown>): void; dispose(): void;
}
