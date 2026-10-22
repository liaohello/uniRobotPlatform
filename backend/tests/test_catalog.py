from pathlib import Path

from unirobot.catalog import load_catalog
from unirobot.contracts import Maturity, TemplateId
from unirobot.settings import CONFIG_PATH


def test_catalog_loads_real_tasks():
    catalog = load_catalog(CONFIG_PATH)
    assert len(catalog.tasks) == 12
    assert {robot.id for robot in catalog.robots.values()} == {"landerpi", "so101_dual"}
    assert {adapter.id for adapter in catalog.adapters.values()} == {
        "mobilecar",
        "bimanual",
        "landerpi",
    }
    assert catalog.warnings == []


def test_every_task_has_existing_evidence():
    catalog = load_catalog(CONFIG_PATH)
    for task in catalog.tasks.values():
        assert task.evidence, task.id
        for path in task.evidence_paths:
            assert Path(path).exists(), f"{task.id}: {path}"


def test_adapters_are_consistent():
    catalog = load_catalog(CONFIG_PATH)
    for task in catalog.tasks.values():
        robot = catalog.robots[task.robot_id]
        assert task.adapter_id in catalog.adapters
        assert robot.adapter_id in catalog.adapters
        assert task.adapter_id == robot.adapter_id or task.adapter_id in catalog.adapters


def test_coverage_covers_all_templates():
    catalog = load_catalog(CONFIG_PATH)
    coverage = catalog.coverage()
    assert len(coverage.rows) == len(TemplateId)
    assert sum(row.tasks for row in coverage.rows) == len(catalog.tasks)
    states = {row.template: row.state for row in coverage.rows}
    assert states[TemplateId.NAV_POINT] == "verified"
    assert states[TemplateId.BI_DIRECT] == "verified"
    assert states[TemplateId.POLICY_ROLLOUT] == "partial"
    assert states[TemplateId.BI_SCREW] == "gap"


def test_maturity_partition():
    catalog = load_catalog(CONFIG_PATH)
    counts = catalog.summary_counts()
    assert counts == {
        "tasks": 12,
        "robots": 2,
        "adapters": 3,
        "verified": 8,
        "experimental": 4,
        "concept": 0,
    }
    assert catalog.list_tasks(maturity=Maturity.VERIFIED)
