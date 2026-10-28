import { Group, Matrix3, Quaternion, Vector3 } from 'three';
import type { ArmSpec, NativeSnapshot, SceneManifest, Vec3 } from '../adapters/types';
export class PreviewKinematics {
  private root = new Group();
  private links = new Map<string, Group>();
  constructor(private readonly scene: SceneManifest, private readonly snapshot: NativeSnapshot, private readonly spec: ArmSpec) {
    for (const link of scene.links) this.links.set(link.name, new Group());
    for (const link of scene.links) (this.links.get(link.parent_name ?? '') ?? this.root).add(this.links.get(link.name)!);
  }
  forward(joints: Record<string, number>): Vec3 {
    for (const link of this.scene.links) {
      const g = this.links.get(link.name)!;
      g.position.fromArray(link.local_transform.position_m);
      g.quaternion.fromArray(link.local_transform.orientation_xyzw);
      const value = joints[link.joint_name ?? ''];
      const axis = new Vector3(...link.joint_axis).normalize();
      if (link.joint_type === 'hinge' && Number.isFinite(value)) g.quaternion.multiply(new Quaternion().setFromAxisAngle(axis, value));
      if (link.joint_type === 'slide' && Number.isFinite(value)) g.position.add(axis.applyQuaternion(g.quaternion).multiplyScalar(value));
      if (link.name === 'base_link') {
        g.position.fromArray(this.snapshot.base.position_world_sim_m);
        g.quaternion.fromArray(this.snapshot.base.orientation_world_sim_xyzw);
      }
    }
    this.root.updateMatrixWorld(true);
    const tip = this.links.get(this.spec.tcp.body);
    if (!tip) throw new Error(`TCP body missing: ${this.spec.tcp.body}`);
    return tip.localToWorld(new Vector3(...this.spec.tcp.position)).toArray() as Vec3;
  }
  // Position-only offline DLS: this candidate has NO collision, timing, dynamics or backend approval.
  solve(position: Vec3, seed: Record<string, number>) {
    const q = { ...seed }; const names = Object.keys(this.spec.limits);
    const target = new Vector3(...position); let residual = Infinity;
    for (let it = 0; it < 100; it++) {
      const current = new Vector3(...this.forward(q)); const error = target.clone().sub(current); residual = error.length();
      if (residual < 0.0007) break;
      const jac = names.map(name => { const d = { ...q, [name]: q[name] + 0.0001 }; return new Vector3(...this.forward(d)).sub(current).multiplyScalar(10000); });
      const v = (r: number, c: number) => jac.reduce((sum, col) => sum + col.getComponent(r) * col.getComponent(c), 0) + (r === c ? 0.00025 : 0);
      const inverse = new Matrix3().set(v(0,0),v(0,1),v(0,2),v(1,0),v(1,1),v(1,2),v(2,0),v(2,1),v(2,2)).invert();
      const step = error.applyMatrix3(inverse);
      names.forEach((name, i) => { const [min,max] = this.spec.limits[name]; q[name] = Math.max(min, Math.min(max, q[name] + Math.max(-0.15, Math.min(0.15, jac[i].dot(step))))); });
    }
    residual = new Vector3(...this.forward(q)).distanceTo(target);
    return { joints: q, residual, converged: residual < 0.002 };
  }
}
