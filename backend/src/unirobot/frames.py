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

A role is complete only when the records its own semantics demand are present exactly once: an
image frame needs one ``rgb`` row and one ``depth`` row, so two rows of one kind are never a
complete pair, and repeated state, transform or timing candidates for one key are reported as
ambiguous with every candidate listed rather than resolved to the first line in the file.

Everything here reads. A joined record whose own ``run_id``/``episode_id`` differs from the
anchor's is reported as an identity mismatch instead of being merged into the frame.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterator

from .episodes import (DEFAULT_PAGE, ID_TOKEN, MAX_PAGE, MAX_RECORD_BYTES, STREAMS, EpisodeArchive,
                       EpisodeLocation, HistoryError, _now)

FRAME_LINK_SCHEMA = "unirobot-mobilecar-frame-link-2"

# Only the time bases that actually exist on the anchor records, measured on the real source.
FRAME_TIME_BASES = {
    "capture_backend_monotonic_s": "seconds, native backend monotonic clock at capture",
    "capture_sim_time_s": "seconds, simulator time at capture",
    "persist_backend_monotonic_s": "seconds, native backend monotonic clock at persist",
}

# Each selectable base names its own clock; the label is copied from the record's vocabulary,
# and a shared name across streams is never treated as proof of a shared clock source.
FRAME_TIME_BASE_CLOCKS = {
    "capture_backend_monotonic_s": "backend_monotonic",
    "capture_sim_time_s": "sim",
    "persist_backend_monotonic_s": "backend_monotonic",
}

# Playback is three separate claims. A is display order, B schedules on recorded intervals of one
# base, C aligns streams. Neither A nor B earns C, and B is earned per base by measurement.
PLAYBACK_MODES = {
    "append_order_display": "A: show anchors in the recorder's own append order of the anchor file",
    "recorded_interval_schedule": "B: schedule a step by the recorded gap on one named capture base",
    "cross_stream_synchronized": "C: play several streams against one verified shared instant",
}

# The scan is bounded so that asking for the census stays cheap and stays honest about its scope.
TIME_QUALITY_ANCHOR_LIMIT = 4000
TIME_QUALITY_DUPLICATE_LIST_LIMIT = 20
TIME_QUALITY_UNDECIDABLE_LIST_LIMIT = 20

# Which line counter feeds which claim. A line the reader cannot decide about is not a line the
# reader may exclude and then ignore: it could have carried the very anchor being counted.
LINE_ACCOUNTING = {
    "blank_lines_skipped": {"classification": "benign", "may_hide_an_anchor": False,
                            "affects_whole_episode_qualification": False,
                            "why": "an empty line carries no record at all, so nothing about it is unknown"},
    "prefiltered_lines_skipped": {"classification": "benign", "may_hide_an_anchor": False,
                                  "affects_whole_episode_qualification": False,
                                  "why": "raw text that cannot contain the requested stream_id token is not an "
                                         "anchor record of the requested stream under the reader's own documented "
                                         "prefilter rule"},
    "oversize_lines_skipped": {"classification": "undecidable", "may_hide_an_anchor": True,
                               "affects_whole_episode_qualification": True,
                               "why": "the content was never parsed, so it cannot be ruled out as an anchor record"},
    "unparseable_lines_skipped": {"classification": "undecidable", "may_hide_an_anchor": True,
                                  "affects_whole_episode_qualification": True,
                                  "why": "a truncated or half-written line is exactly how a lost anchor would look"},
    "non_object_lines_skipped": {"classification": "undecidable", "may_hide_an_anchor": True,
                                 "affects_whole_episode_qualification": True,
                                 "why": "valid JSON that is not an object is not a conforming record, and what it "
                                        "was meant to carry is unknown"},
}


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _base_statistics(samples: list[tuple[int, dict[str, Any]]], field: str) -> dict[str, Any]:
    """Measure one base over the scanned anchors in file order; first/last is never renamed min/max.

    Nothing is sorted into the anchor sequence: the time-ordered comparison below is reported as a
    fact about the recorded values while the frames themselves stay addressed by their raw line index.
    """
    numeric: list[tuple[int, float]] = []
    missing: list[int] = []
    non_numeric: list[dict[str, Any]] = []
    for line_index, record in samples:
        raw = record.get(field)
        if _number(raw):
            numeric.append((line_index, raw))
        elif field not in record:
            missing.append(line_index)
        else:
            non_numeric.append({"line_index": line_index, "value_type": type(raw).__name__})
    gaps = [numeric[index][1] - numeric[index - 1][1] for index in range(1, len(numeric))]
    backwards = [{"from_line_index": numeric[index - 1][0], "to_line_index": numeric[index][0], "step_s": gap}
                 for index, gap in enumerate(gaps, start=1) if gap < 0.0]
    equal = [[numeric[index - 1][0], numeric[index][0]] for index, gap in enumerate(gaps, start=1) if gap == 0.0]
    ordered_values = sorted(value for _, value in numeric)
    time_order = [line_index for line_index, _ in sorted(numeric, key=lambda item: (item[1], item[0]))]
    limit = TIME_QUALITY_DUPLICATE_LIST_LIMIT
    return {"field": field, "unit": "s", "clock": FRAME_TIME_BASE_CLOCKS[field],
            "source_record": "persisted frame anchor in observations/persist.jsonl",
            "anchors_scanned": len(samples), "numeric_count": len(numeric),
            "missing_count": len(missing), "missing_line_indexes": missing[:limit],
            "missing_line_indexes_truncated": len(missing) > limit,
            "non_numeric_count": len(non_numeric), "non_numeric_samples": non_numeric[:limit],
            "non_numeric_samples_truncated": len(non_numeric) > limit,
            "first_in_file_order": numeric[0][1] if numeric else None,
            "last_in_file_order": numeric[-1][1] if numeric else None,
            "first_line_index": numeric[0][0] if numeric else None,
            "last_line_index": numeric[-1][0] if numeric else None,
            "min_recorded_value": ordered_values[0] if ordered_values else None,
            "max_recorded_value": ordered_values[-1] if ordered_values else None,
            "first_minus_last_s": (numeric[0][1] - numeric[-1][1]) if len(numeric) >= 2 else None,
            "recorded_gaps": {"count": len(gaps), "min_s": min(gaps) if gaps else None,
                              "max_s": max(gaps) if gaps else None, "median_s": _median(gaps),
                              "mean_s": (sum(gaps) / len(gaps)) if gaps else None,
                              "total_s": sum(gaps) if gaps else None},
            "equal_adjacent_gaps": {"count": len(equal), "line_index_pairs": equal[:limit],
                                    "line_index_pairs_truncated": len(equal) > limit},
            "backwards_gaps": {"count": len(backwards), "steps": backwards[:limit],
                               "steps_truncated": len(backwards) > limit},
            "monotonic_non_decreasing_in_file_order": not backwards,
            "file_order_matches_value_order": time_order == [line_index for line_index, _ in numeric]}

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
    # These two are optional action roles: they are reported only when the record really shares the
    # frame's capture tick, and they never change a frame's own completeness verdict.
    "recorded_target_event": ("events", "control_tick_id",
                              "the recorded actuator reference (Target) carried on the frame's capture tick; a "
                              "target is not an achieved state"),
    "command_dispatch_event": ("events", "control_tick_id",
                              "the command record the recorder marked as dispatched on the frame's capture tick; "
                              "sparse, and absent for most frames by measurement"),
}

# Completeness is decided by what the role means, not by how many lines happened to carry the key.
ROLE_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "image_observation": {"required_kinds": ("rgb", "depth"), "kind_cardinality": 1,
                          "rule": "one row per required sensor_kind, matched by the row's own sensor_kind field"},
    "camera_transform": {"exact_records": 1, "rule": "exactly one transform row for this sample_id"},
    "capture_timing_event": {"exact_records": 1, "rule": "exactly one rgbd_capture_timing event naming this sample_id"},
    "state_feedback_event": {"exact_records": 1, "rule": "exactly one state event carrying this control_tick_id"},
    "feedback_observation_row": {"exact_records": 1, "rule": "exactly one observation row whose sample_id equals the declared feedback id"},
    "recorded_target_event": {"exact_records": None, "requirement": "optional",
                              "rule": "reported only for records that really carry the frame's control_tick_id; "
                                      "absence stays absence and is never filled from a neighbouring tick"},
    "command_dispatch_event": {"exact_records": None, "requirement": "optional",
                               "rule": "reported only for records that really carry the frame's control_tick_id; "
                                       "a dispatched command is not evidence that the frame or the state reached it"},
}

