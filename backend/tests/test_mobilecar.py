"""Synthetic HTTP fixtures for read-only integration; not product acceptance."""

import copy
import io
import json
import urllib.error
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from unirobot.api import create_app
from unirobot.contracts import AdapterConfig
from unirobot.mobilecar import MobileCarIntegration, READ_PATHS


class FakeOpener:
    def __init__(self, payloads, fail_path=None):
        self.payloads = payloads
        self.fail_path = fail_path
        self.calls = []

    def open(self, request, *, timeout):
        path = urlsplit(request.full_url).path
        self.calls.append((request.get_method(), path))
        if path == self.fail_path:
            raise urllib.error.URLError("synthetic connection failure")
        payload = self.payloads[path]
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return io.BytesIO(body)


@pytest.fixture()
def integration():
    client = MobileCarIntegration(
        AdapterConfig(id="mobilecar", title="fixture", project_root="unused", base_url="http://fixture.invalid")
    )
    expected = client.pin["expected"]
    identity = {"run_id": "synthetic-run", "backend_generation": 1, "episode_id": "synthetic-episode"}
    scene = {key: expected[key] for key in ("contract_version", "model_id", "model_sha256", "scene_id")}
    payloads = {
        READ_PATHS[0]: {**identity, "status": "ok", "recording_required_for_motion": True,
                        "interface_profile": expected["interface_profile"]},
        READ_PATHS[1]: {**scene, "backend_kind": "mujoco", "supported_commands": expected["commands"],
                        "sensor_streams": expected["sensor_streams"]},
        READ_PATHS[2]: scene,
        READ_PATHS[3]: {**identity, "contract_version": "mobilecar-1.0", "base_owner_session_id": None,
                        "arm_owner_session_id": None, "recording": {"status": "IDLE",
                        "command_capture_ready": False, "recording_segment_id": None}},
    }
    opener = FakeOpener(copy.deepcopy(payloads))
    client._opener = opener
    return client, opener


def test_matching_native_reads_never_claim_session_ready_or_send_commands(integration):
    client, opener = integration
    before = copy.deepcopy(opener.payloads)
    report = client.check()
    assert report["read_contract_compatible"] is True
    assert report["session_ready"] is False
    assert report["read_only"] is True
    assert report["runtime_identity"]["run_id"] == "synthetic-run"
    assert opener.calls == [("GET", path) for path in READ_PATHS]
    assert opener.payloads == before
    checks = {item["key"]: item for item in report["checks"]}
    assert checks["prepared_session_and_start"]["status"] == "unsupported"
    assert checks["deployed_source_and_config"]["status"] == "not_checked"


@pytest.mark.parametrize("path,field,value", [
    (READ_PATHS[3], "episode_id", "reset-during-read"),
    (READ_PATHS[3], "backend_generation", 2),
    (READ_PATHS[2], "model_sha256", "0" * 64),
    (READ_PATHS[2], "scene_id", "other-scene"),
    (READ_PATHS[1], "backend_kind", "mock"),
    (READ_PATHS[0], "recording_required_for_motion", False),
    (READ_PATHS[1], "supported_commands", []),
    (READ_PATHS[1], "sensor_streams", []),
])
def test_incompatible_recipe_or_reset_is_visible(integration, path, field, value):
    client, opener = integration
    opener.payloads[path][field] = value
    report = client.check()
    assert report["read_contract_compatible"] is False
    assert report["session_ready"] is False
    assert any(check["status"] == "failed" for check in report["checks"])
    assert all(method == "GET" for method, _ in opener.calls)


@pytest.mark.parametrize("payload", [b"<html>wrong service</html>", b"[]", b'{"status":"ok"}'])
def test_invalid_native_response_stops_reads_and_does_not_echo_body(integration, payload):
    client, opener = integration
    opener.payloads[READ_PATHS[0]] = payload
    report = client.check()
    assert report["transport"] == "incompatible"
    assert report["read_contract_compatible"] is False
    assert opener.calls == [("GET", READ_PATHS[0])]
    assert "<html>" not in json.dumps(report)
    assert [c["status"] for c in report["checks"][:4]] == ["failed", "not_checked", "not_checked", "not_checked"]


def test_offline_service_has_no_retry_or_mutation(integration):
    client, opener = integration
    opener.fail_path = READ_PATHS[1]
    report = client.check()
    assert report["transport"] == "offline"
    assert report["runtime_identity"] is None
    assert opener.calls == [("GET", READ_PATHS[0]), ("GET", READ_PATHS[1])]


def test_unconfigured_adapter_does_not_use_default_loopback():
    client = MobileCarIntegration(None)
    report = client.check()
    assert report["transport"] == "not_configured"
    assert report["session_ready"] is False


def test_gateway_route_and_static_panel(integration):
    integration_client, opener = integration
    app = create_app()
    app.state.mobilecar_integration = integration_client
    with TestClient(app) as http:
        response = http.get("/api/v1/mobilecar/preflight")
        assert response.status_code == 200
        assert response.json()["session_ready"] is False
        assert http.get("/mobilecar/").status_code == 200
        assert http.get("/mobilecar/panel.js").status_code == 200
    assert opener.calls == [("GET", path) for path in READ_PATHS]
