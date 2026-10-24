"""Motion-free validation, prepared Session and explicit Start semantics.

The native endpoint is synthetic. It declares the binding protocol only in the
cases that test the verified path; the live protocol has no such capability.
"""

import copy
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from native_fixtures import create_draft, fixture_app, session_request, validate
from unirobot.recipe import RecipeError, load_recipe
from unirobot.settings import BACKEND_ROOT


@pytest.fixture()
def prepared_client(tmp_path):
    app, fake, payloads, _ = fixture_app(tmp_path, binding=True, declare_protocols=True)
    with TestClient(app) as http:
        yield http, fake, payloads, app


def eligible_snapshot(http):
    draft = create_draft(http)
    result = validate(http, draft)
    assert result["execution_eligible"] is True, result["blocking_reasons"]
    assert result["validated_snapshot_id"] == result["snapshot_id"]
    return draft, result


def test_snapshot_is_immutable_and_reproducible_for_unchanged_evidence(tmp_path):
    app, _, _, _ = fixture_app(tmp_path)
    with TestClient(app) as http:
        draft = create_draft(http)
        first = validate(http, draft)
        second = validate(http, draft)
        assert second["snapshot_id"] == first["snapshot_id"]
        assert second["snapshot_sha256"] == first["snapshot_sha256"]
        assert first["reused"] is False and second["reused"] is True
        stored = http.get(f"/api/v1/config-snapshots/{first['snapshot_id']}").json()
        assert stored == http.get("/api/v1/config-snapshots").json()[-1]
        assert stored["snapshot_sha256"] == first["snapshot_sha256"]
        assert stored["validation_scope"] == "motion_free_configuration_and_declared_protocol_only"
        assert http.get("/api/v1/config-snapshots/missing").status_code == 404


def test_prepared_session_requires_a_verified_native_binding(prepared_client):
    http, fake, _, _ = prepared_client
    draft, snapshot = eligible_snapshot(http)
    response = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"]))
    assert response.status_code == 201, response.text
    session = response.json()["session"]
    assert response.json()["replayed"] is False
    assert session["state"] == "prepared"
    assert session["execution_eligible"] is True and session["start_available"] is True
    assert session["native_binding"]["status"] == "verified"
    assert session["native_binding"]["config_fingerprint"] == snapshot["snapshot_id"]
    assert session["native_identity"] == {"run_id": "fixture-run", "backend_generation": 1, "episode_id": "fixture-episode"}
    assert http.get(f"/api/v1/sessions/{session['session_id']}").json() == session
    assert http.get("/api/v1/sessions").json()[0]["session_id"] == session["session_id"]
    assert http.get("/api/v1/sessions/missing").status_code == 404

    replay = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"]))
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    assert replay.json()["session"]["session_id"] == session["session_id"]


def test_start_reports_a_receipt_and_is_idempotent(prepared_client):
    http, _, _, _ = prepared_client
    draft, snapshot = eligible_snapshot(http)
    session = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"])).json()["session"]
    before = session["execution"]
    assert before["source"] == "prepared"
    assert before["control_scope_granted"] == []
    assert before["owner"]["state"] == "not_acquired"
    assert before["recording_ready"] is False and before["motion_ready"] is False
    started = http.post(f"/api/v1/sessions/{session['session_id']}/start")
    assert started.status_code == 200, started.text
    value = started.json()
    assert value["state"] == "active" and value["start_available"] is False
    receipt = value["start_receipt"]
    assert receipt["native_session_id"] == session["session_id"]
    assert receipt["config_fingerprint"] == snapshot["snapshot_id"]
    assert receipt["control_scope_granted"] == ["base", "arm", "gripper"]
    assert receipt["owner_state"] == "not_acquired"
    assert receipt["recording_ready"] is False
    assert receipt["motion_ready"] is False
    assert "recording_not_ready" in receipt["motion_blockers"]
    assert receipt["started_at_backend_monotonic_s"] == 42.5
    assert value["execution"]["source"] == "native_start"
    assert value["execution"]["owner"] == {
        "state": "not_acquired", "session_id": None,
        "lease_expires_at_backend_monotonic_s": None,
    }
    assert [attempt["result"] for attempt in value["start_attempts"]] == ["started"]
    assert http.post(f"/api/v1/sessions/{session['session_id']}/start").json()["state"] == "active"