PRIMARY_ROLES = ("image_observation", "camera_transform", "capture_timing_event", "state_feedback_event")
OPTIONAL_ACTION_ROLES = ("recorded_target_event", "command_dispatch_event")
# The roles every frame on a page carries; the optional action roles are reported only inside action_basis.
PAGE_ROLES = tuple(role for role in ROLE_SEMANTICS if role not in OPTIONAL_ACTION_ROLES)
STATE_EVENT_TYPES = ("feedback", "feedback_initial")
TIMING_EVENT_TYPE = "rgbd_capture_timing"
TARGET_EVENT_TYPE = "actuator_reference"
DISPATCH_EVENT_TYPE = "dispatch"
COMMAND_CHAIN_EVENT_TYPES = ("requested", "approved", "rejected", "dispatch")

# The categories a replay reader asks history about, each named by the event types the records
# really use. A category with no recorded type in the scanned scope is reported as not_recorded.
ACTION_CATEGORIES = {
    "recorded_state_initial": (("feedback_initial",), "the state snapshot the recorder took when the segment started"),
    "actual_state_feedback": (("feedback",), "recorded robot state as measured (Actual); never promoted to a live read"),
    "recorded_target": (("actuator_reference",), "recorded actuator reference (Target); a target is not an achieved state"),
    "command_intent": (("requested",), "a command the recorder saw requested; intent only, no execution claim"),
    "command_receipt_accepted": (("approved",), "a recorded approval decision beside the request"),
    "command_receipt_rejected": (("rejected",), "a recorded rejection; its absence is not evidence that nothing was rejected"),
    "command_dispatched": (("dispatch",), "a command the recorder marked as dispatched"),
    "capture_timing": (("rgbd_capture_timing",), "the recorder's own per-frame capture timing event"),
    "lease_boundary": (("lease_heartbeat", "lease_expired"), "lease renewal and expiry records naming a session; they are not a takeover protocol"),
    "episode_lifecycle": (("recording_start", "recording_stop", "episode_terminal"), "segment start, stop request and terminal declaration"),
}

# Join keys the reader may associate a record with, and the fields it must not confuse them with.
ACTION_JOIN_KEYS = ("control_tick_id", "command_id", "sample_id", "feedback_sample_id", "session_id")
OPERATOR_FIELDS = ("operator_id", "operator_kind", "view_source", "owner_session_id", "session_id", "channel")

ACTION_BASIS_EVENT_LIMIT = 20000
ACTION_BASIS_POSITION_LIMIT = 3
ACTION_BASIS_CANDIDATE_LIMIT = 8
ACTION_BASIS_COMMAND_LIMIT = 50

ACTION_BASIS_RULES = {
    "association": "exact equality of the recorded key; a frame's capture tick matched against the record's control_tick_id",
    "no_shared_key": "the category is reported as an independent event track, readable by event_seq and named time bases only",
    "when_several_match": "ambiguous_candidates with every candidate position listed; the first line in the file is not chosen",
    "when_nothing_matches": "missing, with the key that was looked for — no carry-over from the previous tick, no nearest-in-time",
    "rejected_requests": "a rejected or unapproved request is never presented as an executed action",
    "recorded_target": "an actuator reference is a recorded Target and is never reported as measured Actual state",
    "operator_source": "the source is whatever the record's own operator fields name; it is never defaulted to Human",
    "zero_action": "no action vector is invented for a tick that records none",
    "clock_parity": "numerically close or even equal stamps never upgrade a link: `synchronized_across_streams` and "
                    "`same_clock_verified` stay false, and an event whose time equals a frame's capture time but "
                    "which names no shared key stays an independent track",
    "units": "taken from the recorder's own field-name suffix; a field without a unit-bearing suffix is reported as unknown_from_field_name",
}

STATUS_MEANING = {
    "matched": "every record the role requires was found by its recorded key, once",
    "partial": "some but not all records the role requires were found",
    "missing": "no record for this role carried the key",
    "unresolved_reference": "the frame declares a reference whose target record is not in this Episode",
    "identity_mismatch": "a candidate record named a different run or Episode and was excluded",
    "stream_absent": "the source stream is not recorded in this Episode",
    "ambiguous_kind": "a sensor_kind the role requires was recorded more than once for the same frame key",
    "ambiguous_candidates": "more than one record claimed this role's key, so no single record can be reported",
}

# Stated precedence so a diagnosis never depends on accidental iteration order.
STATUS_PRECEDENCE = ["stream_absent", "identity_mismatch", "ambiguous_kind", "ambiguous_candidates",
                     "partial", "missing", "unresolved_reference", "matched"]

SELECTION_RULES = {
    "joins": "exact equality of the recorded join key named on each role; never a filename, line order or browser arrival order",
    "when_nothing_matches": "the role is reported as missing, unresolved_reference or stream_absent, with the key that was looked for",
    "when_several_match": "ambiguous_kind or ambiguous_candidates with every candidate line index listed; the first line in the file is not chosen",
    "completeness": "judged by the required sensor_kind set and per-kind cardinality, never by a record count alone",
    "status_precedence": STATUS_PRECEDENCE,
    "state_hold": "not applied: a frame never inherits another frame's state",
    "interpolation": "none",
    "nearest_in_time": "not used; numeric closeness is not treated as identity or as simultaneity",
}

# Each quantity is a named subtraction of two recorded numbers on a named record and field.
TIMING_QUANTITIES: tuple[dict[str, str], ...] = (
    {"key": "state_event_write_minus_frame_capture", "record": "events state feedback envelope",
     "field": "backend_monotonic_s", "relative_to": "persisted frame capture_backend_monotonic_s", "unit": "s",
     "clock": "named backend_monotonic by the record",
     "meaning": "when the recorder wrote the state event; it is not the instant the state was sampled"},
    {"key": "state_payload_feedback_time_minus_frame_capture", "record": "events state feedback payload",
     "field": "feedback_time_monotonic", "relative_to": "persisted frame capture_backend_monotonic_s", "unit": "s",
     "clock": "named backend_monotonic by feedback_clock",
     "meaning": "the as-of time the state payload carries for its own sample"},
    {"key": "state_payload_feedback_time_minus_state_event_write", "record": "events state feedback payload and envelope",
     "field": "feedback_time_monotonic minus backend_monotonic_s", "relative_to": "the same event record", "unit": "s",
     "clock": "named backend_monotonic by the record",
     "meaning": "how long before the event was written the payload says its sample was taken"},
    {"key": "recorder_declared_feedback_time_minus_frame_capture", "record": "events rgbd_capture_timing payload",
     "field": "feedback_time_s", "relative_to": "persisted frame capture_backend_monotonic_s", "unit": "s",
     "clock": "named by payload.feedback_clock",
     "meaning": "the recorder's own declared feedback time for this frame, a third stamp beside the two above"},
    {"key": "timing_payload_capture_minus_anchor_capture", "record": "events rgbd_capture_timing payload",
     "field": "capture_backend_monotonic_s", "relative_to": "persisted frame capture_backend_monotonic_s", "unit": "s",
     "clock": "named backend_monotonic by the record",
     "meaning": "cross-check that the timing event and the persisted frame name the same capture stamp"},
    {"key": "observation_measurement_minus_frame_capture", "record": "observations index row",
     "field": "measurement_time_s", "relative_to": "persisted frame capture_backend_monotonic_s", "unit": "s",
     "clock": "row clock_id", "meaning": "the sensor's own measurement stamp for this frame's stream"},
    {"key": "observation_arrival_minus_frame_capture", "record": "observations index row",
     "field": "arrival_time_s", "relative_to": "persisted frame capture_backend_monotonic_s", "unit": "s",
     "clock": "row clock_id", "meaning": "when the bridge says the observation arrived"},
    {"key": "persist_minus_capture", "record": "persisted frame", "field": "persist_backend_monotonic_s",
     "relative_to": "its own capture_backend_monotonic_s", "unit": "s", "clock": "named backend_monotonic by the record",
     "meaning": "the recorder's own capture-to-disk latency for this frame"},
)

