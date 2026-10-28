"""Identity-bound robot STOP and reliable recording end against a synthetic native.

The fixtures are test-only: the production recipe deliberately does not declare
m1-stop-1 or m1-end-1, so a production Session must be refused as unsupported.
Nothing here proves a real robot stopped; the live physical check is separate.
"""

import pytest
from fastapi.testclient import TestClient

from native_fixtures import RECORDING_END_PATH, SESSION_STOP_PATH, create_draft, fixture_app, session_request, validate

STOP_BODY = {"request_id": "stop-1", "reason": "OPERATOR_STOP"}
END_BODY = {"request_id": "end-1", "reason": "OPERATOR_FINISHED"}


@pytest.fixture()
def client(tmp_path):
    app, fake, payloads, _ = fixture_app(tmp_path, binding=True, declare_protocols=True, stop_end=True)
    with TestClient(app) as http:
        yield http, fake, payloads


@pytest.fixture()
def plain_client(tmp_path):
    app, fake, payloads, _ = fixture_app(tmp_path, binding=True, declare_protocols=True)
    with TestClient(app) as http:
        yield http, fake, payloads


def started_session(http):
    draft = create_draft(http)
    snapshot = validate(http, draft)
    session = http.post("/api/v1/sessions", json=session_request(draft, snapshot["validated_snapshot_id"])).json()["session"]
    assert http.post(f"/api/v1/sessions/{session['session_id']}/start").status_code == 200
    return session


def begin(http, session_id: str) -> dict:
    return http.post(f"/api/v1/sessions/{session_id}/recording/begin",
                     json={"operator_id": "fixture-human"}).json()["session"]


def begun_session(http):
    session = started_session(http)
    return begin(http, session["session_id"])


def writes(fake):
    return [path for method, path in fake.calls if method != "GET"]


def test_stop_and_end_are_refused_until_the_native_protocol_is_declared(plain_client):
    http, fake, _ = plain_client
    session = started_session(http)
    session_id = session["session_id"]
    refused = http.post(f"/api/v1/sessions/{session_id}/stop", json=STOP_BODY)
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"]["code"] == "stop_unsupported"
    assert refused.json()["detail"]["required_protocol"] is None
    assert refused.json()["detail"]["declared"] is None
    not_declared = http.post(f"/api/v1/sessions/{session_id}/recording/end", json=END_BODY)
    assert not_declared.json()["detail"]["code"] == "recording_end_unsupported"
    assert SESSION_STOP_PATH not in writes(fake)
    assert RECORDING_END_PATH not in writes(fake)
    current = http.get(f"/api/v1/sessions/{session_id}").json()["current"]
    assert current["stop_available"] is False and current["recording_end_available"] is False


def test_the_production_recipe_does_not_claim_stop_or_end_support():
    from unirobot.recipe import load_recipe

    protocols = load_recipe().required_protocols
    assert "session_stop" not in protocols and "recording_end" not in protocols


def test_session_stop_reports_dispatch_and_parking_separately_and_keeps_recording(client):
    http, fake, _ = client
    session = begun_session(http)
    session_id = session["session_id"]
    segment = session["recording_begin_receipt"]["recording_segment_id"]
    stopped = http.post(f"/api/v1/sessions/{session_id}/stop", json=STOP_BODY)
    assert stopped.status_code == 201, stopped.text
    value = stopped.json()
    receipt = value["session"]["stop_receipt"]
    assert value["replayed"] is False
    assert receipt["accepted"] is True and receipt["code"] == "stopped"
    assert receipt["protocol"] == "m1-stop-1"
    assert receipt["dispatch"]["dispatched"] is True
    assert receipt["dispatch"]["status"] == "DISPATCHED"
    assert receipt["parking"]["confirmed"] is True
    assert receipt["parking"]["base_stopped"] is True
    # The gripper has no feedback, so full coverage is never claimed.
    assert receipt["parking"]["scope_coverage"]["gripper"] == "not_observed"
    assert receipt["parking"]["coverage_complete"] is False
    assert receipt["parking"]["observed_confirmed"] is True
    assert receipt["recording_touched"] is False and receipt["motion_restored"] is False
    assert receipt["recording_status"] == "RECORDING"
    assert receipt["recording_segment_id"] == segment
    assert [attempt["result"] for attempt in value["session"]["stop_attempts"]] == ["stopped"]

    body = [payload for path, payload in fake.bodies if path == SESSION_STOP_PATH][-1]
    assert body["binding_id"] == session["native_binding"]["binding_id"]
    assert body["session_id"] == session_id
    assert body["episode_id"] == session["native_identity"]["episode_id"]
    assert writes(fake).count(SESSION_STOP_PATH) == 1

    replay = http.post(f"/api/v1/sessions/{session_id}/stop", json=STOP_BODY)
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert writes(fake).count(SESSION_STOP_PATH) == 1


