"""Test-only cross-HTTP check: real platform client and app over real native HTTP.

The native service is the m1h candidate started with its clearly labelled mock
backend and an isolated Recorder root, so files, events and terminal states on
disk are real. Nothing here advances MuJoCo physics, touches 8792 or uses the
production G1 recipe. Parking-unconfirmed and finalize-failure outcomes are not
reachable through HTTP alone and are proven in the native test suite instead.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from unirobot.contracts import AdapterConfig
from unirobot.mobilecar import MobileCarIntegration, RuntimeIdentity
from unirobot.prepare import NativeBindingClient

EXPECTED_PROTOCOLS = {
    "session_binding": "m1-binding-1",
    "recording_begin": "m1-recording-1",
    "session_stop": "m1-stop-1",
    "recording_end": "m1-end-1",
}


def request(base: str, method: str, path: str, body: dict | None = None) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        base.rstrip("/") + path, data=data, method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"raw": raw}


class Checks:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(self, name: str, passed: bool, detail: Any = None) -> None:
        self.items.append({"name": name, "passed": bool(passed), "detail": detail})
        if not passed:
            raise SystemExit(f"check failed: {name} -> {json.dumps(detail, default=str)[:800]}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def episode_files(runs_root: Path, run_id: str, episode_id: str) -> tuple[Path, Path]:
    root = runs_root / run_id / "episodes" / episode_id
    return root / "events.jsonl", root / "episode_complete.json"


def terminal_count(events_path: Path) -> int:
    if not events_path.is_file():
        return 0
    return sum(1 for line in events_path.read_text(encoding="utf-8").splitlines()
               if json.loads(line).get("event_type") == "episode_terminal")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform-url", required=True)
    parser.add_argument("--native-url", required=True)
    parser.add_argument("--native-runs", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    runs_root = Path(args.native_runs)
    checks = Checks()
    refusals: dict[str, Any] = {}
    evidence: dict[str, Any] = {
        "classification": "test-only; mock backend, real native HTTP, real Recorder files",
        "no_physics": True,
        "production_recipe_used": False,
        "platform_url": args.platform_url,
        "native_url": args.native_url,
    }

    recipe = request(args.platform_url, "GET", "/api/v1/mobilecar/execution-recipe")[1]
    checks.add("platform uses the test-only mock recipe",
               recipe.get("recipe_id") == "mobilecar.g1.teleop.mock-testonly", recipe.get("recipe_id"))
    checks.add("test recipe requires stop and end",
               recipe.get("required_protocols") == EXPECTED_PROTOCOLS, recipe.get("required_protocols"))
    capabilities = request(args.native_url, "GET", "/api/v1/capabilities")[1]
    checks.add("native backend is the labelled mock", capabilities.get("backend_kind") == "mock",
               capabilities.get("backend_kind"))
    checks.add("native declares stop and end",
               capabilities.get("session_stop_protocol") == "m1-stop-1"
               and capabilities.get("recording_end_protocol") == "m1-end-1",
               {"stop": capabilities.get("session_stop_protocol"),
                "end": capabilities.get("recording_end_protocol")})
    health_before = request(args.native_url, "GET", "/api/v1/health")[1]
    identity = RuntimeIdentity(run_id=health_before["run_id"],
                               backend_generation=health_before["backend_generation"],
                               episode_id=health_before["episode_id"])
    evidence["native_identity_before"] = identity.model_dump()

    draft = request(args.platform_url, "POST", "/api/v1/experiment-drafts",
                    {"name": "cross-http stop end"})[1]
    validation = request(args.platform_url, "POST", f"/api/v1/experiment-drafts/{draft['draft_id']}/validate",
                         {"execution_revision": draft["execution_revision"],
                          "fingerprint": draft["fingerprint"]})[1]["validation"]["result"]
    checks.add("test recipe validates", validation["status"] == "passed" and validation["execution_eligible"] is True,
               validation["blocking_reasons"])
    session = request(args.platform_url, "POST", "/api/v1/sessions", {
        "execution_revision": draft["execution_revision"],
        "fingerprint": draft["fingerprint"],
        "validated_snapshot_id": validation["validated_snapshot_id"],
        "idempotency_key": "cross-http-stop-end",
    })
    checks.add("prepared session created", "session" in session[1], session[1])
    session = session[1]["session"]
    session_id = session["session_id"]
    binding_id = session["native_binding"]["binding_id"]
    fingerprint = session["native_binding"]["config_fingerprint"]
    checks.add("platform started without motion",
               request(args.platform_url, "POST", f"/api/v1/sessions/{session_id}/start")[1]
               ["execution"]["recording_begin_required"] is True)

    current = request(args.platform_url, "GET", f"/api/v1/sessions/{session_id}")[1]["current"]
    checks.add("current offers stop and end after start",
               current["stop_available"] is True and current["recording_end_available"] is False,
               {"stop": current["stop_available"], "end": current["recording_end_available"]})

    begun = request(args.platform_url, "POST", f"/api/v1/sessions/{session_id}/recording/begin",
                    {"operator_id": "cross-http-human", "view_source": "third_person_3d"})[1]["session"]
    segment = begun["recording_begin_receipt"]["recording_segment_id"]
    evidence["recording_segment_id"] = segment

    status, stop_doc = request(args.platform_url, "POST", f"/api/v1/sessions/{session_id}/stop",
                               {"request_id": "stop-live", "reason": "OPERATOR_STOP"})
    stop = stop_doc["session"]["stop_receipt"]
    checks.add("stop accepted", status == 201 and stop["accepted"] is True and stop["code"] == "stopped",
               {"status": status, "code": stop["code"], "reason": stop["reason"]})
    checks.add("stop dispatch and parking are separate layers",
               stop["dispatch"]["dispatched"] is True and stop["dispatch"]["status"] == "DISPATCHED"
               and stop["parking"]["confirmed"] is True,
               {"dispatch": stop["dispatch"], "parking": stop["parking"]["confirmed"]})
    checks.add("stop does not claim full coverage",
               stop["parking"]["coverage_complete"] is False
               and stop["parking"]["scope_coverage"]["gripper"] == "not_observed",
               stop["parking"]["scope_coverage"])
    checks.add("stop leaves the recording and does not reset",
               stop["recording_touched"] is False and stop["motion_restored"] is False
               and stop["recording_status"] == "RECORDING" and stop["recording_segment_id"] == segment,
               {k: stop[k] for k in ("recording_touched", "motion_restored", "recording_status")})

    status, replay = request(args.platform_url, "POST", f"/api/v1/sessions/{session_id}/stop",
                             {"request_id": "stop-live", "reason": "OPERATOR_STOP"})
    checks.add("same stop request replays", status == 200 and replay["replayed"] is True
               and replay["session"]["stop_receipt"]["dispatch"]["command_id"] == stop["dispatch"]["command_id"],
               {"status": status, "replayed": replay["replayed"]})

    stale = RuntimeIdentity(run_id=identity.run_id, backend_generation=identity.backend_generation,
                            episode_id="episode-not-current")
    client = NativeBindingClient(MobileCarIntegration(AdapterConfig(
        id="mobilecar", title="cross-http native client", project_root="unused", base_url=args.native_url)))
    mismatch = client.stop_session(request_id="stop-wrong-identity", reason="OPERATOR_STOP",
                                   parking_timeout_s=None, identity=stale)
    checks.add("wrong runtime identity is refused without dispatch",
               mismatch["accepted"] is False and mismatch["code"] == "stop_runtime_identity_mismatch"
               and mismatch["dispatch"]["dispatched"] is False,
               {"code": mismatch["code"], "dispatch": mismatch["dispatch"]})
    refusals["stop_runtime_identity_mismatch"] = mismatch

    race: dict[str, tuple[int, Any]] = {}
    barrier = threading.Barrier(2)

    def fire(request_id: str) -> None:
        barrier.wait()
        race[request_id] = request(args.platform_url, "POST", f"/api/v1/sessions/{session_id}/recording/end",
                                   {"request_id": request_id})

    racers = [threading.Thread(target=fire, args=(f"end-race-{index}",)) for index in (1, 2)]
    for thread in racers:
        thread.start()
    for thread in racers:
        thread.join(timeout=60)
        checks.add("concurrent end thread finished", not thread.is_alive())
    checks.add("both concurrent ends answered", len(race) == 2, sorted(race))
    # Either request can win. A winner always yields its own accepted receipt; a loser is
    # either refused by the platform guard or answered from the durable disk tail, and in
    # both cases it never dispatches a second STOP or writes a second tail record.
    accepted_ends = {key: doc["session"]["recording_end_receipt"]
                     for key, (status, doc) in race.items() if status == 201}
    refused_ends = {key: {"status": status, "code": doc["detail"]["code"]}
                    for key, (status, doc) in race.items() if status != 201}
    checks.add("at least one concurrent end was accepted", bool(accepted_ends), sorted(race))
    checks.add("a losing concurrent end is an explicit refusal",
               all(item["status"] == 409 and item["code"] == "session_not_stoppable"
                   for item in refused_ends.values()), refused_ends)
    checks.add("every accepted concurrent end reports a durable complete tail",
               all(receipt["integrity"] == "complete" for receipt in accepted_ends.values()),
               {key: receipt["code"] for key, receipt in accepted_ends.items()})
    dispatched = [key for key, receipt in accepted_ends.items() if receipt["dispatch"]["dispatched"]]
    checks.add("exactly one concurrent end dispatched STOP and finalized",
               len(dispatched) == 1,
               {"dispatched": dispatched,
                "codes": {key: receipt["code"] for key, receipt in accepted_ends.items()}})
    end = accepted_ends[dispatched[0]]
    evidence["concurrent_receipts"] = {
        **{key: {"code": receipt["code"], "dispatched": receipt["dispatch"]["dispatched"],
                 "integrity": receipt["integrity"]} for key, receipt in accepted_ends.items()},
        **{key: {"status": item["status"], "code": item["code"]} for key, item in refused_ends.items()},
    }

    events_path, complete_path = episode_files(runs_root, identity.run_id, identity.episode_id)
    checks.add("end accepted with complete integrity",
               end["accepted"] is True and end["code"] == "ended" and end["integrity"] == "complete",
               {"code": end["code"], "integrity": end["integrity"], "reason": end["reason"]})
    checks.add("end layers stay separate",
               end["dispatch"]["dispatched"] is True and end["parking"]["confirmed"] is True
               and end["drain"]["completed"] is True and end["finalize"]["completed"] is True,
               {"dispatch": end["dispatch"]["status"], "parking": end["parking"]["confirmed"],
                "drain": end["drain"], "finalize": end["finalize"]["completed"]})
    checks.add("end issued no reset or side effects",
               end["reset_issued"] is False and end["safety_cleared"] is False
               and end["owner_acquired"] is False,
               {k: end[k] for k in ("reset_issued", "safety_cleared", "owner_acquired")})
    checks.add("finalize digest matches the file on disk",
               sha256(complete_path) == end["finalize"]["episode_complete_sha256"],
               {"disk": sha256(complete_path), "receipt": end["finalize"]["episode_complete_sha256"]})
    complete = read_json(complete_path)
    checks.add("tail record names this segment",
               complete["recording_segment_id"] == segment and complete["audit_status"] == "COMPLETE",
               {"segment": complete["recording_segment_id"], "audit": complete["audit_status"]})
    checks.add("concurrency left exactly one terminal event", terminal_count(events_path) == 1,
               terminal_count(events_path))
    checks.add("checksummed artifacts reported", end["finalize"]["checksummed_artifacts"] == len(complete["checksums"]),
               {"receipt": end["finalize"]["checksummed_artifacts"], "file": len(complete["checksums"])})
    closed = request(args.platform_url, "GET", f"/api/v1/sessions/{session_id}")[1]
    checks.add("session closed after a durable end", closed["state"] == "closed", closed["state"])

    status, same = request(args.platform_url, "GET", f"/api/v1/sessions/{session_id}")
    stored_ids = sorted(item["request_id"] for item in same["recording_end_receipts"])
    checks.add("every accepted racing request keeps its own receipt",
               stored_ids == sorted(accepted_ends)
               and same["recording_end_receipt"]["request_id"] in stored_ids,
               {"history": stored_ids, "accepted": sorted(accepted_ends)})
    replays = {}
    for request_id, (first_status, _) in sorted(race.items()):
        replay_status, replay_doc = request(args.platform_url, "POST",
                                            f"/api/v1/sessions/{session_id}/recording/end",
                                            {"request_id": request_id})
        replays[request_id] = {
            "first_status": first_status, "replay_status": replay_status,
            "replayed": replay_doc.get("replayed"),
            "code": replay_doc.get("detail", {}).get("code"),
        }
        if replay_status == 409:
            refusals["platform_session_not_stoppable"] = {
                "http_status": replay_status, "envelope": replay_doc,
                "meaning": "the Session already closed; this request_id was never accepted, so no receipt is invented"}
    checks.add("a retry of an accepted end replays without a new tail",
               all(item["replay_status"] == 200 and item["replayed"] is True
                   for item in replays.values() if item["first_status"] == 201)
               and all(item["replay_status"] == 409 and item["code"] == "session_not_stoppable"
                       for item in replays.values() if item["first_status"] != 201)
               and terminal_count(events_path) == 1
               and sha256(complete_path) == end["finalize"]["episode_complete_sha256"],
               {"replays": replays, "terminals": terminal_count(events_path)})

    after = request(args.native_url, "GET", "/api/v1/snapshot")[1]
    checks.add("runtime identity never changed",
               (after["run_id"], after["backend_generation"], after["episode_id"])
               == (identity.run_id, identity.backend_generation, identity.episode_id),
               {"after": after["run_id"], "generation": after["backend_generation"],
                "episode": after["episode_id"]})

    unknown = client.end_recording(request_id="end-unknown-segment", reason="OPERATOR_FINISHED",
                                   parking_timeout_s=None, binding_id=binding_id, session_id=session_id,
                                   config_fingerprint=fingerprint, recording_segment_id="seg_not_present",
                                   identity=identity)
    checks.add("an unknown segment is refused without dispatch",
               unknown["accepted"] is False and unknown["code"] == "end_segment_mismatch"
               and unknown["dispatch"]["dispatched"] is False,
               {"code": unknown["code"], "active": unknown["active_segment_id"]})
    refusals["end_segment_mismatch"] = unknown

    second = client.begin_recording(binding_id=binding_id, session_id=session_id,
                                    config_fingerprint=fingerprint, identity=identity,
                                    operator_id="cross-http-human-2", view_source="third_person_3d")
    newer = second["recording_segment_id"]
    stale_end = client.end_recording(request_id="end-old-segment-after-new", reason="OPERATOR_FINISHED",
                                     parking_timeout_s=None, binding_id=binding_id, session_id=session_id,
                                     config_fingerprint=fingerprint, recording_segment_id=segment,
                                     identity=identity)
    checks.add("an ended segment cannot touch a newer segment",
               stale_end["code"] == "end_already_finalized" and stale_end["replayed"] is False
               and terminal_count(events_path) == 1,
               {"code": stale_end["code"], "terminals": terminal_count(events_path)})
    refusals["end_already_finalized"] = stale_end
    foreign = client.end_recording(request_id="end-foreign-binding", reason="OPERATOR_FINISHED",
                                   parking_timeout_s=None, binding_id="binding-not-present",
                                   session_id=session_id, config_fingerprint=fingerprint,
                                   recording_segment_id=newer, identity=identity)
    checks.add("a foreign binding cannot end the newer segment",
               foreign["accepted"] is False and foreign["code"] == "end_binding_not_found"
               and foreign["dispatch"]["dispatched"] is False, foreign["code"])
    refusals["end_binding_not_found"] = foreign
    cleanup = client.end_recording(request_id="end-cleanup", reason="OPERATOR_FINISHED",
                                   parking_timeout_s=None, binding_id=binding_id, session_id=session_id,
                                   config_fingerprint=fingerprint, recording_segment_id=newer, identity=identity)
    checks.add("the newer segment ends once",
               cleanup["accepted"] is True and cleanup["integrity"] == "complete"
               and terminal_count(events_path) == 2,
               {"code": cleanup["code"], "terminals": terminal_count(events_path)})

    current = request(args.platform_url, "GET", f"/api/v1/sessions/{session_id}")[1]["current"]
    checks.add("current reports closed availability",
               current["recording_end_available"] is False
               and current["last_end_code"] in ("ended", "end_already_finalized")
               and current["recording_integrity"] == "complete",
               {"end_available": current["recording_end_available"], "last_end": current["last_end_code"],
                "integrity": current["recording_integrity"]})
    final = request(args.native_url, "GET", "/api/v1/snapshot")[1]
    checks.add("repeated platform reads never reset or re-open",
               (final["run_id"], final["backend_generation"], final["episode_id"])
               == (identity.run_id, identity.backend_generation, identity.episode_id)
               and final["recording"]["status"] == "COMPLETE",
               {"identity": final["episode_id"], "recording": final["recording"]["status"]})

    openapi = request(args.platform_url, "GET", "/openapi.json")[1]
    checks.add("openapi exposes the two session actions",
               "/api/v1/sessions/{session_id}/stop" in openapi["paths"]
               and "/api/v1/sessions/{session_id}/recording/end" in openapi["paths"],
               sorted(path for path in openapi["paths"] if "stop" in path or "end" in path))

    evidence["refusal_samples"] = refusals
    evidence["checks"] = checks.items
    evidence["passed"] = sum(1 for item in checks.items if item["passed"])
    evidence["native_identity_after"] = final
    evidence["stop_receipt"] = stop
    evidence["end_receipt"] = end
    evidence["episode_complete_file"] = complete
    evidence["terminal_events"] = terminal_count(events_path)
    evidence["not_covered_over_http"] = [
        "parking unconfirmed (needs a never-stopping motion feed)",
        "finalize failure without a tail (needs an injected Recorder failure)",
        "real MuJoCo parking, physical robot STOP confirmation, 8792 deployment",
    ]
    (out / "cross-http-stop-end.json").write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"passed": evidence["passed"], "total": len(checks.items),
                      "terminals": evidence["terminal_events"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