@pytest.mark.parametrize("kwargs,key", [
    ({"safety_latched": True}, "native_safety_stop_latched"),
    ({"owners": ("other-session", None)}, "control_owner_present"),
])
def test_start_refuses_native_preconditions_without_changing_state(tmp_path, kwargs, key):
    app, fake, payloads, _ = fixture_app(tmp_path, binding=True, declare_protocols=True, **kwargs)
    with TestClient(app) as http:
        draft, snapshot = eligible_snapshot(http)
        session = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"])).json()["session"]
        refused = http.post(f"/api/v1/sessions/{session['session_id']}/start")
        assert refused.status_code == 409
        detail = refused.json()["detail"]
        assert detail["code"] == "start_preconditions_unmet"
        assert key in {item["key"] for item in detail["blocking_reasons"]}
        after = http.get(f"/api/v1/sessions/{session['session_id']}").json()
        assert after["state"] == "prepared" and after["start_receipt"] is None
        assert [attempt["result"] for attempt in after["start_attempts"]] == ["refused"]
        assert not any(path == "/api/v1/session/start" for method, path in fake.calls if method == "POST")


def test_start_refuses_when_the_runtime_identity_changed(prepared_client):
    http, _, payloads, _ = prepared_client
    draft, snapshot = eligible_snapshot(http)
    session = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"])).json()["session"]
    payloads["/api/v1/health"]["episode_id"] = "after-reset"
    payloads["/api/v1/snapshot"]["episode_id"] = "after-reset"
    refused = http.post(f"/api/v1/sessions/{session['session_id']}/start")
    assert refused.status_code == 409
    assert "runtime_identity_changed" in {item["key"] for item in refused.json()["detail"]["blocking_reasons"]}


def test_start_refuses_unverified_binding_readback(prepared_client):
    http, fake, _, _ = prepared_client
    draft, snapshot = eligible_snapshot(http)
    session = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"])).json()["session"]
    fake.bindings[session["native_binding"]["binding_id"]]["config_fingerprint"] = "0" * 64
    refused = http.post(f"/api/v1/sessions/{session['session_id']}/start")
    assert refused.status_code == 409
    assert "native_binding_unverified" in {item["key"] for item in refused.json()["detail"]["blocking_reasons"]}


def test_active_native_recording_blocks_preparation(tmp_path):
    app, _, _, _ = fixture_app(tmp_path, binding=True, declare_protocols=True, recording_status="RECORDING")
    with TestClient(app) as http:
        draft = create_draft(http)
        result = validate(http, draft)
        assert result["execution_eligible"] is False
        assert "native_recording_idle" in {reason["key"] for reason in result["blocking_reasons"]}


def test_idempotency_and_single_session_per_runtime(prepared_client):
    http, _, _, _ = prepared_client
    first_draft, first = eligible_snapshot(http)
    session = http.post("/api/v1/sessions", json=session_request(first_draft, first["validated_snapshot_id"], "shared-key")).json()["session"]
    assert session["state"] == "prepared"

    second_draft = create_draft(http)
    second = validate(http, second_draft)
    assert second["snapshot_id"] != first["snapshot_id"]
    conflict = http.post("/api/v1/sessions", json=session_request(second_draft, second["validated_snapshot_id"], "shared-key"))
    assert conflict.status_code == 409 and conflict.json()["detail"]["code"] == "idempotency_conflict"
    occupied = http.post("/api/v1/sessions", json=session_request(second_draft, second["validated_snapshot_id"], "other-key"))
    assert occupied.status_code == 409 and occupied.json()["detail"]["code"] == "session_conflict"
    assert occupied.json()["detail"]["session_id"] == session["session_id"]


def test_stale_or_unknown_snapshot_cannot_create_a_session(prepared_client):
    http, _, _, _ = prepared_client
    draft, snapshot = eligible_snapshot(http)
    missing = http.post("/api/v1/sessions", json=session_request(draft, "cs-" + "0" * 40))
    assert missing.status_code == 404 and missing.json()["detail"]["code"] == "snapshot_not_found"
    wrong = session_request(draft, snapshot["validated_snapshot_id"])
    wrong["execution_revision"] = draft["execution_revision"] + 1
    assert http.post("/api/v1/sessions", json=wrong).status_code == 409


def test_preparation_chain_never_calls_motion_reset_or_recording_endpoints(prepared_client):
    http, fake, _, _ = prepared_client
    draft, snapshot = eligible_snapshot(http)
    session = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"])).json()["session"]
    http.post(f"/api/v1/sessions/{session['session_id']}/start")
    writes = {path for method, path in fake.calls if method != "GET"}
    assert writes <= {"/api/v1/session/prepare", "/api/v1/session/start"}
    assert not [path for _, path in fake.calls if path.startswith("/api/v1/episodes") or path == "/api/v1/commands"]
    assert all(path.startswith("/api/v1/") for _, path in fake.calls)
    assert len([1 for method, _ in fake.calls if method == "POST"]) == len(fake.bodies)


