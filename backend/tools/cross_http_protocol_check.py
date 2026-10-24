"""Cross-HTTP protocol check: platform app + real native mock candidate.

Test-only. The platform recipe used by the target app must identify itself as
the mock protocol recipe; this script refuses to run against the production G1
candidate. The native backend is mock and does not advance MuJoCo physics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from unirobot.contracts import AdapterConfig
from unirobot.mobilecar import MobileCarIntegration, RuntimeIdentity
from unirobot.prepare import BindingError, NativeBindingClient


def request(base: str, method: str, path: str, body: dict | None = None) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        base.rstrip("/") + path, data=data, method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def get(base: str, path: str) -> Any:
    return request(base, "GET", path)[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform-url", required=True)
    parser.add_argument("--native-url", required=True)
    parser.add_argument("--native-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    target = Path(args.out)
    target.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, Any] = {"classification": "test-only mock native; no physics"}

    recipe = get(args.platform_url, "/api/v1/mobilecar/execution-recipe")
    if recipe.get("recipe_id") != "mobilecar.g1.teleop.mock-testonly":
        raise SystemExit("refusing: target platform is not using the mock test recipe")
    evidence["test_recipe"] = {
        "recipe_id": recipe["recipe_id"],
        "recipe_revision": recipe["recipe_revision"],
        "native_commit": recipe["native"]["commit"],
        "expected_config": recipe["expected"]["config_manifest_sha256"],
        "expected_scene": recipe["expected"]["scene_manifest_sha256"],
    }

    draft = request(args.platform_url, "POST", "/api/v1/experiment-drafts",
                    {"name": "cross-http mock protocol"})[1]
    validation = request(
        args.platform_url, "POST", f"/api/v1/experiment-drafts/{draft['draft_id']}/validate",
        {"execution_revision": draft["execution_revision"], "fingerprint": draft["fingerprint"]},
    )[1]["validation"]["result"]
    if validation["status"] != "passed" or validation["execution_eligible"] is not True:
        raise SystemExit(f"test recipe did not validate: {validation['blocking_reasons']}")
    evidence["validation"] = {
        "snapshot_id": validation["snapshot_id"],
        "snapshot_sha256": validation["snapshot_sha256"],
        "status": validation["status"],
        "execution_eligible": validation["execution_eligible"],
        "checks": len(validation["checks"]),
        "blocking_reasons": validation["blocking_reasons"],
    }

    status, envelope = request(
        args.platform_url, "POST", "/api/v1/sessions",
        {
            "execution_revision": draft["execution_revision"],
            "fingerprint": draft["fingerprint"],
            "validated_snapshot_id": validation["validated_snapshot_id"],
            "idempotency_key": "cross-http-mock-1",
        },
    )
    if status != 201:
        raise SystemExit(f"session creation failed: {status} {envelope}")
    session = envelope["session"]
    session_id = session["session_id"]
    binding = session["native_binding"]
    evidence["session_created"] = {
        "session_id": session_id,
        "state": session["state"],
        "binding_id": binding["binding_id"],
        "config_fingerprint": binding["config_fingerprint"],
    }

    prepared = request(args.platform_url, "GET", f"/api/v1/sessions/{session_id}")[1]
    evidence["current_prepared"] = prepared["current"]
    if prepared["current"]["status"] != "prepared" or not prepared["current"]["valid"]:
        raise SystemExit("prepared current observation is not valid")

    started = request(args.platform_url, "POST", f"/api/v1/sessions/{session_id}/start")[1]
    evidence["start"] = {
        "state": started["state"],
        "receipt": started["start_receipt"],
    }
    current_started = request(args.platform_url, "GET", f"/api/v1/sessions/{session_id}")[1]["current"]
    evidence["current_started"] = current_started
    if current_started["status"] != "started" or not current_started["valid"]:
        raise SystemExit("started current observation is not valid")

    identity = RuntimeIdentity.model_validate(session["native_identity"])
    integration = MobileCarIntegration(
        AdapterConfig(id="mobilecar", title="test-only mock", project_root="unused",
                      base_url=args.native_url)
    )
    client = NativeBindingClient(integration)
    readback = client.readback(binding["binding_id"])
    evidence["native_readback_started"] = readback
    duplicate_start = client.start(
        binding_id=binding["binding_id"], session_id=session_id,
        config_fingerprint=binding["config_fingerprint"], identity=identity,
    )
    evidence["native_duplicate_start"] = duplicate_start
    if duplicate_start["started"] is not True:
        raise SystemExit("native duplicate start was not idempotent")
    try:
        client.prepare(
            session_id="ps-direct-duplicate",
            config_fingerprint="cs-" + "f" * 40,
            identity=identity,
        )
    except BindingError as exc:
        evidence["native_duplicate_prepare_refused"] = {
            "code": exc.code, "message": str(exc), "http_status": exc.http_status,
        }
    else:
        raise SystemExit("native duplicate prepare unexpectedly succeeded")
    wrong_identity = identity.model_copy(update={"episode_id": "episode-not-live"})
    try:
        client.prepare(
            session_id="ps-direct-wrong-identity",
            config_fingerprint="cs-" + "e" * 40,
            identity=wrong_identity,
        )
    except BindingError as exc:
        evidence["native_wrong_identity_refused"] = {
            "code": exc.code, "message": str(exc), "http_status": exc.http_status,
        }
    else:
        raise SystemExit("native wrong-identity prepare unexpectedly succeeded")

    duplicate_platform_start = request(
        args.platform_url, "POST", f"/api/v1/sessions/{session_id}/start"
    )[1]
    evidence["platform_duplicate_start_type"] = duplicate_platform_start["state"]

    begun = request(
        args.platform_url, "POST", f"/api/v1/sessions/{session_id}/recording/begin",
        {"operator_id": "cross-http-human", "view_source": "third_person_3d"},
    )[1]
    evidence["begin"] = begun
    if begun["replayed"] is not False:
        raise SystemExit("first begin was replayed")
    receipt = begun["session"]["recording_begin_receipt"]
    current_recording = request(args.platform_url, "GET", f"/api/v1/sessions/{session_id}")[1]["current"]
    evidence["current_recording"] = current_recording
    if not current_recording["valid"] or not current_recording["recording_ready"] or not current_recording["motion_ready"]:
        raise SystemExit("recording current observation is not ready")

    events_path = Path(args.native_root) / "runs" / identity.run_id / "episodes" / identity.episode_id / "events.jsonl"
    snapshot_path = events_path.parent / "initial_snapshot.json"
    snapshot_digest = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    event_count = len(events)
    evidence["native_start_records"] = {
        "initial_snapshot_path": str(snapshot_path),
        "initial_snapshot_sha256": snapshot_digest,
        "receipt_sha256": receipt["initial_snapshot_sha256"],
        "initial_snapshot_matches": snapshot_digest == receipt["initial_snapshot_sha256"],
        "first_events": [(item["event_type"], item.get("event_seq")) for item in events[:3]],
        "event_count": event_count,
    }
    if snapshot_digest != receipt["initial_snapshot_sha256"]:
        raise SystemExit("initial snapshot digest does not match the begin receipt")

    repeated = request(
        args.platform_url, "POST", f"/api/v1/sessions/{session_id}/recording/begin",
        {"operator_id": "cross-http-human", "view_source": "third_person_3d"},
    )[1]
    events_after = len(events_path.read_text(encoding="utf-8").splitlines())
    evidence["duplicate_begin"] = {
        "replayed": repeated["replayed"],
        "segment_id": repeated["session"]["recording_begin_receipt"]["recording_segment_id"],
        "event_count_after": events_after,
    }
    if repeated["replayed"] is not True or events_after != event_count:
        raise SystemExit("duplicate begin created another segment")

    before_release = request(args.platform_url, "GET", f"/api/v1/sessions/{session_id}")[1]["current"]
    released = client.readback(binding["binding_id"])
    if released.get("state") != "started":
        raise SystemExit("native binding was not started before release")
    # The client discards the release response; exercise the exact client call.
    client.release(binding["binding_id"])
    released = client.readback(binding["binding_id"])
    after_release = request(args.platform_url, "GET", f"/api/v1/sessions/{session_id}")[1]["current"]
    evidence["release"] = {
        "before_state": before_release["binding"]["state"],
        "native_readback": released,
        "current": after_release,
    }
    if released.get("state") != "released":
        raise SystemExit("native release did not invalidate the binding")
    if after_release["valid"] or after_release["motion_ready"] or after_release["recording_ready"]:
        raise SystemExit("platform current still reports ready after release")

    stop = request(args.native_url, "POST", "/api/v1/episodes/stop",
                   {"reason": "CROSS_HTTP_TEST_CLEANUP"})[1]
    evidence["cleanup"] = {"note": "existing stop path; not part of m1-recording-1", "response": stop}
    (target / "cross-http.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "session": session_id,
        "validation": validation["status"],
        "start": started["state"],
        "begin": receipt["recording_status"],
        "release_state": released.get("state"),
        "current_after_release": after_release["status"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
