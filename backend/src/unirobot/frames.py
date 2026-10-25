"""Read-only frame linkage for one historical Episode: image frame to recorded robot state.

This answers the question a historical replay cursor needs first — "which robot state does the
recorder itself tie to this image frame?" — using only keys and clocks present in the native
records. Measured on the real source
(run_0104613ff7364ae78cf2f3946bd45f7b / episode_27bfed5427684795b361cd2ec21e9aa7, 303 persisted
frames): observations/persist -> observations/index joins 303/303 by ``sample_id``, -> transforms
joins 303/303 by ``sample_id``, -> the state feedback event joins 303/303 by
``capture_control_tick_id`` == ``control_tick_id``, while the declared ``feedback_sample_id``
resolves to an observation row in only 3/303 frames. That case is returned as an unresolved
reference, never as a match: no filename guessing, no line ordering, no nearest-by-closeness, no
interpolation, and no state carried over from a neighbouring frame.

Everything here reads. A joined record whose own ``run_id``/``episode_id`` differs from the
anchor's is reported as an identity mismatch instead of being merged into the frame.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterator

from .episodes import (DEFAULT_PAGE, ID_TOKEN, MAX_PAGE, MAX_RECORD_BYTES, STREAMS, EpisodeArchive,
                       EpisodeLocation, HistoryError, _now)

FRAME_LINK_SCHEMA = "unirobot-mobilecar-frame-link-1"

# Only the time bases that actually exist on the anchor records, measured on the real source.
FRAME_TIME_BASES = {
    "capture_backend_monotonic_s": "seconds, native backend monotonic clock at capture",
    "capture_sim_time_s": "seconds, simulator time at capture",
    "persist_backend_monotonic_s": "seconds, native backend monotonic clock at persist",
}

# role -> (source stream, recorded join key, what satisfying the role means)
ROLE_SEMANTICS = {
    "image_observation": ("observations-index", "sample_id",
                          "the rgb and depth observation rows recorded for this frame, each with its own media uri"),
    "camera_transform": ("transforms", "sample_id",
                         "camera extrinsics recorded for this frame; not a per-body pose sequence"),
    "capture_timing_event": ("events", "payload.sample_id",
                             "the recorder's own capture-timing event for this frame"),
    "state_feedback_event": ("events", "control_tick_id",
                             "recorded robot state feedback carried on the frame's capture tick"),
    "feedback_observation_row": ("observations-index", "sample_id",
                                 "an observation row whose own sample_id equals the frame's declared feedback_sample_id"),
}

PRIMARY_ROLES = ("image_observation", "camera_transform", "capture_timing_event", "state_feedback_event")
STATE_EVENT_TYPES = ("feedback", "feedback_initial")
TIMING_EVENT_TYPE = "rgbd_capture_timing"

SELECTION_RULES = {
    "joins": "exact equality of the recorded join key named on each role; never a filename, line order or browser arrival order",
    "when_nothing_matches": "the role is reported as missing, unresolved_reference or stream_absent, with the key that was looked for",
    "state_hold": "not applied: a frame never inherits another frame's state",
    "interpolation": "none",
    "nearest_in_time": "not used; numeric closeness is not treated as identity or as simultaneity",
}

NOT_PROVEN = [
    "that two records naming the same clock base were stamped at the same instant: naming is not verification",
    "a cross-stream or cross-episode replay cursor: this page links records inside one Episode only",
    "rendered 3D replay: a transform row is camera extrinsics plus the joint values recorded with it",
    "archive-wide integrity: only the files this request opened are covered",
]

FRAME_FIELDS = ("stream_id", "sample_id", "sensor_kind", "frame_id", "clock_id", "source", "quality",
                "measurement_time_s", "arrival_time_s", "asset_uri", "valid_mask_uri", "capture_sim_time_s",
                "capture_backend_monotonic_s", "capture_control_tick_id", "feedback_sample_id")
EVENT_FIELDS = ("event_seq", "event_type", "control_tick_id", "backend_monotonic_s", "sim_time_s", "wall_utc")
TRANSFORM_FIELDS = ("stream_id", "sample_id", "frame_id", "clock_id", "source", "measurement_time_s", "arrival_time_s")


def _relative(stream_id: str) -> str:
    return STREAMS[stream_id][0]


def _stream_lines(path, tokens: tuple[str, ...]) -> Iterator[tuple[int, dict[str, Any]]]:
    """Yield only the records that can carry one of the wanted keys, keeping the native line index.

    The substring test filters raw text and never changes provenance: ``line_index`` stays the
    real line number in the file, so every returned linkage can be pointed back to its position.
    """
    needles = tuple(f'"{token}"' for token in tokens)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for index, raw in enumerate(handle):
            if not raw.strip() or len(raw) > MAX_RECORD_BYTES or not any(item in raw for item in needles):
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield index, record


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _delta(capture: Any, other: Any, *, label: str, basis: str) -> dict[str, Any] | None:
    """Subtraction of two recorded numbers with the sign kept; never a synchronisation claim."""
    if not _number(capture) or not _number(other):
        return None
    value = other - capture
    return {"label": label, "capture_value": capture, "other_value": other, "value_s": value,
            "abs_value_ms": abs(value) * 1000.0,
            "direction": "earlier" if value < 0 else "later" if value > 0 else "equal",
            "basis": basis, "meaning": "recorded minus recorded, seconds"}


def _identity(record: dict[str, Any], location: EpisodeLocation) -> dict[str, Any]:
    return {"run_id_matches": record.get("run_id") == location.run_id,
            "episode_id_matches": record.get("episode_id") == location.episode_id,
            "declared_run_id": record.get("run_id"), "declared_episode_id": record.get("episode_id")}


def _clocks(record: dict[str, Any]) -> dict[str, Any]:
    keys = ("clock_id", "measurement_time_s", "arrival_time_s", "backend_monotonic_s", "sim_time_s", "wall_utc",
            "capture_backend_monotonic_s", "capture_sim_time_s", "persist_backend_monotonic_s",
            "arrival_backend_monotonic_s", "arrival_to_persist_ms", "capture_to_persist_ms")
    return {key: record.get(key) for key in keys if key in record}


def _declared_media(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Media this row itself cites, with the digest the recorder declared next to it."""
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    out = []
    for field in ("asset_uri", "valid_mask_uri"):
        uri = record.get(field)
        if isinstance(uri, str):
            out.append({"uri": uri, "declared_sha256": metadata.get("asset_sha256") if field == "asset_uri" else None,
                        "declared_bytes": metadata.get("asset_bytes") if field == "asset_uri" else None})
    return out


