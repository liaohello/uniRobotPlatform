/**
 * The history fixed-model surface: the existing SceneView (Three.js scene, camera, orbit controls,
 * mesh loading with digest check, layout and disposal) with click-to-select and a per-frame pose
 * layer on top, and every live-pose entry point left unused.
 *
 * It is deliberately not WorkbenchScene: a historical pane has no Actual, no Target, no gizmo, no tool
 * and no control. What may move is decided per capability by the reader's own `part_readiness` and
 * `mapping` (see `poseDriveOf`), and the values are the recorded ones — model radians for the arm
 * hinges, the base body's world pose for the chassis, a position-only marker for the TCP.
 *
 * Attribution rule: whatever is on screen belongs to the frame it was applied for, never to the frame
 * the header happens to name. `applyFramePose(null)` puts the tree back on its compiled reference
 * layout, so a read in flight or an unreadable frame can never show the previous frame's pose under
 * the new frame's title.
 */
import * as THREE from 'three';
import { SceneView } from './native-scene-view';
import type { SceneLink } from '../adapters/types';

export interface ReferenceSelection {
  linkName: string; parentName: string; jointName: string; jointType: string;
  geoms: { name: string; geomType: string; meshAssetId: string }[];
}
/** What the surface is actually showing right now, as opposed to what was asked for. */
export interface PoseAttribution {
  displayedSample: string; dynamicApplied: boolean; baseApplied: boolean; tcpApplied: boolean;
  jointsApplied: number; jointValues: Record<string, number>; referenceLayout: boolean;
  rootHeightWorldSimM: number | null; compiledRootHeightWorldSimM: number | null;
}
export interface ReferenceInspect {
  links: number; worldLinks: number; selectedJointDriven: Record<string, number>;
  assetFailures: string[]; pendingLoads: number; camera: { distance: number; azimuthDeg: number; polarDeg: number; target: number[] };
  lifecycle: { created: boolean; disposed: boolean; active: boolean; renders: number };
  attribution: PoseAttribution; worldPositions: Record<string, number[]>;
  /** The same positions converted back into the record's own world_sim axes, so a rendered body can be
   *  compared with `base_position_world_sim_m` / `tcp_position_world_m` instead of with our own numbers. */
  worldPositionsSim: Record<string, number[]>; tcpPositionSim: number[] | null;
}
export interface HistoryPoseInput {
  sample: string; joints: Record<string, number>;
  base: { position: number[]; quaternion: number[] } | null; tcp: { position: number[] } | null;
}
export class HistoryReferenceScene extends SceneView {
  private onSelect: ((selection: ReferenceSelection | null) => void) | null = null;
  private selectedName = '';
  private element: HTMLElement | null = null;
  private tcpMarker: THREE.Mesh | null = null;
  private attributionState: PoseAttribution = {
    displayedSample: '', dynamicApplied: false, baseApplied: false, tcpApplied: false, jointsApplied: 0,
    jointValues: {}, referenceLayout: true, rootHeightWorldSimM: null, compiledRootHeightWorldSimM: null,
  };
  /** The compiled root placement, captured once per manifest, that a frame without a pose returns to. */
  private compiledBase: { position: number[]; quaternion: number[] } | null = null;

  mount(container: HTMLElement, onSelect: (selection: ReferenceSelection | null) => void): void {
    this.onSelect = onSelect;
    this.element = container;
    container.addEventListener('pointerdown', this.handlePointerDown);
    container.addEventListener('pointerup', this.handleClick);
  }

  unmount(): void {
    this.element?.removeEventListener('pointerdown', this.handlePointerDown);
    this.element?.removeEventListener('pointerup', this.handleClick);
    this.element = null;
    this.onSelect = null;
    this.selectedName = '';
  }

  /** A new bundle means a new compiled layout: forget the captured home and the posed frame. */
  override setManifest(manifest: Parameters<SceneView['setManifest']>[0]): void {
    super.setManifest(manifest);
    this.compiledBase = null;
    if (this.tcpMarker) this.tcpMarker.visible = false;
    this.attributionState = { ...this.attributionState, displayedSample: '', dynamicApplied: false, baseApplied: false, tcpApplied: false, jointsApplied: 0, jointValues: {}, referenceLayout: true, rootHeightWorldSimM: null, compiledRootHeightWorldSimM: null };
  }

