"""FastAPI surface for task presentation and run preparation."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .adapters import build_adapters
from .catalog import Catalog, load_catalog
from .contracts import (
    AdapterStatus,
    CoverageReport,
    Maturity,
    PlatformSummary,
    RobotView,
    RunRecord,
    RunSpec,
    TaskView,
    TemplateId,
)
from .runtime import (
    InvalidMode,
    RunConflict,
    RunManager,
    RunNotFound,
    TaskNotFound,
)
from .settings import ALLOW_LAUNCH, CONFIG_PATH

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _manager(request: Request) -> RunManager:
    return request.app.state.manager


def _catalog(request: Request) -> Catalog:
    return request.app.state.catalog


def create_app(catalog_path: str | Path | None = None) -> FastAPI:
    path = Path(catalog_path) if catalog_path else CONFIG_PATH

    catalog = load_catalog(path)
    adapters = build_adapters(list(catalog.adapters.values()))
    manager = RunManager(catalog, adapters)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        try:
            yield
        finally:
            for run in manager.list_runs():
                if run.state.value in {"launching", "running"}:
                    manager.stop(run.run_id)

    application = FastAPI(
        title="uniRobotPlatform Gateway",
        version="0.1.0",
        description="统一任务呈现与后端迁移控制面；不直接步进 MuJoCo。",
        lifespan=lifespan,
    )
    application.state.catalog = catalog
    application.state.adapters = adapters
    application.state.manager = manager
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/v1/health")
    def health(request: Request) -> dict[str, Any]:
        manager = _manager(request)
        adapters = request.app.state.adapters
        statuses = [adapter.probe() for adapter in adapters.values()]
        return {
            "status": "ok",
            "version": application.version,
            "catalog_version": _catalog(request).version,
            "active_runs": manager.active_count(),
            "adapters": {item.adapter_id: item.state.value for item in statuses},
        }

    @application.get("/api/v1/platform", response_model=PlatformSummary)
    def platform(request: Request) -> PlatformSummary:
        catalog = _catalog(request)
        counts = catalog.summary_counts()
        return PlatformSummary(
            **counts,
            version=application.version,
            active_runs=_manager(request).active_count(),
            launch_enabled=ALLOW_LAUNCH,
            coverage=catalog.coverage(),
            warnings=catalog.warnings,
        )

    @application.get("/api/v1/adapters", response_model=list[AdapterStatus])
    def adapters(request: Request) -> list[AdapterStatus]:
        return [
            adapter.probe(force=True)
            for adapter in request.app.state.adapters.values()
        ]

    @application.get("/api/v1/adapters/{adapter_id}", response_model=AdapterStatus)
    def adapter_detail(adapter_id: str, request: Request) -> AdapterStatus:
        adapter = request.app.state.adapters.get(adapter_id)
        if adapter is None:
            raise HTTPException(status_code=404, detail=f"unknown adapter {adapter_id}")
        return adapter.probe(force=True)

    @application.get("/api/v1/robots", response_model=list[RobotView])
    def robots(request: Request) -> list[RobotView]:
        catalog = _catalog(request)
        values: list[RobotView] = []
        for robot in catalog.robots.values():
            adapter = request.app.state.adapters[robot.adapter_id]
            values.append(
                RobotView(
                    **robot.model_dump(),
                    adapter=adapter.probe(),
                    task_count=sum(
                        1 for task in catalog.tasks.values() if task.robot_id == robot.id
                    ),
                )
            )
        return values

    @application.get("/api/v1/tasks", response_model=list[TaskView])
    def tasks(
        request: Request,
        robot: str | None = Query(default=None),
        maturity: Maturity | None = Query(default=None),
        template: TemplateId | None = Query(default=None),
    ) -> list[TaskView]:
        catalog = _catalog(request)
        values: list[TaskView] = []
        for task in catalog.list_tasks(
            robot_id=robot, maturity=maturity, template=template
        ):
            adapter = request.app.state.adapters[task.adapter_id]
            status = adapter.probe()
            values.append(
                TaskView(
                    **task.model_dump(),
                    adapter=status,
                    available=status.state.value == "online",
                )
            )
        return values

    @application.get("/api/v1/tasks/{task_id}", response_model=TaskView)
    def task_detail(task_id: str, request: Request) -> TaskView:
        task = _catalog(request).tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"unknown task {task_id}")
        adapter = request.app.state.adapters[task.adapter_id]
        status = adapter.probe()
        return TaskView(
            **task.model_dump(),
            adapter=status,
            available=status.state.value == "online",
        )

    @application.get("/api/v1/coverage", response_model=CoverageReport)
    def coverage(request: Request) -> CoverageReport:
        return _catalog(request).coverage()

    @application.get("/api/v1/runs", response_model=list[RunRecord])
    def list_runs(request: Request) -> list[RunRecord]:
        return _manager(request).list_runs()

    @application.post("/api/v1/runs", response_model=RunRecord, status_code=201)
    def create_run(spec: RunSpec, request: Request) -> RunRecord:
        try:
            return _manager(request).create(spec)
        except TaskNotFound as exc:
            raise HTTPException(status_code=404, detail=f"unknown task {exc.args[0]}") from exc
        except InvalidMode as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RunConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.get("/api/v1/runs/{run_id}", response_model=RunRecord)
    def get_run(run_id: str, request: Request) -> RunRecord:
        try:
            return _manager(request).get(run_id)
        except RunNotFound as exc:
            raise HTTPException(status_code=404, detail=f"unknown run {run_id}") from exc

    @application.post("/api/v1/runs/{run_id}/stop", response_model=RunRecord)
    def stop_run(run_id: str, request: Request) -> RunRecord:
        try:
            return _manager(request).stop(run_id)
        except RunNotFound as exc:
            raise HTTPException(status_code=404, detail=f"unknown run {run_id}") from exc

    @application.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        manager: RunManager = websocket.app.state.manager
        try:
            while True:
                await websocket.send_json(
                    {
                        "type": "snapshot",
                        "runs": [run.model_dump(mode="json") for run in manager.list_runs()],
                        "adapters": [
                            status.model_dump(mode="json")
                            for status in (
                                adapter.probe()
                                for adapter in websocket.app.state.adapters.values()
                            )
                        ],
                    }
                )
                await asyncio.sleep(2.0)
        except (WebSocketDisconnect, RuntimeError):
            return

    if STATIC_DIR.is_dir():
        application.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="console")
    else:  # pragma: no cover - packaging guard
        @application.get("/", response_class=HTMLResponse)
        def placeholder() -> str:
            return (
                "<h1>uniRobot gateway</h1>"
                "<p>静态任务台未打包；API 见 <a href='/docs'>/docs</a>。</p>"
            )

    return application


app = create_app()
