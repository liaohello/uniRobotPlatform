"""Single-source digest of the platform's own runnable bytes.

The launcher freezes this map into the startup manifest; the check tools recompute it
from the tree they are actually running against and refuse to pass when the manifest
and the bytes disagree. Keeping one implementation is what makes
"manifest == bytes == tools == report" checkable instead of asserted.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SOURCE_ROOTS = ("src/unirobot", "config", "tools")
SUFFIXES = {".py", ".json", ".yaml", ".html", ".js", ".css"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_tree(root: Path, relative_roots: tuple[str, ...] = SOURCE_ROOTS) -> dict[str, Any]:
    entries: dict[str, str] = {}
    for part in relative_roots:
        base = root / part
        if not base.is_dir():
            raise SystemExit(f"platform source root is missing: {base}")
        for file in sorted(base.rglob("*")):
            if file.is_file() and file.suffix in SUFFIXES and "__pycache__" not in file.parts:
                entries[file.relative_to(root).as_posix()] = sha256(file)
    aggregate = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"file_count": len(entries), "aggregate": aggregate, "files": entries}


def bind(release_backend: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Compare the running tree against a startup manifest's recorded platform source."""
    actual = digest_tree(release_backend)
    recorded = manifest.get("platform_source") or {}
    differences = sorted(
        path for path in set(actual["files"]) | set(recorded.get("files") or {})
        if actual["files"].get(path) != (recorded.get("files") or {}).get(path)
    )
    return {
        "recorded_aggregate": recorded.get("aggregate"),
        "recomputed_aggregate": actual["aggregate"],
        "recorded_file_count": recorded.get("file_count"),
        "recomputed_file_count": actual["file_count"],
        "match": recorded.get("aggregate") == actual["aggregate"],
        "changed_or_missing_paths": differences,
    }
