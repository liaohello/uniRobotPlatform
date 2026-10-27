"""Paths and runtime switches for the gateway."""

from __future__ import annotations

import os
from pathlib import Path


def _find_repo_root() -> Path:
    override = os.environ.get("UNIROBOT_REPO_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / "docs" / "specs" / "catalog.json").is_file():
            return parent
    return Path.cwd().resolve()


REPO_ROOT = _find_repo_root()
BACKEND_ROOT = REPO_ROOT / "backend"
CONFIG_PATH = Path(
    os.environ.get("UNIROBOT_CATALOG", BACKEND_ROOT / "config" / "catalog.yaml")
).expanduser()
MIGRATION_MANIFEST = BACKEND_ROOT / "migration_manifest.json"

ALLOW_LAUNCH = os.environ.get("UNIROBOT_ALLOW_LAUNCH", "0") == "1"
PROBE_TIMEOUT_S = float(os.environ.get("UNIROBOT_PROBE_TIMEOUT", "0.6"))
DRAFT_DB_PATH = Path(os.environ.get("UNIROBOT_DRAFT_DB", BACKEND_ROOT / "var" / "drafts.sqlite3")).expanduser()
