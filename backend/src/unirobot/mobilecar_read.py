"""Typed, read-only workbench projection of the native mobilecar-1.0 HTTP API.

No native imports, physics, control, leases or recorder writes. Unknown native
fields are dropped at this network boundary, particularly diagnostics/Oracle.
"""
from __future__ import annotations

import hashlib
import re
from typing import Annotated, Any, Literal, TypeVar
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, ValidationError, model_validator

from .contracts import utc_now
from .mobilecar import Health, MobileCarIntegration, NativeReadError, RecordingState, RuntimeIdentity, SceneIdentity

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Vec3 = Annotated[list[Number], Field(min_length=3, max_length=3)]
Quat = Annotated[list[Number], Field(min_length=4, max_length=4)]
Pair = Annotated[list[Number], Field(min_length=2, max_length=2)]
AssetId = Annotated[StrictStr, Field(pattern=r"^[A-Za-z0-9_.-]{1,128}$")]
Digest = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]


class NativeModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Transform(NativeModel):
    position_m: Vec3
    orientation_xyzw: Quat


class Geom(NativeModel):
    name: StrictStr = Field(min_length=1)
    geom_type: Literal["box", "sphere", "ellipsoid", "cylinder", "capsule", "plane", "mesh", "heightfield", "unknown"]
    size_m: list[Number]
    local_transform: Transform
    rgba: Quat
    mesh_asset_id: AssetId | None
    collision: StrictBool
    group: StrictInt


class Link(NativeModel):
    name: StrictStr = Field(min_length=1)
    parent_name: StrictStr | None
    joint_name: StrictStr | None
    joint_type: Literal["free", "ball", "slide", "hinge", "fixed", "unknown"]
    joint_axis: Vec3
    local_transform: Transform
    geoms: list[Geom]


class Asset(NativeModel):
    asset_id: AssetId
    uri: StrictStr
    sha256: Digest
    media_type: Literal["model/stl"]


class SceneData(SceneIdentity):
    links: list[Link]
    world_links: list[Link]
    mesh_assets: list[Asset]
    camera_ids: list[StrictStr]
    tcp_site: StrictStr
    source: StrictStr

    @model_validator(mode="after")
    def references(self):
        links = self.links + self.world_links
        names = [link.name for link in links]
        assets = [asset.asset_id for asset in self.mesh_assets]
        if len(names) != len(set(names)) or len(assets) != len(set(assets)):
            raise ValueError("duplicate link or asset ID")
        for link in links:
            if link.parent_name is not None and link.parent_name not in names:
                raise ValueError("unknown parent link")
            geom_names = [geom.name for geom in link.geoms]
            if len(geom_names) != len(set(geom_names)):
                raise ValueError("duplicate geometry ID within a link")
            if any(geom.mesh_asset_id is not None and geom.mesh_asset_id not in assets for geom in link.geoms):
                raise ValueError("unknown mesh asset")
        if any(asset.asset_id in {".", ".."} for asset in self.mesh_assets):
            raise ValueError("invalid asset ID")
        return self


class CapabilitiesData(SceneIdentity):
    backend_kind: StrictStr
    arm_joint_names: list[StrictStr]
    arm_user_limits_rad: list[Pair]
    arm_velocity_limits_rad_s: list[Number]
    gripper_min_width_m: Number
    gripper_max_width_m: Number
    base_linear_limit_m_s: Number
    base_yaw_limit_rad_s: Number
    tcp_position_tolerance_m: Number
    tcp_orientation_is_soft: StrictBool
    supported_commands: list[StrictStr]
    sensor_streams: list[StrictStr]
    camera_parent_body: StrictStr
    tcp_parent_body: StrictStr
    ground_truth_policy_visible: StrictBool

    @model_validator(mode="after")
    def joint_order(self):
        n = len(self.arm_joint_names)
        if n == 0 or len(set(self.arm_joint_names)) != n or len(self.arm_user_limits_rad) != n or len(self.arm_velocity_limits_rad_s) != n:
            raise ValueError("joint names and limit arrays must have the same nonzero length")
        if any(low > high for low, high in self.arm_user_limits_rad):
            raise ValueError("reversed joint limits")
        return self