class FrameLinkReader:
    def __init__(self, archive: EpisodeArchive) -> None:
        self.archive = archive

    # ---- public entry point ------------------------------------------------------

    def frames(self, episode_id: str, *, run_id: str | None = None, stream: str = "rgbd",
               limit: int = DEFAULT_PAGE, offset: int = 0, time_base: str | None = None,
               time_from: float | None = None, time_to: float | None = None,
               sample_id: str | None = None) -> dict[str, Any]:
        location = self.archive.location(episode_id, run_id)
        anchor_path = location.path_of("observations-persist")
        if not anchor_path.is_file():
            raise HistoryError("episode_stream_unavailable", "this Episode recorded no persisted frames", 404,
                               {"stream_id": "observations-persist", "relative_path": _relative("observations-persist")})
        if time_base and time_base not in FRAME_TIME_BASES:
            raise HistoryError("time_base_unsupported", f"unknown frame time base: {time_base}", 400,
                               {"supported": sorted(FRAME_TIME_BASES),
                                "note": "only bases present on the persisted frame records are selectable here"})
        if time_base and time_from is None and time_to is None:
            raise HistoryError("time_range_required", "time_base needs time_from or time_to in that base", 400)
        if sample_id and not re.fullmatch(ID_TOKEN, sample_id):
            raise HistoryError("sample_id_invalid", "sample id is not a native id token", 400)

        anchors, counters = self._anchors(
            location, anchor_path, stream=stream, limit=limit, offset=offset, sample_id=sample_id,
            # The selectable base is the recorded field name itself; the mapping only describes it.
            selected_field=time_base, time_from=time_from, time_to=time_to)
        links = self._collect(location, anchors)
        frames = [self._frame(location, line_index, record, links) for line_index, record in anchors]
        return {
            "schema_version": FRAME_LINK_SCHEMA,
            "read_only": True,
            "source": self._source_view(location),
            "retrieved_at": _now(),
            "identity": {"run_id": location.run_id, "episode_id": location.episode_id,
                         "episode_directory": str(location.directory),
                         "run_directory_identity": "the run directory was re-validated as itself before this read",
                         "native_contract_version": self.archive.source.contract_version},
            "anchor": {"stream_id": "observations-persist", "relative_path": _relative("observations-persist"),
                       "semantics": "one persisted image frame per record, carrying the recorder's own capture and persist clocks",
                       "requested_stream": stream},
            "paging": {"limit": limit, "offset": offset, "returned": len(frames),
                       "scanned_anchor_lines": counters["scanned"], "skipped_before_offset": counters["skipped_before"],
                       "excluded_stream_mismatch": counters["excluded_no_stream"],
                       "excluded_without_sample_id": counters["excluded_no_anchor_key"],
                       "excluded_outside_time_window": counters["excluded_outside_window"],
                       "excluded_anchor_identity_mismatch": counters["excluded_identity_mismatch"],
                       "records_missing_selected_time_base": counters["missing_selected_base"],
                       "next_offset": anchors[-1][0] + 1 if anchors else None,
                       "has_more": bool(anchors) and counters["scanned"] > anchors[-1][0] + 1},
            "cursor": {"order": "native_append_order_of_the_anchor_stream",
                       "line_index_is_not_a_clock": True,
                       "persist_sequence_is_the_recorders_own_counter": True,
                       "first_line_index": anchors[0][0] if anchors else None,
                       "last_line_index": anchors[-1][0] if anchors else None,
                       "first_persist_sequence": anchors[0][1].get("persist_sequence") if anchors else None,
                       "last_persist_sequence": anchors[-1][1].get("persist_sequence") if anchors else None},
            "time": {"selected_time_base": time_base, "time_from": time_from, "time_to": time_to,
                     "selectable_time_bases": sorted(FRAME_TIME_BASES),
                     "units": {"*_s": "seconds", "*_ms": "milliseconds", "*_rad": "radians", "*_m": "metres"},
                     "synchronized_across_streams": False,
                     "clock_sameness": {"declared_by_recorder": True, "verified_by_reader": False,
                                        "note": "records name a clock base and the timing event declares feedback_clock; naming is not verification that two writers shared one clock"},
                     "deltas_are_recorded_arithmetic": True,
                     "browser_arrival_order_is_not_used": True},
            "linkage": {"roles": {role: {"source_stream": info[0], "join_key": info[1], "meaning": info[2]}
                                  for role, info in ROLE_SEMANTICS.items()},
                        "status_meaning": {"matched": "every expected record for the role was found by its recorded key",
                                           "partial": "some but not all expected records for the role were found",
                                           "missing": "no record for this role carried the key",
                                           "unresolved_reference": "the frame declares a reference whose target record is not in this Episode",
                                           "identity_mismatch": "a candidate record named a different run or Episode and was excluded",
                                           "stream_absent": "the source stream is not recorded in this Episode"},
                        "selection_rules": SELECTION_RULES,
                        "primary_roles": list(PRIMARY_ROLES),
                        "role_coverage_on_this_page": self._coverage(frames)},
            "summary": {"frames_returned": len(frames),
                        "frames_with_all_primary_roles_matched": sum(1 for item in frames if item["linkage_status"] == "matched"),
                        "frames_with_some_primary_roles_missing": sum(1 for item in frames if item["linkage_status"] == "partial"),
                        "frames_with_no_primary_role_matched": sum(1 for item in frames if item["linkage_status"] == "missing"),
                        "frames_without_a_linked_state": sum(1 for item in frames
                                                             if item["state"]["status"] != "matched"),
                        "frames_with_unresolved_feedback_reference": sum(1 for item in frames
                                                                         if item["declared_reference_status"] == "unresolved_reference")},
            "frames": frames,
            "not_proven": NOT_PROVEN,
            "three_d_replay": {"this_slice_does_not_enable_3d_replay": True,
                               "live_geometry_or_actual_may_be_applied": False,
                               "transforms_are_full_per_body_pose_sequences": False},
            "capability_limits": ["no replay execution", "no cross-episode cursor", "no native validate proxy",
                                  "no control, RESET, recording or physics stepping"],
        }

    # ---- anchors ------------------------------------------------------------------

    def _anchors(self, location: EpisodeLocation, path, *, stream: str, limit: int, offset: int,
                 sample_id: str | None, selected_field: str | None, time_from: float | None,
                 time_to: float | None) -> tuple[list[tuple[int, dict[str, Any]]], dict[str, int]]:
        anchors: list[tuple[int, dict[str, Any]]] = []
        counters = {"scanned": 0, "skipped_before": 0, "excluded_no_stream": 0, "excluded_no_anchor_key": 0,
                    "missing_selected_base": 0, "excluded_outside_window": 0, "excluded_identity_mismatch": 0}
        for line_index, record in _stream_lines(path, (stream,)):
            counters["scanned"] += 1
            # The frame record names its own run and Episode; a page never serves a frame that
            # declares someone else's identity, even when the directory itself looked legitimate.
            if record.get("run_id") != location.run_id or record.get("episode_id") != location.episode_id:
                counters["excluded_identity_mismatch"] += 1
                continue
            if record.get("stream_id") != stream:
                counters["excluded_no_stream"] += 1
                continue
            if not isinstance(record.get("sample_id"), str):
                counters["excluded_no_anchor_key"] += 1
                continue
            if sample_id and record.get("sample_id") != sample_id:
                continue
            if selected_field:
                stamp = record.get(selected_field)
                if not _number(stamp):
                    counters["missing_selected_base"] += 1
                    continue
                if (time_from is not None and stamp < time_from) or (time_to is not None and stamp > time_to):
                    counters["excluded_outside_window"] += 1
                    continue
            if line_index < offset:
                counters["skipped_before"] += 1
                continue
            if len(anchors) >= limit:
                break
            anchors.append((line_index, record))
        return anchors, counters

    # ---- join collection ----------------------------------------------------------

    def _collect(self, location: EpisodeLocation,
                 anchors: list[tuple[int, dict[str, Any]]]) -> dict[str, Any]:
        sample_ids = tuple(record["sample_id"] for _, record in anchors)
        ticks = tuple(item for item in (record.get("capture_control_tick_id") for _, record in anchors)
                      if isinstance(item, str))
        feedback_ids = tuple(item for item in (record.get("feedback_sample_id") for _, record in anchors)
                             if isinstance(item, str))
        links: dict[str, Any] = {"observations-index": {}, "transforms": {}, "events": {},
                                 "sample_ids": set(sample_ids), "feedback_ids": set(feedback_ids)}

        for stream_id, tokens in (("observations-index", tuple(dict.fromkeys(sample_ids + feedback_ids))),
                                  ("transforms", sample_ids)):
            path = location.path_of(stream_id)
            links[stream_id]["absent"] = not path.is_file()
            if not path.is_file() or not tokens:
                continue
            wanted = set(tokens)
            for line_index, record in _stream_lines(path, tokens):
                key = record.get("sample_id")
                if isinstance(key, str) and key in wanted:
                    links[stream_id].setdefault("rows", {}).setdefault(key, []).append((line_index, record))

        path = location.path_of("events")
        links["events"]["absent"] = not path.is_file()
        if path.is_file() and (ticks or sample_ids):
            tick_set, sample_set = set(ticks), set(sample_ids)
            for line_index, record in _stream_lines(path, tuple(dict.fromkeys(ticks + sample_ids))):
                event_type = record.get("event_type")
                payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
                tick = record.get("control_tick_id")
                if event_type in STATE_EVENT_TYPES and isinstance(tick, str) and tick in tick_set:
                    links["events"].setdefault("state", {}).setdefault(tick, []).append((line_index, record))
                elif event_type == TIMING_EVENT_TYPE and payload.get("sample_id") in sample_set:
                    links["events"].setdefault("timing", {}).setdefault(payload["sample_id"], []).append((line_index, record))
        return links

    # ---- one frame ---------------------------------------------------------------

    def _entry(self, location: EpisodeLocation, stream_id: str, line_index: int, record: dict[str, Any],
               fields: tuple[str, ...], *, with_media: bool = False, with_payload: bool = False) -> dict[str, Any]:
        metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else None
        entry = {"stream_id": stream_id, "relative_path": _relative(stream_id), "line_index": line_index,
                 "record_position": f"{_relative(stream_id)}#{line_index}",
                 "identity": _identity(record, location), "clocks": _clocks(record),
                 "projection": {key: record.get(key) for key in fields if key in record},
                 "metadata_keys": sorted(metadata) if metadata else None,
                 "present_fields": sorted(key for key in record if key not in ("payload", "value", "metadata"))}
        if with_media:
            entry["declared_media"] = _declared_media(record)
        if with_payload and isinstance(record.get("payload"), dict):
            entry["payload"] = record["payload"]
        return entry

    def _role(self, location: EpisodeLocation, role: str, key_value: Any,
              sources: list[tuple[int, dict[str, Any]]], *, stream_absent: bool, fields: tuple[str, ...],
              expected: int | None, unresolved_when_absent: bool = False,
              with_media: bool = False, with_payload: bool = False) -> dict[str, Any]:
        stream_id, join_key, meaning = ROLE_SEMANTICS[role]
        entries: list[dict[str, Any]] = []
        mismatched = 0
        for line_index, record in sources:
            entry = self._entry(location, stream_id, line_index, record, fields,
                                with_media=with_media, with_payload=with_payload)
            if entry["identity"]["run_id_matches"] and entry["identity"]["episode_id_matches"]:
                entries.append(entry)
            else:
                mismatched += 1
        if stream_absent:
            status = "stream_absent"
        elif mismatched:
            status = "identity_mismatch"
        elif not entries:
            status = "unresolved_reference" if (unresolved_when_absent and key_value is not None) else "missing"
        elif expected is not None and len(entries) < expected:
            status = "partial"
        else:
            status = "matched"
        return {"role": role, "join_key": join_key, "key_value": key_value, "meaning": meaning, "status": status,
                "expected_records": expected, "matched_records": len(entries),
                "identity_mismatched_records": mismatched, "sources": entries}

    def _frame(self, location: EpisodeLocation, line_index: int, record: dict[str, Any],
               links: dict[str, Any]) -> dict[str, Any]:
        sample_id = record["sample_id"]
        tick = record.get("capture_control_tick_id")
        feedback_id = record.get("feedback_sample_id")
        index_rows = links["observations-index"].get("rows", {}).get(sample_id, [])
        transform_rows = links["transforms"].get("rows", {}).get(sample_id, [])
        timing_rows = links["events"].get("timing", {}).get(sample_id, [])
        state_rows = links["events"].get("state", {}).get(tick, []) if isinstance(tick, str) else []
        # A feedback id that happens to be one of this page's own frame ids is not a reference target.
        feedback_rows = (links["observations-index"].get("rows", {}).get(feedback_id, [])
                         if isinstance(feedback_id, str) and feedback_id not in links["sample_ids"] else [])
        index_absent = links["observations-index"].get("absent", False)
        events_absent = links["events"].get("absent", False)

        roles = [
            self._role(location, "image_observation", sample_id, index_rows, stream_absent=index_absent,
                       expected=2, fields=FRAME_FIELDS, with_media=True),
            self._role(location, "camera_transform", sample_id, transform_rows,
                       stream_absent=links["transforms"].get("absent", False), expected=1, fields=TRANSFORM_FIELDS),
            self._role(location, "capture_timing_event", sample_id, timing_rows, stream_absent=events_absent,
                       expected=1, fields=EVENT_FIELDS, with_payload=True),
            self._role(location, "state_feedback_event", tick, state_rows, stream_absent=events_absent,
                       expected=1, fields=EVENT_FIELDS, with_payload=True),
            self._role(location, "feedback_observation_row", feedback_id, feedback_rows, stream_absent=index_absent,
                       expected=1, unresolved_when_absent=True,
                       fields=("stream_id", "sample_id", "sensor_kind", "frame_id", "clock_id",
                               "measurement_time_s", "arrival_time_s")),
        ]
        by_role = {item["role"]: item for item in roles}
        primary = [by_role[name] for name in PRIMARY_ROLES]
        matched_primary = sum(1 for item in primary if item["status"] == "matched")
        linkage_status = ("matched" if matched_primary == len(primary)
                          else "missing" if matched_primary == 0 else "partial")
        media = self._media(location, record, by_role["image_observation"])
        state = self._state(record, by_role)
        times = self._times(record, by_role)
        return {
            "sample_id": sample_id,
            "stream_id": record.get("stream_id"),
            "anchor": {"line_index": line_index, "relative_path": _relative("observations-persist"),
                       "persist_sequence": record.get("persist_sequence"), "identity": _identity(record, location),
                       "clocks": _clocks(record), "declared_keys": sorted(record),
                       "reference_keys": {"capture_control_tick_id": tick, "feedback_sample_id": feedback_id},
                       "profile": {"profile_id": record.get("profile_id"), "profile_version": record.get("profile_version"),
                                   "profile_sha256": record.get("profile_sha256"),
                                   "interface_profile": record.get("interface_profile"), "kinds": record.get("kinds")}},
            "linkage_status": linkage_status,
            "primary_roles_matched": [item["role"] for item in primary if item["status"] == "matched"],
            "declared_reference_status": by_role["feedback_observation_row"]["status"],
            "media": media,
            "state": state,
            "times": times,
            "roles": roles,
        }

    # ---- frame sections ---------------------------------------------------------

    def _media(self, location: EpisodeLocation, record: dict[str, Any],
               image_role: dict[str, Any]) -> dict[str, Any]:
        """Media the frame declares, its availability as observed, and what the rows declare.

        The anchor uri and the row uri are compared as recorded strings. Digests stay declared
        here: they are recomputed only when the asset endpoint actually serves a file.
        """
        rows_by_kind = {}
        for entry in image_role["sources"]:
            kind = entry["projection"].get("sensor_kind")
            if isinstance(kind, str):
                rows_by_kind.setdefault(kind, entry)
        items: list[dict[str, Any]] = []
        for field, kind in (("rgb_uri", "rgb"), ("depth_uri", "depth"), ("valid_mask_uri", "depth")):
            uri = record.get(field)
            entry: dict[str, Any] = {"field": field, "uri": uri if isinstance(uri, str) else None}
            if not isinstance(uri, str):
                entry.update({"availability": "not_recorded_on_this_frame", "row_line_index": None,
                              "agrees_with_observation_row": None, "declared_sha256_by_row": None})
                items.append(entry)
                continue
            row = rows_by_kind.get(kind)
            row_uris = [item["uri"] for item in (row or {}).get("declared_media") or []]
            entry.update({"row_line_index": (row or {}).get("line_index"),
                          "agrees_with_observation_row": (uri in row_uris) if row_uris else None,
                          "declared_sha256_by_row": next((item["declared_sha256"] for item in
                                                          (row or {}).get("declared_media") or []
                                                          if item["uri"] == uri), None),
                          "declared_bytes_by_row": next((item["declared_bytes"] for item in
                                                         (row or {}).get("declared_media") or []
                                                         if item["uri"] == uri), None)})
            try:
                path = location.checked(uri, scope="assets")
            except HistoryError as exc:
                entry.update({"availability": "refused", "refusal_code": exc.code})
                items.append(entry)
                continue
            present = path.is_file()
            entry.update({"availability": "present" if present else "absent",
                          "bytes_on_disk": path.stat().st_size if present else None})
            items.append(entry)
        return {"declared_by": "the persisted frame record and its observation rows, copied verbatim",
                "uri_convention": "assets/<kind>/<file>, served only from this episode's assets tree",
                "digest_verification": "declared only; recomputed when the asset endpoint serves the file",
                "items": items}

    def _state(self, record: dict[str, Any], by_role: dict[str, dict[str, Any]]) -> dict[str, Any]:
        role = by_role["state_feedback_event"]
        source = role["sources"][0] if role["sources"] else None
        timing = by_role["capture_timing_event"]["sources"]
        payload = (timing[0].get("payload") or {}) if timing else {}
        return {"status": role["status"], "join_key": role["join_key"], "key_value": role["key_value"],
                "source": None if source is None else {"stream_id": source["stream_id"],
                                                        "relative_path": source["relative_path"],
                                                        "line_index": source["line_index"],
                                                        "event_seq": source["projection"].get("event_seq"),
                                                        "event_type": source["projection"].get("event_type")},
                "recorded_fields": source["projection"] if source else None,
                "recorded_state": (source or {}).get("payload"),
                "declared_reference": {"feedback_sample_id": record.get("feedback_sample_id"),
                                       "row_status": by_role["feedback_observation_row"]["status"]},
                "recorder_declared_feedback": {"available": payload.get("feedback_time_s") is not None,
                                               "feedback_time_s": payload.get("feedback_time_s"),
                                               "feedback_clock": payload.get("feedback_clock"),
                                               "capture_clocks_declared": payload.get("capture_clocks"),
                                               "meaning": "the recorder's own declared feedback time for this frame, copied, not re-derived"},
                "units": {"*_rad": "radians", "*_rad_s": "radians per second", "*_m": "metres", "*_nm": "newton metres",
                          "*_xyzw": "quaternion x,y,z,w", "*_s": "seconds"},
                "carried_over_from_another_frame": False,
                "interpolated": False,
                "note": "this is the state the recorder placed on the frame's capture tick, not a verified same-instant sample of the scene"}

    def _times(self, record: dict[str, Any], by_role: dict[str, dict[str, Any]]) -> dict[str, Any]:
        capture = record.get("capture_backend_monotonic_s")
        deltas: list[dict[str, Any]] = []

        def add(value: Any, label: str, basis: str, **extra: Any) -> None:
            item = _delta(capture, value, label=label, basis=basis)
            if item:
                deltas.append({**item, **extra})

        state = by_role["state_feedback_event"]["sources"]
        if state:
            add(state[0]["projection"].get("backend_monotonic_s"), "state_event_minus_frame_capture",
                "events record backend_monotonic_s minus persisted frame capture_backend_monotonic_s",
                line_index=state[0]["line_index"])
        timing = by_role["capture_timing_event"]["sources"]
        if timing:
            payload = timing[0].get("payload") or {}
            add(payload.get("feedback_time_s"), "recorder_declared_feedback_time_minus_capture",
                "rgbd_capture_timing payload feedback_time_s minus persisted frame capture_backend_monotonic_s")
            add(payload.get("capture_backend_monotonic_s"), "timing_event_capture_clock_minus_anchor_capture",
                "rgbd_capture_timing payload capture_backend_monotonic_s minus the same field on the anchor")
        for row in by_role["image_observation"]["sources"]:
            for field in ("measurement_time_s", "arrival_time_s"):
                add(row["projection"].get(field), f"observation_{field}_minus_frame_capture",
                    f"observations index row {field} minus persisted frame capture_backend_monotonic_s",
                    sensor_kind=row["projection"].get("sensor_kind"), line_index=row["line_index"])
        add(record.get("persist_backend_monotonic_s"), "persist_minus_capture",
            "persisted frame persist_backend_monotonic_s minus capture_backend_monotonic_s")
        state_delta = next((item for item in deltas if item["label"] == "state_event_minus_frame_capture"), None)
        return {"deltas": deltas,
                "declared_latency_ms": {key: record.get(key) for key in ("arrival_to_persist_ms", "capture_to_persist_ms")
                                        if record.get(key) is not None},
                "age_of_state_relative_to_frame": None if state_delta is None else {
                    "abs_ms": state_delta["abs_value_ms"],
                    "state_recorded_before_capture": state_delta["direction"] == "earlier",
                    "display_hint": "show as the age of the state; not a synchronised instant"},
                "same_clock_verified": False}

    @staticmethod
    def _coverage(frames: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for role in ROLE_SEMANTICS:
            counts: dict[str, int] = {}
            for frame in frames:
                entry = next(item for item in frame["roles"] if item["role"] == role)
                counts[entry["status"]] = counts.get(entry["status"], 0) + 1
            out[role] = counts
        return out

    @staticmethod
    def _source_view(location: EpisodeLocation) -> dict[str, Any]:
        reference = location.relative_reference()
        source = location.source
        return {"source_id": source.source_id, "adapter_id": source.adapter_id, "robot_id": source.robot_id,
                "native_release_id": source.native_release_id, "native_contract_version": source.contract_version,
                "recording_root": source.recording_root, "recording_root_resolved": reference["recording_root_resolved"],
                "access": source.access, "declaring_instance": source.declaring_instance,
                "archive_baseline": source.archive_baseline, "platform_writes": False,
                "path_boundary": "every derived path is re-resolved and must stay inside the declared root and, for "
                                 "episode contents, inside that episode's resolved directory; the run directory must "
                                 "additionally resolve to itself"}
