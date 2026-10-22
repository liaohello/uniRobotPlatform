"""Run lifecycle for presented tasks.

One physical or simulated robot has at most one active run. The gateway never
steps physics; it records which adapter owns the run and keeps the native
command reproducible.
"""

from __future__ import annotations

import secrets
import threading
import time
from subprocess import Popen

from .adapters import Adapter, LaunchError
from .catalog import Catalog
from .contracts import (
    ACTIVE_RUN_STATES,
    AdapterState,
    RunRecord,
    RunSpec,
    RunState,
    utc_now,
)
from .settings import ALLOW_LAUNCH


class TaskNotFound(KeyError):
    pass


class RunNotFound(KeyError):
    pass


class RunConflict(RuntimeError):
    pass


class InvalidMode(ValueError):
    pass


class RunManager:
    def __init__(self, catalog: Catalog, adapters: dict[str, Adapter]) -> None:
        self.catalog = catalog
        self.adapters = adapters
        self._runs: dict[str, RunRecord] = {}
        self._processes: dict[str, Popen[str]] = {}
        self._lock = threading.RLock()

    def _new_id(self) -> str:
        return time.strftime("run-%Y%m%d-%H%M%S-") + secrets.token_hex(2)

    def _active_for(self, robot_id: str) -> RunRecord | None:
        for run in self._runs.values():
            if run.robot_id == robot_id and run.state in ACTIVE_RUN_STATES:
                return run
        return None

    def create(self, spec: RunSpec) -> RunRecord:
        task = self.catalog.tasks.get(spec.task_id)
        if task is None:
            raise TaskNotFound(spec.task_id)
        mode = spec.mode or task.modes[0]
        if mode not in task.modes:
            allowed = ", ".join(item.value for item in task.modes)
            raise InvalidMode(f"{mode.value} not supported by {task.id}; allowed: {allowed}")

        with self._lock:
            active = self._active_for(task.robot_id)
            if active is not None:
                raise RunConflict(
                    f"robot {task.robot_id} already has active run {active.run_id}"
                )
            adapter = self.adapters[task.adapter_id]
            status = adapter.probe()
            run_id = self._new_id()
            command = adapter.render_command(task, spec, run_id)
            notes: list[str] = []
            if status.state is not AdapterState.ONLINE:
                notes.append(
                    f"适配器 {adapter.id} 当前 {status.state.value}；已生成可复现命令，未建立实时连接。"
                )
            state = RunState.PREPARED
            error: str | None = None
            started_at: str | None = None
            process: Popen[str] | None = None

            if spec.launch:
                if not ALLOW_LAUNCH:
                    notes.append(
                        "网关未开启进程启动（UNIROBOT_ALLOW_LAUNCH!=1）；请按原生命令在源工程执行。"
                    )
                else:
                    try:
                        process = adapter.launch_task(task, spec, run_id, command)
                    except LaunchError as exc:
                        state = RunState.FAILED
                        error = str(exc)
                    else:
                        state = RunState.RUNNING
                        started_at = utc_now()
                        notes.append(f"进程已启动，pid={process.pid}。")

            record = RunRecord(
                run_id=run_id,
                task_id=task.id,
                robot_id=task.robot_id,
                adapter_id=adapter.id,
                mode=mode,
                state=state,
                started_at=started_at,
                native_command=command,
                notes=notes,
                error=error,
            )
            self._runs[run_id] = record
            if process is not None:
                self._processes[run_id] = process
            return record.model_copy(deep=True)

    def _refresh(self, run: RunRecord) -> None:
        process = self._processes.get(run.run_id)
        if process is None:
            return
        code = process.poll()
        if code is None:
            return
        run.ended_at = utc_now()
        if code == 0:
            run.state = RunState.STOPPED
        else:
            run.state = RunState.FAILED
            run.error = f"process exited with code {code}"
        self._processes.pop(run.run_id, None)

    def list_runs(self) -> list[RunRecord]:
        with self._lock:
            for run in self._runs.values():
                self._refresh(run)
            return [
                run.model_copy(deep=True)
                for run in sorted(
                    self._runs.values(), key=lambda item: item.created_at, reverse=True
                )
            ]

    def get(self, run_id: str) -> RunRecord:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise RunNotFound(run_id)
            self._refresh(run)
            return run.model_copy(deep=True)

    def stop(self, run_id: str) -> RunRecord:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise RunNotFound(run_id)
            if run.state not in ACTIVE_RUN_STATES:
                return run.model_copy(deep=True)
            run.state = RunState.STOPPING
            process = self._processes.get(run_id)
            if process is None:
                run.state = RunState.STOPPED
                run.ended_at = utc_now()
                run.notes.append("网关未持有该运行的进程；已在平台侧标记停止。")
                return run.model_copy(deep=True)
            adapter = self.adapters[run.adapter_id]
            adapter.stop_process(process)
            self._processes.pop(run_id, None)
            run.state = RunState.STOPPED
            run.ended_at = utc_now()
            run.notes.append("网关已终止其启动的进程组。")
            return run.model_copy(deep=True)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for run in self._runs.values() if run.state in ACTIVE_RUN_STATES)
