"""Public contracts of the unified platform.

The gateway does not import MuJoCo. It presents tasks from isolated runtime
projects and records which one owns the stepping loop for a run.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Maturity(str, Enum):
    VERIFIED = "verified"
    EXPERIMENTAL = "experimental"
    CONCEPT = "concept"


MATURITY_RANK = {
    Maturity.CONCEPT: 0,
    Maturity.EXPERIMENTAL: 1,
    Maturity.VERIFIED: 2,
}


class TaskMode(str, Enum):
    TELEOP = "teleop"
    HUMAN_DEMO = "human_demo"
    EXPERT = "expert"
    POLICY = "policy"
    REPLAY = "replay"
    BATCH = "batch"


class TemplateId(str, Enum):
    NAV_POINT = "NAV-POINT"
    NAV_ROUTE = "NAV-ROUTE"
    NAV_OBJECT = "NAV-OBJECT"
    MOBILE_GRASP = "MOBILE-GRASP"
    BI_DIRECT = "BI-DIRECT"
    BI_TABLE_TRANSFER = "BI-TABLE-TRANSFER"
    BI_HANDOVER = "BI-HANDOVER"
    BI_SCREW = "BI-SCREW"
    PER_FAR = "PER-FAR"
    PER_RGBD = "PER-RGBD"
    PER_RELATIVE = "PER-RELATIVE"
    PER_SERVO = "PER-SERVO"
    IK_FIXED = "IK-FIXED"
    IK_BASE_ASSIST = "IK-BASE-ASSIST"
    POLICY_ROLLOUT = "POLICY-ROLLOUT"
    DATA_COLLECTION = "DATA-COLLECTION"


class Capability(str, Enum):
    BASE_MECANUM = "base.mecanum"
    BASE_NAV2 = "base.nav2"
    ARM_5DOF = "arm.5dof"
    ARM_6DOF = "arm.6dof"
    GRIPPER = "gripper"
    RGB = "sensor.rgb"
    DEPTH = "sensor.depth"
    LIDAR = "sensor.lidar"
    IMU = "sensor.imu"
    LEADER_ARM = "leader.so101"
    ROS2 = "bus.ros2"
    LEROBOT = "format.lerobot"


class AdapterState(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    NOT_CONFIGURED = "not_configured"


class RunState(str, Enum):
    PREPARED = "prepared"
    LAUNCHING = "launching"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


ACTIVE_RUN_STATES = {RunState.PREPARED, RunState.LAUNCHING, RunState.RUNNING}


class LaunchSpec(Contract):
    argv: list[str] = Field(min_length=1)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: str | None = None


class AdapterConfig(Contract):
    id: str
    title: str
    project_root: str
    base_url: str | None = None
    health_path: str = "/api/health"
    console_path: str = "/"
    launch: LaunchSpec | None = None
    auth_env: str | None = None
    notes: list[str] = Field(default_factory=list)


class RobotConfig(Contract):
    id: str
    title: str
    adapter_id: str
    summary: str
    capabilities: list[Capability] = Field(default_factory=list)
    model_ref: str | None = None
    notes: list[str] = Field(default_factory=list)


class TaskConfig(Contract):
    id: str
    title: str
    summary: str
    robot_id: str
    adapter_id: str | None = None
    template: TemplateId
    maturity: Maturity
    modes: list[TaskMode] = Field(min_length=1)
    capabilities: list[Capability] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    native_launch: str
    native_console: str | None = None
    caveats: list[str] = Field(default_factory=list)
    spec_refs: list[str] = Field(default_factory=list)


class CatalogConfig(Contract):
    version: str
    adapters: list[AdapterConfig]
    robots: list[RobotConfig]
    tasks: list[TaskConfig]

    @field_validator("adapters", "robots", "tasks")
    @classmethod
    def unique_ids(cls, value: list[Any]) -> list[Any]:
        seen: set[str] = set()
        for item in value:
            if item.id in seen:
                raise ValueError(f"duplicate id: {item.id}")
            seen.add(item.id)
        return value


class AdapterStatus(Contract):
    adapter_id: str
    state: AdapterState
    base_url: str | None = None
    latency_ms: float | None = None
    version: str | None = None
    detail: str = ""
    checked_at: str = Field(default_factory=utc_now)


class TaskDescriptor(TaskConfig):
    source_project: str
    adapter_id: str
    evidence_paths: list[str] = Field(default_factory=list)


class TaskView(TaskDescriptor):
    adapter: AdapterStatus
    available: bool


class RobotView(RobotConfig):
    adapter: AdapterStatus
    task_count: int


class CoverageRow(Contract):
    template: TemplateId
    tasks: int
    verified: int
    experimental: int
    concept: int
    state: str


class CoverageReport(Contract):
    rows: list[CoverageRow]
    verified: int
    partial: int
    gap: int


class RunSpec(Contract):
    task_id: str
    mode: TaskMode | None = None
    seed: int | None = None
    record: bool = True
    operator: str = "operator"
    launch: bool = False
    overrides: dict[str, str] = Field(default_factory=dict)


class RunRecord(Contract):
    run_id: str
    task_id: str
    robot_id: str
    adapter_id: str
    mode: TaskMode
    state: RunState
    created_at: str = Field(default_factory=utc_now)
    started_at: str | None = None
    ended_at: str | None = None
    native_command: str = ""
    native_run_id: str | None = None
    notes: list[str] = Field(default_factory=list)
    error: str | None = None


class PlatformSummary(Contract):
    version: str
    tasks: int
    robots: int
    adapters: int
    verified: int
    experimental: int
    concept: int
    active_runs: int
    launch_enabled: bool = False
    coverage: CoverageReport
    warnings: list[str] = Field(default_factory=list)