# Two separate simulator-time quantities: the payload's own stamp and the event envelope's stamp.
# A missing payload value is never filled from the envelope, because that would present an
# envelope field under a payload label.
SIM_TIME_QUANTITIES: tuple[dict[str, str], ...] = (
    {"key": "state_sim_time_minus_frame_capture_sim_time", "record": "events state feedback payload",
     "field": "sim_time_s", "relative_to": "persisted frame capture_sim_time_s", "unit": "s", "clock": "sim",
     "missing_behaviour": "not emitted when the payload has no numeric sim_time_s",
     "meaning": "simulator-time separation from the state sample the payload itself carries, a different clock "
                "from every *_backend_monotonic_* quantity above"},
    {"key": "state_event_envelope_sim_time_minus_frame_capture_sim_time",
     "record": "events state feedback envelope", "field": "sim_time_s",
     "relative_to": "persisted frame capture_sim_time_s", "unit": "s", "clock": "sim",
     "missing_behaviour": "not emitted when the envelope has no numeric sim_time_s",
     "meaning": "simulator time recorded on the event envelope; it is not the payload's sample stamp"},
)

# The recorder writes its own per-frame latency numbers; they are copied, never re-derived here.
RECORDER_DECLARED_LATENCY_FIELDS = ("observation_age_ms", "arrival_to_persist_ms", "capture_to_persist_ms",
                                    "capture_to_copy_ms", "capture_to_render_complete_ms", "render_ms",
                                    "render_start_to_render_complete_ms", "encode_ms", "publish_ms",
                                    "capture_to_publish_complete_ms")

FRAME_LINK_VERSION_MIGRATION = {
    "from_schema": "unirobot-mobilecar-frame-link-1",
    "to_schema": FRAME_LINK_SCHEMA,
    "changed": [
        "paging.has_more is decided by finding the next qualifying anchor line rather than by comparing a "
        "prefiltered record count with a raw file line index",
        "paging reports which lines were actually read, and blank, oversize, unparseable and non-object lines "
        "separately from records examined",
        "role completeness is judged by the required sensor_kind set and per-kind cardinality; repeated candidates "
        "are ambiguous_kind or ambiguous_candidates instead of a silent first-wins match",
        "times.quantities names each recorded difference by record, field, unit and meaning, and "
        "times.recorder_declared copies the recorder's own latency fields",
        "time.clock_sameness separates the fields that name a shared clock base from what the reader can verify, and "
        "states how far the record's writing version can be bound",
    ],
    "removed_fields": {"times.age_of_state_relative_to_frame":
                       "it merged the state event's write stamp with the state sample stamps; read "
                       "times.quantities keys state_event_write_minus_frame_capture, "
                       "state_payload_feedback_time_minus_frame_capture and "
                       "recorder_declared_feedback_time_minus_frame_capture instead"},
    "corrections": [
        "state_sim_time_minus_frame_capture_sim_time now names only the state feedback PAYLOAD stamp and is absent "
        "when the payload carries no numeric sim_time_s; earlier builds of this version silently filled it from the "
        "event envelope while still labelling the payload as the source",
        "the envelope's own simulator time is a separate quantity, "
        "state_event_envelope_sim_time_minus_frame_capture_sim_time",
        "no quantity is ever filled from another record: absence is reported as absence",
        "time_quality.coverage.covers_whole_episode now requires both that the scan reached end of file and that "
        "every line of the anchor file was decided; an earlier build of this version reported it from EOF alone, "
        "so a file holding an unparsable or oversized line could still earn whole-episode scheduling on the "
        "strength of the anchors that happened to be readable",
        "time_quality.coverage.scope_note no longer calls a windowed page a reduced census: the page filter narrows "
        "the frames returned, while the census scans this Episode's anchor file on its own terms",
    ],
    "additions": [
        "time_quality.coverage.line_accounting separates benign lines from undecidable ones and names the positions "
        "of the undecided ones, so a coverage statement can be checked against the file it describes",
        "each time base is now reported on three separate questions: reached_end_of_file, "
        "every_line_of_the_anchor_file_is_decided, readable_anchor_timing_satisfies_schedule",
        "action_basis (opt-in) is the measured event vocabulary of one Episode, the join keys each type really "
        "carries, and per-frame association by recorded key — it adds no new endpoint and no server-side session",
    ],
    "compatibility_note": "consumers must read schema_version: frame-link-1 and frame-link-2 pages are not the same contract",
}

