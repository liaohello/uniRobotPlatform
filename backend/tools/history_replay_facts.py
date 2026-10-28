"""Extract the measured minimum fact table a future replay needs, over GET only.

This records what the archive actually contains today — per-stream time bases, the
identifier and media linkage inside real records, units and frames, and the recorded
model identity — and what it does NOT yet prove: cross-stream synchronisation and
rendered 3D replay. It runs against a live candidate over HTTP and writes JSON; it
never sends a non-GET request and never opens a write handle on the archive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from native_get_probe import GetProbe

STREAMS = ("events", "control", "commands", "transforms", "observations-index", "observations-persist")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform-url", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--startup-manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    P = args.platform_url.rstrip("/")
    probe = GetProbe()

    def get(path: str) -> Any:
        status, body = probe.json(f"{P}{path}")
        if status != 200:
            raise SystemExit(f"GET {path} -> {status}: {json.dumps(body, default=str)[:200]}")
        return body

    scoped = f"?run_id={args.run_id}"
    detail = get(f"/api/v1/episodes/{args.episode_id}{scoped}")
    streams: dict[str, Any] = {}
    for stream in STREAMS:
        page = get(f"/api/v1/episodes/{args.episode_id}/streams/{stream}/records{scoped}&limit=3"
                   if scoped else f"/api/v1/episodes/{args.episode_id}/streams/{stream}/records?limit=3")
        records = [item["record"] for item in page["records"]]
        fields = sorted({key for record in records for key in record})
        media = sorted({key for record in records for key in record.get("metadata", {}) if isinstance(record.get("metadata"), dict)})
        streams[stream] = {
            "relative_path": page["stream"]["relative_path"],
            "time_bases_in_returned_records": page["time"]["available_time_bases"] if "available_time_bases" in page["time"] else None,
            "record_fields": fields,
            "identifier_fields": {key: sorted({str(record.get(key)) for record in records})[:4]
                                  for key in ("event_seq", "stream_id", "sample_id", "feedback_sample_id",
                                               "command_id", "control_tick_id", "persist_sequence", "plan_id")
                                  if any(key in record for record in records)},
            "clock_and_frame": {key: sorted({str(record.get(key)) for record in records if record.get(key) is not None})[:4]
                                for key in ("clock_id", "frame_id", "source", "quality")
                                if any(key in record for record in records)},
            "media_metadata_keys": media,
            "event_seq_present_in_any_record": any("event_seq" in record for record in records),
            "returned": len(records),
        }
    index = get(f"/api/v1/episodes/{args.episode_id}/streams/observations-index/records{scoped}&limit=64")
    candidates = [item["record"] for item in index["records"]]
    # Take the first record that actually carries a media reference rather than assuming
    # the stream order, so an empty sample means "not in the fetched window", not "absent".
    sample = next((record for record in candidates
                   if any(str(key).endswith(("_uri", "_sha256")) for key in record)), {})
    linked = sample.get("metadata", {}) if isinstance(sample.get("metadata"), dict) else {}

    out = {
        "source": {"episode_id": args.episode_id, "run_id": args.run_id,
                   "platform_url": P,
                   "candidate_startup_manifest_digest": hashlib.sha256(args.startup_manifest.read_bytes()).hexdigest(),
                   "platform_source_aggregate": json.loads(args.startup_manifest.read_text())["platform_source"]["aggregate"]},
        "identity": detail["identity"],
        "recorded_model_identity": detail["recorded_model_identity"],
        "three_d_replay": detail["three_d_replay"],
        "declared": detail["declared"],
        "integrity": detail["integrity"],
        "platform_time_statement": detail["time"],
        "action_semantics": detail["action_semantics"],
        "streams": streams,
        "media_linkage_sample": {"fetched_index_records": len(candidates),
                                 "sample_stream_id": sample.get("stream_id"), "sample_sensor_kind": sample.get("sensor_kind"),
                                 "sample_id": sample.get("sample_id"),
                                 "observation_keys_with_media_reference": sorted(key for key in sample
                                                                                  if "uri" in key or "sha256" in key or key.endswith("_id")),
                                 "asset_uri": sample.get("asset_uri"), "valid_mask_uri": sample.get("valid_mask_uri"),
                                 "asset_sha256": sample.get("asset_sha256"),
                                 "valid_mask_sha256": sample.get("valid_mask_sha256"),
                                 "feedback_sample_id": sample.get("feedback_sample_id"),
                                 "metadata_keys": sorted(linked),
                                 "note": "media path association is whatever the recorded observation carries; it is copied, not inferred"},
        "paging_contract": {"offset_is_line_index": True, "limit_max": 200,
                            "cursor": "native append order; line_index is never a clock",
                            "event_seq_range": "records without a true integer event_seq are excluded and counted when a range is active"},
        "proven_by_this_run": ["each listed field exists in the fetched records of this real Episode",
                              "per-stream time bases and frames are copied from the records themselves",
                              "the recorded model/scene identity and its comparison to the current pin"],
        "not_proven": ["cross-stream time alignment or a shared replay cursor",
                       "that similar measurement/arrival values are the same instant",
                       "rendered 3D replay correctness even when the model digest matches",
                       "that files outside the fetched set are unchanged",
                       "completeness of the whole archive or training qualification"],
        "requests": probe.summary(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "streams": sorted(streams), "requests": out["requests"]["requests"],
                      "not_proven": len(out["not_proven"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
