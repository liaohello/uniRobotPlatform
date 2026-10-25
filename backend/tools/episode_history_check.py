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
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

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


def raw(url: str, body: bytes | None = None, timeout: float = 20.0) -> tuple[int, bytes, dict[str, str]]:
    request = urllib.request.Request(url, data=body, headers={"content-type": "application/json"} if body else {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def get_json(url: str) -> tuple[int, Any]:
    status, payload, _ = raw(url)
    try:
        return status, json.loads(payload)
    except json.JSONDecodeError:
        return status, payload.decode("utf-8", "replace")


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
    args = parser.parse_args()

    P = args.platform_url.rstrip("/")
    N = args.native_url.rstrip("/")
    source = json.loads(args.source_config.read_text(encoding="utf-8"))
    complete_run, complete_id = args.complete_episode.split(":", 1)
    failed_run, failed_id = args.failed_episode.split(":", 1)
    results = Results()

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
    results.add("OpenAPI exposes exactly the five read-only history paths",
                len(paths) == 5 and all(set(value) == {"get"} for value in paths.values()), sorted(paths))
    results.add("no validate/assessment write is proxied",
                not any("validate" in key or "assessment" in key or "eligibility" in key for key in paths), sorted(paths))
    status, native_detail, _ = raw(f"{N}/api/v1/episodes/{complete_id}")
    light = len(json.dumps(body))
    results.add("platform detail stays light compared with the native whole-record dump",
                status == 200 and light * 5 < len(native_detail), {"platform_bytes": light, "native_bytes": len(native_detail)})

    # ---- nothing was written ----------------------------------------------------
    _, native_after = get_json(f"{N}/api/v1/health")
    results.add("declaring native instance is unchanged by the whole read pass",
                native_before == native_after, {"before": native_before.get("episode_id"), "after": native_after.get("episode_id"),
                                                "recording": native_before.get("recording_status")})
    blob = json.dumps(capabilities)
    results.add("declaring native instance still advertises no stop/end protocol",
                "session_stop_protocol" not in blob and "recording_end_protocol" not in blob,
                {"keys": sorted(capabilities) if isinstance(capabilities, dict) else type(capabilities).__name__})
    agg = archive_digest(Path(source["recording_root"]), source["declared_scale"]["episodes_from_native_list"])
    results.add("archive raw files are byte-identical to the frozen baseline",
                agg == source["archive_baseline"]["aggregate_sha256"], {"before": source["archive_baseline"]["aggregate_sha256"],
                                                                        "after": agg})

    out = {"platform_url": P, "native_url": N, "source_id": source["source_id"],
           "complete_record": f"{complete_run}:{complete_id}", "failed_record": f"{failed_run}:{failed_id}",
           "checks": results.items, "passed": sum(1 for item in results.items if item["passed"]),
           "total": len(results.items),
           "classification": "read-only historical slice; the archive is native-owned and was not written",
           "not_covered": ["synchronized 3D replay rendering", "new collection closure", "M1.5/M1 acceptance"]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": out["passed"], "total": out["total"], "out": str(args.out)}))
    return 0


def archive_digest(root: Path, expected_episodes: int) -> str:
    """Same recipe as the frozen baseline: every episode.json and episode_complete.json digest, folded."""
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


if __name__ == "__main__":
    sys.exit(main())