def test_kinematics_profile_is_cross_checked_against_live_native(tmp_path):
    app, _, _, _ = fixture_app(tmp_path)
    with TestClient(app) as http:
        value = http.get("/api/v1/mobilecar/kinematics").json()
        assert value["schema_version"] == "unirobot-mobilecar-kinematics-1"
        assert value["profile_id"] == "landerpi.kinematics.v1"
        assert len(value["digest"]) == 64
        assert value["authority"] == "platform_reference_not_native_attested"
        assert value["profile"]["arm"]["zero_model_rad"][3] == -1.5707963267948966
        assert value["profile"]["tcp"]["orientation_xyzw"] is None
        assert value["consistency"] == {
            "joint_order_consistent": True, "user_limits_consistent": True, "tcp_mount_consistent": True,
            "camera_mount_consistent": True, "gripper_limits_consistent": True, "max_user_limit_error_rad": 0.0,
        }


def test_kinematics_mismatch_is_reported_not_corrected(tmp_path):
    app, _, _, _ = fixture_app(tmp_path, user_limit_shift=0.5)
    with TestClient(app) as http:
        value = http.get("/api/v1/mobilecar/kinematics").json()
        assert value["consistency"]["user_limits_consistent"] is False
        assert value["consistency"]["max_user_limit_error_rad"] == 0.5
        draft = create_draft(http)
        result = validate(http, draft)
        assert result["status"] == "failed"
        assert "kinematics_user_limits" in {check["key"] for check in result["checks"] if check["status"] == "failed"}


def test_execution_recipe_names_its_sources_and_protocols(tmp_path):
    app, _, _, _ = fixture_app(tmp_path)
    with TestClient(app) as http:
        recipe = http.get("/api/v1/mobilecar/execution-recipe").json()
        assert recipe["recipe_id"] == "mobilecar.g1.teleop"
        assert recipe["recipe_revision"] == 3
        assert len(recipe["recipe_fingerprint"]) == 64
        assert recipe["expected"]["interface_profile"] == "g2a-1.0"
        assert recipe["expected"]["scene_file_digest_scope"].endswith("not observable through native HTTP")
        assert len(recipe["expected"]["config_manifest_sha256"]) == 64
        assert len(recipe["expected"]["scene_manifest_sha256"]) == 64
        assert recipe["native"]["commit"] == "a5cef52d932ba41424b4bcc134539914031fda39"
        lock = recipe["dependencies"]["requirements_lock"]
        assert lock["packages"]["mujoco"] == "3.1.6"
        assert lock["source"]["path"] == "requirements.lock"
        assert lock["source"]["project"] == "mobileCar"
        assert lock["release_file"]["sha256"] == lock["source"]["sha256"]
        assert lock["verification"] == {
            "release_file_bytes_read": True,
            "source_digest_matches": True,
            "package_pins_match_file": True,
            "runtime_environment": "not checked at platform startup; native runtime_package_versions is checked at readiness",
        }
        assert recipe["required_protocols"] == {"session_binding": "m1-binding-1", "recording_begin": "m1-recording-1"}
        assert recipe["attestation"]["native_attested"] is False
        assert {source["role"] for source in recipe["sources"]} == {"preset_pin", "kinematics", "dependencies"}


def test_requirements_lock_is_read_from_the_pinned_release_copy():
    recipe = load_recipe()
    lock = recipe.body["dependencies"]["requirements_lock"]
    assert lock["source"] == {
        "project": "mobileCar",
        "commit": "a5cef52d932ba41424b4bcc134539914031fda39",
        "path": "requirements.lock",
        "sha256": "c1cad889649bcf3cdc56560c86019af1081c166b030021ad8ebf1679f1fc8439",
    }
    assert lock["release_file"]["sha256"] == lock["source"]["sha256"]
    assert lock["release_file"]["size_bytes"] > 0
    assert lock["verification"]["release_file_bytes_read"] is True
    assert lock["verification"]["package_pins_match_file"] is True
    assert lock["packages"]["mujoco"] == "3.1.6"


def _recipe_root(tmp_path: Path) -> Path:
    root = tmp_path / "backend"
    shutil.copytree(BACKEND_ROOT / "config", root / "config")
    return root


