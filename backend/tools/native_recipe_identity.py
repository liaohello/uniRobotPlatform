"""Generate the pinned native config/scene digests used by the G1 recipe.

Run on the server inside the native MuJoCo environment, with the patched native
source on PYTHONPATH and the platform backend on PYTHONPATH for this file:

  PYTHONPATH=<native_release>/src python backend/tools/native_recipe_identity.py \
      --config <native_release>/configs/default.yaml \
      --backend-kind mujoco --require-recording \
      --out report/native-identity.json

The scene digest compiles the MuJoCo model only. MjData/mj_step/mj_forward are
replaced with a hard failure so this tool cannot advance or initialize physics.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mobilecar import attestation
from mobilecar.config import load_config


def forbidden(*args, **kwargs):
    raise AssertionError("physics state/stepping is forbidden in attestation generation")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--backend-kind", default="mujoco")
    parser.add_argument("--require-recording", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args()

    config = load_config(args.config)
    manifest = attestation.build_config_manifest(
        config,
        backend_kind=args.backend_kind,
        require_recording=True if args.require_recording else None,
    )
    for entry in manifest["config_files"]:
        if entry.get("external"):
            raise SystemExit(f"config source is outside the native root: {entry['path']}")
    import mujoco

    mujoco.MjData = forbidden
    mujoco.mj_step = forbidden
    mujoco.mj_forward = forbidden
    result = {
        "schema_version": "mobilecar-recipe-identity-1",
        "config_manifest": manifest,
        "config_manifest_sha256": attestation.config_manifest_digest(manifest),
        "scene_manifest_sha256": attestation.scene_manifest_digest(config),
        "runtime_environment": attestation.runtime_environment(),
        "physics_state_calls": 0,
    }
    body = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(body, encoding="utf-8")
    else:
        sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