def test_stop_needs_no_recording_no_owner_and_no_motion_readiness(client):
    http, _, _ = client
    session = started_session(http)
    assert session["execution"]["recording_ready"] is False
    stopped = http.post(f"/api/v1/sessions/{session['session_id']}/stop",
                        json={"request_id": "stop-idle"}).json()["session"]["stop_receipt"]
    assert stopped["accepted"] is True
    assert stopped["recording_status"] == "IDLE"
    assert stopped["owner_cleared_after_stop"] is True


def test_unconfirmed_parking_and_partial_coverage_stay_visible(client):
    http, fake, _ = client
    session = begun_session(http)
    fake.parking_confirmed = False
    unconfirmed = http.post(f"/api/v1/sessions/{session['session_id']}/stop",
                            json={"request_id": "stop-no-parking"}).json()["session"]["stop_receipt"]
    assert unconfirmed["accepted"] is False
    assert unconfirmed["code"] == "stop_dispatched_parking_unconfirmed"
    assert unconfirmed["dispatch"]["dispatched"] is True
    assert unconfirmed["parking"]["confirmed"] is False
    fake.parking_confirmed = True
    fake.arm_observed = "unconfirmed"
    partial = http.post(f"/api/v1/sessions/{session['session_id']}/stop",
                        json={"request_id": "stop-partial"}).json()["session"]["stop_receipt"]
    assert partial["accepted"] is True and partial["code"] == "stopped_partial_coverage"
    assert partial["parking"]["observed_confirmed"] is False


def test_refused_dispatch_and_a_lost_connection_are_not_reported_as_stopped(client):
    http, fake, _ = client
    session = begun_session(http)
    fake.dispatch_accepted = False
    refused = http.post(f"/api/v1/sessions/{session['session_id']}/stop",
                        json={"request_id": "stop-refused"}).json()["session"]["stop_receipt"]
    assert refused["accepted"] is False and refused["code"] == "stop_dispatch_failed"
    fake.dispatch_accepted = True

    fake.fail_path = SESSION_STOP_PATH
    offline = http.post(f"/api/v1/sessions/{session['session_id']}/stop", json={"request_id": "stop-offline"})
    assert offline.status_code == 504, offline.text
    assert offline.json()["detail"]["code"] == "native_stop_failed"
    stored = http.get(f"/api/v1/sessions/{session['session_id']}").json()
    assert stored["stop_receipt"]["code"] == "stop_dispatch_failed"
    assert [attempt["result"] for attempt in stored["stop_attempts"]] == ["refused", "result_unknown"]


def test_recording_end_binds_the_segment_this_session_began_and_closes_the_session(client):
    http, fake, _ = client
    session = begun_session(http)
    session_id = session["session_id"]
    segment = session["recording_begin_receipt"]["recording_segment_id"]
    ended = http.post(f"/api/v1/sessions/{session_id}/recording/end", json=END_BODY)
    assert ended.status_code == 201, ended.text
    closed = ended.json()["session"]
    receipt = closed["recording_end_receipt"]
    body = [payload for path, payload in fake.bodies if path == RECORDING_END_PATH][-1]
    assert body["recording_segment_id"] == segment
    assert body["binding_id"] == session["native_binding"]["binding_id"]
    assert receipt["accepted"] is True and receipt["code"] == "ended"
    assert receipt["protocol"] == "m1-end-1"
    assert receipt["integrity"] == "complete"
    assert receipt["parking"]["confirmed"] is True
    assert receipt["drain"]["completed"] is True
    assert receipt["finalize"]["complete_tail"] is True
    assert receipt["finalize"]["audit_status"] == "COMPLETE"
    assert receipt["finalize"]["episode_complete_sha256"] == "a" * 64
    assert receipt["reset_issued"] is False and receipt["safety_cleared"] is False
    assert receipt["owner_acquired"] is False
    assert closed["state"] == "closed" and closed["closed_at"] is not None
    assert closed["execution"]["recording_ready"] is False
    assert closed["execution"]["motion_ready"] is False
    assert "recording_closed" in closed["execution"]["motion_blockers"]
    forbidden = {"/api/v1/episodes/start", "/api/v1/episodes/stop", "/api/v1/commands",
                 "/api/v1/session/release"}
    assert not (set(writes(fake)) & forbidden)

    current = http.get(f"/api/v1/sessions/{session_id}").json()["current"]
    assert current["recording_end_available"] is False
    assert current["last_end_code"] == "ended"
    assert current["recording_integrity"] == "complete"


