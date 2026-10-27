"""Read-only mobileCar compatibility checks; never acquires control or records."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, Field, StrictBool, StrictInt, StrictStr, ValidationError

from .contracts import AdapterConfig, utc_now
from .settings import BACKEND_ROOT, PROBE_TIMEOUT_S

PIN_PATH = BACKEND_ROOT / "config" / "mobilecar-g1-source.json"
READ_PATHS = (
    "/api/v1/health",
    "/api/v1/capabilities",
    "/api/v1/scene",
    "/api/v1/snapshot",
)
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class RuntimeIdentity(BaseModel):
    run_id: StrictStr = Field(min_length=1)
    backend_generation: StrictInt = Field(ge=1)
    episode_id: StrictStr = Field(min_length=1)


class Health(RuntimeIdentity):
    status: Literal["ok"]
    recording_required_for_motion: StrictBool
    interface_profile: StrictStr


class SceneIdentity(BaseModel):
    contract_version: Literal["mobilecar-1.0"]
    model_id: StrictStr
    model_sha256: StrictStr = Field(pattern=r"^[0-9a-f]{64}$")
    scene_id: StrictStr


class Capabilities(SceneIdentity):
    backend_kind: StrictStr
    supported_commands: list[StrictStr]
    sensor_streams: list[StrictStr]


class RecordingState(BaseModel):
    status: Literal["IDLE", "STARTING", "RECORDING", "DRAINING", "COMPLETE", "FAILED"]
    command_capture_ready: StrictBool
    recording_segment_id: StrictStr | None


class Snapshot(RuntimeIdentity):
    contract_version: Literal["mobilecar-1.0"]
    recording: RecordingState
    base_owner_session_id: StrictStr | None
    arm_owner_session_id: StrictStr | None


class NativeReadError(RuntimeError):
    def __init__(self, status: str, detail: str) -> None:
        super().__init__(detail)
        self.status = status


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward configured credentials to another service.
        return None


class MobileCarIntegration:
    def __init__(
        self,
        config: AdapterConfig | None,
        *,
        pin_path: Path = PIN_PATH,
    ) -> None:
        self.config = config
        self.pin = json.loads(pin_path.read_text(encoding="utf-8"))
        if self.pin["schema_version"] != 1:
            raise ValueError("unsupported mobileCar source manifest version")
        self._opener = urllib.request.build_opener(_RejectRedirects())

    def _read(self, path: str) -> dict[str, Any]:
        if path not in READ_PATHS:
            raise ValueError(f"not a mobileCar preflight read path: {path}")
        if self.config is None or not self.config.base_url:
            raise NativeReadError("not_configured", "mobileCar service URL is not configured")
        url = self.config.base_url.rstrip("/") + path
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        if self.config.auth_env:
            token = os.environ.get(self.config.auth_env)
            if token:
                request.add_header("Authorization", f"Bearer {token}")
        try:
            with self._opener.open(request, timeout=PROBE_TIMEOUT_S) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise NativeReadError("error", f"{path}: HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise NativeReadError("offline", f"{path}: service unreachable or timed out") from exc
        if len(body) > MAX_RESPONSE_BYTES:
            raise NativeReadError("error", f"{path}: JSON response exceeds size limit")
        try:
            value = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NativeReadError("incompatible", f"{path}: invalid UTF-8 JSON") from exc
        if not isinstance(value, dict):
            raise NativeReadError("incompatible", f"{path}: expected a JSON object")
        return value

    def check(self) -> dict[str, Any]:
        checks: list[dict[str, str]] = []

        def add(key: str, status: str, detail: str) -> None:
            checks.append({"key": key, "status": status, "detail": detail})

        def compare(key: str, accepted: bool, detail: str) -> None:
            add(key, "passed" if accepted else "failed", detail)

        result: dict[str, Any] = {
            "schema_version": "mobilecar-integration-1",
            "task_id": self.pin["preset_id"],
            "checked_at": utc_now(),
            "read_only": True,
            "session_ready": False,
            "read_contract_compatible": False,
            "verification_scope": "Only the checked fields of four native GET responses; not full scene/config/assets or deployed-source verification",
            "transport": "not_configured",
            "runtime_identity": None,
            "native_resource_identity": None,
            "recording": None,
            "preset": {
                key: self.pin[key]
                for key in ("preset_id", "native_commit", "manifest_sha256", "recipe", "expected")
            },
            "checks": checks,
        }
        models = (Health, Capabilities, SceneIdentity, Snapshot)
        values: list[BaseModel] = []
        transport = "online"
        for path, model in zip(READ_PATHS, models):
            try:
                value = model.model_validate(self._read(path))
            except NativeReadError as exc:
                transport = exc.status
                add(path, "failed", str(exc))
                break
            except ValidationError as exc:
                transport = "incompatible"
                fields = ", ".join(".".join(map(str, e["loc"])) for e in exc.errors())
                add(path, "failed", f"native contract mismatch: {fields}")
                break
            add(path, "passed", "Read-only response received and required fields checked")
            values.append(value)
        for path in READ_PATHS[len(checks):]:
            add(path, "not_checked", "An earlier native read failed")
        result["transport"] = transport

        if len(values) == len(READ_PATHS):
            health = cast(Health, values[0])
            capabilities = cast(Capabilities, values[1])
            scene = cast(SceneIdentity, values[2])
            snapshot = cast(Snapshot, values[3])
            expected = self.pin["expected"]
            identity_fields = ("run_id", "backend_generation", "episode_id")
            identity = {key: getattr(snapshot, key) for key in identity_fields}
            result["runtime_identity"] = identity
            result["native_resource_identity"] = {
                "model_id": capabilities.model_id,
                "model_sha256": capabilities.model_sha256,
                "scene_id": capabilities.scene_id,
                "backend_kind": capabilities.backend_kind,
                "interface_profile": health.interface_profile,
            }
            result["recording"] = snapshot.recording.model_dump()
            compare("runtime_identity", identity == {key: getattr(health, key) for key in identity_fields},
                    "health and snapshot must name the same run/generation/episode; recheck after a reset or restart")
            for key in ("model_id", "model_sha256", "scene_id"):
                compare(key, getattr(capabilities, key) == getattr(scene, key) == expected[key],
                        f"capabilities={getattr(capabilities, key)}; scene={getattr(scene, key)}; expected {key}={expected[key]}")
            compare("backend_kind", capabilities.backend_kind == expected["backend_kind"],
                    "The physical M1 preset requires the MuJoCo backend; mock is insufficient")
            compare("interface_profile", health.interface_profile == expected["interface_profile"],
                    f"Native interface profile={health.interface_profile}; expected={expected['interface_profile']}")
            compare("recording_gate", health.recording_required_for_motion is True,
                    "The selected recipe must require recording before motion")
            compare("human_commands", set(expected["commands"]).issubset(capabilities.supported_commands),
                    "Native must declare the preset's human control and safety commands")
            compare("declared_streams", set(expected["sensor_streams"]).issubset(capabilities.sensor_streams),
                    "Checks advertised stream support only; fresh persisted samples are not verified")
            result["read_contract_compatible"] = all(c["status"] == "passed" for c in checks)

        # These guarantees are absent from the pinned native protocol. A healthy
        # service, matching model, or capture_ready flag cannot supply them.
        add("deployed_source_and_config", "not_checked",
            "Native HTTP does not attest the full source/config/asset manifest; local pin is expected content only")
        add("prepared_session_and_start", "unsupported",
            "Pinned native protocol has no non-motion Session binding and explicit Start; episodes/start performs RESET and recording")
        add("recording_reset_applied", "unsupported",
            "Native start accepts RESET RECEIVED/DISPATCHED before taking the initial snapshot; applied identity needs confirmation")
        add("parking_receipt", "unsupported",
            "Native stop finalizes after parking feedback or timeout without a separate parking result in its response")
        return result
