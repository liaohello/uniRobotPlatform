"""Config-driven task catalog.

Adapters are data first: a project, an HTTP health endpoint and an optional
launch command. A task becomes visible only when it names a real robot, a real
template and an evidence file that exists in the source project.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import yaml

from .contracts import (
    AdapterConfig,
    CatalogConfig,
    CoverageReport,
    CoverageRow,
    Maturity,
    RobotConfig,
    TaskDescriptor,
    TemplateId,
)
from .settings import REPO_ROOT

_TEMPLATE_ORDER = list(TemplateId)


class CatalogError(ValueError):
    pass


class Catalog:
    def __init__(
        self,
        config: CatalogConfig,
        *,
        adapters: dict[str, AdapterConfig],
        robots: dict[str, RobotConfig],
        tasks: dict[str, TaskDescriptor],
        warnings: list[str],
    ) -> None:
        self.config = config
        self.adapters = adapters
        self.robots = robots
        self.tasks = tasks
        self.warnings = warnings

    @property
    def version(self) -> str:
        return self.config.version

    def list_tasks(
        self,
        *,
        robot_id: str | None = None,
        maturity: Maturity | None = None,
        template: TemplateId | None = None,
    ) -> list[TaskDescriptor]:
        values = list(self.tasks.values())
        if robot_id:
            values = [task for task in values if task.robot_id == robot_id]
        if maturity:
            values = [task for task in values if task.maturity == maturity]
        if template:
            values = [task for task in values if task.template == template]
        return sorted(values, key=lambda task: (task.source_project, task.id))

    def coverage(self) -> CoverageReport:
        rows: list[CoverageRow] = []
        for template in _TEMPLATE_ORDER:
            matching = [task for task in self.tasks.values() if task.template == template]
            verified = sum(1 for task in matching if task.maturity == Maturity.VERIFIED)
            experimental = sum(
                1 for task in matching if task.maturity == Maturity.EXPERIMENTAL
            )
            concept = sum(1 for task in matching if task.maturity == Maturity.CONCEPT)
            state = (
                "verified"
                if verified
                else "partial"
                if experimental or concept
                else "gap"
            )
            rows.append(
                CoverageRow(
                    template=template,
                    tasks=len(matching),
                    verified=verified,
                    experimental=experimental,
                    concept=concept,
                    state=state,
                )
            )
        return CoverageReport(
            rows=rows,
            verified=sum(1 for row in rows if row.state == "verified"),
            partial=sum(1 for row in rows if row.state == "partial"),
            gap=sum(1 for row in rows if row.state == "gap"),
        )

    def summary_counts(self) -> dict[str, int]:
        tasks = list(self.tasks.values())
        return {
            "tasks": len(tasks),
            "robots": len(self.robots),
            "adapters": len(self.adapters),
            "verified": sum(1 for task in tasks if task.maturity == Maturity.VERIFIED),
            "experimental": sum(
                1 for task in tasks if task.maturity == Maturity.EXPERIMENTAL
            ),
            "concept": sum(1 for task in tasks if task.maturity == Maturity.CONCEPT),
        }


def _resolve_under(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return (root / path).resolve() if not path.is_absolute() else path.resolve()


def _load_requirement_ids() -> set[str]:
    path = REPO_ROOT / "docs" / "specs" / "traceability.json"
    if not path.is_file():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {
        str(item.get("id", "")).upper()
        for item in payload.get("requirements", [])
        if item.get("id")
    }


def load_catalog(path: str | Path) -> Catalog:
    config_path = Path(path).expanduser().resolve()
    if not config_path.is_file():
        raise CatalogError(f"catalog not found: {config_path}")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    try:
        config = CatalogConfig.model_validate(raw)
    except Exception as exc:  # pydantic error is verbose enough
        raise CatalogError(f"invalid catalog: {exc}") from exc

    adapters = {adapter.id: adapter for adapter in config.adapters}
    robots = {robot.id: robot for robot in config.robots}
    warnings: list[str] = []
    requirement_ids = _load_requirement_ids()

    for adapter in config.adapters:
        root = _resolve_under(REPO_ROOT, adapter.project_root)
        if not root.is_dir():
            warnings.append(
                f"adapter {adapter.id}: project root missing: {adapter.project_root}"
            )

    for robot in config.robots:
        if robot.adapter_id not in adapters:
            raise CatalogError(
                f"robot {robot.id} references unknown adapter {robot.adapter_id}"
            )
        if not robot.capabilities:
            warnings.append(f"robot {robot.id}: no capabilities declared")

    tasks: dict[str, TaskDescriptor] = {}
    for task in config.tasks:
        robot = robots.get(task.robot_id)
        if robot is None:
            raise CatalogError(f"task {task.id} references unknown robot {task.robot_id}")
        adapter_id = task.adapter_id or robot.adapter_id
        adapter = adapters.get(adapter_id)
        if adapter is None:
            raise CatalogError(
                f"task {task.id} references unknown adapter {adapter_id}"
            )
        root = _resolve_under(REPO_ROOT, adapter.project_root)
        evidence_paths: list[str] = []
        for evidence in task.evidence:
            candidate = _resolve_under(root, evidence)
            if not candidate.exists():
                warnings.append(
                    f"task {task.id}: evidence missing: {adapter.project_root}/{evidence}"
                )
            evidence_paths.append(str(candidate))
        for ref in task.spec_refs:
            upper = ref.upper()
            if upper.startswith("REQ-") and requirement_ids and upper not in requirement_ids:
                warnings.append(f"task {task.id}: unknown requirement id {ref}")
        payload = task.model_dump()
        payload.update(
            source_project=Path(adapter.project_root).name,
            adapter_id=adapter_id,
            evidence_paths=evidence_paths,
        )
        tasks[task.id] = TaskDescriptor(**payload)

    if not tasks:
        warnings.append("catalog contains no tasks")

    return Catalog(
        config=config,
        adapters=adapters,
        robots=robots,
        tasks=tasks,
        warnings=warnings,
    )


def iter_evidence_paths(tasks: Iterable[TaskDescriptor]) -> Iterable[str]:
    for task in tasks:
        yield from task.evidence_paths
