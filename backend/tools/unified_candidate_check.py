"""Verify one unified platform candidate really serves every surface from one process.

The candidate is launched by tools/launch_unified_gateway.py against the real native
instance with GET-only access. Anything that would need a native write is expected to be
refused by the platform before the transport, and this check proves that refusal is real
by comparing the native read state before and after.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import source_digest

REQUIRED_PATHS = (
    "/api/v1/mobilecar/scene", "/api/v1/mobilecar/capabilities", "/api/v1/mobilecar/snapshot",
    "/api/v1/mobilecar/kinematics", "/api/v1/mobilecar/execution-recipe",
    "/api/v1/experiment-drafts", "/api/v1/maps", "/api/v1/route-drafts",
    "/api/v1/sessions", "/api/v1/sessions/{session_id}", "/api/v1/sessions/{session_id}/stop",
    "/api/v1/sessions/{session_id}/recording/end",
)
REQUIRED_SCHEMAS = ("StopSession", "EndRecording", "StopReceipt", "RecordingEndReceipt", "SessionCurrent")
CURRENT_FIELDS = ("stop_available", "recording_end_available", "session_stop_protocol",
                  "recording_end_protocol", "last_stop_code", "last_end_code", "recording_integrity")


class Failed(Exception):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def request(base: str, path: str, body: dict | None = None, method: str | None = None) -> tuple[int, Any]:
    data = canonical(body) if body is not None else None
    call = urllib.request.Request(base.rstrip("/") + path, data=data,
                                  method=method or ("POST" if data else "GET"),
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(call, timeout=90) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        raw = error.read().decode()
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, {"raw": raw[:300]}


def raw_request(base: str, path: str) -> bytes:
    try:
        with urllib.request.urlopen(base.rstrip("/") + path, timeout=90) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise Failed(f"GET {path} -> HTTP {error.code}: {error.read().decode()[:300]}")


def code_of(payload: Any) -> Any:
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, dict):
        return detail.get("code")
    if isinstance(detail, str):
        return detail
    return json.dumps(detail, default=str)[:200] if detail is not None else None


def check(name: str, passed: bool, detail: Any, results: list) -> None:
    results.append({"name": name, "passed": bool(passed), "detail": detail})
    if not passed:
        raise Failed(f"{name} -> {json.dumps(detail, default=str)[:900]}")


def native_state(base: str) -> dict:
    health = request(base, "/api/v1/health")[1]
    snapshot = request(base, "/api/v1/snapshot")[1]
    return {"run_id": health["run_id"], "backend_generation": health["backend_generation"],
            "episode_id": health["episode_id"], "recording_status": health["recording_status"],
            "recording_segment_id": health.get("recording_segment_id"),
            "safety_latched": bool(snapshot.get("safety_latched")),
            "base_owner_session_id": snapshot.get("base_owner_session_id"),
            "arm_owner_session_id": snapshot.get("arm_owner_session_id"),
            "stopped": snapshot["base"]["stopped"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform-url", required=True)
    parser.add_argument("--native-url", required=True)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--startup-manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    results: list = []
    startup = json.loads(args.startup_manifest.read_text(encoding="utf-8"))
    before = native_state(args.native_url)

    recipe = request(args.platform_url, "/api/v1/mobilecar/execution-recipe")[1]
    check("unified candidate runs the production recipe", recipe["recipe_id"] == "mobilecar.g1.teleop",
          recipe["recipe_id"], results)
    check("production recipe still declares only binding and begin",
          set(recipe["required_protocols"]) == {"session_binding", "recording_begin"},
          recipe["required_protocols"], results)

    spec = request(args.platform_url, "/openapi.json")[1]
    check("one OpenAPI exposes every surface", not [path for path in REQUIRED_PATHS if path not in spec["paths"]],
          [path for path in REQUIRED_PATHS if path not in spec["paths"]], results)
    schemas = spec["components"]["schemas"]
    check("STOP and end schemas are published", all(name in schemas for name in REQUIRED_SCHEMAS),
          [name for name in REQUIRED_SCHEMAS if name not in schemas], results)
    check("current exposes stop and end availability",
          all(field in schemas["SessionCurrent"]["properties"] for field in CURRENT_FIELDS),
          [field for field in CURRENT_FIELDS if field not in schemas["SessionCurrent"]["properties"]], results)
    stop_doc = json.dumps(spec["paths"]["/api/v1/sessions/{session_id}/stop"]["post"])
    check("STOP endpoint names the process-stop endpoint it is not", "/api/v1/runs/" in stop_doc, stop_doc[:220], results)
    end_doc = json.dumps(spec["paths"]["/api/v1/sessions/{session_id}/recording/end"]["post"])
    check("end endpoint documents the separate evidence layers",
          all(word in end_doc for word in ("dispatch", "drain", "finalize", "integrity")), end_doc[:220], results)
    check("process stop remains a distinct operation", "/api/v1/runs/{run_id}/stop" in spec["paths"],
          sorted(path for path in spec["paths"] if "stop" in path), results)

    status, scene = request(args.platform_url, "/api/v1/mobilecar/scene")
    check("scene read is geometry-2", status == 200 and scene.get("schema_version") == "unirobot-mobilecar-geometry-2",
          {"status": status, "schema": scene.get("schema_version")}, results)
    bundle_manifest = json.loads((args.bundle_dir / "bundle.json").read_text(encoding="utf-8"))
    provenance, binding = scene["geometry_provenance"], scene["geometry_binding"]
    check("geometry provenance names the frozen bundle and compiled scene",
          binding["bundle_sha256"] == bundle_manifest["geometry_provenance"]["bundle_sha256"]
          == provenance["bundle_sha256"]
          and canonical(bundle_manifest["scene"]) and binding["content_identity_sha256"],
          {"bundle_sha256": binding["bundle_sha256"][:16], "content_identity": binding["content_identity_sha256"][:16]},
          results)
    assets = scene["data"]["mesh_assets"]
    check("geometry-2 publishes 23 assets", len(assets) == 23, len(assets), results)
    readable = []
    for asset in assets:
        body = raw_request(args.platform_url, asset["uri"])
        readable.append(hashlib.sha256(body).hexdigest() == asset["sha256"])
    check("every asset byte stream matches its declared digest", all(readable) and len(readable) == 23,
          {"checked": len(readable), "mismatched": readable.count(False)}, results)

    capabilities = request(args.platform_url, "/api/v1/mobilecar/capabilities")[1]
    check("real native declares no stop or end protocol",
          capabilities.get("session_stop_protocol") is None and capabilities.get("recording_end_protocol") is None,
          {key: value for key, value in capabilities.items() if "protocol" in str(key).lower()}, results)
    def dig(node: Any, key: str) -> Any:
        if isinstance(node, str) and node.strip().startswith(("{", "[")):
            try:
                node = json.loads(node)
            except json.JSONDecodeError:
                return None
        if isinstance(node, dict):
            if key in node:
                return node[key]
            for value in node.values():
                found = dig(value, key)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for value in node:
                found = dig(value, key)
                if found is not None:
                    return found
        return None

    def actual(body: dict) -> dict:
        return {"tick": dig(body, "control_tick_id"), "monotonic": dig(body, "backend_monotonic_s"),
                "sim": dig(body, "sim_time_s"), "envelope_keys": sorted(body)[:12],
                "data_source": body.get("data_source")}

    first = actual(request(args.platform_url, "/api/v1/mobilecar/snapshot")[1])
    second = actual(request(args.platform_url, "/api/v1/mobilecar/snapshot")[1])
    advancing = (first["tick"] and second["tick"] and first["tick"] != second["tick"]) \
        or (first["monotonic"] is not None and second["monotonic"] is not None
            and float(second["monotonic"]) > float(first["monotonic"])) \
        or (first["sim"] is not None and second["sim"] is not None and float(second["sim"]) > float(first["sim"]))
    check("actual state keeps advancing through the platform", bool(advancing),
          {"first": first, "second": second}, results)
    kinematics = request(args.platform_url, "/api/v1/mobilecar/kinematics")[1]
    check("kinematics is served with a fixed profile and digest",
          bool(kinematics.get("profile_id") and kinematics.get("digest")),
          {"profile_id": kinematics.get("profile_id"), "digest": (kinematics.get("digest") or "")[:16]}, results)

    maps = request(args.platform_url, "/api/v1/maps")[1]
    listed = maps.get("maps", [])
    check("real map packages are listed as offline history",
          maps.get("supported") is True and len(listed) >= 2
          and all(item.get("live") is False for item in listed),
          {"count": len(listed), "ids": [item.get("map_id") for item in listed]}, results)
    room = listed[0]
    version_status, version = request(args.platform_url, f"/api/v1/maps/{room['map_id']}/versions/{room['version']}")
    check("map version is readable with fixed identity and offline provenance",
          version_status == 200 and version.get("status") == "available"
          and version.get("frame") == room.get("frame") and version.get("live") is False
          and version.get("assets_verified") is True and bool(version.get("manifest_sha256")),
          {"status": version.get("status"), "source": version.get("source"), "test_only": version.get("test_only"),
           "manifest_sha256": (version.get("manifest_sha256") or "")[:16]}, results)
    image_ref = version.get("image") or {}
    fallback = f"/api/v1/maps/{room['map_id']}/versions/{room['version']}/image"
    if image_ref.get("sha256") and "sha256=" not in (image_ref.get("href") or ""):
        fallback = f"{fallback}?sha256={image_ref['sha256']}"
    image_path = image_ref.get("href") or fallback
    image = raw_request(args.platform_url, image_path)
    check("map image bytes match the verified package digest",
          bool(image_ref.get("sha256")) and hashlib.sha256(image).hexdigest() == image_ref["sha256"],
          {"read_bytes": len(image), "digest": hashlib.sha256(image).hexdigest()[:16]}, results)
    check("map version never claims navigation eligibility",
          not any(value is True for value in (version.get("compatibility") or {}).values()),
          version.get("compatibility"), results)

    draft = request(args.platform_url, "/api/v1/route-drafts",
                    {"name": "unified-candidate-route", "map_ref": {"map_id": room["map_id"],
                                                                    "version": room["version"], "frame": room["frame"]},
                     "waypoints": [{"id": "wp-1", "order": 1, "x_m": 0.0, "y_m": 0.0, "yaw_rad": 0.0},
                                   {"id": "wp-2", "order": 2, "x_m": 0.5, "y_m": 0.0, "yaw_rad": 0.0}]})
    check("route draft persists in the candidate namespace", draft[0] == 201 and "route_id" in draft[1],
          {"status": draft[0], "detail": code_of(draft[1]) if draft[0] != 201 else draft[1]["route_id"]}, results)
    route = draft[1]
    published = request(args.platform_url, f"/api/v1/route-drafts/{route['route_id']}/publish",
                        {"base_revision": route["draft_revision"]})
    check("route version publishes immutably with display-only flags",
          published[0] == 200 and published[1]["route_version"]["navigation_eligible"] is False
          and published[1]["route_version"]["adoption_supported"] is False
          and published[1]["route_version"]["execution_supported"] is False
          and published[1]["route_version"]["display_supported"] is True,
          {"status": published[0], "detail": code_of(published[1]) if published[0] != 200 else
              {"version": published[1]["route_version"]["version"]}}, results)
    current = request(args.platform_url, f"/api/v1/route-drafts/{route['route_id']}")[1]
    newer = request(args.platform_url, f"/api/v1/route-drafts/{route['route_id']}",
                    {"base_revision": current["draft_revision"], "name": current["name"] + " (advanced)",
                     "map_ref": current["map_ref"], "waypoints": current["waypoints"]}, method="PUT")
    conflict = request(args.platform_url, f"/api/v1/route-drafts/{route['route_id']}",
                       {"base_revision": current["draft_revision"], "name": "stale save",
                        "map_ref": current["map_ref"], "waypoints": current["waypoints"]}, method="PUT")
    check("saving advances the revision and a now-stale base revision is refused",
          newer[0] == 200 and newer[1]["draft_revision"] == current["draft_revision"] + 1
          and conflict[0] == 409,
          {"advanced_to": newer[1]["draft_revision"] if newer[0] == 200 else code_of(newer[1]),
           "conflict_status": conflict[0], "conflict_code": code_of(conflict[1])}, results)

    experiment = request(args.platform_url, "/api/v1/experiment-drafts", {"name": "unified candidate check"})[1]
    validation = request(args.platform_url, f"/api/v1/experiment-drafts/{experiment['draft_id']}/validate",
                         {"execution_revision": experiment["execution_revision"], "fingerprint": experiment["fingerprint"]})
    outcome = validation[1].get("validation", {}).get("result", {})
    check("configuration validation refuses for the real reason",
          outcome.get("status") == "failed" and outcome.get("execution_eligible") is False
          and bool(outcome.get("blocking_reasons")),
          {"status": outcome.get("status"), "reasons": outcome.get("blocking_reasons")}, results)
    session = request(args.platform_url, "/api/v1/sessions",
                      {"execution_revision": experiment["execution_revision"], "fingerprint": experiment["fingerprint"],
                       "validated_snapshot_id": "no-eligible-snapshot", "idempotency_key": "unified-candidate-check"})
    check("no Session can be created from an ineligible snapshot", session[0] != 201 and "session" not in session[1],
          {"status": session[0], "code": code_of(session[1])}, results)

    stop = request(args.platform_url, "/api/v1/sessions/ps-unified-unknown/stop", {"request_id": "stop-check"})
    end = request(args.platform_url, "/api/v1/sessions/ps-unified-unknown/recording/end", {"request_id": "end-check"})
    check("STOP and end refuse without reaching native",
          stop[0] in (404, 409) and end[0] in (404, 409)
          and code_of(stop[1]) in ("session_not_found", "stop_unsupported")
          and code_of(end[1]) in ("session_not_found", "recording_end_unsupported"),
          {"stop": stop[0], "stop_code": code_of(stop[1]), "end": end[0], "end_code": code_of(end[1])}, results)

    after = native_state(args.native_url)
    check("native instance is untouched by the whole check", before == after, {"before": before, "after": after}, results)
    database = Path(startup["database"]["path"])
    check("candidate database is isolated and was new", database.is_file() and not startup["database"]["existed_before"],
          str(database), results)
    source_binding = source_digest.bind(Path(startup["platform_source"]["backend_root"]), startup)
    check("candidate bytes equal the frozen startup manifest",
          source_binding["match"] and source_binding["recorded_file_count"] == source_binding["recomputed_file_count"],
          {"recorded": source_binding["recorded_aggregate"], "recomputed": source_binding["recomputed_aggregate"],
           "files": source_binding["recomputed_file_count"],
           "changed_or_missing_paths": source_binding["changed_or_missing_paths"]}, results)

    evidence = {
        "classification": "unified candidate; real native access is GET-only and execution qualification is unchanged",
        "listen": startup["listen"], "native_url": args.native_url,
        "startup_manifest_digest": hashlib.sha256(args.startup_manifest.read_bytes()).hexdigest(),
        "platform_source": {"file_count": startup["platform_source"]["file_count"],
                            "aggregate": startup["platform_source"]["aggregate"],
                            "recomputed_aggregate": source_binding["recomputed_aggregate"],
                            "matches_running_bytes": source_binding["match"]},
        "recipe": {"id": startup["recipe"]["recipe_id"], "fingerprint": startup["recipe"]["fingerprint"],
                   "required_protocols": startup["recipe"]["required_protocols"]},
        "geometry_bundle": {"path": startup["geometry_bundle"]["path"],
                            "asset_count": startup["geometry_bundle"]["asset_count"],
                            "bundle_json_sha256": startup["geometry_bundle"]["bundle_json_sha256"],
                            "bundle_sha256": binding["bundle_sha256"],
                            "content_identity_sha256": binding["content_identity_sha256"],
                            "compiled_scene_sha256": provenance["compiled_scene_sha256"]},
        "maps": {"root": startup["maps"]["root"], "packages": startup["maps"]["packages"],
                 "listed": [item.get("map_id") for item in listed]},
        "route": {"route_id": route["route_id"], "published_version": published[1]["route_version"]["version"]},
        "native_read_state": {"before": before, "after": after},
        "checks": results,
        "not_covered": ["positive begin/STOP/end lifecycle needs the test-only recipe against a mock native",
                        "physical parking confirmation, 8792 deployment, and any native write"],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": sum(1 for item in results if item["passed"]), "total": len(results),
                      "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Failed as error:
        print(f"unified check failed: {error}")
        raise SystemExit(1)