  private downPoint = { x: 0, y: 0 };

  private handlePointerDown = (event: PointerEvent): void => { this.downPoint = { x: event.clientX, y: event.clientY }; };

  /** Raycast on release only when the pointer did not travel: an orbit drag must not select. */
  private handleClick = (event: PointerEvent): void => {
    const host = this.element;
    if (!host || this.disposed) return;
    const rect = host.getBoundingClientRect();
    const dx = event.clientX - this.downPoint.x, dy = event.clientY - this.downPoint.y;
    if (Math.hypot(dx, dy) > 4) return;
    this.pointer.set(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1);
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hit = this.raycaster.intersectObjects([this.actualRoot, this.worldRoot], true)
      .find((entry) => !!(entry.object as { userData?: { geom?: unknown } }).userData?.geom);
    const link = linkOf(hit?.object ?? null);
    this.selectedName = link?.name ?? '';
    this.onSelect?.(link ? selectionOf(link) : null);
  };

  private baseGroup(): THREE.Group | null { return this.linkGroups.get('base_link')?.group ?? null; }

  /**
   * Put the tree into the pose of one frame, or back onto the compiled reference layout. The base
   * placement replaces the root link's transform — the reader's own cross-check excludes re-adding the
   * bundle root offset — and the TCP is a point only, because no orientation is recorded. Nothing here
   * rebuilds the viewport: meshes, camera and layout stay as they are.
   */
  applyFramePose(input: HistoryPoseInput | null): void {
    if (this.disposed) return;
    const base = this.baseGroup();
    if (base && !this.compiledBase) {
      this.compiledBase = { position: base.position.toArray(), quaternion: [base.quaternion.x, base.quaternion.y, base.quaternion.z, base.quaternion.w] };
    }
    if (!input) {
      if (base && this.compiledBase) {
        base.position.fromArray(this.compiledBase.position);
        base.quaternion.fromArray(this.compiledBase.quaternion);
      }
      // Joints go back to their compiled reference values; the free root joint is left alone by
      // _applyJointValues, so the base transform above is what restores the compiled layout.
      this._applyJointValues({});
      if (this.tcpMarker) this.tcpMarker.visible = false;
      this.attributionState = {
        displayedSample: '', dynamicApplied: false, baseApplied: false, tcpApplied: false, jointsApplied: 0,
        jointValues: {}, referenceLayout: true, rootHeightWorldSimM: null, compiledRootHeightWorldSimM: this.compiledBase?.position[2] ?? null,
      };
      this._requestRender(true);
      return;
    }
    if (input.base && base) {
      base.position.fromArray(input.base.position);
      base.quaternion.fromArray(input.base.quaternion);
    } else if (base && this.compiledBase) {
      base.position.fromArray(this.compiledBase.position);
      base.quaternion.fromArray(this.compiledBase.quaternion);
    }
    this._applyJointValues(input.joints);
    const names = Object.keys(input.joints);
    if (input.tcp) {
      const marker = this.ensureTcpMarker();
      marker.position.fromArray(input.tcp.position);
      marker.visible = true;
    } else if (this.tcpMarker) {
      this.tcpMarker.visible = false;
    }
    this.attributionState = {
      displayedSample: input.sample, dynamicApplied: Boolean(input.base || input.tcp || names.length),
      baseApplied: Boolean(input.base && base), tcpApplied: Boolean(input.tcp),
      jointsApplied: names.length, jointValues: { ...input.joints }, referenceLayout: false,
      rootHeightWorldSimM: input.base ? input.base.position[2] ?? null : this.compiledBase?.position[2] ?? null,
      compiledRootHeightWorldSimM: this.compiledBase?.position[2] ?? null,
    };
    this._requestRender(true);
  }

  /** A small sphere in the same world_sim space the record uses; position only, never an oriented frame. */
  private ensureTcpMarker(): THREE.Mesh {
    if (this.tcpMarker) return this.tcpMarker;
    const marker = new THREE.Mesh(
      new THREE.SphereGeometry(0.008, 16, 12),
      new THREE.MeshBasicMaterial({ color: 0xffb703, transparent: true, opacity: 0.95 }),
    );
    marker.name = 'history-tcp-marker';
    marker.visible = false;
    this.mujocoRoot.add(marker);
    this.tcpMarker = marker;
    return marker;
  }