def test_recipe_rejects_a_missing_lock_file(tmp_path):
    root = _recipe_root(tmp_path)
    (root / "config" / "pins" / "mobilecar-a5cef52" / "requirements.lock").unlink()
    with pytest.raises(RecipeError, match="missing"):
        load_recipe(root / "config" / "mobilecar-g1-recipe-v2.json", root=root)


def test_recipe_rejects_a_tampered_lock_file(tmp_path):
    root = _recipe_root(tmp_path)
    (root / "config" / "pins" / "mobilecar-a5cef52" / "requirements.lock").write_text(
        "mujoco==3.1.6\n", encoding="utf-8"
    )
    with pytest.raises(RecipeError, match="digest mismatch"):
        load_recipe(root / "config" / "mobilecar-g1-recipe-v2.json", root=root)


def test_recipe_rejects_declared_packages_that_differ_from_the_lock(tmp_path):
    root = _recipe_root(tmp_path)
    recipe_path = root / "config" / "mobilecar-g1-recipe-v2.json"
    raw = json.loads(recipe_path.read_text(encoding="utf-8"))
    raw["dependencies"]["requirements_lock"]["packages"]["mujoco"] = "9.9.9"
    recipe_path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(RecipeError, match="package pins differ"):
        load_recipe(recipe_path, root=root)


@pytest.mark.parametrize("field,value,key", [
    ("config_manifest_sha256", "0" * 64, "deployed_config_attestation"),
    ("scene_manifest_sha256", "0" * 64, "scene_manifest_attestation"),
    ("runtime_python_version", "3.14.0", "runtime_python_version"),
])
def test_readiness_compares_native_attestations_with_the_pinned_values(tmp_path, field, value, key):
    app, _, payloads, _ = fixture_app(tmp_path, declare_protocols=True)
    payloads["/api/v1/capabilities"][field] = value
    with TestClient(app) as http:
        draft = create_draft(http)
        result = validate(http, draft)
        assert result["execution_eligible"] is False
        failed = {check["key"] for check in result["checks"] if check["status"] == "failed"}
        assert key in failed
        assert result["validated_snapshot_id"] is None


def test_readiness_comparses_runtime_package_versions(tmp_path):
    app, _, payloads, _ = fixture_app(tmp_path, declare_protocols=True)
    payloads["/api/v1/capabilities"]["runtime_package_versions"]["mujoco"] = "3.2.0"
    with TestClient(app) as http:
        draft = create_draft(http)
        result = validate(http, draft)
        assert result["execution_eligible"] is False
        assert "runtime_package_versions" in {
            check["key"] for check in result["checks"] if check["status"] == "failed"
        }


def test_attestations_pass_when_all_same_scope_values_match(tmp_path):
    app, _, _, _ = fixture_app(tmp_path, declare_protocols=True)
    with TestClient(app) as http:
        draft = create_draft(http)
        result = validate(http, draft)
        assert result["execution_eligible"] is True
        passed = {check["key"] for check in result["checks"] if check["status"] == "passed"}
        assert {
            "deployed_config_attestation", "scene_manifest_attestation",
            "runtime_python_version", "runtime_package_versions",
        } <= passed


def test_recording_begin_is_separate_idempotent_and_never_resets(prepared_client):
    http, fake, _, _ = prepared_client
    draft, snapshot = eligible_snapshot(http)
    session = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"])).json()["session"]
    assert session["execution"]["recording_ready"] is False
    assert http.post(f"/api/v1/sessions/{session['session_id']}/start").status_code == 200
    begun = http.post(
        f"/api/v1/sessions/{session['session_id']}/recording/begin",
        json={"operator_id": "fixture-human", "view_source": "third_person_3d"},
    )
    assert begun.status_code == 201, begun.text
    value = begun.json()
    assert value["replayed"] is False
    active = value["session"]
    receipt = active["recording_begin_receipt"]
    assert receipt["recording_status"] == "RECORDING"
    assert receipt["command_capture_ready"] is True
    assert receipt["durable_start_records"] is True
    assert receipt["recording_start_event_seq"] == 1
    assert receipt["initial_snapshot_sha256"] == "d" * 64
    assert active["execution"]["recording_ready"] is True
    assert active["execution"]["motion_ready"] is True
    assert active["execution"]["owner"]["state"] == "not_acquired"
    assert [attempt["result"] for attempt in active["recording_begin_attempts"]] == ["begun"]

    native_calls = len(fake.calls)
    repeated = http.post(
        f"/api/v1/sessions/{session['session_id']}/recording/begin",
        json={"operator_id": "fixture-human", "view_source": "third_person_3d"},
    )
    assert repeated.status_code == 200
    assert repeated.json()["replayed"] is True
    assert repeated.json()["session"]["recording_begin_receipt"]["recording_segment_id"] == receipt["recording_segment_id"]
    assert len(fake.calls) == native_calls
    writes = {path for method, path in fake.calls if method != "GET"}
    assert "/api/v1/episodes/start" not in writes
    assert "/api/v1/episodes/stop" not in writes
    assert "/api/v1/commands" not in writes