class BaseActual(NativeModel):
    frame_id: Literal["base_link"]
    position_world_sim_m: Vec3
    orientation_world_sim_xyzw: Quat
    vx_m_s: Number
    vy_m_s: Number
    wz_rad_s: Number
    stopped: StrictBool
    stop_latched: StrictBool


class BaseNative(BaseActual):
    requested_vx_m_s: Number
    requested_vy_m_s: Number
    requested_wz_rad_s: Number


class ArmActual(NativeModel):
    user_joint_positions_rad: list[Number]
    model_joint_positions_rad: list[Number]
    joint_velocities_rad_s: list[Number]
    joint_torques_nm: list[Number]
    joint_margin_rad: list[Number]
    model_limits_rad: list[Pair]
    coordinates_status: StrictStr


class ArmNative(ArmActual):
    user_joint_targets_rad: list[Number]
    model_joint_targets_rad: list[Number]


class GripperActual(NativeModel):
    width_m: Number
    model_drive_position_rad: Number


class GripperNative(GripperActual):
    target_width_m: Number
    model_drive_target_rad: Number


class TCPActual(NativeModel):
    frame_id: Literal["world_sim"]
    position_m: Vec3
    orientation_xyzw: Quat
    position_error_m: Number | None
    orientation_error_rad: Number | None
    held: StrictBool


class SensorReference(NativeModel):
    kind: StrictStr
    available: StrictBool
    fresh: StrictBool
    sample_id: StrictStr | None
    stream_id: StrictStr | None
    measurement_time_s: Number | None
    arrival_time_s: Number | None
    clock_id: StrictStr
    valid_fraction: Number | None
    quality: StrictStr
    capture_sim_time_s: Number | None
    capture_backend_monotonic_s: Number | None
    capture_control_tick_id: StrictStr | None
    feedback_sample_id: StrictStr | None
    observation_age_s: Number | None
    profile_id: StrictStr | None
    native_asset_uri: StrictStr | None = Field(validation_alias="asset_uri")
    frame_id: None = None  # native SensorState does not expose the observation Frame


class NativeRecording(RecordingState):
    episode_id: StrictStr | None
    queued_events: StrictInt
    dropped_events: StrictInt
    error: StrictStr | None


class NativeSnapshot(RuntimeIdentity):
    contract_version: Literal["mobilecar-1.0"]
    episode_started_backend_monotonic_s: Number
    backend_monotonic_s: Number
    sim_time_s: Number
    feedback_time_s: Number
    wall_utc: StrictStr
    clock_id: StrictStr
    control_tick_id: StrictStr
    task_phase: StrictStr
    base: BaseNative
    arm: ArmNative
    gripper: GripperNative
    tcp: TCPActual
    sensors: list[SensorReference]
    model_joint_positions_rad: dict[StrictStr, Number]
    base_owner_session_id: StrictStr | None
    arm_owner_session_id: StrictStr | None
    active_session_id: StrictStr | None
    active_operator_kind: StrictStr | None
    safety_latched: StrictBool
    recording: NativeRecording


class ObjectIdentity(BaseModel):
    object_id: str
    kind: Literal["robot_link", "world_link", "joint", "geom"]
    native_name: str
    parent_object_id: str | None


class ReadEnvelope(BaseModel):
    schema_version: Literal["unirobot-mobilecar-read-1"] = "unirobot-mobilecar-read-1"
    data_source: Literal["live_native_http"] = "live_native_http"
    adapter_id: Literal["mobilecar"] = "mobilecar"
    robot_id: Literal["landerpi"] = "landerpi"
    read_only: Literal[True] = True
    session_ready: Literal[False] = False
    platform_session_id: None = None
    retrieved_at: str
    runtime_identity: RuntimeIdentity
    resource_identity: SceneIdentity
    interface_profile: str
    recording_required_for_motion: bool
    resource_matches_pin: bool
    deployed_content_verified: Literal[False] = False


class SceneRead(ReadEnvelope):
    data: SceneData
    objects: list[ObjectIdentity]
    world_pose_semantics: Literal["compiled_initial_layout_not_live_object_state"] = "compiled_initial_layout_not_live_object_state"


