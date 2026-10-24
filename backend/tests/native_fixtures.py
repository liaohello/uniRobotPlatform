"""Synthetic native HTTP endpoints for the preparation chain.

These payloads describe a hypothetical native process that satisfies the pinned
recipe and (optionally) declares the motion-free binding protocol. They are
test fixtures, not a real run and not product acceptance.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import urllib.error
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from unirobot.api import create_app
from unirobot.contracts import AdapterConfig
from unirobot.mobilecar import MobileCarIntegration
from unirobot.recipe import Recipe, canonical, digest, load_recipe

IDENTITY = {"run_id": "fixture-run", "backend_generation": 1, "episode_id": "fixture-episode"}
ASSET_BODY = b"synthetic compiled mesh, not a product model"
ASSET_SHA = hashlib.sha256(ASSET_BODY).hexdigest()
TRANSFORM = {"position_m": [0, 0, 0], "orientation_xyzw": [0, 0, 0, 1]}


class FakeNative:
    def __init__(self, payloads: dict, *, binding: bool = False) -> None:
        self.payloads = payloads
        self.binding = binding
        self.calls: list[tuple[str, str]] = []
        self.bodies: list[tuple[str, dict]] = []
        self.bindings: dict[str, dict] = {}
        self.fail_path: str | None = None
        self.recording_status = "IDLE"
        self.recording_segment_id: str | None = None

    def open(self, request, *, timeout):
        path = urlsplit(request.full_url).path
        method = request.get_method()
        self.calls.append((method, path))
        payload = json.loads(request.data) if request.data else {}
        if request.data:
            self.bodies.append((path, payload))
        if path == self.fail_path:
            raise urllib.error.URLError("synthetic connection failure")
        if path.startswith("/api/v1/session/") or path == "/api/v1/recording/begin":
            return self._session(method, path, payload)
        body = self.payloads[path]
        return io.BytesIO(body if isinstance(body, bytes) else json.dumps(body).encode())

    def _json(self, value: dict) -> io.BytesIO:
        return io.BytesIO(json.dumps(value).encode())

    def _session(self, method: str, path: str, body: dict):
        if not self.binding:
            raise urllib.error.HTTPError(path, 404, "not found", {}, None)
        if method == "GET" and path.startswith("/api/v1/session/prepared/"):
            binding = self.bindings.get(path.rsplit("/", 1)[-1])
            if binding is None:
                raise urllib.error.HTTPError(path, 404, "unknown binding", {}, None)
            return self._json(binding)
        if method == "POST" and path == "/api/v1/session/prepare":
            health = self.payloads["/api/v1/health"]
            if any(body.get(key) != health[key] for key in IDENTITY):
                return self._json({"accepted": False, "code": "runtime_identity_mismatch",
                                   "reason": "runtime identity mismatch"})
            for existing in self.bindings.values():
                if existing["state"] in {"prepared", "started"}:
                    return self._json({"accepted": False, "code": "binding_conflict",
                                       "reason": "runtime already has a binding"})
            binding_id = f"binding-{len(self.bindings) + 1}"
            record = {
                "accepted": True, "reason": "", "protocol": "m1-binding-1",
                "binding_id": binding_id, "session_id": body["session_id"],
                "run_id": body["run_id"], "backend_generation": body["backend_generation"],
                "episode_id": body["episode_id"], "config_fingerprint": body["config_fingerprint"],
                "state": "prepared", "motion_commands_accepted": False,
                "created_at_backend_monotonic_s": 10.0,
                "expires_at_backend_monotonic_s": 100.0,
                "started_at_backend_monotonic_s": None,
                "control_scope_granted": [], "owner_state": "not_acquired",
                "owner_session_id": None, "lease_expires_at_backend_monotonic_s": None,
                "recording_required_for_motion": True, "recording_begin_required": True,
                "recording_ready": False, "motion_ready": False,
                "motion_blockers": ["binding_not_started"],
            }
            self.bindings[binding_id] = record
            return self._json(record)
        if method == "POST" and path == "/api/v1/session/start":
            record = self.bindings.get(body.get("binding_id", ""))
            if record is None:
                return self._json({"started": False, "code": "binding_not_found",
                                   "reason": "unknown binding"})
            if record["session_id"] != body.get("session_id"):
                return self._json({"started": False, "code": "binding_session_mismatch",
                                   "reason": "session_id mismatch"})
            if record["config_fingerprint"] != body.get("config_fingerprint"):
                return self._json({"started": False, "code": "binding_config_mismatch",
                                   "reason": "config_fingerprint mismatch"})
            record.update(state="started", started_at_backend_monotonic_s=42.5,
                          control_scope_granted=["base", "arm", "gripper"],
                          owner_state="not_acquired", owner_session_id=None,
                          lease_expires_at_backend_monotonic_s=None,
                          recording_ready=False, motion_ready=False,
                          motion_blockers=["recording_not_ready"])
            return self._json({**record, "started": True})
        if method == "POST" and path == "/api/v1/session/release":
            record = self.bindings.get(body.get("binding_id", ""))
            if record is None:
                return self._json({"released": False})
            record.update(state="released", reason="released by the platform")
            return self._json({"released": True})
        if method == "POST" and path == "/api/v1/recording/begin":
            record = self.bindings.get(body.get("binding_id", ""))
            if record is None or record["state"] != "started":
                return self._json({"accepted": False, "reason": "binding is not started"})
            if record["session_id"] != body.get("session_id"):
                return self._json({"accepted": False, "reason": "session_id mismatch"})
            if record["config_fingerprint"] != body.get("config_fingerprint"):
                return self._json({"accepted": False, "reason": "config_fingerprint mismatch"})
            if self.recording_status != "IDLE":
                return self._json({"accepted": False,
                                   "reason": f"recording is already {self.recording_status}"})
            self.recording_status = "RECORDING"
            self.recording_segment_id = "seg_fixture_001"
            recording = self.payloads["/api/v1/snapshot"]["recording"]
            recording.update(
                status="RECORDING",
                episode_id=record["episode_id"],
                recording_segment_id=self.recording_segment_id,
                command_capture_ready=True,
                error=None,
            )
            self.payloads["/api/v1/health"]["recording_status"] = "RECORDING"
            return self._json({
                "accepted": True, "reason": "", "protocol": "m1-recording-1",
                "state": "started", "motion_commands_accepted": False,
                "binding_id": record["binding_id"], "session_id": record["session_id"],
                "config_fingerprint": record["config_fingerprint"],
                "run_id": record["run_id"], "backend_generation": record["backend_generation"],
                "episode_id": record["episode_id"],
                "recording_segment_id": self.recording_segment_id,
                "recording_status": "RECORDING", "command_capture_ready": True,
                "recording_start_event_seq": 1,
                "initial_snapshot_sha256": "d" * 64,
                "started_at_backend_monotonic_s": 43.0,
                "recording_required_for_motion": True,
                "recording_begin_required": True, "durable_start_records": True,
            })
        raise urllib.error.HTTPError(path, 404, "not found", {}, None)


def build_payloads(*, interface_profile: str | None = None, declare_protocols: bool = False,
                   safety_latched: bool = False, owners: tuple[str | None, str | None] = (None, None),
                   recording_status: str = "IDLE", user_limit_shift: float = 0.0) -> dict:
    recipe = load_recipe()
    expected = recipe.expected
    kinematics = recipe.kinematics
    profile = interface_profile or expected["interface_profile"]
    model_limits = [[-2.09, 2.09] for _ in range(5)]
    zero = kinematics["arm"]["zero_model_rad"]
    user_limits = [[min(low - z, high - z), max(low - z, high - z)] for (low, high), z in zip(model_limits, zero)]
    user_limits[0] = [user_limits[0][0] + user_limit_shift, user_limits[0][1]]
    resource = {key: expected[key] for key in ("contract_version", "model_id", "model_sha256", "scene_id")}
    link = {"name": "base_link", "parent_name": None, "joint_name": None, "joint_type": "free",
            "joint_axis": [0, 0, 1], "local_transform": TRANSFORM,
            "geoms": [{"name": "base_visual", "geom_type": "mesh", "size_m": [1, 1, 1],
                       "local_transform": TRANSFORM, "rgba": [1, 1, 1, 1], "mesh_asset_id": "base",
                       "collision": False, "group": 1}]}
    scene = {**resource, "links": [link], "world_links": [],
             "mesh_assets": [{"asset_id": "base", "uri": "https://untrusted.invalid/ignored",
                              "sha256": ASSET_SHA, "media_type": "model/stl"}],
             "camera_ids": ["rgbd"], "tcp_site": kinematics["tcp"]["site"], "source": "mujoco_model_compile"}
    capabilities = {
        **resource, "backend_kind": "mujoco",
        "arm_joint_names": list(kinematics["arm"]["joint_names"]),
        "arm_user_limits_rad": user_limits,
        "arm_velocity_limits_rad_s": [0.6] * 5,
        "gripper_min_width_m": kinematics["gripper"]["min_width_m"],
        "gripper_max_width_m": kinematics["gripper"]["max_width_m"],
        "base_linear_limit_m_s": 0.05, "base_yaw_limit_rad_s": 0.3,
        "tcp_position_tolerance_m": 0.005, "tcp_orientation_is_soft": True,
        "supported_commands": list(expected["commands"]), "sensor_streams": list(expected["sensor_streams"]),
        "camera_parent_body": kinematics["camera_mount"]["parent_body"],
        "tcp_parent_body": kinematics["tcp"]["parent_body"], "ground_truth_policy_visible": False,
        "config_manifest_sha256": expected["config_manifest_sha256"],
        "scene_manifest_sha256": digest(scene),
        "runtime_python_version": "3.11.9",
        "runtime_package_versions": dict(
            recipe.body["dependencies"]["requirements_lock"]["packages"]
        ),
    }
    if declare_protocols:
        capabilities["session_binding_protocol"] = recipe.required_protocols["session_binding"]
        capabilities["recording_begin_protocol"] = recipe.required_protocols["recording_begin"]
    snapshot = {
        **IDENTITY, "contract_version": "mobilecar-1.0",
        "episode_started_backend_monotonic_s": 0.0, "backend_monotonic_s": 20.0, "sim_time_s": 2.0,
        "feedback_time_s": 19.99, "wall_utc": "2026-10-23T00:00:00Z", "clock_id": "backend_monotonic",
        "control_tick_id": "tick-1", "task_phase": "OBSERVE",
        "base": {"frame_id": "base_link", "position_world_sim_m": [0, 0, 0], "orientation_world_sim_xyzw": [0, 0, 0, 1],
                 "vx_m_s": 0.0, "vy_m_s": 0.0, "wz_rad_s": 0.0, "requested_vx_m_s": 0.0, "requested_vy_m_s": 0.0,
                 "requested_wz_rad_s": 0.0, "stopped": True, "stop_latched": safety_latched},
        "arm": {"user_joint_positions_rad": [0.0] * 5, "model_joint_positions_rad": list(zero),
                "joint_velocities_rad_s": [0.0] * 5, "joint_torques_nm": [0.0] * 5, "joint_margin_rad": [1.0] * 5,
                "model_limits_rad": model_limits, "coordinates_status": "known",
                "user_joint_targets_rad": [0.0] * 5, "model_joint_targets_rad": list(zero)},
        "gripper": {"width_m": 0.025, "model_drive_position_rad": -1.077632656580025,
                    "target_width_m": 0.025, "model_drive_target_rad": -1.077632656580025},
        "tcp": {"frame_id": "world_sim", "position_m": [0.3, 0.0, 0.1], "orientation_xyzw": [0, 0, 0, 1],
                "position_error_m": None, "orientation_error_rad": None, "held": False},
        "sensors": [],
        "model_joint_positions_rad": {name: value for name, value in zip(kinematics["arm"]["joint_names"], zero)},
        "base_owner_session_id": owners[0], "arm_owner_session_id": owners[1],
        "active_session_id": owners[0] or owners[1], "active_operator_kind": "human" if any(owners) else None,
        "safety_latched": safety_latched,
        "recording": {"status": recording_status, "episode_id": None, "command_capture_ready": False,
                      "recording_segment_id": None, "queued_events": 0, "dropped_events": 0, "error": None},
    }
    return {
        "/api/v1/health": {**IDENTITY, "status": "ok", "recording_status": recording_status,
                           "recording_required_for_motion": True, "interface_profile": profile},
        "/api/v1/capabilities": capabilities,
        "/api/v1/scene": scene,
        "/api/v1/scene/assets/base": ASSET_BODY,
        "/api/v1/snapshot": snapshot,
    }


def fixture_app(tmp_path, *, binding: bool = False, **payload_kwargs):
    integration = MobileCarIntegration(
        AdapterConfig(id="mobilecar", title="fixture", project_root="unused", base_url="http://fixture.invalid"))
    payloads = build_payloads(**payload_kwargs)
    fake = FakeNative(copy.deepcopy(payloads), binding=binding)
    integration._opener = fake
    recipe = load_recipe()
    body = copy.deepcopy(recipe.body)
    # The synthetic scene cannot reproduce the pinned compiled-scene digest.
    # Declare a self-consistent fixture digest so the platform's same-scope
    # comparison can be exercised without claiming the real native scene.
    body["expected"]["scene_manifest_sha256"] = digest(payloads["/api/v1/scene"])
    body["expected"]["config_manifest_sha256"] = recipe.expected["config_manifest_sha256"]
    fixture_recipe = Recipe(body=body, sources=recipe.sources, pin=recipe.pin)
    app = create_app(draft_db_path=tmp_path / "prepare.sqlite3",
                     mobilecar_integration=integration, recipe=fixture_recipe)
    return app, fake, fake.payloads, integration


def create_draft(http) -> dict:
    response = http.post("/api/v1/experiment-drafts", json={"name": "Fixture", "description": "synthetic"})
    assert response.status_code == 201, response.text
    return response.json()


def validate(http, draft: dict) -> dict:
    response = http.post(f"/api/v1/experiment-drafts/{draft['draft_id']}/validate",
                         json={"execution_revision": draft["execution_revision"], "fingerprint": draft["fingerprint"]})
    assert response.status_code == 200, response.text
    return response.json()["validation"]["result"]


def session_request(draft: dict, snapshot_id: str, key: str = "fixture-key") -> dict:
    return {"execution_revision": draft["execution_revision"], "fingerprint": draft["fingerprint"],
            "validated_snapshot_id": snapshot_id, "idempotency_key": key}
