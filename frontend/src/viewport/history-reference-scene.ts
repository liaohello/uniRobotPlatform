/**
 * The history fixed-model reference surface: the existing SceneView (Three.js scene, camera, orbit
 * controls, mesh loading with digest check, layout and disposal) with click-to-select added on top
 * and every live-pose entry point left unused.
 *
 * It is deliberately not WorkbenchScene: a historical pane has no Actual, no Target, no gizmo, no
 * tool and no control. Only the joints whose recorded mapping the backend marks `verified` may be
 * moved, and they are moved with the recorded model radians — the user-zero conversion belongs to the
 * live Target layer and is not applied here.
 */
import { SceneView } from './native-scene-view';
import type { SceneLink } from '../adapters/types';

export interface ReferenceSelection {
  linkName: string; parentName: string; jointName: string; jointType: string;
  geoms: { name: string; geomType: string; meshAssetId: string }[];
}
export interface ReferenceInspect {
  links: number; worldLinks: number; selectedJointDriven: Record<string, number>;
  assetFailures: string[]; pendingLoads: number; camera: { distance: number; azimuthDeg: number; polarDeg: number; target: number[] };
  lifecycle: { created: boolean; disposed: boolean; active: boolean; renders: number };
}
/** The hinge/slide joints a reference view may actually be posed on. */
const POSABLE = new Set(['hinge', 'slide']);

export class HistoryReferenceScene extends SceneView {
  private onSelect: ((selection: ReferenceSelection | null) => void) | null = null;
  private selectedName = '';
  private driven: Record<string, number> = {};
  private element: HTMLElement | null = null;

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

  /** Only ever called with joints the mapping gate allowed through. */
  applyVerifiedJoints(values: Record<string, number>): void {
    this.driven = values;
    this._applyJointValues(values);
  }

  inspect(): ReferenceInspect {
    const spherical = { distance: this.controls.getDistance(), azimuthDeg: this.controls.getAzimuthalAngle() * 180 / Math.PI, polarDeg: this.controls.getPolarAngle() * 180 / Math.PI };
    return {
      links: this.manifest?.links?.length ?? 0,
      worldLinks: this.manifest?.world_links?.length ?? 0,
      selectedJointDriven: this.driven,
      assetFailures: [...this.failedAssets],
      pendingLoads: this.pendingLoads,
      camera: { ...spherical, target: [this.controls.target.x, this.controls.target.y, this.controls.target.z] },
      lifecycle: { created: !this.disposed, disposed: this.disposed, active: !this.disposed, renders: this.renderCount },
    };
  }

  selectedLinkName(): string { return this.selectedName; }

  dispose(): void { this.unmount(); super.dispose(); }
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
export const POSABLE_JOINT_TYPES = POSABLE;
