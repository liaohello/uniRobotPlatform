"""Pure forward kinematics over a frozen compiled scene tree.

Conventions are taken from what the native scene builder writes into the bundle: a link's
``local_transform`` is MuJoCo ``body_pos`` / ``body_quat`` relative to the parent body frame
(wxyz on disk, relabelled xyzw), and ``joint_axis`` is ``model.jnt_axis`` expressed in that
child body frame, so a hinge rotates the child frame and its subtree about the axis after the
body offset. The root free joint's pose is the recorded base pose itself.

This is arithmetic over recorded numbers and the frozen bundle only. No MuJoCo, no numpy, no
native call: agreement supports kinematic consistency of the mapping, never hardware calibration
and never the writer's version.
"""

from __future__ import annotations

import math
from typing import Any, Iterable

Vec3 = tuple[float, float, float]
Quat4 = tuple[float, float, float, float]  # x, y, z, w

SLIDE_TOLERANCE_M = 1e-12


def _vec(value: Any) -> Vec3 | None:
    if isinstance(value, (list, tuple)) and len(value) == 3 and all(
            isinstance(item, (int, float)) and not isinstance(item, bool) for item in value):
        return (float(value[0]), float(value[1]), float(value[2]))
    return None


def _quat(value: Any) -> Quat4 | None:
    if isinstance(value, (list, tuple)) and len(value) == 4 and all(
            isinstance(item, (int, float)) and not isinstance(item, bool) for item in value):
        norm = math.sqrt(sum(float(item) ** 2 for item in value))
        if norm <= 0.0:
            return None
        return (float(value[0]) / norm, float(value[1]) / norm, float(value[2]) / norm, float(value[3]) / norm)
    return None


def quat_mul(a: Quat4, b: Quat4) -> Quat4:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def quat_rotate(q: Quat4, v: Vec3) -> Vec3:
    """Rotate a vector by q, expanded so no intermediate conjugate product is needed."""
    x, y, z, w = q
    t = (2.0 * (y * v[2] - z * v[1]),
         2.0 * (z * v[0] - x * v[2]),
         2.0 * (x * v[1] - y * v[0]))
    return (v[0] + w * t[0] + (y * t[2] - z * t[1]),
            v[1] + w * t[1] + (z * t[0] - x * t[2]),
            v[2] + w * t[2] + (x * t[1] - y * t[0]))


def axis_angle_quat(axis: Vec3, angle_rad: float) -> Quat4:
    ux, uy, uz = axis
    norm = math.sqrt(ux * ux + uy * uy + uz * uz)
    if norm <= 0.0:
        return (0.0, 0.0, 0.0, 1.0)
    ux, uy, uz = ux / norm, uy / norm, uz / norm
    s = math.sin(angle_rad / 2.0)
    return (ux * s, uy * s, uz * s, math.cos(angle_rad / 2.0))


class FrozenSceneTree:
    """The bundle's link hierarchy, addressed by name."""

    def __init__(self, links: Iterable[dict[str, Any]]) -> None:
        self.links: dict[str, dict[str, Any]] = {}
        for link in links:
            name = link.get("name")
            if isinstance(name, str):
                self.links[name] = link

    def parent_of(self, name: str) -> str | None:
        parent = self.links.get(name, {}).get("parent_name")
        return parent if isinstance(parent, str) and parent in self.links else None

    def chain(self, name: str, stop: str | None = None) -> list[str] | None:
        """Root-to-name link names, or None when the chain is broken."""
        if name not in self.links:
            return None
        path = [name]
        current = name
        while True:
            parent = self.parent_of(current)
            if parent is None:
                break
            if stop is not None and parent == stop:
                path.append(parent)
                break
            path.append(parent)
            current = parent
            if len(path) > len(self.links):
                return None
        path.reverse()
        return path

    def body_poses(self, root_name: str, root_position: Vec3, root_orientation_xyzw: Quat4,
                   joint_angles: dict[str, float]) -> dict[str, tuple[Vec3, Quat4]] | None:
        """World pose of every body from the root down, applying ``joint_angles`` by joint name.

        The root pose is taken as given: for this robot the root body carries the free joint whose
        recorded values already are the body's world pose. Every other link composes its parent
        frame with its own body offset and, when the link declares a movable joint, that joint's
        motion. A joint whose angle is absent is left at zero and reported by ``missing_joints``.
        """
        if root_name not in self.links:
            return None
        children: dict[str, list[str]] = {}
        for name, link in self.links.items():
            parent = link.get("parent_name")
            if isinstance(parent, str):
                children.setdefault(parent, []).append(name)
        poses: dict[str, tuple[Vec3, Quat4]] = {root_name: (root_position, root_orientation_xyzw)}
        pending = [name for name in children.get(root_name, [])]
        seen = {root_name}
        while pending:
            name = pending.pop(0)
            link = self.links[name]
            for child in children.get(name, []):
                if child not in seen:
                    pending.append(child)
            seen.add(name)
            parent = link.get("parent_name")
            if parent not in poses:
                return None
            position = _vec((link.get("local_transform") or {}).get("position_m")) or (0.0, 0.0, 0.0)
            orientation = _quat((link.get("local_transform") or {}).get("orientation_xyzw")) or (0.0, 0.0, 0.0, 1.0)
            if parent not in poses:
                return None
            p_position, p_orientation = poses[parent]
            offset = quat_rotate(p_orientation, position)
            composed = (p_position[0] + offset[0], p_position[1] + offset[1], p_position[2] + offset[2])
            composed_orientation = quat_mul(p_orientation, orientation)

            joint_type = link.get("joint_type")
            joint_name = link.get("joint_name")
            angle = joint_angles.get(joint_name) if isinstance(joint_name, str) else None
            if joint_type == "hinge" and isinstance(angle, (int, float)) and not isinstance(angle, bool):
                axis = _vec(link.get("joint_axis")) or (0.0, 0.0, 1.0)
                composed_orientation = quat_mul(composed_orientation, axis_angle_quat(axis, float(angle)))
            elif joint_type == "slide" and isinstance(angle, (int, float)) and not isinstance(angle, bool):
                axis = _vec(link.get("joint_axis")) or (0.0, 0.0, 1.0)
                along = quat_rotate(composed_orientation, axis)
                unit = math.sqrt(sum(item * item for item in axis)) or 1.0
                scale = float(angle) / unit
                composed = (composed[0] + along[0] * scale, composed[1] + along[1] * scale,
                            composed[2] + along[2] * scale)
            poses[name] = (composed, composed_orientation)
        return poses


