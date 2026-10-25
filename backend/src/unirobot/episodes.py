"""Read-only access to real historical mobileCar Episodes.

The archive is native-owned output on the server disk. This module never writes,
moves, re-exports or reinterprets it: it keeps native record identity, native time
fields and native action semantics, and it reports the declared status of a record
separately from whatever this reader actually verified while serving a request.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .contracts import Contract

EPISODE_READ_SCHEMA = "unirobot-mobilecar-episode-read-1"
SOURCE_SCHEMA = "unirobot-history-source-1"

DEFAULT_PAGE = 50
MAX_PAGE = 200
MEDIA_SAMPLE = 20
SCAN_LINE_LIMIT = 500_000
MAX_RECORD_BYTES = 256 * 1024

# stream id -> (path relative to the episode directory, record format, what the records mean)
STREAMS: dict[str, tuple[str, str, str]] = {
    "events": ("events.jsonl", "jsonl", "native event append order: lifecycle, feedback_initial, actuator_reference, command intent and feedback events"),
    "control": ("control.jsonl", "jsonl", "recorded targets, command intent and execution feedback carried on the control path"),
    "commands": ("commands.jsonl", "jsonl", "command dispatch records"),
    "transforms": ("transforms.jsonl", "jsonl", "recorded object/body transforms, the only pose source that belongs to this Episode"),
    "observations-index": ("observations/index.jsonl", "jsonl", "observation index: stream_id, sample_id, sensor_kind, clock and frame fields, inline value where small"),
    "observations-persist": ("observations/persist.jsonl", "jsonl", "persist accounting: persist_sequence, arrival/persist latencies, profile identity"),
    "initial-snapshot": ("initial_snapshot.json", "json", "initial state snapshot recorded at Episode start"),
    "episode": ("episode.json", "json", "Episode identity, segments, declared statuses and termination reason"),
    "tail": ("episode_complete.json", "json", "recorder tail marker with declared per-file checksums"),
}

TIME_BASES = {
    "wall_utc": ("wall_utc", "ISO-8601 Z, record arrival wall clock"),
    "backend_monotonic_s": ("backend_monotonic_s", "seconds, native backend monotonic clock"),
    "sim_time_s": ("sim_time_s", "seconds, simulator time"),
    "measurement_time_s": ("measurement_time_s", "seconds, sensor measurement time (observation records)"),
    "arrival_time_s": ("arrival_time_s", "seconds, sensor arrival time (observation records)"),
}

ACTION_SEMANTICS = {
    "recorded_target": ["actuator_reference"],
    "command_intent": ["requested", "approved", "rejected", "dispatch", "dispatched", "expired", "command_response"],
    "execution_feedback": ["feedback"],
    "recorded_state": ["feedback_initial"],
    "lifecycle": ["recording_start", "recording_stop", "episode_terminal"],
}

INTEGRITY_NOT_VERIFIED = [
    "files not opened by this request",
    "asset payloads except the ones actually served",
    "archive-wide per-record checksum verification",
    "physical settle/stop evidence behind a recorded status",
]


class HistoryError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 404,
                 detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code, self.status_code, self.detail = code, status_code, detail or {}


class HistorySource(Contract):
    schema_version: str
    source_id: str
    adapter_id: str
    robot_id: str
    contract_version: str
    reader_format: str
    recording_root: str
    native_release_id: str
    declaring_instance: dict[str, Any]
    access: str
    declared_scale: dict[str, Any]
    archive_baseline: dict[str, Any]
    policy: dict[str, Any]


class EpisodeLocation:
    """One Episode directory, addressed by its native (run_id, episode_id) pair."""

    def __init__(self, source: HistorySource, root: Path, run_id: str, episode_id: str) -> None:
        self.source = source
        self.root = root
        self.run_id = run_id
        self.episode_id = episode_id
        self.directory = root / run_id / "episodes" / episode_id

    def path_of(self, stream_id: str) -> Path:
        return self.directory / STREAMS[stream_id][0]

    def relative_reference(self) -> dict[str, Any]:
        return {
            "source_id": self.source.source_id,
            "adapter_id": self.source.adapter_id,
            "recording_root": str(self.source.recording_root),
            "run_id": self.run_id,
            "episode_id": self.episode_id,
            "episode_directory": str(self.directory),
            "native_contract_version": self.source.contract_version,
        }


def load_history_source(path: Path, root_override: str | os.PathLike[str] | None = None) -> tuple[HistorySource, Path]:
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    if body.get("schema_version") != SOURCE_SCHEMA:
        raise HistoryError("history_source_invalid", f"unsupported history source schema: {body.get('schema_version')}", 500)
    source = HistorySource(**body)
    root = Path(root_override).expanduser() if root_override else Path(source.recording_root)
    if not root.is_dir():
        raise HistoryError("history_source_unavailable", f"recording root is not a readable directory: {root}", 503)
    return source, root.resolve()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, f"corrupt:{exc.__class__.__name__}"
    return (value if isinstance(value, dict) else None), None if isinstance(value, dict) else "not_an_object"


def _iter_lines(path: Path) -> Iterator[tuple[int, str]]:
    with path.open("r", encoding="utf-8", errors="strict") as handle:
        for index, line in enumerate(handle):
            if line.strip():
                yield index, line


class EpisodeArchive:
    def __init__(self, source: HistorySource, root: Path, *, reference_model_sha256: str | None = None,
                 reference_scene_id: str | None = None) -> None:
        self.source = source
        self.root = root
        self.reference_model_sha256 = reference_model_sha256
        self.reference_scene_id = reference_scene_id
        self._index: dict[str, list[str]] | None = None
        self._manifest_cache: dict[str, dict[str, Any]] = {}

    # ---- index -----------------------------------------------------------------

    def _episode_index(self) -> dict[str, list[str]]:
        if self._index is None:
            index: dict[str, list[str]] = {}
            for run_dir in sorted(p for p in self.root.iterdir() if p.is_dir()):
                episodes = run_dir / "episodes"
                if not episodes.is_dir():
                    continue
                for episode_dir in sorted(p for p in episodes.iterdir() if p.is_dir()):
                    index.setdefault(episode_dir.name, []).append(run_dir.name)
            self._index = index
        return self._index

    def location(self, episode_id: str, run_id: str | None = None) -> EpisodeLocation:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", episode_id):
            raise HistoryError("episode_id_invalid", "episode id is not a native id token", 404)
        candidates = self._episode_index().get(episode_id, [])
        if run_id:
            candidates = [item for item in candidates if item == run_id]
        if not candidates:
            raise HistoryError("episode_not_found", "no Episode directory with that identity in this source", 404,
                               {"episode_id": episode_id, "run_id": run_id})
        if len(candidates) > 1:
            # The same display/episode id under more than one run must never cross-read.
            raise HistoryError("episode_id_ambiguous", "episode id exists under multiple runs; run_id is required", 409,
                               {"episode_id": episode_id, "runs": candidates})
        location = EpisodeLocation(self.source, self.root, candidates[0], episode_id)
        if not location.directory.is_dir():
            raise HistoryError("episode_not_found", "episode directory is not readable", 404)
        return location

    def _run_manifest(self, run_id: str) -> dict[str, Any]:
        if run_id not in self._manifest_cache:
            value, _ = _load_json(self.root / run_id / "manifest.json")
            self._manifest_cache[run_id] = value or {}
        return self._manifest_cache[run_id]

    # ---- list ------------------------------------------------------------------

    def list_episodes(self, *, limit: int = DEFAULT_PAGE, offset: int = 0, run_id: str | None = None,
                      recording_status: str | None = None, episode_id: str | None = None) -> dict[str, Any]:
        limit = max(1, min(limit, MAX_PAGE))
        locations = []
        for target, runs in sorted(self._episode_index().items()):
            for candidate in runs:
                if run_id and candidate != run_id:
                    continue
                if episode_id and target != episode_id:
                    continue
                locations.append(EpisodeLocation(self.source, self.root, candidate, target))
        if recording_status:
            wanted = recording_status.upper()
            locations = [item for item in locations
                         if (_load_json(item.path_of("episode"))[0] or {}).get("recording_status") == wanted]
        locations.sort(key=lambda item: (item.run_id, item.episode_id))
        total = len(locations)
        page = locations[offset:offset + limit]
        items = []
        for location in page:
            episode, error = _load_json(location.path_of("episode"))
            episode = episode or {}
            items.append({
                "run_id": location.run_id,
                "episode_id": location.episode_id,
                "contract_version": episode.get("contract_version"),
                "readable": error is None,
                "read_error": error,
                "task_language": episode.get("task_language"),
                "operator_id": episode.get("operator_id"),
                "operator_kind": episode.get("operator_kind"),
                "view_source": episode.get("view_source"),
                "map_mode": episode.get("map_mode"),
                "created_wall_utc": episode.get("created_wall_utc"),
                "ended_wall_utc": episode.get("ended_wall_utc"),
                "segment_count": len(episode.get("segments") or []),
                "declared": {
                    "recording_status": episode.get("recording_status"),
                    "audit_status": episode.get("audit_status"),
                    "result": episode.get("result"),
                    "termination_reason": episode.get("termination_reason"),
                    "require_recording": episode.get("require_recording"),
                },
                "declaration_only": True,
            })
        return {
            "schema_version": EPISODE_READ_SCHEMA,
            "read_only": True,
            "source": self._source_view(),
            "retrieved_at": _now(),
            "paging": {"limit": limit, "offset": offset, "returned": len(items), "total_matches": total,
                       "next_offset": offset + len(items) if offset + len(items) < total else None,
                       "order": "run_id_then_episode_id",
                       "declared_total_from_native_list": self.source.declared_scale.get("episodes_from_native_list")},
            "filters": {"run_id": run_id, "recording_status": recording_status, "episode_id": episode_id},
            "episodes": items,
            "integrity_scope": "statuses are as declared by the native record files; this list opened episode.json only",
            "capability_limits": ["no replay execution", "no native validate proxy", "no control, RESET, recording or physics stepping"],
        }

    def _source_view(self) -> dict[str, Any]:
        return {
            "source_id": self.source.source_id,
            "adapter_id": self.source.adapter_id,
            "robot_id": self.source.robot_id,
            "native_release_id": self.source.native_release_id,
            "native_contract_version": self.source.contract_version,
            "recording_root": str(self.source.recording_root),
            "access": self.source.access,
            "declaring_instance": self.source.declaring_instance,
            "archive_baseline": self.source.archive_baseline,
            "platform_writes": False,
        }

    # ---- detail ----------------------------------------------------------------

    def detail(self, episode_id: str, run_id: str | None = None) -> dict[str, Any]:
        location = self.location(episode_id, run_id)
        episode, episode_error = _load_json(location.path_of("episode"))
        tail, tail_error = _load_json(location.path_of("tail"))
        manifest = self._run_manifest(location.run_id)
        segments = [
            {
                "recording_segment_id": item.get("recording_segment_id"),
                "previous_recording_segment_id": item.get("previous_recording_segment_id"),
                "status": item.get("status"),
                "reason": item.get("reason"),
                "started_wall_utc": item.get("started_wall_utc"),
                "ended_wall_utc": item.get("ended_wall_utc"),
                "started_backend_monotonic_s": item.get("started_backend_monotonic_s"),
                "termination_reason": item.get("termination_reason"),
            }
            for item in (episode or {}).get("segments") or []
        ]
        streams = self.streams_view(location)
        checksums = (tail or {}).get("checksums") if isinstance(tail, dict) else None
        matched: list[dict[str, Any]] = []
        mismatched: list[dict[str, Any]] = []
        if isinstance(checksums, dict):
            # Recompute only what this request actually opened; the rest stays unverified.
            for name, path in (("episode.json", location.path_of("episode")),
                               ("episode_complete.json", location.path_of("tail"))):
                declared = checksums.get(name)
                if declared and path.is_file():
                    actual = self._file_digest(path)
                    (matched if actual == declared else mismatched).append(
                        {"relative_path": name, "declared_sha256": declared, "actual_sha256": actual})
        return {
            "schema_version": EPISODE_READ_SCHEMA,
            "read_only": True,
            "source": self._source_view(),
            "retrieved_at": _now(),
            "identity": {
                **location.relative_reference(),
                "backend_generation": self._generation(location),
                "segments": segments,
                "episode_display_name_is_not_a_key": True,
            },
            "declared": {
                "recording_status": (episode or {}).get("recording_status"),
                "audit_status": (episode or {}).get("audit_status"),
                "result": (episode or {}).get("result"),
                "task_result_source": (episode or {}).get("task_result_source"),
                "termination_reason": (episode or {}).get("termination_reason"),
                "require_recording": (episode or {}).get("require_recording"),
                "complete_tail_file_present": location.path_of("tail").is_file(),
                "declared_checksum_entries": len(checksums) if isinstance(checksums, dict) else None,
                "episode_json_readable": episode_error is None,
                "tail_json_readable": tail_error is None,
            },
            "integrity": {
                "status": self._integrity_status(episode, tail, tail_error, episode_error),
                "scope": "this episode, as read by this request",
                "this_read_evidence": {
                    "episode_json_parsed": episode_error is None,
                    "tail_json_parsed": tail_error is None,
                    "episode_json_sha256": self._file_digest(location.path_of("episode")),
                    "tail_json_sha256": self._file_digest(location.path_of("tail")),
                    "files_recomputed_here": ["episode.json", "episode_complete.json"],
                },
                "checksum_verification": {
                    "declared_entries": len(checksums) if isinstance(checksums, dict) else 0,
                    "matched": matched,
                    "mismatched": mismatched,
                    "verdict": ("all_matched" if matched and not mismatched
                                else "mismatch_present" if mismatched else "nothing_recomputable"),
                    "meaning": "a tail checksum is the recorder's own declaration; only the files listed here were re-computed by this request, and a mismatch is reported as a finding instead of relabeled",
                },
                "not_verified": INTEGRITY_NOT_VERIFIED,
                "declaration_is_not_verification": True,
            },
            "streams": streams,
            "time": {
                "record_order_is_native_append_order": True,
                "clocks_declared_by_run_manifest": manifest.get("clocks"),
                "available_time_bases": self._time_bases(location),
                "units": {"*_s": "seconds", "*_ms": "milliseconds", "*_rad": "radians", "*_m": "metres"},
                "browser_arrival_order_is_not_used": True,
                "synchronized_across_streams": False,
            },
            "action_semantics": {
                **ACTION_SEMANTICS,
                "note": "Actual state, recorded Target, command intent and execution feedback stay in separate event classes; this reader never promotes one into another",
                "categories_are_by_recorded_event_type": True,
            },
            "recorded_model_identity": {
                "model_id": manifest.get("model_id"),
                "model_sha256": manifest.get("model_sha256"),
                "scene_id": manifest.get("scene_id"),
                "map_mode": manifest.get("map_mode"),
                "truth_access": manifest.get("truth_access"),
                "run_contract_version": manifest.get("contract_version"),
                "source": "run manifest.json as recorded",
            },
            "three_d_replay": self._three_d_replay(location, manifest, streams),
            "platform_association": self._association(location),
            "training_qualification": self._qualification(location),
            "media_summary": self._media_summary(location, checksums),
            "capability_limits": ["no replay execution", "no native validate proxy", "no control, RESET, recording or physics stepping"],
        }

    def _generation(self, location: EpisodeLocation) -> dict[str, Any]:
        # Native keeps backend_generation inside the recorded command payload, never at record top level.
        path = location.path_of("events")
        if not path.is_file():
            return {"available": False, "reason": "events stream missing", "values": []}
        found: list[int] = []
        for index, line in _iter_lines(path):
            if "backend_generation" not in line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            for holder in (payload.get("request"), payload.get("command"), payload):
                if isinstance(holder, dict) and isinstance(holder.get("backend_generation"), int):
                    found.append(holder["backend_generation"])
                    break
            if len(found) >= 5 or index > SCAN_LINE_LIMIT:
                break
        return {"available": bool(found), "reason": None if found else "no recorded command payload carried a generation",
                "distinct_values": sorted(set(found)), "scope": "sampled recorded payloads, not a per-record field"}

    def _file_digest(self, path: Path) -> str | None:
        return _sha256(path.read_bytes()) if path.is_file() else None

    def _integrity_status(self, episode: dict | None, tail: dict | None, tail_error: str | None,
                          episode_error: str | None) -> str:
        if episode_error:
            return "unknown"
        if tail is None:
            return "finalize_failed_missing_tail"
        recording = (episode or {}).get("recording_status")
        audit = (episode or {}).get("audit_status")
        if recording == "COMPLETE" and audit == "COMPLETE":
            return "complete"
        return "incomplete_terminal_recorded"

    def _time_bases(self, location: EpisodeLocation) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for stream_id in ("events", "control", "observations-index"):
            path = location.path_of(stream_id)
            if not path.is_file():
                out[stream_id] = {"available": False}
                continue
            present: set[str] = set()
            for _, line in _iter_lines(path):
                for base, (field, _) in TIME_BASES.items():
                    if f'"{field}"' in line:
                        present.add(base)
                break
            out[stream_id] = {"available": True, "time_bases_in_first_record": sorted(present)}
        return out

    def streams_view(self, location: EpisodeLocation) -> list[dict[str, Any]]:
        out = []
        for stream_id, (relative, fmt, meaning) in STREAMS.items():
            path = location.directory / relative
            entry: dict[str, Any] = {"stream_id": stream_id, "relative_path": relative, "format": fmt,
                                     "semantics": meaning, "available": path.is_file()}
            if not path.is_file():
                entry.update({"bytes": None, "records": None, "records_counted": False,
                              "reason": "stream_not_recorded_or_missing"})
            elif fmt == "json":
                value, error = _load_json(path)
                entry.update({"bytes": path.stat().st_size, "records": 1 if value else None,
                              "records_counted": value is not None, "parse_error": error})
            else:
                count, oversized = 0, 0
                with path.open("r", encoding="utf-8", errors="strict") as handle:
                    for line in handle:
                        if not line.strip():
                            continue
                        count += 1
                        if len(line) > MAX_RECORD_BYTES:
                            oversized += 1
                        if count >= SCAN_LINE_LIMIT:
                            entry["scan_truncated"] = True
                            break
                entry.update({"bytes": path.stat().st_size, "records": count, "records_counted": True,
                              "records_over_read_size_limit": oversized})
            out.append(entry)
        return out

    def _media_summary(self, location: EpisodeLocation, checksums: dict | None) -> dict[str, Any]:
        assets = location.directory / "assets"
        kinds: dict[str, Any] = {}
        if assets.is_dir():
            for kind_dir in sorted(p for p in assets.iterdir() if p.is_dir()):
                files = sorted((p for p in kind_dir.rglob("*") if p.is_file()), key=lambda p: p.name)
                sample = []
                for path in files[:MEDIA_SAMPLE]:
                    relative = str(path.relative_to(location.directory))
                    sample.append({"relative_path": relative, "bytes": path.stat().st_size,
                                   "declared_sha256": (checksums or {}).get(relative)})
                kinds[kind_dir.name] = {"count": len(files), "bytes_total": sum(p.stat().st_size for p in files),
                                        "sample": sample,
                                        "sample_truncated": len(files) > len(sample),
                                        "declared_sha256_coverage": f"{sum(1 for item in sample if item['declared_sha256'])}/{len(sample)}"}
        return {"assets_root": "assets/", "kinds": kinds,
                "uri_convention": "assets/<kind>/<file>, served only from this episode directory",
                "declared_sha256_source": "episode_complete.json checksums when present",
                "verification": "digests are recomputed only for assets actually served by the asset endpoint"}

    def _three_d_replay(self, location: EpisodeLocation, manifest: dict, streams: list[dict]) -> dict[str, Any]:
        recorded_model = manifest.get("model_sha256")
        transforms = next((item for item in streams if item["stream_id"] == "transforms"), None)
        if recorded_model and self.reference_model_sha256:
            model_match = "match" if recorded_model == self.reference_model_sha256 else "mismatch"
        else:
            model_match = "unknown"
        scene_match = ("match" if manifest.get("scene_id") == self.reference_scene_id else "mismatch") \
            if (manifest.get("scene_id") and self.reference_scene_id) else "unknown"
        reasons = []
        if model_match != "match" or scene_match != "match":
            status = "restricted"
            if model_match != "match":
                reasons.append("recorded model identity does not match the current production recipe pin" if model_match == "mismatch"
                               else "recorded model identity is missing or the reference pin is unavailable")
            if scene_match != "match":
                reasons.append("recorded scene id differs from the current recipe scene" if scene_match == "mismatch"
                               else "recorded scene id is missing or the reference scene is unavailable")
        else:
            status = "identity_verified_rendering_unverified"
            reasons.append("the recorded model and scene digests equal the current production pin, so the mesh identity can be reused")
        reasons.append("rendered-replay correctness is not verified by this slice and live Actual/geometry is never substituted for recorded state")
        return {"status": status,
                "recorded_model_sha256": recorded_model,
                "reference_model_sha256": self.reference_model_sha256,
                "recorded_scene_id": manifest.get("scene_id"),
                "reference_scene_id": self.reference_scene_id,
                "model_match": model_match,
                "scene_match": scene_match,
                "recorded_transforms_available": bool(transforms and transforms.get("available")),
                "live_geometry_or_actual_may_be_applied": False,
                "reasons": reasons,
                "still_available": ["metadata", "events", "recorded transforms", "media assets that exist"]}

    def _association(self, location: EpisodeLocation) -> dict[str, Any]:
        sidecar = location.directory / "platform_session.json"
        if sidecar.is_file():
            value, error = _load_json(sidecar)
            if value:
                return {"known": True, "source": "platform_session.json sidecar", "sidecar_error": error,
                        "validated_snapshot_ref": value.get("validated_snapshot_ref"),
                        "platform_session_id": value.get("platform_session_id")}
        return {"known": False, "validated_snapshot_ref": None, "platform_session_id": None,
                "reason": "legacy_native_record_without_platform_sidecar",
                "policy": "no platform configuration association is invented for a native record"}

    def _qualification(self, location: EpisodeLocation) -> dict[str, Any]:
        value, _ = _load_json(location.directory / "assessments" / "eligibility.json")
        report, _ = _load_json(location.directory / "quality_report.json")
        return {"declared_eligibility_present": bool(value), "training_qualified": (value or {}).get("training_qualified"),
                "export_valid": (value or {}).get("export_valid"),
                "quality_report_present": bool(report),
                "blocks_raw_read": False,
                "note": "training_qualified=false never blocks a qualified raw read of the recorded data"}

    # ---- records ---------------------------------------------------------------

    def records(self, episode_id: str, stream_id: str, *, run_id: str | None = None,
                limit: int = DEFAULT_PAGE, offset: int = 0, event_seq_from: int | None = None,
                event_seq_to: int | None = None, time_base: str | None = None,
                time_from: float | None = None, time_to: float | None = None) -> dict[str, Any]:
        location = self.location(episode_id, run_id)
        if stream_id not in STREAMS:
            raise HistoryError("episode_stream_unsupported", f"unknown stream id: {stream_id}", 404,
                               {"supported": sorted(STREAMS)})
        relative, fmt, meaning = STREAMS[stream_id]
        path = location.directory / relative
        if not path.is_file():
            raise HistoryError("episode_stream_unavailable", "this stream is not present in the record", 404,
                               {"stream_id": stream_id, "relative_path": relative})
        limit = max(1, min(limit, MAX_PAGE))
        selected_field, _ = TIME_BASES[time_base] if time_base in TIME_BASES else (None, None)
        if time_base and time_base not in TIME_BASES:
            raise HistoryError("time_base_unsupported", f"unknown time base: {time_base}", 400,
                               {"supported": sorted(TIME_BASES)})
        if time_base and (time_from is None and time_to is None):
            raise HistoryError("time_range_required", "time_base needs time_from or time_to in that base", 400)
        window_active = selected_field is not None and (time_from is not None or time_to is not None)

        records: list[dict[str, Any]] = []
        skipped_before = 0
        scanned = 0
        corrupt: list[dict[str, Any]] = []
        truncated: list[int] = []
        missing_time_base = 0

        if fmt == "json":
            value, error = _load_json(path)
            if error:
                raise HistoryError("episode_record_corrupt", f"record file could not be parsed: {error}", 502,
                                   {"stream_id": stream_id, "relative_path": relative})
            all_records = [value]
        else:
            all_records = None  # streamed below

        def accept(record: dict[str, Any]) -> bool:
            nonlocal missing_time_base
            seq = record.get("event_seq")
            if event_seq_from is not None and isinstance(seq, int) and seq < event_seq_from:
                return False
            if event_seq_to is not None and isinstance(seq, int) and seq > event_seq_to:
                return False
            if window_active:
                stamp = record.get(selected_field)
                if not isinstance(stamp, (int, float)):
                    missing_time_base += 1
                    return False
                if time_from is not None and stamp < time_from:
                    return False
                if time_to is not None and stamp > time_to:
                    return False
            return True

        if all_records is not None:
            for index, record in enumerate(all_records):
                scanned = index + 1
                if index < offset:
                    skipped_before += 1
                    continue
                if not accept(record):
                    continue
                if len(records) < limit:
                    records.append({"line_index": index, "record": record})
        else:
            with path.open("r", encoding="utf-8") as handle:
                index = -1
                for raw in handle:
                    if not raw.strip():
                        continue
                    index += 1
                    scanned = index + 1
                    if len(raw) > MAX_RECORD_BYTES:
                        truncated.append(index)
                        continue
                    if index < offset:
                        skipped_before += 1
                        continue
                    try:
                        record = json.loads(raw)
                    except json.JSONDecodeError as exc:
                        corrupt.append({"line_index": index, "error": f"{exc.__class__.__name__}: {exc.msg}",
                                        "column": exc.colno})
                        continue
                    if not isinstance(record, dict):
                        corrupt.append({"line_index": index, "error": "record_is_not_an_object"})
                        continue
                    if not accept(record):
                        continue
                    if len(records) >= limit:
                        break
                    records.append({"line_index": index, "record": record})

        first = records[0]["record"] if records else None
        last = records[-1]["record"] if records else None
        return {
            "schema_version": EPISODE_READ_SCHEMA,
            "read_only": True,
            "source": self._source_view(),
            "retrieved_at": _now(),
            "identity": {"run_id": location.run_id, "episode_id": location.episode_id,
                         "native_contract_version": (first or {}).get("contract_version", self.source.contract_version)},
            "stream": {"stream_id": stream_id, "relative_path": relative, "format": fmt, "semantics": meaning,
                       "file_bytes": path.stat().st_size},
            "paging": {"limit": limit, "offset": offset, "returned": len(records),
                       "scanned_lines": scanned, "skipped_before_offset": skipped_before,
                       "next_offset": records[-1]["line_index"] + 1 if records else None,
                       "has_more": bool(records) and (scanned > records[-1]["line_index"] + 1)},
            "cursor": {
                "order": "native_append_order",
                "first_line_index": records[0]["line_index"] if records else None,
                "last_line_index": records[-1]["line_index"] if records else None,
                "first_event_seq": (first or {}).get("event_seq"),
                "last_event_seq": (last or {}).get("event_seq"),
                "line_index_is_not_a_clock": True,
            },
            "time": {"selected_time_base": time_base, "time_from": time_from, "time_to": time_to,
                     "units": "seconds for *_s, milliseconds for *_ms; wall_utc is ISO-8601 Z",
                     "records_without_the_selected_base": missing_time_base,
                     "synchronized_across_streams": False},
            "records": records,
            "integrity": {"corrupt_lines": corrupt, "lines_over_read_size_limit": truncated,
                          "declared_status": self._declared_status(location),
                          "scope": "records returned by this page only",
                          "not_verified": ["records outside this page", "asset payloads referenced by these records"]},
        }

    def _declared_status(self, location: EpisodeLocation) -> dict[str, Any]:
        episode, _ = _load_json(location.path_of("episode"))
        return {"recording_status": (episode or {}).get("recording_status"),
                "audit_status": (episode or {}).get("audit_status"),
                "termination_reason": (episode or {}).get("termination_reason"),
                "declaration_only": True}

    def stream_catalog(self, episode_id: str, run_id: str | None = None) -> dict[str, Any]:
        location = self.location(episode_id, run_id)
        return {
            "schema_version": EPISODE_READ_SCHEMA,
            "read_only": True,
            "source": self._source_view(),
            "retrieved_at": _now(),
            "identity": location.relative_reference(),
            "declared_status": self._declared_status(location),
            "streams": self.streams_view(location),
            "media_summary": self._media_summary(location, (_load_json(location.path_of("tail"))[0] or {}).get("checksums")),
            "capability_limits": ["no replay execution", "no native validate proxy"],
        }

    # ---- media assets ----------------------------------------------------------

    def resolve_asset(self, episode_id: str, asset_path: str, run_id: str | None = None) -> tuple[EpisodeLocation, Path]:
        location = self.location(episode_id, run_id)
        if not asset_path or asset_path.startswith("/") or ".." in Path(asset_path).parts:
            raise HistoryError("episode_asset_path_invalid", "asset path must be a relative path inside this episode", 400,
                               {"episode_id": episode_id})
        parts = Path(asset_path).parts
        # Native stores and cites media as assets/<kind>/<file>; both that URI and the bare
        # kind/file remainder address the same file, and nothing outside assets/ is reachable.
        relative = Path(*parts) if parts[0] == "assets" else Path("assets").joinpath(*parts)
        candidate = (location.directory / relative).resolve()
        assets_root = (location.directory / "assets").resolve()
        if not candidate.is_relative_to(assets_root):
            raise HistoryError("episode_asset_escape", "asset resolves outside this episode's assets tree", 409,
                               {"episode_id": episode_id, "hint": "raw jsonl streams are read through the streams endpoint"})
        if not candidate.is_file():
            raise HistoryError("episode_asset_missing", "asset is not present in the record", 404, {"episode_id": episode_id})
        return location, candidate

    def asset(self, episode_id: str, asset_path: str, run_id: str | None = None,
              sha256: str | None = None) -> tuple[bytes, str, dict[str, Any]]:
        location, candidate = self.resolve_asset(episode_id, asset_path, run_id)
        media_type = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                      ".npy": "application/octet-stream", ".json": "application/json"}.get(candidate.suffix.lower())
        if media_type is None:
            raise HistoryError("episode_asset_type_unsupported", f"unsupported asset type: {candidate.suffix}", 415,
                               {"suffix": candidate.suffix})
        if candidate.stat().st_size > 32 * 1024 * 1024:
            raise HistoryError("episode_asset_too_large", "asset exceeds the read size limit", 413,
                               {"bytes": candidate.stat().st_size})
        body = candidate.read_bytes()
        digest = _sha256(body)
        if sha256 and sha256 != digest:
            raise HistoryError("episode_asset_digest_mismatch", "asset digest does not match the requested sha256", 409,
                               {"expected": sha256, "actual": digest})
        return body, media_type, {"X-Episode-Asset-Sha256": digest, "X-Episode-Run-Id": location.run_id}
