"""Test-only launcher: production platform code + a native mock HTTP candidate.

This module deliberately builds a *test-only* recipe from the live mock native's
own declarations. It never changes the production G1 recipe, pin or fingerprint,
and it refuses to run against a non-mock native. Use it only for protocol
integration over real HTTP; the mock backend has no MuJoCo physics.

Environment:
  UNIROBOT_MOCK_NATIVE_URL  e.g. http://127.0.0.1:18947
  UNIROBOT_MOCK_TEST_DB     SQLite path for drafts/snapshots/sessions
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

from unirobot.api import create_app
from unirobot.contracts import AdapterConfig
from unirobot.mobilecar import MobileCarIntegration
from unirobot.recipe import Recipe, canonical, digest, load_recipe


def _get(base: str, path: str) -> dict[str, Any]:
    with urllib.request.urlopen(base.rstrip("/") + path, timeout=3) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path}: expected a JSON object")
    return value


def build_test_recipe(base: str) -> Recipe:
    capabilities = _get(base, "/api/v1/capabilities")
    health = _get(base, "/api/v1/health")
    scene = _get(base, "/api/v1/scene")
    snapshot = _get(base, "/api/v1/snapshot")
    attestation = _get(base, "/api/v1/attestation")
    if capabilities.get("backend_kind") != "mock":
        raise SystemExit("refusing to build the test recipe against a non-mock native")
    required = {
        "session_binding": ("session_binding_protocol", "m1-binding-1"),
        "recording_begin": ("recording_begin_protocol", "m1-recording-1"),
        "session_stop": ("session_stop_protocol", "m1-stop-1"),
        "recording_end": ("recording_end_protocol", "m1-end-1"),
    }
    for key, (field, expected) in required.items():
        if capabilities.get(field) != expected:
            raise SystemExit(f"native does not declare {expected} (capabilities.{field})")
    required_protocols = {key: value[1] for key, value in required.items()}
    resource = {key: scene[key] for key in ("contract_version", "model_id", "model_sha256", "scene_id")}
    if any(capabilities.get(key) != resource[key] for key in resource):
        raise SystemExit("mock native capabilities and scene identity disagree")
    production = load_recipe()
    packages = production.body["dependencies"]["requirements_lock"]["packages"]
    joint_names = list(capabilities["arm_joint_names"])
    kinematics = {
        "schema_version": 1,
        "profile_id": "landerpi.mock-protocol-testonly.v1",
        "authority": "test_only_mock_native",
        "arm": {
            "joint_names": joint_names,
            "zero_model_rad": [0.0] * len(joint_names),
            "user_direction": [1.0] * len(joint_names),
        },
        "gripper": {
            "min_width_m": float(capabilities["gripper_min_width_m"]),
            "max_width_m": float(capabilities["gripper_max_width_m"]),
        },
        "tcp": {"parent_body": capabilities["tcp_parent_body"], "site": scene["tcp_site"]},
        "camera_mount": {"parent_body": capabilities["camera_parent_body"]},
        "sources": ["live mock native capabilities; no physics"],
        "limitations": ["test-only protocol recipe; not the production G1 recipe"],
    }
    expected = {
        "contract_version": capabilities["contract_version"],
        "backend_kind": capabilities["backend_kind"],
        "interface_profile": health["interface_profile"],
        "model_id": capabilities["model_id"],
        "model_sha256": capabilities["model_sha256"],
        "scene_id": capabilities["scene_id"],
        "scene_file_sha256": None,
        "scene_file_digest_scope": "test-only mock; no source XML digest",
        "commands": list(capabilities["supported_commands"]),
        "sensor_streams": list(capabilities["sensor_streams"]),
        "config_manifest_sha256": attestation["config_manifest_sha256"],
        "scene_manifest_sha256": attestation["scene_manifest_sha256"],
        "config_manifest_scope": "test-only live mock attestation",
        "scene_manifest_scope": "test-only live mock compiled scene",
    }
    body = {
        "recipe_id": "mobilecar.g1.teleop.mock-testonly",
        "recipe_revision": 2,
        "preset": {
            "argv": ["mobilecar", "--backend", "mock", "--require-recording"],
            "env": {},
            "config_path": "configs/default.yaml",
            "effective_overrides": {
                "backend.kind": "mock",
                "recording.required_for_motion": True,
            },
            "execution_location": "test_only_server_mock_no_physics",
            "editable_initial_state_fields": [],
            "execution_sources": ["human_teleop"],
            "recording_profile": "configs/profiles/g2a_rgbd_5hz.yaml",
            "action_profile": "configs/profiles/g2a_action_teleop_v1.yaml",
        },
        "expected": expected,
        "native": {
            "commit": "test-only-mock",
            "worktree_status": "",
            "manifest_sha256": "test-only-mock",
            "manifest_digest_format": "not applicable",
        },
        "dependencies": {
            "python": production.body["dependencies"]["python"],
            "requirements_lock": {
                "source": {
                    "project": "test-only",
                    "commit": "test-only",
                    "path": "none",
                    "sha256": "0" * 64,
                },
                "release_file": {"path": "test-only", "sha256": "0" * 64, "size_bytes": 0},
                "packages": packages,
                "verification": {
                    "release_file_bytes_read": False,
                    "source_digest_matches": False,
                    "package_pins_match_file": False,
                    "runtime_environment": "test-only launcher; not verified",
                },
            },
        },
        "required_protocols": required_protocols,
        "kinematics": {
            "profile_id": kinematics["profile_id"],
            "digest": digest(kinematics),
            "body": kinematics,
        },
        "native_attestation": {
            "generated_by": "backend/tools/mock_native_protocol_app.py",
            "generated_from": {
                "mock_native": base,
                "backend_kind": capabilities["backend_kind"],
            },
        },
        "attestation": {
            "declared_by": "test_only_mock_native",
            "native_attested": False,
            "limitations": [
                "test-only recipe built from live mock declarations; not the production G1 recipe",
                "mock backend does not advance MuJoCo physics",
                "requirements-lock release-file verification is disabled for this test recipe",
            ],
        },
    }
    # The snapshot model limits are part of the live mock snapshot; the test
    # profile uses zero/direction one so the platform recomputes the same range.
    if not snapshot.get("arm", {}).get("model_limits_rad"):
        raise SystemExit("mock snapshot has no model limits")
    return Recipe(
        body=body,
        sources=[{"role": "test_only_mock_native", "path": base, "sha256": "test-only"}],
        pin={},
    )


def build_app() -> Any:
    base = os.environ.get("UNIROBOT_MOCK_NATIVE_URL", "").strip()
    if not base:
        raise SystemExit("UNIROBOT_MOCK_NATIVE_URL is required")
    db = Path(os.environ.get("UNIROBOT_MOCK_TEST_DB", "/tmp/unirobot-mock-test.sqlite3"))
    db.parent.mkdir(parents=True, exist_ok=True)
    integration = MobileCarIntegration(
        AdapterConfig(id="mobilecar", title="test-only mock native", project_root="unused", base_url=base)
    )
    return create_app(
        recipe=build_test_recipe(base),
        mobilecar_integration=integration,
        draft_db_path=db,
    )


app = build_app()