def site_world_position(poses: dict[str, tuple[Vec3, Quat4]], parent_body: str,
                        offset: Vec3) -> Vec3 | None:
    body = poses.get(parent_body)
    if body is None:
        return None
    position, orientation = body
    rotated = quat_rotate(orientation, offset)
    return (position[0] + rotated[0], position[1] + rotated[1], position[2] + rotated[2])


def distance_m(a: Vec3, b: Vec3) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def tcp_from_recorded_state(links: list[dict[str, Any]], arm_joint_names: list[str],
                            arm_model_qpos_rad: Any, base_position: Any, base_quaternion_xyzw: Any,
                            tcp_parent_body: str, tcp_offset: Any,
                            root_body: str = "base_link") -> dict[str, Any]:
    """Reconstruct the recorded TCP site position from recorded state plus the frozen tree."""
    position = _vec(base_position)
    orientation = _quat(base_quaternion_xyzw)
    angles_values = (arm_model_qpos_rad if isinstance(arm_model_qpos_rad, list) else [])
    offset = _vec(tcp_offset)
    tree = FrozenSceneTree(links)
    if position is None or orientation is None or offset is None:
        return {"status": "not_computable", "reason": "a required recorded vector is absent or non-numeric",
                "inputs": {"base_position_present": position is not None,
                           "base_orientation_present": orientation is not None,
                           "tcp_offset_present": offset is not None}}
    if len(angles_values) != len(arm_joint_names):
        return {"status": "not_computable",
                "reason": "the recorded arm array length does not equal the declared arm joint count",
                "inputs": {"recorded_length": len(angles_values), "declared_joint_count": len(arm_joint_names)}}
    angles = {name: float(value) for name, value in zip(arm_joint_names, angles_values)}
    poses = tree.body_poses(root_body, position, orientation, angles)
    if poses is None:
        return {"status": "not_computable",
                "reason": "the frozen bundle tree does not connect the root body to the site's parent body",
                "inputs": {"root_body": root_body, "tcp_parent_body": tcp_parent_body}}
    if tcp_parent_body not in poses:
        return {"status": "not_computable", "reason": "the site's parent body is not in the frozen tree",
                "inputs": {"tcp_parent_body": tcp_parent_body}}
    computed = site_world_position(poses, tcp_parent_body, offset)
    chain = tree.chain(tcp_parent_body) or []
    movable = [name for name in chain if tree.links[name].get("joint_type") in ("hinge", "slide", "ball", "free")]
    return {"status": "computed", "position_m": list(computed),
            "chain_links": chain,
            "joints_on_chain": [tree.links[name].get("joint_name") for name in chain
                                if tree.links[name].get("joint_name")],
            "movable_joints_on_chain": [tree.links[name].get("joint_name") for name in movable
                                        if tree.links[name].get("joint_name")],
            "joint_angles_used": {name: angles[name] for name in arm_joint_names if name in angles},
            # A joint left at zero is a hinge or slide with no supplied value; the root's free joint is
            # supplied by the recorded base pose and fixed joints have no value to supply.
            "joints_left_at_zero": [tree.links[name].get("joint_name") for name in movable
                                    if tree.links[name].get("joint_type") in ("hinge", "slide", "ball")
                                    and tree.links[name].get("joint_name") not in angles]}
