"""Fixed-preset persistence and trust boundaries; native responses are synthetic."""

import copy

import pytest
from fastapi.testclient import TestClient

from unirobot.api import create_app
from unirobot.drafts import DraftStore, SaveDraft


@pytest.fixture()
def draft_app(tmp_path):
    app = create_app(draft_db_path=tmp_path / "drafts.sqlite3")
    calls = []

    def check():
        calls.append("read_only_preflight")
        return {"checked_at": "2026-10-23T00:00:00Z", "checks": [
            {"key": "prepared_session_and_start", "status": "unsupported", "detail": "synthetic native binding gap"}
        ]}

    app.state.mobilecar_integration.check = check
    with TestClient(app) as http:
        yield app, http, calls


def create(http):
    response = http.post("/api/v1/experiment-drafts", json={"name": "Fixture", "description": "synthetic"})
    assert response.status_code == 201
    return response.json()


def validation_request(draft):
    return {"execution_revision": draft["execution_revision"], "fingerprint": draft["fingerprint"]}


def test_create_read_and_reload_persistent_store_without_native_calls(draft_app):
    app, http, calls = draft_app
    draft = create(http)
    store = DraftStore(app.state.drafts.path, app.state.mobilecar_integration)
    assert store.get(draft["draft_id"]) == draft
    assert http.get(f"/api/v1/experiment-drafts/{draft['draft_id']}").json() == draft
    assert http.get("/api/v1/experiment-drafts").json() == [draft]
    assert draft["validation"]["status"] == "unvalidated"
    assert draft["preset"]["recipe"]["editable_initial_state_fields"] == []
    assert calls == []


def test_metadata_save_changes_only_draft_revision_and_keeps_validation(draft_app):
    _, http, calls = draft_app
    draft = create(http)
    path = f"/api/v1/experiment-drafts/{draft['draft_id']}"
    validated = http.post(path + "/validate", json=validation_request(draft)).json()
    saved = http.put(path, json={"base_revision": 1, "name": "Renamed", "description": "new metadata"}).json()
    assert saved["draft_revision"] == 2
    assert saved["execution_revision"] == 1
    assert saved["fingerprint"] == draft["fingerprint"]
    assert saved["validation"] == validated["validation"]
    assert calls == ["read_only_preflight"]
    repeated = http.put(path, json={"base_revision": 2, "name": "Renamed", "description": "new metadata"}).json()
    assert repeated["draft_revision"] == 2


def test_stale_host_save_is_rejected_without_overwriting(draft_app):
    app, http, calls = draft_app
    draft = create(http)
    path = f"/api/v1/experiment-drafts/{draft['draft_id']}"
    other_host = DraftStore(app.state.drafts.path, app.state.mobilecar_integration)
    other_host.save(draft["draft_id"], SaveDraft(base_revision=1, name="Other host", description="accepted"))
    rejected = http.put(path, json={"base_revision": 1, "name": "Old host", "description": "outdated"})
    assert rejected.status_code == 409
    assert http.get(path).json()["name"] == "Other host"
    assert calls == []


@pytest.mark.parametrize("extra", [{"initial_state": {"joint1": 0}}, {"seed": 12}, {"preset_id": "arbitrary"}])
def test_unknown_or_unsupported_execution_edits_are_rejected(draft_app, extra):
    _, http, calls = draft_app
    assert http.post("/api/v1/experiment-drafts", json={"name": "fixture", **extra}).status_code == 422
    draft = create(http)
    path = f"/api/v1/experiment-drafts/{draft['draft_id']}"
    assert http.put(path, json={"base_revision": 1, "name": "fixture", **extra}).status_code == 422
    assert http.get(path).json()["draft_revision"] == 1
    assert calls == []


def test_validation_cannot_issue_snapshot_or_create_session(draft_app):
    _, http, calls = draft_app
    draft = create(http)
    response = http.post(f"/api/v1/experiment-drafts/{draft['draft_id']}/validate", json=validation_request(draft))
    assert response.status_code == 200
    result = response.json()["validation"]
    assert result["status"] == "failed"
    assert result["result"]["validated_snapshot_id"] is None
    assert result["result"]["checks"][0]["status"] == "unsupported"
    rejected = http.post("/api/v1/sessions", json={**validation_request(draft),
        "validated_snapshot_id": "forged-snapshot", "idempotency_key": "synthetic-key"})
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "unsupported"
    assert calls == ["read_only_preflight"]


def test_dependency_change_and_revert_does_not_revive_validation(draft_app):
    app, http, calls = draft_app
    draft = create(http)
    path = f"/api/v1/experiment-drafts/{draft['draft_id']}"
    http.post(path + "/validate", json=validation_request(draft))
    old_digest = app.state.mobilecar_integration.pin["manifest_sha256"]
    app.state.mobilecar_integration.pin["manifest_sha256"] = "0" * 64
    stale = http.get(path).json()
    assert stale["validation"]["status"] == "stale"
    assert stale["validation"]["result"] is not None
    app.state.mobilecar_integration.pin["manifest_sha256"] = old_digest
    assert http.get(path).json()["validation"]["status"] == "stale"
    assert http.post(path + "/validate", json=validation_request(draft)).status_code == 409
    assert calls == ["read_only_preflight"]


def test_metadata_saved_during_validation_is_not_overwritten(draft_app):
    app, http, _ = draft_app
    draft = create(http)
    original_check = app.state.mobilecar_integration.check

    def delayed_check():
        app.state.drafts.save(draft["draft_id"], SaveDraft(base_revision=1, name="Saved during check", description="kept"))
        return original_check()

    app.state.mobilecar_integration.check = delayed_check
    response = http.post(f"/api/v1/experiment-drafts/{draft['draft_id']}/validate", json=validation_request(draft))
    assert response.status_code == 200
    assert response.json()["name"] == "Saved during check"
    assert response.json()["draft_revision"] == 2


def test_dependencies_changed_during_check_cannot_accept_late_result(draft_app):
    app, http, _ = draft_app
    draft = create(http)
    original_check = app.state.mobilecar_integration.check

    def changed_check():
        app.state.mobilecar_integration.pin["manifest_sha256"] = "1" * 64
        return original_check()

    app.state.mobilecar_integration.check = changed_check
    path = f"/api/v1/experiment-drafts/{draft['draft_id']}"
    assert http.post(path + "/validate", json=validation_request(draft)).status_code == 409
    assert http.get(path).json()["validation"]["result"] is None


def test_missing_draft_and_invalid_execution_revision_are_diagnostic(draft_app):
    _, http, calls = draft_app
    assert http.get("/api/v1/experiment-drafts/missing").status_code == 404
    draft = create(http)
    spec = copy.deepcopy(validation_request(draft))
    spec["execution_revision"] = 2
    assert http.post(f"/api/v1/experiment-drafts/{draft['draft_id']}/validate", json=spec).status_code == 409
    assert calls == []