class CapabilitiesRead(ReadEnvelope):
    data: CapabilitiesData
    platform_commands_available: Literal[False] = False
    platform_recording_available: Literal[False] = False
    platform_replay_available: Literal[False] = False


class ActualState(BaseModel):
    base: BaseActual
    arm: ArmActual
    gripper: GripperActual
    tcp: TCPActual
    model_joint_positions_rad: dict[str, Number]


class BaseVelocityTarget(BaseModel):
    frame_id: Literal["base_link"] = "base_link"
    vx_m_s: Number
    vy_m_s: Number
    wz_rad_s: Number


class TargetState(BaseModel):
    base_velocity: BaseVelocityTarget
    user_joint_positions_rad: list[Number]
    model_joint_positions_rad: list[Number]
    gripper_width_m: Number
    gripper_model_drive_position_rad: Number
    command_id: None = None  # native snapshot does not bind targets to a command ID
    tcp: None = None  # no command-correlated TCP target in this read projection


class SourceTime(BaseModel):
    episode_started_backend_monotonic_s: Number
    backend_monotonic_s: Number
    sim_time_s: Number
    feedback_time_s: Number
    wall_utc: str
    clock_id: str
    control_tick_id: str


class ObservedAuthority(BaseModel):
    base_owner_session_id: str | None
    arm_owner_session_id: str | None
    active_session_id: str | None
    active_operator_kind: str | None
    authorizes_caller: Literal[False] = False
    lease_status: Literal["not_exposed"] = "not_exposed"


class SnapshotData(BaseModel):
    time: SourceTime
    arm_joint_names: list[str]
    actual: ActualState
    target: TargetState
    preview: None = None
    sensors: list[SensorReference]
    sensor_media_status: Literal["not_exposed"] = "not_exposed"
    authority: ObservedAuthority
    safety_latched: bool
    recording: NativeRecording
    task_phase: str


class SnapshotRead(ReadEnvelope):
    data: SnapshotData


class ReadServiceError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.code, self.status_code = code, status_code


Model = TypeVar("Model", bound=BaseModel)