def test_end_is_refused_before_a_segment_exists_and_after_the_session_is_closed(client):
    http, fake, _ = client
    session = started_session(http)
    session_id = session["session_id"]
    early = http.post(f"/api/v1/sessions/{session_id}/recording/end", json=END_BODY)
    assert early.status_code == 409
    assert early.json()["detail"]["code"] == "recording_not_begun"
    assert RECORDING_END_PATH not in writes(fake)

    begin(http, session_id)
    ended = http.post(f"/api/v1/sessions/{session_id}/recording/end", json=END_BODY)
    assert ended.status_code == 201, ended.text
    again = http.post(f"/api/v1/sessions/{session_id}/recording/end", json={"request_id": "end-2"})
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "session_not_stoppable"
    assert writes(fake).count(RECORDING_END_PATH) == 1


def test_finalize_failure_keeps_the_session_open_and_is_diagnosable(client):
    http, fake, _ = client
    session = begun_session(http)
    fake.end_integrity = "finalize_failed_missing_tail"
    broken = http.post(f"/api/v1/sessions/{session['session_id']}/recording/end", json=END_BODY)
    assert broken.status_code == 201, broken.text
    receipt = broken.json()["session"]["recording_end_receipt"]
    assert receipt["accepted"] is False and receipt["code"] == "end_finalize_failed"
    assert receipt["integrity"] == "finalize_failed_missing_tail"
    assert receipt["finalize"]["completed"] is False
    assert receipt["finalize"]["complete_tail"] is False
    assert "injected finalize failure" in receipt["finalize"]["error"]
    assert broken.json()["session"]["state"] == "active"

    replay = http.post(f"/api/v1/sessions/{session['session_id']}/recording/end", json=END_BODY)
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    fake.end_integrity = "complete"
    retried = http.post(f"/api/v1/sessions/{session['session_id']}/recording/end",
                        json={"request_id": "end-retry"}).json()["session"]
    assert retried["recording_end_receipt"]["integrity"] == "complete"
    assert retried["state"] == "closed"
    assert [attempt["result"] for attempt in retried["recording_end_attempts"]] == ["refused", "ended"]


def test_an_incomplete_tail_is_never_reported_as_a_complete_recording(client):
    http, fake, _ = client
    session = begun_session(http)
    fake.end_integrity = "incomplete_terminal_recorded"
    receipt = http.post(f"/api/v1/sessions/{session['session_id']}/recording/end",
                        json=END_BODY).json()["session"]["recording_end_receipt"]
    assert receipt["accepted"] is True
    assert receipt["code"] == "ended_incomplete_terminal"
    assert receipt["integrity"] == "incomplete_terminal_recorded"
    assert receipt["finalize"]["complete_tail"] is True
    assert receipt["finalize"]["audit_status"] == "INCOMPLETE"


def test_stop_and_end_never_send_reset_and_current_stays_read_only(client):
    http, fake, _ = client
    session = begun_session(http)
    http.post(f"/api/v1/sessions/{session['session_id']}/stop", json=STOP_BODY)
    http.post(f"/api/v1/sessions/{session['session_id']}/recording/end", json=END_BODY)
    before = len(fake.calls)
    http.get(f"/api/v1/sessions/{session['session_id']}")
    assert all(method == "GET" for method, _ in fake.calls[before:])
    payload = [body for path, body in fake.bodies if path == SESSION_STOP_PATH][-1]
    assert "reset" not in str(payload).lower()
    assert not any(path.endswith("/reset") for path in writes(fake))


