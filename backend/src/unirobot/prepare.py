"""Motion-free configuration validation and Session preparation.

Nothing in this module moves the robot, resets an Episode or starts a recording.
Validation only issues GET reads. A prepared Session is created only after a
native binding is prepared and read back; the pinned native protocol has no such
capability, so live creation is refused with an explicit blocking reason rather
than simulated with a platform-local flag.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, StrictStr, ValidationError

from .contracts import Contract, utc_now
from .mobilecar import Health, MobileCarIntegration, NativeReadError, RuntimeIdentity, SceneIdentity
from .mobilecar_read import CapabilitiesData, MobileCarReadService, NativeSnapshot, ReadServiceError, SceneData
from .recipe import Recipe, RecipeError, canonical, derived_user_limits, digest

BINDING_TIMEOUT_S = 3.0
# A native STOP/end call waits for the parking proof and the Recorder drain inside one
# lifecycle critical section, so it cannot reuse the 3s read timeout.
LIFECYCLE_WRITE_TIMEOUT_S = 45.0
LIFECYCLE_RECEIPT_HISTORY = 16
TOLERANCE = 1e-9
BINDING_PATHS = (
    "/api/v1/session/prepare",
    "/api/v1/session/start",
    "/api/v1/session/release",
    "/api/v1/session/stop",
)
RECORDING_BEGIN_PATH = "/api/v1/recording/begin"
RECORDING_END_PATH = "/api/v1/recording/end"
SESSION_STOP_PATH = "/api/v1/session/stop"


class CapabilitiesWithAttestation(CapabilitiesData):
    """Read projection plus optional native attestations; absent means not attested."""

    config_manifest_sha256: StrictStr | None = None
    scene_manifest_sha256: StrictStr | None = None
    session_binding_protocol: StrictStr | None = None
    recording_begin_protocol: StrictStr | None = None
    session_stop_protocol: StrictStr | None = None
    recording_end_protocol: StrictStr | None = None
    runtime_python_version: StrictStr | None = None
    runtime_package_versions: dict[str, StrictStr] | None = None


class Check(Contract):
    key: str
    status: Literal["passed", "failed", "unsupported", "not_checked"]
    phase: Literal["configuration", "readiness"]
    scope: str
    detail: str


class BlockingReason(Contract):
    key: str
    scope: Literal["configuration", "readiness"]
    message: str


class Observation(Contract):
    runtime_identity: RuntimeIdentity
    resource_identity: SceneIdentity
    backend_kind: str
    interface_profile: str
    recording_required_for_motion: bool
    supported_commands: list[str]
    sensor_streams: list[str]
    config_manifest_attestation: str | None
    scene_manifest_attestation: str | None
    session_binding_protocol: str | None
    recording_begin_protocol: str | None
    session_stop_protocol: str | None
    recording_end_protocol: str | None
    runtime_python_version: str | None
    runtime_package_versions: dict[str, str] | None
    scene_manifest_sha256: str
    arm_joint_names: list[str]
    arm_user_limits_rad: list[list[float]]
    model_limits_rad: list[list[float]]
    gripper_min_width_m: float
    gripper_max_width_m: float
    tcp_parent_body: str
    tcp_site: str
    camera_parent_body: str
    recording_status: str
    recording_episode_id: str | None
    recording_segment_id: str | None
    recording_command_capture_ready: bool
    recording_error: str | None
    base_owner_session_id: str | None
    arm_owner_session_id: str | None
    active_session_id: str | None
    safety_latched: bool


class KinematicsEvidence(Contract):
    profile_id: str
    digest: str
    authority: str
    joint_order_consistent: bool
    user_limits_consistent: bool
    tcp_mount_consistent: bool
    camera_mount_consistent: bool
    gripper_limits_consistent: bool
    max_user_limit_error_rad: float
    limitations: list[str]


class ConfigurationSnapshot(Contract):
    schema_version: Literal["unirobot-config-snapshot-1"] = "unirobot-config-snapshot-1"
    snapshot_id: str
    snapshot_sha256: str
    created_at: str
    draft_id: str
    draft_revision: int
    execution_revision: int
    fingerprint: str
    recipe_fingerprint: str
    recipe: dict
    observation: Observation
    kinematics: KinematicsEvidence
    checks: list[Check]
    validation_status: Literal["passed", "failed"]
    validation_scope: Literal["motion_free_configuration_and_declared_protocol_only"]
    execution_eligible: bool
    validated_snapshot_id: str | None
    blocking_reasons: list[BlockingReason]


class NativeBinding(Contract):
    status: Literal["unverified", "verified", "unsupported"]
    protocol: str
    binding_id: str | None = None
    native_session_id: str | None = None
    config_fingerprint: str | None = None
    expires_at_backend_monotonic_s: float | None = None
    verified_at: str | None = None
    readback_sha256: str | None = None
    reason: str | None = None


class StartBlock(Contract):
    key: str
    scope: Literal["platform", "native", "recording"]
    message: str


class StartAttempt(Contract):
    at: str
    result: Literal["refused", "started", "failed"]
    blocking: list[StartBlock]
    detail: str = ""


class StartReceipt(Contract):
    binding_id: str
    native_session_id: str
    run_id: str
    backend_generation: int
    episode_id: str
    config_fingerprint: str
    started_at_backend_monotonic_s: float
    control_scope_granted: list[str]
    recording_required_for_motion: bool
    recording_begin_required: bool
    owner_state: str
    owner_session_id: str | None
    lease_expires_at_backend_monotonic_s: float | None
    recording_ready: bool
    motion_ready: bool
    motion_blockers: list[str]


class OwnerLease(Contract):
    state: Literal["not_acquired", "held", "unknown"]
    session_id: str | None
    lease_expires_at_backend_monotonic_s: float | None


class SessionExecution(Contract):
    control_scope_granted: list[str]
    owner: OwnerLease
    recording_required_for_motion: bool
    recording_begin_required: bool
    recording_ready: bool
    motion_ready: bool
    motion_blockers: list[str]
    observed_at: str
    source: Literal["prepared", "native_start", "native_recording_begin", "native_recording_end"]


class RecordingBeginReceipt(Contract):
    binding_id: str
    native_session_id: str
    run_id: str
    backend_generation: int
    episode_id: str
    config_fingerprint: str
    recording_segment_id: str
    recording_status: str
    command_capture_ready: bool
    recording_start_event_seq: int
    initial_snapshot_sha256: str
    durable_start_records: bool
    started_at_backend_monotonic_s: float


class RecordingAttempt(Contract):
    at: str
    result: Literal["begun", "refused", "failed"]
    reason: str = ""


class StopAttempt(Contract):
    at: str
    request_id: str
    result: Literal["stopped", "refused", "result_unknown"]
    code: str = ""
    reason: str = ""


class RecordingEndAttempt(Contract):
    at: str
    request_id: str
    result: Literal["ended", "refused", "result_unknown"]
    code: str = ""
    reason: str = ""


class StopDispatchView(Contract):
    dispatched: bool
    command_id: str | None
    status: str
    status_detail: str


class ParkingEvidenceView(Contract):
    confirmed: bool
    waited_ms: int
    timeout_ms: int
    base_stopped: bool | None
    base_stop_latched: bool | None
    base_velocity_m_s: list[float]
    arm_max_joint_velocity_rad_s: float | None
    control_tick_id: str | None
    observed_at_backend_monotonic_s: float | None
    scope_coverage: dict[str, str]
    observed_confirmed: bool
    coverage_complete: bool
    coverage_note: str


class RecordingDrainView(Contract):
    completed: bool
    fanout_drained: bool
    recorder_queue_empty: bool
    queued_events: int
    dropped_events: int


class RecordingFinalizeView(Contract):
    completed: bool
    error: str | None
    terminal_event_written: bool
    complete_tail: bool
    recording_status: str
    audit_status: str
    event_count: int | None
    dropped_events: int | None
    storage_ref: str | None
    episode_complete_sha256: str | None
    checksummed_artifacts: int
    preserved_records: bool


class StopReceipt(Contract):
    """One native m1-stop-1 answer; parking.coverage_complete is the only whole-robot proof."""

    accepted: bool
    code: str
    reason: str = ""
    protocol: StrictStr
    request_id: str
    replayed: bool
    binding_id: str | None
    session_id: str | None
    config_fingerprint: str | None
    run_id: str
    backend_generation: int
    episode_id: str
    dispatch: StopDispatchView
    parking: ParkingEvidenceView
    owner_cleared_after_stop: bool
    safety_latched: bool
    recording_status: str
    recording_segment_id: str | None
    recording_touched: Literal[False]
    motion_restored: Literal[False]
    observed_at: str


class RecordingEndReceipt(Contract):
    """One native m1-end-1 answer with the five layers kept separately."""

    accepted: bool
    code: str
    reason: str = ""
    protocol: StrictStr
    request_id: str
    replayed: bool
    binding_id: str
    session_id: str
    config_fingerprint: str
    run_id: str
    backend_generation: int
    episode_id: str
    recording_segment_id: str | None
    active_segment_id: str | None
    binding_state: str
    dispatch: StopDispatchView
    parking: ParkingEvidenceView
    drain: RecordingDrainView
    finalize: RecordingFinalizeView
    integrity: Literal["complete", "incomplete_terminal_recorded",
                       "finalize_failed_missing_tail", "unknown"]
    recording_status: str
    safety_latched: bool
    reset_issued: Literal[False]
    safety_cleared: Literal[False]
    owner_acquired: Literal[False]
    observed_at: str


class BeginRecording(Contract):
    operator_id: StrictStr = Field(min_length=1)
    view_source: StrictStr = Field(default="third_person_3d", min_length=1)


class StopSession(Contract):
    request_id: StrictStr = Field(min_length=1, max_length=128)
    reason: StrictStr = Field(default="OPERATOR_STOP", min_length=1, max_length=64)
    parking_timeout_s: float | None = Field(default=None, gt=0, le=30)


class EndRecording(Contract):
    request_id: StrictStr = Field(min_length=1, max_length=128)
    reason: StrictStr = Field(default="OPERATOR_FINISHED", min_length=1, max_length=64)
    parking_timeout_s: float | None = Field(default=None, gt=0, le=30)


class CurrentBinding(Contract):
    binding_id: str | None
    state: Literal["prepared", "started", "expired", "invalidated", "released", "missing", "unverified"]
    matches: bool
    readback_sha256: str | None
    error: str | None


class CurrentRecording(Contract):
    status: str
    episode_id: str | None
    segment_id: str | None
    command_capture_ready: bool
    error: str | None
    ready: bool


class CurrentOwner(Contract):
    state: Literal["not_acquired", "held", "unknown"]
    session_id: str | None
    lease_expires_at_backend_monotonic_s: float | None
    lease_exposed: bool = False


class SessionCurrent(Contract):
    source: Literal["live_native_read_only"] = "live_native_read_only"
    observed_at: str
    valid: bool
    status: Literal[
        "prepared", "started", "expired", "invalidated", "released",
        "offline", "identity_changed", "snapshot_ineligible", "unverified",
    ]
    error: str | None
    runtime_identity: RuntimeIdentity | None
    runtime_identity_matches: bool
    binding: CurrentBinding
    snapshot_id: str
    snapshot_eligible: bool
    recipe_fingerprint_matches: bool
    control_scope_granted: list[str]
    recording_required_for_motion: bool
    recording_begin_required: bool
    recording: CurrentRecording
    owner: CurrentOwner
    safety_latched: bool | None
    recording_ready: bool
    motion_ready: bool
    start_available: bool
    recording_begin_available: bool
    stop_available: bool
    recording_end_available: bool
    session_stop_protocol: str | None
    recording_end_protocol: str | None
    last_stop_code: str | None
    last_end_code: str | None
    recording_integrity: str | None
    blockers: list[str]


class PreparedSession(Contract):
    schema_version: Literal["unirobot-prepared-session-1"] = "unirobot-prepared-session-1"
    session_id: str
    state: Literal["prepared", "active", "closed", "failed"]
    created_at: str
    updated_at: str
    snapshot_id: str
    recipe_fingerprint: str
    execution_revision: int
    fingerprint: str
    native_identity: RuntimeIdentity
    native_binding: NativeBinding
    execution_eligible: bool
    start_available: bool
    execution: SessionExecution
    blocking_reasons: list[StartBlock]
    start_attempts: list[StartAttempt] = Field(default_factory=list)
    started_at: str | None = None
    start_receipt: StartReceipt | None = None
    recording_begin_attempts: list[RecordingAttempt] = Field(default_factory=list)
    recording_begin_receipt: RecordingBeginReceipt | None = None
    stop_attempts: list[StopAttempt] = Field(default_factory=list)
    stop_receipt: StopReceipt | None = None
    stop_receipts: list[StopReceipt] = Field(default_factory=list)
    recording_end_attempts: list[RecordingEndAttempt] = Field(default_factory=list)
    recording_end_receipt: RecordingEndReceipt | None = None
    recording_end_receipts: list[RecordingEndReceipt] = Field(default_factory=list)
    closed_at: str | None = None
    current: SessionCurrent | None = None


class SessionList(Contract):
    source: Literal["stored"] = "stored"
    live: Literal[False] = False
    retrieved_at: str
    sessions: list[PreparedSession]


class SessionEnvelope(Contract):
    session: PreparedSession
    replayed: bool


class PreparationError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 409, detail: dict | None = None) -> None:
        super().__init__(message)
        self.code, self.status_code, self.detail = code, status_code, detail or {}


class BindingError(RuntimeError):
    def __init__(self, code: str, message: str, *, transport: bool = False,
                 http_status: int | None = None) -> None:
        super().__init__(message)
        self.code, self.transport, self.http_status = code, transport, http_status


def _rounded(value: float) -> float:
    return round(value, 12)


def _python_satisfies(version: str | None, spec: str) -> tuple[bool, str]:
    if version is None:
        return False, "Native does not report a Python version"
    match = re.fullmatch(r"(\d+)\.(\d+)(?:\.\d+)?", version)
    if match is None:
        return False, f"Unparseable native Python version {version!r}"
    actual = (int(match.group(1)), int(match.group(2)))
    for part in spec.split(","):
        bound = re.fullmatch(r"(>=|<=|==|>|<)\s*(\d+)\.(\d+)", part.strip())
        if bound is None:
            return False, f"Unsupported Python range {part!r}"
        target = (int(bound.group(2)), int(bound.group(3)))
        accepted = {
            ">=": actual >= target, "<=": actual <= target, "==": actual == target,
            ">": actual > target, "<": actual < target,
        }[bound.group(1)]
        if not accepted:
            return False, f"observed Python {version}; required {spec}"
    return True, f"observed Python {version}; required {spec}"


class Validator:
    """Single read-only observation pass plus the declared check matrix."""

    def __init__(self, recipe: Recipe, integration: MobileCarIntegration) -> None:
        self.recipe = recipe
        self.integration = integration
        self.service = MobileCarReadService(integration)

    def _typed(self, path: str, model: type) -> Any:
        try:
            return model.model_validate(self.integration._read(path))
        except NativeReadError as exc:
            status = 503 if exc.status in {"not_configured", "offline"} else 502
            raise ReadServiceError(f"native_{exc.status}", str(exc), status) from exc
        except ValidationError as exc:
            fields = ", ".join(".".join(map(str, e["loc"])) for e in exc.errors())
            raise ReadServiceError("native_incompatible", f"{path}: invalid native fields: {fields}") from exc

    def observe(self) -> Observation:
        before = self._typed("/api/v1/health", Health)
        capabilities = self._typed("/api/v1/capabilities", CapabilitiesWithAttestation)
        raw_scene = self.integration._read("/api/v1/scene")
        try:
            scene = SceneData.model_validate(raw_scene)
        except ValidationError as exc:
            fields = ", ".join(".".join(map(str, e["loc"])) for e in exc.errors())
            raise ReadServiceError("native_incompatible", f"/api/v1/scene: invalid native fields: {fields}") from exc
        snapshot = self._typed("/api/v1/snapshot", NativeSnapshot)
        after = self._typed("/api/v1/health", Health)
        identity = RuntimeIdentity.model_validate(before.model_dump())
        stable = ("run_id", "backend_generation", "episode_id", "interface_profile", "recording_required_for_motion")
        if any(getattr(before, key) != getattr(after, key) for key in stable):
            raise ReadServiceError("native_identity_changed", "Native runtime changed during validation; retry", 409)
        if any(getattr(identity, key) != getattr(snapshot, key) for key in ("run_id", "backend_generation", "episode_id")):
            raise ReadServiceError("native_identity_changed", "Snapshot belongs to another runtime; retry", 409)
        return Observation(
            runtime_identity=identity,
            resource_identity=SceneIdentity.model_validate(scene.model_dump()),
            backend_kind=capabilities.backend_kind,
            interface_profile=after.interface_profile,
            recording_required_for_motion=after.recording_required_for_motion,
            supported_commands=list(capabilities.supported_commands),
            sensor_streams=list(capabilities.sensor_streams),
            config_manifest_attestation=capabilities.config_manifest_sha256,
            scene_manifest_attestation=capabilities.scene_manifest_sha256,
            session_binding_protocol=capabilities.session_binding_protocol,
            recording_begin_protocol=capabilities.recording_begin_protocol,
            session_stop_protocol=capabilities.session_stop_protocol,
            recording_end_protocol=capabilities.recording_end_protocol,
            runtime_python_version=capabilities.runtime_python_version,
            runtime_package_versions=(
                dict(capabilities.runtime_package_versions)
                if capabilities.runtime_package_versions is not None else None
            ),
            scene_manifest_sha256=digest(raw_scene),
            arm_joint_names=list(capabilities.arm_joint_names),
            arm_user_limits_rad=[[float(v) for v in pair] for pair in capabilities.arm_user_limits_rad],
            model_limits_rad=[[float(v) for v in pair] for pair in snapshot.arm.model_limits_rad],
            gripper_min_width_m=float(capabilities.gripper_min_width_m),
            gripper_max_width_m=float(capabilities.gripper_max_width_m),
            tcp_parent_body=capabilities.tcp_parent_body,
            tcp_site=scene.tcp_site,
            camera_parent_body=capabilities.camera_parent_body,
            recording_status=snapshot.recording.status,
            recording_episode_id=snapshot.recording.episode_id,
            recording_segment_id=snapshot.recording.recording_segment_id,
            recording_command_capture_ready=snapshot.recording.command_capture_ready,
            recording_error=snapshot.recording.error,
            base_owner_session_id=snapshot.base_owner_session_id,
            arm_owner_session_id=snapshot.arm_owner_session_id,
            active_session_id=snapshot.active_session_id,
            safety_latched=snapshot.safety_latched,
        )

    def kinematics(self, observation: Observation) -> tuple[KinematicsEvidence, list[Check]]:
        profile = self.recipe.kinematics
        arm = profile["arm"]
        expected_joints = list(arm["joint_names"])
        joint_order = observation.arm_joint_names == expected_joints
        limits_error = None
        try:
            derived = derived_user_limits(profile, observation.model_limits_rad)
        except RecipeError:
            derived = []
        if derived and len(derived) == len(observation.arm_user_limits_rad):
            limits_error = max(
                abs(a - b) for pair_a, pair_b in zip(derived, observation.arm_user_limits_rad) for a, b in zip(pair_a, pair_b)
            )
        limits_ok = limits_error is not None and limits_error <= TOLERANCE
        tcp_ok = observation.tcp_parent_body == profile["tcp"]["parent_body"] and observation.tcp_site == profile["tcp"]["site"]
        camera_ok = observation.camera_parent_body == profile["camera_mount"]["parent_body"]
        gripper_ok = (
            abs(observation.gripper_min_width_m - profile["gripper"]["min_width_m"]) <= TOLERANCE
            and abs(observation.gripper_max_width_m - profile["gripper"]["max_width_m"]) <= TOLERANCE
        )
        evidence = KinematicsEvidence(
            profile_id=profile["profile_id"],
            digest=self.recipe.kinematics_digest,
            authority=profile["authority"],
            joint_order_consistent=joint_order,
            user_limits_consistent=limits_ok,
            tcp_mount_consistent=tcp_ok,
            camera_mount_consistent=camera_ok,
            gripper_limits_consistent=gripper_ok,
            max_user_limit_error_rad=_rounded(limits_error) if limits_error is not None else 0.0,
            limitations=list(profile["limitations"]),
        )
        detail = (
            f"joints {len(observation.arm_joint_names)} vs profile {len(expected_joints)}; "
            f"max user-limit error {evidence.max_user_limit_error_rad} rad"
        )
        checks = [
            Check(key="kinematics_joint_order", status="passed" if joint_order else "failed", phase="configuration",
                  scope="native arm_joint_names vs platform kinematics profile", detail=detail),
            Check(key="kinematics_user_limits", status="passed" if limits_ok else "failed", phase="configuration",
                  scope="derived (model_limits - zero) * direction vs native arm_user_limits_rad", detail=detail),
            Check(key="kinematics_tcp_mount", status="passed" if tcp_ok else "failed", phase="configuration",
                  scope="native tcp_parent_body/tcp_site vs profile", detail=f"{observation.tcp_parent_body}/{observation.tcp_site}"),
            Check(key="kinematics_camera_mount", status="passed" if camera_ok else "failed", phase="configuration",
                  scope="native camera_parent_body vs profile", detail=observation.camera_parent_body),
            Check(key="kinematics_gripper_limits", status="passed" if gripper_ok else "failed", phase="configuration",
                  scope="native gripper width limits vs profile", detail=f"{observation.gripper_min_width_m}..{observation.gripper_max_width_m} m"),
        ]
        return evidence, checks

    def evaluate(self, observation: Observation) -> tuple[list[Check], KinematicsEvidence, list[BlockingReason]]:
        expected = self.recipe.expected
        checks: list[Check] = []

        def add(key: str, ok: bool, scope: str, detail: str, *, phase: str = "configuration") -> None:
            checks.append(Check(key=key, status="passed" if ok else "failed", phase=phase, scope=scope, detail=detail))

        resource = observation.resource_identity
        add("native_contract_version", resource.contract_version == expected["contract_version"], "native capabilities/scene contract_version",
            f"observed {resource.contract_version}; expected {expected['contract_version']}")
        add("resource_identity", all(getattr(resource, key) == expected[key] for key in ("model_id", "model_sha256", "scene_id")),
            "native model_id/model_sha256/scene_id", f"model={resource.model_id}; scene={resource.scene_id}")
        add("backend_kind", observation.backend_kind == expected["backend_kind"], "native capabilities backend_kind",
            f"observed {observation.backend_kind}; expected {expected['backend_kind']}")
        add("interface_profile", observation.interface_profile == expected["interface_profile"], "native /api/v1/health self-report",
            f"observed {observation.interface_profile}; recipe expects {expected['interface_profile']}; this value is derived from config flags, not attested")
        add("recording_required_for_motion", observation.recording_required_for_motion is True, "native /api/v1/health",
            "The recipe requires recording before motion")
        missing_commands = sorted(set(expected["commands"]) - set(observation.supported_commands))
        add("required_commands", not missing_commands, "native supported_commands superset of recipe commands",
            "missing: " + ", ".join(missing_commands) if missing_commands else "all recipe commands declared")
        missing_streams = sorted(set(expected["sensor_streams"]) - set(observation.sensor_streams))
        add("required_sensor_streams", not missing_streams, "native sensor_streams superset of recipe streams",
            "missing: " + ", ".join(missing_streams) if missing_streams else "all recipe streams declared")

        kinematics, kinematics_checks = self.kinematics(observation)
        checks.extend(kinematics_checks)

        # Readiness: these decide whether an executable Session may exist at all.
        attestation = observation.config_manifest_attestation
        expected_config = expected["config_manifest_sha256"]
        if attestation is None:
            checks.append(Check(key="deployed_config_attestation", status="unsupported", phase="readiness",
                                scope="native declared config manifest digest",
                                detail="Native HTTP does not attest the deployed config manifest; a healthy service cannot supply it"))
        else:
            add("deployed_config_attestation", attestation == expected_config,
                "native declared config manifest digest vs pinned native_attestation.config_manifest_sha256",
                f"declared {attestation}; pinned {expected_config}", phase="readiness")

        declared_scene = observation.scene_manifest_attestation
        expected_scene = expected["scene_manifest_sha256"]
        if declared_scene is None:
            checks.append(Check(key="scene_manifest_attestation", status="unsupported", phase="readiness",
                                scope="native declared compiled scene manifest digest",
                                detail=f"Observed scene manifest digest {observation.scene_manifest_sha256} is not attested; the pin only covers the scene XML file"))
        elif declared_scene != observation.scene_manifest_sha256:
            add("scene_manifest_attestation", False,
                "native declared scene manifest digest vs the scene body it serves",
                f"declared {declared_scene}; observed {observation.scene_manifest_sha256}", phase="readiness")
        else:
            add("scene_manifest_attestation", observation.scene_manifest_sha256 == expected_scene,
                "observed compiled scene manifest digest vs pinned native_attestation.scene_manifest_sha256",
                f"observed {observation.scene_manifest_sha256}; pinned {expected_scene}", phase="readiness")

        if observation.runtime_python_version is None:
            checks.append(Check(key="runtime_python_version", status="unsupported", phase="readiness",
                                scope="native reported Python version vs recipe range",
                                detail="Native does not report a Python version"))
        else:
            python_ok, python_detail = _python_satisfies(
                observation.runtime_python_version, self.recipe.body["dependencies"]["python"]
            )
            add("runtime_python_version", python_ok, "native reported Python version vs recipe range",
                python_detail, phase="readiness")

        pinned_packages = self.recipe.body["dependencies"]["requirements_lock"]["packages"]
        observed_packages = observation.runtime_package_versions
        if observed_packages is None:
            checks.append(Check(key="runtime_package_versions", status="unsupported", phase="readiness",
                                scope="native reported installed package versions vs requirements lock",
                                detail="Native does not report installed package versions"))
        else:
            missing = sorted(name for name in pinned_packages if name not in observed_packages)
            mismatched = {
                name: {"expected": pinned_packages[name], "observed": observed_packages[name]}
                for name in pinned_packages
                if name in observed_packages and observed_packages[name] != pinned_packages[name]
            }
            add("runtime_package_versions", not missing and not mismatched,
                "native reported installed package versions vs requirements lock",
                f"missing: {sorted(missing)}; mismatched: {mismatched}", phase="readiness")

        required_binding = self.recipe.required_protocols["session_binding"]
        if observation.session_binding_protocol is None:
            checks.append(Check(key="session_binding_protocol", status="unsupported", phase="readiness",
                                scope="native declared session binding protocol",
                                detail=f"Native declares no motion-free Session binding; required {required_binding}. episodes/start performs RESET and recording"))
        else:
            add("session_binding_protocol", observation.session_binding_protocol == required_binding,
                "native declared session binding protocol", f"declared {observation.session_binding_protocol}", phase="readiness")

        required_recording = self.recipe.required_protocols["recording_begin"]
        if observation.recording_begin_protocol is None:
            checks.append(Check(key="recording_begin_protocol", status="unsupported", phase="readiness",
                                scope="native declared recording begin protocol",
                                detail=f"Native has no recording begin without RESET; required {required_recording}"))
        else:
            add("recording_begin_protocol", observation.recording_begin_protocol == required_recording,
                "native declared recording begin protocol", f"declared {observation.recording_begin_protocol}", phase="readiness")

        add("native_recording_idle", observation.recording_status == "IDLE", "native recording state",
            f"observed {observation.recording_status}; an active native recording must not be replaced", phase="readiness")

        blocking = [
            BlockingReason(key=check.key, scope=check.phase,
                           message=f"{check.scope}: {check.detail}")
            for check in checks if check.status in {"failed", "unsupported", "not_checked"}
        ]
        return checks, kinematics, blocking


class NativeBindingClient:
    """Client for the declared motion-free binding protocol only; never guesses endpoints."""

    def __init__(self, integration: MobileCarIntegration) -> None:
        self.integration = integration

    def _call(self, method: str, path: str, body: dict | None = None,
              *, timeout_s: float = BINDING_TIMEOUT_S) -> dict:
        if (
            path not in BINDING_PATHS
            and path not in (RECORDING_BEGIN_PATH, RECORDING_END_PATH)
            and not re.fullmatch(r"/api/v1/session/prepared/[A-Za-z0-9_.-]{1,128}", path)
        ):
            raise BindingError("binding_path_rejected", f"not a declared binding path: {path}")
        if self.integration.config is None or not self.integration.config.base_url:
            raise BindingError("not_configured", "mobileCar service URL is not configured", transport=True)
        url = self.integration.config.base_url.rstrip("/") + path
        data = canonical(body) if body is not None else None
        request = urllib.request.Request(url, data=data, method=method,
                                         headers={"Accept": "application/json", "Content-Type": "application/json"})
        if self.integration.config.auth_env:
            token = os.environ.get(self.integration.config.auth_env)
            if token:
                request.add_header("Authorization", f"Bearer {token}")
        try:
            with self.integration._opener.open(request, timeout=timeout_s) as response:
                payload = response.read(1024 * 1024 + 1)
        except urllib.error.HTTPError as exc:
            raise BindingError("binding_http_error", f"{path}: HTTP {exc.code}",
                               http_status=exc.code) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise BindingError("offline", f"{path}: service unreachable or timed out", transport=True) from exc
        if len(payload) > 1024 * 1024:
            raise BindingError("binding_response_too_large", f"{path}: response exceeds size limit")
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BindingError("binding_incompatible", f"{path}: invalid JSON") from exc
        if not isinstance(value, dict):
            raise BindingError("binding_incompatible", f"{path}: expected a JSON object")
        return value

    @staticmethod
    def _require(value: dict, keys: tuple[str, ...]) -> None:
        missing = [key for key in keys if key not in value]
        if missing:
            raise BindingError("binding_incompatible", "missing binding fields: " + ", ".join(missing))

    def prepare(self, *, session_id: str, config_fingerprint: str, identity: RuntimeIdentity) -> dict:
        request = {
            "contract_version": "mobilecar-1.0",
            "session_id": session_id,
            "config_fingerprint": config_fingerprint,
            "run_id": identity.run_id,
            "backend_generation": identity.backend_generation,
            "episode_id": identity.episode_id,
        }
        value = self._call("POST", "/api/v1/session/prepare", request)
        if value.get("accepted") is not True:
            raise BindingError("binding_refused", f"native refused the binding: {value.get('reason', 'no reason')}")
        self._require(value, ("accepted", "binding_id", "session_id", "run_id", "backend_generation",
                              "episode_id", "config_fingerprint", "state", "motion_commands_accepted",
                              "owner_state", "recording_ready", "motion_ready"))
        self._verify(value, session_id, config_fingerprint, identity, expected_states=("prepared",))
        return value

    def readback(self, binding_id: str) -> dict:
        return self._call("GET", f"/api/v1/session/prepared/{binding_id}")

    def release(self, binding_id: str) -> None:
        self._call("POST", "/api/v1/session/release", {"binding_id": binding_id})

    def start(self, *, binding_id: str, session_id: str, config_fingerprint: str, identity: RuntimeIdentity) -> dict:
        value = self._call("POST", "/api/v1/session/start", {
            "binding_id": binding_id, "session_id": session_id, "config_fingerprint": config_fingerprint,
        })
        if value.get("started") is not True:
            raise BindingError("start_refused", f"native refused the start: {value.get('reason', 'no reason')}")
        self._require(value, ("started", "binding_id", "session_id", "run_id", "backend_generation", "episode_id",
                              "config_fingerprint", "started_at_backend_monotonic_s", "control_scope_granted",
                              "recording_required_for_motion", "recording_begin_required", "owner_state",
                              "recording_ready", "motion_ready", "motion_blockers"))
        self._verify(value, session_id, config_fingerprint, identity, binding_id=binding_id,
                     expected_states=("started",))
        return value

    def begin_recording(self, *, binding_id: str, session_id: str, config_fingerprint: str,
                        identity: RuntimeIdentity, operator_id: str, view_source: str) -> dict:
        value = self._call("POST", RECORDING_BEGIN_PATH, {
            "contract_version": "mobilecar-1.0",
            "binding_id": binding_id,
            "session_id": session_id,
            "config_fingerprint": config_fingerprint,
            "operator_id": operator_id,
            "operator_kind": "human_teleop",
            "view_source": view_source,
        })
        if value.get("accepted") is not True:
            raise BindingError("recording_begin_refused",
                               f"native refused recording begin: {value.get('reason', 'no reason')}")
        self._require(value, ("accepted", "binding_id", "session_id", "config_fingerprint", "run_id",
                              "backend_generation", "episode_id", "recording_segment_id", "recording_status",
                              "command_capture_ready", "recording_start_event_seq", "initial_snapshot_sha256",
                              "durable_start_records"))
        self._verify(value, session_id, config_fingerprint, identity, binding_id=binding_id,
                     expected_states=("started",))
        if value["recording_status"] != "RECORDING":
            raise BindingError("recording_not_confirmed", "native did not report RECORDING")
        if value["command_capture_ready"] is not True or value["durable_start_records"] is not True:
            raise BindingError("recording_not_durable", "native did not confirm durable start records")
        if not isinstance(value["recording_start_event_seq"], int) or value["recording_start_event_seq"] < 1:
            raise BindingError("recording_not_durable", "native did not report a recording_start event sequence")
        if not isinstance(value["initial_snapshot_sha256"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", value["initial_snapshot_sha256"]
        ):
            raise BindingError("recording_not_durable", "native did not report an initial snapshot digest")
        if not isinstance(value["recording_segment_id"], str) or not value["recording_segment_id"]:
            raise BindingError("recording_not_durable", "native did not report a recording segment")
        return value

    def stop_session(self, *, request_id: str, reason: str, parking_timeout_s: float | None,
                     identity: RuntimeIdentity, binding_id: str | None = None,
                     session_id: str | None = None, config_fingerprint: str | None = None) -> dict:
        """m1-stop-1 call. A refused stop is a normal answer; a contract breach is not."""
        value = self._call("POST", SESSION_STOP_PATH, {
            "contract_version": "mobilecar-1.0",
            "request_id": request_id,
            "run_id": identity.run_id,
            "backend_generation": identity.backend_generation,
            "episode_id": identity.episode_id,
            "binding_id": binding_id,
            "session_id": session_id,
            "config_fingerprint": config_fingerprint,
            "reason": reason,
            "parking_timeout_s": parking_timeout_s,
        }, timeout_s=LIFECYCLE_WRITE_TIMEOUT_S)
        self._require(value, ("accepted", "code", "protocol", "request_id", "replayed", "run_id",
                              "backend_generation", "episode_id", "dispatch", "parking",
                              "owner_cleared_after_stop", "safety_latched", "recording_status",
                              "recording_touched", "motion_restored"))
        self._check_lifecycle_answer(value, protocol="m1-stop-1", request_id=request_id, identity=identity)
        StopReceipt.model_validate({**value, "observed_at": utc_now()})
        return value

    def end_recording(self, *, request_id: str, reason: str, parking_timeout_s: float | None,
                      binding_id: str, session_id: str, config_fingerprint: str,
                      recording_segment_id: str, identity: RuntimeIdentity) -> dict:
        """m1-end-1 call bound to the segment this Session began."""
        value = self._call("POST", RECORDING_END_PATH, {
            "contract_version": "mobilecar-1.0",
            "request_id": request_id,
            "binding_id": binding_id,
            "session_id": session_id,
            "config_fingerprint": config_fingerprint,
            "run_id": identity.run_id,
            "backend_generation": identity.backend_generation,
            "episode_id": identity.episode_id,
            "recording_segment_id": recording_segment_id,
            "reason": reason,
            "parking_timeout_s": parking_timeout_s,
        }, timeout_s=LIFECYCLE_WRITE_TIMEOUT_S)
        self._require(value, ("accepted", "code", "protocol", "request_id", "replayed", "binding_id",
                              "session_id", "config_fingerprint", "run_id", "backend_generation",
                              "episode_id", "recording_segment_id", "binding_state", "dispatch",
                              "parking", "drain", "finalize", "integrity", "recording_status",
                              "safety_latched", "reset_issued", "safety_cleared", "owner_acquired"))
        self._check_lifecycle_answer(value, protocol="m1-end-1", request_id=request_id, identity=identity)
        if value["binding_id"] != binding_id or value["session_id"] != session_id:
            raise BindingError("end_binding_mismatch", "native echoed another binding or Session")
        if value["recording_segment_id"] != recording_segment_id:
            raise BindingError("end_segment_mismatch", "native echoed another recording segment")
        if value["reset_issued"] is not False or value["safety_cleared"] is not False \
                or value["owner_acquired"] is not False:
            raise BindingError("end_did_extra_side_effects",
                               "native end performed an action outside STOP and Recorder finalization")
        if value["accepted"] is True and value["integrity"] == "complete":
            if value["finalize"]["complete_tail"] is not True:
                raise BindingError("end_not_complete_tail", "native reported complete integrity without a tail record")
            if not isinstance(value["finalize"].get("episode_complete_sha256"), str) or not re.fullmatch(
                r"[0-9a-f]{64}", str(value["finalize"].get("episode_complete_sha256"))
            ):
                raise BindingError("end_missing_tail_digest", "native reported a complete tail without a file digest")
        RecordingEndReceipt.model_validate({**value, "observed_at": utc_now()})
        return value

    @staticmethod
    def _check_lifecycle_answer(value: dict, *, protocol: str, request_id: str,
                                identity: RuntimeIdentity) -> None:
        if value.get("protocol") != protocol:
            raise BindingError("lifecycle_protocol_mismatch", f"native answered with {value.get('protocol')}")
        if value.get("request_id") != request_id:
            raise BindingError("lifecycle_request_mismatch", "native answered a different request_id")
        if protocol == "m1-stop-1" and (value.get("recording_touched") is not False
                                        or value.get("motion_restored") is not False):
            raise BindingError("stop_did_extra_side_effects",
                               "native stop touched the recording or restored motion")
        # A refusal legitimately echoes the live runtime, which is exactly what the
        # caller was told did not match; only an accepted answer must agree.
        if value.get("accepted") is not True:
            return
        mismatch = [
            key for key, expected in (
                ("run_id", identity.run_id),
                ("backend_generation", identity.backend_generation),
                ("episode_id", identity.episode_id),
            ) if value.get(key) != expected
        ]
        if mismatch:
            raise BindingError(
                "lifecycle_identity_mismatch",
                "accepted native stop/end does not belong to the observed runtime: " + ", ".join(mismatch),
            )

    @staticmethod
    def _verify(value: dict, session_id: str, config_fingerprint: str, identity: RuntimeIdentity,
                *, binding_id: str | None = None, expected_states: tuple[str, ...]) -> None:
        mismatch = [
            key for key, expected in (
                ("session_id", session_id),
                ("config_fingerprint", config_fingerprint),
                ("run_id", identity.run_id),
                ("backend_generation", identity.backend_generation),
                ("episode_id", identity.episode_id),
            ) if value.get(key) != expected
        ]
        if binding_id is not None and value.get("binding_id") != binding_id:
            mismatch.append("binding_id")
        if value.get("state") not in expected_states:
            mismatch.append("state")
        if value.get("motion_commands_accepted") is True:
            mismatch.append("motion_commands_accepted")
        if mismatch:
            raise BindingError("binding_unverified", "native binding readback does not match the request: " + ", ".join(mismatch))


class PreparationStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS config_snapshots (id TEXT PRIMARY KEY, document TEXT NOT NULL, created_at TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS prepared_sessions (id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE, "
                       "runtime_key TEXT NOT NULL, state TEXT NOT NULL, request_sha256 TEXT NOT NULL, document TEXT NOT NULL)")

    def put_snapshot(self, document: dict) -> bool:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("INSERT INTO config_snapshots VALUES (?, ?, ?)",
                           (document["snapshot_id"], json.dumps(document), document["created_at"]))
                return True
            except sqlite3.IntegrityError:
                return False

    def get_snapshot(self, snapshot_id: str) -> dict:
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute("SELECT document FROM config_snapshots WHERE id=?", (snapshot_id,)).fetchone()
        if row is None:
            raise PreparationError("snapshot_not_found", "Configuration snapshot not found", 404)
        return json.loads(row[0])

    def list_snapshots(self, limit: int = 50) -> list[dict]:
        with closing(sqlite3.connect(self.path)) as db, db:
            rows = db.execute("SELECT document FROM config_snapshots ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def put_session(self, document: dict, idempotency_key: str, request_sha256: str) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO prepared_sessions VALUES (?, ?, ?, ?, ?, ?)",
                       (document["session_id"], idempotency_key, _runtime_key(document["native_identity"]),
                        document["state"], request_sha256, json.dumps(document)))

    def update_session(self, document: dict) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE prepared_sessions SET state=?, document=? WHERE id=?",
                       (document["state"], json.dumps(document), document["session_id"]))

    def get_session(self, session_id: str) -> dict:
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute("SELECT document FROM prepared_sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            raise PreparationError("session_not_found", "Session not found", 404)
        return json.loads(row[0])

    def list_sessions(self, limit: int = 50) -> list[dict]:
        with closing(sqlite3.connect(self.path)) as db, db:
            rows = db.execute("SELECT document FROM prepared_sessions ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def session_by_key(self, idempotency_key: str) -> tuple[dict, str] | None:
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute("SELECT document, request_sha256 FROM prepared_sessions WHERE idempotency_key=?",
                             (idempotency_key,)).fetchone()
        return (json.loads(row[0]), row[1]) if row else None

    def occupied_runtime(self, identity: RuntimeIdentity) -> dict | None:
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute("SELECT document FROM prepared_sessions WHERE runtime_key=? AND state IN ('prepared','active') LIMIT 1",
                             (_runtime_key(identity),)).fetchone()
        return json.loads(row[0]) if row else None

    def occupied_runtime(self, identity: RuntimeIdentity) -> dict | None:
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute("SELECT document FROM prepared_sessions WHERE runtime_key=? AND state IN ('prepared','active') LIMIT 1",
                             (_runtime_key(identity),)).fetchone()
        return json.loads(row[0]) if row else None


def _runtime_key(identity: RuntimeIdentity | dict) -> str:
    if isinstance(identity, dict):
        return f"{identity['run_id']}|{identity['backend_generation']}|{identity['episode_id']}"
    return f"{identity.run_id}|{identity.backend_generation}|{identity.episode_id}"


def _hashed(value: dict) -> dict:
    return {key: value[key] for key in value if key not in {"snapshot_id", "snapshot_sha256", "created_at"}}


class PreparationService:
    def __init__(self, store: PreparationStore, validator: Validator, recipe: Recipe) -> None:
        self.store = store
        self.validator = validator
        self.recipe = recipe
        self.binding = NativeBindingClient(validator.integration)
        # Guards only the short read-modify-write of one Session document. Network calls to
        # native happen outside it, so a slow STOP never blocks another Session write.
        self.session_write_lock = threading.Lock()

    def snapshot(self, draft: dict) -> tuple[dict, bool]:
        observation = self.validator.observe()
        checks, kinematics, blocking = self.validator.evaluate(observation)
        configuration_ok = all(check.status == "passed" for check in checks if check.phase == "configuration")
        ready = configuration_ok and all(check.status == "passed" for check in checks if check.phase == "readiness")
        document = {
            "schema_version": "unirobot-config-snapshot-1",
            "draft_id": draft["draft_id"],
            "draft_revision": draft["draft_revision"],
            "execution_revision": draft["execution_revision"],
            "fingerprint": draft["fingerprint"],
            "recipe_fingerprint": self.recipe.fingerprint,
            "recipe": {
                "recipe_id": self.recipe.recipe_id,
                "recipe_revision": self.recipe.revision,
                "sources": self.recipe.sources,
            },
            "observation": observation.model_dump(),
            "kinematics": kinematics.model_dump(),
            "checks": [check.model_dump() for check in checks],
            "validation_status": "passed" if configuration_ok else "failed",
            "validation_scope": "motion_free_configuration_and_declared_protocol_only",
            "execution_eligible": ready,
            "blocking_reasons": [reason.model_dump() for reason in blocking],
        }
        document["snapshot_id"] = "cs-" + digest(_hashed(document))[:40]
        document["created_at"] = utc_now()
        document["snapshot_sha256"] = digest(document)
        document["validated_snapshot_id"] = document["snapshot_id"] if ready else None
        inserted = self.store.put_snapshot(document)
        if not inserted:
            # Same evidence must reproduce the stored document, including its hash.
            return self.store.get_snapshot(document["snapshot_id"]), True
        return document, False

    def create_session(self, request: dict) -> tuple[dict, bool]:
        snapshot = self.store.get_snapshot(request["validated_snapshot_id"])
        if snapshot["execution_revision"] != request["execution_revision"] or snapshot["fingerprint"] != request["fingerprint"]:
            raise PreparationError("stale_execution_reference", "Request does not match the snapshot's execution revision/fingerprint")
        if snapshot["recipe_fingerprint"] != self.recipe.fingerprint:
            raise PreparationError("recipe_changed", "The execution recipe changed after this snapshot was issued")
        if not snapshot["execution_eligible"]:
            raise PreparationError("validation_incomplete", "Snapshot is not execution eligible", 409,
                                   {"blocking_reasons": snapshot["blocking_reasons"]})
        request_sha256 = hashlib.sha256(canonical({key: request[key] for key in
                                                   ("validated_snapshot_id", "execution_revision", "fingerprint")})).hexdigest()
        existing = self.store.session_by_key(request["idempotency_key"])
        if existing is not None:
            stored, stored_sha256 = existing
            if stored_sha256 == request_sha256:
                return stored, True
            raise PreparationError("idempotency_conflict", "Idempotency key was used for a different request")

        identity = RuntimeIdentity.model_validate(snapshot["observation"]["runtime_identity"])
        observation = self.validator.observe()
        if observation.runtime_identity != identity:
            raise PreparationError("runtime_identity_changed", "Native runtime changed since the snapshot was issued")
        occupied = self.store.occupied_runtime(identity)
        if occupied is not None:
            raise PreparationError("session_conflict", "Another prepared or active Session already holds this runtime", 409,
                                   {"session_id": occupied["session_id"]})

        session_id = "ps-" + uuid4().hex
        binding = self._prepare_binding(session_id, snapshot, identity, observation)
        now = utc_now()
        recording_begin_required = (
            observation.recording_required_for_motion
            and observation.recording_begin_protocol == self.recipe.required_protocols["recording_begin"]
        )
        document = {
            "schema_version": "unirobot-prepared-session-1",
            "session_id": session_id,
            "state": "prepared",
            "created_at": now,
            "updated_at": now,
            "snapshot_id": snapshot["snapshot_id"],
            "recipe_fingerprint": snapshot["recipe_fingerprint"],
            "execution_revision": snapshot["execution_revision"],
            "fingerprint": snapshot["fingerprint"],
            "native_identity": identity.model_dump(),
            "native_binding": binding.model_dump(),
            "execution_eligible": True,
            "start_available": True,
            "execution": SessionExecution(
                control_scope_granted=[],
                owner=OwnerLease(state="not_acquired", session_id=None,
                                 lease_expires_at_backend_monotonic_s=None),
                recording_required_for_motion=observation.recording_required_for_motion,
                recording_begin_required=recording_begin_required,
                recording_ready=False,
                motion_ready=False,
                motion_blockers=["session_not_active"],
                observed_at=now,
                source="prepared",
            ).model_dump(),
            "blocking_reasons": [],
            "start_attempts": [],
            "started_at": None,
            "start_receipt": None,
            "recording_begin_attempts": [],
            "recording_begin_receipt": None,
        }
        try:
            self.store.put_session(document, request["idempotency_key"], request_sha256)
        except sqlite3.IntegrityError as exc:
            self._release_quietly(binding.binding_id)
            replay = self.store.session_by_key(request["idempotency_key"])
            if replay is not None and replay[1] == request_sha256:
                return replay[0], True
            raise PreparationError("idempotency_conflict", "Idempotency key was used for a different request") from exc
        return document, False

    def _release_quietly(self, binding_id: str) -> None:
        try:
            self.binding.release(binding_id)
        except BindingError:
            # The prepared binding expires on its own; failing to release it must
            # not be reported as a successful Session creation.
            pass

    def _prepare_binding(self, session_id: str, snapshot: dict, identity: RuntimeIdentity,
                         observation: Observation) -> NativeBinding:
        protocol = self.recipe.required_protocols["session_binding"]
        if observation.session_binding_protocol != protocol:
            raise PreparationError("native_binding_unsupported", "Native does not declare the required binding protocol",
                                   409, {"protocol": protocol, "declared": observation.session_binding_protocol})
        try:
            prepared = self.binding.prepare(session_id=session_id, config_fingerprint=snapshot["snapshot_id"], identity=identity)
            readback = self.binding.readback(prepared["binding_id"])
            NativeBindingClient._verify(readback, session_id, snapshot["snapshot_id"], identity,
                                        binding_id=prepared["binding_id"], expected_states=("prepared",))
        except BindingError as exc:
            if exc.transport:
                raise PreparationError("native_offline", str(exc), 503) from exc
            raise PreparationError("native_binding_unverified", str(exc), 409,
                                   {"protocol": protocol}) from exc
        binding = NativeBinding(
            status="verified", protocol=protocol, binding_id=prepared["binding_id"], native_session_id=session_id,
            config_fingerprint=snapshot["snapshot_id"], expires_at_backend_monotonic_s=prepared.get("expires_at_backend_monotonic_s"),
            verified_at=utc_now(), readback_sha256=digest(readback), reason=None,
        )
        return binding

    def start(self, session_id: str) -> dict:
        session = self.store.get_session(session_id)
        if session["state"] == "active":
            return session
        if session["state"] != "prepared":
            raise PreparationError("session_not_startable", f"Session is {session['state']}; only a prepared Session can start")
        blocking: list[StartBlock] = []
        observation: Observation | None = None
        try:
            observation = self.validator.observe()
        except ReadServiceError as exc:
            blocking.append(StartBlock(key=exc.code, scope="native", message=str(exc)))

        if session["recipe_fingerprint"] != self.recipe.fingerprint:
            blocking.append(StartBlock(key="recipe_changed", scope="platform",
                                       message="The execution recipe changed; revalidate the configuration"))
        try:
            snapshot = self.store.get_snapshot(session["snapshot_id"])
        except PreparationError as exc:
            snapshot = None
            blocking.append(StartBlock(key=exc.code, scope="platform", message=str(exc)))
        if snapshot is not None and not snapshot["execution_eligible"]:
            blocking.append(StartBlock(key="snapshot_not_eligible", scope="platform",
                                       message="The accepted snapshot is no longer execution eligible"))

        identity = RuntimeIdentity.model_validate(session["native_identity"])
        if observation is not None:
            if observation.runtime_identity != identity:
                blocking.append(StartBlock(key="runtime_identity_changed", scope="native",
                                           message="Live run/generation/episode differs from the prepared Session"))
            if observation.recording_status != "IDLE":
                blocking.append(StartBlock(key="native_recording_active", scope="recording",
                                           message=f"Native recording is {observation.recording_status}; it must not be replaced"))
            if observation.base_owner_session_id or observation.arm_owner_session_id:
                blocking.append(StartBlock(key="control_owner_present", scope="native",
                                           message="Native already has an owner for base or arm"))
            if observation.safety_latched:
                blocking.append(StartBlock(key="native_safety_stop_latched", scope="native",
                                           message="Native safety stop is latched; clear it explicitly before starting"))

        binding = NativeBinding.model_validate(session["native_binding"])
        if binding.status != "verified" or binding.binding_id is None or binding.config_fingerprint is None:
            blocking.append(StartBlock(key="native_binding_unverified", scope="native",
                                       message="Native Session binding was never verified"))
        else:
            try:
                readback = self.binding.readback(binding.binding_id)
                NativeBindingClient._verify(readback, session_id, binding.config_fingerprint, identity,
                                            binding_id=binding.binding_id,
                                            expected_states=("prepared", "started"))
            except BindingError as exc:
                blocking.append(StartBlock(key="native_binding_unverified", scope="native", message=str(exc)))

        if blocking:
            self._record_attempt(session, "refused", blocking, "Start preconditions are not met; no native start was requested")
            raise PreparationError("start_preconditions_unmet", "Start preconditions are not met", 409,
                                   {"blocking_reasons": [item.model_dump() for item in blocking]})

        try:
            started = self.binding.start(binding_id=binding.binding_id, session_id=session_id,
                                          config_fingerprint=binding.config_fingerprint, identity=identity)
        except BindingError as exc:
            self._record_attempt(session, "failed", [], str(exc))
            raise PreparationError("native_start_failed", str(exc), 502 if exc.transport else 409) from exc

        recording_required = bool(started["recording_required_for_motion"])
        recording_begin_required = bool(started["recording_begin_required"])
        if recording_required and not recording_begin_required:
            detail = "Native start does not require the recording begin protocol while motion requires recording"
            self._record_attempt(session, "failed", [], detail)
            raise PreparationError("native_start_failed", detail, 409)
        owner_state = str(started["owner_state"])
        if owner_state not in {"not_acquired", "held"}:
            detail = f"Native start reported an unsupported owner state: {owner_state}"
            self._record_attempt(session, "failed", [], detail)
            raise PreparationError("native_start_failed", detail, 409)
        receipt = StartReceipt(
            binding_id=binding.binding_id, native_session_id=session_id, run_id=identity.run_id,
            backend_generation=identity.backend_generation, episode_id=identity.episode_id,
            config_fingerprint=binding.config_fingerprint,
            started_at_backend_monotonic_s=float(started["started_at_backend_monotonic_s"]),
            control_scope_granted=[str(item) for item in started["control_scope_granted"]],
            recording_required_for_motion=recording_required,
            recording_begin_required=recording_begin_required,
            owner_state=owner_state,
            owner_session_id=started.get("owner_session_id"),
            lease_expires_at_backend_monotonic_s=started.get("lease_expires_at_backend_monotonic_s"),
            recording_ready=bool(started["recording_ready"]),
            motion_ready=bool(started["motion_ready"]),
            motion_blockers=[str(item) for item in started["motion_blockers"]],
        )
        now = utc_now()
        session.update(state="active", started_at=now, updated_at=now,
                       start_receipt=receipt.model_dump(), start_available=False)
        session["execution"] = SessionExecution(
            control_scope_granted=receipt.control_scope_granted,
            owner=OwnerLease(
                state=owner_state,
                session_id=receipt.owner_session_id,
                lease_expires_at_backend_monotonic_s=receipt.lease_expires_at_backend_monotonic_s,
            ),
            recording_required_for_motion=recording_required,
            recording_begin_required=recording_begin_required,
            recording_ready=receipt.recording_ready,
            motion_ready=receipt.motion_ready,
            motion_blockers=receipt.motion_blockers,
            observed_at=now,
            source="native_start",
        ).model_dump()
        session["start_attempts"] = [*session["start_attempts"], StartAttempt(
            at=now, result="started", blocking=[], detail="Native start acknowledged the prepared binding").model_dump()]
        self.store.update_session(session)
        return session

    def begin_recording(self, session_id: str, request: dict) -> tuple[dict, bool]:
        session = self.store.get_session(session_id)
        if session["state"] != "active":
            raise PreparationError("session_not_active", f"Session is {session['state']}; recording requires an active Session")
        if session["recipe_fingerprint"] != self.recipe.fingerprint:
            raise PreparationError("recipe_changed", "The execution recipe changed; revalidate the configuration")
        if session.get("recording_begin_receipt") is not None and session["execution"]["recording_ready"]:
            return session, True
        try:
            snapshot = self.store.get_snapshot(session["snapshot_id"])
        except PreparationError as exc:
            raise PreparationError(exc.code, str(exc)) from exc
        if not snapshot["execution_eligible"] or snapshot["recipe_fingerprint"] != self.recipe.fingerprint:
            raise PreparationError("snapshot_not_eligible", "The accepted snapshot is no longer execution eligible")
        try:
            observation = self.validator.observe()
        except ReadServiceError as exc:
            raise PreparationError(exc.code, str(exc), exc.status_code) from exc
        identity = RuntimeIdentity.model_validate(session["native_identity"])
        if observation.runtime_identity != identity:
            raise PreparationError("runtime_identity_changed", "Native runtime changed after the Session started")
        required = self.recipe.required_protocols["recording_begin"]
        if observation.recording_begin_protocol != required:
            raise PreparationError(
                "recording_begin_unsupported",
                "Native does not declare the required recording begin protocol", 409,
                {"protocol": required, "declared": observation.recording_begin_protocol},
            )
        binding = NativeBinding.model_validate(session["native_binding"])
        if binding.status != "verified" or binding.binding_id is None or binding.config_fingerprint is None:
            raise PreparationError("native_binding_unverified", "Native Session binding was never verified")
        try:
            readback = self.binding.readback(binding.binding_id)
            NativeBindingClient._verify(readback, session_id, binding.config_fingerprint, identity,
                                        binding_id=binding.binding_id, expected_states=("started",))
            begun = self.binding.begin_recording(
                binding_id=binding.binding_id, session_id=session_id,
                config_fingerprint=binding.config_fingerprint, identity=identity,
                operator_id=request["operator_id"], view_source=request["view_source"],
            )
        except BindingError as exc:
            self._record_recording_attempt(session, "failed", str(exc))
            raise PreparationError("native_recording_begin_failed", str(exc),
                                   503 if exc.transport else 409) from exc

        receipt = RecordingBeginReceipt(
            binding_id=binding.binding_id,
            native_session_id=session_id,
            run_id=identity.run_id,
            backend_generation=identity.backend_generation,
            episode_id=identity.episode_id,
            config_fingerprint=binding.config_fingerprint,
            recording_segment_id=str(begun["recording_segment_id"]),
            recording_status=str(begun["recording_status"]),
            command_capture_ready=bool(begun["command_capture_ready"]),
            recording_start_event_seq=int(begun["recording_start_event_seq"]),
            initial_snapshot_sha256=str(begun["initial_snapshot_sha256"]),
            durable_start_records=bool(begun["durable_start_records"]),
            started_at_backend_monotonic_s=float(begun["started_at_backend_monotonic_s"]),
        )
        now = utc_now()
        blockers: list[str] = []
        if not session["execution"]["control_scope_granted"]:
            blockers.append("control_scope_empty")
        if observation.safety_latched:
            blockers.append("safety_latched")
        if observation.base_owner_session_id or observation.arm_owner_session_id:
            blockers.append("control_owner_present")
        execution = SessionExecution(
            control_scope_granted=session["execution"]["control_scope_granted"],
            owner=OwnerLease(
                state="held" if (observation.base_owner_session_id or observation.arm_owner_session_id) else "not_acquired",
                session_id=observation.base_owner_session_id or observation.arm_owner_session_id,
                lease_expires_at_backend_monotonic_s=None,
            ),
            recording_required_for_motion=session["execution"]["recording_required_for_motion"],
            recording_begin_required=session["execution"]["recording_begin_required"],
            recording_ready=True,
            motion_ready=not blockers,
            motion_blockers=blockers,
            observed_at=now,
            source="native_recording_begin",
        )
        session.update(updated_at=now, recording_begin_receipt=receipt.model_dump(),
                       execution=execution.model_dump())
        self._record_recording_attempt(session, "begun", "")
        return session, False

    def _lifecycle_guard(self, session_id: str, *, require_started: bool) -> tuple[dict, Observation, RuntimeIdentity, NativeBinding]:
        """Shared preconditions for STOP and recording end: identity, not motion readiness."""
        session = self.store.get_session(session_id)
        if session["state"] not in ({"prepared", "active"} if not require_started else {"active"}):
            raise PreparationError(
                "session_not_stoppable",
                f"Session is {session['state']}; STOP and recording end need a bound Session",
            )
        if session["recipe_fingerprint"] != self.recipe.fingerprint:
            raise PreparationError("recipe_changed", "The execution recipe changed; revalidate the configuration")
        try:
            snapshot = self.store.get_snapshot(session["snapshot_id"])
        except PreparationError as exc:
            raise PreparationError(exc.code, str(exc)) from exc
        if not snapshot["execution_eligible"] or snapshot["recipe_fingerprint"] != self.recipe.fingerprint:
            raise PreparationError("snapshot_not_eligible", "The accepted snapshot is no longer execution eligible")
        try:
            observation = self.validator.observe()
        except ReadServiceError as exc:
            raise PreparationError(exc.code, str(exc), exc.status_code) from exc
        identity = RuntimeIdentity.model_validate(session["native_identity"])
        if observation.runtime_identity != identity:
            raise PreparationError("runtime_identity_changed", "Native runtime changed; re-observe before stopping")
        binding = NativeBinding.model_validate(session["native_binding"])
        if binding.status != "verified" or binding.binding_id is None or binding.config_fingerprint is None:
            raise PreparationError("native_binding_unverified", "Native Session binding was never verified")
        return session, observation, identity, binding

    @staticmethod
    def _remembered_receipt(session: dict, list_key: str, latest_key: str, request_id: str) -> dict | None:
        stored = session.get(list_key) or []
        for receipt in reversed(stored):
            if receipt.get("request_id") == request_id:
                return receipt
        latest = session.get(latest_key)
        return latest if latest is not None and latest.get("request_id") == request_id else None

    @staticmethod
    def _store_receipt(session: dict, list_key: str, latest_key: str, receipt: dict) -> None:
        history = [*(session.get(list_key) or []), receipt]
        session[list_key] = history[-LIFECYCLE_RECEIPT_HISTORY:]
        session[latest_key] = receipt

    def stop_session(self, session_id: str, request: dict) -> tuple[dict, bool]:
        session = self.store.get_session(session_id)
        if self._remembered_receipt(session, "stop_receipts", "stop_receipt", request["request_id"]) is not None:
            return session, True
        session, observation, identity, binding = self._lifecycle_guard(session_id, require_started=False)
        required = self.recipe.required_protocols.get("session_stop")
        if required is None:
            raise PreparationError(
                "stop_unsupported",
                "The execution recipe does not require a robot STOP protocol",
                detail={"required_protocol": None, "declared": observation.session_stop_protocol},
            )
        if observation.session_stop_protocol != required:
            raise PreparationError(
                "stop_unsupported",
                "Native does not declare the required session STOP protocol",
                detail={"required_protocol": required, "declared": observation.session_stop_protocol},
            )
        try:
            stopped = self.binding.stop_session(
                request_id=request["request_id"], reason=request["reason"],
                parking_timeout_s=request["parking_timeout_s"], identity=identity,
                binding_id=binding.binding_id, session_id=session_id,
                config_fingerprint=binding.config_fingerprint,
            )
        except BindingError as exc:
            result = "refused" if exc.http_status is not None else "result_unknown"
            self._record_failure(session_id, "stop_attempts", StopAttempt(
                at=utc_now(), request_id=request["request_id"], result=result,
                code="", reason=str(exc)[:400]).model_dump())
            raise PreparationError("native_stop_failed", str(exc), 504 if exc.transport else 409) from exc
        receipt = StopReceipt.model_validate({**stopped, "observed_at": utc_now()})
        attempt = StopAttempt(at=utc_now(), request_id=request["request_id"],
                               result="stopped" if receipt.accepted else "refused",
                               code=receipt.code, reason=receipt.reason[:400]).model_dump()
        def commit(document: dict) -> None:
            self._store_receipt(document, "stop_receipts", "stop_receipt", receipt.model_dump())
            document["stop_attempts"] = [*(document.get("stop_attempts") or []), attempt]
        return self._commit_lifecycle(session_id, commit), receipt.replayed

    def end_recording(self, session_id: str, request: dict) -> tuple[dict, bool]:
        session = self.store.get_session(session_id)
        if self._remembered_receipt(session, "recording_end_receipts", "recording_end_receipt",
                                    request["request_id"]) is not None:
            return session, True
        session, observation, identity, binding = self._lifecycle_guard(session_id, require_started=True)
        required = self.recipe.required_protocols.get("recording_end")
        if required is None:
            raise PreparationError(
                "recording_end_unsupported",
                "The execution recipe does not require a recording end protocol",
                detail={"required_protocol": None, "declared": observation.recording_end_protocol},
            )
        if observation.recording_end_protocol != required:
            raise PreparationError(
                "recording_end_unsupported",
                "Native does not declare the required recording end protocol",
                detail={"required_protocol": required, "declared": observation.recording_end_protocol},
            )
        begun = session.get("recording_begin_receipt")
        if begun is None:
            raise PreparationError("recording_not_begun", "This Session never began a recording segment")
        segment = str(begun["recording_segment_id"])
        try:
            ended = self.binding.end_recording(
                request_id=request["request_id"], reason=request["reason"],
                parking_timeout_s=request["parking_timeout_s"], binding_id=binding.binding_id,
                session_id=session_id, config_fingerprint=binding.config_fingerprint,
                recording_segment_id=segment, identity=identity,
            )
        except BindingError as exc:
            result = "refused" if exc.http_status is not None else "result_unknown"
            self._record_failure(session_id, "recording_end_attempts", RecordingEndAttempt(
                at=utc_now(), request_id=request["request_id"], result=result,
                code="", reason=str(exc)[:400]).model_dump())
            raise PreparationError("native_recording_end_failed", str(exc), 504 if exc.transport else 409) from exc
        receipt = RecordingEndReceipt.model_validate({**ended, "observed_at": utc_now()})
        attempt = RecordingEndAttempt(
            at=utc_now(), request_id=request["request_id"],
            result="ended" if receipt.accepted else "refused",
            code=receipt.code, reason=receipt.reason[:400]).model_dump()

        def commit(document: dict) -> None:
            self._store_receipt(document, "recording_end_receipts", "recording_end_receipt",
                                receipt.model_dump())
            document["recording_end_attempts"] = [
                *(document.get("recording_end_attempts") or []), attempt]
            if receipt.accepted:
                # The segment reached a durable terminal record, so this Session's collection
                # is closed. Integrity stays on the receipt: an INCOMPLETE tail never becomes
                # "complete" and the historical failure is not wiped.
                now = utc_now()
                execution = SessionExecution.model_validate(document["execution"])
                document["state"] = "closed"
                document["closed_at"] = now
                document["execution"] = SessionExecution(
                    control_scope_granted=execution.control_scope_granted,
                    owner=execution.owner,
                    recording_required_for_motion=execution.recording_required_for_motion,
                    recording_begin_required=execution.recording_begin_required,
                    recording_ready=False,
                    motion_ready=False,
                    motion_blockers=[*execution.motion_blockers, "recording_closed"],
                    observed_at=now,
                    source="native_recording_end",
                ).model_dump()

        return self._commit_lifecycle(session_id, commit), receipt.replayed

    def _commit_lifecycle(self, session_id: str, mutate) -> dict:
        """Merge one lifecycle outcome into the freshest stored Session document.

        The gateway is a single process, so this lock plus a re-read is enough to keep two
        concurrent answers from overwriting each other's receipt history.
        """
        with self.session_write_lock:
            document = self.store.get_session(session_id)
            mutate(document)
            document["updated_at"] = utc_now()
            self.store.update_session(document)
        return document

    def _record_failure(self, session_id: str, key: str, attempt: dict) -> None:
        """Record a refused or unknown-result attempt. No receipt is invented for it."""
        def commit(document: dict) -> None:
            document[key] = [*(document.get(key) or []), attempt]
        self._commit_lifecycle(session_id, commit)

    def current_observation(self, session: dict) -> SessionCurrent:
        """Read-only live view; never writes, starts, renews or rebinds."""
        now = utc_now()
        identity = RuntimeIdentity.model_validate(session["native_identity"])
        binding = NativeBinding.model_validate(session["native_binding"])
        try:
            execution = SessionExecution.model_validate(session["execution"])
        except (KeyError, ValidationError):
            execution = SessionExecution(
                control_scope_granted=[],
                owner=OwnerLease(state="not_acquired", session_id=None,
                                 lease_expires_at_backend_monotonic_s=None),
                recording_required_for_motion=True,
                recording_begin_required=True,
                recording_ready=False,
                motion_ready=False,
                motion_blockers=["legacy_session_document"],
                observed_at=utc_now(),
                source="prepared",
            )
        blockers: list[str] = []
        stored_stop = session.get("stop_receipt")
        stored_end = session.get("recording_end_receipt")
        history = {
            "last_stop_code": stored_stop["code"] if stored_stop else None,
            "last_end_code": stored_end["code"] if stored_end else None,
            "recording_integrity": stored_end["integrity"] if stored_end else None,
        }

        def add(key: str) -> None:
            if key not in blockers:
                blockers.append(key)

        stored_snapshot = None
        try:
            stored_snapshot = self.store.get_snapshot(session["snapshot_id"])
        except PreparationError:
            pass
        snapshot_ok = bool(
            stored_snapshot is not None
            and stored_snapshot["execution_eligible"]
            and stored_snapshot["recipe_fingerprint"] == self.recipe.fingerprint
        )
        recipe_ok = session["recipe_fingerprint"] == self.recipe.fingerprint
        if stored_snapshot is None:
            add("snapshot_not_found")
        elif not stored_snapshot["execution_eligible"]:
            add("snapshot_not_eligible")
        if not recipe_ok:
            add("recipe_changed")

        try:
            observation = self.validator.observe()
        except ReadServiceError as exc:
            add(exc.code)
            return SessionCurrent(
                observed_at=now, valid=False, status="offline", error=str(exc),
                runtime_identity=None, runtime_identity_matches=False,
                binding=CurrentBinding(
                    binding_id=binding.binding_id, state="unverified", matches=False,
                    readback_sha256=None, error=str(exc),
                ),
                snapshot_id=session["snapshot_id"], snapshot_eligible=snapshot_ok,
                recipe_fingerprint_matches=recipe_ok,
                control_scope_granted=execution.control_scope_granted,
                recording_required_for_motion=execution.recording_required_for_motion,
                recording_begin_required=execution.recording_begin_required,
                recording=CurrentRecording(
                    status="UNKNOWN", episode_id=None, segment_id=None,
                    command_capture_ready=False, error=None, ready=False,
                ),
                owner=CurrentOwner(
                    state="unknown", session_id=None,
                    lease_expires_at_backend_monotonic_s=None,
                ),
                safety_latched=None, recording_ready=False, motion_ready=False,
                start_available=False, recording_begin_available=False,
                stop_available=False, recording_end_available=False,
                session_stop_protocol=None, recording_end_protocol=None,
                **history,
                blockers=blockers,
            )

        identity_matches = observation.runtime_identity == identity
        if not identity_matches:
            add("runtime_identity_changed")
        if observation.session_binding_protocol != self.recipe.required_protocols["session_binding"]:
            add("session_binding_unsupported")
        required_begin = self.recipe.required_protocols["recording_begin"]
        if observation.recording_begin_protocol != required_begin:
            add("recording_begin_unsupported")
        if observation.recording_required_for_motion != execution.recording_required_for_motion:
            add("native_recording_policy_changed")

        binding_state = "unverified"
        binding_matches = False
        readback_sha = None
        binding_error = None
        if binding.binding_id and binding.config_fingerprint:
            try:
                readback = self.binding.readback(binding.binding_id)
                readback_sha = digest(readback)
                reported = readback.get("state")
                binding_state = reported if reported in {
                    "prepared", "started", "expired", "invalidated", "released"
                } else "unverified"
                binding_matches = (
                    readback.get("binding_id") == binding.binding_id
                    and readback.get("session_id") == session["session_id"]
                    and readback.get("config_fingerprint") == binding.config_fingerprint
                    and readback.get("run_id") == identity.run_id
                    and readback.get("backend_generation") == identity.backend_generation
                    and readback.get("episode_id") == identity.episode_id
                    and readback.get("motion_commands_accepted") is not True
                )
                if not binding_matches:
                    add("native_binding_mismatch")
                if binding_state == "expired":
                    add("native_binding_expired")
                elif binding_state == "invalidated":
                    add("native_binding_invalidated")
                elif binding_state == "released":
                    add("native_binding_released")
                elif binding_state not in {"prepared", "started"}:
                    add("native_binding_unverified")
            except BindingError as exc:
                binding_error = str(exc)
                binding_state = "missing" if exc.http_status == 404 else "unverified"
                add("native_binding_missing" if binding_state == "missing" else "native_binding_unverified")
        else:
            binding_error = "Session has no verified binding identifier"
            add("native_binding_unverified")
        if session["state"] == "active" and binding_state != "started":
            add("native_binding_not_started")

        recording_ready = bool(
            identity_matches and binding_state == "started"
            and observation.recording_status == "RECORDING"
            and observation.recording_command_capture_ready
            and observation.recording_episode_id == identity.episode_id
            and not observation.recording_error
        )
        if observation.recording_status == "FAILED":
            add("native_recording_failed")
        elif observation.recording_status in {"STARTING", "DRAINING"}:
            add("native_recording_transitioning")
        requires_recording = bool(
            execution.recording_required_for_motion
            or observation.recording_required_for_motion
        )
        if requires_recording and not recording_ready:
            add("recording_not_ready")

        owners = [
            owner for owner in (
                observation.base_owner_session_id, observation.arm_owner_session_id
            ) if owner
        ]
        if owners:
            add("control_owner_present")
        if observation.safety_latched:
            add("safety_latched")
        if not execution.control_scope_granted:
            add("control_scope_empty")
        if session["state"] != "active":
            add("session_not_active")

        active_recording = observation.recording_status in {"STARTING", "RECORDING", "DRAINING"}
        valid = bool(
            identity_matches and snapshot_ok and recipe_ok and binding_matches
            and binding_state in {"prepared", "started"}
            and not (session["state"] == "active" and binding_state != "started")
        )
        start_available = bool(
            session["state"] == "prepared" and valid
            and binding_state in {"prepared", "started"}
            and observation.session_binding_protocol == self.recipe.required_protocols["session_binding"]
            and observation.recording_status == "IDLE"
            and not observation.safety_latched and not owners
        )
        recording_begin_available = bool(
            session["state"] == "active" and valid and identity_matches and snapshot_ok
            and recipe_ok and binding_matches and binding_state == "started"
            and observation.recording_begin_protocol == required_begin
            and observation.recording_status not in {"STARTING", "RECORDING", "DRAINING", "FAILED"}
        )
        motion_ready = bool(
            valid and session["state"] == "active" and binding_state == "started"
            and (not requires_recording or recording_ready)
            and not observation.safety_latched and not owners
            and bool(execution.control_scope_granted)
        )
        required_stop = self.recipe.required_protocols.get("session_stop")
        required_end = self.recipe.required_protocols.get("recording_end")
        stop_available = bool(
            valid and session["state"] in {"prepared", "active"}
            and binding_state in {"prepared", "started"}
            and required_stop is not None and observation.session_stop_protocol == required_stop
        )
        begun_segment = (session.get("recording_begin_receipt") or {}).get("recording_segment_id")
        recording_end_available = bool(
            valid and session["state"] == "active" and binding_state == "started"
            and required_end is not None and observation.recording_end_protocol == required_end
            and begun_segment is not None and observation.recording_segment_id == begun_segment
            and observation.recording_status in {"STARTING", "RECORDING", "DRAINING"}
        )
        if not identity_matches:
            status = "identity_changed"
        elif binding_state in {"expired", "invalidated", "released"}:
            status = binding_state
        elif not snapshot_ok or not recipe_ok:
            status = "snapshot_ineligible"
        elif not binding_matches or binding_state not in {"prepared", "started"}:
            status = "unverified"
        elif session["state"] == "active" and binding_state != "started":
            status = "unverified"
        else:
            status = binding_state
        return SessionCurrent(
            observed_at=now, valid=valid, status=status,
            error=binding_error,
            runtime_identity=observation.runtime_identity,
            runtime_identity_matches=identity_matches,
            binding=CurrentBinding(
                binding_id=binding.binding_id, state=binding_state,
                matches=binding_matches, readback_sha256=readback_sha,
                error=binding_error,
            ),
            snapshot_id=session["snapshot_id"], snapshot_eligible=snapshot_ok,
            recipe_fingerprint_matches=recipe_ok,
            control_scope_granted=execution.control_scope_granted,
            recording_required_for_motion=observation.recording_required_for_motion,
            recording_begin_required=execution.recording_begin_required,
            recording=CurrentRecording(
                status=observation.recording_status,
                episode_id=observation.recording_episode_id,
                segment_id=observation.recording_segment_id,
                command_capture_ready=observation.recording_command_capture_ready,
                error=observation.recording_error,
                ready=recording_ready,
            ),
            owner=CurrentOwner(
                state="held" if owners else "not_acquired",
                session_id=owners[0] if owners else None,
                lease_expires_at_backend_monotonic_s=None,
            ),
            safety_latched=observation.safety_latched,
            recording_ready=recording_ready, motion_ready=motion_ready,
            start_available=start_available,
            recording_begin_available=recording_begin_available,
            stop_available=stop_available,
            recording_end_available=recording_end_available,
            session_stop_protocol=observation.session_stop_protocol,
            recording_end_protocol=observation.recording_end_protocol,
            **history,
            blockers=blockers,
        )

    def _record_recording_attempt(self, session: dict, result: str, reason: str) -> None:
        session["recording_begin_attempts"] = [
            *session.get("recording_begin_attempts", []),
            RecordingAttempt(at=utc_now(), result=result, reason=reason).model_dump(),
        ]
        session["updated_at"] = utc_now()
        self.store.update_session(session)

    def _record_attempt(self, session: dict, result: str, blocking: list[StartBlock], detail: str) -> None:
        session["start_attempts"] = [*session["start_attempts"],
                                     StartAttempt(at=utc_now(), result=result, blocking=blocking, detail=detail).model_dump()]
        session["updated_at"] = utc_now()
        self.store.update_session(session)
