"""Focused coverage for run-directory identity, the frame linkage slice and its pose preparation.

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
from unirobot.mobilecar_geometry import GeometryBundle

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
ARM_MODEL_QPOS = [0.03, -0.0002, 0.0, -1.5705, 0.033]
MODEL_ID = "landerpi_mecanum_dynamic_5dof_3ca3d6d0a92a"
MODEL_SHA256 = "3ca3d6d0a92a48bbfbce5ac7a04e37a0f7cf7a73297045ae327bf461ad50e280"


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


def _client(root: Path, tmp_path: Path, bundle: Path | None = None) -> TestClient:
    return TestClient(create_app_for(root, tmp_path, bundle))


def create_app_for(root: Path, tmp_path: Path, bundle: Path | None = None):
    from unirobot.api import create_app
    return create_app(draft_db_path=tmp_path / "drafts.sqlite3", history_source_path=_source_file(tmp_path, root),
                      compiled_geometry_path=bundle)


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
                  escape_asset=False, foreign_row=False, no_state_event=False, write_persist=True,
                  blank_lines=False, corrupt_lines=False, duplicate_rgb_row=False,
                  duplicate_state_event=False, payload_sim_time="absent", arm_qpos=None,
                  tcp_position=None, base_position=None) -> None:
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
    if duplicate_rgb_row:
        # A second rgb row for the same frame: the pair the role requires is not satisfied by this.
        extra = dict(rows[2])
        extra["asset_uri"] = f"assets/rgb/{F2}_rgb_other.png"
        extra["measurement_time_s"] = CAPTURE_2 + 0.001
        rows.append(extra)
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
        if blank_lines:
            # Leading and interior blank lines shift the raw line indexes the cursor reports.
            persist_path.write_text("\n" + json.dumps(anchors[0]) + "\n\n" + json.dumps(anchors[1]) + "\n",
                                    encoding="utf-8")
        else:
            persist_path.write_text("".join(json.dumps(item) + "\n" for item in anchors), encoding="utf-8")
        if corrupt_lines:
            with persist_path.open("a", encoding="utf-8") as handle:
                handle.write('{"stream_id": "rgbd" this line is not json\n')
                handle.write('{"sample_id": "rgbd_huge", "pad": "' + "x" * (256 * 1024 + 8) + '"}\n')
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
                                   "arrival_backend_monotonic_s": capture + 0.03, "observation_age_ms": 30.0,
                                   "capture_control_tick_id": tick, "feedback_sample_id": feedback,
                                   "feedback_time_s": capture - 0.0036, "feedback_clock": "backend_monotonic"}})
        seq += 1
        if no_state_event and tick == TICK_2:
            continue
        for qpos in ([arm_qpos or ARM_MODEL_QPOS]
                     + ([[0.09, 0.0, 0.0, -1.5, 0.0]] if duplicate_state_event and tick == TICK_2 else [])):
            events.append({"contract_version": "mobilecar-1.0", "run_id": RUN, "episode_id": EPISODE,
                           "event_seq": seq, "event_type": "feedback", "wall_utc": "2026-10-17T16:10:29.730000Z",
                           "backend_monotonic_s": capture - 0.002, "sim_time_s": sim - 0.01, "control_tick_id": tick,
                           "payload": {"arm_model_qpos_rad": qpos,
                                       "wheel_velocity_rad_s": [0.0, 0.0, 0.0, 0.0],
                                       "base_position_world_sim_m": base_position or [0.1, 0.2, 0.0],
                                       "base_quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
                                       "tcp_position_world_m": tcp_position or [0.3, 0.1, 0.2],
                                       "gripper_width_m": 0.02,
                                       "feedback_time_monotonic": capture - 0.002,
                                       **({"sim_time_s": 0.14} if payload_sim_time == "numeric" else
                                          {"sim_time_s": "0.14"} if payload_sim_time == "string" else {})}})
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
        if duplicate_rgb_row:
            (directory / "assets" / kind / f"{F2}_rgb_other.png").write_bytes(PNG)


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
    assert body["schema_version"] == "unirobot-mobilecar-frame-link-2"
    assert body["read_only"] is True
    assert body["linkage"]["selection_rules"]["interpolation"] == "none"
    assert body["linkage"]["roles"]["image_observation"]["requirement"]["required_kinds"] == ["rgb", "depth"]
    assert body["time"]["synchronized_across_streams"] is False
    assert body["cursor"]["line_index_is_not_a_clock"] is True
    assert body["three_d_replay"]["transforms_are_full_per_body_pose_sequences"] is False
    assert "times.age_of_state_relative_to_frame" in body["version_migration"]["removed_fields"]

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
    assert image["matched_kinds"] == ["depth", "rgb"] and image["missing_kinds"] == []
    assert image["duplicate_kinds"] == [] and image["status"] == "matched"
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
    assert media["rgb_uri"]["observation_row_candidates"] == 1
    assert "observation_rows_conflict" not in media["rgb_uri"]
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


def test_a_repeated_rgb_row_without_a_depth_row_is_never_called_complete(tmp_path):
    body = _frames_client(tmp_path, duplicate_rgb_row=True, drop_depth_row=True).get(
        f"/api/v1/episodes/{EPISODE}/frames").json()
    frame = body["frames"][1]
    image = next(item for item in frame["roles"] if item["role"] == "image_observation")
    # Two rows and the rgb pair present would have looked sufficient; the required kind set does not.
    assert image["status"] == "ambiguous_kind"
    assert image["duplicate_kinds"] == ["rgb"] and image["missing_kinds"] == ["depth"]
    assert image["kind_inventory"]["rgb"] == image["candidate_line_indexes"][-2:]
    assert frame["linkage_status"] != "matched"
    assert "image_observation" not in frame["primary_roles_matched"]
    assert body["linkage"]["status_precedence"].index("ambiguous_kind") < body["linkage"]["status_precedence"].index("partial")
    assert body["summary"]["frames_with_ambiguous_primary_role"] == 1
    # Both candidate rows stay visible instead of the first line winning.
    media = {item["field"]: item for item in frame["media"]["items"]}
    assert media["rgb_uri"]["observation_row_candidates"] == 2
    assert media["rgb_uri"]["observation_rows_conflict"] is True
    assert len(media["rgb_uri"]["observation_row_line_indexes"]) == 2


def test_repeated_state_candidates_are_reported_rather_than_the_first_one(tmp_path):
    body = _frames_client(tmp_path, duplicate_state_event=True).get(f"/api/v1/episodes/{EPISODE}/frames").json()
    frame = body["frames"][1]
    state = next(item for item in frame["roles"] if item["role"] == "state_feedback_event")
    assert state["status"] == "ambiguous_candidates"
    assert state["requirement"]["exact_records"] == 1
    assert {item["conflicts_with_first"] for item in state["ambiguous_records"][1:]} == {True}
    assert frame["state"]["status"] == "ambiguous_candidates"
    assert frame["state"]["single_state_selected"] is False
    assert frame["state"]["recorded_state"] is None
    assert len(frame["state"]["candidates"]) == 2
    assert "none is chosen" in frame["state"]["multiple_candidates_note"]
    # No state-derived quantity is presented as if one record had been selected.
    keys = [item["key"] for item in frame["times"]["quantities"]]
    assert keys.count("state_payload_feedback_time_minus_frame_capture") == 2
    assert frame["linkage_status"] == "partial"


def test_state_times_separate_the_write_stamp_the_sample_stamp_and_the_declared_age(tmp_path):
    body = _frames_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/frames").json()
    frame = body["frames"][0]
    assert frame["state"]["recorded_state"]["arm_model_qpos_rad"] == ARM_MODEL_QPOS
    assert frame["state"]["carried_over_from_another_frame"] is False
    assert frame["state"]["interpolated"] is False
    assert frame["state"]["recorder_declared_feedback"]["feedback_clock"] == "backend_monotonic"

    quantities = {item["key"]: item for item in frame["times"]["quantities"]}
    event_write = quantities["state_event_write_minus_frame_capture"]
    payload_sample = quantities["state_payload_feedback_time_minus_frame_capture"]
    declared = quantities["recorder_declared_feedback_time_minus_frame_capture"]
    assert round(event_write["abs_ms"], 3) == 2.0 and event_write["direction"] == "earlier"
    assert round(declared["abs_ms"], 3) == 3.6
    assert event_write["source_record"] != declared["source_record"]
    assert event_write["field"] == "backend_monotonic_s"
    assert payload_sample["field"] == "feedback_time_monotonic"
    assert declared["field"] == "feedback_time_s"
    assert quantities["state_payload_feedback_time_minus_state_event_write"]["abs_ms"] == pytest.approx(0.0)
    assert quantities["timing_payload_capture_minus_anchor_capture"]["direction"] == "equal"
    # A different clock base is never folded into the monotonic differences, and the envelope value
    # is labelled as the envelope's own rather than as the payload's.
    sim = quantities["state_event_envelope_sim_time_minus_frame_capture_sim_time"]
    assert sim["clock"] == "sim" and round(sim["abs_ms"], 3) == 10.0
    assert sim["source_record"] == "events state feedback envelope"
    assert "state_sim_time_minus_frame_capture_sim_time" not in quantities  # the payload has no sim_time_s
    assert any("payload" in item for item in body["version_migration"]["corrections"])
    assert quantities["observation_measurement_minus_frame_capture"]["direction"] == "equal"
    assert quantities["observation_arrival_minus_frame_capture"]["direction"] == "later"
    assert quantities["persist_minus_capture"]["abs_ms"] == pytest.approx(100.0)
    assert "age_of_state_relative_to_frame" not in frame["times"]
    assert frame["times"]["same_clock_verified"] is False
    # The recorder's own age is copied and compared, never merged with the state stamps.
    recorder = frame["times"]["recorder_declared"]
    assert recorder["fields"]["observation_age_ms"] == 30.0
    assert recorder["recomputed_arrival_minus_capture_ms"] == pytest.approx(30.0)
    assert recorder["agrees_with_recomputation"] is True
    assert recorder["fields"]["capture_to_persist_ms"] == pytest.approx(100.0)
    assert "not the difference between a state sample" in recorder["observation_age_ms_note"]
    sameness = body["time"]["clock_sameness"]
    assert sameness["verified_by_reader"] is False
    assert sameness["writer_version_binding"]["not_recorded"] == ["the native build or release that wrote the archive",
                                                                 "a source commit for the writer"]
    assert sameness["writer_version_binding"]["synchronized_upgraded_by_numeric_closeness"] is False


def test_a_frame_without_a_state_record_gets_no_invented_state(tmp_path):
    body = _frames_client(tmp_path, no_state_event=True).get(f"/api/v1/episodes/{EPISODE}/frames").json()
    second = body["frames"][1]
    assert second["state"]["status"] == "missing"
    assert second["state"]["recorded_state"] is None
    assert second["state"]["source"] is None
    assert [item for item in second["times"]["quantities"] if item["key"].startswith("state_")] == []
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
    assert "image_observation" not in first["primary_roles_matched"]
    assert second["linkage_status"] == "matched"


def test_frames_paging_time_window_and_bounded_limits(tmp_path):
    client = _frames_client(tmp_path)
    page = client.get(f"/api/v1/episodes/{EPISODE}/frames?limit=1").json()
    assert [item["sample_id"] for item in page["frames"]] == [F1]
    assert page["paging"]["next_offset"] == 1 and page["paging"]["has_more"] is True
    assert page["paging"]["next_qualifying_anchor_line_index"] == 1
    assert page["paging"]["scan"]["whole_file_scanned"] is False
    assert page["paging"]["post_page_records_examined"] == 1
    assert page["paging"]["anchor_records_examined"] == 2
    assert page["cursor"]["first_persist_sequence"] == 1

    rest = client.get(f"/api/v1/episodes/{EPISODE}/frames?offset=1").json()
    assert [item["sample_id"] for item in rest["frames"]] == [F2]
    assert rest["paging"]["skipped_before_offset"] == 1
    # Reaching the end of the file is the only thing that can say there is no next page.
    assert rest["paging"]["has_more"] is False and rest["paging"]["next_offset"] is None
    assert rest["paging"]["scan"]["whole_file_scanned"] is True

    window = client.get(f"/api/v1/episodes/{EPISODE}/frames?time_base=capture_sim_time_s"
                        f"&time_from=0.0&time_to=1.0").json()
    assert [item["sample_id"] for item in window["frames"]] == [F1]
    assert window["paging"]["excluded_outside_time_window"] == 1
    assert window["paging"]["records_missing_selected_time_base"] == 0
    assert window["paging"]["has_more"] is False

    assert client.get(f"/api/v1/episodes/{EPISODE}/frames?limit=201").status_code == 422
    wrong = client.get(f"/api/v1/episodes/{EPISODE}/frames?time_base=wall_utc&time_from=1").json()
    assert wrong["detail"]["code"] == "time_base_unsupported"
    assert "capture_backend_monotonic_s" in wrong["detail"]["supported"]
    bare = client.get(f"/api/v1/episodes/{EPISODE}/frames?time_base=capture_sim_time_s").json()
    assert bare["detail"]["code"] == "time_range_required"


def test_blank_and_unreadable_anchor_lines_are_counted_not_silently_last_page(tmp_path):
    client = _frames_client(tmp_path, blank_lines=True, corrupt_lines=True)
    first = client.get(f"/api/v1/episodes/{EPISODE}/frames?limit=1").json()
    # Blank lines shifted the raw anchors, and the cursor keeps the real file line numbers.
    assert first["paging"]["anchor_lines"]["lines_read"] == 4
    assert first["paging"]["anchor_lines"]["blank_lines_skipped"] == 2
    assert first["frames"][0]["anchor"]["line_index"] == 1
    assert first["paging"]["next_offset"] == 2
    assert first["paging"]["has_more"] is True and first["paging"]["scan"]["whole_file_scanned"] is False

    last = client.get(f"/api/v1/episodes/{EPISODE}/frames?offset=2").json()
    assert [item["sample_id"] for item in last["frames"]] == [F2]
    assert last["paging"]["anchor_lines"]["unparseable_lines_skipped"] == 1
    assert last["paging"]["anchor_lines"]["oversize_lines_skipped"] == 1
    assert last["paging"]["anchor_lines"]["blank_lines_skipped"] == 2
    assert last["paging"]["has_more"] is False
    assert last["paging"]["scan"]["note"].startswith("a full page stops")

    whole = client.get(f"/api/v1/episodes/{EPISODE}/frames").json()
    assert [item["sample_id"] for item in whole["frames"]] == [F1, F2]
    assert whole["paging"]["anchor_records_examined"] == 2
    assert whole["paging"]["anchor_lines"]["prefiltered_lines_skipped"] == 0
    assert whole["paging"]["has_more"] is False


def test_single_frame_lookup_by_sample_id(tmp_path):
    body = _frames_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/frames?sample_id={F2}").json()
    assert [item["sample_id"] for item in body["frames"]] == [F2]
    assert body["paging"]["returned"] == 1 and body["cursor"]["first_line_index"] == 1
    assert body["paging"]["excluded_by_sample_id_filter"] == 1
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


# ---- historical pose preparation ----------------------------------------------------

def _bundle(tmp_path: Path, *, model_sha256: str = MODEL_SHA256) -> Path:
    """A minimal frozen bundle in the compiled-geometry shape, written for the fixture only."""
    directory = tmp_path / "geometry"
    (directory / "assets").mkdir(parents=True, exist_ok=True)
    mesh = b"solid\nfake stl\nendsolid\n"
    directory.joinpath("assets", "base_link.stl").write_bytes(mesh)
    directory.joinpath("assets", "link1.stl").write_bytes(mesh)
    digest = hashlib.sha256(mesh).hexdigest()

    def transform(position, orientation=None):
        return {"position_m": position, "orientation_xyzw": orientation or [0.0, 0.0, 0.0, 1.0]}

    def mesh_geom(name, asset_id):
        return {"name": name, "geom_type": "mesh", "size_m": [1.0, 1.0, 1.0],
                "local_transform": transform([0.0, 0.0, 0.0]), "rgba": [0.2, 0.2, 0.2, 1.0],
                "mesh_asset_id": asset_id, "contype": 0, "conaffinity": 0, "collision": False, "group": 0}

    def box_geom(name):
        return {"name": name, "geom_type": "box", "size_m": [0.02, 0.02, 0.02],
                "local_transform": transform([0.0, 0.0, 0.0]), "rgba": [0.2, 0.2, 0.2, 1.0],
                "mesh_asset_id": None, "contype": 1, "conaffinity": 1, "collision": True, "group": 1}

    def link(name, parent, joint, joint_type, axis, position, geoms):
        return {"name": name, "parent_name": parent, "joint_name": joint, "joint_type": joint_type,
                "joint_axis": axis, "local_transform": transform(position), "geoms": geoms}

    links = [link("base_link", None, "base_free", "free", [0.0, 0.0, 1.0], [0.0, 0.0, 0.0556],
                  [mesh_geom("base_mesh", "base_link"), box_geom("base_collision")])]
    for index in range(1, 6):
        geoms = [mesh_geom(f"link{index}_mesh", "link1")] if index == 1 else [box_geom(f"link{index}_collision")]
        links.append(link(f"link{index}", links[-1]["name"], f"joint{index}", "hinge",
                          [0.0, 0.0, 1.0], [0.1, 0.0, 0.0], geoms))
    # A straight chain to the site's parent body: with every arm angle at zero the TCP position is a
    # plain sum of x offsets, so the cross-check expectation is hand-computable and independent.
    links.append(link("gripper_link", "link5", None, "fixed", [0.0, 0.0, 1.0], [0.1, 0.0, 0.0],
                      [box_geom("gripper_collision")]))
    links.append(link("guide_rod_link", "gripper_link", None, "fixed", [0.0, 0.0, 1.0], [0.1, 0.0, 0.0],
                      [box_geom("guide_rod_collision")]))
    links.append(link("camera_connect_link", "link4", None, "fixed", [0.0, 0.0, 1.0],
                      [-0.03, 0.01, 0.04], [box_geom("camera_connect_collision")]))
    links.append(link("depth_cam_link", "camera_connect_link", None, "fixed", [0.0, 0.0, 1.0],
                      [0.02, 0.0, 0.005], [box_geom("depth_cam_collision")]))
    for joint in ("left_jaw_joint", "right_jaw_joint"):
        links.append(link(joint.replace("_joint", "_link"), "link5", joint, "slide", [0.0, -1.0, 0.0],
                          [0.0, 0.0, 0.0], [box_geom(f"{joint}_collision")]))
    scene = {"contract_version": "mobilecar-1.0", "model_id": MODEL_ID, "model_sha256": model_sha256,
             "scene_id": "mobile_pick", "links": links,
             "world_links": [link("world_static", None, None, "fixed", [0.0, 0.0, 1.0], [0.0, 0.0, 0.0],
                                  [{"name": "floor", "geom_type": "plane", "size_m": [3.0, 3.0, 0.1],
                                    "local_transform": transform([0.0, 0.0, 0.0]), "rgba": [0.5, 0.5, 0.5, 1.0],
                                    "mesh_asset_id": None, "contype": 1, "conaffinity": 1, "collision": True, "group": 1}])],
             "mesh_assets": [{"asset_id": name, "uri": f"/api/v1/scene/assets/{name}", "sha256": digest,
                              "media_type": "model/stl", "coordinate_space": "mujoco_compiled_mesh", "units": "m",
                              "mesh_preprocessing_applied": True, "source_sha256": digest,
                              "source_mesh_name": f"{name}_mesh"}
                             for name in ("base_link", "link1")],
             "camera_ids": ["rgbd"], "tcp_site": "grasp_tcp", "source": "mujoco_model_compile"}
    from unirobot.mobilecar_geometry import content_digest
    model_inputs = [{"path": "assets/landerpi/model/robot.xml", "sha256": model_sha256, "size_bytes": 1366}]
    bundle = {"scene": scene, "model_inputs": model_inputs, "mesh_report": [], "geometry_provenance": {
        "compiler": "MuJoCo", "compiler_version": "3.1.6",
        "runtime_identity": {"run_id": "run_other", "backend_generation": 1, "episode_id": "episode_other"},
        "resource_identity": {"contract_version": "mobilecar-1.0", "model_id": MODEL_ID,
                              "model_sha256": model_sha256, "scene_id": "mobile_pick"},
        "native_scene_sha256": "1" * 64, "model_inputs_sha256": content_digest(model_inputs),
        "compiled_scene_sha256": content_digest(scene), "native_scene_builder_sha256": "4" * 64,
        "verification_scope": "static_compilation_matches_live_manifest_not_live_memory_or_contacts"}}
    # The loader recomputes the digest of the document with bundle_sha256 removed, so it is written the same way.
    bundle["geometry_provenance"]["bundle_sha256"] = content_digest(bundle)
    directory.joinpath("bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    return directory


def _pose_client(tmp_path, *, model_sha256: str = MODEL_SHA256, recorded_model_sha256: str = MODEL_SHA256,
                 **frame_options):
    root = tmp_path / "runs"
    directory = _episode(root, RUN, EPISODE)
    # The run manifest is where the recorder pins the model identity the pose slice must match.
    manifest_path = root / RUN / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({"model_id": MODEL_ID, "model_sha256": recorded_model_sha256, "scene_id": "mobile_pick",
                     "contract_version": "mobilecar-1.0", "map_mode": "unavailable",
                     "truth_access": "GT_DEBUG_SEPARATE_FROM_DEFAULT_OBSERVATION",
                     "clocks": ["sim", "backend_monotonic", "device", "wall_utc"],
                     "software": {"name": "mobilecar", "version": "0.1.0"}})
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    _write_frames(directory, **frame_options)
    return _client(root, tmp_path, _bundle(tmp_path / "prepared", model_sha256=model_sha256))


def test_robot_state_maps_recorded_pose_onto_the_frozen_bundle(tmp_path):
    body = _pose_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/robot-state").json()
    assert body["schema_version"] == "unirobot-mobilecar-history-pose-1"
    assert body["read_only"] is True
    assert body["identity"]["recorded_run_manifest"]["model_sha256"] == MODEL_SHA256
    assert body["model_resource"]["status"] == "match"
    assert body["model_resource"]["live_native_scene_proxied"] is False
    assert [item["asset_id"] for item in body["model_resource"]["assets"]] == ["base_link", "link1"]
    assert body["model_resource"]["arm_hinge_joints"] == ["joint1", "joint2", "joint3", "joint4", "joint5"]
    assert body["model_resource"]["tcp_site"] == "grasp_tcp"
    chain = [item["name"] for item in body["model_resource"]["camera_link_chain"]]
    assert chain[:3] == ["depth_cam_link", "camera_connect_link", "link4"] and chain[-1] == "base_link"

    mapping = {item["target"]: item for item in body["mapping"]}
    assert mapping["arm_joint_positions"]["status"] == "partially_verified"
    assert mapping["arm_joint_positions"]["recorded_length"] == 5
    assert mapping["arm_joint_positions"]["evidence"]["order_attested_at_index"] == 3
    assert mapping["arm_joint_positions"]["no_default_applied"] is True
    for target in ("base_position", "base_orientation", "gripper_joints", "tcp_site_position"):
        assert mapping[target]["status"] == "unverified", target
        assert mapping[target]["no_default_applied"] is True
    assert mapping["camera_extrinsics"]["status"] == "missing"
    assert mapping["dynamic_scene_objects"]["evidence"]["render_from_record"] is False

    assert body["pose_readiness"]["robot_state_can_be_rebuilt_without_assumptions"] is False
    assert body["pose_readiness"]["blocking_fields"]
    assert body["rendering"]["verified"] is False and body["rendering"]["frontend_assembly_done"] is False
    assert body["state"]["recorded_payload"]["arm_model_qpos_rad"] == ARM_MODEL_QPOS
    assert body["frame"]["linkage_schema"] == "unirobot-mobilecar-frame-link-2"
    assert [item["key"] for item in body["time"]["quantities"]]


def test_robot_state_refuses_to_map_a_different_model_identity(tmp_path):
    body = _pose_client(tmp_path, model_sha256="9" * 64).get(f"/api/v1/episodes/{EPISODE}/robot-state").json()
    assert body["model_resource"]["status"] == "mismatch"
    assert body["model_resource"]["comparison"]["model_sha256"]["equal"] is False
    assert body["pose_readiness"]["mapping_valid_for_this_episode"] is False

    refused = _pose_client(tmp_path, model_sha256="9" * 64).get(f"/api/v1/episodes/{EPISODE}/model/assets/base_link")
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "history_model_identity_mismatch"


def test_frozen_bundle_mesh_is_served_without_the_native_scene(tmp_path):
    client = _pose_client(tmp_path)
    digest = hashlib.sha256(b"solid\nfake stl\nendsolid\n").hexdigest()
    response = client.get(f"/api/v1/episodes/{EPISODE}/model/assets/base_link?sha256={digest}")
    assert response.status_code == 200
    assert response.headers["X-UniRobot-Model-Source"] == "frozen_compiled_geometry_bundle"
    assert response.headers["ETag"] == f'"sha256:{digest}"'

    stale = client.get(f"/api/v1/episodes/{EPISODE}/model/assets/base_link?sha256={'0' * 64}")
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "history_asset_revision_changed"
    unknown = client.get(f"/api/v1/episodes/{EPISODE}/model/assets/no_such_link")
    assert unknown.status_code == 404
    assert unknown.json()["detail"]["code"] == "history_model_asset_unavailable"


def test_robot_state_needs_a_configured_bundle(tmp_path):
    response = _frames_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/robot-state")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "history_model_bundle_not_configured"


def test_history_pose_reader_reuses_the_bundle_integrity_checks(tmp_path):
    directory = _bundle(tmp_path / "prepared")
    bundle = GeometryBundle(directory)
    assert sorted(bundle.assets) == ["base_link", "link1"]
    assert bundle.provenance.resource_identity.model_id == MODEL_ID


def test_a_missing_payload_sim_time_is_never_filled_from_the_envelope(tmp_path):
    absent = _frames_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/frames").json()
    keys = {item["key"] for item in absent["frames"][0]["times"]["quantities"]}
    assert "state_event_envelope_sim_time_minus_frame_capture_sim_time" in keys
    assert "state_sim_time_minus_frame_capture_sim_time" not in keys

    numeric = _frames_client(tmp_path, payload_sim_time="numeric").get(f"/api/v1/episodes/{EPISODE}/frames").json()
    quantities = {item["key"]: item for item in numeric["frames"][0]["times"]["quantities"]}
    payload = quantities["state_sim_time_minus_frame_capture_sim_time"]
    envelope = quantities["state_event_envelope_sim_time_minus_frame_capture_sim_time"]
    assert payload["source_record"] == "events state feedback payload" and payload["abs_ms"] == pytest.approx(0.0)
    assert envelope["source_record"] == "events state feedback envelope" and envelope["abs_ms"] == pytest.approx(10.0)
    assert {item["field"] for item in (payload, envelope)} == {"sim_time_s"}

    # A non-numeric payload stamp is absence, not a value to be recovered from the envelope.
    text = _frames_client(tmp_path, payload_sim_time="string").get(f"/api/v1/episodes/{EPISODE}/frames").json()
    keys = {item["key"] for item in text["frames"][0]["times"]["quantities"]}
    assert "state_sim_time_minus_frame_capture_sim_time" not in keys
    assert "state_event_envelope_sim_time_minus_frame_capture_sim_time" in keys


KINEMATICS = json.loads((Path(__file__).resolve().parents[1] / "config"
                         / "mobilecar-landerpi-kinematics-v1.json").read_text(encoding="utf-8"))


def _pose_client_fk(tmp_path):
    """A frame whose recorded TCP equals the frozen chain at zero joint angles, computed by hand."""
    tcp = KINEMATICS["tcp"]
    # The fixture chain is base_link -> link1..link5 -> gripper_link -> guide_rod_link, each link
    # offset 0.1 m along x, and every arm angle is zero: the site's parent body therefore sits at
    # x = 0.7 with the base at the origin, so the expected TCP is a plain sum, not an FK result.
    expected = [0.7 + tcp["position_m"][0], tcp["position_m"][1], tcp["position_m"][2]]
    return (_pose_client(tmp_path, arm_qpos=[0.0] * 5, tcp_position=expected, base_position=[0.0, 0.0, 0.0]),
            expected)


def test_arm_mapping_carries_the_source_chain_and_its_version_ceiling(tmp_path):
    body = _pose_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/robot-state").json()
    arm = next(item for item in body["mapping"] if item["target"] == "arm_joint_positions")
    assert arm["draw_source"] == "model radians, applied directly to the hinge joints"
    assert arm["requires_user_angle_conversion"] is False
    assert "ARM_JOINTS = tuple" in arm["evidence"]["source_chain"]["joint_name_list"]
    assert "qpos = model.jnt_qposadr" in arm["evidence"]["source_chain"]["qpos_is_name_addressed"]
    assert "arm_model_qpos_rad" in arm["evidence"]["source_chain"]["feedback_serialisation"]
    assert arm["evidence"]["names_equal_to_bundle"] is True
    assert arm["evidence"]["source_chain"]["sixth_element_excluded"].startswith("GRIPPER_DRIVE")
    binding = body["version_binding"]
    assert binding["chain_verified_in_reference_source"] is True
    assert binding["writer_identified"] is False
    assert len(binding["frozen_release_snapshots_at_the_recording_hour"]) == 3
    assert binding["record_carries_no"] == ["native release id", "build id", "git commit"]
    assert "does not identify a single build" in binding["conclusion"]


def test_model_angles_are_drawn_without_the_user_angle_step(tmp_path):
    body = _pose_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/robot-state").json()
    angles = body["model_vs_user_angles"]
    assert angles["conversion_is_required_for_drawing"] is False
    assert angles["config_joint_names_equal_bundle_arm_hinges"] is True
    assert angles["user_angle_formula"]["used_for"] == "user-facing display and limit comparison only"
    assert angles["zero_pose_authority"]["zero_status"] == "user_defined_photo_pose_not_hardware_500"
    assert angles["zero_pose_authority"]["calibration_session"] == "uncalibrated"
    assert angles["authority"] == "platform_reference_not_native_attested"
    assert "-pi/2" in angles["record_index3_observation"]


def test_per_part_readiness_separates_assembly_from_the_whole_robot(tmp_path):
    body = _pose_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/robot-state").json()
    parts = {item["capability"]: item for item in body["part_readiness"]}
    assert set(parts) == {"fixed_model_reference_assembly", "arm_local_pose", "base_pose_placement",
                          "gripper_visual_appearance", "tcp_position_marker", "tcp_orientation_frame",
                          "camera_view_from_record", "dynamic_scene_objects_from_record",
                          "wheel_pose_from_record"}
    assert all(item["status"] in body["part_status_meaning"] for item in parts.values())
    # A blocked part never blocks the fixed assembly, and the assembly is available without any pose input.
    assert parts["fixed_model_reference_assembly"]["status"] == "ready"
    assert parts["fixed_model_reference_assembly"]["pose_input_required"] is False
    assert parts["arm_local_pose"]["status"] == "ready_with_caveats"
    summary = body["capability_summary"]
    assert summary["fixed_model_assembly_available"] is True
    assert summary["whole_robot_pose_rebuildable"] is False
    assert "never upgrades" in summary["escalation_forbidden"] and summary["defaults_forbidden"]
    for capability in ("tcp_orientation_frame", "camera_view_from_record", "dynamic_scene_objects_from_record"):
        assert parts[capability]["status"] == "blocked" and parts[capability]["gaps"], capability
    assert all("frontend_rule" in item for item in parts.values())


def test_tcp_cross_check_distinguishes_the_root_conventions(tmp_path):
    client, expected = _pose_client_fk(tmp_path)
    body = client.get(f"/api/v1/episodes/{EPISODE}/robot-state").json()
    check = body["tcp_kinematic_cross_check"]
    assert check["status"] == "computed" and check["verdict"] == "consistent"
    assert check["recorded_tcp_position_m"] == pytest.approx(expected, abs=1e-12)
    assert check["abs_error_m"] < 1e-9
    assert check["joints_left_at_zero"] == [] and check["chain_links"][-1] == "guide_rod_link"
    assert check["movable_joints_on_chain"] == ["base_free", "joint1", "joint2", "joint3", "joint4", "joint5"]
    alternative = check["hypotheses"][1]
    assert alternative["verdict"] == "inconsistent"
    assert alternative["abs_error_m"] == pytest.approx(0.0556, abs=1e-9)   # the base body offset, once
    assert check["supports"].startswith("kinematic consistency")
    assert "does not calibrate hardware" in check["does_not_prove"]
    mapping = {item["target"]: item for item in body["mapping"]}
    assert mapping["arm_joint_positions"]["status"] == "verified"
    assert mapping["base_position"]["status"] == "verified" and mapping["base_orientation"]["status"] == "verified"
    assert mapping["tcp_site_position"]["status"] == "verified"
    assert mapping["gripper_joints"]["status"] == "unverified" and mapping["camera_extrinsics"]["status"] == "missing"
    parts = {item["capability"]: item for item in body["part_readiness"]}
    assert parts["base_pose_placement"]["status"] == "ready_with_caveats"
    assert parts["tcp_position_marker"]["status"] == "ready_with_caveats"
    assert body["capability_summary"]["kinematic_agreement"] == "consistent"
    assert body["capability_summary"]["whole_robot_pose_rebuildable"] is False


def test_a_disagreeing_tcp_keeps_the_base_and_marker_conditional(tmp_path):
    body = _pose_client(tmp_path).get(f"/api/v1/episodes/{EPISODE}/robot-state").json()
    check = body["tcp_kinematic_cross_check"]
    assert check["verdict"] == "inconsistent" and check["abs_error_m"] > 0.1
    mapping = {item["target"]: item for item in body["mapping"]}
    assert mapping["base_position"]["status"] == "unverified"
    assert mapping["arm_joint_positions"]["status"] == "partially_verified"
    parts = {item["capability"]: item for item in body["part_readiness"]}
    assert parts["base_pose_placement"]["status"] == "conditional"
    assert parts["tcp_position_marker"]["status"] == "conditional"
    assert body["capability_summary"]["usable_now"] == ["fixed_model_reference_assembly", "arm_local_pose"]
    assert "gripper_visual_appearance" in body["capability_summary"]["usable_only_with_the_named_caveat"]
