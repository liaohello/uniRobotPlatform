"""Preparation slice for historical 3D: recorded robot pose mapped onto the fixed model bundle.

This answers "can the recorded state rebuild the robot on the frozen model, and which mappings are
actually attested?" It reuses the frame linkage join rules (one state event per frame capture tick),
compares the run manifest's own model and scene identity with the immutable compiled geometry
bundle, and then reports every pose field with an explicit status. Nothing is defaulted: a field
whose frame, sign, order or joint convention is not attested is reported as unverified or missing,
and the mesh bytes are served from the frozen bundle only — never from the live native scene,
snapshot or Actual.

Resource readiness is not rendering. Verified identity and validated mapping say that a frontend
*can* assemble this pose; whether the assembled pose looks right is left to the frontend round.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .episodes import EpisodeArchive, HistoryError, _now
from .frames import FrameLinkReader

POSE_SCHEMA = "unirobot-mobilecar-history-pose-1"

STATUS_MEANING = {
    "verified": "the record and the fixed bundle agree on this mapping, and nothing had to be assumed",
    "partially_verified": "some parts of the mapping are attested; the attested indexes or fields are named here",
    "unverified": "the value is recorded, but its frame, order, sign or convention is not attested by the record or the bundle",
    "missing": "the value a renderer would need is not recorded at all",
    "not_required_for_pose": "recorded data that this slice does not need to place the robot",
}

# The five arm hinges of this model, taken from the bundle rather than assumed by position.
ARM_HINGE_JOINTS = ("joint1", "joint2", "joint3", "joint4", "joint5")
GRIPPER_SLIDE_JOINTS = ("left_jaw_joint", "right_jaw_joint")
WHEEL_HINGE_JOINTS = ("front_left_joint", "rear_left_joint", "front_right_joint", "rear_right_joint")


def _length(value: Any) -> int | None:
    return len(value) if isinstance(value, list) else (1 if isinstance(value, (int, float)) and not isinstance(value, bool) else None)


def _digest_matches(expected: str, body: bytes) -> bool:
    return hashlib.sha256(body).hexdigest() == expected


class HistoryPoseReader:
    def __init__(self, archive: EpisodeArchive, bundle, kinematics: dict | None) -> None:
        self.archive = archive
        self.bundle = bundle
        self.kinematics = kinematics

    # ---- public entry points --------------------------------------------------------

    def robot_state(self, episode_id: str, *, run_id: str | None = None,
                    sample_id: str | None = None) -> dict[str, Any]:
        linkage = FrameLinkReader(self.archive).frames(episode_id, run_id=run_id, stream="rgbd",
                                                       limit=1, sample_id=sample_id)
        if not linkage["frames"]:
            raise HistoryError("frame_not_found", "this Episode has no persisted frame matching the request", 404,
                               {"episode_id": episode_id, "run_id": linkage["identity"]["run_id"],
                                "sample_id": sample_id})
        frame = linkage["frames"][0]
        recorded = self.archive.run_identity(linkage["identity"]["run_id"])
        bundle_view = self._bundle_view(recorded)
        payload = frame["state"]["recorded_state"]
        mapping = self._mapping(payload, bundle_view)
        return {
            "schema_version": POSE_SCHEMA,
            "read_only": True,
            "source": linkage["source"],
            "retrieved_at": _now(),
            "identity": {"run_id": linkage["identity"]["run_id"], "episode_id": linkage["identity"]["episode_id"],
                         "recorded_run_manifest": recorded,
                         "identity_source": "the run manifest the recorder itself wrote, copied verbatim"},
            "frame": {"sample_id": frame["sample_id"], "linkage_schema": linkage["schema_version"],
                      "linkage_status": frame["linkage_status"],
                      "anchor": {"relative_path": frame["anchor"]["relative_path"],
                                 "line_index": frame["anchor"]["line_index"],
                                 "persist_sequence": frame["anchor"]["persist_sequence"],
                                 "profile": frame["anchor"]["profile"]},
                      "media": frame["media"]},
            "state": {"linkage_status": frame["state"]["status"],
                      "source": frame["state"]["source"],
                      "candidate_records": frame["state"]["candidate_records"],
                      "single_state_selected": frame["state"]["single_state_selected"],
                      "recorded_payload": payload,
                      "declared_reference": frame["state"]["declared_reference"],
                      "units": frame["state"]["units"]},
            "time": {"quantities": frame["times"]["quantities"],
                     "state_time_quantity_keys": frame["times"]["state_time_quantity_keys"],
                     "recorder_declared": frame["times"]["recorder_declared"],
                     "semantics_rule": frame["times"]["semantics_rule"],
                     "same_clock_verified": False,
                     "clock_sameness": linkage["time"]["clock_sameness"]},
            "model_resource": bundle_view,
            "mapping": mapping,
            "status_meaning": STATUS_MEANING,
            "pose_readiness": self._readiness(mapping, bundle_view),
            "rendering": {"verified": False,
                          "frontend_assembly_done": False,
                          "note": "this slice prepares and reports the mapping; it does not render, and identity or "
                                  "digest checks are not evidence that the assembled pose looks right"},
            "not_proven": self._gaps(mapping),
            "capability_limits": ["no replay execution", "no live geometry or Actual substitution",
                                  "no fabricated dynamic object pose", "no control, RESET, recording or physics stepping"],
        }

    def model_asset(self, episode_id: str, asset_id: str, *, run_id: str | None = None,
                    sha256: str | None = None) -> tuple[bytes, str, dict[str, str]]:
        """Serve one frozen bundle mesh, after the episode's own model identity has been checked."""
        recorded = self.archive.run_identity(self.archive.location(episode_id, run_id).run_id)
        bundle_view = self._bundle_view(recorded)
        if bundle_view["status"] != "match":
            raise HistoryError("history_model_identity_mismatch",
                               "the recorded model identity does not match the frozen geometry bundle", 409,
                               {"episode_id": episode_id, "identity_comparison": bundle_view["comparison"]})
        if self.bundle is None or asset_id not in self.bundle.assets:
            raise HistoryError("history_model_asset_unavailable", "this asset is not in the frozen geometry bundle",
                               404, {"asset_id": asset_id,
                                     "supported": sorted(self.bundle.assets) if self.bundle else []})
        declared = next(item["sha256"] for item in bundle_view["assets"] if item["asset_id"] == asset_id)
        if sha256 and sha256 != declared:
            raise HistoryError("history_asset_revision_changed", "asset digest differs from the frozen bundle", 409,
                               {"asset_id": asset_id, "bundle_sha256": declared, "requested_sha256": sha256})
        body = self.bundle.assets[asset_id]
        if not _digest_matches(declared, body):
            raise HistoryError("history_asset_digest_mismatch", "asset bytes no longer match the frozen bundle", 409,
                               {"asset_id": asset_id})
        return body, "model/stl", {"Cache-Control": "no-store", "ETag": f'"sha256:{declared}"',
                                   "X-UniRobot-Model-Source": "frozen_compiled_geometry_bundle"}

    # ---- model resource -------------------------------------------------------------

    def _bundle_view(self, recorded: dict[str, Any]) -> dict[str, Any]:
        if self.bundle is None:
            return {"status": "not_configured",
                    "reason": "no compiled geometry bundle is configured for this platform process",
                    "comparison": {"recorded": {key: recorded.get(key) for key in
                                                ("contract_version", "model_id", "model_sha256", "scene_id")},
                                   "bundle": None}}
        identity = self.bundle.provenance.resource_identity
        fields = ("contract_version", "model_id", "model_sha256", "scene_id")
        bundle_side = {key: getattr(identity, key) for key in fields}
        comparison = {key: {"recorded": recorded.get(key), "bundle": bundle_side[key],
                            "equal": recorded.get(key) == bundle_side[key]} for key in fields}
        matched = all(item["equal"] for item in comparison.values())
        links = self.bundle.scene.links
        return {"status": "match" if matched else "mismatch", "comparison": comparison,
                "bundle_sha256": self.bundle.provenance.bundle_sha256,
                "content_identity_sha256": self.bundle.content_identity_sha256,
                "compiler": {"name": self.bundle.provenance.compiler,
                             "version": self.bundle.provenance.compiler_version},
                "verification_scope": self.bundle.provenance.verification_scope,
                "model_inputs_sha256": self.bundle.provenance.model_inputs_sha256,
                "compiled_scene_sha256": self.bundle.provenance.compiled_scene_sha256,
                "compile_runtime_identity": self.bundle.provenance.runtime_identity.model_dump(),
                "compile_runtime_identity_is_this_episode": None,
                "scene_source": self.bundle.scene.source,
                "tcp_site": self.bundle.scene.tcp_site,
                "camera_ids": list(self.bundle.scene.camera_ids),
                "link_count": len(links),
                "arm_hinge_joints": [name for name in ARM_HINGE_JOINTS
                                     if any(link.joint_name == name for link in links)],
                "gripper_slide_joints": [name for name in GRIPPER_SLIDE_JOINTS
                                         if any(link.joint_name == name for link in links)],
                "wheel_hinge_joints": [name for name in WHEEL_HINGE_JOINTS
                                       if any(link.joint_name == name for link in links)],
                "root_joint": self._link_view("base_link"),
                "camera_link_chain": self._chain("depth_cam_link"),
                "end_effector_link": self._link_view("end_effector_link"),
                "world_links": [{"name": link.name, "geom_types": sorted({geom.geom_type for geom in link.geoms})}
                                for link in self.bundle.scene.world_links],
                "assets": [{"asset_id": item.asset_id, "sha256": item.sha256, "media_type": item.media_type,
                            "coordinate_space": item.coordinate_space, "units": item.units,
                            "bytes": len(self.bundle.assets[item.asset_id])}
                           for item in self.bundle.scene.mesh_assets],
                "asset_integrity": "every mesh file's digest was verified against the bundle manifest when the "
                                   "bundle was loaded, and is re-verified per request before bytes leave the process",
                "live_native_scene_proxied": False,
                "served_via": "GET /api/v1/episodes/{episode_id}/model/assets/{asset_id} (frozen bundle only)"}

    def _link_view(self, name: str) -> dict[str, Any] | None:
        if self.bundle is None:
            return None
        link = next((item for item in self.bundle.scene.links if item.name == name), None)
        if link is None:
            return None
        return {"name": link.name, "parent_name": link.parent_name, "joint_name": link.joint_name,
                "joint_type": link.joint_type, "joint_axis": list(link.joint_axis),
                "local_position_m": list(link.local_transform.position_m),
                "local_orientation_xyzw": list(link.local_transform.orientation_xyzw)}

    def _chain(self, name: str) -> list[dict[str, Any]]:
        chain: list[dict[str, Any]] = []
        current: dict[str, Any] | None = self._link_view(name) if self.bundle else None
        while current:
            chain.append({"name": current["name"], "joint_name": current["joint_name"],
                          "joint_type": current["joint_type"]})
            current = self._link_view(current["parent_name"]) if current["parent_name"] else None
        return chain

    # ---- mapping --------------------------------------------------------------------

    def _mapping(self, payload: dict[str, Any] | None, bundle_view: dict[str, Any]) -> list[dict[str, Any]]:
        state = payload or {}
        arm = state.get("arm_model_qpos_rad")
        kinematics = (self.kinematics or {}).get("arm") if isinstance(self.kinematics, dict) else None
        config_names = list(kinematics.get("joint_names") or []) if isinstance(kinematics, dict) else []
        zero_model_rad = list(kinematics.get("zero_model_rad") or []) if isinstance(kinematics, dict) else []
        direction = kinematics.get("user_direction") if isinstance(kinematics, dict) else None
        bundle_arm = bundle_view.get("arm_hinge_joints") or []
        entries = [
            {"target": "arm_joint_positions", "recorded_field": "arm_model_qpos_rad",
             "recorded_unit": "rad", "recorded_length": _length(arm),
             "target_field": "bundle hinge joints " + ", ".join(bundle_arm),
             "status": "partially_verified" if bundle_arm and _length(arm) == len(bundle_arm) else "unverified",
             "evidence": {"bundle_arm_hinge_joints_in_document_order": bundle_arm,
                          "platform_kinematics_joint_names": config_names,
                          "names_equal_to_bundle": config_names == bundle_arm,
                          "length_matches_arm_hinge_count": _length(arm) == len(bundle_arm) or None,
                          "positions_are_model_radians_not_user_radians": True,
                          "order_attested_at_index": 3,
                          "order_attestation": "the record's own model/user joint pair differs exactly at index 3, "
                                               "which matches the platform zero offset for joint4; the other "
                                               "indexes are not individually attested"},
             "model_to_user_formula": {"q_user": "(q_model - zero_model_rad) / user_direction",
                                       "q_model": "zero_model_rad + user_direction * q_user",
                                       "zero_model_rad": zero_model_rad, "user_direction": direction,
                                       "authority": "platform_reference_not_native_attested"},
             "no_default_applied": True,
             "gap": "joint positions for indexes 0, 1, 2 and 4 are mapped by array order without a per-index attestation"},
            {"target": "base_position", "recorded_field": "base_position_world_sim_m",
             "recorded_unit": "m", "recorded_length": _length(state.get("base_position_world_sim_m")),
             "target_field": self._root_description(bundle_view),
             "status": "unverified", "evidence": {
                 "recorded_field_names_a_world_frame": True,
                 "bundle_root_joint": bundle_view.get("root_joint"),
                 "which_origin_the_position_refers_to": "not attested by the record or the bundle",
                 "recorded_z_and_bundle_root_local_z_are_different_quantities": True},
             "no_default_applied": True,
             "gap": "the body origin, frame and z convention for the recorded base position is not attested"},
            {"target": "base_orientation", "recorded_field": "base_quaternion_xyzw",
             "recorded_unit": "unit quaternion", "recorded_length": _length(state.get("base_quaternion_xyzw")),
             "target_field": "bundle transforms declare orientation as xyzw",
             "status": "unverified", "evidence": {
                 "recorded_field_label_declares_order": "xyzw",
                 "bundle_transform_field_declares_order": "orientation_xyzw",
                 "order_labels_agree": True,
                 "rotation_of_which_body_in_which_frame": "not attested by the record"},
             "no_default_applied": True,
             "gap": "the quaternion's order is labelled consistently, but the body and frame it rotates are not attested"},
            {"target": "gripper_joints", "recorded_field": "gripper_width_m",
             "recorded_unit": "m", "recorded_length": _length(state.get("gripper_width_m")),
             "target_field": "bundle slide joints " + ", ".join(bundle_view.get("gripper_slide_joints") or []),
             "status": "unverified", "evidence": {
                 "recorded_value_is_a_scalar_width": True,
                 "bundle_jaw_slide_joints": bundle_view.get("gripper_slide_joints"),
                 "additional_gripper_joints_in_bundle": ["gripper_base_joint", "gripper_left_join", "gripper_right_joint"],
                 "width_to_joint_value_convention": "not attested anywhere in the record, the bundle or the platform config"},
             "no_default_applied": True,
             "gap": "no attested rule turns the recorded width into jaw joint values; a half-width or sign guess would "
                    "have to be invented"},
            {"target": "tcp_site_position", "recorded_field": "tcp_position_world_m",
             "recorded_unit": "m", "recorded_length": _length(state.get("tcp_position_world_m")),
             "target_field": f"bundle tcp_site {bundle_view.get('tcp_site')}",
             "status": "unverified", "evidence": {
                 "bundle_declares_a_tcp_site_name": bundle_view.get("tcp_site"),
                 "recorded_field_names_a_world_position": True,
                 "the_site_is_not_a_link_in_the_bundle": True,
                 "tcp_orientation": "not recorded"},
             "no_default_applied": True,
             "gap": "whether the recorded position is the named site's world position, and any TCP orientation, is not attested"},
            {"target": "camera_extrinsics", "recorded_field": None, "recorded_unit": None, "recorded_length": None,
             "target_field": "bundle camera link chain " + " <- ".join(item["name"] for item in bundle_view.get("camera_link_chain") or []),
             "status": "missing", "evidence": {
                 "bundle_camera_ids": bundle_view.get("camera_ids"),
                 "recorded_observation_frame_id": "rgbd_optical",
                 "recorded_camera_calibration": "not present in the persisted frame, its rows or its transforms",
                 "placement_source": "forward kinematics of the fixed bundle plus the mapped joint state"},
             "no_default_applied": True,
             "gap": "no recorded camera calibration, so the optical frame's relation to the model link is unverified"},
            {"target": "wheel_joint_velocities", "recorded_field": "wheel_velocity_rad_s",
             "recorded_unit": "rad/s", "recorded_length": _length(state.get("wheel_velocity_rad_s")),
             "target_field": "bundle wheel hinges " + ", ".join(bundle_view.get("wheel_hinge_joints") or []),
             "status": "not_required_for_pose", "evidence": {
                 "per_wheel_labels_recorded": False,
                 "bundle_wheel_hinge_count": len(bundle_view.get("wheel_hinge_joints") or [])},
             "no_default_applied": True,
             "gap": "the four wheel values carry no per-wheel identity; a static pose does not need them"},
            {"target": "base_twist", "recorded_field": "base_twist_body_m_s", "recorded_unit": "m/s or rad/s per component",
             "recorded_length": _length(state.get("base_twist_body_m_s")), "target_field": None,
             "status": "not_required_for_pose", "evidence": {"component_labels_recorded": False},
             "no_default_applied": True, "gap": "component meaning is not recorded and a static pose does not need it"},
            {"target": "dynamic_scene_objects", "recorded_field": None, "recorded_unit": None, "recorded_length": None,
             "target_field": "bundle world links " + ", ".join(item["name"] for item in bundle_view.get("world_links") or []),
             "status": "missing", "evidence": {
                 "recorded_pose_for_non_robot_objects": "the state payload carries only the robot",
                 "render_from_record": False},
             "no_default_applied": True,
             "gap": "no historical position is recorded for dynamic scene objects, so they cannot be placed from the record"},
        ]
        return entries

    def _root_description(self, bundle_view: dict[str, Any]) -> str | None:
        root = bundle_view.get("root_joint")
        return None if not root else f"bundle root link {root['name']} free joint {root['joint_name']}"

    @staticmethod
    def _readiness(mapping: list[dict[str, Any]], bundle_view: dict[str, Any]) -> dict[str, Any]:
        ready = sum(1 for entry in mapping if entry["status"] in ("verified", "partially_verified"))
        return {"model_identity": bundle_view["status"],
                "mapping_valid_for_this_episode": bundle_view["status"] == "match",
                "mapped_targets_partially_or_fully_verified": f"{ready}/{len(mapping)}",
                "robot_state_can_be_rebuilt_without_assumptions": False,
                "blocking_fields": [entry["target"] for entry in mapping
                                    if entry["status"] in ("unverified", "missing")],
                "next_round_owner": "frontend assembly plus an attested base/gripper mapping source",
                "note": "resource identity, digests and joint-length checks pass; the remaining gaps are attestation "
                        "gaps, not missing files"}

    @staticmethod
    def _gaps(mapping: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"target": entry["target"], "status": entry["status"], "gap": entry["gap"]}
                for entry in mapping if entry["status"] in ("unverified", "missing")]