  attribution(): PoseAttribution { return this.attributionState; }

  /** World-space position of one link group, used to prove the render itself moved between frames. */
  linkWorldPosition(name: string): number[] | null {
    const group = this.linkGroups.get(name)?.group ?? this.worldGroups.get(name)?.group;
    if (!group) return null;
    return group.getWorldPosition(new THREE.Vector3()).toArray();
  }

  /** A body's rendered position expressed back in world_sim, through the render root's own transform.
   *  That conversion is the only place where the ±90° axis mapping could hide an error, so the acceptance
   *  compares this against the record's vector rather than trusting the mapping. */
  worldSimPosition(name: string): number[] | null {
    const group = this.linkGroups.get(name)?.group ?? this.worldGroups.get(name)?.group;
    if (!group) return null;
    return this.mujocoRoot.worldToLocal(group.getWorldPosition(new THREE.Vector3())).toArray();
  }

  tcpWorldSimPosition(): number[] | null {
    if (!this.tcpMarker?.visible) return null;
    return this.mujocoRoot.worldToLocal(this.tcpMarker.getWorldPosition(new THREE.Vector3())).toArray();
  }

  /** The same three standard views the live workbench offers; only the camera moves. */
  standardView(view: 'front' | 'side' | 'top'): void {
    if (this.disposed) return;
    const distance = this.camera.position.distanceTo(this.controls.target);
    // world_sim +X is the chassis forward axis; mujocoRoot maps +X to Three +X and world_sim −Y to
    // Three +Z, so 车头 sits on +X and 车侧 on +Z. The model root is never rotated for a view.
    const direction = view === 'top' ? new THREE.Vector3(0, 1, 0.0001) : view === 'front' ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 0, 1);
    this.camera.position.copy(this.controls.target).addScaledVector(direction, Math.max(distance, 0.3));
    this.controls.update();
    this._requestRender(true);
  }

  inspect(): ReferenceInspect {
    const spherical = { distance: this.controls.getDistance(), azimuthDeg: this.controls.getAzimuthalAngle() * 180 / Math.PI, polarDeg: this.controls.getPolarAngle() * 180 / Math.PI };
    return {
      links: this.manifest?.links?.length ?? 0,
      worldLinks: this.manifest?.world_links?.length ?? 0,
      selectedJointDriven: { ...this.attributionState.jointValues },
      assetFailures: [...this.failedAssets],
      pendingLoads: this.pendingLoads,
      camera: { ...spherical, target: [this.controls.target.x, this.controls.target.y, this.controls.target.z] },
      lifecycle: { created: !this.disposed, disposed: this.disposed, active: !this.disposed, renders: this.renderCount },
      attribution: this.attributionState,
      // Where a few named bodies actually ended up in the rendered scene: proof the picture moved, not
      // only that a number was applied.
      worldPositions: Object.fromEntries(['base_link', 'link5', 'gripper_link']
        .map((name) => [name, this.linkWorldPosition(name)])
        .filter((entry): entry is [string, number[]] => entry[1] !== null)),
      worldPositionsSim: Object.fromEntries(['base_link', 'link5', 'gripper_link']
        .map((name) => [name, this.worldSimPosition(name)])
        .filter((entry): entry is [string, number[]] => entry[1] !== null)),
      tcpPositionSim: this.tcpWorldSimPosition(),
    };
  }

  selectedLinkName(): string { return this.selectedName; }

  dispose(): void {
    this.tcpMarker?.geometry.dispose();
    (this.tcpMarker?.material as THREE.Material | undefined)?.dispose();
    this.tcpMarker = null;
    this.unmount();
    super.dispose();
  }
}

function linkOf(object: unknown): SceneLink | null {
  let node = object as { parent?: unknown; userData?: { sceneLink?: SceneLink } } | null;
  while (node) {
    if (node.userData?.sceneLink) return node.userData.sceneLink;
    node = node.parent as typeof node;
  }
  return null;
}
function selectionOf(link: SceneLink): ReferenceSelection {
  return {
    linkName: link.name, parentName: link.parent_name ?? 'null', jointName: link.joint_name ?? 'null',
    jointType: link.joint_type,
    geoms: (link.geoms ?? []).map((geom) => ({ name: geom.name, geomType: geom.geom_type, meshAssetId: geom.mesh_asset_id ?? 'null' })),
  };
}
