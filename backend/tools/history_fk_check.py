#!/usr/bin/env python3
"""Offline kinematic cross-check of recorded robot state against the frozen model.

Reads the historical archive and the frozen compiled geometry bundle straight from disk, never
over HTTP, and answers one question with numbers: when the recorded base pose and the recorded
five arm angles are pushed through the frozen model tree, does the site position we compute match
the site position the recorder wrote in the same payload?

Agreement is kinematic consistency only. It does not calibrate hardware, does not certify rendered
appearance, and does not identify which native build wrote the archive. Axes the samples never
moved are reported as unexercised rather than validated.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from unirobot.frames import STREAMS, _stream_lines  # noqa: E402
from unirobot.history_fk import FrozenSceneTree, _quat, _vec, distance_m, site_world_position  # noqa: E402
from unirobot.mobilecar_geometry import GeometryBundle  # noqa: E402

TOLERANCE_M = 0.005
STATE_EVENT_TYPES = ("feedback", "feedback_initial")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _episode_directory(runs: Path, run_id: str, episode_id: str) -> Path:
    for candidate in ((runs / run_id / "episodes" / episode_id),):
        resolved = candidate.resolve()
        if not str(resolved).startswith(str(runs.resolve())):
            raise SystemExit("the episode path escapes the declared runs root")
        if not resolved.is_dir():
            raise SystemExit(f"no such episode directory: {resolved}")
        return resolved


def _anchors(episode: Path, sample_limit: int) -> tuple[list[dict[str, Any]], int, int]:
    """Every persisted frame, thinned to a bounded stride so the pass stays predictable."""
    rows = [record for _, record in _stream_lines(episode / STREAMS["observations-persist"][0], ("rgbd",))
            if record.get("stream_id") == "rgbd" and isinstance(record.get("sample_id"), str)]
    if len(rows) <= sample_limit:
        return rows, len(rows), 1
    stride = -(-len(rows) // sample_limit)
    return rows[::stride], len(rows), stride


def _state_by_tick(episode: Path, ticks: set[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    conflicts: set[str] = set()
    for _, record in _stream_lines(episode / STREAMS["events"][0], tuple(ticks)):
        tick = record.get("control_tick_id")
        if record.get("event_type") in STATE_EVENT_TYPES and isinstance(tick, str) and tick in ticks:
            if tick in found and json.dumps(found[tick].get("payload"), sort_keys=True) != json.dumps(record.get("payload"), sort_keys=True):
                conflicts.add(tick)
            found.setdefault(tick, record)
    for tick in conflicts:
        found.pop(tick, None)
    return found


def _fk(links: list[dict[str, Any]], arm_names: list[str], qpos: list[float], base_position: list[float],
        base_quaternion: list[float], site_parent: str, site_offset: list[float]) -> tuple[float, float, float] | None:
    position = _vec(base_position)
    orientation = _quat(base_quaternion)
    if position is None or orientation is None:
        return None
    tree = FrozenSceneTree(links)
    poses = tree.body_poses("base_link", position, orientation, dict(zip(arm_names, qpos)))
    if poses is None or site_parent not in poses:
        return None
    return site_world_position(poses, site_parent, _vec(site_offset) or (0.0, 0.0, 0.0))


def _spread_m(points: list[list[float]]) -> dict[str, float]:
    """Per-axis travel of the recorded base position across the compared samples."""
    if not points:
        return {}
    axes = range(min(len(item) for item in points))
    return {f"axis_{axis}_range_m": max(item[axis] for item in points) - min(item[axis] for item in points)
            for axis in axes}


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values)
    return {"count": len(ordered), "min_m": ordered[0], "median_m": statistics.median(ordered),
            "p95_m": ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))], "max_m": ordered[-1]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--kinematics-config", required=True, type=Path)
    parser.add_argument("--sample-limit", type=int, default=120)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    bundle = GeometryBundle(args.bundle)
    links = [link.model_dump() for link in bundle.scene.links]
    config = json.loads(args.kinematics_config.read_text(encoding="utf-8"))
    arm_names = list(config["arm"]["joint_names"])
    bundle_arm_order = [link.joint_name for link in bundle.scene.links if link.joint_name in arm_names]
    tcp = config["tcp"]
    root_offset = _vec(next((link.local_transform.position_m for link in bundle.scene.links
                             if link.name == "base_link"), [0.0, 0.0, 0.0])) or (0.0, 0.0, 0.0)

    episode = _episode_directory(args.runs_root, args.run_id, args.episode_id)
    manifest = json.loads((args.runs_root / args.run_id / "manifest.json").read_text(encoding="utf-8"))
    anchors, anchor_total, stride = _anchors(episode, args.sample_limit)
    states = _state_by_tick(episode, {item["capture_control_tick_id"] for item in anchors
                                      if isinstance(item.get("capture_control_tick_id"), str)})

    compared: list[dict[str, Any]] = []
    skipped: dict[str, int] = {"no_state_event_on_the_capture_tick": 0, "state_payload_missing_fields": 0}
    excursions: list[list[float]] = [[] for _ in arm_names]
    base_positions: list[list[float]] = []
    for anchor in anchors:
        tick = anchor.get("capture_control_tick_id")
        state = states.get(tick if isinstance(tick, str) else "")
        payload = (state or {}).get("payload") if state else None
        if not payload:
            skipped["no_state_event_on_the_capture_tick"] += 1
            continue
        qpos, base_position, base_quaternion, recorded_tcp = (payload.get("arm_model_qpos_rad"),
                                                              payload.get("base_position_world_sim_m"),
                                                              payload.get("base_quaternion_xyzw"),
                                                              _vec(payload.get("tcp_position_world_m")))
        if not (isinstance(qpos, list) and len(qpos) == len(arm_names) and all(isinstance(v, (int, float)) for v in qpos)) \
                or _vec(base_position) is None or _quat(base_quaternion) is None or recorded_tcp is None:
            skipped["state_payload_missing_fields"] += 1
            continue
        primary = _fk(links, arm_names, qpos, base_position, base_quaternion, tcp["parent_body"], tcp["position_m"])
        alternative = _fk(links, arm_names, qpos,
                          [base_position[0] + root_offset[0], base_position[1] + root_offset[1],
                           base_position[2] + root_offset[2]], base_quaternion,
                          tcp["parent_body"], tcp["position_m"])
        # Permutations are diagnostics, not hypotheses to be fitted: the source order is the claim
        # under test, and the table only shows how well the alternatives would have done.
        permutations = {}
        if primary is not None:
            for index, value in enumerate(qpos):
                excursions[index].append(float(value))
            permutations["source_order_joint1_to_joint5"] = distance_m(primary, recorded_tcp)
            reversed_order = _fk(links, arm_names, list(reversed(qpos)), base_position, base_quaternion,
                                 tcp["parent_body"], tcp["position_m"])
            permutations["reversed"] = distance_m(reversed_order, recorded_tcp) if reversed_order else None
        entry = {"sample_id": anchor.get("sample_id"), "control_tick_id": tick,
                 "error_primary_m": distance_m(primary, recorded_tcp) if primary else None,
                 "difference_m": [primary[i] - recorded_tcp[i] for i in range(3)] if primary else None,
                 "error_with_base_offset_added_m": distance_m(alternative, recorded_tcp) if alternative else None,
                 "permutation_errors_m": permutations}
        compared.append(entry)
        base_positions.append([float(item) for item in base_position])

    errors = [item["error_primary_m"] for item in compared if item["error_primary_m"] is not None]
    alternatives = [item["error_with_base_offset_added_m"] for item in compared
                    if item["error_with_base_offset_added_m"] is not None]
    moved = {arm_names[index]: (min(values), max(values)) for index, values in enumerate(excursions) if values}
    unexercised = [name for name in arm_names if name not in moved]
    per_axis_bias = ([statistics.median([item["difference_m"][axis] for item in compared if item["difference_m"]])
                      for axis in range(3)] if errors else [])

    verdict = ("kinematic_consistency_holds" if errors and max(errors) <= TOLERANCE_M
               else "kinematic_consistency_fails" if errors else "insufficient_data")
    report = {
        "schema_version": "unirobot-mobilecar-history-fk-check-1",
        "read_only": True,
        "scope": {"run_id": args.run_id, "episode_id": args.episode_id,
                  "episode_directory": str(episode), "manifest_software": manifest.get("software"),
                  "anchors_in_episode": anchor_total, "anchors_sampled": len(anchors), "stride": stride,
                  "compared": len(compared),
                  "skipped": skipped},
        "identity": {"recorded": {key: manifest.get(key) for key in
                                  ("contract_version", "model_id", "model_sha256", "scene_id")},
                     "bundle": bundle.provenance.resource_identity.model_dump(),
                     "bundle_sha256": bundle.provenance.bundle_sha256,
                     "bundle_json_sha256": _sha(args.bundle / "bundle.json"),
                     "kinematics_config_sha256": _sha(args.kinematics_config),
                     "arm_names_in_bundle_document_order": bundle_arm_order,
                     "arm_names_in_platform_config_order": arm_names,
                     "orders_equal": bundle_arm_order == arm_names},
        "method": {"tree": "frozen compiled bundle links; body offset then joint motion in the child body frame",
                   "site_attachment": tcp, "site_attachment_authority": config.get("authority"),
                   "tolerance_m": TOLERANCE_M,
                   "tolerance_authority": "stated by this check; not a calibration limit"},
        "results": {"verdict": verdict,
                    "error_primary_m": _stats(errors),
                    "per_axis_median_difference_m": per_axis_bias,
                    "error_with_base_offset_added_m": _stats(alternatives),
                    "worst_sample": max(compared, key=lambda item: item["error_primary_m"] or 0.0,
                                        default=None),
                    "permutation_error_medians_m": {name: (statistics.median([item["permutation_errors_m"][name]
                                                                            for item in compared
                                                                            if item["permutation_errors_m"].get(name) is not None])
                                                            if any(item["permutation_errors_m"].get(name) is not None
                                                                   for item in compared) else None)
                                                    for name in ("source_order_joint1_to_joint5", "reversed")},
                    "joint_excursion_rad": {name: {"min": values[0], "max": values[1], "range": values[1] - values[0]}
                                            for name, values in moved.items()},
                    "unexercised_joints": unexercised,
                    "base_motion_observed_m": _spread_m(base_positions)},
        "supports": ["kinematic consistency between the recorded state, the frozen model tree and the declared "
                     "site attachment",
                     f"per-joint excursion coverage over {len(compared)} compared frames"],
        "does_not_prove": ["hardware or sensor calibration",
                           "that any specific native build wrote this archive: records carry no release or commit id",
                           "rendered appearance, and unexercised joints are not validated by this pass"],
        "limits": {"axes_declared_verified": [name for name, values in moved.items()
                                              if values[1] - values[0] > 1e-3],
                   "note": "an axis is only exercised where the samples actually move it; a consistent total error "
                           "with a static axis does not validate that axis on its own"},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": verdict, "compared": len(compared), "skipped": skipped,
                      "error": report["results"]["error_primary_m"],
                      "alternative": report["results"]["error_with_base_offset_added_m"],
                      "unexercised": unexercised, "orders_equal": report["identity"]["orders_equal"],
                      "out": str(args.out)}, ensure_ascii=False))
    return 0 if errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
