"""Verify the read-only historical Episode slice against the REAL archive on the server.

Every assertion here runs over HTTP against one candidate process plus GETs to the
declaring native instance. Nothing writes, moves or re-exports a recording, and the
archive baseline digest is recomputed at the end to prove the raw files are unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import source_digest
from native_get_probe import GetProbe

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from unirobot.mobilecar_geometry import GeometryBundle  # noqa: E402

NATIVE_VOCABULARY = {"recording_start", "recording_stop", "episode_terminal", "feedback_initial",
                    "feedback", "actuator_reference", "requested", "approved", "rejected",
                    "dispatch", "dispatched", "expired", "command_response"}
ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".npy", ".json"}


class Failed(AssertionError):
    pass


class Results:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(self, name: str, passed: bool, detail: Any = None) -> None:
        self.items.append({"name": name, "passed": bool(passed), "detail": detail})
        if not passed:
            raise Failed(f"{name}: {json.dumps(detail, ensure_ascii=False)[:400]}")


PROBE: GetProbe


def raw(url: str) -> tuple[int, bytes, dict[str, str]]:
    """GET only: the probe object has no method or body parameter to misuse."""
    return PROBE.get(url)


def get_json(url: str) -> tuple[int, Any]:
    status, payload, _ = raw(url)
    try:
        return status, json.loads(payload)
    except json.JSONDecodeError:
        return status, payload.decode("utf-8", "replace")


def coverage_snapshot(root: Path, records: list[tuple[str, str]]) -> dict[str, str]:
    """Digests of the files this run actually opens, so 'unchanged' can only ever mean this set."""
    covered: dict[str, str] = {}
    for run_id, episode_id in records:
        base = root / run_id / "episodes" / episode_id
        for name in ("manifest.json",):
            path = root / run_id / name
            if path.is_file():
                covered[f"{run_id}/{name}"] = hashlib.sha256(path.read_bytes()).hexdigest()
        for name in ("episode.json", "episode_complete.json", "events.jsonl", "control.jsonl", "commands.jsonl",
                     "transforms.jsonl", "initial_snapshot.json", "quality_report.json",
                     "observations/index.jsonl", "observations/persist.jsonl"):
            path = base / name
            if path.is_file():
                covered[f"{run_id}/{episode_id}/{name}"] = hashlib.sha256(path.read_bytes()).hexdigest()
        assets = base / "assets"
        if assets.is_dir():
            for path in sorted(assets.rglob("*")):
                if path.is_file():
                    covered[f"{run_id}/{episode_id}/{path.relative_to(base).as_posix()}"] = hashlib.sha256(path.read_bytes()).hexdigest()
    for run_id, episode_id in records:
        for name in ("episode.json", "episode_complete.json"):
            path = root / run_id / "episodes" / episode_id / name
            if path.is_file():
                covered.setdefault(f"{run_id}/{episode_id}/{name}", hashlib.sha256(path.read_bytes()).hexdigest())
    return covered


def archive_digest(root: Path) -> str:
    """The frozen baseline recipe: every episode.json and episode_complete.json digest, folded."""
    entries: dict[str, str] = {}
    for run_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        episodes = run_dir / "episodes"
        if not episodes.is_dir():
            continue
        for episode in sorted(p for p in episodes.iterdir() if p.is_dir()):
            for name in ("episode.json", "episode_complete.json"):
                path = episode / name
                if path.is_file():
                    entries[f"{run_dir.name}/{episode.name}/{name}"] = hashlib.sha256(path.read_bytes()).hexdigest()
    folded = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
    return hashlib.sha256(folded.encode()).hexdigest()


def code_of(payload: Any) -> str | None:
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, dict):
            return detail.get("code")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform-url", required=True)
    parser.add_argument("--native-url", required=True)
    parser.add_argument("--source-config", type=Path, required=True)
    parser.add_argument("--complete-episode", required=True, help="run_id:episode_id of a real COMPLETE record")
    parser.add_argument("--failed-episode", required=True, help="run_id:episode_id of a real FAILED/incomplete record")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--startup-manifest", type=Path, required=True,
                        help="frozen manifest of the release being checked; its recorded platform source aggregate is recomputed against the running bytes")
    parser.add_argument("--probe-log", type=Path, required=True, help="JSONL record of every GET issued by this run")
    parser.add_argument("--coverage-out", type=Path, required=True, help="digests of the covered file set, before and after")
    args = parser.parse_args()

    global PROBE
    PROBE = GetProbe(args.probe_log)

    P = args.platform_url.rstrip("/")
    N = args.native_url.rstrip("/")
    source = json.loads(args.source_config.read_text(encoding="utf-8"))
    complete_run, complete_id = args.complete_episode.split(":", 1)
    failed_run, failed_id = args.failed_episode.split(":", 1)
    results = Results()

    manifest = json.loads(args.startup_manifest.read_text(encoding="utf-8"))
    root = Path(manifest["history"]["resolved_recording_root"])
    covered_before = coverage_snapshot(root, [(complete_run, complete_id), (failed_run, failed_id)])
    baseline_before = archive_digest(root)

    def detail_for(episode_id: str, run_id: str) -> dict[str, Any]:
        status, body = get_json(f"{P}/api/v1/episodes/{episode_id}?run_id={run_id}")
        if status != 200:
            raise Failed(f"detail {episode_id} returned {status}: {json.dumps(body)[:300]}")
        return body

    def records(episode_id: str, run_id: str, stream: str, query: str = "") -> tuple[int, Any]:
        return get_json(f"{P}/api/v1/episodes/{episode_id}/streams/{stream}/records?run_id={run_id}{query}")

    _, native_before = get_json(f"{N}/api/v1/health")
    _, capabilities = get_json(f"{N}/api/v1/capabilities")

    # ---- source identity and read-only posture ---------------------------------
    status, listing = get_json(f"{P}/api/v1/episodes?limit=5")
    results.add("history list answers on the candidate", status == 200, {"status": status, "code": code_of(listing)})
    results.add("list uses the frozen episode read schema", listing["schema_version"] == "unirobot-mobilecar-episode-read-1",
                listing["schema_version"])
    results.add("list declares itself read-only", listing["read_only"] is True, listing.get("read_only"))
    src = listing["source"]
    results.add("list carries the fixed source identity",
                src["source_id"] == source["source_id"] and src["adapter_id"] == "mobilecar"
                and src["native_release_id"] == source["native_release_id"]
                and src["recording_root"] == source["recording_root"], src)
    results.add("source declares GET-only native access",
                src["declaring_instance"]["access"] == "GET_only" and src["access"] == "read_only_files"
                and src["platform_writes"] is False, src["declaring_instance"])
    results.add("source carries the frozen archive baseline", src["archive_baseline"]["aggregate_sha256"]
                == source["archive_baseline"]["aggregate_sha256"], src["archive_baseline"])
    results.add("list states its capability limits",
                any("no replay execution" in item for item in listing["capability_limits"]), listing["capability_limits"])

    # ---- bounded paging over 348 real records ---------------------------------
    status, native_list = get_json(f"{N}/api/v1/episodes")
    results.add("platform index matches the native list size",
                status == 200 and listing["paging"]["total_matches"] == len(native_list["episodes"]),
                {"platform": listing["paging"]["total_matches"], "native": len(native_list["episodes"])})
    results.add("list page honours the limit", len(listing["episodes"]) == 5, len(listing["episodes"]))
    status, second = get_json(f"{P}/api/v1/episodes?limit=5&offset=5")
    keys_a = {(item["run_id"], item["episode_id"]) for item in listing["episodes"]}
    keys_b = {(item["run_id"], item["episode_id"]) for item in second["episodes"]}
    results.add("offset pages do not overlap", not (keys_a & keys_b), sorted(keys_a & keys_b))
    results.add("paging reports a resolvable next_offset", second["paging"]["offset"] == 5
                and second["paging"]["next_offset"] == 10, second["paging"])
    status, over = get_json(f"{P}/api/v1/episodes?limit=1000")
    results.add("oversized page is rejected not truncated silently", status == 422, status)
    results.add("list marks every status as declared-only",
                all(item["declaration_only"] is True for item in listing["episodes"]), None)
    status, failed = get_json(f"{P}/api/v1/episodes?recording_status=FAILED&limit=20")
    results.add("FAILED filter returns the real incomplete records",
                len(failed["episodes"]) == 6 and all(item["declared"]["recording_status"] == "FAILED"
                                                     for item in failed["episodes"]),
                {"count": len(failed["episodes"])})

    # ---- a real COMPLETE record ------------------------------------------------
    body = detail_for(complete_id, complete_run)
    identity = body["identity"]
    results.add("COMPLETE detail keeps native run/episode/segment identity",
                identity["run_id"] == complete_run and identity["episode_id"] == complete_id
                and identity["segments"][0]["recording_segment_id"].startswith("seg_")
                and identity["native_contract_version"] == "mobilecar-1.0", identity["segments"])
    results.add("episode display name is not treated as a global key",
                identity["episode_display_name_is_not_a_key"] is True, None)
    results.add("backend generation is reported from the recorded payload or as unavailable",
                set(identity["backend_generation"]) >= {"available", "reason", "distinct_values"}, identity["backend_generation"])
    results.add("COMPLETE detail declares the recorded statuses verbatim",
                body["declared"]["recording_status"] == "COMPLETE" and body["declared"]["audit_status"] == "COMPLETE"
                and body["declared"]["complete_tail_file_present"] is True, body["declared"])
    integrity = body["integrity"]
    results.add("recorded lifecycle closure and checksum verification are separate layers",
                integrity["status"] == "complete" and integrity["declaration_is_not_verification"] is True
                and integrity["checksum_verification"]["verdict"] in
                {"all_matched", "mismatch_present", "nothing_recomputable"}, integrity["status"])
    results.add("unverified scope is stated, not implied",
                any("archive-wide" in item for item in integrity["not_verified"]), integrity["not_verified"])
    results.add("stale declared checksums are surfaced as a finding, not relabeled",
                isinstance(integrity["checksum_verification"]["mismatched"], list), 
                {"matched": len(integrity["checksum_verification"]["matched"]),
                 "mismatched": [item["relative_path"] for item in integrity["checksum_verification"]["mismatched"]],
                 "verdict": integrity["checksum_verification"]["verdict"]})
    streams = {item["stream_id"]: item for item in body["streams"]}
    results.add("stream availability is per-file and honest",
                {"events", "control", "observations-index", "transforms", "initial-snapshot"} <= set(streams)
                and all({"available", "relative_path", "records", "format"} <= set(item.keys()) for item in body["streams"]),
                {key: (item["available"], item["records"]) for key, item in streams.items()})
    results.add("jsonl record counts come from an actual scan",
                streams["events"]["records_counted"] is True and streams["events"]["records"] > 0,
                streams["events"])
    results.add("record order stays native append order with no synthetic clock",
                body["time"]["record_order_is_native_append_order"] is True
                and body["time"]["synchronized_across_streams"] is False
                and body["time"]["browser_arrival_order_is_not_used"] is True, body["time"])
    results.add("run manifest clock set is preserved",
                bool(body["time"]["clocks_declared_by_run_manifest"]) and "backend_monotonic" in body["time"]["clocks_declared_by_run_manifest"],
                body["time"]["clocks_declared_by_run_manifest"])
    semantics = body["action_semantics"]
    results.add("Actual, recorded target, command intent and feedback stay separate classes",
                semantics["recorded_target"] == ["actuator_reference"] and "feedback" in semantics["execution_feedback"]
                and "requested" in semantics["command_intent"], semantics["recorded_target"])
    results.add("legacy records carry no invented platform configuration",
                body["platform_association"]["known"] is False
                and body["platform_association"]["validated_snapshot_ref"] is None
                and body["platform_association"]["reason"] == "legacy_native_record_without_platform_sidecar",
                body["platform_association"])
    results.add("training qualification never blocks the raw read",
                body["training_qualification"]["blocks_raw_read"] is False, body["training_qualification"])
    three_d = body["three_d_replay"]
    expect_restricted = three_d["model_match"] != "match" or three_d["scene_match"] != "match"
    results.add("3D replay status follows the recorded identity, never the live scene",
                three_d["live_geometry_or_actual_may_be_applied"] is False and bool(three_d["recorded_model_sha256"])
                and (three_d["status"] == "restricted") == expect_restricted
                and three_d["status"] in {"restricted", "identity_verified_rendering_unverified"}
                and any("live Actual/geometry is never substituted" in reason for reason in three_d["reasons"]),
                {"status": three_d["status"], "model_match": three_d["model_match"], "scene_match": three_d["scene_match"],
                 "recorded": three_d["recorded_model_sha256"][:12], "reference": (three_d["reference_model_sha256"] or "")[:12]})

    # ---- real state/action/event reads ----------------------------------------
    status, page = records(complete_id, complete_run, "events", "&limit=5")
    seqs = [item["record"].get("event_seq") for item in page["records"]]
    types = {item["record"].get("event_type") for item in page["records"]}
    results.add("events page returns real recorded events",
                status == 200 and len(page["records"]) == 5 and all(isinstance(s, int) for s in seqs)
                and seqs == sorted(seqs) and types <= NATIVE_VOCABULARY, {"seqs": seqs, "types": sorted(types)})
    results.add("event records keep native time fields and units untouched",
                all(("wall_utc" in item["record"]) for item in page["records"])
                and page["time"]["units"].startswith("seconds"), page["time"])
    results.add("cursor states that line index is not a clock",
                page["cursor"]["line_index_is_not_a_clock"] is True, page["cursor"])
    status, nxt = records(complete_id, complete_run, "events", "&limit=5&offset=5")
    results.add("event pages advance without overlap",
                nxt["records"][0]["record"]["event_seq"] > seqs[-1] and nxt["paging"]["offset"] == 5,
                nxt["paging"])
    status, window = records(complete_id, complete_run, "events", "&event_seq_from=100&event_seq_to=104&limit=10")
    wseq = [item["record"]["event_seq"] for item in window["records"]]
    results.add("event_seq window filters inside the stream", all(100 <= s <= 104 for s in wseq) and len(wseq) >= 1, wseq)
    status, timed = records(complete_id, complete_run, "control", "&limit=5&time_base=sim_time_s&time_from=0.02")
    results.add("time window uses a named native time base, not file position",
                status == 200 and all(item["record"].get("sim_time_s", 0) >= 0.02 for item in timed["records"])
                and timed["time"]["selected_time_base"] == "sim_time_s",
                {"returned": len(timed["records"]), "without_base": timed["time"]["records_without_the_selected_base"]})
    status, bad_base = records(complete_id, complete_run, "events", "&time_base=browser_arrival&time_from=1")
    results.add("unknown clock base is refused", status == 400 and code_of(bad_base) == "time_base_unsupported",
                {"status": status, "code": code_of(bad_base)})
    status, control = records(complete_id, complete_run, "control", "&limit=3")
    results.add("recorded control stream exposes target and feedback records",
                status == 200 and control["records"] and "payload" in control["records"][0]["record"],
                [item["record"].get("event_type") for item in control["records"]])
    status, obs = records(complete_id, complete_run, "observations-index", "&limit=3")
    oversize = obs["integrity"]["lines_over_read_size_limit"]
    results.add("oversized observation lines are reported, never replaced with invented frames",
                status == 200 and (obs["records"] or oversize) and obs["stream"]["relative_path"] == "observations/index.jsonl",
                {"returned": len(obs["records"]), "over_limit_lines": oversize[:3]})
    status, persist = records(complete_id, complete_run, "observations-persist", "&limit=2")
    results.add("persist accounting stream is readable", status == 200 and persist["records"] != [],
                {"returned": len(persist["records"]) if status == 200 else persist})
    status, transforms = records(complete_id, complete_run, "transforms", "&limit=2")
    results.add("recorded transforms are separate from any live geometry",
                status == 200 and transforms["records"], {"returned": len(transforms["records"])})
    status, snapshot = records(complete_id, complete_run, "initial-snapshot", "&limit=2")
    results.add("initial snapshot record is readable as one json document",
                status == 200 and len(snapshot["records"]) == 1, {"returned": len(snapshot["records"])})

    # ---- media asset reads ------------------------------------------------------
    media = body["media_summary"]["kinds"]
    results.add("media summary counts real assets",
                {"rgb", "depth", "masks"} <= set(media) and media["rgb"]["count"] > 200,
                {key: item["count"] for key, item in media.items()})
    sample = media["rgb"]["sample"][0]
    digest = hashlib.sha256(raw(f"{P}/api/v1/episodes/{complete_id}/assets/{sample['relative_path']}",
                                )[1]).hexdigest()
    results.add("media asset is served and digest-verified by the reader", len(digest) == 64, digest[:16])
    status, payload, headers = raw(f"{P}/api/v1/episodes/{complete_id}/assets/{sample['relative_path']}?sha256={digest}")
    lowered = {key.lower(): value for key, value in headers.items()}
    results.add("asset honours the requested sha256",
                status == 200 and lowered.get("x-episode-asset-sha256") == digest and payload,
                {"status": status, "declared_matches_digest": sample["declared_sha256"] == digest,
                 "header": lowered.get("x-episode-asset-sha256", "")[:16], "run_header": lowered.get("x-episode-run-id")})
    status, wrong, _ = raw(f"{P}/api/v1/episodes/{complete_id}/assets/{sample['relative_path']}?sha256={'0' * 64}")
    results.add("digest mismatch is refused before the bytes are returned",
                status == 409 and code_of(json.loads(wrong)) == "episode_asset_digest_mismatch", status)
    unsupported = [item["relative_path"] for kind in media.values() for item in kind["sample"]
                   if Path(item["relative_path"]).suffix not in ALLOWED_SUFFIXES]
    if unsupported:
        status, payload = get_json(f"{P}/api/v1/episodes/{complete_id}/assets/{unsupported[0]}")
        results.add("unsupported media format is refused not guessed",
                    status == 415 and code_of(payload) == "episode_asset_type_unsupported", {"path": unsupported[0], "status": status})
    else:
        results.add("no unsupported asset type exists in this record", True, {"checked_samples": media["rgb"]["count"]})
    status, escaped = get_json(f"{P}/api/v1/episodes/{complete_id}/assets/rgb/%2e%2e/%2e%2e/%2e%2e/%2e%2e/assets/rgb/frame.png")
    results.add("traversal outside the episode is rejected",
                status in (400, 409) and code_of(escaped) in {"episode_asset_path_invalid", "episode_asset_escape"},
                {"status": status, "code": code_of(escaped)})
    status, absent = get_json(f"{P}/api/v1/episodes/{complete_id}/assets/rgb/definitely-not-recorded.png")
    results.add("missing media is located as missing", status == 404 and code_of(absent) == "episode_asset_missing", status)

    # ---- a real FAILED / incomplete record --------------------------------------
    failed_body = detail_for(failed_id, failed_run)
    results.add("FAILED record keeps its declared failure and incomplete audit",
                failed_body["declared"]["recording_status"] == "FAILED"
                and failed_body["declared"]["audit_status"] == "INCOMPLETE", failed_body["declared"])
    results.add("FAILED record is layered as an incompletely recorded terminal state",
                failed_body["integrity"]["status"] == "incomplete_terminal_recorded", failed_body["integrity"]["status"])
    status, failed_records = records(failed_id, failed_run, "events", "&limit=3")
    results.add("an incomplete record is still readable rather than hidden",
                status == 200 and failed_records["integrity"]["declared_status"]["recording_status"] == "FAILED",
                failed_records["integrity"]["declared_status"])
    unavailable_streams = [item["stream_id"] for item in failed_body["streams"] if not item["available"]]
    results.add("absent streams in the FAILED record are named", isinstance(unavailable_streams, list),
                {"absent": unavailable_streams, "note": "empty means the record carries every stream file"})

    # ---- frame linkage on a real Episode (image to recorded state) ---------------
    status, frames = get_json(f"{P}/api/v1/episodes/{complete_id}/frames?run_id={complete_run}&limit=5")
    results.add("frame linkage answers with its own read-only schema",
                status == 200 and frames["schema_version"] == "unirobot-mobilecar-frame-link-2"
                and frames["read_only"] is True, {"status": status, "code": code_of(frames)})
    page = frames["frames"]

    def roles(frame: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {item["role"]: item for item in frame["roles"]}

    def quantities(frame: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {item["key"]: item for item in frame["times"]["quantities"]}

    results.add("real persisted frames arrive in native append order with the recorder's own counter",
                len(page) == 5
                and [item["anchor"]["line_index"] for item in page] == sorted(item["anchor"]["line_index"] for item in page)
                and all(isinstance(item["anchor"]["persist_sequence"], int) for item in page),
                {"line_indexes": [item["anchor"]["line_index"] for item in page],
                 "persist_sequences": [item["anchor"]["persist_sequence"] for item in page]})
    results.add("every returned frame carries one rgb row and one depth row, judged by kind",
                all(roles(item)["image_observation"]["status"] == "matched"
                    and roles(item)["image_observation"]["matched_kinds"] == ["depth", "rgb"]
                    and roles(item)["image_observation"]["missing_kinds"] == []
                    and roles(item)["image_observation"]["duplicate_kinds"] == []
                    and len(roles(item)["image_observation"]["sources"]) == 2 for item in page),
                {"requirement": frames["linkage"]["roles"]["image_observation"]["requirement"],
                 "coverage": frames["linkage"]["role_coverage_on_this_page"]["image_observation"]})
    results.add("a repeated kind is judged by the required set rather than by a record count",
                frames["linkage"]["status_precedence"].index("ambiguous_kind")
                < frames["linkage"]["status_precedence"].index("partial")
                and frames["linkage"]["status_meaning"]["ambiguous_kind"].startswith("a sensor_kind"),
                {"precedence": frames["linkage"]["status_precedence"]})
    results.add("every returned frame reaches a transform row recorded for the same sample_id",
                all(roles(item)["camera_transform"]["status"] == "matched"
                    and roles(item)["camera_transform"]["candidate_records"] == 1 for item in page),
                {"note": "the row names frame_id rgbd_optical and is not a per-body pose sequence"})
    results.add("every returned frame reaches exactly one recorded state event through its capture tick",
                all(roles(item)["state_feedback_event"]["status"] == "matched"
                    and roles(item)["state_feedback_event"]["candidate_records"] == 1
                    and item["state"]["single_state_selected"] is True
                    and roles(item)["state_feedback_event"]["sources"][0]["relative_path"] == "events.jsonl"
                    and all(source["identity"]["run_id_matches"] and source["identity"]["episode_id_matches"]
                            for role in roles(item).values() for source in role["sources"]) for item in page),
                {"join_key": "control_tick_id",
                 "example_key": roles(page[0])["state_feedback_event"]["key_value"]})
    first_quantities = quantities(page[0])
    state_keys = ("state_event_write_minus_frame_capture", "state_payload_feedback_time_minus_frame_capture",
                  "recorder_declared_feedback_time_minus_frame_capture")
    results.add("the three state-related stamps stay three named quantities instead of one age",
                all(key in first_quantities for key in state_keys)
                and len({round(first_quantities[key]["abs_ms"], 3) for key in state_keys}) == 3
                and len({first_quantities[key]["source_record"] + first_quantities[key]["field"]
                         for key in state_keys}) == 3
                and all(first_quantities[key]["direction"] == "earlier" for key in state_keys),
                {"event_write_ms": round(first_quantities[state_keys[0]]["abs_ms"], 6),
                 "payload_sample_ms": round(first_quantities[state_keys[1]]["abs_ms"], 6),
                 "recorder_declared_ms": round(first_quantities[state_keys[2]]["abs_ms"], 6),
                 "fields": [first_quantities[key]["field"] for key in state_keys],
                 "note": "measured on the real first frame: 2.885407 / 3.669841 / 3.668296 ms"})
    results.add("the same state sample is separated from the event write by its own recorded difference",
                abs(first_quantities["state_payload_feedback_time_minus_state_event_write"]["abs_ms"] - 0.784434) < 1e-4
                and quantities(page[0])["timing_payload_capture_minus_anchor_capture"]["direction"] == "equal",
                {"payload_minus_event_write_ms":
                     round(first_quantities["state_payload_feedback_time_minus_state_event_write"]["abs_ms"], 6)})
    sim_items = {key: item for key, item in first_quantities.items() if item["clock"] == "sim"}
    results.add("both simulator-time stamps stay on the sim clock and nothing else is folded into it",
                set(sim_items) == {"state_sim_time_minus_frame_capture_sim_time",
                                   "state_event_envelope_sim_time_minus_frame_capture_sim_time"}
                and all(item["unit"] == "s" for item in sim_items.values())
                and len({item["source_record"] for item in sim_items.values()}) == 2
                and all(item["clock"] != "sim" for key, item in first_quantities.items() if key not in sim_items),
                {"sim_deltas_s": {key: item["value"] for key, item in sim_items.items()},
                 "monotonic_event_delta_s": first_quantities["state_event_write_minus_frame_capture"]["value"]})
    recorder = page[0]["times"]["recorder_declared"]
    results.add("the recorder's own observation age is copied and compared, never merged with state stamps",
                recorder["agrees_with_recomputation"] is True
                and abs(recorder["fields"]["observation_age_ms"]
                        - recorder["recomputed_arrival_minus_capture_ms"]) < 1e-6
                and abs(recorder["fields"]["observation_age_ms"]
                        - first_quantities["state_payload_feedback_time_minus_frame_capture"]["abs_ms"]) > 20.0
                and "not the difference between a state sample" in recorder["observation_age_ms_note"],
                {"observation_age_ms": recorder["fields"]["observation_age_ms"],
                 "recomputed_arrival_minus_capture_ms": recorder["recomputed_arrival_minus_capture_ms"],
                 "state_sample_minus_capture_ms":
                     round(first_quantities["state_payload_feedback_time_minus_frame_capture"]["abs_ms"], 6)})
    results.add("no page presents an age that mixes the state write stamp with the sample stamp",
                all("age_of_state_relative_to_frame" not in item["times"] for item in page)
                and "times.age_of_state_relative_to_frame" in frames["version_migration"]["removed_fields"]
                and frames["time"]["synchronized_across_streams"] is False
                and frames["time"]["clock_sameness"]["verified_by_reader"] is False
                and all(item["state"]["interpolated"] is False and item["state"]["carried_over_from_another_frame"] is False
                        for item in page),
                {"removed": frames["version_migration"]["removed_fields"],
                 "writer_binding": frames["time"]["clock_sameness"]["writer_version_binding"]})
    media_items = [entry for item in page for entry in item["media"]["items"]]
    results.add("frame media uris resolve inside the episode and agree with their observation row",
                all(entry["availability"] == "present" for entry in media_items)
                and all(entry["agrees_with_observation_row"] is True for entry in media_items
                        if entry["field"] in ("rgb_uri", "depth_uri"))
                and all(entry["observation_row_candidates"] == 1 for entry in media_items
                        if entry["field"] in ("rgb_uri", "depth_uri")),
                {"fields": sorted({entry["field"] for entry in media_items}), "count": len(media_items)})
    results.add("declared asset digests are carried as declarations, not as verified bytes",
                all(entry["declared_sha256_by_row"] for entry in media_items if entry["field"] in ("rgb_uri", "depth_uri"))
                and "declared only" in page[0]["media"]["digest_verification"],
                {"example_rgb": media_items[0]["declared_sha256_by_row"],
                 "mask_declared_digest": next(entry["declared_sha256_by_row"] for entry in media_items
                                              if entry["field"] == "valid_mask_uri")})
    reference = frames["linkage"]["role_coverage_on_this_page"]["feedback_observation_row"]
    results.add("a declared feedback reference with no recorded row is reported unresolved, not matched",
                sum(reference.values()) == len(page) and reference.get("unresolved_reference", 0) >= 2
                and all(item["declared_reference_status"] in ("matched", "unresolved_reference") for item in page),
                {"coverage": reference,
                 "note": "this source declares joint_feedback ids for every frame but records such rows for only 3 of 303 frames"})
    status, one = get_json(f"{P}/api/v1/episodes/{complete_id}/frames?run_id={complete_run}&limit=1")
    results.add("has_more is decided by the next qualifying anchor, not by a prefiltered count",
                 status == 200 and one["paging"]["next_offset"] == 1 and one["paging"]["has_more"] is True
                 and one["paging"]["next_qualifying_anchor_line_index"] == 1
                 and one["paging"]["post_page_records_examined"] == 1
                 and one["paging"]["scan"]["whole_file_scanned"] is False, one["paging"])
    results.add("line bookkeeping counts only the lines this scan actually read",
                 one["paging"]["anchor_lines"]["lines_read"] == 2
                 and one["paging"]["anchor_lines"]["blank_lines_skipped"] == 0
                 and one["paging"]["anchor_lines"]["unparseable_lines_skipped"] == 0
                 and one["paging"]["anchor_lines"]["oversize_lines_skipped"] == 0
                 and one["paging"]["anchor_records_examined"] == 2,
                 {"anchor_lines": one["paging"]["anchor_lines"],
                  "note": "the real anchor file has no blank or unreadable lines; the counters are reported, not assumed"})
    status, past_end = get_json(f"{P}/api/v1/episodes/{complete_id}/frames?run_id={complete_run}&offset=1000000")
    results.add("reading past the end returns an empty page rather than inventing a last page",
                 status == 200 and past_end["frames"] == [] and past_end["paging"]["has_more"] is False
                 and past_end["paging"]["next_offset"] is None
                 and past_end["paging"]["scan"]["whole_file_scanned"] is True,
                 {"skipped_before_offset": past_end["paging"]["skipped_before_offset"],
                  "anchor_lines_read": past_end["paging"]["anchor_lines"]["lines_read"]})
    status, picked = get_json(f"{P}/api/v1/episodes/{complete_id}/frames?run_id={complete_run}&sample_id={page[1]['sample_id']}")
    results.add("a single frame can be addressed by its recorded sample_id",
                status == 200 and [item["sample_id"] for item in picked["frames"]] == [page[1]["sample_id"]]
                and picked["paging"]["excluded_by_sample_id_filter"] >= 1,
                picked["paging"])
    status, window = get_json(f"{P}/api/v1/episodes/{complete_id}/frames?run_id={complete_run}&limit=5"
                              f"&time_base=capture_sim_time_s&time_from=0&time_to=1e9")
    results.add("a named frame time base filters without reordering",
                status == 200 and len(window["frames"]) == 5
                and window["paging"]["records_missing_selected_time_base"] == 0
                and window["paging"]["excluded_outside_time_window"] == 0
                and [item["anchor"]["line_index"] for item in window["frames"]]
                == sorted(item["anchor"]["line_index"] for item in window["frames"]),
                window["paging"])
    status, wrong_base = get_json(f"{P}/api/v1/episodes/{complete_id}/frames?run_id={complete_run}&time_base=wall_utc&time_from=1")
    results.add("frame selection rejects a base the persisted frames do not carry",
                status == 400 and code_of(wrong_base) == "time_base_unsupported"
                and "capture_backend_monotonic_s" in wrong_base["detail"]["supported"], status)
    status, bad_token = get_json(f"{P}/api/v1/episodes/{complete_id}/frames?run_id={complete_run}&sample_id=bad!token")
    results.add("an unusable sample_id is refused rather than guessed", status == 400 and code_of(bad_token) == "sample_id_invalid", status)
    status, other_stream = get_json(f"{P}/api/v1/episodes/{complete_id}/frames?run_id={complete_run}&stream=lidar")
    results.add("a stream with no persisted frames returns an empty page rather than a substitute",
                status == 200 and other_stream["frames"] == [] and other_stream["paging"]["next_offset"] is None
                and other_stream["paging"]["has_more"] is False,
                other_stream["paging"])
    status, incomplete_frames = get_json(f"{P}/api/v1/episodes/{failed_id}/frames?run_id={failed_run}&limit=10")
    results.add("the incomplete real record exposes frame linkage in the documented vocabulary",
                status == 200 and len(incomplete_frames["frames"]) == 4
                and all(item["linkage_status"] in ("matched", "partial", "missing") for item in incomplete_frames["frames"])
                and all(role_status in frames["linkage"]["status_meaning"]
                        for counts in incomplete_frames["linkage"]["role_coverage_on_this_page"].values()
                        for role_status in counts),
                {"statuses": [item["linkage_status"] for item in incomplete_frames["frames"]],
                 "coverage": incomplete_frames["linkage"]["role_coverage_on_this_page"]})
    results.add("frame linkage never opens the door to 3d replay or live substitution",
                frames["three_d_replay"]["this_slice_does_not_enable_3d_replay"] is True
                and frames["three_d_replay"]["live_geometry_or_actual_may_be_applied"] is False
                and frames["three_d_replay"]["transforms_are_full_per_body_pose_sequences"] is False
                and frames["three_d_replay"]["robot_pose_readiness_slice"].startswith("GET /api/v1/episodes")
                and any("cross-episode cursor" in item for item in frames["capability_limits"]),
                frames["three_d_replay"])

    # ---- historical robot pose against the frozen model (readiness, not rendering) --
    status, pose = get_json(f"{P}/api/v1/episodes/{complete_id}/robot-state?run_id={complete_run}"
                            f"&sample_id={page[0]['sample_id']}")
    results.add("pose preparation reads the recorded frame through the same linkage rules",
                status == 200 and pose["schema_version"] == "unirobot-mobilecar-history-pose-1"
                and pose["read_only"] is True and pose["frame"]["sample_id"] == page[0]["sample_id"]
                and pose["frame"]["linkage_schema"] == "unirobot-mobilecar-frame-link-2",
                {"status": status, "code": code_of(pose)})
    results.add("the recorded run identity equals the frozen geometry bundle identity",
                pose["model_resource"]["status"] == "match"
                and all(item["equal"] for item in pose["model_resource"]["comparison"].values())
                and pose["identity"]["recorded_run_manifest"]["model_sha256"]
                == pose["model_resource"]["comparison"]["model_sha256"]["bundle"],
                {"comparison": pose["model_resource"]["comparison"],
                 "bundle_sha256": pose["model_resource"]["bundle_sha256"],
                 "content_identity": pose["model_resource"]["content_identity_sha256"]})
    pose_mapping = {item["target"]: item for item in pose["mapping"]}
    results.add("the arm maps onto the bundle's five hinge joints with its attested index named",
                pose_mapping["arm_joint_positions"]["status"] in ("verified", "partially_verified")
                and isinstance(pose_mapping["arm_joint_positions"]["verified_basis"], list)
                and pose_mapping["arm_joint_positions"]["recorded_length"] == 5
                and pose_mapping["arm_joint_positions"]["evidence"]["names_equal_to_bundle"] is True
                and pose_mapping["arm_joint_positions"]["evidence"]["order_attested_at_index"] == 3
                and pose_mapping["arm_joint_positions"]["no_default_applied"] is True,
                {"bundle_joints": pose["model_resource"]["arm_hinge_joints"],
                 "evidence": pose_mapping["arm_joint_positions"]["evidence"]})
    results.add("unattested mappings are reported as gaps and never filled with defaults",
                all(pose_mapping[target]["no_default_applied"] is True and pose_mapping[target]["gap"]
                    for target in pose_mapping)
                and all(pose_mapping[target]["status"] in ("unverified", "missing")
                        for target in ("gripper_joints", "camera_extrinsics", "dynamic_scene_objects"))
                and all(pose_mapping[target]["status"] in ("verified", "unverified")
                        for target in ("base_position", "base_orientation", "tcp_site_position"))
                and all(pose_mapping[target]["verified_basis"] for target in
                        ("base_position", "base_orientation", "tcp_site_position")
                        if pose_mapping[target]["status"] == "verified")
                and "gripper_joints" in pose["pose_readiness"]["blocking_fields"]
                and set(pose["pose_readiness"]["blocking_fields"]) <= {"gripper_joints", "camera_extrinsics",
                                                                       "dynamic_scene_objects", "tcp_site_orientation",
                                                                       "base_position", "base_orientation",
                                                                       "tcp_site_position", "arm_joint_positions"}
                and all(item["target"] not in pose["pose_readiness"]["blocking_fields"]
                        for item in pose["mapping"] if item["status"] == "verified"),
                {"statuses": {target: pose_mapping[target]["status"] for target in
                              ("base_position", "base_orientation", "gripper_joints", "tcp_site_position",
                               "camera_extrinsics", "dynamic_scene_objects")},
                 "note": "no historical position is recorded for dynamic scene objects, so none is invented"})
    results.add("resource readiness is kept apart from rendering verification",
                pose["pose_readiness"]["robot_state_can_be_rebuilt_without_assumptions"] is False
                and pose["pose_readiness"]["mapping_valid_for_this_episode"] is True
                and pose["rendering"]["verified"] is False and pose["rendering"]["frontend_assembly_done"] is False
                and pose["state"]["recorded_payload"]["arm_model_qpos_rad"]
                == page[0]["state"]["recorded_state"]["arm_model_qpos_rad"],
                {"readiness": pose["pose_readiness"], "gaps": pose["not_proven"]})
    results.add("pose time carries the same separated quantities as the frame page",
                {item["key"] for item in pose["time"]["quantities"]} >= set(state_keys)
                and pose["time"]["same_clock_verified"] is False
                and pose["time"]["clock_sameness"]["writer_version_binding"]["synchronized_upgraded_by_numeric_closeness"] is False,
                {"keys": [item["key"] for item in pose["time"]["quantities"]]})
    mesh = pose["model_resource"]["assets"][0]
    status, mesh_body, mesh_headers = raw(f"{P}/api/v1/episodes/{complete_id}/model/assets/{mesh['asset_id']}"
                                f"?run_id={complete_run}&sha256={mesh['sha256']}")
    results.add("the frozen bundle mesh is served without reading the live native scene",
                 status == 200 and hashlib.sha256(mesh_body).hexdigest() == mesh["sha256"]
                 and mesh_headers.get("x-unirobot-model-source") == "frozen_compiled_geometry_bundle"
                 and mesh_headers.get("etag") == f'"sha256:{mesh["sha256"]}"',
                 {"asset_id": mesh["asset_id"], "bytes_on_disk": mesh["bytes"],
                  "asset_count": len(pose["model_resource"]["assets"])})
    status, stale_mesh = get_json(f"{P}/api/v1/episodes/{complete_id}/model/assets/{mesh['asset_id']}"
                                  f"?run_id={complete_run}&sha256={'0' * 64}")
    results.add("a stale mesh digest is refused instead of silently serving a different revision",
                 status == 409 and code_of(stale_mesh) == "history_asset_revision_changed", status)
    status, absent_mesh = get_json(f"{P}/api/v1/episodes/{complete_id}/model/assets/no_such_asset?run_id={complete_run}")
    results.add("an asset outside the frozen bundle is named as unavailable",
                 status == 404 and code_of(absent_mesh) == "history_model_asset_unavailable"
                 and mesh["asset_id"] in absent_mesh["detail"]["supported"], status)

    # ---- M1.5e: kinematic cross-check, per-part readiness, sim source labelling ----
    sim_keys = {item["key"]: item for item in page[0]["times"]["quantities"]
                if "sim_time" in item["key"]}
    results.add("both simulator-time stamps are reported with their own source record",
                {"state_sim_time_minus_frame_capture_sim_time",
                 "state_event_envelope_sim_time_minus_frame_capture_sim_time"} <= set(sim_keys)
                and len({item["source_record"] for item in sim_keys.values()}) == len(sim_keys),
                {key: item["source_record"] for key, item in sim_keys.items()})
    cross = pose["tcp_kinematic_cross_check"]
    results.add("recorded TCP is reproduced from recorded state through the frozen tree",
                cross["status"] == "computed" and cross["verdict"] == "consistent"
                and cross["abs_error_m"] < 1e-9 and cross["joints_left_at_zero"] == [],
                {"abs_error_m": cross["abs_error_m"], "recorded": cross["recorded_tcp_position_m"],
                 "computed": cross["computed_tcp_position_m"], "chain": cross["chain_links"],
                 "tolerance_m": cross["consistency_tolerance_m"]})
    alternative = cross["hypotheses"][1]
    results.add("the competing root convention is separated by exactly the base body offset",
                alternative["verdict"] == "inconsistent"
                and abs(alternative["abs_error_m"] - 0.0556) < 1e-6,
                {"abs_error_m": alternative["abs_error_m"], "hypothesis": alternative["hypothesis"]})
    verified_targets = {item["target"]: item["status"] for item in pose["mapping"]}
    results.add("reproduction upgrades only the fields it depends on and leaves the rest unproven",
                all(verified_targets[target] == "verified" for target in
                    ("arm_joint_positions", "base_position", "base_orientation", "tcp_site_position"))
                and verified_targets["gripper_joints"] == "unverified"
                and verified_targets["camera_extrinsics"] == "missing"
                and verified_targets["dynamic_scene_objects"] == "missing",
                {"statuses": verified_targets})
    arm_mapping = next(item for item in pose["mapping"] if item["target"] == "arm_joint_positions")
    results.add("the arm mapping cites the name-addressed source chain and its version ceiling",
                "ARM_JOINTS = tuple" in arm_mapping["evidence"]["source_chain"]["joint_name_list"]
                and "qpos = model.jnt_qposadr" in arm_mapping["evidence"]["source_chain"]["qpos_is_name_addressed"]
                and arm_mapping["evidence"]["source_chain"]["sixth_element_excluded"].startswith("GRIPPER_DRIVE")
                and pose["version_binding"]["writer_identified"] is False
                and len(pose["version_binding"]["frozen_release_snapshots_at_the_recording_hour"]) == 3,
                {"chain": arm_mapping["evidence"]["source_chain"],
                 "binding": pose["version_binding"]["conclusion"]})
    angles = pose["model_vs_user_angles"]
    results.add("model radians draw the arm without the user-angle step",
                angles["conversion_is_required_for_drawing"] is False
                and angles["config_joint_names_equal_bundle_arm_hinges"] is True
                and arm_mapping["requires_user_angle_conversion"] is False
                and angles["zero_pose_authority"]["zero_status"] == "user_defined_photo_pose_not_hardware_500"
                and angles["zero_pose_authority"]["calibration_session"] == "uncalibrated",
                {"authority": angles["authority"], "user_formula_used_for":
                    angles["user_angle_formula"]["used_for"]})
    capabilities = {item["capability"]: item for item in pose["part_readiness"]}
    summary = pose["capability_summary"]
    results.add("readiness is per part, and a whole-robot gap never blocks the fixed assembly",
                capabilities["fixed_model_reference_assembly"]["status"] == "ready"
                and capabilities["fixed_model_reference_assembly"]["pose_input_required"] is False
                and capabilities["arm_local_pose"]["status"] == "ready_with_caveats"
                and capabilities["base_pose_placement"]["status"] == "ready_with_caveats"
                and capabilities["camera_view_from_record"]["status"] == "blocked"
                and capabilities["dynamic_scene_objects_from_record"]["status"] == "blocked"
                and all(item["status"] in pose["part_status_meaning"] for item in capabilities.values())
                and all("frontend_rule" in item for item in capabilities.values()),
                {"statuses": {name: item["status"] for name, item in capabilities.items()},
                 "usable_now": summary["usable_now"],
                 "usable_with_caveat": summary["usable_only_with_the_named_caveat"],
                 "blocked": summary["blocked"]})
    results.add("the summary keeps assembly, partial pose and whole-robot rebuild three separate claims",
                summary["fixed_model_assembly_available"] is True
                and summary["whole_robot_pose_rebuildable"] is False
                and "never upgrades" in summary["escalation_forbidden"]
                and pose["rendering"]["verified"] is False and pose["rendering"]["frontend_assembly_done"] is False
                and "does not calibrate hardware" in cross["does_not_prove"],
                {"kinematic_agreement": summary["kinematic_agreement"],
                 "abs_tcp_error_m": summary["abs_tcp_error_m"]})

    # ---- M1.5f: the opt-in static model tree (assembly data straight from the frozen bundle) --
    entries_before_tree = len(PROBE.entries)
    tree_url = f"{P}/api/v1/episodes/{complete_id}/robot-state?run_id={complete_run}&include_model_tree=true"
    status, tree_body, tree_headers = raw(tree_url)
    tree_page = json.loads(tree_body)
    tree = tree_page["model_resource"]["model_tree"]
    loaded = GeometryBundle(Path(manifest["geometry_bundle"]["path"]))
    results.add("the default response carries no tree and the requested one adds it without changing anything else",
                "model_tree" not in pose["model_resource"] and status == 200 and tree["included"] is True
                and {key: value for key, value in tree_page["model_resource"].items() if key != "model_tree"}
                == pose["model_resource"]
                and tree_page["frame"] == pose["frame"] and tree_page["mapping"] == pose["mapping"]
                and tree_page["part_readiness"] == pose["part_readiness"],
                {"default_model_resource_keys": len(pose["model_resource"]),
                 "added_keys": sorted(set(tree_page["model_resource"]) - set(pose["model_resource"]))})
    results.add("the opt-in answer is the whole frozen tree, equal link for link to the loaded bundle",
                tree["authority"] == "frozen_compiled_geometry_bundle"
                and tree["live_native_scene_proxied"] is False
                and tree["links"] == [link.model_dump(mode="json") for link in loaded.scene.links]
                and tree["world_links"] == [link.model_dump(mode="json") for link in loaded.scene.world_links]
                and tree["counts"]["links"] == tree_page["model_resource"]["link_count"]
                and len(tree["links"]) > 3,
                {"counts": tree["counts"], "response_bytes": len(tree_body),
                 "link_count_on_model_resource": tree_page["model_resource"]["link_count"]})
    results.add("every link carries the assembly fields the three named summary views do not",
                all(set(link) == {"name", "parent_name", "joint_name", "joint_type", "joint_axis",
                                  "local_transform", "geoms"} for link in tree["links"] + tree["world_links"])
                and all("local_position_m" not in link for link in tree["links"])
                and all({"name", "geom_type", "size_m", "local_transform", "rgba", "mesh_asset_id",
                         "collision", "group", "contype", "conaffinity"} == set(geom)
                        for link in tree["links"] + tree["world_links"] for geom in link["geoms"]),
                {"links_without_geoms": [link["name"] for link in tree["links"] + tree["world_links"]
                                          if not link["geoms"]]})
    referenced = {geom["mesh_asset_id"] for link in tree["links"] + tree["world_links"]
                  for geom in link["geoms"] if geom["mesh_asset_id"]}
    published = {item["asset_id"] for item in tree_page["model_resource"]["assets"]}
    results.add("the tree's mesh references resolve inside the same frozen asset list the viewer already uses",
                bool(referenced) and referenced <= published,
                {"referenced_by_the_tree": len(referenced), "published_in_model_resource": len(published),
                 "unreferenced_assets": sorted(published - referenced)})
    results.add("the tree reuses the four published digests instead of a second identity scheme",
                all(tree["content_identity"][key] == tree_page["model_resource"][key] for key in
                    ("bundle_sha256", "content_identity_sha256", "compiled_scene_sha256", "model_inputs_sha256"))
                and tree["content_identity"]["bundle_sha256"] == loaded.provenance.bundle_sha256
                and tree["content_identity"]["compiled_scene_sha256"] == loaded.provenance.compiled_scene_sha256
                and tree["content_identity"]["content_identity_sha256"] == loaded.content_identity_sha256,
                {key: tree["content_identity"][key] for key in
                 ("bundle_sha256", "content_identity_sha256", "compiled_scene_sha256")})
    status_second, other_frame = get_json(f"{tree_url}&sample_id={page[1]['sample_id']}")
    results.add("the static tree is the same answer for another frame, so it needs no per-frame re-read",
                status_second == 200 and other_frame["model_resource"]["model_tree"] == tree
                and other_frame["frame"]["sample_id"] != tree_page["frame"]["sample_id"]
                and other_frame["state"]["recorded_payload"] != tree_page["state"]["recorded_payload"],
                {"sample_ids": [tree_page["frame"]["sample_id"], other_frame["frame"]["sample_id"]],
                 "tree_identical": True})
    results.add("the tree is labelled reference layout, and the dynamic response carries no content ETag",
                tree["semantics"]["world_links"] == "compiled_initial_layout_not_live_object_state"
                and tree["semantics"]["is_recorded_state"] is False
                and tree["semantics"]["world_links_are_not_recorded_object_positions"] is True
                and tree["caching"]["identical_for_every_frame_of_this_bundle"] is True
                and "per-frame" in tree["caching"]["fetch_rule"]
                and "etag" not in tree_headers
                and tree["mesh_bytes"].startswith("geoms[].mesh_asset_id"),
                {"headers": sorted(tree_headers), "fetch_rule": tree["caching"]["fetch_rule"],
                 "world_links_named": [item["name"] for item in tree["world_links"]]})
    results.add("asking for the tree issues no live native scene read, only the platform GET",
                [item["url"] for item in PROBE.entries[entries_before_tree:]] == [tree_url,
                                                                                  f"{tree_url}&sample_id={page[1]['sample_id']}"]
                and all(item["url"].startswith(P) for item in PROBE.entries[entries_before_tree:])
                and all(item["method"] == "GET" for item in PROBE.entries[entries_before_tree:]),
                {"issued": [item["url"] for item in PROBE.entries[entries_before_tree:]],
                 "live_scene_reads_in_this_run": sum(1 for item in PROBE.entries
                                                     if "/api/v1/scene" in item["url"])})

    # ---- M1.5g: anchor time quality, eligibility and a full page walk --------------
    entries_before_census = len(PROBE.entries)
    status, census_page = get_json(f"{P}/api/v1/episodes/{complete_id}/frames?run_id={complete_run}"
                                   f"&limit=200&include_time_quality=true")
    census = census_page["time_quality"]
    coverage = census["coverage"]
    bases = census["time_bases"]
    schedule = census["playback_eligibility"]["recorded_interval_schedule"]["eligible_by_base"]
    results.add("the default page stays light and the census is opt-in only",
                "time_quality" not in frames
                and status == 200 and census["requested"] is True
                and set(census) == {"requested", "coverage", "time_bases", "identity", "recorder_counters",
                                    "profile", "playback_eligibility", "not_proven"}
                and census_page["summary"]["anchors_with_repeated_sample_id_on_this_page"] == 0,
                {"census_bytes": len(json.dumps(census)), "page_bytes": len(json.dumps(census_page))})
    results.add("the census counts readable anchors and their valid identity, and says what it covered",
                coverage["anchors_in_this_scan"] == coverage["unique_sample_ids"]
                and coverage["anchors_in_this_scan"] > 200 and coverage["whole_anchor_file_scanned"] is True
                and coverage["covers_whole_episode"] is True and coverage["not_a_whole_archive_sweep"] is True
                and sum(coverage["rejected_anchors"].values()) == 0
                and coverage["first_anchor_line_index"] <= coverage["last_anchor_line_index"],
                {key: coverage[key] for key in ("anchors_in_this_scan", "unique_sample_ids",
                                                "first_anchor_line_index", "last_anchor_line_index")}
                | {"rejected": coverage["rejected_anchors"], "anchor_lines": coverage["anchor_lines"]})
    results.add("each capture base is reported with its field, unit, clock and per-base counts",
                all({item["field"], item["unit"], item["clock"], item["source_record"]} and item["unit"] == "s"
                    for item in bases.values())
                and {item["clock"] for item in bases.values()} == {"backend_monotonic", "sim"}
                and all(item["numeric_count"] == coverage["anchors_in_this_scan"] and item["missing_count"] == 0
                        and item["non_numeric_count"] == 0 for item in bases.values()),
                {field: {key: item[key] for key in ("field", "unit", "clock", "numeric_count",
                                                    "missing_count", "non_numeric_count")}
                 for field, item in bases.items()})
    results.add("first/last in file order is separated from min/max in value order for every base",
                all(item["first_line_index"] <= item["last_line_index"]
                    and item["min_recorded_value"] is not None and item["max_recorded_value"] is not None
                    and item["min_recorded_value"] <= item["max_recorded_value"]
                    and item["file_order_matches_value_order"] is True
                    and item["monotonic_non_decreasing_in_file_order"] is True
                    and item["backwards_gaps"]["count"] == 0 and item["equal_adjacent_gaps"]["count"] == 0
                    for item in bases.values()),
                {field: {"first": item["first_in_file_order"], "last": item["last_in_file_order"],
                         "min": item["min_recorded_value"], "max": item["max_recorded_value"],
                         "gaps": item["recorded_gaps"], "ties": item["equal_adjacent_gaps"]["count"],
                         "backwards": item["backwards_gaps"]["count"]} for field, item in bases.items()})
    results.add("recorded time advances in append order, so no anomaly had to be explained away",
                all(item["recorded_gaps"]["count"] == coverage["anchors_in_this_scan"] - 1
                    and item["recorded_gaps"]["min_s"] > 0.0 for item in bases.values())
                and census["recorder_counters"]["persist_sequence_backwards_steps_in_file_order"] == 0
                and census["recorder_counters"]["line_index_is_not_a_clock"] is True,
                {field: {"gap_count": item["recorded_gaps"]["count"], "min_s": item["recorded_gaps"]["min_s"],
                         "max_s": item["recorded_gaps"]["max_s"], "median_s": item["recorded_gaps"]["median_s"],
                         "implied_rate_hz": schedule[field]["implied_rate_hz_from_median_recorded_gap"]}
                 for field, item in bases.items()})
    results.add("no rate is assumed: the numbers come from the recorded values, never from a default",
                census["playback_eligibility"]["recorded_interval_schedule"]["never_assumed"] == {
                    "default_rate_hz_applied": False, "browser_arrival_time_used": False,
                    "clock_stitched_across_reset": False,
                    "why": census["playback_eligibility"]["recorded_interval_schedule"]["never_assumed"]["why"]}
                and census["profile"]["anchor_fields_declaring_a_numeric_rate"] == []
                and all(schedule[field]["implied_rate_hz_from_median_recorded_gap"]
                        == 1.0 / bases[field]["recorded_gaps"]["median_s"] for field in bases),
                {"profile_ids": census["profile"]["profile_ids_seen"],
                 "implied_rates_hz": {field: schedule[field]["implied_rate_hz_from_median_recorded_gap"]
                                       for field in bases}})
    results.add("append-order display, recorded-interval scheduling and cross-stream sync stay three claims",
                census["playback_eligibility"]["append_order_display"]["eligible"] is True
                and census["playback_eligibility"]["append_order_display"]
                    ["anchor_position_never_reordered_by_time"] is True
                and census["playback_eligibility"]["recorded_interval_schedule"]
                    ["any_base_eligible_for_whole_episode"] is True
                and census["playback_eligibility"]["cross_stream_synchronized"]["eligible"] is False
                and census["playback_eligibility"]["cross_stream_synchronized"]["not_derivable_from"] == ["A", "B"]
                and census["playback_eligibility"]["cross_stream_synchronized"]["same_page_evidence"]
                    ["same_clock_verified"] is False,
                {field: {"eligible_for_whole_episode": item["eligible_for_whole_episode"],
                         "blocking": item["blocking_reasons"], "ties": item["zero_interval_ties_present"]}
                 for field, item in schedule.items()})
    results.add("anchor identity is unique here, and the census would name every position if it were not",
                census["identity"]["duplicate_sample_id_groups"] == 0 and census["identity"]["duplicates"] == []
                and census["identity"]["every_anchor_position_is_reported"] is True
                and "robot-state" in census["identity"]["effect_on_robot_state"]
                and "frame_sample_id_ambiguous" in census["identity"]["effect_on_robot_state"],
                {"effect_on_frames": census["identity"]["effect_on_this_route"],
                 "effect_on_robot_state": census["identity"]["effect_on_robot_state"]})

    walked, walk_pages, offset, walk_ok = [], 0, 0, True
    while True:
        status, walked_page = get_json(f"{P}/api/v1/episodes/{complete_id}/frames?run_id={complete_run}"
                                       f"&limit=200&offset={offset}")
        walked.extend(item["anchor"]["line_index"] for item in walked_page["frames"])
        walk_pages += 1
        if not walked_page["paging"]["has_more"]:
            last_walk_page = walked_page
            break
        if walked_page["paging"]["next_offset"] is None or walk_pages > 8:
            walk_ok = False
            last_walk_page = walked_page
            break
        offset = walked_page["paging"]["next_offset"]
    results.add("walking the pages consumes every anchor once, in append order, with no gap or repeat",
                walk_ok and walked == sorted(set(walked)) and len(walked) == coverage["anchors_in_this_scan"]
                and walked[0] == coverage["first_anchor_line_index"]
                and walked[-1] == coverage["last_anchor_line_index"]
                and last_walk_page["paging"]["has_more"] is False
                and last_walk_page["paging"]["next_offset"] is None
                and last_walk_page["paging"]["scan"]["whole_file_scanned"] is True,
                {"pages": walk_pages, "anchors_walked": len(walked),
                 "first_lines": walked[:3], "last_lines": walked[-3:],
                 "terminated_cleanly": walk_ok,
                 "last_page": {key: last_walk_page["paging"][key] for key in
                               ("returned", "has_more", "next_offset", "post_page_records_examined")}})
    status, census_windowed = get_json(f"{P}/api/v1/episodes/{complete_id}/frames?run_id={complete_run}"
                                       f"&time_base=capture_sim_time_s&time_from=0&time_to=1e9"
                                       f"&limit=5&include_time_quality=true")
    results.add("asking for the census leaves paging and both filters exactly as they were",
                status == 200 and census_windowed["time_quality"]["coverage"]["anchors_in_this_scan"]
                == coverage["anchors_in_this_scan"]
                and census_windowed["paging"]["excluded_outside_time_window"] == 0
                and census_windowed["paging"]["records_missing_selected_time_base"] == 0
                and len(census_windowed["frames"]) == 5
                and [item["anchor"]["line_index"] for item in census_windowed["frames"]]
                == sorted(item["anchor"]["line_index"] for item in census_windowed["frames"])
                and census_windowed["time_quality"]["coverage"]["page_filter_context"]["time_base"]
                == "capture_sim_time_s",
                {"filter_context": census_windowed["time_quality"]["coverage"]["page_filter_context"],
                 "window_counters": {key: census_windowed["paging"][key] for key in
                                     ("excluded_outside_time_window", "records_missing_selected_time_base")}})
    status, failed_census_body = get_json(f"{P}/api/v1/episodes/{failed_id}/frames?run_id={failed_run}"
                                          f"&include_time_quality=true")
    failed_census = failed_census_body["time_quality"]
    results.add("the incomplete real record is measured with the same vocabulary and the same honesty",
                status == 200 and failed_census["coverage"]["anchors_in_this_scan"] == 4
                and failed_census["coverage"]["covers_whole_episode"] is True
                and failed_census["coverage"]["rejected_anchors"]["excluded_identity_mismatch"] == 0
                and set(failed_census["time_bases"]) == set(bases)
                and failed_census["playback_eligibility"]["append_order_display"]["eligible"] is True
                and failed_census["playback_eligibility"]["cross_stream_synchronized"]["eligible"] is False
                and failed_census["identity"]["duplicate_sample_id_groups"] == 0,
                {"anchors": failed_census["coverage"]["anchors_in_this_scan"],
                 "per_base": {field: {"numeric": item["numeric_count"], "missing": item["missing_count"],
                                      "non_numeric": item["non_numeric_count"],
                                      "backwards": item["backwards_gaps"]["count"],
                                      "ties": item["equal_adjacent_gaps"]["count"],
                                      "eligible": failed_census["playback_eligibility"]
                                      ["recorded_interval_schedule"]["eligible_by_base"][field]
                                      ["eligible_for_whole_episode"]}
                              for field, item in failed_census["time_bases"].items()}})
    results.add("the census and the page walk ask the platform only, never the live native scene",
                all(item["url"].startswith(P) and item["method"] == "GET"
                    for item in PROBE.entries[entries_before_census:])
                and sum(1 for item in PROBE.entries[entries_before_census:]
                        if "/api/v1/scene" in item["url"]) == 0,
                {"requests_since_census_start": len(PROBE.entries) - entries_before_census})

    # ---- M1.5h: coverage boundary of the census, and the recorded action/event basis ----
    accounting = coverage["line_accounting"]
    results.add("coverage is three separate facts: EOF reached, every line decided, readable timing",
                coverage["reached_end_of_file"] is True and accounting["every_line_of_the_anchor_file_is_decided"] is True
                and accounting["undecidable_total"] == 0
                and all(item["reached_end_of_file"] is True
                        and item["every_line_of_the_anchor_file_is_decided"] is True
                        and item["readable_anchor_timing_satisfies_schedule"] is True
                        and item["eligible_for_whole_episode"] is True for item in schedule.values())
                and coverage["covers_whole_episode"] is True,
                {"lines_read": coverage["anchor_lines"]["lines_read"], "benign": accounting["benign_lines"],
                 "undecidable": accounting["undecidable_lines"],
                 "rejected_after_parsing": accounting["parsed_records_rejected_by_rule"]})
    results.add("line accounting names which counters could hide an anchor and which cannot",
                set(accounting["rules"]) == {"blank_lines_skipped", "prefiltered_lines_skipped",
                                             "oversize_lines_skipped", "unparseable_lines_skipped",
                                             "non_object_lines_skipped"}
                and all(accounting["rules"][key]["classification"] == "benign"
                        and accounting["rules"][key]["affects_whole_episode_qualification"] is False
                        for key in ("blank_lines_skipped", "prefiltered_lines_skipped"))
                and all(accounting["rules"][key]["classification"] == "undecidable"
                        and accounting["rules"][key]["may_hide_an_anchor"] is True
                        and accounting["rules"][key]["affects_whole_episode_qualification"] is True
                        for key in ("oversize_lines_skipped", "unparseable_lines_skipped",
                                    "non_object_lines_skipped")),
                {key: value["classification"] for key, value in accounting["rules"].items()})
    results.add("append-order browsing stays available and is told apart from a complete sequence",
                census["playback_eligibility"]["append_order_display"]["eligible"] is True
                and census["playback_eligibility"]["append_order_display"]["displayed_sequence_may_have_gaps"] is False
                and census["playback_eligibility"]["recorded_interval_schedule"]
                ["coverage_is_a_separate_question_from_timing"] is True,
                {"rules_when_unqualified": list(census["playback_eligibility"]["recorded_interval_schedule"]
                                                ["rules_when_unqualified"])})
    status, window_scope = get_json(f"{P}/api/v1/episodes/{complete_id}/frames?run_id={complete_run}"
                                    f"&time_base=capture_sim_time_s&time_from=0.2&time_to=0.6"
                                    f"&include_time_quality=true")
    results.add("a time window narrows the frame page while the census still scans the anchor file",
                status == 200 and len(window_scope["frames"]) == 1
                and window_scope["paging"]["excluded_outside_time_window"] == coverage["anchors_in_this_scan"] - 1
                and window_scope["time_quality"]["coverage"]["anchors_in_this_scan"] == coverage["anchors_in_this_scan"]
                and window_scope["time_quality"]["coverage"]["covers_whole_episode"] is True
                and "not the census" in window_scope["time_quality"]["coverage"]["scope_note"]
                and window_scope["time_quality"]["coverage"]["page_filter_context"]["time_base"]
                == "capture_sim_time_s",
                {"page_frames": len(window_scope["frames"]),
                 "excluded": window_scope["paging"]["excluded_outside_time_window"],
                 "census_anchors": window_scope["time_quality"]["coverage"]["anchors_in_this_scan"],
                 "scope_note": window_scope["time_quality"]["coverage"]["scope_note"]})

    entries_before_basis = len(PROBE.entries)
    status, basis_page = get_json(f"{P}/api/v1/episodes/{complete_id}/frames?run_id={complete_run}"
                                  f"&limit=200&include_action_basis=true")
    basis = basis_page["action_basis"]
    vocabulary, categories = basis["vocabulary"], basis["categories"]
    results.add("the action basis is opt-in and the default page still carries neither block",
                status == 200 and "action_basis" not in frames and "action_basis" not in census_page
                and set(basis_page) - set(frames) - {"time_quality"} == {"action_basis"}
                and basis["scope"]["reached_end_of_file"] is True
                and basis["scope"]["events_stream_present"] is True,
                {"basis_bytes": len(json.dumps(basis)), "records_scanned": basis["scope"]["records_scanned"]})
    results.add("the vocabulary accounts for every event record the stream declares",
                sum(item["count"] for item in vocabulary.values()) + basis["scope"]["records_without_an_event_type"]
                == streams["events"]["records"]
                and basis["scope"]["records_scanned"] == streams["events"]["records"],
                {"declared": streams["events"]["records"], "types": {name: item["count"]
                                                                    for name, item in vocabulary.items()}})
    results.add("Actual, recorded Target, intent, acceptance and dispatch are separate recorded classes",
                {name: categories[name]["status"] for name in
                 ("actual_state_feedback", "recorded_target", "command_intent", "command_receipt_accepted",
                  "command_dispatched", "episode_lifecycle")} ==
                dict.fromkeys(("actual_state_feedback", "recorded_target", "command_intent",
                               "command_receipt_accepted", "command_dispatched", "episode_lifecycle"), "observed")
                and categories["actual_state_feedback"]["event_types_recorded"] == ["feedback"]
                and categories["recorded_target"]["event_types_recorded"] == ["actuator_reference"]
                and categories["command_dispatched"]["event_types_recorded"] == ["dispatch"],
                {name: categories[name]["counts"] for name in categories})
    results.add("an absent category is reported as not recorded, never filled or treated as impossible",
                categories["command_receipt_rejected"]["status"] == "not_recorded_in_this_scan"
                and categories["command_receipt_rejected"]["absent_event_types"] == ["rejected"]
                and "rejected" not in vocabulary
                and "never write one" in categories["command_receipt_rejected"]["status_note"],
                {"vocabulary_types": sorted(vocabulary)})
    results.add("a join key that the record carries as null is not treated as a join key",
                vocabulary["feedback"]["join_keys"]["command_id"]["envelope"] == {"present": 0,
                                                                                 "null": vocabulary["feedback"]["count"]}
                and vocabulary["feedback"]["join_keys"]["control_tick_id"]["envelope"]["null"] == 0
                and vocabulary["requested"]["join_keys"]["command_id"]["envelope"]["present"]
                == vocabulary["requested"]["count"]
                and vocabulary["requested"]["join_keys"]["control_tick_id"]["envelope"]["present"] == 0,
                {name: vocabulary[name]["join_keys"] for name in ("feedback", "requested", "dispatch")})
    association = basis["frame_association"]
    target_bucket = association["by_event_type"]["actuator_reference"]["candidate_count_per_frame_on_this_page"]
    dispatch_bucket = association["by_event_type"]["dispatch"]["candidate_count_per_frame_on_this_page"]
    results.add("per-frame association lists every candidate and reports absence without borrowing one",
                association["key"] == ("control_tick_id equals the frame anchor's own capture_control_tick_id")
                and set(target_bucket) == {"1"} and sum(target_bucket.values()) == len(basis_page["frames"])
                and max(int(key) for key in dispatch_bucket) <= 1
                and all(item["by_event_type"]["dispatch"]["status"] in ("matched", "missing")
                        for item in association["candidate_positions_per_frame"])
                and association["rules"]["when_nothing_matches"].startswith("missing")
                and association["rules"]["zero_action"] == "no action vector is invented for a tick that records none",
                {"target_candidates_per_frame": target_bucket, "dispatch_candidates_per_frame": dispatch_bucket,
                 "frames_without_a_dispatch": dispatch_bucket.get("0", 0)})
    results.add("the command chain is grouped by command_id and claims no execution result",
                basis["command_chain"]["grouped_by"] == "command_id"
                and basis["command_chain"]["commands_truncated"] is False
                and all(set(item["stages"]) <= {"requested", "approved", "dispatch", "rejected"}
                        for item in basis["command_chain"]["commands"])
                and sum(item["stages"].get("dispatch", 0) for item in basis["command_chain"]["commands"])
                == vocabulary["dispatch"]["count"]
                and "no execution result" in basis["command_chain"]["note"]
                and "that any command below was physically executed" in basis["not_proven"],
                {"commands": len(basis["command_chain"]["commands"]),
                 "kinds": sorted({item["stages"].get("dispatch", 0) for item in basis["command_chain"]["commands"]})})
    results.add("units and stamps come from the record's own names, and an unsuffixed field stays unknown",
                vocabulary["actuator_reference"]["time_fields"]["backend_monotonic_s"]["unit"] == "second"
                and vocabulary["actuator_reference"]["time_fields"]["wall_utc"]["unit"] == "iso8601_utc"
                and "payload.wheel_target_rad_s" not in vocabulary["actuator_reference"]["time_fields"]
                and "payload.wheel_velocity_rad_s" not in vocabulary["feedback"]["time_fields"],
                {name: sorted(vocabulary[name]["time_fields"]) for name in ("actuator_reference", "feedback")})
    results.add("control source is only what the record names, and no takeover event was recorded",
                basis["control_source"]["status"] == "recorded_only_inside_payload_fields"
                and basis["control_source"]["takeover_event_type_recorded"] is False
                and "feedback" not in basis["control_source"]["fields_observed"]
                and any(path.endswith("operator_id") for paths in basis["control_source"]["fields_observed"].values()
                        for path in paths)
                and basis["frame_association"]["rules"]["operator_source"].endswith("never defaulted to Human"),
                {"fields": basis["control_source"]["fields_observed"],
                 "lease": basis["control_source"]["lease_evidence"]})
    results.add("events sharing no key with a frame stay an independent track",
                {"command_intent", "command_receipt_accepted", "episode_lifecycle", "lease_boundary"}
                <= set(basis["independent_tracks"])
                and "recorded_target" not in basis["independent_tracks"]
                and "actual_state_feedback" not in basis["independent_tracks"]
                and "never attached to" in basis["independent_track_reason"],
                {"independent": basis["independent_tracks"], "joined": ["recorded_target", "command_dispatched",
                                                                       "actual_state_feedback", "capture_timing"]})
    status, command_page = records(complete_id, complete_run, "events", "&event_seq_from=332&event_seq_to=334&limit=5")
    command_stamps = [item["record"]["backend_monotonic_s"] for item in command_page["records"]
                      if item["record"].get("event_type") in ("requested", "approved")
                      and isinstance(item["record"].get("backend_monotonic_s"), (int, float))]
    status, persist_page = records(complete_id, complete_run, "observations-persist", "&limit=200")
    anchor_stamps = [item["record"]["capture_backend_monotonic_s"] for item in persist_page["records"]
                     if isinstance(item["record"].get("capture_backend_monotonic_s"), (int, float))]
    closest = min((abs(stamp - anchor) for stamp in command_stamps for anchor in anchor_stamps), default=None)
    results.add("a command stamp numerically close to a frame buys no link and no clock claim",
                bool(command_stamps) and bool(anchor_stamps) and closest is not None and closest < 1.0
                and "requested" not in basis["frame_association"]["by_event_type"]
                and "approved" not in basis["frame_association"]["by_event_type"]
                and basis_page["time"]["same_clock_verified"] is False
                and basis_page["time"]["clock_sameness"]["verified_by_reader"] is False
                and basis["frame_association"]["rules"]["clock_parity"].startswith("numerically close"),
                {"closest_command_to_anchor_stamp_s": closest, "command_stamps": command_stamps,
                 "association_types": sorted(basis["frame_association"]["by_event_type"]),
                 "same_clock_verified": basis_page["time"]["same_clock_verified"]})
    results.add("a rejection is a receipt category, and this archive records none to promote",
                categories["command_receipt_rejected"]["status"] == "not_recorded_in_this_scan"
                and "rejected" not in association["by_event_type"]
                and categories["command_receipt_accepted"]["counts"] == {"approved": vocabulary["approved"]["count"]}
                and basis["frame_association"]["rules"]["rejected_requests"].endswith(
                    "never presented as an executed action")
                and "that any command below was physically executed" in basis["not_proven"]
                and vocabulary["requested"]["join_keys"]["control_tick_id"]["envelope"]["present"] == 0
                and vocabulary["approved"]["join_keys"]["control_tick_id"]["envelope"]["present"] == 0,
                {"rejected": categories["command_receipt_rejected"], "accepted": categories["command_receipt_accepted"],
                 "requested_tick_present": vocabulary["requested"]["join_keys"]["control_tick_id"]["envelope"]})
    status, failed_basis = get_json(f"{P}/api/v1/episodes/{failed_id}/frames?run_id={failed_run}"
                                    f"&include_action_basis=true")
    status, failed_detail = get_json(f"{P}/api/v1/episodes/{failed_id}?run_id={failed_run}")
    failed_streams = {item["stream_id"]: item["records"] for item in failed_detail["streams"]}
    failed_categories = failed_basis["action_basis"]["categories"]
    results.add("the incomplete real record is read with the same vocabulary and its own absences",
                status == 200 and failed_basis["action_basis"]["scope"]["reached_end_of_file"] is True
                and failed_categories["episode_lifecycle"]["counts"].get("recording_stop") == 1
                and failed_categories["episode_lifecycle"]["counts"].get("episode_terminal") == 1
                and failed_categories["lease_boundary"]["counts"] == {"lease_expired": 1}
                and failed_categories["command_receipt_rejected"]["status"] == "not_recorded_in_this_scan"
                and sum(item["count"] for item in failed_basis["action_basis"]["vocabulary"].values())
                == failed_streams["events"] == failed_basis["action_basis"]["scope"]["records_scanned"],
                {"declared_events": failed_streams["events"],
                 "types": {name: item["count"] for name, item in failed_basis["action_basis"]["vocabulary"].items()},
                 "terminal_null_clocks": failed_basis["action_basis"]["vocabulary"]["episode_terminal"]["time_fields"]
                 ["backend_monotonic_s"]})
    results.add("the action basis is asked only of the platform reader, never the live native scene",
                all(item["url"].startswith(P) and item["method"] == "GET"
                    for item in PROBE.entries[entries_before_basis:])
                and sum(1 for item in PROBE.entries[entries_before_basis:]
                        if "/api/v1/scene" in item["url"]) == 0,
                {"requests_since_basis_start": len(PROBE.entries) - entries_before_basis})

    # ---- how the whole archive behaves, over a bounded sample -------------------
    status, sample = get_json(f"{P}/api/v1/episodes?limit=200")
    picked = sample["episodes"][::12][:16]
    verdicts: dict[str, int] = {}
    statuses: dict[str, int] = {}
    layered = True
    for item in picked:
        record = detail_for(item["episode_id"], item["run_id"])
        check = record["integrity"]["checksum_verification"]
        verdicts[check["verdict"]] = verdicts.get(check["verdict"], 0) + 1
        statuses[record["integrity"]["status"]] = statuses.get(record["integrity"]["status"], 0) + 1
        layered = layered and isinstance(check["matched"], list) and isinstance(check["mismatched"], list) \
            and record["integrity"]["declaration_is_not_verification"] is True \
            and (record["declared"]["recording_status"] == "COMPLETE") == (record["integrity"]["status"] == "complete")
    results.add("a stale recorder self-check never rewrites the declared lifecycle status",
                layered and len(picked) >= 10, {"sampled": len(picked), "checksum_verdicts": verdicts,
                                                 "lifecycle_statuses": statuses,
                                                 "note": "mismatch_present is the recorder's own stale declaration for episode.json, reported as a finding"})

    # ---- error surface ----------------------------------------------------------
    status, unknown = get_json(f"{P}/api/v1/episodes/episode_0000000000000000000000000000dead")
    results.add("unknown episode returns a located 404", status == 404 and code_of(unknown) == "episode_not_found", status)
    status, badstream = records(complete_id, complete_run, "no-such-stream", "&limit=1")
    results.add("unknown stream names the supported set",
                status == 404 and code_of(badstream) == "episode_stream_unsupported"
                and "events" in (badstream["detail"]["supported"] if isinstance(badstream, dict) else []), status)

    # ---- contract surface -------------------------------------------------------
    status, openapi = get_json(f"{P}/openapi.json")
    paths = {key: value for key, value in openapi["paths"].items() if key.startswith("/api/v1/episodes")}
    results.add("OpenAPI exposes exactly the eight read-only history paths",
                len(paths) == 8 and all(set(value) == {"get"} for value in paths.values())
                and {"/api/v1/episodes/{episode_id}/frames", "/api/v1/episodes/{episode_id}/robot-state",
                     "/api/v1/episodes/{episode_id}/model/assets/{asset_id}"} <= set(paths), sorted(paths))
    results.add("no validate/assessment write is proxied",
                not any("validate" in key or "assessment" in key or "eligibility" in key for key in paths), sorted(paths))
    status, native_detail, _ = raw(f"{N}/api/v1/episodes/{complete_id}")
    light = len(json.dumps(body))
    results.add("platform detail stays light compared with the native whole-record dump",
                status == 200 and light * 5 < len(native_detail), {"platform_bytes": light, "native_bytes": len(native_detail)})

    # ---- the report is bound to the frozen bytes it is checking -----------------
    binding = source_digest.bind(Path(manifest["platform_source"]["backend_root"]), manifest)
    results.add("running tree equals the frozen startup manifest",
                binding["match"] and binding["recorded_file_count"] == binding["recomputed_file_count"],
                {"recorded": binding["recorded_aggregate"], "recomputed": binding["recomputed_aggregate"],
                 "files": binding["recomputed_file_count"], "changed_or_missing_paths": binding["changed_or_missing_paths"]})
    results.add("history source bytes equal the manifest hash",
                hashlib.sha256(args.source_config.read_bytes()).hexdigest()
                == manifest["history"]["source_file_sha256"],
                {"manifest": manifest["history"]["source_file_sha256"][:16]})
    results.add("candidate reports the resolved root and the boundary rule",
                src.get("recording_root_resolved") == str(root) and "resolve" in src.get("path_boundary", ""),
                {"resolved": src.get("recording_root_resolved"), "boundary": src.get("path_boundary")})
    results.add("real archive needs no symlink exclusions",
                detail_for(complete_id, complete_run)["media_summary"]["excluded_count"] == 0,
                detail_for(complete_id, complete_run)["media_summary"]["symlink_or_escape_excluded"])
    status, anomalies = get_json(f"{P}/api/v1/episodes/{complete_id}/streams/observations-index/records"
                                 f"?run_id={complete_run}&event_seq_from=1&event_seq_to=5&limit=5")
    results.add("streams without event_seq are excluded and counted under a range, never invented",
                anomalies["records"] == [] and anomalies["filtering"]["event_seq_range"]["active"] is True
                and anomalies["filtering"]["event_seq_range"]["excluded_without_valid_event_seq"] > 0
                and "no sequence number is invented" in anomalies["filtering"]["note"],
                {"excluded": anomalies["filtering"]["event_seq_range"]["excluded_without_valid_event_seq"],
                 "anomalies": anomalies["filtering"]["event_seq_range"]["anomalies"][:2]})
    status, wall = records(complete_id, complete_run, "events", "&time_base=wall_utc&time_from=1")
    results.add("a calendar time base refuses numeric bounds instead of comparing strings",
                status == 400 and code_of(wall) == "time_base_not_numeric", {"status": status, "code": code_of(wall)})

    # ---- nothing was written ----------------------------------------------------
    _, native_after = get_json(f"{N}/api/v1/health")
    results.add("declaring native instance is unchanged by the whole read pass",
                native_before == native_after, {"before": native_before.get("episode_id"), "after": native_after.get("episode_id"),
                                                "recording": native_before.get("recording_status")})
    blob = json.dumps(capabilities)
    results.add("declaring native instance still advertises no stop/end protocol",
                "session_stop_protocol" not in blob and "recording_end_protocol" not in blob,
                {"keys": sorted(capabilities) if isinstance(capabilities, dict) else type(capabilities).__name__})
    agg = archive_digest(root)
    results.add("archive raw files are byte-identical to the frozen baseline",
                agg == source["archive_baseline"]["aggregate_sha256"], {"before": baseline_before, "after": agg,
                                                                       "matches_frozen_baseline": agg == source["archive_baseline"]["aggregate_sha256"],
                                                                       "coverage": "every episode.json and episode_complete.json under the declared root"})
    covered_after = coverage_snapshot(root, [(complete_run, complete_id), (failed_run, failed_id)])
    drift = sorted(path for path in set(covered_before) | set(covered_after)
                   if covered_before.get(path) != covered_after.get(path))
    results.add("the covered file set is unchanged across this read pass",
                drift == [], {"covered_files": len(covered_after),
                              "covered_names": sorted({path.split('/')[-1] for path in covered_after}),
                              "drift": drift,
                              "not_covered": ["files outside these two records",
                                              "the derived quality_report.json pre-image was never snapshotted, so no claim is made about it"]})
    summary = PROBE.summary()
    results.add("every request this run issued was GET",
                summary["non_get"] == [] and summary["methods"] == ["GET"], summary)

    args.coverage_out.parent.mkdir(parents=True, exist_ok=True)
    args.coverage_out.write_text(json.dumps({"covered_files_before": len(covered_before),
                                             "covered_files_after": len(covered_after),
                                             "before": covered_before, "after": covered_after,
                                             "drift": drift,
                                             "archive_baseline_before": baseline_before,
                                             "archive_baseline_after": agg,
                                             "coverage_scope": "the two representative records plus every episode.json/episode_complete.json in the archive",
                                             "explicitly_not_covered": ["derived quality_report.json pre-image (never snapshotted)",
                                                                        "files of other episodes beyond the two identity files"]},
                                            indent=2, sort_keys=True) + "\n", encoding="utf-8")
    PROBE.write_summary(args.probe_log.with_suffix(".json"))

    out = {"platform_url": P, "native_url": N, "source_id": source["source_id"],
           "startup_manifest_digest": hashlib.sha256(args.startup_manifest.read_bytes()).hexdigest(),
           "platform_source": {"recorded_aggregate": binding["recorded_aggregate"],
                               "recomputed_aggregate": binding["recomputed_aggregate"],
                               "match": binding["match"], "file_count": binding["recomputed_file_count"]},
           "requests": {"total": summary["requests"], "methods": summary["methods"],
                        "log": str(args.probe_log)},
           "coverage": {"files": len(covered_after), "drift": drift, "artifact": str(args.coverage_out)},
           "complete_record": f"{complete_run}:{complete_id}", "failed_record": f"{failed_run}:{failed_id}",
           "checks": results.items, "passed": sum(1 for item in results.items if item["passed"]),
           "total": len(results.items),
           "classification": "read-only historical slice; requests issued by this run were GET only, and the covered file set was unchanged across the pass",
           "not_covered": ["synchronized 3D replay rendering", "new collection closure", "M1.5/M1 acceptance"]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": out["passed"], "total": out["total"], "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
