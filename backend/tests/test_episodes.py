"""Focused coverage for the read-only historical Episode reader.

Every fixture here is an isolated copy under tmp_path: the real archive is never
written to, and no recording is started to manufacture a failure case.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from unirobot.api import create_app

PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000a49444154789c6300010000050001"
                    "0d0a2db40000000049454e44ae426082")


def _episode(root: Path, run_id: str, episode_id: str, *, recording="COMPLETE", audit="COMPLETE",
             tail=True, events=None, checksums=True, transforms=True, media=True, task_result="failure",
             result="failure", sidecar: dict | None = None, task_language="pick the red block") -> Path:
    directory = root / run_id / "episodes" / episode_id
    directory.mkdir(parents=True, exist_ok=True)
    (root / run_id / "manifest.json").write_text(json.dumps({
        "contract_version": "mobilecar-1.0", "run_id": run_id,
        "model_id": "landerpi_mecanum_dynamic_5dof_recordedonly",
        "model_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "scene_id": "mobile_pick", "map_mode": "unavailable",
        "truth_access": "GT_DEBUG_SEPARATE_FROM_DEFAULT_OBSERVATION",
        "clocks": ["sim", "backend_monotonic", "device", "wall_utc"]}), encoding="utf-8")
    episode = {
        "contract_version": "mobilecar-1.0", "run_id": run_id, "episode_id": episode_id,
        "task_language": task_language, "operator_id": "operator-1", "operator_kind": "agent_ui",
        "view_source": "third_person_3d", "map_mode": "unavailable", "require_recording": True,
        "created_wall_utc": "2026-10-17T16:10:29.710217Z", "ended_wall_utc": "2026-10-17T16:11:31.300807Z",
        "recording_status": recording, "audit_status": audit, "result": result, "task_result": task_result,
        "termination_reason": "USER_STOP" if recording == "FAILED" else "OPERATOR_FINISHED",
        "segments": [{"recording_segment_id": "seg_001_abc", "previous_recording_segment_id": None,
                      "status": recording, "reason": "ok", "started_wall_utc": "2026-10-17T16:10:29.710250Z",
                      "ended_wall_utc": "2026-10-17T16:11:31.300794Z", "started_backend_monotonic_s": 426494.22}],
    }
    (directory / "episode.json").write_text(json.dumps(episode), encoding="utf-8")
    (directory / "initial_snapshot.json").write_text(json.dumps({"contract_version": "mobilecar-1.0",
                                                                "snapshot": {"base_pose_m": [0, 0, 0]}}), encoding="utf-8")
    lines = events if events is not None else [
        {"contract_version": "mobilecar-1.0", "run_id": run_id, "episode_id": episode_id, "event_seq": 1,
         "event_type": "recording_start", "wall_utc": "2026-10-17T16:10:29.711000Z",
         "backend_monotonic_s": 426494.23, "sim_time_s": 0.0, "payload": {"recording_segment_id": "seg_001_abc"}},
        {"contract_version": "mobilecar-1.0", "run_id": run_id, "episode_id": episode_id, "event_seq": 2,
         "event_type": "feedback_initial", "wall_utc": "2026-10-17T16:10:29.712000Z",
         "backend_monotonic_s": 426494.24, "sim_time_s": 0.01,
         "payload": {"request": {"backend_generation": 7}, "snapshot": {"base_twist_m_s": [0.1, 0.0, 0.0]}}},
        {"contract_version": "mobilecar-1.0", "run_id": run_id, "episode_id": episode_id, "event_seq": 3,
         "event_type": "actuator_reference", "wall_utc": "2026-10-17T16:10:29.716000Z",
         "backend_monotonic_s": 426494.31, "sim_time_s": 0.02, "control_tick_id": "tick_1",
         "payload": {"target_velocity_m_s": [0.2, 0.0, 0.0]}},
        {"contract_version": "mobilecar-1.0", "run_id": run_id, "episode_id": episode_id, "event_seq": 4,
         "event_type": "requested", "wall_utc": "2026-10-17T16:10:29.720000Z", "command_id": "cmd-1",
         "payload": {"intent": "drive"}},
        {"contract_version": "mobilecar-1.0", "run_id": run_id, "episode_id": episode_id, "event_seq": 5,
         "event_type": "feedback", "wall_utc": "2026-10-17T16:10:29.730000Z", "command_id": "cmd-1",
         "payload": {"applied_velocity_m_s": [0.19, 0.0, 0.0]}},
        {"contract_version": "mobilecar-1.0", "run_id": run_id, "episode_id": episode_id, "event_seq": 6,
         "event_type": "episode_terminal", "wall_utc": "2026-10-17T16:11:31.300000Z",
         "payload": {"recording_segment_id": "seg_001_abc", "recording_status": recording}},
    ]
    (directory / "events.jsonl").write_text("".join(
        (item if isinstance(item, str) else json.dumps(item)) + "\n" for item in lines), encoding="utf-8")
    (directory / "control.jsonl").write_text(json.dumps({
        "contract_version": "mobilecar-1.0", "run_id": run_id, "episode_id": episode_id, "event_seq": 3,
        "event_type": "actuator_reference", "backend_monotonic_s": 426494.31, "sim_time_s": 0.02,
        "control_tick_id": "tick_1", "payload": {"target_velocity_m_s": [0.2, 0.0, 0.0]}}) + "\n", encoding="utf-8")
    (directory / "commands.jsonl").write_text(json.dumps({
        "contract_version": "mobilecar-1.0", "run_id": run_id, "episode_id": episode_id,
        "event_seq": 4, "event_type": "requested", "wall_utc": "2026-10-17T16:10:29.720000Z"}) + "\n", encoding="utf-8")
    (directory / "observations" / "index.jsonl").parent.mkdir(exist_ok=True)
    (directory / "observations" / "index.jsonl").write_text(json.dumps({
        "contract_version": "mobilecar-1.0", "run_id": run_id, "episode_id": episode_id, "stream_id": "lidar",
        "sample_id": "laser_1", "sensor_kind": "lidar", "measurement_time_s": 426494.249,
        "arrival_time_s": 426494.249, "clock_id": "backend_monotonic", "frame_id": "base_link",
        "source": "mujoco_mj_ray", "quality": "simulated_raycast",
        "value": {"ranges_m": [None, 1.2], "angle_increment_rad": 0.017}}) + "\n", encoding="utf-8")
    (directory / "observations" / "persist.jsonl").write_text(json.dumps({
        "contract_version": "mobilecar-1.0", "persist_sequence": 1, "persist_backend_monotonic_s": 426494.9,
        "arrival_to_persist_ms": 12.5}) + "\n", encoding="utf-8")
    if transforms:
        (directory / "transforms.jsonl").write_text(json.dumps({
            "contract_version": "mobilecar-1.0", "run_id": run_id, "episode_id": episode_id,
            "event_seq": 7, "body": "base_link", "position_m": [0.1, 0.2, 0.0],
            "orientation_wxyz": [1.0, 0.0, 0.0, 0.0], "sim_time_s": 0.02}) + "\n", encoding="utf-8")
    if media:
        (directory / "assets" / "rgb").mkdir(parents=True, exist_ok=True)
        (directory / "assets" / "rgb" / "frame_1_rgb.png").write_bytes(PNG)
        (directory / "assets" / "depth").mkdir(parents=True, exist_ok=True)
        (directory / "assets" / "depth" / "frame_1_depth.npy").write_bytes(b"\x93NUMPY\x01\x00")
        (directory / "assets" / "tool.exe").write_bytes(b"MZ")
    if tail:
        digests = {}
        if checksums:
            for name in ("episode.json", "episode_complete.json"):
                digests[name] = hashlib.sha256((directory / name).read_bytes()).hexdigest() if (directory / name).is_file() else None
            digests = {key: value for key, value in digests.items() if value}
            if (directory / "assets" / "rgb" / "frame_1_rgb.png").is_file():
                digests["assets/rgb/frame_1_rgb.png"] = hashlib.sha256(PNG).hexdigest()
        (directory / "episode_complete.json").write_text(json.dumps({
            "contract_version": "mobilecar-1.0", "run_id": run_id, "episode_id": episode_id,
            "recording_segment_id": "seg_001_abc", "termination_reason": "OPERATOR_FINISHED",
            "audit_status": audit, "closed_wall_utc": "2026-10-17T16:11:31.400000Z",
            "event_count": len(lines), "checksums": digests}), encoding="utf-8")
    if sidecar is not None:
        (directory / "platform_session.json").write_text(json.dumps(sidecar), encoding="utf-8")
    return directory


def _client(root: Path, tmp_path: Path) -> TestClient:
    source = tmp_path / "history-source.json"
    source.write_text(json.dumps({
        "schema_version": "unirobot-history-source-1", "source_id": "fixture-history", "adapter_id": "mobilecar",
        "robot_id": "landerpi", "contract_version": "mobilecar-1.0", "reader_format": "native recorder layout",
        "recording_root": str(root),
        "native_release_id": "fixture-release", "declaring_instance": {"base_url": "http://127.0.0.1:1",
                                                                       "access": "GET_only"},
        "access": "read_only_files", "declared_scale": {"episodes_from_native_list": 2},
        "archive_baseline": {"files_hashed": 0}, "policy": {"platform_writes": False}}), encoding="utf-8")
    application = create_app(draft_db_path=tmp_path / "drafts.sqlite3", history_source_path=source)
    return TestClient(application)


def test_list_is_bounded_and_keeps_native_identity(tmp_path):
    root = tmp_path / "runs"
    _episode(root, "run_aaa", "episode_one")
    _episode(root, "run_bbb", "episode_two", recording="FAILED", audit="INCOMPLETE")
    client = _client(root, tmp_path)

    body = client.get("/api/v1/episodes?limit=1").json()
    assert body["schema_version"] == "unirobot-mobilecar-episode-read-1"
    assert body["read_only"] is True
    assert body["paging"]["limit"] == 1 and body["paging"]["total_matches"] == 2
    assert body["paging"]["next_offset"] == 1
    assert body["source"]["access"] == "read_only_files"
    item = body["episodes"][0]
    assert {"run_id", "episode_id", "declared", "declaration_only"} <= item.keys()
    assert item["declaration_only"] is True

    failed = client.get("/api/v1/episodes?recording_status=FAILED").json()["episodes"]
    assert [entry["episode_id"] for entry in failed] == ["episode_two"]
    assert failed[0]["declared"]["recording_status"] == "FAILED"


def test_detail_layers_declared_and_verified_and_refuses_to_inherit_live_state(tmp_path):
    root = tmp_path / "runs"
    _episode(root, "run_aaa", "episode_one")
    client = _client(root, tmp_path)

    body = client.get("/api/v1/episodes/episode_one").json()
    assert body["identity"]["run_id"] == "run_aaa"
    assert body["identity"]["segments"][0]["recording_segment_id"] == "seg_001_abc"
    assert body["identity"]["backend_generation"]["distinct_values"] == [7]
    assert body["identity"]["episode_display_name_is_not_a_key"] is True
    assert body["declared"]["recording_status"] == "COMPLETE"
    assert body["integrity"]["status"] == "complete"
    assert body["integrity"]["declaration_is_not_verification"] is True
    # Only the files this request actually opened are re-computed against the declared checksums.
    check = body["integrity"]["checksum_verification"]
    assert {item["relative_path"] for item in check["matched"]} == {"episode.json"}
    assert check["mismatched"] == [] and check["verdict"] == "all_matched"
    assert check["declared_entries"] == 2
    assert body["integrity"]["this_read_evidence"]["files_recomputed_here"] == ["episode.json", "episode_complete.json"]
    assert "archive-wide per-record checksum verification" in body["integrity"]["not_verified"]
    assert body["time"]["record_order_is_native_append_order"] is True
    assert body["time"]["synchronized_across_streams"] is False
    assert body["action_semantics"]["recorded_target"] == ["actuator_reference"]
    assert body["platform_association"]["known"] is False
    assert body["platform_association"]["reason"] == "legacy_native_record_without_platform_sidecar"
    assert body["training_qualification"]["blocks_raw_read"] is False
    assert body["three_d_replay"]["status"] == "restricted"
    assert body["three_d_replay"]["model_match"] == "mismatch"
    assert body["three_d_replay"]["live_geometry_or_actual_may_be_applied"] is False
    assert any("live Actual/geometry is never substituted" in reason for reason in body["three_d_replay"]["reasons"])
    assert body["three_d_replay"]["recorded_model_sha256"].startswith("aaaa")
    assert body["recorded_model_identity"]["scene_id"] == "mobile_pick"
    assert body["media_summary"]["kinds"]["rgb"]["count"] == 1


def test_recorded_identity_match_is_reported_without_claiming_rendered_replay(tmp_path):
    from unirobot.episodes import EpisodeArchive, load_history_source
    root = tmp_path / "runs"
    _episode(root, "run_aaa", "episode_one")
    _client(root, tmp_path)  # writes the history source declaration for this fixture archive
    source, resolved = load_history_source(tmp_path / "history-source.json")
    archive = EpisodeArchive(source, resolved,
                            reference_model_sha256="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                            reference_scene_id="mobile_pick")
    three_d = archive.detail("episode_one")["three_d_replay"]
    assert three_d["status"] == "identity_verified_rendering_unverified"
    assert three_d["model_match"] == "match" and three_d["scene_match"] == "match"
    assert three_d["live_geometry_or_actual_may_be_applied"] is False
    assert any("rendered-replay correctness is not verified" in reason for reason in three_d["reasons"])
    # a different reference pin must flip it back to restricted rather than guessing
    other = EpisodeArchive(source, resolved, reference_model_sha256="b" * 64, reference_scene_id="mobile_pick")
    assert other.detail("episode_one")["three_d_replay"]["status"] == "restricted"


def test_sidecar_association_is_read_when_the_record_really_carries_one(tmp_path):
    root = tmp_path / "runs"
    _episode(root, "run_aaa", "episode_one", sidecar={"platform_session_id": "sess-1",
                                                      "validated_snapshot_ref": "snap-1"})
    body = _client(root, tmp_path).get("/api/v1/episodes/episode_one").json()
    assert body["platform_association"] == {"known": True, "source": "platform_session.json sidecar",
                                           "sidecar_error": None, "validated_snapshot_ref": "snap-1",
                                           "platform_session_id": "sess-1"}


def test_records_page_by_native_append_order_not_by_whole_file(tmp_path):
    root = tmp_path / "runs"
    _episode(root, "run_aaa", "episode_one")
    client = _client(root, tmp_path)

    first = client.get("/api/v1/episodes/episode_one/streams/events/records?limit=2").json()
    assert [item["record"]["event_seq"] for item in first["records"]] == [1, 2]
    assert first["paging"]["next_offset"] == 2 and first["paging"]["has_more"] is True
    assert first["cursor"]["line_index_is_not_a_clock"] is True

    second = client.get("/api/v1/episodes/episode_one/streams/events/records?limit=2&offset=2").json()
    assert [item["record"]["event_seq"] for item in second["records"]] == [3, 4]
    assert second["cursor"]["first_line_index"] == 2

    window = client.get("/api/v1/episodes/episode_one/streams/events/records"
                        "?event_seq_from=5&event_seq_to=6").json()
    assert [item["record"]["event_seq"] for item in window["records"]] == [5, 6]

    timed = client.get("/api/v1/episodes/episode_one/streams/events/records"
                       "?time_base=sim_time_s&time_from=0.02").json()
    assert all(item["record"]["sim_time_s"] >= 0.02 for item in timed["records"])

    unknown_base = client.get("/api/v1/episodes/episode_one/streams/events/records"
                              "?time_base=browser_arrival&time_from=1").json()
    assert client.get("/api/v1/episodes/episode_one/streams/events/records"
                      "?time_base=browser_arrival&time_from=1").status_code == 400
    assert unknown_base["detail"]["code"] == "time_base_unsupported"

    baseless = client.get("/api/v1/episodes/episode_one/streams/commands/records"
                          "?time_base=sim_time_s&time_from=0.0").json()
    assert baseless["records"] == []
    assert baseless["time"]["records_without_the_selected_base"] == 1

    missing = client.get("/api/v1/episodes/episode_one/streams/episode/records").json()
    assert missing["records"][0]["record"]["episode_id"] == "episode_one"


def test_streams_report_availability_counts_and_absence(tmp_path):
    root = tmp_path / "runs"
    _episode(root, "run_aaa", "episode_one", transforms=False)
    catalog = _client(root, tmp_path).get("/api/v1/episodes/episode_one/streams").json()
    by_id = {item["stream_id"]: item for item in catalog["streams"]}
    assert by_id["transforms"]["available"] is False
    assert by_id["transforms"]["reason"] == "stream_not_recorded_or_missing"
    assert by_id["events"]["available"] is True and by_id["events"]["records"] == 6
    assert by_id["observations-index"]["relative_path"] == "observations/index.jsonl"
    assert by_id["initial-snapshot"]["format"] == "json"

    refused = root / "run_aaa" / "episodes" / "episode_one" / "events.jsonl"
    assert refused.is_file()
    unavailable = _client(root, tmp_path).get("/api/v1/episodes/episode_one/streams/transforms/records")
    assert unavailable.status_code == 404 and unavailable.json()["detail"]["code"] == "episode_stream_unavailable"
    unsupported = _client(root, tmp_path).get("/api/v1/episodes/episode_one/streams/nope/records")
    assert unsupported.status_code == 404 and unsupported.json()["detail"]["code"] == "episode_stream_unsupported"


def test_assets_are_confined_to_the_episode_assets_tree(tmp_path):
    root = tmp_path / "runs"
    _episode(root, "run_aaa", "episode_one")
    _episode(root, "run_bbb", "episode_two")
    client = _client(root, tmp_path)

    digest = hashlib.sha256(PNG).hexdigest()
    ok = client.get(f"/api/v1/episodes/episode_one/assets/rgb/frame_1_rgb.png?sha256={digest}")
    assert ok.status_code == 200 and ok.headers["content-type"] == "image/png"
    assert ok.headers["X-Episode-Asset-Sha256"] == digest
    assert ok.headers["X-Episode-Run-Id"] == "run_aaa"

    # the native URI form recorded in the observation metadata resolves to the same file
    prefixed = client.get(f"/api/v1/episodes/episode_one/assets/assets/rgb/frame_1_rgb.png?sha256={digest}")
    assert prefixed.status_code == 200 and prefixed.content == ok.content

    mismatch = client.get("/api/v1/episodes/episode_one/assets/rgb/frame_1_rgb.png"
                          f"?sha256={'0' * 64}")
    assert mismatch.status_code == 409 and mismatch.json()["detail"]["code"] == "episode_asset_digest_mismatch"

    # a symlink inside the episode that points at another episode must not be followed
    link = root / "run_aaa" / "episodes" / "episode_one" / "assets" / "rgb" / "link.png"
    link.symlink_to(root / "run_bbb" / "episodes" / "episode_two" / "assets" / "rgb" / "frame_1_rgb.png")

    cases = [("rgb/%2e%2e/%2e%2e/%2e%2e/episode_two/assets/rgb/frame_1_rgb.png", "episode_asset_path_invalid"),
             ("rgb/link.png", "episode_asset_escape"),
             ("events.jsonl", "episode_asset_missing"),
             ("rgb/no_such.png", "episode_asset_missing"),
             ("tool.exe", "episode_asset_type_unsupported")]
    for path, code in cases:
        response = client.get(f"/api/v1/episodes/episode_one/assets/{path}")
        assert response.status_code in (400, 404, 409, 415), (path, response.status_code)
        assert response.json()["detail"]["code"] == code, (path, response.json())

    # traversal that a URL client would otherwise normalize is checked at the service boundary
    from unirobot.episodes import HistoryError, load_history_source, EpisodeArchive
    source, root_resolved = load_history_source(tmp_path / "history-source.json")
    archive = EpisodeArchive(source, root_resolved)
    for attempt in ("../episode_two/assets/rgb/frame_1_rgb.png", "/etc/passwd",
                    "rgb/../../../../etc/passwd", "assets/../../episode_two/assets/rgb/frame_1_rgb.png"):
        try:
            archive.resolve_asset("episode_one", attempt)
            raise AssertionError(f"{attempt} should not resolve")
        except HistoryError as exc:
            assert exc.code == "episode_asset_path_invalid", (attempt, exc.code)


def test_stale_declared_checksum_is_reported_instead_of_relabelled(tmp_path):
    root = tmp_path / "runs"
    directory = _episode(root, "run_aaa", "episode_one")
    client = _client(root, tmp_path)
    path = directory / "episode.json"
    path.write_text(path.read_text() + " ", encoding="utf-8")

    body = client.get("/api/v1/episodes/episode_one").json()
    check = body["integrity"]["checksum_verification"]
    assert check["verdict"] == "mismatch_present"
    assert [item["relative_path"] for item in check["mismatched"]] == ["episode.json"]
    assert check["matched"] == []
    # the lifecycle closure stays what the record declares; the stale self-check does not rewrite it
    assert body["integrity"]["status"] == "complete"
    assert body["declared"]["recording_status"] == "COMPLETE"
    assert body["integrity"]["declaration_is_not_verification"] is True


def test_incomplete_and_corrupt_records_are_located_not_hidden(tmp_path):
    root = tmp_path / "runs"
    _episode(root, "run_aaa", "episode_failed", recording="FAILED", audit="INCOMPLETE")
    _episode(root, "run_bbb", "episode_no_tail", tail=False)
    _episode(root, "run_ccc", "episode_corrupt", events=[
        {"contract_version": "mobilecar-1.0", "event_seq": 1, "event_type": "recording_start"},
        '{"broken": ',
    ])
    client = _client(root, tmp_path)

    failed = client.get("/api/v1/episodes/episode_failed").json()
    assert failed["integrity"]["status"] == "incomplete_terminal_recorded"
    assert failed["declared"]["complete_tail_file_present"] is True

    no_tail = client.get("/api/v1/episodes/episode_no_tail").json()
    assert no_tail["integrity"]["status"] == "finalize_failed_missing_tail"
    assert no_tail["declared"]["complete_tail_file_present"] is False

    bad = client.get("/api/v1/episodes/episode_corrupt/streams/events/records").json()
    assert bad["integrity"]["corrupt_lines"]
    assert bad["integrity"]["corrupt_lines"][0]["line_index"] == 1
    assert [item["record"]["event_seq"] for item in bad["records"]] == [1]

    damaged = root / "run_aaa" / "episodes" / "episode_failed" / "episode.json"
    original = damaged.read_text()
    damaged.write_text("{not json")
    broken = client.get("/api/v1/episodes/episode_failed").json()
    assert broken["integrity"]["status"] == "unknown"
    assert broken["declared"]["episode_json_readable"] is False
    damaged.write_text(original)


def test_same_episode_id_under_two_runs_never_cross_reads(tmp_path):
    root = tmp_path / "runs"
    _episode(root, "run_aaa", "episode_dup", task_language="from run aaa")
    _episode(root, "run_bbb", "episode_dup", task_language="from run bbb")
    client = _client(root, tmp_path)

    ambiguous = client.get("/api/v1/episodes/episode_dup")
    assert ambiguous.status_code == 409
    assert ambiguous.json()["detail"]["code"] == "episode_id_ambiguous"
    assert set(ambiguous.json()["detail"]["runs"]) == {"run_aaa", "run_bbb"}

    scoped = client.get("/api/v1/episodes/episode_dup?run_id=run_bbb").json()
    assert scoped["identity"]["run_id"] == "run_bbb"
    assert scoped["identity"]["episode_display_name_is_not_a_key"] is True

    missing = client.get("/api/v1/episodes/episode_absent")
    assert missing.status_code == 404 and missing.json()["detail"]["code"] == "episode_not_found"


def test_history_source_without_readable_root_refuses_instead_of_faking(tmp_path):
    source = tmp_path / "history-source.json"
    source.write_text(json.dumps({
        "schema_version": "unirobot-history-source-1", "source_id": "missing", "adapter_id": "mobilecar",
        "robot_id": "landerpi", "contract_version": "mobilecar-1.0", "reader_format": "native recorder layout",
        "recording_root": str(tmp_path / "nowhere"),
        "native_release_id": "x", "declaring_instance": {}, "access": "read_only_files",
        "declared_scale": {}, "archive_baseline": {}, "policy": {}}), encoding="utf-8")
    client = TestClient(create_app(draft_db_path=tmp_path / "drafts.sqlite3", history_source_path=source))
    response = client.get("/api/v1/episodes")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "history_source_unavailable"


def test_openapi_exposes_the_history_slice_and_no_write_routes(tmp_path):
    root = tmp_path / "runs"
    _episode(root, "run_aaa", "episode_one")
    paths = _client(root, tmp_path).get("/openapi.json").json()["paths"]
    history = sorted(key for key in paths if key.startswith("/api/v1/episodes"))
    assert history == ["/api/v1/episodes", "/api/v1/episodes/{episode_id}",
                       "/api/v1/episodes/{episode_id}/assets/{asset_path}",
                       "/api/v1/episodes/{episode_id}/streams",
                       "/api/v1/episodes/{episode_id}/streams/{stream_id}/records"]
    for item in history:
        assert set(paths[item]) == {"get"}, item
    assert "/api/v1/episodes/{episode_id}/validate" not in paths