NOT_PROVEN = [
    "that two records naming the same clock base were stamped by one writer at one instant: naming is not verification",
    "which native build wrote these records: the run manifest pins contract_version and a software name/version only",
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


def _stream_lines(path, tokens: tuple[str, ...], stats: dict[str, int] | None = None,
                  undecidable: list[dict[str, Any]] | None = None) -> Iterator[tuple[int, dict[str, Any]]]:
    """Yield only the records that can carry one of the wanted keys, keeping the native line index.

    The substring test filters raw text and never changes provenance: ``line_index`` stays the
    real line number in the file, so every returned linkage can be pointed back to its position.
    Lines dropped on the way are counted rather than silently lost, and a caller that needs to
    know whether a dropped line could have carried an anchor gets its position in ``undecidable``.
    """
    needles = tuple(f'"{token}"' for token in tokens)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for index, raw in enumerate(handle):
            if stats is not None:
                stats["lines_read"] += 1
            if not raw.strip():
                if stats is not None:
                    stats["blank_lines_skipped"] += 1
                continue
            if len(raw) > MAX_RECORD_BYTES:
                if stats is not None:
                    stats["oversize_lines_skipped"] += 1
                if undecidable is not None:
                    undecidable.append({"line_index": index, "reason": "oversize", "bytes": len(raw)})
                continue
            if needles and not any(item in raw for item in needles):
                if stats is not None:
                    stats["prefiltered_lines_skipped"] += 1
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                if stats is not None:
                    stats["unparseable_lines_skipped"] += 1
                if undecidable is not None:
                    undecidable.append({"line_index": index, "reason": "unparseable", "bytes": len(raw)})
                continue
            if isinstance(record, dict):
                yield index, record
            elif stats is not None:
                stats["non_object_lines_skipped"] += 1
                if undecidable is not None:
                    undecidable.append({"line_index": index, "reason": "non_object",
                                        "json_type": type(record).__name__})


def _new_line_stats() -> dict[str, int]:
    return {"lines_read": 0, "blank_lines_skipped": 0, "oversize_lines_skipped": 0, "unparseable_lines_skipped": 0,
            "non_object_lines_skipped": 0, "prefiltered_lines_skipped": 0}


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# The records name a unit only inside the field name, so the reader reports what the suffix says and
# says unknown when the name carries no unit at all.
_UNIT_BY_SUFFIX = (("_rad_s", "rad_per_second"), ("_rad", "radian"), ("_nm", "newton_metre"), ("_ms", "millisecond"),
                   ("_m", "metre"), ("_s", "second"))
TIME_UNITS = {"second", "millisecond", "iso8601_utc"}


def _unit_of(field: str) -> str:
    if field.endswith("wall_utc"):
        return "iso8601_utc"
    for suffix, unit in _UNIT_BY_SUFFIX:
        if field.endswith(suffix):
            return unit
    return "unknown_from_field_name"


def _is_time_named(field: str) -> bool:
    # A velocity named *_rad_s ends in "s" without being an instant, so the derived unit decides.
    return _unit_of(field) in TIME_UNITS or "time" in field


def _delta(capture: Any, other: Any, meta: dict[str, str], *, line_index: int | None = None) -> dict[str, Any] | None:
    """Subtraction of two recorded numbers with the sign kept; never a synchronisation claim."""
    if not _number(capture) or not _number(other):
        return None
    value = other - capture
    item = {"key": meta["key"], "source_record": meta["record"], "field": meta["field"],
            "relative_to": meta["relative_to"], "unit": meta["unit"], "clock": meta["clock"],
            "meaning": meta["meaning"], "capture_value": capture, "other_value": other, "value": value,
            "abs_ms": abs(value) * 1000.0 if meta["unit"] == "s" else None,
            "direction": "earlier" if value < 0 else "later" if value > 0 else "equal"}
    if line_index is not None:
        item["line_index"] = line_index
    return item


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
               sample_id: str | None = None, include_time_quality: bool = False,
               include_action_basis: bool = False) -> dict[str, Any]:
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

        limit = max(1, min(limit, MAX_PAGE))
        anchors, counters, lines, next_anchor = self._anchors(
            location, anchor_path, stream=stream, limit=limit, offset=offset, sample_id=sample_id,
            # The selectable base is the recorded field name itself; the mapping only describes it.
            selected_field=time_base, time_from=time_from, time_to=time_to)
        links = self._collect(location, anchors)
        frames = [self._frame(location, line_index, record, links) for line_index, record in anchors]
        ambiguous_primary = sum(1 for item in frames
                                if any(entry["status"] in ("ambiguous_kind", "ambiguous_candidates")
                                       for entry in item["roles"] if entry["role"] in PRIMARY_ROLES))
        page_ids = [record["sample_id"] for _, record in anchors]
        repeated_on_page = sum(1 for key in set(page_ids) if page_ids.count(key) > 1)
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
                       "has_more": next_anchor is not None,
                       "next_offset": anchors[-1][0] + 1 if next_anchor is not None and anchors else None,
                       "next_qualifying_anchor_line_index": next_anchor,
                       "offset_semantics": "next_offset is the raw line index after the last returned anchor in the "
                                           "anchor file; the following request re-tests every line at or above it "
                                           "against the same eligibility rules",
                       "skipped_before_offset": counters["skipped_before"],
                       "excluded_anchor_identity_mismatch": counters["excluded_identity_mismatch"],
                       "excluded_stream_mismatch": counters["excluded_stream_mismatch"],
                       "excluded_without_sample_id": counters["excluded_without_sample_id"],
                       "excluded_by_sample_id_filter": counters["excluded_by_sample_id_filter"],
                       "excluded_outside_time_window": counters["excluded_outside_time_window"],
                       "records_missing_selected_time_base": counters["records_missing_selected_time_base"],
                       "anchor_records_examined": counters["examined"],
                       "post_page_records_examined": counters["post_page_records_examined"],
                       "anchor_lines": lines,
                       "scan": {"whole_file_scanned": next_anchor is None,
                                "stopped_after_full_page_at_line_index": next_anchor,
                                "note": "a full page stops at the first further qualifying anchor, so the counts "
                                        "above describe the lines actually read and are not a whole-file census"}},
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
                     "same_clock_verified": False,
                     "clock_sameness": self._clock_sameness(),
                     "deltas_are_recorded_arithmetic": True,
                     "browser_arrival_order_is_not_used": True},
            "linkage": {"roles": {role: {"source_stream": info[0], "join_key": info[1], "meaning": info[2],
                                         "requirement": ROLE_REQUIREMENTS[role]}
                                  for role, info in ROLE_SEMANTICS.items()},
                        "status_meaning": STATUS_MEANING,
                        "status_precedence": STATUS_PRECEDENCE,
                        "selection_rules": SELECTION_RULES,
                        "primary_roles": list(PRIMARY_ROLES),
                        "role_coverage_on_this_page": self._coverage(frames)},
            "version_migration": FRAME_LINK_VERSION_MIGRATION,
            "summary": {"frames_returned": len(frames),
                        "frames_with_all_primary_roles_matched": sum(1 for item in frames if item["linkage_status"] == "matched"),
                        "frames_with_some_primary_roles_missing": sum(1 for item in frames if item["linkage_status"] == "partial"),
                        "frames_with_no_primary_role_matched": sum(1 for item in frames if item["linkage_status"] == "missing"),
                        "frames_with_ambiguous_primary_role": ambiguous_primary,
                        "frames_without_a_linked_state": sum(1 for item in frames
                                                             if item["state"]["status"] != "matched"),
                        "frames_with_unresolved_feedback_reference": sum(1 for item in frames
                                                                         if item["declared_reference_status"] == "unresolved_reference"),
                        "anchors_with_repeated_sample_id_on_this_page": repeated_on_page},
            # The census re-reads the anchor file, so it stays opt-in and the default page remains light.
            **({"time_quality": self._time_quality(
                    location, anchor_path, stream=stream,
                    page_context={"time_base": time_base, "time_from": time_from, "time_to": time_to,
                                  "sample_id": sample_id, "offset": offset, "limit": limit,
                                  "returned": len(frames),
                                  "note": "the census covers the anchors this Episode exposes in file order, not only "
                                          "the rows of this page"})} if include_time_quality else {}),
            # The action basis reads the events stream in full, so it is opt-in for the same reason.
            **({"action_basis": self._action_basis(location, anchors)} if include_action_basis else {}),
            "frames": frames,
            "not_proven": NOT_PROVEN,
            "three_d_replay": {"this_slice_does_not_enable_3d_replay": True,
                               "live_geometry_or_actual_may_be_applied": False,
                               "transforms_are_full_per_body_pose_sequences": False,
                               "robot_pose_readiness_slice": "GET /api/v1/episodes/{episode_id}/robot-state"},
            "capability_limits": ["no replay execution", "no cross-episode cursor", "no native validate proxy",
                                  "no control, RESET, recording or physics stepping"],
        }

    # ---- anchors ------------------------------------------------------------------

    def _anchor_rejection(self, location: EpisodeLocation, record: dict[str, Any], *, stream: str,
                          sample_id: str | None, selected_field: str | None, time_from: float | None,
                          time_to: float | None) -> str | None:
        """The first failed eligibility rule names the counter this record consumed."""
        # The frame record names its own run and Episode; a page never serves a frame that
        # declares someone else's identity, even when the directory itself looked legitimate.
        if record.get("run_id") != location.run_id or record.get("episode_id") != location.episode_id:
            return "excluded_identity_mismatch"
        if record.get("stream_id") != stream:
            return "excluded_stream_mismatch"
        if not isinstance(record.get("sample_id"), str):
            return "excluded_without_sample_id"
        if sample_id and record.get("sample_id") != sample_id:
            return "excluded_by_sample_id_filter"
        if selected_field:
            stamp = record.get(selected_field)
            if not _number(stamp):
                return "records_missing_selected_time_base"
            if (time_from is not None and stamp < time_from) or (time_to is not None and stamp > time_to):
                return "excluded_outside_time_window"
        return None

    def _anchors(self, location: EpisodeLocation, path, *, stream: str, limit: int, offset: int,
                 sample_id: str | None, selected_field: str | None, time_from: float | None,
                 time_to: float | None) -> tuple[list[tuple[int, dict[str, Any]]], dict[str, int],
                                                  dict[str, int], int | None]:
        anchors: list[tuple[int, dict[str, Any]]] = []
        counters = {"examined": 0, "skipped_before": 0, "excluded_identity_mismatch": 0,
                    "excluded_stream_mismatch": 0, "excluded_without_sample_id": 0,
                    "excluded_by_sample_id_filter": 0, "excluded_outside_time_window": 0,
                    "records_missing_selected_time_base": 0, "post_page_records_examined": 0}
        lines = _new_line_stats()
        next_anchor: int | None = None
        for line_index, record in _stream_lines(path, (stream,), lines):
            counters["examined"] += 1
            rejection = self._anchor_rejection(location, record, stream=stream, sample_id=sample_id,
                                               selected_field=selected_field, time_from=time_from, time_to=time_to)
            if rejection:
                counters[rejection] += 1
                continue
            if line_index < offset:
                counters["skipped_before"] += 1
                continue
            if len(anchors) >= limit:
                # One further qualifying anchor is enough to say a next page exists. Scanning on
                # would only inflate the counters with lines this page never served.
                counters["post_page_records_examined"] += 1
                next_anchor = line_index
                break
            anchors.append((line_index, record))
        return anchors, counters, lines, next_anchor

    # ---- bounded time-quality census ---------------------------------------------

    def _time_quality(self, location: EpisodeLocation, path, *, stream: str,
                      page_context: dict[str, Any]) -> dict[str, Any]:
        """Re-read the anchor file once, on request, and say what a schedule could be built from.

        The census is bounded and scoped: a truncated scan reports itself as truncated and supports
        no whole-episode claim. Nothing here sorts, fills or substitutes a recorded value.
        """
        samples: list[tuple[int, dict[str, Any]]] = []
        rejected = {"excluded_identity_mismatch": 0, "excluded_stream_mismatch": 0,
                    "excluded_without_sample_id": 0}
        lines = _new_line_stats()
        undecidable: list[dict[str, Any]] = []
        truncated_at: int | None = None
        for line_index, record in _stream_lines(path, (stream,), lines, undecidable):
            if record.get("run_id") != location.run_id or record.get("episode_id") != location.episode_id:
                rejected["excluded_identity_mismatch"] += 1
                continue
            if record.get("stream_id") != stream:
                rejected["excluded_stream_mismatch"] += 1
                continue
            if not isinstance(record.get("sample_id"), str):
                rejected["excluded_without_sample_id"] += 1
                continue
            samples.append((line_index, record))
            if len(samples) >= TIME_QUALITY_ANCHOR_LIMIT:
                truncated_at = line_index
                break

        # Reached EOF and "every line is decided" are different facts: a dropped oversize or
        # unparseable line is reached-past but not known, and it could have carried an anchor.
        reached_eof = truncated_at is None
        undecidable_total = len(undecidable)
        coverage_blocking = ([] if reached_eof else ["scan_stopped_at_anchor_limit_before_eof"]) + (
            [f"{undecidable_total}_lines_are_undecidable_and_could_hide_anchors"] if undecidable_total else [])

        occurrences: dict[str, list[int]] = {}
        for line_index, record in samples:
            occurrences.setdefault(record["sample_id"], []).append(line_index)
        duplicates = sorted(({"sample_id": key, "occurrences": len(indexes), "line_indexes": indexes,
                              "record_positions": [f"observations/persist.jsonl#{item}" for item in indexes]}
                             for key, indexes in occurrences.items() if len(indexes) > 1),
                            key=lambda item: (-item["occurrences"], item["line_indexes"][0]))
        sequences = {field: _base_statistics(samples, field) for field in sorted(FRAME_TIME_BASES)}
        every_line_is_decided = reached_eof and undecidable_total == 0
        covers_whole_episode = every_line_is_decided

        sequences_out: dict[str, Any] = {}
        eligible_bases: dict[str, Any] = {}
        for field, stats in sequences.items():
            timing_blocking = []
            if not samples:
                timing_blocking.append("no_readable_anchors_in_this_scan")
            if stats["missing_count"]:
                timing_blocking.append(f"time_base_absent_on_{stats['missing_count']}_anchors")
            if stats["non_numeric_count"]:
                timing_blocking.append(f"time_base_non_numeric_on_{stats['non_numeric_count']}_anchors")
            if stats["backwards_gaps"]["count"]:
                timing_blocking.append(f"clock_steps_backwards_{stats['backwards_gaps']['count']}_times_in_file_order")
            timing_ok = bool(samples) and not timing_blocking
            median_gap = stats["recorded_gaps"]["median_s"]
            sequences_out[field] = {**stats, "description": FRAME_TIME_BASES[field]}
            eligible_bases[field] = {
                "reached_end_of_file": reached_eof,
                "every_line_of_the_anchor_file_is_decided": every_line_is_decided,
                "readable_anchor_timing_satisfies_schedule": timing_ok,
                "eligible_for_whole_episode": timing_ok and not coverage_blocking,
                "eligible_within_this_scan": timing_ok,
                "blocking_reasons": coverage_blocking + timing_blocking,
                "blocking_reason_scope": {"coverage": coverage_blocking, "timing": timing_blocking},
                "zero_interval_ties_present": stats["equal_adjacent_gaps"]["count"] > 0,
                "implied_rate_hz_from_median_recorded_gap": (1.0 / median_gap) if median_gap else None,
                "implied_rate_note": "derived from the recorded values of this scan; it is not a rate the "
                                     "recorder declared and it is not a playback guarantee"}
        profile_ids = sorted({record.get("profile_id") for _, record in samples
                              if isinstance(record.get("profile_id"), str)})
        persist_values = [record.get("persist_sequence") for _, record in samples]
        persist_backwards = sum(1 for index in range(1, len(persist_values))
                                if _number(persist_values[index]) and _number(persist_values[index - 1])
                                and persist_values[index] < persist_values[index - 1])

        return {
            "requested": True,
            "coverage": {"run_id": location.run_id, "episode_id": location.episode_id, "stream_id": stream,
                         "anchor_relative_path": _relative("observations-persist"),
                         "anchors_in_this_scan": len(samples), "unique_sample_ids": len(occurrences),
                         "rejected_anchors": rejected, "anchor_lines": lines,
                         "first_anchor_line_index": samples[0][0] if samples else None,
                         "last_anchor_line_index": samples[-1][0] if samples else None,
                         "reached_end_of_file": reached_eof,
                         "whole_anchor_file_scanned": reached_eof, "anchor_limit": TIME_QUALITY_ANCHOR_LIMIT,
                         "stopped_at_line_index": truncated_at,
                         "line_accounting": {
                             "benign_lines": {key: lines[key] for key in LINE_ACCOUNTING
                                              if LINE_ACCOUNTING[key]["classification"] == "benign"},
                             "undecidable_lines": {key: lines[key] for key in LINE_ACCOUNTING
                                                   if LINE_ACCOUNTING[key]["classification"] == "undecidable"},
                             "undecidable_total": undecidable_total,
                             "undecidable_positions": [
                                 {**item, "record_position": f"{_relative('observations-persist')}#{item['line_index']}"}
                                 for item in undecidable[:TIME_QUALITY_UNDECIDABLE_LIST_LIMIT]],
                             "undecidable_positions_truncated": undecidable_total > TIME_QUALITY_UNDECIDABLE_LIST_LIMIT,
                             "parsed_records_rejected_by_rule": sum(rejected.values()),
                             "every_line_of_the_anchor_file_is_decided": every_line_is_decided,
                             "rules": LINE_ACCOUNTING,
                             "note": "a blank line and a line that cannot carry the requested stream token are "
                                     "decided, not corruption; a line the reader could not parse is undecided and "
                                     "could have carried an anchor, so it blocks a whole-episode claim"},
                         "covers_whole_episode": covers_whole_episode,
                         "not_a_whole_archive_sweep": True,
                         "scope_note": "the census scans this Episode's anchor file itself; a time window or page "
                                       "filter narrows the frame page, not the census, so whole-episode support "
                                       "depends only on this scan reaching EOF with every line decided — a scan "
                                       "that stopped at the anchor limit or met undecidable content supports no "
                                       "whole-episode or whole-archive claim",
                         "page_filter_context": page_context},
            "time_bases": sequences_out,
            "identity": {"duplicate_sample_id_groups": len(duplicates),
                         "duplicates": duplicates[:TIME_QUALITY_DUPLICATE_LIST_LIMIT],
                         "duplicates_truncated": len(duplicates) > TIME_QUALITY_DUPLICATE_LIST_LIMIT,
                         "every_anchor_position_is_reported": True,
                         "effect_on_this_route": "a duplicated id makes `sample_id=` address more than one anchor, "
                                                 "so the page cannot name one position for it",
                         "effect_on_robot_state": "GET /api/v1/episodes/{episode_id}/robot-state?sample_id= refuses "
                                                  "with frame_sample_id_ambiguous instead of taking the first match"},
            "recorder_counters": {"persist_sequence_backwards_steps_in_file_order": persist_backwards,
                                  "persist_sequence_is_the_recorders_own_counter": True,
                                  "line_index_is_not_a_clock": True},
            "profile": {"profile_ids_seen": profile_ids, "anchor_fields_declaring_a_numeric_rate": [],
                        "note": "the anchors carry a profile identifier, not a declared numeric rate; no rate is "
                                "inferred from the profile name"},
            "playback_eligibility": {
                "modes": PLAYBACK_MODES,
                "append_order_display": {
                    "mode": "A", "eligible": bool(samples),
                    "basis": "the anchor file is read in the recorder's own append order and a full page stops at "
                             "the first further qualifying anchor",
                    "does_not_require": ["a numeric capture time base", "clock sameness", "unique sample ids"],
                    "displayed_sequence_may_have_gaps": not every_line_is_decided,
                    "gap_note": "A stays available: undecidable lines are reported with their positions so the "
                                "reader can show what it could not decide, but they are not silently presented as "
                                "a complete frame sequence",
                    "anchor_position_never_reordered_by_time": True},
                "recorded_interval_schedule": {
                    "mode": "B", "eligible_by_base": eligible_bases,
                    "any_base_eligible_for_whole_episode": any(item["eligible_for_whole_episode"]
                                                               for item in eligible_bases.values()),
                    "coverage_is_a_separate_question_from_timing": True,
                    "rules_when_unqualified": {
                        "missing_or_non_numeric_time": "the base is refused for scheduling; the frame stays visible "
                                                       "in append order and no value is filled from another record",
                        "equal_adjacent_values": "ties are shown as ties; they are not interpolated and a rate is "
                                                 "not computed by dividing by zero",
                        "backwards_step": "the base is refused for scheduling over that range, because one continuous "
                                          "clock across the step is not established by the record",
                        "clock_unknown": "a base that only names a clock is not evidence of a shared clock source",
                        "undecidable_or_truncated_scan": "no whole-episode schedule is claimed: undecided content "
                                                         "could hide an anchor, so the clean timing of the readable "
                                                         "anchors cannot prove the rest of the Episode"},
                    "never_assumed": {"default_rate_hz_applied": False, "browser_arrival_time_used": False,
                                      "clock_stitched_across_reset": False,
                                      "why": "no record establishes a nominal rate, a host clock relationship across "
                                             "segments, or a RESET boundary on these anchors"}},
                "cross_stream_synchronized": {
                    "mode": "C", "eligible": False,
                    "reason": "the records name shared clock bases but nothing lets this reader verify one shared "
                              "clock source or one sampled instant across streams",
                    "not_derivable_from": ["A", "B"],
                    "same_page_evidence": {"same_clock_verified": False, "synchronized_across_streams": False}}},
            "not_proven": ["a declared sampling rate", "clock sameness across streams", "a sampled-instant match",
                           "coverage beyond the anchors scanned here", "RESET or segment boundaries on anchors",
                           "that undecided anchor-file lines carry no frame record, when such lines exist"],
        }

    # ---- action and event basis ---------------------------------------------------

    def _action_basis(self, location: EpisodeLocation, anchors: list[tuple[int, dict[str, Any]]]) -> dict[str, Any]:
        """One bounded pass over the events stream that says what a replay can be built from.

        The pass is unfiltered because a vocabulary answer must not miss a type that happens to
        carry none of this page's keys. Nothing here invents an action, promotes an approval into
        an execution result, or attaches a record to a frame it does not name.
        """
        path = location.path_of("events")
        relative = _relative("events")
        ticks = {record.get("capture_control_tick_id") for _, record in anchors
                 if isinstance(record.get("capture_control_tick_id"), str)}
        vocabulary: dict[str, Any] = {}
        by_tick: dict[str, dict[str, list[str]]] = {}
        tick_candidates_truncated = False
        commands: dict[str, Any] = {}
        scanned = 0
        untyped = 0
        truncated_at: int | None = None

        if path.is_file():
            for line_index, record in _stream_lines(path, ()):
                scanned += 1
                event_type = record.get("event_type")
                if not isinstance(event_type, str):
                    untyped += 1
                    continue
                entry = vocabulary.setdefault(
                    event_type, {"count": 0, "first_line_index": line_index, "last_line_index": line_index,
                                 "positions": [], "join_keys": {}, "time_fields": {}, "operator_fields": set()})
                entry["count"] += 1
                entry["last_line_index"] = line_index
                if len(entry["positions"]) < ACTION_BASIS_POSITION_LIMIT:
                    entry["positions"].append(f"{relative}#{line_index}")
                payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
                for key in ACTION_JOIN_KEYS:
                    if key in record or key in payload:
                        slot = entry["join_keys"].setdefault(key, {"envelope": {"present": 0, "null": 0},
                                                                   "payload": {"present": 0, "null": 0}})
                        for side, holder in (("envelope", record), ("payload", payload)):
                            if key in holder:
                                slot[side]["present" if holder[key] is not None else "null"] += 1
                for field, value in record.items():
                    if _is_time_named(field):
                        stamp = entry["time_fields"].setdefault(
                            field, {"unit": _unit_of(field), "numeric": 0, "null": 0, "other": 0})
                        stamp["numeric" if _number(value) else ("null" if value is None else "other")] += 1
                for field, value in payload.items():
                    if _is_time_named(field):
                        stamp = entry["time_fields"].setdefault(
                            f"payload.{field}", {"unit": _unit_of(field), "numeric": 0, "null": 0, "other": 0})
                        stamp["numeric" if _number(value) else ("null" if value is None else "other")] += 1
                entry["operator_fields"].update({f"payload.{field}" for field in OPERATOR_FIELDS if field in payload}
                                                | {field for field in OPERATOR_FIELDS if field in record})
                # The recorder names its operator one level deeper, inside request and command objects.
                for container, values in payload.items():
                    if isinstance(values, dict):
                        entry["operator_fields"].update(f"payload.{container}.{field}" for field in OPERATOR_FIELDS
                                                       if field in values)
                tick = record.get("control_tick_id")
                if (isinstance(tick, str) and tick in ticks
                        and event_type in (TARGET_EVENT_TYPE, DISPATCH_EVENT_TYPE, *STATE_EVENT_TYPES)):
                    found = by_tick.setdefault(tick, {}).setdefault(event_type, [])
                    if len(found) < ACTION_BASIS_CANDIDATE_LIMIT:
                        found.append(f"{relative}#{line_index}")
                    else:
                        tick_candidates_truncated = True
                if event_type in COMMAND_CHAIN_EVENT_TYPES:
                    command_id = record.get("command_id")
                    handle = commands.setdefault(
                        command_id if isinstance(command_id, str) else "<command_id_absent_or_null>",
                        {"command_id": command_id, "stages": {}, "positions": {}, "control_tick_id_present": 0})
                    stage = handle["stages"].setdefault(event_type, 0)
                    handle["stages"][event_type] = stage + 1
                    if len(handle["positions"].setdefault(event_type, [])) < ACTION_BASIS_POSITION_LIMIT:
                        handle["positions"][event_type].append(f"{relative}#{line_index}")
                    if isinstance(record.get("control_tick_id"), str):
                        handle["control_tick_id_present"] += 1
                if scanned >= ACTION_BASIS_EVENT_LIMIT:
                    truncated_at = line_index
                    break

        categories: dict[str, Any] = {}
        for name, (types, meaning) in ACTION_CATEGORIES.items():
            present = {event_type: vocabulary[event_type]["count"] for event_type in types if event_type in vocabulary}
            categories[name] = {
                "event_types_recorded": sorted(present),
                "counts": present,
                "status": "observed" if present else "not_recorded_in_this_scan",
                "meaning": meaning,
                "absent_event_types": sorted(set(types) - set(present))}
        for name, entry in categories.items():
            if not entry["event_types_recorded"]:
                entry["status_note"] = ("the scan found no record of this category; that is a fact about this "
                                        "Episode's events stream, not a claim that the recorder can never write one")

        by_frame = []
        distribution: dict[str, dict[str, int]] = {event_type: {} for event_type in
                                                  (TARGET_EVENT_TYPE, DISPATCH_EVENT_TYPE, *STATE_EVENT_TYPES)}
        for _, record in anchors:
            tick = record.get("capture_control_tick_id")
            roles = {}
            for event_type in (TARGET_EVENT_TYPE, DISPATCH_EVENT_TYPE, *STATE_EVENT_TYPES):
                if not isinstance(tick, str):
                    roles[event_type] = {"status": "missing", "reason": "the frame anchor carries no capture_control_tick_id"}
                    continue
                found = by_tick.get(tick, {}).get(event_type, [])
                bucket = distribution[event_type]
                bucket[str(len(found))] = bucket.get(str(len(found)), 0) + 1
                roles[event_type] = ({"status": "missing", "reason": "no record of this type names this capture tick",
                                      "looked_for": {"control_tick_id": tick}} if not found else
                                     {"status": "matched", "candidate_count": len(found), "record_positions": found}
                                    if len(found) == 1 else
                                     {"status": "ambiguous_candidates", "candidate_count": len(found),
                                      "record_positions": found,
                                      "note": "more than one record names this tick, so no single one is chosen"})
            by_frame.append({"sample_id": record.get("sample_id"), "capture_control_tick_id": tick, "by_event_type": roles})

        return {
            "requested": True,
            "scope": {"stream_id": "events", "relative_path": relative, "records_scanned": scanned,
                      "reached_end_of_file": truncated_at is None, "stopped_at_line_index": truncated_at,
                      "record_limit": ACTION_BASIS_EVENT_LIMIT, "events_stream_present": path.is_file(),
                      "records_without_an_event_type": untyped,
                      "scope_note": "the vocabulary covers every record the scan read in this Episode's events "
                                    "stream; a scan that stopped at the record limit describes only what it read",
                      "page_ticks_considered": len(ticks), "anchors_on_this_page": len(anchors)},
            "categories": categories,
            "vocabulary": {name: {"count": entry["count"], "first_line_index": entry["first_line_index"],
                                  "last_line_index": entry["last_line_index"], "record_positions": entry["positions"],
                                  "join_keys": entry["join_keys"], "time_fields": entry["time_fields"]}
                           for name, entry in sorted(vocabulary.items(), key=lambda item: -item[1]["count"])},
            "frame_association": {
                "key": "control_tick_id equals the frame anchor's own capture_control_tick_id",
                "by_event_type": {event_type: {"candidate_count_per_frame_on_this_page": bucket,
                                               "frames_with_this_verdict": sum(bucket.values())}
                                  for event_type, bucket in distribution.items()},
                "candidate_positions_per_frame": by_frame,
                "candidate_list_limit": ACTION_BASIS_CANDIDATE_LIMIT,
                "candidate_lists_truncated": tick_candidates_truncated,
                "rules": ACTION_BASIS_RULES},
            "command_chain": {
                "grouped_by": "command_id",
                "commands": list(commands.values())[:ACTION_BASIS_COMMAND_LIMIT],
                "commands_truncated": len(commands) > ACTION_BASIS_COMMAND_LIMIT,
                "note": "a request, its approval and its dispatch are separate records joined by command_id; the "
                        "chain proves no execution result, and a rejected request never becomes an executed action"},
            "control_source": {
                "status": "recorded_only_inside_payload_fields",
                "fields_observed": {name: sorted(entry["operator_fields"]) for name, entry in sorted(vocabulary.items())
                                   if entry["operator_fields"]},
                "takeover_event_type_recorded": any(name in vocabulary for name in ("takeover", "control_source_change")),
                "lease_evidence": {name: vocabulary[name]["count"] for name in ("lease_heartbeat", "lease_expired")
                                   if name in vocabulary},
                "note": "the recorder names an operator inside some payloads and a lease beside its own session id; "
                        "it records no control-source switch or takeover event in this scan, and the reader never "
                        "defaults a source to Human"},
            "independent_tracks": sorted(name for name, entry in categories.items()
                                        if entry["status"] == "observed"
                                        and name not in ("actual_state_feedback", "recorded_target",
                                                          "command_dispatched", "capture_timing")),
            "independent_track_reason": "these categories share no key with a frame anchor in this scan, so they are "
                                        "read as their own track by event_seq or a named time base, never attached to "
                                        "the nearest frame or the previous record",
            "not_proven": ["that any command below was physically executed", "a control-source switch or takeover",
                           "that an absent category is impossible for the recorder", "any cross-stream simultaneity",
                           "that a scanned event and a frame share one clock instant"],
        }

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
              unresolved_when_absent: bool = False, with_media: bool = False,
              with_payload: bool = False) -> dict[str, Any]:
        stream_id, join_key, meaning = ROLE_SEMANTICS[role]
        requirement = ROLE_REQUIREMENTS[role]
        entries: list[dict[str, Any]] = []
        mismatched = 0
        for line_index, record in sources:
            entry = self._entry(location, stream_id, line_index, record, fields,
                                with_media=with_media, with_payload=with_payload)
            if entry["identity"]["run_id_matches"] and entry["identity"]["episode_id_matches"]:
                entries.append(entry)
            else:
                mismatched += 1

        required_kinds = requirement.get("required_kinds")
        line_indexes = [item["line_index"] for item in entries]
        detail: dict[str, Any] = {"role": role, "join_key": join_key, "key_value": key_value, "meaning": meaning,
                                  "requirement": requirement, "candidate_records": len(sources),
                                  "matched_records": len(entries), "identity_mismatched_records": mismatched,
                                  "candidate_line_indexes": [item[0] for item in sources],
                                  "sources": entries}
        if required_kinds:
            rows_by_kind: dict[str, list[int]] = {}
            for item in entries:
                kind = item["projection"].get("sensor_kind")
                if isinstance(kind, str):
                    rows_by_kind.setdefault(kind, []).append(item["line_index"])
                else:
                    rows_by_kind.setdefault("sensor_kind_absent", []).append(item["line_index"])
            duplicate_kinds = sorted(kind for kind, indexes in rows_by_kind.items() if len(indexes) > 1)
            missing_kinds = sorted(kind for kind in required_kinds if not rows_by_kind.get(kind))
            detail.update({"kind_inventory": rows_by_kind, "required_kinds": list(required_kinds),
                           "matched_kinds": sorted(kind for kind in required_kinds if rows_by_kind.get(kind)),
                           "missing_kinds": missing_kinds, "duplicate_kinds": duplicate_kinds,
                           "unexpected_kinds": sorted(kind for kind in rows_by_kind if kind not in required_kinds)})
        elif len(entries) > 1:
            detail["ambiguous_records"] = [
                {"line_index": item["line_index"], "record_position": item["record_position"],
                 "conflicts_with_first": _conflicts(item, entries[0])}
                for item in entries]

        if stream_absent:
            status = "stream_absent"
        elif mismatched:
            status = "identity_mismatch"
        elif required_kinds:
            if detail["duplicate_kinds"]:
                status = "ambiguous_kind"
            elif not entries:
                status = "missing"
            elif detail["missing_kinds"]:
                status = "partial" if detail["matched_kinds"] else "missing"
            else:
                status = "matched"
        elif not entries:
            status = "unresolved_reference" if (unresolved_when_absent and key_value is not None) else "missing"
        elif len(entries) > 1:
            status = "ambiguous_candidates"
        else:
            status = "matched"
        detail["status"] = status
        return detail

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
                       fields=FRAME_FIELDS, with_media=True),
            self._role(location, "camera_transform", sample_id, transform_rows,
                       stream_absent=links["transforms"].get("absent", False), fields=TRANSFORM_FIELDS),
            self._role(location, "capture_timing_event", sample_id, timing_rows, stream_absent=events_absent,
                       fields=EVENT_FIELDS, with_payload=True),
            self._role(location, "state_feedback_event", tick, state_rows, stream_absent=events_absent,
                       fields=EVENT_FIELDS, with_payload=True),
            self._role(location, "feedback_observation_row", feedback_id, feedback_rows, stream_absent=index_absent,
                       unresolved_when_absent=True,
                       fields=("stream_id", "sample_id", "sensor_kind", "frame_id", "clock_id",
                               "measurement_time_s", "arrival_time_s")),
        ]
        by_role = {item["role"]: item for item in roles}
        primary = [by_role[name] for name in PRIMARY_ROLES]
        matched_primary = sum(1 for item in primary if item["status"] == "matched")
        ambiguous_primary = [item["role"] for item in primary
                             if item["status"] in ("ambiguous_kind", "ambiguous_candidates")]
        linkage_status = ("matched" if matched_primary == len(primary)
                          else "missing" if matched_primary == 0 else "partial")
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
            "primary_roles_ambiguous": ambiguous_primary,
            "declared_reference_status": by_role["feedback_observation_row"]["status"],
            "media": self._media(location, record, by_role["image_observation"]),
            "state": self._state(record, by_role),
            "times": self._times(record, by_role, anchor_line_index=line_index),
            "roles": roles,
        }

    # ---- frame sections ---------------------------------------------------------

    def _media(self, location: EpisodeLocation, record: dict[str, Any],
               image_role: dict[str, Any]) -> dict[str, Any]:
        """Media the frame declares, its availability as observed, and what the rows declare.

        The anchor uri and the row uri are compared as recorded strings. When more than one row
        carries a kind, every candidate is listed and agreement means "some candidate declares
        this uri" — the first row is not silently picked. Digests stay declared here: they are
        recomputed only when the asset endpoint actually serves a file.
        """
        rows_by_kind: dict[str, list[dict[str, Any]]] = {}
        for entry in image_role["sources"]:
            kind = entry["projection"].get("sensor_kind")
            if isinstance(kind, str):
                rows_by_kind.setdefault(kind, []).append(entry)
        items: list[dict[str, Any]] = []
        for field, kind in (("rgb_uri", "rgb"), ("depth_uri", "depth"), ("valid_mask_uri", "depth")):
            uri = record.get(field)
            entry: dict[str, Any] = {"field": field, "uri": uri if isinstance(uri, str) else None}
            if not isinstance(uri, str):
                entry.update({"availability": "not_recorded_on_this_frame", "observation_row_line_indexes": [],
                              "observation_row_candidates": 0, "agrees_with_observation_row": None,
                              "declared_sha256_by_row": None})
                items.append(entry)
                continue
            rows = rows_by_kind.get(kind, [])
            row_uris = [item["uri"] for row in rows for item in row.get("declared_media") or []]
            entry.update({"observation_row_line_indexes": [row["line_index"] for row in rows],
                          "observation_row_candidates": len(rows),
                          "agrees_with_observation_row": (uri in row_uris) if row_uris else None,
                          "declared_sha256_by_row": next((item["declared_sha256"] for row in rows
                                                          for item in row.get("declared_media") or []
                                                          if item["uri"] == uri), None),
                          "declared_bytes_by_row": next((item["declared_bytes"] for row in rows
                                                         for item in row.get("declared_media") or []
                                                         if item["uri"] == uri), None)})
            if len(rows) > 1:
                differing = {json.dumps(row.get("declared_media"), sort_keys=True) for row in rows}
                entry["observation_rows_conflict"] = len(differing) > 1
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
                "duplicate_row_rule": "every candidate row for the kind is listed; none is silently chosen",
                "items": items}

    def _state(self, record: dict[str, Any], by_role: dict[str, dict[str, Any]]) -> dict[str, Any]:
        role = by_role["state_feedback_event"]
        candidates = role["sources"]
        single = candidates[0] if len(candidates) == 1 else None
        timing_role = by_role["capture_timing_event"]
        timing_single = timing_role["sources"][0] if len(timing_role["sources"]) == 1 else None
        payload = (timing_single or {}).get("payload") or {} if timing_single else {}
        return {"status": role["status"], "join_key": role["join_key"], "key_value": role["key_value"],
                "candidate_records": len(candidates),
                "source": None if single is None else {"stream_id": single["stream_id"],
                                                       "relative_path": single["relative_path"],
                                                       "line_index": single["line_index"],
                                                       "event_seq": single["projection"].get("event_seq"),
                                                       "event_type": single["projection"].get("event_type")},
                "recorded_fields": single["projection"] if single else None,
                "recorded_state": (single or {}).get("payload") if single else None,
                "candidates": [{"line_index": item["line_index"], "record_position": item["record_position"],
                                "event_seq": item["projection"].get("event_seq"),
                                "event_type": item["projection"].get("event_type"),
                                "backend_monotonic_s": item["projection"].get("backend_monotonic_s"),
                                "sim_time_s": item["projection"].get("sim_time_s"),
                                "payload": item.get("payload")} for item in candidates],
                "single_state_selected": single is not None,
                "multiple_candidates_note": None if single is not None or not candidates else
                                            "several state records carry this control_tick_id; all are listed and none is chosen",
                "declared_reference": {"feedback_sample_id": record.get("feedback_sample_id"),
                                       "row_status": by_role["feedback_observation_row"]["status"]},
                "recorder_declared_feedback": {"available": payload.get("feedback_time_s") is not None if timing_single else None,
                                               "timing_event_status": timing_role["status"],
                                               "feedback_time_s": payload.get("feedback_time_s") if timing_single else None,
                                               "feedback_clock": payload.get("feedback_clock") if timing_single else None,
                                               "capture_clocks_declared": payload.get("capture_clocks") if timing_single else None,
                                               "meaning": "the recorder's own declared feedback time for this frame, copied, not re-derived"},
                "units": {"*_rad": "radians", "*_rad_s": "radians per second", "*_m": "metres", "*_nm": "newton metres",
                          "*_xyzw": "quaternion x,y,z,w", "*_s": "seconds"},
                "carried_over_from_another_frame": False,
                "interpolated": False,
                "note": "this is the state the recorder placed on the frame's capture tick, not a verified same-instant sample of the scene"}

    def _times(self, record: dict[str, Any], by_role: dict[str, dict[str, Any]], *,
               anchor_line_index: int | None = None) -> dict[str, Any]:
        """Every difference names its own two records; nothing here is called one state sample age."""
        capture = record.get("capture_backend_monotonic_s")
        sim_capture = record.get("capture_sim_time_s")
        quantities: list[dict[str, Any]] = []
        meta = {item["key"]: item for item in TIMING_QUANTITIES}
        sim_meta = {item["key"]: item for item in SIM_TIME_QUANTITIES}

        state_role = by_role["state_feedback_event"]
        for item in state_role["sources"]:
            projection = item["projection"]
            payload = item.get("payload") or {}
            for key, value in (("state_event_write_minus_frame_capture", projection.get("backend_monotonic_s")),
                               ("state_payload_feedback_time_minus_frame_capture", payload.get("feedback_time_monotonic"))):
                delta = _delta(capture, value, meta[key], line_index=item["line_index"])
                if delta:
                    quantities.append(delta)
            between = _delta(projection.get("backend_monotonic_s"), payload.get("feedback_time_monotonic"),
                             meta["state_payload_feedback_time_minus_state_event_write"], line_index=item["line_index"])
            if between:
                between["capture_value"] = projection.get("backend_monotonic_s")
                quantities.append(between)
            # A payload stamp is never taken from the envelope: if the payload carries no numeric
            # sim_time_s, that quantity is absent instead of being filled from another record.
            for key, value in ((sim_meta["state_sim_time_minus_frame_capture_sim_time"]["key"], payload.get("sim_time_s")),
                               (sim_meta["state_event_envelope_sim_time_minus_frame_capture_sim_time"]["key"],
                                projection.get("sim_time_s"))):
                delta = _delta(sim_capture, value if _number(value) else None, sim_meta[key],
                               line_index=item["line_index"])
                if delta:
                    quantities.append(delta)

        for item in by_role["capture_timing_event"]["sources"]:
            payload = item.get("payload") or {}
            for key, value in (("recorder_declared_feedback_time_minus_frame_capture", payload.get("feedback_time_s")),
                               ("timing_payload_capture_minus_anchor_capture", payload.get("capture_backend_monotonic_s"))):
                delta = _delta(capture, value, meta[key], line_index=item["line_index"])
                if delta:
                    quantities.append(delta)

        for item in by_role["image_observation"]["sources"]:
            projection = item["projection"]
            for key, field in (("observation_measurement_minus_frame_capture", "measurement_time_s"),
                               ("observation_arrival_minus_frame_capture", "arrival_time_s")):
                delta = _delta(capture, projection.get(field), meta[key], line_index=item["line_index"])
                if delta:
                    delta["sensor_kind"] = projection.get("sensor_kind")
                    quantities.append(delta)

        persist_delta = _delta(capture, record.get("persist_backend_monotonic_s"), meta["persist_minus_capture"],
                               line_index=anchor_line_index)
        if persist_delta:
            quantities.append(persist_delta)

        timing_sources = by_role["capture_timing_event"]["sources"]
        timing_payload = timing_sources[0].get("payload") or {} if len(timing_sources) == 1 else {}
        declared = {key: value for key in RECORDER_DECLARED_LATENCY_FIELDS
                    for source in (timing_payload, record) if (value := source.get(key)) is not None}
        arrival = timing_payload.get("arrival_backend_monotonic_s")
        recomputed = (arrival - capture) * 1000.0 if _number(arrival) and _number(capture) else None
        return {"quantities": quantities,
                "semantics_rule": "each quantity is one named subtraction of two recorded fields; two records naming "
                                  "the same clock base are not merged into one instant",
                "recorder_declared": {"fields": declared,
                                      "observation_age_ms_note": "the recorder's observation_age_ms is its own "
                                                                 "capture-to-arrival figure for this frame, not the "
                                                                 "difference between a state sample and the capture",
                                      "recomputed_arrival_minus_capture_ms": recomputed,
                                      "agrees_with_recomputation": None if recomputed is None or declared.get("observation_age_ms") is None
                                      else abs(recomputed - declared["observation_age_ms"]) < 1e-6},
                "state_time_quantity_keys": ["state_event_write_minus_frame_capture",
                                             "state_payload_feedback_time_minus_frame_capture",
                                             "recorder_declared_feedback_time_minus_frame_capture"],
                "sim_time_quantity_keys": [item["key"] for item in SIM_TIME_QUANTITIES],
                "same_clock_verified": False,
                "removed_in_this_version": "age_of_state_relative_to_frame"}

    @staticmethod
    def _coverage(frames: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for role in PAGE_ROLES:
            counts: dict[str, int] = {}
            for frame in frames:
                entry = next(item for item in frame["roles"] if item["role"] == role)
                counts[entry["status"]] = counts.get(entry["status"], 0) + 1
            out[role] = counts
        return out

    def _clock_sameness(self) -> dict[str, Any]:
        """What the records name, what the reader can verify, and how far the writer can be bound."""
        return {"fields_that_name_a_shared_base": ["persisted frame clock and capture_clocks, transform row clock_id, "
                                                   "state event backend_monotonic_s, timing payload feedback_clock",
                                                   "on the representative frame all of them name backend_monotonic"],
                "declared_by_recorder": True,
                "verified_by_reader": False,
                "verified_claim": "naming one clock base is not proof that two writers stamped it at one instant",
                "writer_version_binding": {
                    "recorded": ["run manifest contract_version and software name/version",
                                 "each record's own contract_version",
                                 "observation profile_id, profile_version and profile_sha256 on the persisted frame"],
                    "not_recorded": ["the native build or release that wrote the archive",
                                     "a source commit for the writer"],
                    "consequence": "current native source can describe how these fields are produced, but cannot be "
                                   "cited as proof that this archive's writer behaved identically",
                    "synchronized_upgraded_by_numeric_closeness": False}}

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


def _conflicts(entry: dict[str, Any], first: dict[str, Any]) -> bool:
    """Whether a repeated candidate differs from the others on the fields this role projects."""
    return (json.dumps(entry["projection"], sort_keys=True) != json.dumps(first["projection"], sort_keys=True)
            or json.dumps(entry.get("payload"), sort_keys=True) != json.dumps(first.get("payload"), sort_keys=True))