def test_recording_begin_requires_an_active_session(prepared_client):
    http, fake, _, _ = prepared_client
    draft, snapshot = eligible_snapshot(http)
    session = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"])).json()["session"]
    response = http.post(
        f"/api/v1/sessions/{session['session_id']}/recording/begin",
        json={"operator_id": "fixture-human"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "session_not_active"
    assert not any(path == "/api/v1/recording/begin" for _, path in fake.calls)


def test_recording_begin_requires_the_declared_native_protocol(prepared_client):
    http, _, payloads, _ = prepared_client
    draft, snapshot = eligible_snapshot(http)
    session = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"])).json()["session"]
    http.post(f"/api/v1/sessions/{session['session_id']}/start")
    payloads["/api/v1/capabilities"]["recording_begin_protocol"] = None
    response = http.post(
        f"/api/v1/sessions/{session['session_id']}/recording/begin",
        json={"operator_id": "fixture-human"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "recording_begin_unsupported"


def test_recording_begin_transport_failure_is_recorded_and_retryable(prepared_client):
    http, fake, _, _ = prepared_client
    draft, snapshot = eligible_snapshot(http)
    session = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"])).json()["session"]
    http.post(f"/api/v1/sessions/{session['session_id']}/start")
    fake.fail_path = "/api/v1/recording/begin"
    failed = http.post(
        f"/api/v1/sessions/{session['session_id']}/recording/begin",
        json={"operator_id": "fixture-human"},
    )
    assert failed.status_code == 503
    assert failed.json()["detail"]["code"] == "native_recording_begin_failed"
    after = http.get(f"/api/v1/sessions/{session['session_id']}").json()
    assert after["state"] == "active"
    assert after["execution"]["recording_ready"] is False
    assert after["recording_begin_receipt"] is None
    assert [attempt["result"] for attempt in after["recording_begin_attempts"]] == ["failed"]
    fake.fail_path = None
    retried = http.post(
        f"/api/v1/sessions/{session['session_id']}/recording/begin",
        json={"operator_id": "fixture-human"},
    )
    assert retried.status_code == 201
    assert retried.json()["session"]["execution"]["recording_ready"] is True


def test_recording_begin_refuses_a_tampered_binding_readback(prepared_client):
    http, fake, _, _ = prepared_client
    draft, snapshot = eligible_snapshot(http)
    session = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"])).json()["session"]
    http.post(f"/api/v1/sessions/{session['session_id']}/start")
    fake.bindings[session["native_binding"]["binding_id"]]["config_fingerprint"] = "0" * 64
    response = http.post(
        f"/api/v1/sessions/{session['session_id']}/recording/begin",
        json={"operator_id": "fixture-human"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "native_recording_begin_failed"
    after = http.get(f"/api/v1/sessions/{session['session_id']}").json()
    assert after["execution"]["recording_ready"] is False
    assert [attempt["result"] for attempt in after["recording_begin_attempts"]] == ["failed"]


def test_start_recovers_when_native_already_started_the_binding(prepared_client):
    http, fake, _, _ = prepared_client
    draft, snapshot = eligible_snapshot(http)
    session = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"])).json()["session"]
    fake.bindings[session["native_binding"]["binding_id"]]["state"] = "started"
    started = http.post(f"/api/v1/sessions/{session['session_id']}/start")
    assert started.status_code == 200, started.text
    assert started.json()["state"] == "active"


def test_missing_runtime_environment_attestation_is_unsupported(tmp_path):
    app, _, payloads, _ = fixture_app(tmp_path, declare_protocols=True)
    capabilities = payloads["/api/v1/capabilities"]
    capabilities.pop("runtime_python_version")
    capabilities.pop("runtime_package_versions")
    with TestClient(app) as http:
        draft = create_draft(http)
        result = validate(http, draft)
        assert result["execution_eligible"] is False
        statuses = {check["key"]: check["status"] for check in result["checks"]}
        assert statuses["runtime_python_version"] == "unsupported"
        assert statuses["runtime_package_versions"] == "unsupported"
        assert {
            "runtime_python_version", "runtime_package_versions"
        } <= {reason["key"] for reason in result["blocking_reasons"]}
