"""Launch ONE gateway exposing every unified-candidate surface from one frozen source.

Geometry-2 read, capabilities/snapshot/kinematics, Map/Route resources, draft/validate,
Session envelope plus read-only current, and the M1.4 STOP/end schema all come from the
same process and the same startup manifest. Every input path is required: a missing
geometry bundle, map package, catalog or recipe refuses the launch instead of quietly
serving a reduced candidate.

Execution qualification is a separate question from geometry read compatibility. This
launcher never relaxes a pin and never rewrites the recipe: whatever the recipe requires
and whatever native declares is what the candidate answers with.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
from pathlib import Path
from typing import Any

import uvicorn

from source_digest import SOURCE_ROOTS, digest_tree

from unirobot.api import create_app
from unirobot.mobilecar import MobileCarIntegration
from unirobot.catalog import load_catalog
from unirobot.recipe import load_recipe
from unirobot.settings import BACKEND_ROOT, CONFIG_PATH


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        return probe.connect_ex((host, port)) != 0


def require(path: Path, label: str) -> Path:
    if not path.exists():
        raise SystemExit(f"{label} is missing: {path}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--catalog", type=Path, default=CONFIG_PATH)
    parser.add_argument("--native-url", default=None,
                        help="override the catalog base_url; the gateway only sends GET to native")
    parser.add_argument("--geometry-bundle", type=Path, required=True)
    parser.add_argument("--map-catalog", type=Path, required=True)
    parser.add_argument("--maps-root", type=Path, required=True)
    parser.add_argument("--draft-db", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, default=BACKEND_ROOT / "config" / "mobilecar-g1-recipe-v2.json")
    parser.add_argument("--history-source", type=Path, default=BACKEND_ROOT / "config" / "mobilecar-history-source.json",
                        help="frozen declaration of ONE historical source and its recording root")
    parser.add_argument("--episode-root", type=Path, default=None,
                        help="override the declared recording root, e.g. an isolated fixture copy")
    parser.add_argument("--out-manifest", type=Path, required=True)
    parser.add_argument("--allow-existing-db", action="store_true",
                        help="reuse a candidate database deliberately; off by default so an earlier namespace is never overwritten")
    args = parser.parse_args()

    if not port_is_free(args.host, args.port):
        raise SystemExit(f"refusing to start: {args.host}:{args.port} is already listening")
    catalog_path = require(args.catalog, "catalog")
    bundle = require(args.geometry_bundle, "geometry bundle")
    map_catalog = require(args.map_catalog, "map catalog")
    maps_root = require(args.maps_root, "maps root")
    recipe_path = require(args.recipe, "recipe")
    if args.draft_db.exists() and not args.allow_existing_db:
        raise SystemExit(f"refusing to overwrite an existing database: {args.draft_db}")
    database_existed_before = args.draft_db.exists()
    args.draft_db.parent.mkdir(parents=True, exist_ok=True)

    recipe = load_recipe(recipe_path)
    integration = None
    if args.native_url:
        entry = load_catalog(catalog_path).adapters["mobilecar"]
        integration = MobileCarIntegration(entry.model_copy(update={"base_url": args.native_url}))

    require(bundle / "bundle.json", "geometry bundle manifest")
    assets = sorted((bundle / "assets").glob("*.stl"))
    if not args.history_source.is_file():
        raise SystemExit(f"history source declaration is missing: {args.history_source}")
    application = create_app(catalog_path=catalog_path, draft_db_path=args.draft_db,
                             compiled_geometry_path=bundle, recipe=recipe,
                             map_catalog_path=map_catalog, maps_root=maps_root,
                             mobilecar_integration=integration,
                             history_source_path=args.history_source, episode_root=args.episode_root)
    history = application.state.history_unavailable or {}
    archive = application.state.episodes

    manifest = {
        "candidate": "unified-platform-candidate",
        "listen": {"host": args.host, "port": args.port, "was_free_before_start": True},
        "platform_source": {"backend_root": str(BACKEND_ROOT), "roots": list(SOURCE_ROOTS),
                            **digest_tree(BACKEND_ROOT, SOURCE_ROOTS)},
        "geometry_bundle": {"path": str(bundle), "bundle_json": str(bundle / "bundle.json"),
                            "bundle_json_sha256": sha256(bundle / "bundle.json"),
                            "asset_count": len(assets),
                            "assets_sha256": {item.name: sha256(item) for item in assets}},
        "maps": {"catalog": str(map_catalog), "catalog_sha256": sha256(map_catalog), "root": str(maps_root),
                 "packages": sorted(item.name for item in maps_root.iterdir() if item.is_dir())},
        "recipe": {"path": str(recipe_path), "sha256": sha256(recipe_path), "recipe_id": recipe.recipe_id,
                   "revision": recipe.revision, "fingerprint": recipe.fingerprint,
                   "required_protocols": getattr(recipe, "required_protocols", None)
                   or recipe.body.get("required_protocols", {})},
        "native": {"catalog": str(catalog_path), "base_url": args.native_url or "from catalog",
                   "gateway_access": "GET only; no write request is sent to any native instance by this launch"},
        "history": {
            "source_file": str(args.history_source),
            "source_file_sha256": sha256(args.history_source),
            "configured": archive is not None,
            "source_id": archive.source.source_id if archive else None,
            "resolved_recording_root": str(archive.root) if archive else None,
            "root_override": str(args.episode_root) if args.episode_root else None,
            "declared_scale": archive.source.declared_scale if archive else None,
            "access": "read_only_files; the platform never writes, moves or re-exports the recordings",
            "unavailable_reason": history or None,
        },
        "database": {"path": str(args.draft_db), "existed_before": database_existed_before,
                     "namespace_note": "isolated file; no earlier candidate SQLite is read or replaced"},
        "scene_read_contract": "unirobot-mobilecar-geometry-2",
        "qualification_note": "geometry-2 read compatibility is not profile/readiness qualification; "
                              "prepared/Start/begin/STOP/end keep refusing with their real codes until native declares the protocols",
    }
    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in manifest.items() if key != "platform_source"},
                     default=str)[:900], flush=True)
    uvicorn.Server(uvicorn.Config(application, host=args.host, port=args.port, log_level="warning")).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
