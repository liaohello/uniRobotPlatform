"""Fixed-preset persistence and trust boundaries; native responses are synthetic."""

import copy

import pytest
from fastapi.testclient import TestClient

from native_fixtures import create_draft, fixture_app, session_request, validate
from unirobot.drafts import DraftStore, SaveDraft


@pytest.fixture()
def draft_app(tmp_path):
    app, fake, payloads, integration = fixture_app(tmp_path)
    with TestClient(app) as http:
        yield app, http, fake


def validation_request(draft):
    return {"execution_revision": draft["execution_revision"], "fingerprint": draft["fingerprint"]}


def test_create_read_and_reload_persistent_store_without_native_calls(draft_app):
    app, http, fake = draft_app
    draft = create_draft(http)
    store = DraftStore(app.state.drafts.path, app.state.mobilecar_integration, recipe=app.state.recipe)
    assert store.get(draft["draft_id"]) == draft
    assert http.get(f"/api/v1/experiment-drafts/{draft['draft_id']}").json() == draft
    assert http.get("/api/v1/experiment-drafts").json() == [draft]
    assert draft["validation"]["status"] == "unvalidated"
    assert draft["preset"]["recipe"]["editable_initial_state_fields"] == []
    assert draft["recipe_fingerprint"] == app.state.recipe.fingerprint
    assert fake.calls == []


def test_metadata_save_changes_only_draft_revision_and_keeps_validation(draft_app):
    _, http, fake = draft_app
    draft = create_draft(http)
    path = f"/api/v1/experiment-drafts/{draft['draft_id']}"
    validated = http.post(path + "/validate", json=validation_request(draft)).json()
    saved = http.put(path, json={"base_revision": 1, "name": "Renamed", "description": "new metadata"}).json()
    assert saved["draft_revision"] == 2
    assert saved["execution_revision"] == 1
    assert saved["fingerprint"] == draft["fingerprint"]
    assert saved["validation"] == validated["validation"]
    repeated = http.put(path, json={"base_revision": 2, "name": "Renamed", "description": "new metadata"}).json()
    assert repeated["draft_revision"] == 2
    assert all(method == "GET" for method, _ in fake.calls)


def test_stale_host_save_is_rejected_without_overwriting(draft_app):
    app, http, _ = draft_app
    draft = create_draft(http)
    path = f"/api/v1/experiment-drafts/{draft['draft_id']}"
    other_host = DraftStore(app.state.drafts.path, app.state.mobilecar_integration, recipe=app.state.recipe)
    other_host.save(draft["draft_id"], SaveDraft(base_revision=1, name="Other host", description="accepted"))
    rejected = http.put(path, json={"base_revision": 1, "name": "Old host", "description": "outdated"})
    assert rejected.status_code == 409
    assert http.get(path).json()["name"] == "Other host"


@pytest.mark.parametrize("extra", [{"initial_state": {"joint1": 0}}, {"seed": 12}, {"preset_id": "arbitrary"}])
def test_unknown_or_unsupported_execution_edits_are_rejected(draft_app, extra):
    _, http, _ = draft_app
    assert http.post("/api/v1/experiment-drafts", json={"name": "fixture", **extra}).status_code == 422
    draft = create_draft(http)
    path = f"/api/v1/experiment-drafts/{draft['draft_id']}"
    assert http.put(path, json={"base_revision": 1, "name": "fixture", **extra}).status_code == 422
    assert http.get(path).json()["draft_revision"] == 1


def test_configuration_can_pass_while_execution_stays_ineligible(draft_app):
    _, http, _ = draft_app
    draft = create_draft(http)
    result = validate(http, draft)
    assert result["status"] == "passed"
    assert result["execution_eligible"] is False
    assert result["validated_snapshot_id"] is None
    reasons = {reason["key"] for reason in result["blocking_reasons"]}
    assert {"session_binding_protocol", "recording_begin_protocol"} <= reasons
    rejected = http.post("/api/v1/sessions", json=session_request(draft, result["snapshot_id"]))
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "validation_incomplete"
    assert {item["key"] for item in rejected.json()["detail"]["blocking_reasons"]} >= {"session_binding_protocol"}


def test_profile_mismatch_fails_configuration_validation(tmp_path):
    app, _, _, _ = fixture_app(tmp_path, interface_profile="g4a1-1.0")
    with TestClient(app) as http:
        draft = create_draft(http)
        result = validate(http, draft)
        assert result["status"] == "failed"
        assert result["execution_eligible"] is False
        failed = {check["key"] for check in result["checks"] if check["status"] == "failed"}
        assert "interface_profile" in failed


def test_dependency_change_and_revert_does_not_revive_validation(draft_app):
    app, http, _ = draft_app
    draft = create_draft(http)
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


def test_recipe_change_marks_unvalidated_draft_stale(draft_app):
    app, http, _ = draft_app
    draft = create_draft(http)
    original = app.state.recipe.fingerprint
    app.state.recipe.fingerprint = "f" * 64
    stale = http.get(f"/api/v1/experiment-drafts/{draft['draft_id']}").json()
    assert stale["validation"]["status"] == "stale"
    app.state.recipe.fingerprint = original


def test_metadata_saved_during_validation_is_not_overwritten(draft_app):
    app, http, _ = draft_app
    draft = create_draft(http)
    original_observe = app.state.preparation.validator.observe

    def delayed_observe():
        app.state.drafts.save(draft["draft_id"], SaveDraft(base_revision=1, name="Saved during check", description="kept"))
        return original_observe()

    app.state.preparation.validator.observe = delayed_observe
    response = http.post(f"/api/v1/experiment-drafts/{draft['draft_id']}/validate", json=validation_request(draft))
    assert response.status_code == 200
    assert response.json()["name"] == "Saved during check"
    assert response.json()["draft_revision"] == 2


def test_dependencies_changed_during_check_cannot_accept_late_result(draft_app):
    app, http, _ = draft_app
    draft = create_draft(http)
    original_observe = app.state.preparation.validator.observe

    def changed_observe():
        app.state.mobilecar_integration.pin["manifest_sha256"] = "1" * 64
        return original_observe()

    app.state.preparation.validator.observe = changed_observe
    path = f"/api/v1/experiment-drafts/{draft['draft_id']}"
    assert http.post(path + "/validate", json=validation_request(draft)).status_code == 409
    assert http.get(path).json()["validation"]["result"] is None


def test_missing_draft_and_invalid_execution_revision_are_diagnostic(draft_app):
    _, http, fake = draft_app
    assert http.get("/api/v1/experiment-drafts/missing").status_code == 404
    draft = create_draft(http)
    spec = copy.deepcopy(validation_request(draft))
    spec["execution_revision"] = 2
    assert http.post(f"/api/v1/experiment-drafts/{draft['draft_id']}/validate", json=spec).status_code == 409
    assert fake.calls == []
