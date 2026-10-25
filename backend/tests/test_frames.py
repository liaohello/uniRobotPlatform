"""Focused coverage for run-directory identity and the read-only frame linkage slice.

Every fixture is an isolated copy under tmp_path, written in the shape measured on the real
recorder (persist/index/transforms/events field names). The real archive is never modified, and
no recording is started to manufacture a case.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from test_episodes import PNG, _episode
from unirobot.episodes import EpisodeArchive, HistoryError, load_history_source

RUN = "run_aaa"
EPISODE = "episode_one"
F1 = "rgbd_f1"
F2 = "rgbd_f2"
TICK_1 = "tick_000000100"
TICK_2 = "tick_000000200"
FEEDBACK_1 = f"joint_feedback_{TICK_1.split('_')[1]}"
FEEDBACK_2 = f"joint_feedback_{TICK_2.split('_')[1]}"
CAPTURE_1 = 426494.351568496
CAPTURE_2 = 426496.425533806
DEPTH = b"\x93NUMPY\x01\x00"


def _source_file(tmp_path: Path, root: Path) -> Path:
    source = tmp_path / "history-source.json"
    source.write_text(json.dumps({
        "schema_version": "unirobot-history-source-1", "source_id": "fixture-history", "adapter_id": "mobilecar",
        "robot_id": "landerpi", "contract_version": "mobilecar-1.0", "reader_format": "native recorder layout",
        "recording_root": str(root), "native_release_id": "fixture-release",
        "declaring_instance": {"base_url": "http://127.0.0.1:1", "access": "GET_only"},
        "access": "read_only_files", "declared_scale": {"episodes_from_native_list": 1},
        "archive_baseline": {"files_hashed": 0}, "policy": {"platform_writes": False}}), encoding="utf-8")
    return source


def _client(root: Path, tmp_path: Path) -> TestClient:
    return TestClient(create_app_for(root, tmp_path))


def create_app_for(root: Path, tmp_path: Path):
    from unirobot.api import create_app
    return create_app(draft_db_path=tmp_path / "drafts.sqlite3", history_source_path=_source_file(tmp_path, root))


def _frame_record(run: str, episode: str, sample: str, tick: str, feedback: str, capture: float,
                  sim: float, persist: float) -> dict:
    return {"interface_profile": "g2a-1.0", "contract_version": "mobilecar-1.0", "run_id": run,
            "episode_id": episode, "stream_id": "rgbd", "sample_id": sample, "kinds": ["rgb", "depth"],
            "persist_sequence": 1 if sample == F1 else 2, "persist_backend_monotonic_s": persist,
            "arrival_backend_monotonic_s": capture + 0.03, "capture_backend_monotonic_s": capture,
            "capture_sim_time_s": sim, "capture_control_tick_id": tick, "feedback_sample_id": feedback,
            "arrival_to_persist_ms": 66.5, "capture_to_persist_ms": (persist - capture) * 1000.0,
            "rgb_uri": f"assets/rgb/{sample}_rgb.png", "depth_uri": f"assets/depth/{sample}_depth_m.npy",
            "valid_mask_uri": f"assets/masks/{sample}_valid.png", "profile_id": "g2a-rgbd-5hz-original",
            "profile_version": 1, "profile_sha256": "b" * 64}


def _index_row(run: str, episode: str, sample: str, kind: str, capture: float, sim: float, tick: str,
               feedback: str, *, digest: str | None, uri_field: str, uri: str, mask: str | None) -> dict:
    return {"contract_version": "mobilecar-1.0", "run_id": run, "episode_id": episode, "stream_id": "rgbd",
            "sample_id": sample, "sensor_kind": kind, "measurement_time_s": capture,
            "arrival_time_s": capture + 0.03, "clock_id": "backend_monotonic", "frame_id": "rgbd_optical",
            "source": "mujoco_renderer", "quality": "simulated_nominal", uri_field: uri, "valid_mask_uri": mask,
            "value": {"height": 240, "width": 320}, "metadata": {"asset_sha256": digest, "asset_bytes": 68,
                                                                 "interface_profile": "g2a-1.0"},
            "capture_sim_time_s": sim, "capture_backend_monotonic_s": capture, "capture_control_tick_id": tick,
            "feedback_sample_id": feedback,
            "timing": {"capture_clocks": {"sim": "sim", "backend_monotonic": "backend_monotonic", "wall_utc": "wall_utc"}}}


def _write_frames(directory: Path, *, resolve_feedback=True, drop_depth_row=False, absent_asset=False,
                  escape_asset=False, foreign_row=False, no_state_event=False, write_persist=True) -> None:
    index_path = directory / "observations" / "index.jsonl"
    persist_path = directory / "observations" / "persist.jsonl"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for sample, tick, feedback, capture, sim in ((F1, TICK_1, FEEDBACK_1, CAPTURE_1, 0.14),
                                                 (F2, TICK_2, FEEDBACK_2, CAPTURE_2, 2.21)):
        rows.append(_index_row(RUN, EPISODE, sample, "rgb", capture, sim, tick, feedback,
                               digest=hashlib.sha256(PNG).hexdigest(), uri_field="asset_uri",
                               uri=f"assets/rgb/{sample}_rgb.png", mask=None))
        if not (drop_depth_row and sample == F2):
            rows.append(_index_row(RUN, EPISODE, sample, "depth", capture, sim, tick, feedback,
                                   digest=hashlib.sha256(DEPTH).hexdigest(), uri_field="asset_uri",
                                   uri=f"assets/depth/{sample}_depth_m.npy",
                                   mask=f"assets/masks/{sample}_valid.png"))
    if resolve_feedback:
        rows.append({"contract_version": "mobilecar-1.0", "run_id": RUN, "episode_id": EPISODE,
                     "stream_id": "joint_feedback", "sample_id": FEEDBACK_1, "sensor_kind": "joint_feedback",
                     "measurement_time_s": CAPTURE_1 - 0.002, "arrival_time_s": CAPTURE_1 - 0.002,
                     "clock_id": "backend_monotonic", "frame_id": "arm_base", "source": "mujoco_motor",
                     "quality": "simulated_nominal", "value": {"model_joint_positions_rad": [0.03, -0.0, 0.0, -1.57, 0.03]},
                     "metadata": {"control_tick_id": TICK_1}})
    if foreign_row:
        other = dict(rows[0])
        other["episode_id"] = "episode_somewhere_else"
        rows.append(other)
    index_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    anchors = [_frame_record(RUN, EPISODE, F1, TICK_1, FEEDBACK_1, CAPTURE_1, 0.14, CAPTURE_1 + 0.1),
               _frame_record(RUN, EPISODE, F2, TICK_2, FEEDBACK_2, CAPTURE_2, 2.21, CAPTURE_2 + 0.16)]
    if write_persist:
        persist_path.write_text("".join(json.dumps(item) + "\n" for item in anchors), encoding="utf-8")
    else:
        # The base fixture writes one placeholder persist line; a real "no persisted frames"
        # Episode has no such file at all.
        persist_path.unlink(missing_ok=True)

    (directory / "transforms.jsonl").write_text("".join(json.dumps({
        "contract_version": "mobilecar-1.0", "run_id": RUN, "episode_id": EPISODE, "stream_id": "rgbd",
        "sample_id": sample, "measurement_time_s": capture, "arrival_time_s": capture + 0.03,
        "clock_id": "backend_monotonic", "frame_id": "rgbd_optical", "source": "mujoco_renderer",
        "metadata": {"transform_version": "g2a-transform-1", "matrix_storage": "row_major",
                     "T_base_link4": [[1.0, 0.0, 0.0, 0.04]] * 4, "joint_model_qpos_rad": [0.03, 0.0, 0.0, -1.57, 0.03]}})
        + "\n" for sample, capture in ((F1, CAPTURE_1), (F2, CAPTURE_2))), encoding="utf-8")

    events = [
        {"contract_version": "mobilecar-1.0", "run_id": RUN, "episode_id": EPISODE, "event_seq": 1,
         "event_type": "recording_start", "wall_utc": "2026-10-17T16:10:29.711000Z",
         "backend_monotonic_s": CAPTURE_1 - 0.1, "sim_time_s": 0.0, "control_tick_id": "tick_000000099",
         "payload": {"recording_segment_id": "seg_001_abc"}},
    ]
    seq = 2
    for sample, tick, feedback, capture, sim in ((F1, TICK_1, FEEDBACK_1, CAPTURE_1, 0.14),
                                                 (F2, TICK_2, FEEDBACK_2, CAPTURE_2, 2.21)):
        events.append({"contract_version": "mobilecar-1.0", "run_id": RUN, "episode_id": EPISODE,
                       "event_seq": seq, "event_type": "rgbd_capture_timing", "wall_utc": "2026-10-17T16:10:29.898727Z",
                       "backend_monotonic_s": capture + 0.06, "sim_time_s": sim, "control_tick_id": tick,
                       "payload": {"sample_id": sample, "interface_profile": "g2a-1.0",
                                   "capture_clocks": {"sim": "sim", "backend_monotonic": "backend_monotonic",
                                                      "wall_utc": "wall_utc"},
                                   "capture_sim_time_s": sim, "capture_backend_monotonic_s": capture,
                                   "capture_control_tick_id": tick, "feedback_sample_id": feedback,
                                   "feedback_time_s": capture - 0.0036, "feedback_clock": "backend_monotonic"}})
        seq += 1
        if no_state_event and tick == TICK_2:
            continue
        events.append({"contract_version": "mobilecar-1.0", "run_id": RUN, "episode_id": EPISODE,
                       "event_seq": seq, "event_type": "feedback", "wall_utc": "2026-10-17T16:10:29.730000Z",
                       "backend_monotonic_s": capture - 0.002, "sim_time_s": sim - 0.01, "control_tick_id": tick,
                       "payload": {"arm_model_qpos_rad": [0.03, -0.0002, 0.0, -1.5705, 0.033],
                                   "wheel_velocity_rad_s": [0.0, 0.0, 0.0, 0.0],
                                   "base_position_world_sim_m": [0.1, 0.2, 0.0],
                                   "base_quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
                                   "tcp_position_world_m": [0.3, 0.1, 0.2], "gripper_width_m": 0.02,
                                   "feedback_time_monotonic": capture - 0.002}})
        seq += 1
    (directory / "events.jsonl").write_text("".join(json.dumps(item) + "\n" for item in events), encoding="utf-8")

    body_by_kind = {"rgb": PNG, "depth": DEPTH, "masks": PNG}
    name_by_kind = {"rgb": "_rgb.png", "depth": "_depth_m.npy", "masks": "_valid.png"}
    for kind in name_by_kind:
        (directory / "assets" / kind).mkdir(parents=True, exist_ok=True)
        for sample in (F1, F2):
            path = directory / "assets" / kind / f"{sample}{name_by_kind[kind]}"
            if sample == F2 and kind == "rgb" and absent_asset:
                continue
            if sample == F2 and kind == "rgb" and escape_asset:
                outside = directory / "outside.png"
                outside.write_bytes(PNG)
                path.symlink_to(outside)
                continue
            path.write_bytes(body_by_kind[kind])


# ---- run directory identity --------------------------------------------------------

def test_run_directory_swapped_for_a_sibling_run_is_refused_after_the_index_is_cached(tmp_path):
    root = tmp_path / "runs"
    _episode(root, RUN, EPISODE, task_language="A belongs to run_aaa")
    _episode(root, "run_bbb", EPISODE, task_language="B belongs to run_bbb")
    client = _client(root, tmp_path)

    before = client.get(f"/api/v1/episodes/{EPISODE}?run_id={RUN}").json()
    assert before["identity"]["run_id"] == RUN
    assert before["action_semantics"] or before["declared"]  # the page built its index already

    shutil.rmtree(root / RUN)
    (root / RUN).symlink_to(root / "run_bbb")

    for path in (f"/api/v1/episodes/{EPISODE}?run_id={RUN}",
                 f"/api/v1/episodes?run_id={RUN}",
                 f"/api/v1/episodes/{EPISODE}/streams/events/records?run_id={RUN}",
                 f"/api/v1/episodes/{EPISODE}/frames?run_id={RUN}"):
        response = client.get(path)
        assert response.status_code == 409, path
        assert response.json()["detail"]["code"] == "history_path_escape", path
        assert "run_bbb" not in json.dumps(response.json()), path
        assert "B belongs to run_bbb" not in json.dumps(response.json()), path

    # The untouched sibling run still reads normally: the guard rejects the swap, not the source.
    sibling = client.get(f"/api/v1/episodes/{EPISODE}?run_id=run_bbb").json()
    assert sibling["identity"]["run_id"] == "run_bbb"


def test_run_directory_identity_is_checked_on_every_read(tmp_path):
    root = tmp_path / "runs"
    _episode(root, RUN, EPISODE)
    _episode(root, "run_bbb", EPISODE)
    source, resolved = load_history_source(_source_file(tmp_path, root))
    archive = EpisodeArchive(source, resolved)
    assert archive.location(EPISODE, RUN).run_directory == root.resolve() / RUN

    shutil.rmtree(root / RUN)
    (root / RUN).symlink_to(root / "run_bbb")
    with pytest.raises(HistoryError) as failure:
        archive.location(EPISODE, RUN)
    assert failure.value.code == "history_path_escape"
    # The refusal names the identity it could not honour, without echoing where the link points.
    assert failure.value.detail["run_directory_is_symlink"] is True
    assert "run_bbb" not in json.dumps(failure.value.detail)
    with pytest.raises(HistoryError):
        archive._run_manifest(RUN)


# ---- frame linkage on real field shapes ---------------------------------------------

def _frames_client(tmp_path, **options):
    root = tmp_path / "runs"
    directory = _episode(root, RUN, EPISODE)
    _write_frames(directory, **options)
    return _client(root, tmp_path)


def test_frames_join_image_to_state_only_on_recorded_keys(tmp_path):
    body = _frames_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/frames").json()
    assert body["schema_version"] == "unirobot-mobilecar-frame-link-1"
    assert body["read_only"] is True
    assert body["linkage"]["selection_rules"]["interpolation"] == "none"
    assert body["time"]["synchronized_across_streams"] is False
    assert body["cursor"]["line_index_is_not_a_clock"] is True
    assert body["three_d_replay"]["transforms_are_full_per_body_pose_sequences"] is False

    assert [item["sample_id"] for item in body["frames"]] == [F1, F2]
    first, second = body["frames"]
    assert first["linkage_status"] == "matched"
    assert set(first["primary_roles_matched"]) == {"image_observation", "camera_transform",
                                                  "capture_timing_event", "state_feedback_event"}
    assert first["declared_reference_status"] == "matched"
    # The second frame declares a feedback reference that is not recorded as a row in this Episode.
    assert second["declared_reference_status"] == "unresolved_reference"
    by_role = {item["role"]: item for item in second["roles"]}
    assert by_role["feedback_observation_row"]["key_value"] == FEEDBACK_2
    assert by_role["feedback_observation_row"]["matched_records"] == 0
    assert by_role["feedback_observation_row"]["sources"] == []

    state = by_role["state_feedback_event"]
    assert state["join_key"] == "control_tick_id" and state["key_value"] == TICK_2
    assert state["sources"][0]["relative_path"] == "events.jsonl"
    assert state["sources"][0]["record_position"].startswith("events.jsonl#")
    assert state["sources"][0]["identity"]["run_id_matches"] is True
    image = by_role["image_observation"]
    assert image["matched_records"] == 2
    transform = by_role["camera_transform"]
    assert "metadata_keys" not in transform  # row fields live on the source entry, not on the role
    assert "T_base_link4" in transform["sources"][0]["metadata_keys"]
    assert "T_base_link4" not in json.dumps(transform["sources"][0]["projection"])
    assert "joint_model_qpos_rad" in transform["sources"][0]["metadata_keys"]
    assert body["summary"]["frames_with_all_primary_roles_matched"] == 2
    assert body["summary"]["frames_with_unresolved_feedback_reference"] == 1


def test_frames_report_media_availability_and_declared_digests(tmp_path):
    body = _frames_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/frames").json()
    media = {item["field"]: item for item in body["frames"][0]["media"]["items"]}
    assert media["rgb_uri"]["availability"] == "present"
    assert media["rgb_uri"]["agrees_with_observation_row"] is True
    assert media["rgb_uri"]["declared_sha256_by_row"] == hashlib.sha256(PNG).hexdigest()
    assert media["depth_uri"]["declared_sha256_by_row"] == hashlib.sha256(DEPTH).hexdigest()
    # The mask is cited by the depth row and carries no digest of its own in the record.
    assert media["valid_mask_uri"]["availability"] == "present"
    assert media["valid_mask_uri"]["declared_sha256_by_row"] is None
    assert body["frames"][0]["media"]["digest_verification"].startswith("declared only")


def test_missing_or_escaping_media_is_reported_not_repaired(tmp_path):
    absent = _frames_client(tmp_path, absent_asset=True).get(f"/api/v1/episodes/{EPISODE}/frames").json()
    second = {item["field"]: item for item in absent["frames"][1]["media"]["items"]}
    assert second["rgb_uri"]["availability"] == "absent"
    assert second["rgb_uri"]["bytes_on_disk"] is None

    escaping = _frames_client(tmp_path, escape_asset=True).get(f"/api/v1/episodes/{EPISODE}/frames").json()
    link = {item["field"]: item for item in escaping["frames"][1]["media"]["items"]}["rgb_uri"]
    assert link["availability"] == "refused"
    assert link["refusal_code"] == "episode_asset_escape"
    assert link["uri"].endswith("rgbd_f2_rgb.png")


def test_state_age_is_shown_as_an_age_and_never_as_the_same_instant(tmp_path):
    body = _frames_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/frames").json()
    frame = body["frames"][0]
    assert frame["state"]["recorded_state"]["arm_model_qpos_rad"] == [0.03, -0.0002, 0.0, -1.5705, 0.033]
    assert frame["state"]["carried_over_from_another_frame"] is False
    assert frame["state"]["interpolated"] is False
    assert frame["state"]["recorder_declared_feedback"]["feedback_clock"] == "backend_monotonic"
    age = frame["times"]["age_of_state_relative_to_frame"]
    assert age["state_recorded_before_capture"] is True
    assert round(age["abs_ms"], 3) == 2.0
    assert frame["times"]["same_clock_verified"] is False
    labels = {item["label"]: item for item in frame["times"]["deltas"]}
    assert labels["state_event_minus_frame_capture"]["direction"] == "earlier"
    assert labels["observation_measurement_time_s_minus_frame_capture"]["direction"] == "equal"
    assert labels["observation_arrival_time_s_minus_frame_capture"]["direction"] == "later"
    assert labels["recorder_declared_feedback_time_minus_capture"]["abs_value_ms"] == pytest.approx(3.6, abs=1e-6)
    assert frame["times"]["declared_latency_ms"]["capture_to_persist_ms"] == pytest.approx(100.0)
    assert body["time"]["clock_sameness"]["verified_by_reader"] is False


def test_a_frame_without_a_state_record_gets_no_invented_state(tmp_path):
    body = _frames_client(tmp_path, no_state_event=True).get(f"/api/v1/episodes/{EPISODE}/frames").json()
    second = body["frames"][1]
    assert second["state"]["status"] == "missing"
    assert second["state"]["recorded_state"] is None
    assert second["state"]["source"] is None
    assert second["times"]["age_of_state_relative_to_frame"] is None
    assert second["linkage_status"] == "partial"
    assert body["summary"]["frames_without_a_linked_state"] == 1


def test_a_candidate_record_naming_another_episode_is_excluded(tmp_path):
    body = _frames_client(tmp_path, foreign_row=True).get(f"/api/v1/episodes/{EPISODE}/frames").json()
    first, second = body["frames"]
    image = next(item for item in first["roles"] if item["role"] == "image_observation")
    assert image["status"] == "identity_mismatch"
    assert image["identity_mismatched_records"] == 1
    assert all(item["identity"]["episode_id_matches"] for item in image["sources"])
    # The frame is reported as degraded rather than quietly served as if fully linked.
    assert first["linkage_status"] == "partial"
    assert "image_observation" not in second["primary_roles_matched"] or second["linkage_status"] in ("partial", "matched")


def test_frames_paging_time_window_and_bounded_limits(tmp_path):
    client = _frames_client(tmp_path)
    page = client.get(f"/api/v1/episodes/{EPISODE}/frames?limit=1").json()
    assert [item["sample_id"] for item in page["frames"]] == [F1]
    assert page["paging"]["next_offset"] == 1 and page["paging"]["has_more"] is True
    assert page["cursor"]["first_persist_sequence"] == 1

    rest = client.get(f"/api/v1/episodes/{EPISODE}/frames?offset=1").json()
    assert [item["sample_id"] for item in rest["frames"]] == [F2]
    assert rest["paging"]["skipped_before_offset"] == 1

    window = client.get(f"/api/v1/episodes/{EPISODE}/frames?time_base=capture_sim_time_s"
                        f"&time_from=0.0&time_to=1.0").json()
    assert [item["sample_id"] for item in window["frames"]] == [F1]
    assert window["paging"]["excluded_outside_time_window"] == 1
    assert window["paging"]["records_missing_selected_time_base"] == 0

    assert client.get(f"/api/v1/episodes/{EPISODE}/frames?limit=201").status_code == 422
    wrong = client.get(f"/api/v1/episodes/{EPISODE}/frames?time_base=wall_utc&time_from=1").json()
    assert wrong["detail"]["code"] == "time_base_unsupported"
    assert "capture_backend_monotonic_s" in wrong["detail"]["supported"]
    bare = client.get(f"/api/v1/episodes/{EPISODE}/frames?time_base=capture_sim_time_s").json()
    assert bare["detail"]["code"] == "time_range_required"


def test_single_frame_lookup_by_sample_id(tmp_path):
    body = _frames_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/frames?sample_id={F2}").json()
    assert [item["sample_id"] for item in body["frames"]] == [F2]
    assert body["paging"]["returned"] == 1 and body["cursor"]["first_line_index"] == 1
    bad = _frames_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/frames?sample_id=../escape").json()
    assert bad["detail"]["code"] == "sample_id_invalid"


def test_an_episode_without_persisted_frames_says_so(tmp_path):
    body = _frames_client(tmp_path, write_persist=False)
    response = body.get(f"/api/v1/episodes/{EPISODE}/frames")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "episode_stream_unavailable"
    assert response.json()["detail"]["read_only"] is True


def test_frame_links_stay_inside_their_own_episode(tmp_path):
    root = tmp_path / "runs"
    first = _episode(root, RUN, EPISODE)
    _write_frames(first)
    second = _episode(root, "run_ccc", "episode_two")
    _write_frames(second, write_persist=False)
    client = _client(root, tmp_path)

    body = client.get(f"/api/v1/episodes/{EPISODE}/frames?run_id={RUN}").json()
    assert body["identity"]["run_id"] == RUN and body["identity"]["episode_id"] == EPISODE
    for frame in body["frames"]:
        for role in frame["roles"]:
            for source in role["sources"]:
                assert source["identity"]["declared_run_id"] == RUN
                assert source["identity"]["declared_episode_id"] == EPISODE
        for item in frame["media"]["items"]:
            assert item["uri"] is None or item["uri"].startswith("assets/")

    missing = client.get("/api/v1/episodes/episode_two/frames?run_id=run_ccc")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "episode_stream_unavailable"
    unknown = client.get("/api/v1/episodes/episode_absent/frames")
    assert unknown.status_code == 404
    assert unknown.json()["detail"]["code"] == "episode_not_found"
