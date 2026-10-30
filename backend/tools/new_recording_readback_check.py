"""Test-only: reload one newly recorded Episode through the current platform reader.

The writer is expected to be the frozen ``new_recording_roundtrip.py`` driver, run
separately with the native release interpreter. This tool never records: it builds a
test-only execution recipe from a live mock native, serves the test-only platform app,
and after the writer has stopped, starts the platform reader over real HTTP against the
isolated recording root.

Classification: real unirobot app and real HTTP; real Recorder files on disk; synthetic
media/events produced by the mock-backed generator. No MuJoCo, no render, no physics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import socket
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SCHEMA = "unirobot-new-recording-readback-1"
CLASSIFICATION = {
    "writer": "real Recorder inside the real mobilecar app; mock backend; synthetic media and events",
    "platform": "real unirobot reader app served over real HTTP",
    "input": "synthetic (mock), labelled; not a human recording and not a physical sensor measurement",
    "physics": "none; the mock backend does not step MuJoCo",
}
TIME_BASES = ("capture_backend_monotonic_s", "capture_sim_time_s", "persist_backend_monotonic_s")
PRIMARY_ROLES = ("image_observation", "camera_transform", "capture_timing_event", "state_feedback_event")


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        return probe.connect_ex((host, port)) != 0


def port_is_closed(host: str, port: int) -> bool:
    return port_is_free(host, port)


def inventory(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        stat = path.stat()
        out[path.relative_to(root).as_posix()] = {
            "bytes": stat.st_size, "sha256": sha256_file(path), "mtime_ns": stat.st_mtime_ns}
    return out


def inventory_digest(entries: dict[str, dict[str, Any]]) -> str:
    canonical = json.dumps(
        {path: {"bytes": item["bytes"], "sha256": item["sha256"]} for path, item in entries.items()},
        sort_keys=True, separators=(",", ":"),
    ).encode()
    return sha256_bytes(canonical)


def request(base: str, method: str, path: str, body: dict | None = None,
            timeout: float = 60.0) -> tuple[int, Any, dict[str, str], bytes]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        base.rstrip("/") + path, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            headers = {key.lower(): value for key, value in response.headers.items()}
            if "json" in headers.get("content-type", ""):
                return response.status, json.loads(raw.decode("utf-8")), headers, raw
            return response.status, raw, headers, raw
    except urllib.error.HTTPError as error:
        raw = error.read()
        headers = {key.lower(): value for key, value in error.headers.items()}
        try:
            document = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            document = {"raw": raw.decode("utf-8", errors="replace")[:2000]}
        return error.code, document, headers, raw


class HttpLog:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def get_json(self, base: str, path: str, timeout: float = 60.0) -> tuple[int, Any]:
        status, document, headers, raw = request(base, "GET", path, timeout=timeout)
        self.items.append({"method": "GET", "path": path, "status": status, "bytes": len(raw),
                           "sha256": sha256_bytes(raw), "content_type": headers.get("content-type")})
        return status, document

    def get_bytes(self, base: str, path: str, timeout: float = 120.0) -> tuple[int, bytes, dict[str, str]]:
        status, document, headers, raw = request(base, "GET", path, timeout=timeout)
        self.items.append({"method": "GET", "path": path, "status": status, "bytes": len(raw),
                           "sha256": sha256_bytes(raw), "content_type": headers.get("content-type")})
        return status, (document if isinstance(document, bytes) else raw), headers


class Checks:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(self, name: str, passed: bool, detail: Any = None) -> None:
        self.items.append({"name": name, "passed": bool(passed), "detail": detail})

    @property
    def failed(self) -> list[dict[str, Any]]:
        return [item for item in self.items if not item["passed"]]


def wait_for(predicate, *, timeout: float, what: str):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            value = predicate()
        except Exception as exc:  # readiness polling only; the last error is surfaced
            last = exc
            value = None
        if value:
            return value
        time.sleep(0.1)
    raise SystemExit(f"timed out waiting for {what}" + (f": {last}" if last else ""))


def build_reader_app(recipe_body: Path, native_url: str, history_source: Path, episode_root: Path,
                     draft_db: Path, port: int, manifest_path: Path | None, label: str):
    from source_digest import digest_tree
    from unirobot.api import create_app
    from unirobot.contracts import AdapterConfig
    from unirobot.mobilecar import MobileCarIntegration
    from unirobot.recipe import Recipe
    from unirobot.settings import BACKEND_ROOT

    if not port_is_free("127.0.0.1", port):
        raise SystemExit(f"refusing to start reader: 127.0.0.1:{port} is already listening")
    if draft_db.exists():
        raise SystemExit(f"refusing to overwrite an existing reader database: {draft_db}")
    document = json.loads(recipe_body.read_text(encoding="utf-8"))
    recipe = Recipe(body=document["body"], sources=document.get("sources") or [], pin=document.get("pin") or {})
    integration = MobileCarIntegration(AdapterConfig(
        id="mobilecar", title="test-only mock native", project_root="unused", base_url=native_url))
    draft_db.parent.mkdir(parents=True, exist_ok=True)
    application = create_app(
        recipe=recipe, mobilecar_integration=integration, draft_db_path=draft_db,
        history_source_path=history_source, episode_root=episode_root)
    if application.state.history_unavailable:
        raise SystemExit(f"reader history source is unavailable: {application.state.history_unavailable}")
    archive = application.state.episodes
    source_digest = {"backend_root": str(BACKEND_ROOT), **digest_tree(BACKEND_ROOT)}
    manifest = {
        "label": label,
        "listen": {"host": "127.0.0.1", "port": port, "was_free_before_start": True},
        "classification": CLASSIFICATION,
        "recipe": {"path": str(recipe_body), "sha256": sha256_file(recipe_body),
                   "recipe_id": recipe.recipe_id, "fingerprint": recipe.fingerprint},
        "native": {"base_url": native_url, "reachable_at_start": not port_is_closed("127.0.0.1", _port_of(native_url))},
        "history": {"source_file": str(history_source), "source_file_sha256": sha256_file(history_source),
                    "source_id": archive.source.source_id, "resolved_recording_root": str(archive.root)},
        "database": {"path": str(draft_db), "existed_before": False},
        "geometry": {"configured": False,
                     "effect": "robot-state and model/assets refuse with history_model_bundle_not_configured; "
                               "no online geometry is substituted"},
        "platform_source": source_digest,
        "read_only": True,
    }
    if manifest_path is not None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return application, manifest


def _port_of(url: str) -> int:
    rest = url.split("://", 1)[-1]
    return int(rest.rsplit(":", 1)[-1].split("/", 1)[0])


class ReaderServer:
    def __init__(self, application, port: int) -> None:
        import uvicorn
        self.port = port
        self.server = uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", port=port, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=30)
        wait_for(lambda: port_is_closed("127.0.0.1", self.port), timeout=5,
                 what=f"reader port {self.port} to close")


def write_source(args) -> int:
    recording_root = args.recording_root.expanduser().resolve()
    recording_root.mkdir(parents=True, exist_ok=True)
    document = {
        "schema_version": "unirobot-history-source-1",
        "source_id": args.source_id,
        "adapter_id": "mobilecar",
        "robot_id": "landerpi",
        "contract_version": "mobilecar-1.0",
        "reader_format": "native recorder on-disk layout (runs/<run_id>/episodes/<episode_id>/...)",
        "recording_root": str(recording_root),
        "native_release_id": args.native_release_id,
        "declaring_instance": {"base_url": args.native_url, "config_file": "test-only mock config",
                               "access": "test-only mock; no production instance is declared"},
        "access": "read_only_files",
        "declared_scale": {"note": "test-only isolated recording root; no native list was consulted"},
        "archive_baseline": {"scope": "not applicable to the isolated test-only recording root",
                             "files_hashed": 0, "aggregate_sha256": None,
                             "meaning": "this source describes one test recording, not the production archive"},
        "policy": {"raw_data_stays_on_server": True, "platform_writes": False,
                   "copies_or_moves_recordings": False, "recomputes_or_reexports_for_reading": False,
                   "modifies_or_restarts_declaring_instance": False,
                   "proxies_native_validate_or_assessment": False},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"source": str(args.out), "sha256": sha256_file(args.out),
                      "recording_root": str(recording_root)}))
    return 0


def build_recipe(args) -> int:
    from mock_native_protocol_app import build_test_recipe

    base = args.native_url.rstrip("/")
    recipe = build_test_recipe(base)
    declarations = {}
    for name, path in (("capabilities", "/api/v1/capabilities"), ("health", "/api/v1/health"),
                       ("scene", "/api/v1/scene"), ("snapshot", "/api/v1/snapshot"),
                       ("attestation", "/api/v1/attestation")):
        status, document, _headers, _raw = request(base, "GET", path, timeout=10)
        if status != 200:
            raise SystemExit(f"native {path} returned {status}")
        declarations[name] = document
    document = {
        "classification": "test-only recipe built from live mock native declarations",
        "native_url": base,
        "recipe_id": recipe.recipe_id,
        "recipe_fingerprint": recipe.fingerprint,
        "body": recipe.body,
        "sources": recipe.sources,
        "pin": recipe.pin,
        "native_declarations": declarations,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"recipe": str(args.out), "sha256": sha256_file(args.out),
                      "recipe_id": recipe.recipe_id, "fingerprint": recipe.fingerprint}))
    return 0


def serve(args) -> int:
    import uvicorn
    application, manifest = build_reader_app(
        args.recipe_body, args.native_url, args.history_source, args.episode_root,
        args.draft_db, args.port, args.out_manifest, args.label)
    print(json.dumps({"label": args.label, "listen": manifest["listen"],
                      "history": manifest["history"], "recipe": manifest["recipe"]}, default=str), flush=True)
    uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", port=args.port, log_level="warning")).run()
    return 0


def _compare_records(reader_records: list[dict], expected_rows: list[dict], keys: tuple[str, ...]) -> dict[str, Any]:
    mismatches = []
    for index, (actual, expected) in enumerate(zip(reader_records, expected_rows)):
        record = actual.get("record", {})
        for key in keys:
            if record.get(key) != expected.get(key):
                mismatches.append({"index": index, "key": key, "reader": record.get(key),
                                   "writer": expected.get(key)})
    return {"counts": [len(reader_records), len(expected_rows)], "mismatches": mismatches}


def verify(args) -> int:
    from unirobot.settings import BACKEND_ROOT

    phase1_path = args.phase1.expanduser().resolve()
    phase1 = json.loads(phase1_path.read_text(encoding="utf-8"))
    recording_root = args.recording_root.expanduser().resolve()
    run_id = phase1["run_id"]
    episode_id = phase1["episode_id"]
    run_dir = recording_root / run_id
    episode_dir = run_dir / "episodes" / episode_id
    checks = Checks()
    log = HttpLog()
    evidence: dict[str, Any] = {
        "schema_version": SCHEMA,
        "classification": CLASSIFICATION,
        "phase1": {"path": str(phase1_path), "sha256": sha256_file(phase1_path)},
        "run_id": run_id,
        "episode_id": episode_id,
        "recording_root": str(recording_root),
        "episode_directory": str(episode_dir),
        "checks": checks.items,
        "requests": log.items,
        "limitations": {},
        "not_proven": [
            "any physical sensor measurement or human demonstration",
            "cross-stream synchronization",
            "M1 acceptance or production deployment",
        ],
    }

    writer_checks = phase1.get("checks") or {}
    checks.add("the frozen generator reported every writer check passed",
               bool(writer_checks) and all(writer_checks.values()), writer_checks)
    checks.add("the frozen generator shut its mock native writer down",
               phase1.get("writer_process_alive_after_shutdown") is False,
               phase1.get("writer_process_alive_after_shutdown"))
    checks.add("no mock writer is listening on the recorded native port",
               port_is_closed("127.0.0.1", args.native_port), {"port": args.native_port})
    counts = phase1.get("event_type_counts") or {}
    samples = phase1.get("samples") or []
    persist_rows = phase1.get("persist_rows") or []
    ticks = phase1.get("ticks") or []
    checks.add("the writer recorded at least two paired RGB/depth samples on disk",
               len(samples) >= 2 and len(persist_rows) == len(samples),
               {"samples": len(samples), "persist_rows": len(persist_rows)})
    checks.add("the writer emitted feedback and actuator references for every tick",
               counts.get("feedback") == len(ticks) and counts.get("actuator_reference") == len(ticks),
               {"ticks": len(ticks), "feedback": counts.get("feedback"),
                "actuator_reference": counts.get("actuator_reference")})
    checks.add("the writer emitted one capture-timing record per sample",
               counts.get("rgbd_capture_timing") == len(samples),
               {"samples": len(samples), "rgbd_capture_timing": counts.get("rgbd_capture_timing")})
    checks.add("the writer recorded one Episode terminal event",
               counts.get("episode_terminal") == 1, counts.get("episode_terminal"))
    checks.add("the Episode tail exists and matches the end receipt",
               phase1.get("episode_complete_matches_receipt") is True,
               phase1.get("episode_complete_matches_receipt"))
    checks.add("the recording tree contains the Episode and persist anchors",
               episode_dir.is_dir() and (episode_dir / "observations" / "persist.jsonl").is_file(),
               {"episode_dir": str(episode_dir)})
    media_expected = {}
    for sample in samples:
        for kind, key in (("rgb", "rgb_uri"), ("depth", "depth_uri")):
            row = next(item for item in persist_rows if item["sample_id"] == sample["sample_id"])
            relative = row[key]
            path = episode_dir / relative
            expected = sample[f"{kind}_sha256"]
            media_expected[relative] = expected
            checks.add(f"{sample['sample_id']} {kind} file exists with the injected bytes",
                       path.is_file() and sha256_file(path) == expected,
                       {"path": relative, "expected": expected,
                        "actual": sha256_file(path) if path.is_file() else None})
    declared = phase1.get("declared_by_writer") or {}
    evidence["writer_self_report"] = {
        "declared_sensor_streams": declared.get("sensor_streams"),
        "declared_source": declared.get("source"),
        "test_expected_streams": phase1.get("test_expected_streams"),
        "test_expected_streams_are_not_a_manifest_fact": phase1.get(
            "test_expected_streams_are_not_a_manifest_fact"),
        "manifest": phase1.get("manifest"),
    }
    manifest = phase1.get("manifest") or {}
    declared_stream_fields = {key: value for key, value in manifest.items()
                              if "stream" in key.lower() or "sensor" in key.lower()}
    evidence["required_streams"] = {
        "writer_declaration": declared.get("sensor_streams"),
        "test_expectation_only": phase1.get("test_expected_streams"),
        "manifest_declared_stream_fields": declared_stream_fields,
        "status": "unknown" if not declared_stream_fields else "declared",
        "note": "test expectations are not written into the manifest; no Episode-level required-stream set is invented",
    }

    before = inventory(recording_root)
    evidence["digest_before"] = {"file_count": len(before), "aggregate": inventory_digest(before),
                                 "episode_files": {path: item for path, item in before.items()
                                                   if path.startswith(f"{run_id}/episodes/{episode_id}/")}}
    write_source_args = argparse.Namespace(
        recording_root=recording_root, source_id=f"testonly-new-recording-{run_id}",
        native_release_id=Path(phase1.get("native_release", "test-only-native")).name,
        native_url=f"http://127.0.0.1:{args.native_port}", out=args.history_source_out)
    write_source(write_source_args)

    reader = None
    missing_reader = None
    try:
        application, reader_manifest = build_reader_app(
            args.recipe_body, f"http://127.0.0.1:{args.native_port}", args.history_source_out,
            recording_root, args.draft_db, args.reader_port, args.reader_manifest, "reader-new-recording")
        evidence["reader"] = reader_manifest
        if args.expected_platform_source:
            expected = json.loads(Path(args.expected_platform_source).read_text(encoding="utf-8"))
            recorded = expected.get("platform_source") or {}
            actual = reader_manifest["platform_source"]
            checks.add("the reader runs the frozen platform source recorded by the startup manifest",
                       recorded.get("aggregate") == actual.get("aggregate")
                       and recorded.get("file_count") == actual.get("file_count"),
                       {"recorded_aggregate": recorded.get("aggregate"),
                        "actual_aggregate": actual.get("aggregate"),
                        "recorded_files": recorded.get("file_count"), "actual_files": actual.get("file_count")})
        reader = ReaderServer(application, args.reader_port)
        reader.start()
        base = f"http://127.0.0.1:{args.reader_port}"
        wait_for(lambda: log.get_json(base, "/api/v1/episodes?limit=1")[0] == 200,
                 timeout=30, what="the test reader")

        status, listing = log.get_json(base, "/api/v1/episodes?limit=50")
        entries = listing.get("episodes", []) if isinstance(listing, dict) else []
        entry = next((item for item in entries if item.get("run_id") == run_id
                      and item.get("episode_id") == episode_id), None)
        checks.add("the reader list returns the new Episode", status == 200 and entry is not None,
                   {"status": status, "run_id": run_id, "episode_id": episode_id,
                    "listed": len(entries)})
        checks.add("the list marks the new Episode readable and COMPLETE",
                   bool(entry) and entry.get("readable") is True
                   and (entry.get("declared") or {}).get("recording_status") == "COMPLETE",
                   {"readable": (entry or {}).get("readable"),
                    "declared": (entry or {}).get("declared")})
        checks.add("the list source is the test-only source, not the production archive",
                   listing.get("source", {}).get("source_id") == f"testonly-new-recording-{run_id}",
                   listing.get("source", {}).get("source_id"))

        status, detail = log.get_json(base, f"/api/v1/episodes/{episode_id}?run_id={run_id}")
        identity = detail.get("identity", {}) if isinstance(detail, dict) else {}
        declared_detail = detail.get("declared", {}) if isinstance(detail, dict) else {}
        checks.add("the reader detail keeps the new run/episode identity",
                   status == 200 and identity.get("run_id") == run_id
                   and identity.get("episode_id") == episode_id
                   and identity.get("recording_root_resolved") == str(recording_root),
                   {"status": status, "identity_run": identity.get("run_id"),
                    "identity_episode": identity.get("episode_id"),
                    "recording_root_resolved": identity.get("recording_root_resolved")})
        checks.add("the detail reads the Episode and tail declarations",
                   declared_detail.get("episode_json_readable") is True
                   and declared_detail.get("tail_json_readable") is True
                   and declared_detail.get("complete_tail_file_present") is True,
                   {key: declared_detail.get(key) for key in
                    ("episode_json_readable", "tail_json_readable", "complete_tail_file_present")})
        integrity = detail.get("integrity", {}) if isinstance(detail, dict) else {}
        evidence["integrity"] = integrity
        evidence["declared_detail"] = declared_detail
        evidence["recorded_model_identity"] = detail.get("recorded_model_identity") if isinstance(detail, dict) else None
        evidence["three_d_replay"] = detail.get("three_d_replay") if isinstance(detail, dict) else None
        evidence["media_summary"] = detail.get("media_summary") if isinstance(detail, dict) else None

        status, streams = log.get_json(base, f"/api/v1/episodes/{episode_id}/streams?run_id={run_id}")
        stream_entries = {item.get("stream_id"): item for item in streams.get("streams", [])} \
            if isinstance(streams, dict) else {}
        expected_streams = {"events": sum(counts.values()),
                            "observations-index": phase1.get("index_rows"),
                            "observations-persist": len(persist_rows),
                            "transforms": len(samples)}
        stream_ok = status == 200 and all(
            stream_entries.get(name, {}).get("available") is True
            and stream_entries.get(name, {}).get("records") == expected
            for name, expected in expected_streams.items())
        checks.add("the stream catalogue lists and counts every written stream",
                   stream_ok, {"status": status,
                               "expected": expected_streams,
                               "actual": {name: {key: stream_entries.get(name, {}).get(key)
                                                 for key in ("available", "records")}
                                          for name in expected_streams}})

        status, events_page = log.get_json(
            base, f"/api/v1/episodes/{episode_id}/streams/events/records?run_id={run_id}&limit=200")
        event_records = events_page.get("records", []) if isinstance(events_page, dict) else []
        event_types: dict[str, int] = {}
        for item in event_records:
            record = item.get("record", {})
            event_types[record.get("event_type")] = event_types.get(record.get("event_type"), 0) + 1
        checks.add("bounded event records return every written event with its line position",
                   status == 200 and len(event_records) == sum(counts.values())
                   and all(isinstance(item.get("line_index"), int) for item in event_records),
                   {"status": status, "records": len(event_records),
                    "writer": sum(counts.values())})
        checks.add("the reader reads the same event vocabulary as the writer",
                   event_types == counts, {"reader": event_types, "writer": counts})

        status, persist_page = log.get_json(
            base, f"/api/v1/episodes/{episode_id}/streams/observations-persist/records?run_id={run_id}&limit=50")
        persist_records = persist_page.get("records", []) if isinstance(persist_page, dict) else []
        persist_compare = _compare_records(
            persist_records, persist_rows,
            ("run_id", "episode_id", "stream_id", "sample_id", "persist_sequence",
             "persist_backend_monotonic_s", "capture_backend_monotonic_s", "capture_sim_time_s",
             "rgb_uri", "depth_uri"))
        checks.add("bounded persist records match the writer row for row",
                   status == 200 and persist_compare["counts"] == [len(persist_rows), len(persist_rows)]
                   and not persist_compare["mismatches"], persist_compare)

        status, transforms_page = log.get_json(
            base, f"/api/v1/episodes/{episode_id}/streams/transforms/records?run_id={run_id}&limit=50")
        transforms = transforms_page.get("records", []) if isinstance(transforms_page, dict) else []
        transform_samples = {item.get("record", {}).get("sample_id") for item in transforms}
        checks.add("bounded transform records reach every sample by sample_id",
                   status == 200 and transform_samples == {item["sample_id"] for item in samples},
                   {"status": status, "samples": sorted(transform_samples)})

        status, frames = log.get_json(
            base, f"/api/v1/episodes/{episode_id}/frames?run_id={run_id}&limit=10&include_time_quality=true"
                  "&include_action_basis=true")
        frame_items = frames.get("frames", []) if isinstance(frames, dict) else []
        checks.add("the reader returns both new frames in append order",
                   status == 200 and [item.get("sample_id") for item in frame_items]
                   == [item["sample_id"] for item in samples],
                   {"status": status, "sample_ids": [item.get("sample_id") for item in frame_items]})
        role_state = {}
        for frame in frame_items:
            roles = {item.get("role"): item for item in frame.get("roles", [])}
            role_state[frame.get("sample_id")] = {
                "linkage_status": frame.get("linkage_status"),
                "roles": {name: {"candidate_records": roles.get(name, {}).get("candidate_records"),
                                 "matched_records": roles.get(name, {}).get("matched_records")}
                          for name in PRIMARY_ROLES + ("feedback_observation_row",)},
                "anchor": frame.get("anchor"),
            }
        checks.add("every frame matches image rows, transform, capture timing and state by recorded keys",
                   all(state["linkage_status"] == "matched"
                       and state["roles"]["image_observation"]["matched_records"] == 2
                       and state["roles"]["image_observation"]["candidate_records"] == 2
                       and state["roles"]["camera_transform"]["matched_records"] == 1
                       and state["roles"]["capture_timing_event"]["matched_records"] == 1
                       and state["roles"]["state_feedback_event"]["matched_records"] == 1
                       for state in role_state.values()), role_state)
        checks.add("each frame carries the writer's sample id and capture tick",
                   all(frame.get("sample_id") == sample["sample_id"]
                       and (frame.get("anchor", {}).get("reference_keys") or {}).get("capture_control_tick_id")
                       == sample["capture_control_tick_id"]
                       for frame, sample in zip(frame_items, samples)),
                   [{"sample_id": item.get("sample_id"),
                     "tick": (item.get("anchor", {}).get("reference_keys") or {}).get("capture_control_tick_id")}
                    for item in frame_items])
        evidence["frame_roles"] = role_state

        tq = frames.get("time_quality") or {}
        coverage = tq.get("coverage") or {}
        checks.add("time quality scanned to EOF and decided every anchor line",
                   coverage.get("reached_end_of_file") is True
                   and (coverage.get("line_accounting") or {}).get("every_line_of_the_anchor_file_is_decided") is True
                   and (coverage.get("line_accounting") or {}).get("undecidable_total") == 0
                   and coverage.get("anchors_in_this_scan") == len(samples)
                   and coverage.get("covers_whole_episode") is True,
                   {"reached_end_of_file": coverage.get("reached_end_of_file"),
                    "line_accounting": coverage.get("line_accounting"),
                    "anchors_in_this_scan": coverage.get("anchors_in_this_scan"),
                    "covers_whole_episode": coverage.get("covers_whole_episode")})
        eligibility = tq.get("playback_eligibility") or {}
        checks.add("append-order display stays eligible and every base satisfies whole-Episode timing",
                   (eligibility.get("append_order_display") or {}).get("eligible") is True
                   and (eligibility.get("append_order_display") or {}).get(
                       "displayed_sequence_may_have_gaps") is False
                   and all((eligibility.get("recorded_interval_schedule", {})
                            .get("eligible_by_base", {}).get(base, {})
                            .get("eligible_for_whole_episode")) is True for base in TIME_BASES),
                   {"append": eligibility.get("append_order_display"),
                    "by_base": {base: (eligibility.get("recorded_interval_schedule", {})
                                       .get("eligible_by_base", {}).get(base))
                                for base in TIME_BASES}})
        base_values = {}
        for time_base in TIME_BASES:
            entry_base = (tq.get("time_bases") or {}).get(time_base) or {}
            base_values[time_base] = {
                "numeric_count": entry_base.get("numeric_count"),
                "missing_count": entry_base.get("missing_count"),
                "non_numeric_count": entry_base.get("non_numeric_count"),
                "first_in_file_order": entry_base.get("first_in_file_order"),
                "last_in_file_order": entry_base.get("last_in_file_order"),
            }
        checks.add("each capture base exposes exactly the written numeric anchors",
                   all(base_values[base]["numeric_count"] == len(samples)
                       and base_values[base]["missing_count"] == 0
                       and base_values[base]["non_numeric_count"] == 0 for base in TIME_BASES),
                   base_values)
        ordered = sorted(persist_rows, key=lambda row: row["persist_sequence"])
        checks.add("the reader's first/last values are the writer's own values",
                   all(base_values[base]["first_in_file_order"] == ordered[0].get(base)
                       and base_values[base]["last_in_file_order"] == ordered[-1].get(base)
                       for base in TIME_BASES),
                   {base: {"reader_first": base_values[base]["first_in_file_order"],
                           "writer_first": ordered[0].get(base),
                           "reader_last": base_values[base]["last_in_file_order"],
                           "writer_last": ordered[-1].get(base)} for base in TIME_BASES})
        evidence["time_quality"] = {"coverage": coverage, "time_bases": base_values,
                                    "playback_eligibility": eligibility}

        action = frames.get("action_basis") or {}
        categories = action.get("categories") or {}
        reader_counts = {name: categories.get(name, {}).get("counts", {}) for name in categories}
        checks.add("action basis accounts for every written event type",
                   sum(sum(item.values()) for item in reader_counts.values()) == sum(counts.values())
                   and all((categories.get(name, {}).get("status") == "observed")
                           for name in ("actual_state_feedback", "recorded_target", "capture_timing",
                                        "episode_lifecycle")),
                   {"categories": {name: categories.get(name) for name in
                                   ("actual_state_feedback", "recorded_target", "capture_timing",
                                    "episode_lifecycle", "command_intent", "command_receipt_rejected",
                                    "command_dispatched", "lease_boundary")}})
        association = action.get("frame_association") or {}
        by_type = association.get("by_event_type") or {}
        checks.add("per-frame association lists exactly one actual and one target candidate",
                   all(by_type.get(name, {}).get("candidate_count_per_frame_on_this_page", {}).get("1")
                       == len(samples) for name in ("feedback", "actuator_reference"))
                   and not association.get("ambiguous_candidates"),
                   by_type)
        rules = association.get("rules") or {}
        checks.add("the action rules keep rejection, Target and clock parity in separate domains",
                   all(key in rules for key in ("rejected_requests", "recorded_target", "clock_parity"))
                   and "never" in str(rules.get("clock_parity")),
                   {key: rules.get(key) for key in ("rejected_requests", "recorded_target", "clock_parity")})
        control_source = action.get("control_source") or {}
        observed_sources = json.dumps(control_source.get("fields_observed") or {})
        checks.add("the absent command control source is not defaulted to Human",
                   control_source.get("status") in {"not_recorded_in_this_scan",
                                                    "recorded_only_inside_payload_fields"}
                   and (not control_source.get("operator_default")
                        or control_source.get("operator_default") != "human")
                   and ('"human"' not in observed_sources.lower()),
                   control_source)
        checks.add("action basis scanned the same event stream to EOF",
                   (action.get("scope") or {}).get("records_scanned") == sum(counts.values())
                   and (action.get("scope") or {}).get("reached_end_of_file") is True,
                   action.get("scope"))
        evidence["action_basis"] = {
            "scope": action.get("scope"),
            "categories": {name: categories.get(name) for name in categories},
            "frame_association": association,
            "control_source": control_source,
            "command_chain": action.get("command_chain"),
            "independent_tracks": action.get("independent_tracks"),
            "not_proven": action.get("not_proven"),
        }

        asset_checks = []
        for sample in samples:
            row = next(item for item in persist_rows if item["sample_id"] == sample["sample_id"])
            for kind, key in (("rgb", "rgb_uri"), ("depth", "depth_uri")):
                relative = row[key]
                status, body, headers = log.get_bytes(
                    base, f"/api/v1/episodes/{episode_id}/assets/{relative}?run_id={run_id}")
                digest = sha256_bytes(body)
                good = (status == 200 and digest == sample[f"{kind}_sha256"]
                        and headers.get("x-episode-asset-sha256") == digest)
                asset_checks.append({"sample_id": sample["sample_id"], "kind": kind, "uri": relative,
                                     "status": status, "digest": digest,
                                     "expected": sample[f"{kind}_sha256"], "passed": good})
                status_wrong, wrong_doc, _ = log.get_bytes(
                    base, f"/api/v1/episodes/{episode_id}/assets/{relative}?run_id={run_id}&sha256={'0' * 64}")
                asset_checks.append({"sample_id": sample["sample_id"], "kind": kind,
                                     "wrong_digest_status": status_wrong,
                                     "wrong_digest_code": (wrong_doc.get("detail", {}) or {}).get("code")
                                     if isinstance(wrong_doc, dict) else None})
        checks.add("every media asset is served with the writer's bytes and digest",
                   all(item.get("passed") for item in asset_checks if "passed" in item), asset_checks)
        checks.add("a requested digest that does not match is refused",
                   all(item.get("wrong_digest_status") == 409 for item in asset_checks
                       if "wrong_digest_status" in item), asset_checks)
        evidence["media"] = asset_checks

        status, scene = log.get_json(base, "/api/v1/mobilecar/scene")
        evidence["limitations"]["live_native_scene"] = {
            "status": status,
            "code": (scene.get("detail", {}) or {}).get("code") if isinstance(scene, dict) else None,
            "meaning": "the writer is stopped; history reads do not need the live native scene",
        }
        checks.add("history reads continue while the mock writer is stopped",
                   status != 200, {"scene_status": status})
        status, pose = log.get_json(base, f"/api/v1/episodes/{episode_id}/robot-state?run_id={run_id}")
        evidence["limitations"]["robot_state"] = {
            "status": status,
            "code": (pose.get("detail", {}) or {}).get("code") if isinstance(pose, dict) else None,
            "meaning": "no geometry bundle was configured; no online geometry is substituted",
        }
        checks.add("no geometry bundle means a stated refusal, not a substituted online tree",
                   status == 503 and (pose.get("detail", {}) or {}).get("code") == "history_model_bundle_not_configured",
                   {"status": status, "code": (pose.get("detail", {}) or {}).get("code")})

        after = inventory(recording_root)
        evidence["digest_after"] = {"file_count": len(after), "aggregate": inventory_digest(after),
                                    "episode_files": {path: item for path, item in after.items()
                                                      if path.startswith(f"{run_id}/episodes/{episode_id}/")}}
        checks.add("the read pass leaves the recording tree byte-identical",
                   inventory_digest(before) == inventory_digest(after),
                   {"before": inventory_digest(before), "after": inventory_digest(after),
                    "added": sorted(set(after) - set(before)),
                    "removed": sorted(set(before) - set(after))})
        checks.add("every reader request was a GET",
                   all(item["method"] == "GET" for item in log.items),
                   {"count": len(log.items), "methods": sorted({item["method"] for item in log.items})})

        if args.missing_media_root:
            missing_root = Path(args.missing_media_root).expanduser().resolve()
            if missing_root.exists():
                shutil.rmtree(missing_root)
            missing_root.mkdir(parents=True)
            shutil.copytree(run_dir, missing_root / run_id)
            deleted_relative = next(item for item in persist_rows
                                    if item["sample_id"] == samples[0]["sample_id"])["depth_uri"]
            deleted_path = missing_root / run_id / "episodes" / episode_id / deleted_relative
            deleted_sha = sha256_file(deleted_path)
            deleted_path.unlink()
            missing_source = missing_root / "history-source-testonly.json"
            write_source(argparse.Namespace(
                recording_root=missing_root, source_id=f"testonly-missing-media-{run_id}",
                native_release_id=Path(phase1.get("native_release", "test-only-native")).name,
                native_url=f"http://127.0.0.1:{args.native_port}", out=missing_source))
            missing_application, missing_manifest = build_reader_app(
                args.recipe_body, f"http://127.0.0.1:{args.native_port}", missing_source,
                missing_root, args.missing_media_draft_db, args.missing_media_port,
                args.missing_media_manifest, "reader-missing-media-copy")
            missing_reader = ReaderServer(missing_application, args.missing_media_port)
            missing_reader.start()
            missing_base = f"http://127.0.0.1:{args.missing_media_port}"
            wait_for(lambda: log.get_json(missing_base, "/api/v1/episodes?limit=1")[0] == 200,
                     timeout=30, what="the missing-media reader")
            status, copy_detail = log.get_json(
                missing_base, f"/api/v1/episodes/{episode_id}?run_id={run_id}")
            status_asset, copy_asset = log.get_json(
                missing_base, f"/api/v1/episodes/{episode_id}/assets/{deleted_relative}?run_id={run_id}")
            status_frames, copy_frames = log.get_json(
                missing_base, f"/api/v1/episodes/{episode_id}/frames?run_id={run_id}&limit=10")
            copy_frame = next((item for item in copy_frames.get("frames", [])
                               if item.get("sample_id") == samples[0]["sample_id"]), {})
            copy_depth = next((item for item in copy_frame.get("media", {}).get("items", [])
                               if item.get("field") == "depth_uri"), {})
            checks.add("a missing media file is diagnosed, not invented",
                       status_asset == 404
                       and (copy_asset.get("detail", {}) or {}).get("code") == "episode_asset_missing"
                       and copy_depth.get("availability") in {"absent", "refused"},
                       {"asset_status": status_asset,
                        "asset_code": (copy_asset.get("detail", {}) or {}).get("code"),
                        "frame_media_availability": copy_depth.get("availability")})
            checks.add("the missing-media copy is still readable as a record, with its loss visible",
                       status == 200 and status_frames == 200
                       and copy_detail.get("declared", {}).get("complete_tail_file_present") is True,
                       {"detail_status": status, "frames_status": status_frames,
                        "declared": copy_detail.get("declared")})
            evidence["missing_media"] = {
                "classification": "isolated copy; the successful recording root was not modified",
                "copy_root": str(missing_root), "deleted_relative_path": deleted_relative,
                "deleted_sha256": deleted_sha, "reader_manifest": missing_manifest,
                "detail_status": status, "asset_status": status_asset,
                "asset_code": (copy_asset.get("detail", {}) or {}).get("code"),
                "frame_media_availability": copy_depth.get("availability"),
                "declared": copy_detail.get("declared"),
                "integrity": copy_detail.get("integrity"),
            }
            missing_before = inventory(missing_root)
            missing_reader.stop()
            missing_reader = None
            missing_after = inventory(missing_root)
            checks.add("reading the missing-media copy does not rewrite it",
                       inventory_digest(missing_before) == inventory_digest(missing_after),
                       {"before": inventory_digest(missing_before), "after": inventory_digest(missing_after)})
    finally:
        if reader is not None:
            reader.stop()
        if missing_reader is not None:
            missing_reader.stop()

    digest_check = next(
        (item for item in evidence["checks"]
         if item["name"] == "the read pass leaves the recording tree byte-identical"), None)
    evidence["digest"] = {
        "before": evidence.pop("digest_before"),
        "after": evidence.pop("digest_after"),
        "equal": bool(digest_check and digest_check["passed"]),
    }
    evidence["writer_self_report"]["persist_rows_written"] = len(persist_rows)
    evidence["writer_self_report"]["samples_written"] = len(samples)
    evidence["writer_self_report"]["event_type_counts"] = counts
    evidence["post_run"] = {
        "native_port_closed_after_reader": port_is_closed("127.0.0.1", args.native_port),
        "reader_port_closed_after_shutdown": port_is_closed("127.0.0.1", args.reader_port),
        "missing_media_port_closed_after_shutdown": port_is_closed("127.0.0.1", args.missing_media_port)
        if args.missing_media_root else None,
    }
    checks.add("the reader and missing-media reader are stopped after the read pass",
               port_is_closed("127.0.0.1", args.reader_port)
               and (not args.missing_media_root or port_is_closed("127.0.0.1", args.missing_media_port)),
               evidence["post_run"])
    evidence["passed"] = len(checks.items) - len(checks.failed)
    evidence["total"] = len(checks.items)
    evidence["failed"] = [item["name"] for item in checks.failed]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": run_id, "episode_id": episode_id,
                      "passed": evidence["passed"], "total": evidence["total"],
                      "failed": evidence["failed"], "out": str(args.out)}))
    return 0 if not checks.failed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    recipe = sub.add_parser("build-recipe", help="build the test-only recipe from a live mock native")
    recipe.add_argument("--native-url", required=True)
    recipe.add_argument("--out", required=True, type=Path)
    recipe.set_defaults(func=build_recipe)

    source = sub.add_parser("write-source", help="write a test-only history source declaration")
    source.add_argument("--recording-root", required=True, type=Path)
    source.add_argument("--source-id", required=True)
    source.add_argument("--native-release-id", required=True)
    source.add_argument("--native-url", required=True)
    source.add_argument("--out", required=True, type=Path)
    source.set_defaults(func=write_source)

    server = sub.add_parser("serve", help="serve the test-only platform app over real HTTP")
    server.add_argument("--recipe-body", required=True, type=Path)
    server.add_argument("--native-url", required=True)
    server.add_argument("--history-source", required=True, type=Path)
    server.add_argument("--episode-root", required=True, type=Path)
    server.add_argument("--draft-db", required=True, type=Path)
    server.add_argument("--port", required=True, type=int)
    server.add_argument("--out-manifest", required=True, type=Path)
    server.add_argument("--label", default="test-only-platform")
    server.set_defaults(func=serve)

    check = sub.add_parser("verify", help="reload the new recording through the platform reader")
    check.add_argument("--phase1", required=True, type=Path)
    check.add_argument("--recording-root", required=True, type=Path)
    check.add_argument("--recipe-body", required=True, type=Path)
    check.add_argument("--draft-db", required=True, type=Path)
    check.add_argument("--reader-port", required=True, type=int)
    check.add_argument("--native-port", required=True, type=int)
    check.add_argument("--history-source-out", required=True, type=Path)
    check.add_argument("--reader-manifest", required=True, type=Path)
    check.add_argument("--out", required=True, type=Path)
    check.add_argument("--expected-platform-source", type=Path, default=None)
    check.add_argument("--missing-media-root", type=Path, default=None)
    check.add_argument("--missing-media-draft-db", type=Path, default=None)
    check.add_argument("--missing-media-port", type=int, default=None)
    check.add_argument("--missing-media-manifest", type=Path, default=None)
    check.set_defaults(func=verify)

    args = parser.parse_args()
    if args.command == "verify":
        if args.missing_media_root is not None:
            if args.missing_media_draft_db is None or args.missing_media_port is None \
                    or args.missing_media_manifest is None:
                parser.error("missing-media-root needs --missing-media-draft-db, --missing-media-port "
                             "and --missing-media-manifest")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