def test_each_stop_request_keeps_its_own_receipt(client):
    http, fake, _ = client
    session = begun_session(http)
    session_id = session["session_id"]
    first = http.post(f"/api/v1/sessions/{session_id}/stop", json=STOP_BODY)
    fake.parking_confirmed = False
    second = http.post(f"/api/v1/sessions/{session_id}/stop",
                       json={"request_id": "stop-2", "reason": "OPERATOR_STOP"})
    stored = second.json()["session"]
    assert [item["request_id"] for item in stored["stop_receipts"]] == ["stop-1", "stop-2"]
    assert stored["stop_receipt"]["request_id"] == "stop-2"
    calls_before = len(fake.calls)
    replay = http.post(f"/api/v1/sessions/{session_id}/stop", json=STOP_BODY)
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    assert replay.json()["session"]["stop_receipts"][0]["code"] == "stopped"
    assert len(fake.calls) == calls_before


def test_the_client_returns_a_refused_stop_instead_of_raising_on_identity_drift(tmp_path):
    from unirobot.contracts import AdapterConfig
    from unirobot.mobilecar import MobileCarIntegration, RuntimeIdentity
    from unirobot.prepare import NativeBindingClient

    _, _, _, integration = fixture_app(tmp_path, binding=True, declare_protocols=True, stop_end=True)
    client = NativeBindingClient(integration)
    stale = RuntimeIdentity(run_id="fixture-run", backend_generation=1, episode_id="episode-not-current")
    refused = client.stop_session(request_id="stop-stale", reason="OPERATOR_STOP", parking_timeout_s=None,
                                  identity=stale, binding_id="binding-1", session_id="ps", config_fingerprint="cs")
    assert refused["accepted"] is False
    assert refused["code"] == "stop_runtime_identity_mismatch"
    assert refused["episode_id"] == "fixture-episode"
    assert refused["dispatch"]["dispatched"] is False


def test_concurrent_ends_keep_both_receipts_and_one_native_finalize(client):
    import threading

    http, fake, _ = client
    session = begun_session(http)
    session_id = session["session_id"]
    barrier = threading.Barrier(2)

    def fire(request_id: str) -> None:
        barrier.wait()
        results[request_id] = http.post(
            f"/api/v1/sessions/{session_id}/recording/end", json={"request_id": request_id})

    results: dict[str, object] = {}
    threads = [threading.Thread(target=fire, args=(f"end-race-{index}",)) for index in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert len(results) == 2, results
    stored = http.get(f"/api/v1/sessions/{session_id}").json()
    accepted = [key for key, response in results.items() if response.status_code == 201]
    refused = {key: response.json()["detail"]["code"] for key, response in results.items()
               if response.status_code != 201}
    # Whichever request won the race, the loser is refused instead of silently overwriting,
    # and every accepted answer keeps its own receipt in the stored history.
    assert accepted, results
    assert all(code == "session_not_stoppable" for code in refused.values()), refused
    stored_ids = [item["request_id"] for item in stored["recording_end_receipts"]]
    assert sorted(accepted) == sorted(stored_ids)
    assert stored["recording_end_receipt"]["request_id"] in stored_ids
    assert len(stored["recording_end_attempts"]) == len(accepted)
    assert stored["state"] == "closed"
    # One accepted end is one native finalize; a refused duplicate never reaches the Recorder.
    assert sum(1 for _, path in fake.calls if path == RECORDING_END_PATH) == len(accepted)


def test_openapi_publishes_the_stop_and_end_contracts(client):
    http, _, _ = client
    spec = http.get("/openapi.json").json()
    stop_post = spec["paths"]["/api/v1/sessions/{session_id}/stop"]["post"]
    end_post = spec["paths"]["/api/v1/sessions/{session_id}/recording/end"]["post"]
    assert stop_post["summary"].startswith("Latched robot STOP")
    schemas = spec["components"]["schemas"]
    assert set(schemas["StopSession"]["required"]) == {"request_id"}
    assert set(schemas["EndRecording"]["required"]) == {"request_id"}
    current = schemas["SessionCurrent"]["properties"]
    for field in ("stop_available", "recording_end_available", "session_stop_protocol",
                  "recording_end_protocol", "last_stop_code", "last_end_code", "recording_integrity"):
        assert field in current
    layers = schemas["RecordingEndReceipt"]["properties"]
    assert {"dispatch", "parking", "drain", "finalize", "integrity"} <= set(layers)
    assert end_post["summary"].startswith("Stop and reliably finalize")
