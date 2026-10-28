"""Build or verify a strict release identity for a candidate that is not yet deployed.

A release identity must fail loudly when a required path is missing. Hashing only
the files that happen to exist is how a candidate silently loses an execution module,
so this tool resolves a required set first and compares it against the tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "unirobot-release-identity-1"
EXTENDS = re.compile(r"^\s*extends\s*:\s*(\S.*?)\s*$", re.MULTILINE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_entries(entries: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def extends_closure(root: Path, entry_paths: list[str]) -> list[str]:
    """Follow every `extends:` chain reachable from the entry configs, in discovery order."""
    seen: list[str] = []
    queue = list(entry_paths)
    while queue:
        relative = queue.pop(0)
        if relative in seen:
            continue
        seen.append(relative)
        file = root / relative
        if not file.is_file():
            continue
        for target in EXTENDS.findall(file.read_text(encoding="utf-8")):
            target = target.strip("'\"")
            if target.startswith("/"):
                continue
            resolved = (file.parent / target).resolve()
            try:
                chain = resolved.relative_to(root.resolve()).as_posix()
            except ValueError:
                raise SystemExit(f"config extends escapes the release root: {relative} -> {target}")
            queue.append(chain)
    return seen


def required_paths(root: Path, spec: dict[str, Any], platform_root: Path) -> tuple[dict[str, list[str]], list[str], list[dict[str, str]]]:
    """Return {group: [paths]}, the declared exclusions, and any resolution faults."""
    groups: dict[str, list[str]] = {}
    faults: list[dict[str, str]] = []
    declared = spec.get("required_groups", {})

    baseline = declared.get("baseline_source")
    if baseline:
        pin = Path(baseline["pin_file"])
        if not pin.is_absolute():
            pin = platform_root / pin
        if not pin.is_file():
            faults.append({"group": "baseline_source", "path": str(pin), "fault": "pin file missing"})
        else:
            ignore = set(baseline.get("ignore_paths", []))
            listed = [entry["path"] for entry in json.loads(pin.read_text(encoding="utf-8"))["files"]]
            groups["baseline_source"] = [path for path in listed if path not in ignore]
    for group in ("patch_added_modules", "dependency_locks", "runtime_assets", "extra_required"):
        if group in declared:
            groups[group] = list(declared[group])
    configs = declared.get("execution_configs")
    if configs:
        try:
            groups["execution_configs"] = extends_closure(root, configs["entry_paths"])
        except SystemExit as exc:
            faults.append({"group": "execution_configs", "path": configs["entry_paths"][0], "fault": str(exc)})
    return groups, spec.get("excluded", []), faults


def excluded_prefixes(spec: dict[str, Any]) -> list[str]:
    return [item["prefix"] for item in spec.get("excluded", []) if item.get("kind", "prefix") == "prefix"]


def unlisted_under_required_roots(root: Path, required: set[str], spec: dict[str, Any]) -> list[str]:
    """Any file under a watched source root that the identity neither names nor declares excluded."""
    skip = [item["prefix"] for item in spec.get("excluded", [])]
    found: list[str] = []
    for pattern_root in spec.get("watched_roots", []):
        base = root / pattern_root
        if not base.is_dir():
            continue
        for file in sorted(base.rglob("*")):
            if not file.is_file():
                continue
            relative = file.relative_to(root).as_posix()
            if relative in required or any(relative.startswith(prefix) for prefix in skip) \
                    or "/__pycache__/" in f"/{relative}/" or relative.endswith((".pyc", ".pyo")):
                continue
            found.append(relative)
    return found


def build(root: Path, spec: dict[str, Any], platform_root: Path) -> tuple[dict[str, Any], int]:
    groups, excluded, faults = required_paths(root, spec, platform_root)
    entries: dict[str, str] = {}
    groups_out: dict[str, Any] = {}
    missing: list[dict[str, str]] = list({"group": "spec", "path": fault["path"], "fault": fault["fault"]} for fault in faults)
    for group, paths in sorted(groups.items()):
        present, absent = {}, []
        for relative in sorted(set(paths)):
            file = root / relative
            if file.is_file():
                present[relative] = sha256_file(file)
            else:
                absent.append(relative)
        entries.update(present)
        groups_out[group] = {"required": len(set(paths)), "hashed": len(present), "missing": absent}
        missing.extend({"group": group, "path": relative, "fault": "required path missing from release"} for relative in absent)
    complete = not missing
    report: dict[str, Any] = {
        "schema_version": SCHEMA,
        "candidate_id": spec["candidate_id"],
        "root": str(root),
        "root_kind": spec.get("root_kind"),
        "baseline": spec.get("baseline", {}),
        "digest_format": spec.get("digest_format",
                                'sha256 of UTF-8 json.dumps({path: sha256}, sort_keys=True, separators=(",",":"))'),
        "groups": groups_out,
        "excluded": excluded,
        "unique_required_count": len({path for group in groups.values() for path in group}),
        "group_entry_total": sum(item["required"] for item in groups_out.values()),
        "watched_roots": spec.get("watched_roots", []),
        "unlisted_under_watched_roots": unlisted_under_required_roots(root, set(entries), spec),
        "required_count": len({path for group in groups.values() for path in group}),
        "hashed_count": len(entries),
        "missing_required": missing,
        "complete": complete,
    }
    if complete:
        report["release_digest"] = digest_entries(entries)
        report["entries"] = dict(sorted(entries.items()))
    report["count_invariant"] = {"hashed_count_equals_entries": report.get("hashed_count") == len(entries),
                                 "aggregate_covers_all_hashed": complete}
    return report, (0 if complete else 2)


def verify(root: Path, manifest: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Recompute the manifest against a tree and report added, removed and changed paths."""
    recorded = manifest.get("entries", {})
    actual: dict[str, str] = {}
    removed = []
    for relative, digest in sorted(recorded.items()):
        file = root / relative
        if not file.is_file():
            removed.append(relative)
            continue
        value = sha256_file(file)
        actual[relative] = value
    changed = [relative for relative, digest in recorded.items()
               if relative in actual and actual[relative] != digest]
    recomputed = digest_entries(actual) if len(actual) == len(recorded) else None
    ok = not removed and not changed and recomputed == manifest.get("release_digest")
    return {"schema_version": SCHEMA, "candidate_id": manifest.get("candidate_id"), "root": str(root),
            "recorded_count": len(recorded), "present_count": len(actual), "removed_paths": removed,
            "changed_paths": changed, "recomputed_release_digest": recomputed,
            "expected_release_digest": manifest.get("release_digest"), "match": ok}, (0 if ok else 2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--spec", type=Path, help="identity spec (build)")
    parser.add_argument("--platform-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path, help="recorded manifest (verify)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.root.is_dir():
        raise SystemExit(f"release root is not a directory: {args.root}")
    if args.mode == "build":
        if not args.spec:
            raise SystemExit("build needs --spec")
        report, code = build(args.root, json.loads(args.spec.read_text(encoding="utf-8")), args.platform_root)
    else:
        if not args.manifest:
            raise SystemExit("verify needs --manifest")
        report, code = verify(args.root, json.loads(args.manifest.read_text(encoding="utf-8")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k != "entries"}, default=str)[:1200])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