class MobileCarReadService:
    def __init__(self, integration: MobileCarIntegration):
        self.integration = integration

    def _read(self, path: str, model: type[Model]) -> Model:
        try:
            return model.model_validate(self.integration._read(path))
        except NativeReadError as exc:
            status = 503 if exc.status in {"not_configured", "offline"} else 502
            raise ReadServiceError(f"native_{exc.status}", str(exc), status) from exc
        except ValidationError as exc:
            fields = ", ".join(".".join(map(str, e["loc"])) for e in exc.errors())
            raise ReadServiceError("native_incompatible", f"{path}: invalid native fields: {fields}") from exc

    def _finish(self, before: Health, resource: SceneIdentity) -> dict[str, Any]:
        after = self._read("/api/v1/health", Health)
        identity = RuntimeIdentity.model_validate(after.model_dump())
        if any(getattr(before, key) != getattr(after, key) for key in ("run_id", "backend_generation", "episode_id", "interface_profile", "recording_required_for_motion")):
            raise ReadServiceError("native_identity_changed", "Native runtime changed during reads; reload the scene and state", 409)
        expected = self.integration.pin["expected"]
        return dict(
            retrieved_at=utc_now(), runtime_identity=identity, resource_identity=resource,
            interface_profile=after.interface_profile, recording_required_for_motion=after.recording_required_for_motion,
            resource_matches_pin=all(getattr(resource, key) == expected[key] for key in ("model_id", "model_sha256", "scene_id")),
        )

    def capabilities(self) -> CapabilitiesRead:
        before = self._read("/api/v1/health", Health)
        data = self._read("/api/v1/capabilities", CapabilitiesData)
        return CapabilitiesRead(**self._finish(before, SceneIdentity.model_validate(data.model_dump())), data=data)

    def scene(self) -> SceneRead:
        before = self._read("/api/v1/health", Health)
        data = self._read("/api/v1/scene", SceneData)
        objects = []
        # Native body/joint names are stable only within the exact resource identity.
        for kind, links in (("robot_link", data.links), ("world_link", data.world_links)):
            for link in links:
                object_id = f"body:{quote(link.name, safe='')}"
                objects.append(ObjectIdentity(object_id=object_id, kind=kind, native_name=link.name, parent_object_id=f"body:{quote(link.parent_name, safe='')}" if link.parent_name else None))
                if link.joint_name:
                    objects.append(ObjectIdentity(object_id=f"joint:{quote(link.joint_name, safe='')}", kind="joint", native_name=link.joint_name, parent_object_id=object_id))
                for geom in link.geoms:
                    objects.append(ObjectIdentity(object_id=f"geom:{quote(link.name, safe='')}/{quote(geom.name, safe='')}", kind="geom", native_name=geom.name, parent_object_id=object_id))
        for asset in data.mesh_assets:
            asset.uri = f"/api/v1/mobilecar/scene/assets/{asset.asset_id}?sha256={asset.sha256}"
        return SceneRead(**self._finish(before, SceneIdentity.model_validate(data.model_dump())), data=data, objects=objects)

    def snapshot(self) -> SnapshotRead:
        before = self._read("/api/v1/health", Health)
        capabilities = self._read("/api/v1/capabilities", CapabilitiesData)
        value = self._read("/api/v1/snapshot", NativeSnapshot)
        if any(getattr(before, key) != getattr(value, key) for key in ("run_id", "backend_generation", "episode_id")):
            raise ReadServiceError("native_identity_changed", "Snapshot belongs to another runtime or Episode; reload", 409)
        n = len(capabilities.arm_joint_names)
        if any(len(getattr(value.arm, key)) != n for key in ArmNative.model_fields if isinstance(getattr(value.arm, key), list)):
            raise ReadServiceError("native_incompatible", "Snapshot joint arrays do not match capability joint order")
        data = SnapshotData(
            time=SourceTime.model_validate(value.model_dump()), arm_joint_names=capabilities.arm_joint_names,
            actual=ActualState(base=BaseActual.model_validate(value.base.model_dump()), arm=ArmActual.model_validate(value.arm.model_dump()),
                gripper=GripperActual.model_validate(value.gripper.model_dump()), tcp=value.tcp, model_joint_positions_rad=value.model_joint_positions_rad),
            target=TargetState(base_velocity=BaseVelocityTarget(vx_m_s=value.base.requested_vx_m_s, vy_m_s=value.base.requested_vy_m_s, wz_rad_s=value.base.requested_wz_rad_s),
                user_joint_positions_rad=value.arm.user_joint_targets_rad, model_joint_positions_rad=value.arm.model_joint_targets_rad,
                gripper_width_m=value.gripper.target_width_m, gripper_model_drive_position_rad=value.gripper.model_drive_target_rad),
            sensors=value.sensors,
            authority=ObservedAuthority.model_validate(value.model_dump()), safety_latched=value.safety_latched,
            recording=value.recording, task_phase=value.task_phase,
        )
        return SnapshotRead(**self._finish(before, SceneIdentity.model_validate(capabilities.model_dump())), data=data)

    def asset(self, asset_id: str, expected_sha256: str) -> bytes:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", asset_id) or asset_id in {".", ".."}:
            raise ReadServiceError("unknown_asset", "Unknown scene asset", 404)
        asset = next((a for a in self.scene().data.mesh_assets if a.asset_id == asset_id), None)
        if asset is None:
            raise ReadServiceError("unknown_asset", "Unknown scene asset", 404)
        if asset.sha256 != expected_sha256:
            raise ReadServiceError("asset_revision_changed", "Asset digest changed; reload the scene manifest", 409)
        try:
            body = self.integration.read_scene_asset(asset_id)
        except NativeReadError as exc:
            raise ReadServiceError(f"native_{exc.status}", str(exc), 503 if exc.status in {"not_configured", "offline"} else 502) from exc
        if hashlib.sha256(body).hexdigest() != expected_sha256:
            raise ReadServiceError("asset_integrity_failed", "Native asset bytes do not match the scene digest")
        return body
