"""Audit the module-level migration manifest.

The manifest never moves code by itself. It records the intended target and the
environment boundary so a module is only extracted after its contract is
stable and its runtime can still be tested in the source project.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .settings import MIGRATION_MANIFEST, REPO_ROOT

PROJECTS_ROOT = REPO_ROOT.parent


@dataclass
class ModuleAudit:
    id: str
    source: str
    target: str
    strategy: str
    priority: str
    declared: str
    source_exists: bool
    target_exists: bool
    source_lines: int
    state: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "strategy": self.strategy,
            "priority": self.priority,
            "declared": self.declared,
            "source_exists": self.source_exists,
            "target_exists": self.target_exists,
            "source_lines": self.source_lines,
            "state": self.state,
        }


def _line_count(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        with path.open("rb") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    target = path or MIGRATION_MANIFEST
    return json.loads(target.read_text(encoding="utf-8"))


def audit(path: Path | None = None) -> dict[str, Any]:
    manifest = load_manifest(path)
    modules: list[ModuleAudit] = []
    for item in manifest.get("modules", []):
        source = (PROJECTS_ROOT / item["source"]).resolve()
        target = (REPO_ROOT / item["target"]).resolve()
        source_exists = source.exists()
        target_exists = target.exists()
        declared = item.get("status", "pending")
        if declared == "done":
            state = "done"
        elif target_exists:
            state = "in_progress"
        elif not source_exists:
            state = "blocked"
        else:
            state = "pending"
        modules.append(
            ModuleAudit(
                id=item["id"],
                source=item["source"],
                target=item["target"],
                strategy=item.get("strategy", "extract"),
                priority=item.get("priority", "P2"),
                declared=declared,
                source_exists=source_exists,
                target_exists=target_exists,
                source_lines=_line_count(source),
                state=state,
            )
        )
    counts: dict[str, int] = {}
    for module in modules:
        counts[module.state] = counts.get(module.state, 0) + 1
    return {
        "manifest_version": manifest.get("version"),
        "strategy": manifest.get("strategy"),
        "modules": [module.as_dict() for module in modules],
        "counts": counts,
        "environments": manifest.get("environments", []),
        "do_not_migrate": manifest.get("do_not_migrate", []),
        "phases": manifest.get("phases", []),
    }


def _print_table(report: dict[str, Any]) -> None:
    print(f"manifest {report['manifest_version']} · {report['strategy']}")
    print(f"{'STATE':<12}{'PRI':<4}{'LINES':>6}  {'ID':<28} SOURCE")
    for item in report["modules"]:
        print(
            f"{item['state']:<12}{item['priority']:<4}{item['source_lines']:>6}  "
            f"{item['id']:<28} {item['source']}"
        )
    print()
    print("counts:", ", ".join(f"{key}={value}" for key, value in report["counts"].items()))
    print("environments:")
    for env in report["environments"]:
        print(
            f"  - {env.get('project')}: python {env.get('python')}, "
            f"mujoco {env.get('mujoco')}, isolated={env.get('isolated')}"
        )
    print("do not migrate:")
    for item in report["do_not_migrate"]:
        print(f"  - {item.get('path')}: {item.get('reason')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit the backend migration manifest")
    parser.add_argument("command", nargs="?", default="status", choices=("status",))
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = audit(args.manifest)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_table(report)
    return 0 if report["counts"].get("blocked", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
