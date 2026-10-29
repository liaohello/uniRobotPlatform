"""Preparation slice for historical 3D: recorded robot pose mapped onto the fixed model bundle.

This answers "can the recorded state rebuild the robot on the frozen model, which mappings are
attested, and which parts can a frontend actually use?" It reuses the frame linkage join rules
(one state event per frame capture tick), compares the run manifest's own model and scene identity
with the immutable compiled geometry bundle, reconstructs the TCP site position by pure forward
kinematics and cross-checks it against the value recorded in the same payload, and then reports
readiness per part. Nothing is defaulted: a field whose frame, order, sign or convention is not
attested is reported as unverified or missing, and the mesh bytes come from the frozen bundle only
— never from the live native scene, snapshot or Actual.

Per-part readiness is not whole-robot readiness. The fixed model can be assembled while the base
or gripper pose stays unevidenced, and an available arm pose never upgrades into a rebuildable
whole robot. Resource readiness is not rendering either: agreement here is kinematic consistency,
not calibration, and never proof of which native build wrote the archive.

`include_model_tree=true` adds `model_resource.model_tree`: the complete frozen link and geom tree
for assembly, with parent, joint, transform and mesh identity for every link. It is static per
bundle, so it is asked for once per content identity rather than per frame, and its bytes still come
only from this bundle — the live scene, snapshot and Actual are never read to build it.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .episodes import EpisodeArchive, HistoryError, _now
from .frames import FrameLinkReader
from .history_fk import distance_m, _vec, tcp_from_recorded_state

POSE_SCHEMA = "unirobot-mobilecar-history-pose-1"

STATUS_MEANING = {
    "verified": "the record and the fixed bundle agree on this mapping, and nothing had to be assumed",
    "partially_verified": "some parts of the mapping are attested; the attested indexes or fields are named here",
    "unverified": "the value is recorded, but its frame, order, sign or convention is not attested by the record or the bundle",
    "missing": "the value a renderer would need is not recorded at all",
    "not_required_for_pose": "recorded data that this slice does not need to place the robot",
}

PART_STATUS_MEANING = {
    "ready": "the inputs, the fixed resources and the mapping rule are all present and consistent",
    "ready_with_caveats": "usable now, with the named limits stated beside it",
    "conditional": "usable only if the consumer accepts the named unattested assumption and shows it",
    "blocked": "a required input or attestation is absent, so this part must not be drawn from the record",
    "not_required": "this part is not needed to place the robot",
}

# Static source chain for arm_model_qpos_rad, re-read in the native tree and in frozen native
# release snapshots for this slice. The values are name-addressed, so the order is not an inference
# from array layout.
ARM_MAPPING_CHAIN = {
    "joint_name_list": "src/mobilecar/backends/modelgen/model/arm.py:10  "
                       "ARM_JOINTS = tuple(f\"joint{i}\" for i in range(1, 6))",
    "qpos_is_name_addressed": "src/mobilecar/control/arm.py:12-14  names = ARM_JOINTS + (GRIPPER_DRIVE,); "
                              "joints = [model.joint(name).id]; qpos = model.jnt_qposadr[self.joints]",
    "feedback_serialisation": "src/mobilecar/backends/mujoco/backend.py:3385 (current source) / :1386 "
                              "(2026-10-17 release snapshots)  \"arm_model_qpos_rad\": "
                              "self.data.qpos[self.arm.qpos[:5]].tolist()",
    "sixth_element_excluded": "GRIPPER_DRIVE = gripper_base_joint occupies index 5 and is sliced off, so the "
                              "recorded five values are the five arm hinges and no gripper joint",
    "order_is_not_layout_dependent": "the slice order follows ARM_JOINTS, not the XML document order or the "
                                     "raw qpos layout",
    "model_xml": "assets/landerpi/model/arm.xml declares joint1..joint5 on bodies link1..link5 in the same "
                 "document order, which coincides but is not load-bearing",
}

# How far the chain can be tied to a version, and where that tie stops.
VERSION_BINDING = {
    "reference_source": "native working tree at commit a5cef52 (dirty: app.py, cli.py, config.py, "
                        "contracts/models.py, data/recorder.py modified)",
    "chain_verified_in_reference_source": True,
    "frozen_release_snapshots_at_the_recording_hour": ["g2a-20261017T155919Z-1bf2b553093a",
                                                       "g2a-20261017T160655Z-92c71ff8d582",
                                                       "g2a-20261017T160903Z-7e3afdbaff8f"],
    "same_chain_found_in_each_snapshot": "ARM_JOINTS at backends/modelgen/model/arm.py:10, "
                                         "model.jnt_qposadr at control/arm.py:14, arm_model_qpos_rad at "
                                         "backends/mujoco/backend.py:1386",
    "model_digests_equal_in_each_snapshot": {"arm.xml": "794b0c38e0c69643…",
                                             "robot.xml": "3ca3d6d0a92a48bb… (= the recorded model_sha256)"},
    "record_carries_no": ["native release id", "build id", "git commit"],
    "run_manifest_declares_only": ["contract_version", "software name and version", "model_id/model_sha256/scene_id"],
    "later_release_note": "drvfix-20261019T044549Z postdates this archive and its backend.py hash differs from the "
                          "current checkout, so it is not the writer of these records",
    "conclusion": "the semantic chain is present both in the current source and in frozen snapshots from the same "
                  "hour as the recording, which narrows the writer to that release family; it does not identify a "
                  "single build, and no commit or build id is invented here",
    "writer_identified": False,
}

# The platform's declared reference model angles versus user angles. Drawing the model uses the
# recorded model radians directly; the user conversion is a display/limits concern, not a gate.
def _model_vs_user_angles(kinematics: dict[str, Any] | None) -> dict[str, Any]:
    arm = (kinematics or {}).get("arm") if isinstance(kinematics, dict) else None
    arm = arm if isinstance(arm, dict) else {}
    return {"render_source": "arm_model_qpos_rad applied to the bundle hinge joints, in model radians, with no "
                             "conversion step",
            "conversion_is_required_for_drawing": False,
            "user_angle_formula": {"q_user": arm.get("user_from_model"), "q_model": arm.get("model_from_user"),
                                   "zero_model_rad": arm.get("zero_model_rad"),
                                   "user_direction": arm.get("user_direction"),
                                   "used_for": "user-facing display and limit comparison only"},
            "zero_pose_authority": {"zero_status": arm.get("zero_status"),
                                    "calibration_session": arm.get("calibration_session"),
                                    "note": "the zero is a user-defined photo pose, not a hardware calibration, and "
                                            "it is not applied when drawing recorded model angles"},
            "config_joint_names_equal_bundle_arm_hinges": None,
            "record_index3_observation": "on the representative record the same joint_feedback row's model and user "
                                         "arrays differ exactly at index 3 by -1.5707963267948966 rad (= the "
                                         "config's declared zero for joint4, which the config stores as the exact "
                                         "-pi/2, not a rounded literal); the other four indexes are identical",
            "authority": (kinematics or {}).get("authority") if isinstance(kinematics, dict) else None,
            "limitations": (kinematics or {}).get("limitations") if isinstance(kinematics, dict) else None}


def _tcp_reference(kinematics: dict[str, Any] | None) -> dict[str, Any]:
    tcp = (kinematics or {}).get("tcp") if isinstance(kinematics, dict) else None
    return tcp if isinstance(tcp, dict) else {}


def _digest_matches(expected: str, body: bytes) -> bool:
    return hashlib.sha256(body).hexdigest() == expected


class HistoryPoseReader:
    def __init__(self, archive: EpisodeArchive, bundle, kinematics: dict | None) -> None:
        self.archive = archive
        self.bundle = bundle
        self.kinematics = kinematics

    # ---- public entry points --------------------------------------------------------

    def robot_state(self, episode_id: str, *, run_id: str | None = None,
                    sample_id: str | None = None, include_model_tree: bool = False) -> dict[str, Any]:
        linkage = FrameLinkReader(self.archive).frames(episode_id, run_id=run_id, stream="rgbd",
                                                       limit=1, sample_id=sample_id)
        if sample_id and linkage["paging"]["has_more"]:
            # Under a sample_id filter a further qualifying anchor can only be another anchor with the same id,
            # so the frame the caller asked to name is not unique. Taking the first one would silently attach
            # this pose to whichever anchor happened to be read first.
            raise HistoryError("frame_sample_id_ambiguous",
                               "more than one persisted anchor records this sample_id, so no single frame can be "
                               "selected by it", 409,
                               {"episode_id": episode_id, "run_id": linkage["identity"]["run_id"],
                                "sample_id": sample_id,
                                "first_matching_anchor_line_index": linkage["cursor"]["first_line_index"],
                                "next_matching_anchor_line_index":
                                    linkage["paging"]["next_qualifying_anchor_line_index"],
                                "no_first_match_was_assumed": True,
                                "state_is_not_taken_from_either_candidate": True,
                                "how_to_inspect": "GET /api/v1/episodes/{episode_id}/frames?include_time_quality=true "
                                                  "lists every duplicate anchor position for this Episode"})
        if not linkage["frames"]:
            raise HistoryError("frame_not_found", "this Episode has no persisted frame matching the request", 404,
                               {"episode_id": episode_id, "run_id": linkage["identity"]["run_id"],
                                "sample_id": sample_id})
        frame = linkage["frames"][0]
        recorded = self.archive.run_identity(linkage["identity"]["run_id"])
        bundle_view = self._bundle_view(recorded)
        payload = frame["state"]["recorded_state"]
        cross_check = self._cross_check(payload, bundle_view)
        mapping = self._mapping(payload, bundle_view, cross_check)
        parts = self._part_readiness(payload, bundle_view, mapping, cross_check)
        if include_model_tree:
            bundle_view["model_tree"] = self._model_tree(bundle_view)
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
                     "sim_time_quantity_keys": frame["times"]["sim_time_quantity_keys"],
                     "recorder_declared": frame["times"]["recorder_declared"],
                     "semantics_rule": frame["times"]["semantics_rule"],
                     "same_clock_verified": False,
                     "clock_sameness": linkage["time"]["clock_sameness"]},
            "model_resource": bundle_view,
            "mapping": mapping,
            "status_meaning": STATUS_MEANING,
            "arm_mapping_chain": ARM_MAPPING_CHAIN,
            "version_binding": VERSION_BINDING,
            "model_vs_user_angles": self._angles_block(bundle_view),
            "tcp_kinematic_cross_check": cross_check,
            "part_readiness": parts,
            "part_status_meaning": PART_STATUS_MEANING,
            "capability_summary": self._capability_summary(parts, bundle_view, cross_check),
            "pose_readiness": self._readiness(mapping, bundle_view, parts, cross_check),
            "rendering": {"verified": False,
                          "frontend_assembly_done": False,
                          "note": "this slice prepares and reports the mapping; it does not render, and identity or "
                                  "digest checks are not evidence that the assembled pose looks right"},
            "not_proven": self._gaps(mapping),
            "capability_limits": ["no replay execution", "no live geometry or Actual substitution",
                                  "no fabricated dynamic object pose", "no calibration claim",
                                  "no control, RESET, recording or physics stepping"],
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
                "gripper_other_joints_in_bundle": [link.joint_name for link in links
                                                   if link.joint_name and link.joint_name.startswith("gripper_")],
                "wheel_hinge_joints": [name for name in WHEEL_HINGE_JOINTS
                                       if any(link.joint_name == name for link in links)],
                "root_joint": self._link_view("base_link"),
                "tcp_parent_body_view": self._link_view(_tcp_reference(self.kinematics).get("parent_body")),
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
                "link_frames": "each link's local_transform is the model body offset relative to its parent body, "
                               "and joint_axis is the model joint axis in that child body frame",
                "live_native_scene_proxied": False,
                "served_via": "GET /api/v1/episodes/{episode_id}/model/assets/{asset_id} (frozen bundle only)"}

    def _link_view(self, name: str | None) -> dict[str, Any] | None:
        if self.bundle is None or not name:
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

    def _model_tree(self, view: dict[str, Any]) -> dict[str, Any]:
        """The whole frozen assembly, only when asked for: it is static per bundle, never per frame.

        This is the compiled structure itself (the same link/geom serialization the geometry surface
        uses), not the named `_link_view` summaries, so a frontend can place every link without ever
        reading the live scene route. A model that does not match this Episode's record gets no tree
        and no substitute.
        """
        if self.bundle is None or view["status"] != "match":
            return {"requested": True, "included": False,
                    "reason": ("no compiled geometry bundle is configured for this process" if self.bundle is None
                               else "this Episode's recorded model identity does not match the frozen bundle, "
                                    "so no tree is served"),
                    "links_are_substituted": False,
                    "summary_views_still_on_model_resource": True}
        links = [link.model_dump(mode="json") for link in self.bundle.scene.links]
        world_links = [link.model_dump(mode="json") for link in self.bundle.scene.world_links]
        geoms = [geom for link in self.bundle.scene.links + self.bundle.scene.world_links for geom in link.geoms]
        return {"requested": True, "included": True,
                "authority": "frozen_compiled_geometry_bundle",
                "live_native_scene_proxied": False,
                "links": links, "world_links": world_links,
                "counts": {"links": len(links), "world_links": len(world_links), "geoms": len(geoms),
                           "mesh_geoms": sum(1 for geom in geoms if geom.geom_type == "mesh")},
                "content_identity": {"bundle_sha256": view["bundle_sha256"],
                                     "content_identity_sha256": view["content_identity_sha256"],
                                     "compiled_scene_sha256": view["compiled_scene_sha256"],
                                     "model_inputs_sha256": view["model_inputs_sha256"],
                                     "same_values_as": "the four digests already on model_resource; no second "
                                                      "digest scheme is introduced here",
                                     "use_as": "the cache key for this tree: it changes only when the frozen "
                                               "bundle content changes"},
                "caching": {"fetch_rule": "request this once per content_identity_sha256 — on first load or when "
                                          "that value changes — and omit include_model_tree on later per-frame "
                                          "robot-state requests",
                            "identical_for_every_frame_of_this_bundle": True,
                            "response_is_dynamic": True,
                            "model_content_etag_applies_to": "GET /api/v1/episodes/{episode_id}/model/assets/"
                                                             "{asset_id} only",
                            "etag_note": "this response also carries retrieved_at and the selected frame's pose, so "
                                         "a mesh-content ETag must not be attached to or compared against the whole "
                                         "robot-state response"},
                "semantics": {"links": "the frozen compiled reference layout: parent_name, joint name/type/axis, "
                                       "local_transform as the body offset in the parent body frame, and every geom "
                                       "with type, size, transform, rgba and mesh_asset_id",
                              "world_links": "compiled_initial_layout_not_live_object_state",
                              "world_links_are_not_recorded_object_positions": True,
                              "world_links_note": "a world link carrying a task object is shown where the model was "
                                                  "compiled, not where the record says it was during this Episode; "
                                                  "dynamic_scene_objects stays missing until it is attested",
                              "is_recorded_state": False,
                              "recorded_pose_lives_in": "state.recorded_payload, mapping and part_readiness"},
                "mesh_bytes": "geoms[].mesh_asset_id resolves against model_resource.assets[]; bytes only from "
                              "GET /api/v1/episodes/{episode_id}/model/assets/{asset_id}, never from the live "
                              "scene asset route",
                "summary_views_still_on_model_resource": True}

    # ---- mapping --------------------------------------------------------------------

    def _mapping(self, payload: dict[str, Any] | None, bundle_view: dict[str, Any],
                 cross_check: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Statuses follow the evidence: a reproduced TCP upgrades the fields that reproduction depends on."""
        state = payload or {}
        consistent = bool(cross_check) and cross_check.get("verdict") == "consistent"
        exercised = bool(cross_check) and not cross_check.get("joints_left_at_zero")
        arm = state.get("arm_model_qpos_rad")
        kinematics = (self.kinematics or {}).get("arm") if isinstance(self.kinematics, dict) else None
        config_names = list(kinematics.get("joint_names") or []) if isinstance(kinematics, dict) else []
        bundle_arm = bundle_view.get("arm_hinge_joints") or []
        tcp = _tcp_reference(self.kinematics)
        entries = [
            {"target": "arm_joint_positions", "recorded_field": "arm_model_qpos_rad",
             "recorded_unit": "rad", "recorded_length": _length(arm),
             "target_field": "bundle hinge joints " + ", ".join(bundle_arm),
             "status": ("verified" if consistent and exercised and bundle_arm and _length(arm) == len(bundle_arm)
                        else "partially_verified" if bundle_arm and _length(arm) == len(bundle_arm) else "unverified"),
             "verified_basis": (["the recorded TCP position is reproduced from these five values through the frozen "
                                 "tree", "the source chain addresses the joints by name"]
                                if consistent and exercised else []),
             "draw_source": "model radians, applied directly to the hinge joints",
             "requires_user_angle_conversion": False,
             "evidence": {"bundle_arm_hinge_joints_in_document_order": bundle_arm,
                          "platform_kinematics_joint_names": config_names,
                          "names_equal_to_bundle": config_names == bundle_arm,
                          "length_matches_arm_hinge_count": _length(arm) == len(bundle_arm) or None,
                          "positions_are_model_radians_not_user_radians": True,
                          "source_chain": ARM_MAPPING_CHAIN,
                          "order_attested_at_index": 3,
                          "order_attestation": "the record's own model/user joint pair differs exactly at index 3, "
                                               "which matches the platform zero offset for joint4; the other indexes "
                                               "are carried by the source chain and, when the TCP cross-check holds, "
                                               "by that reproduction as well",
                          "version_binding": VERSION_BINDING},
             "no_default_applied": True,
             "gap": "index 0, 1, 2 and 4 are mapped through the source order chain; a per-index record attestation "
                    "exists only at index 3"},
            {"target": "base_position", "recorded_field": "base_position_world_sim_m",
             "recorded_unit": "m", "recorded_length": _length(state.get("base_position_world_sim_m")),
             "target_field": self._root_description(bundle_view),
             "status": "verified" if consistent else "unverified",
             "verified_basis": (["reproducing the recorded TCP position requires the base pose to be the base body's "
                                 "world pose; the alternative convention is off by exactly the base body offset"]
                                if consistent else []), "evidence": {
                 "native_source_declaration": "backends/mujoco/backend.py assigns it from "
                                              "data.xpos[base_link], i.e. the base body frame origin in the world",
                 "bundle_root_joint": bundle_view.get("root_joint"),
                 "recorded_z_and_bundle_root_local_z_are_different_quantities": True,
                 "cross_check": "see tcp_kinematic_cross_check"},
             "no_default_applied": True,
             "gap": "the MuJoCo quantity behind the field is declared in native source that cannot be tied to a "
                    "single writer build; the kinematic cross-check is reported separately"},
            {"target": "base_orientation", "recorded_field": "base_quaternion_xyzw",
             "recorded_unit": "unit quaternion", "recorded_length": _length(state.get("base_quaternion_xyzw")),
             "target_field": "bundle transforms declare orientation as xyzw",
             "status": "verified" if consistent else "unverified",
             "verified_basis": (["the recorded TCP position is reproduced with this quaternion read in xyzw order"]
                                if consistent else []), "evidence": {
                 "recorded_field_label_declares_order": "xyzw",
                 "bundle_transform_field_declares_order": "orientation_xyzw",
                 "order_labels_agree": True,
                 "native_source_declaration": "data.xquat[base_link] converted from wxyz to xyzw by "
                                              "backends/common.py quat_wxyz_to_xyzw"},
             "no_default_applied": True,
             "gap": "the component order is labelled consistently and declared in native source, but no record-side "
                    "attestation ties this archive to that writer"},
            {"target": "gripper_joints", "recorded_field": "gripper_width_m",
             "recorded_unit": "m", "recorded_length": _length(state.get("gripper_width_m")),
             "target_field": "bundle slide joints " + ", ".join(bundle_view.get("gripper_slide_joints") or []),
             "status": "unverified", "evidence": {
                 "recorded_value_is_a_scalar_width": True,
                 "native_source_declaration": "gripper_width_m is the distance between the two finger sites "
                                              "(backends/mujoco/backend.py _snapshot_gripper_width), not a joint value",
                 "the_arm_slice_excludes_the_gripper_drive": "gripper_base_joint is ARM_JOINTS + GRIPPER_DRIVE index 5 "
                                                             "and is sliced off arm_model_qpos_rad, so no gripper "
                                                             "joint value is recorded for the frame",
                 "bundle_jaw_slide_joints": bundle_view.get("gripper_slide_joints"),
                 "other_gripper_joints_in_bundle": bundle_view.get("gripper_other_joints_in_bundle"),
                 "platform_declared_gripper_constants": (self.kinematics or {}).get("gripper")
                     if isinstance(self.kinematics, dict) else None,
                 "constants_authority": (self.kinematics or {}).get("authority") if isinstance(self.kinematics, dict) else None},
             "no_default_applied": True,
             "gap": "turning the recorded width into jaw and drive joint values needs the platform's declared "
                    "gripper constants accepted as authoritative; nothing in the record or bundle attests them"},
            {"target": "tcp_site_position", "recorded_field": "tcp_position_world_m",
             "recorded_unit": "m", "recorded_length": _length(state.get("tcp_position_world_m")),
             "target_field": f"bundle tcp_site {bundle_view.get('tcp_site')} on body {tcp.get('parent_body')}",
             "status": "verified" if consistent else "unverified",
             "verified_basis": (["the recomputed site position matches the recorded one within the stated tolerance"]
                                if consistent else []), "evidence": {
                 "bundle_declares_a_tcp_site_name": bundle_view.get("tcp_site"),
                 "platform_declared_site_attachment": {"parent_body": tcp.get("parent_body"),
                                                       "position_m": tcp.get("position_m"),
                                                       "orientation_status": tcp.get("orientation_status")},
                 "the_site_is_not_a_link_in_the_bundle": True,
                 "tcp_orientation": "not recorded",
                 "cross_check": "see tcp_kinematic_cross_check"},
             "no_default_applied": True,
             "gap": "the site offset lives in the platform reference config, not in the frozen bundle or the record; "
                    "the cross-check reports how well that attachment reproduces the recorded position"},
            {"target": "tcp_site_orientation", "recorded_field": None, "recorded_unit": None, "recorded_length": None,
             "target_field": f"site {tcp.get('site')}", "status": "missing",
             "evidence": {"recorded": "no orientation field exists in the state payload",
                          "platform_reference": tcp.get("orientation_status")},
             "no_default_applied": True, "gap": "no TCP orientation is recorded and the reference declares none"},
            {"target": "camera_extrinsics", "recorded_field": None, "recorded_unit": None, "recorded_length": None,
             "target_field": "bundle camera link chain " + " <- ".join(item["name"] for item in bundle_view.get("camera_link_chain") or []),
             "status": "missing", "evidence": {
                 "bundle_camera_ids": bundle_view.get("camera_ids"),
                 "recorded_observation_frame_id": "rgbd_optical",
                 "recorded_camera_calibration": "not present in the persisted frame, its rows or its transforms",
                 "platform_declared_mount": (self.kinematics or {}).get("camera_mount")
                     if isinstance(self.kinematics, dict) else None,
                 "placement_source": "forward kinematics of the fixed bundle plus the mapped joint state"},
             "no_default_applied": True,
             "gap": "no recorded camera calibration, and the declared mount body is not rigid to the TCP"},
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

    def _angles_block(self, bundle_view: dict[str, Any]) -> dict[str, Any]:
        block = _model_vs_user_angles(self.kinematics)
        config_names = ((self.kinematics or {}).get("arm") or {}).get("joint_names") if isinstance(self.kinematics, dict) else None
        block["config_joint_names_equal_bundle_arm_hinges"] = (list(config_names or [])
                                                               == bundle_view.get("arm_hinge_joints"))
        return block

    # ---- kinematic cross-check ------------------------------------------------------

    def _cross_check(self, payload: dict[str, Any] | None, bundle_view: dict[str, Any]) -> dict[str, Any]:
        """Rebuild the TCP site position from recorded state plus the frozen tree and compare it.

        Two root conventions are tested rather than assumed, because the difference between them is
        exactly the bundle's own base body offset: the recorded base pose read as the body's world
        pose, and the same reading with that offset added on top.
        """
        if bundle_view.get("status") != "match" or self.bundle is None:
            return {"status": "not_computable", "reason": "the recorded model identity does not match the frozen bundle"}
        state = payload or {}
        tcp = _tcp_reference(self.kinematics)
        arm_names = bundle_view.get("arm_hinge_joints") or []
        links = [link.model_dump() for link in self.bundle.scene.links]
        recorded_tcp = _vec(state.get("tcp_position_world_m"))
        root_offset = _vec((bundle_view.get("root_joint") or {}).get("local_position_m")) or (0.0, 0.0, 0.0)
        hypotheses = []
        for label, shift in (("recorded_pose_is_base_body_world_pose", (0.0, 0.0, 0.0)),
                             ("recorded_pose_needs_the_bundle_base_offset", root_offset)):
            position = _vec(state.get("base_position_world_sim_m"))
            if position is None:
                computed = {"status": "not_computable", "reason": "the frame records no numeric base position"}
            else:
                shifted = [position[0] + shift[0], position[1] + shift[1], position[2] + shift[2]]
                computed = tcp_from_recorded_state(links, arm_names, state.get("arm_model_qpos_rad"),
                                                  shifted, state.get("base_quaternion_xyzw"),
                                                  tcp.get("parent_body"), tcp.get("position_m"))
            entry = {"hypothesis": label, "status": computed.get("status")}
            if computed.get("status") == "computed" and recorded_tcp is not None:
                error = distance_m(tuple(computed["position_m"]), recorded_tcp)
                entry.update({"computed_tcp_position_m": computed["position_m"],
                              "abs_error_m": error,
                              "difference_m": [computed["position_m"][index] - recorded_tcp[index] for index in range(3)],
                              "verdict": "consistent" if error <= TOLERANCE_M else "inconsistent",
                              "chain_links": computed["chain_links"],
                              "joints_on_chain": computed["joints_on_chain"],
                              "movable_joints_on_chain": computed["movable_joints_on_chain"],
                              "joints_left_at_zero": computed["joints_left_at_zero"]})
            elif computed.get("status") != "computed":
                entry.update({"reason": computed.get("reason"), "inputs": computed.get("inputs")})
            hypotheses.append(entry)
        supported = [item for item in hypotheses if item.get("verdict") == "consistent"]
        primary = hypotheses[0]
        result = {"status": "computed" if primary.get("abs_error_m") is not None else "not_computable",
                  "method": "pure forward kinematics over the frozen bundle tree; hinge rotation about the model "
                            "joint axis in the child body frame, then the declared site offset on its parent body",
                  "recorded_tcp_position_m": list(recorded_tcp) if recorded_tcp else None,
                  "hypotheses": hypotheses,
                  "supported_hypotheses": [item["hypothesis"] for item in supported],
                  "consistency_tolerance_m": TOLERANCE_M,
                  "tolerance_authority": "stated by this slice to judge kinematic agreement; it is not a calibration "
                                         "limit and not a contract threshold",
                  "verdict": primary.get("verdict"),
                  "computed_tcp_position_m": primary.get("computed_tcp_position_m"),
                  "abs_error_m": primary.get("abs_error_m"),
                  "difference_m": primary.get("difference_m"),
                  "chain_links": primary.get("chain_links"),
                  "joints_on_chain": primary.get("joints_on_chain"),
                  "movable_joints_on_chain": primary.get("movable_joints_on_chain"),
                  "joints_left_at_zero": primary.get("joints_left_at_zero"),
                  "inputs_used": {"base_position": "base_position_world_sim_m",
                                  "base_orientation": "base_quaternion_xyzw",
                                  "arm_angles": "arm_model_qpos_rad",
                                  "site_attachment": "platform kinematics reference (declared authority)"},
                  "single_frame_scope": "this comparison covers the one frame this request returned; aggregate "
                                        "error and joint-excursion coverage come from the offline check tool",
                  "supports": "kinematic consistency between the recorded state, the frozen model tree and the "
                              "declared site attachment",
                  "does_not_prove": "this comparison is arithmetic on recorded numbers: it does not calibrate hardware, "
                                    "does not prove which native build wrote the archive, and does not verify rendered "
                                    "appearance"}
        return result if result["status"] == "computed" else {**result,
                                                              "reason": primary.get("reason")
                                                                        or "the frame lacks a numeric recorded TCP position to compare with"}

    # ---- per-part readiness ---------------------------------------------------------

    def _part_readiness(self, payload: dict[str, Any] | None, bundle_view: dict[str, Any],
                        mapping: list[dict[str, Any]], cross_check: dict[str, Any] | None) -> list[dict[str, Any]]:
        state = payload or {}
        by_target = {item["target"]: item for item in mapping}
        identity_ok = bundle_view.get("status") == "match"
        consistent = bool(cross_check) and cross_check.get("verdict") == "consistent"
        arm_values = state.get("arm_model_qpos_rad")
        parts = [
            {"capability": "fixed_model_reference_assembly",
             "status": "ready" if identity_ok else "blocked",
             "requires": ["model/scene identity match", "mesh assets with digests", "the link tree"],
             "pose_input_required": False,
             "inputs_available": {"identity": bundle_view.get("status"),
                                  "asset_count": len(bundle_view.get("assets") or []),
                                  "link_count": bundle_view.get("link_count"),
                                  "asset_routes": "GET /api/v1/episodes/{episode_id}/model/assets/{asset_id}"},
             "frontend_rule": "the frozen model may be assembled and shown for any frame of this Episode once the "
                              "identity matches; a whole-robot pose gap never blocks this assembly",
             "gaps": [] if identity_ok else ["the recorded model identity does not match the frozen bundle"]},
            {"capability": "arm_local_pose",
             "status": "ready_with_caveats" if identity_ok and _length(arm_values) == len(bundle_view.get("arm_hinge_joints") or []) else "blocked",
             "requires": ["arm_model_qpos_rad", "bundle hinge joints joint1..joint5"],
             "pose_input_required": True,
             "inputs_available": {"recorded_length": _length(arm_values),
                                  "bundle_joints": bundle_view.get("arm_hinge_joints"),
                                  "draw_in_model_radians": True},
             "frontend_rule": "apply the recorded five values directly to the five arm hinges in model radians; do "
                              "not convert through user angles to draw, and do not claim an axis is exercised unless "
                              "the samples actually move it",
             "evidence": {"source_chain": ARM_MAPPING_CHAIN, "kinematic_cross_check": (cross_check or {}).get("verdict")},
             "gaps": ["the writer is narrowed to the 2026-10-17 release family but not identified",
                      "per-index record attestation exists only at index 3"]},
            {"capability": "base_pose_placement",
             "status": "conditional" if not consistent else "ready_with_caveats",
             "requires": ["base_position_world_sim_m", "base_quaternion_xyzw"],
             "pose_input_required": True,
             "inputs_available": {"position_length": _length(state.get("base_position_world_sim_m")),
                                  "quaternion_length": _length(state.get("base_quaternion_xyzw"))},
             "frontend_rule": "the base may be placed only with the caveat shown beside it: the field's meaning comes "
                              "from native source that is not bound to an identified writer build; if the kinematic "
                              "cross-check disagrees, do not place the base",
             "evidence": {"mapping_status": by_target["base_position"]["status"],
                          "orientation_mapping_status": by_target["base_orientation"]["status"],
                          "kinematic_cross_check": (cross_check or {}).get("verdict"),
                          "abs_error_m": (cross_check or {}).get("abs_error_m")},
             "gaps": [by_target["base_position"]["gap"], by_target["base_orientation"]["gap"]]},
            {"capability": "gripper_visual_appearance",
             "status": "conditional",
             "requires": ["gripper_width_m", "the platform's declared gripper constants"],
             "pose_input_required": True,
             "inputs_available": {"recorded_scalar": _length(state.get("gripper_width_m")) == 1,
                                  "platform_constants": (self.kinematics or {}).get("gripper")
                                      if isinstance(self.kinematics, dict) else None},
             "frontend_rule": "the jaws may be posed only from the platform reference constants, which declare "
                              "themselves not native-attested; otherwise keep the jaws at the bundle's own layout and "
                              "label the gripper as not-from-record",
             "gaps": [by_target["gripper_joints"]["gap"]]},
            {"capability": "tcp_position_marker",
             "status": "ready_with_caveats" if consistent else "conditional",
             "requires": ["a TCP position", "the declared site attachment"],
             "pose_input_required": True,
             "inputs_available": {"recorded_position": _length(state.get("tcp_position_world_m")),
                                  "computed_position": (cross_check or {}).get("computed_tcp_position_m"),
                                  "abs_error_m": (cross_check or {}).get("abs_error_m")},
             "frontend_rule": "a point marker is allowed; it must not be drawn as an oriented frame because no TCP "
                              "orientation is recorded",
             "gaps": [by_target["tcp_site_position"]["gap"], by_target["tcp_site_orientation"]["gap"]]},
            {"capability": "tcp_orientation_frame", "status": "blocked",
             "requires": ["a recorded TCP orientation"], "pose_input_required": True,
             "inputs_available": {"recorded": False},
             "frontend_rule": "do not synthesise an oriented TCP frame",
             "gaps": [by_target["tcp_site_orientation"]["gap"]]},
            {"capability": "camera_view_from_record", "status": "blocked",
             "requires": ["recorded camera calibration or an attested mount"], "pose_input_required": True,
             "inputs_available": {"recorded_calibration": False,
                                  "declared_mount": (self.kinematics or {}).get("camera_mount")
                                      if isinstance(self.kinematics, dict) else None},
             "frontend_rule": "an image plane or a viewer-placed camera is allowed; a record-derived camera pose is not",
             "gaps": [by_target["camera_extrinsics"]["gap"]]},
            {"capability": "dynamic_scene_objects_from_record", "status": "blocked",
             "requires": ["recorded object poses"], "pose_input_required": True,
             "inputs_available": {"recorded": False},
             "frontend_rule": "keep world objects at the bundle's compiled initial layout and label that layout as "
                              "not the historical state",
             "gaps": [by_target["dynamic_scene_objects"]["gap"]]},
            {"capability": "wheel_pose_from_record", "status": "not_required",
             "requires": [], "pose_input_required": False,
             "inputs_available": {"unlabelled_velocity_count": _length(state.get("wheel_velocity_rad_s"))},
             "frontend_rule": "wheel angles are not needed to place the robot for this slice",
             "gaps": [by_target["wheel_joint_velocities"]["gap"]]},
        ]
        return parts

    @staticmethod
    def _capability_summary(parts: list[dict[str, Any]], bundle_view: dict[str, Any],
                            cross_check: dict[str, Any] | None) -> dict[str, Any]:
        usable = [item["capability"] for item in parts if item["status"] in ("ready", "ready_with_caveats")]
        conditional = [item["capability"] for item in parts if item["status"] == "conditional"]
        blocked = [item["capability"] for item in parts if item["status"] == "blocked"]
        return {"usable_now": usable, "usable_only_with_the_named_caveat": conditional, "blocked": blocked,
                "fixed_model_assembly_available": bool(bundle_view.get("status") == "match"),
                "whole_robot_pose_rebuildable": False,
                "escalation_forbidden": "a usable part never upgrades into whole-robot rebuild, rendering or "
                                        "synchronised replay",
                "defaults_forbidden": "no part may be filled with an assumed value",
                "kinematic_agreement": (cross_check or {}).get("verdict"),
                "abs_tcp_error_m": (cross_check or {}).get("abs_error_m")}

    def _root_description(self, bundle_view: dict[str, Any]) -> str | None:
        root = bundle_view.get("root_joint")
        return None if not root else f"bundle root link {root['name']} free joint {root['joint_name']}"

    @staticmethod
    def _readiness(mapping: list[dict[str, Any]], bundle_view: dict[str, Any], parts: list[dict[str, Any]],
                  cross_check: dict[str, Any] | None) -> dict[str, Any]:
        ready = sum(1 for entry in mapping if entry["status"] in ("verified", "partially_verified"))
        return {"model_identity": bundle_view["status"],
                "mapping_valid_for_this_episode": bundle_view["status"] == "match",
                "mapped_targets_partially_or_fully_verified": f"{ready}/{len(mapping)}",
                "robot_state_can_be_rebuilt_without_assumptions": False,
                "parts_ready": [item["capability"] for item in parts if item["status"] in ("ready", "ready_with_caveats")],
                "parts_conditional": [item["capability"] for item in parts if item["status"] == "conditional"],
                "parts_blocked": [item["capability"] for item in parts if item["status"] == "blocked"],
                "blocking_fields": [entry["target"] for entry in mapping
                                    if entry["status"] in ("unverified", "missing")],
                "kinematic_agreement": (cross_check or {}).get("verdict"),
                "next_round_owner": "frontend assembly plus an attested base/gripper mapping source",
                "note": "resource identity, digests and joint-length checks pass; the remaining gaps are attestation "
                        "gaps, not missing files"}

    @staticmethod
    def _gaps(mapping: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"target": entry["target"], "status": entry["status"], "gap": entry["gap"]}
                for entry in mapping if entry["status"] in ("unverified", "missing")]


# The five arm hinges of this model, taken from the bundle rather than assumed by position.
ARM_HINGE_JOINTS = ("joint1", "joint2", "joint3", "joint4", "joint5")
GRIPPER_SLIDE_JOINTS = ("left_jaw_joint", "right_jaw_joint")
WHEEL_HINGE_JOINTS = ("front_left_joint", "rear_left_joint", "front_right_joint", "rear_right_joint")

# Stated here so the agreement verdict is reproducible; this is not a calibration limit.
TOLERANCE_M = 0.005


def _length(value: Any) -> int | None:
    return len(value) if isinstance(value, list) else (1 if isinstance(value, (int, float)) and not isinstance(value, bool) else None)
