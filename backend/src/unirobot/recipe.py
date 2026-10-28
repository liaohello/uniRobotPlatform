"""Self-verifying execution recipe: fixed preset, dependencies, protocols, kinematics.

The recipe is the only place that states what a validated snapshot is allowed to
mean. It is content-addressed so a draft, a snapshot and a prepared Session can
all name the exact same execution definition without re-reading mutable files.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .settings import BACKEND_ROOT

RECIPE_PATH = BACKEND_ROOT / "config" / "mobilecar-g1-recipe-v2.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


class RecipeError(RuntimeError):
    """The configured recipe or one of its declared sources is inconsistent."""


class Recipe:
    def __init__(self, body: dict, sources: list[dict], pin: dict) -> None:
        self.body = body
        self.fingerprint = digest(body)
        self.sources = sources
        self.pin = pin

    @property
    def recipe_id(self) -> str:
        return self.body["recipe_id"]

    @property
    def revision(self) -> int:
        return self.body["recipe_revision"]

    @property
    def expected(self) -> dict:
        return self.body["expected"]

    @property
    def kinematics(self) -> dict:
        return self.body["kinematics"]["body"]

    @property
    def kinematics_digest(self) -> str:
        return self.body["kinematics"]["digest"]

    @property
    def required_protocols(self) -> dict:
        return self.body["required_protocols"]

    def document(self) -> dict:
        """Public recipe view; the hashed body stays internal but its digest does not."""
        return {
            "schema_version": "unirobot-execution-recipe-1",
            "recipe_id": self.recipe_id,
            "recipe_revision": self.revision,
            "recipe_fingerprint": self.fingerprint,
            "preset": self.body["preset"],
            "expected": self.expected,
            "native": self.body["native"],
            "dependencies": self.body["dependencies"],
            "required_protocols": self.required_protocols,
            "kinematics": {"profile_id": self.kinematics["profile_id"], "digest": self.kinematics_digest},
            "sources": self.sources,
            "attestation": self.body["attestation"],
        }


def _read_declared(relative: str, expected_sha256: str, root: Path = BACKEND_ROOT) -> bytes:
    path = (root / relative).resolve()
    if root.resolve() not in path.parents:
        raise RecipeError(f"recipe source escapes the backend root: {relative}")
    if not path.is_file():
        raise RecipeError(f"recipe source is missing: {relative}")
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != expected_sha256:
        raise RecipeError(f"recipe source digest mismatch: {relative}")
    return body


def _parse_lock(body: bytes) -> dict[str, str]:
    """Read the exact ``name==version`` pins; the digest covers the whole file."""
    packages: dict[str, str] = {}
    for line in body.decode("utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s=]+)", value)
        if match is None:
            raise RecipeError(f"requirements lock has an unsupported line: {value}")
        name, version = match.groups()
        if name in packages:
            raise RecipeError(f"requirements lock repeats a package: {name}")
        packages[name] = version
    if not packages:
        raise RecipeError("requirements lock declares no packages")
    return packages


def load_recipe(path: Path = RECIPE_PATH, *, root: Path = BACKEND_ROOT) -> Recipe:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 2:
        raise RecipeError("unsupported execution recipe version")
    pin_body = _read_declared(raw["preset_source"]["path"], raw["preset_source"]["sha256"], root)
    kinematics_body = _read_declared(raw["kinematics_source"]["path"], raw["kinematics_source"]["sha256"], root)
    lock = raw["dependencies"]["requirements_lock"]
    lock_source = lock["source"]
    lock_release_path = lock["release_file"]["path"]
    lock_body = _read_declared(lock_release_path, lock_source["sha256"], root)
    lock_packages = _parse_lock(lock_body)
    if lock_packages != lock["packages"]:
        raise RecipeError("requirements lock bytes and the declared package pins differ")
    pin = json.loads(pin_body)
    kinematics = json.loads(kinematics_body)
    if pin.get("schema_version") != 1 or kinematics.get("schema_version") != 1:
        raise RecipeError("unsupported preset or kinematics manifest version")
    if pin["preset_id"] != raw["recipe_id"]:
        raise RecipeError("recipe id does not match the pinned preset")

    native_attestation = raw.get("native_attestation") or {}
    for key in ("config_manifest_sha256", "scene_manifest_sha256"):
        value = native_attestation.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise RecipeError(f"recipe does not pin native_attestation.{key}")

    declared = pin["expected"]
    expected = {
        "contract_version": declared["contract_version"],
        "backend_kind": declared["backend_kind"],
        "interface_profile": declared["interface_profile"],
        "model_id": declared["model_id"],
        "model_sha256": declared["model_sha256"],
        "scene_id": declared["scene_id"],
        # The pinned scene digest is the scene XML file digest from the native
        # manifest. Native HTTP exposes neither the file nor a manifest digest,
        # so this value can never be checked over the wire.
        "scene_file_sha256": declared["scene_content_sha256"],
        "scene_file_digest_scope": "scene XML file digest from the native file manifest; not observable through native HTTP",
        "commands": list(declared["commands"]),
        "sensor_streams": list(declared["sensor_streams"]),
        "config_manifest_sha256": native_attestation["config_manifest_sha256"],
        "scene_manifest_sha256": native_attestation["scene_manifest_sha256"],
        "config_manifest_scope": native_attestation.get("config_manifest_scope"),
        "scene_manifest_scope": native_attestation.get("scene_manifest_scope"),
    }
    body = {
        "recipe_id": raw["recipe_id"],
        "recipe_revision": raw["recipe_revision"],
        "preset": {
            key: pin["recipe"][key]
            for key in (
                "argv", "env", "config_path", "effective_overrides", "execution_location",
                "editable_initial_state_fields", "execution_sources", "recording_profile", "action_profile",
            )
        },
        "expected": expected,
        "native": {
            "commit": pin["native_commit"],
            "worktree_status": pin["native_worktree_status"],
            "manifest_sha256": pin["manifest_sha256"],
            "manifest_digest_format": pin["manifest_digest_format"],
        },
        "dependencies": {
            "python": raw["dependencies"]["python"],
            "requirements_lock": {
                "source": dict(lock_source),
                "release_file": {
                    "path": lock_release_path,
                    "sha256": hashlib.sha256(lock_body).hexdigest(),
                    "size_bytes": len(lock_body),
                },
                "packages": lock_packages,
                "verification": {
                    "release_file_bytes_read": True,
                    "source_digest_matches": True,
                    "package_pins_match_file": True,
                    "runtime_environment": "not checked at platform startup; native runtime_package_versions is checked at readiness",
                },
            },
        },
        "required_protocols": raw["required_protocols"],
        "kinematics": {"profile_id": kinematics["profile_id"], "digest": digest(kinematics), "body": kinematics},
        "native_attestation": {
            "generated_by": native_attestation.get("generated_by"),
            "generated_from": native_attestation.get("generated_from"),
        },
        "attestation": {
            "declared_by": "platform_local_pin",
            "native_attested": False,
            "limitations": [
                "Preset, dependency and model identity are local expectations; native HTTP does not attest the deployed source tree",
                "The pinned scene digest covers the scene XML file only, not the compiled scene manifest served by the running process",
                "The requirements lock is verified as a pinned release file, not read from the live native environment",
                "Runtime package versions are a native self-report and are checked against the lock; they are not a platform-side environment inspection",
                "Kinematics constants come from source files, not from a native capability endpoint",
            ],
        },
    }
    sources = [
        {"role": "preset_pin", "path": raw["preset_source"]["path"], "sha256": raw["preset_source"]["sha256"]},
        {"role": "kinematics", "path": raw["kinematics_source"]["path"], "sha256": raw["kinematics_source"]["sha256"]},
        {"role": "dependencies", "path": lock_release_path, "sha256": hashlib.sha256(lock_body).hexdigest()},
    ]
    return Recipe(body=body, sources=sources, pin=pin)


def derived_user_limits(kinematics: dict, model_limits: list[list[float]]) -> list[list[float]]:
    """Native's own mapping, recomputed from the profile, for an independent cross-check."""
    zero = kinematics["arm"]["zero_model_rad"]
    direction = kinematics["arm"]["user_direction"]
    if len(zero) != len(direction) or len(model_limits) != len(zero):
        raise RecipeError("kinematics and native limit arrays do not share joint order")
    limits = []
    for (low, high), z, d in zip(model_limits, zero, direction):
        first, second = (low - z) * d, (high - z) * d
        limits.append([min(first, second), max(first, second)])
    return limits
