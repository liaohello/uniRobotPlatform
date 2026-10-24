"""FastAPI surface for task presentation and run preparation."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
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
    utc_now,
)
from .runtime import (
    InvalidMode,
    RunConflict,
    RunManager,
    RunNotFound,
    TaskNotFound,
)
from .mobilecar import MobileCarIntegration
from .mobilecar_read import CapabilitiesRead, MobileCarReadService, ReadServiceError, SceneRead, SnapshotRead
from .mobilecar_geometry import CompiledGeometryReadService, CompiledSceneRead, GeometryBundle
from .drafts import CreateDraft, CreateSession, DraftConflict, DraftNotFound, DraftStore, SaveDraft, ValidateDraft
from .prepare import (
    BeginRecording, ConfigurationSnapshot, EndRecording, PreparationError, PreparationService, PreparationStore,
    PreparedSession, SessionEnvelope, SessionList, StopSession, Validator,
)
from .recipe import Recipe, load_recipe
from .maps import MapError, MapList, MapStore, MapVersionView
from .routes import (
    CreateRouteDraft, MapRef, PublishRouteDraft, PublishResult, RouteDraft, RouteError, RouteService,
    RouteVersion, RouteVersionList, SaveRouteDraft,
)
from .settings import ALLOW_LAUNCH, CONFIG_PATH, DRAFT_DB_PATH, MAP_CATALOG_PATH, MAPS_ROOT

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _manager(request: Request) -> RunManager:
    return request.app.state.manager


def _catalog(request: Request) -> Catalog:
    return request.app.state.catalog


def create_app(catalog_path: str | Path | None = None, *, draft_db_path: Path | None = None,
               compiled_geometry_path: Path | None = None,
               mobilecar_integration: MobileCarIntegration | None = None,
               recipe: Recipe | None = None,
               map_catalog_path: Path | None = None,
               maps_root: Path | None = None) -> FastAPI:
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
    application.state.mobilecar_integration = mobilecar_integration or MobileCarIntegration(catalog.adapters.get("mobilecar"))
    geometry_path = compiled_geometry_path or os.environ.get("UNIROBOT_GEOMETRY_BUNDLE")
    geometry = GeometryBundle(Path(geometry_path)) if geometry_path else None

    def scene_service(request: Request):
        integration = request.app.state.mobilecar_integration
        return CompiledGeometryReadService(integration, geometry) if geometry else MobileCarReadService(integration)
    recipe = recipe or load_recipe()
    preparation_store = PreparationStore(draft_db_path or DRAFT_DB_PATH)
    preparation = PreparationService(preparation_store, Validator(recipe, application.state.mobilecar_integration), recipe)
    application.state.recipe = recipe
    application.state.preparation = preparation
    application.state.drafts = DraftStore(draft_db_path or DRAFT_DB_PATH, application.state.mobilecar_integration,
                                          recipe=recipe, preparation=preparation)
    map_store = MapStore(
        map_catalog_path or MAP_CATALOG_PATH,
        maps_root or MAPS_ROOT,
        reference_scene_id=recipe.expected.get("scene_id"),
        reference_model_sha256=recipe.expected.get("model_sha256"),
    )
    application.state.maps = map_store
    application.state.routes = RouteService(draft_db_path or DRAFT_DB_PATH, map_store)
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

    @application.get("/api/v1/mobilecar/preflight")
    def mobilecar_preflight(request: Request) -> dict[str, Any]:
        return request.app.state.mobilecar_integration.check()

    @application.exception_handler(ReadServiceError)
    async def native_read_error(request: Request, exc: ReadServiceError):
        return JSONResponse(status_code=exc.status_code, content={"detail": {
            "code": exc.code, "message": str(exc), "read_only": True, "session_ready": False,
        }})

    @application.get("/api/v1/mobilecar/capabilities", response_model=CapabilitiesRead)
    def mobilecar_capabilities(request: Request):
        return MobileCarReadService(request.app.state.mobilecar_integration).capabilities()

    @application.get("/api/v1/mobilecar/scene", response_model=CompiledSceneRead if geometry else SceneRead)
    def mobilecar_scene(request: Request):
        return scene_service(request).scene()

    @application.get("/api/v1/mobilecar/snapshot", response_model=SnapshotRead)
    def mobilecar_snapshot(request: Request):
        return MobileCarReadService(request.app.state.mobilecar_integration).snapshot()

    @application.get("/api/v1/mobilecar/scene/assets/{asset_id}")
    def mobilecar_scene_asset(asset_id: str, request: Request, sha256: str = Query(pattern=r"^[0-9a-f]{64}$")):
        body = scene_service(request).asset(asset_id, sha256)
        return Response(body, media_type="model/stl", headers={"ETag": f'"{sha256}"', "Cache-Control": "no-store"})

    @application.middleware("http")
    async def no_stale_workbench_reads(request: Request, call_next):
        response = await call_next(request)
        if (request.url.path.startswith("/api/v1/mobilecar/") or request.url.path.startswith("/api/v1/sessions")
            or request.url.path.startswith("/api/v1/maps") or request.url.path.startswith("/api/v1/routes")
            or request.url.path.startswith("/api/v1/route-drafts")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(DraftNotFound)
    async def missing_draft(request: Request, exc: DraftNotFound):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": {"code": "draft_not_found", "message": "Draft not found"}})

    @application.exception_handler(DraftConflict)
    async def stale_draft(request: Request, exc: DraftConflict):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=409, content={"detail": {"code": "conflict", "message": str(exc)}})

    @application.exception_handler(PreparationError)
    async def preparation_failure(request: Request, exc: PreparationError):
        return JSONResponse(status_code=exc.status_code,
                            content={"detail": {"code": exc.code, "message": str(exc), **exc.detail}})

    @application.exception_handler(MapError)
    async def map_failure(request: Request, exc: MapError):
        return JSONResponse(status_code=exc.status_code,
                            content={"detail": {"code": exc.code, "message": str(exc), **exc.detail}})

    @application.exception_handler(RouteError)
    async def route_failure(request: Request, exc: RouteError):
        return JSONResponse(status_code=exc.status_code,
                            content={"detail": {"code": exc.code, "message": str(exc), **exc.detail}})

    @application.get("/api/v1/experiment-drafts")
    def list_drafts(request: Request) -> list[dict]:
        return request.app.state.drafts.list()

    @application.post("/api/v1/experiment-drafts", status_code=201)
    def create_draft(spec: CreateDraft, request: Request) -> dict:
        return request.app.state.drafts.create(spec)

    @application.get("/api/v1/experiment-drafts/{draft_id}")
    def get_draft(draft_id: str, request: Request) -> dict:
        return request.app.state.drafts.get(draft_id)

    @application.put("/api/v1/experiment-drafts/{draft_id}")
    def save_draft(draft_id: str, spec: SaveDraft, request: Request) -> dict:
        return request.app.state.drafts.save(draft_id, spec)

    @application.post("/api/v1/experiment-drafts/{draft_id}/validate")
    def validate_draft(draft_id: str, spec: ValidateDraft, request: Request) -> dict:
        return request.app.state.drafts.validate(draft_id, spec)

    @application.post("/api/v1/sessions", response_model=SessionEnvelope, status_code=201)
    def create_session(spec: CreateSession, request: Request, response: Response):
        session, replayed = request.app.state.preparation.create_session(spec.model_dump())
        response.status_code = 200 if replayed else 201
        return {"session": session, "replayed": replayed}

    @application.get("/api/v1/sessions", response_model=SessionList)
    def list_sessions(request: Request) -> dict:
        return {
            "source": "stored",
            "live": False,
            "retrieved_at": utc_now(),
            "sessions": request.app.state.preparation.store.list_sessions(),
        }

    @application.get("/api/v1/sessions/{session_id}", response_model=PreparedSession)
    def get_session(session_id: str, request: Request) -> dict:
        preparation: PreparationService = request.app.state.preparation
        session = preparation.store.get_session(session_id)
        current = preparation.current_observation(session)
        return {**session, "current": current.model_dump()}

    @application.post("/api/v1/sessions/{session_id}/start", response_model=PreparedSession)
    def start_session(session_id: str, request: Request) -> dict:
        return request.app.state.preparation.start(session_id)

    @application.post("/api/v1/sessions/{session_id}/recording/begin", response_model=SessionEnvelope)
    def begin_recording(session_id: str, spec: BeginRecording, request: Request, response: Response):
        session, replayed = request.app.state.preparation.begin_recording(session_id, spec.model_dump())
        response.status_code = 200 if replayed else 201
        return {"session": session, "replayed": replayed}

    @application.post(
        "/api/v1/sessions/{session_id}/stop",
        response_model=SessionEnvelope,
        summary="Latched robot STOP for this Session's runtime identity",
        description=(
            "Sends the native latched STOP inside the lifecycle critical section and returns dispatch, "
            "parking and coverage evidence separately. It is not POST /api/v1/runs/{run_id}/stop, it never "
            "RESETs, never clears the safety latch and never ends the recording."
        ),
    )
    def stop_session(session_id: str, spec: StopSession, request: Request, response: Response):
        session, replayed = request.app.state.preparation.stop_session(session_id, spec.model_dump())
        response.status_code = 200 if replayed else 201
        return {"session": session, "replayed": replayed}

    @application.post(
        "/api/v1/sessions/{session_id}/recording/end",
        response_model=SessionEnvelope,
        summary="Stop and reliably finalize the recording segment this Session began",
        description=(
            "Identity-bound end of the Session's own recording segment. The receipt separates STOP dispatch, "
            "parking evidence, Recorder drain, finalize proof and episode integrity; a tail file alone is not "
            "reported as a complete recording."
        ),
    )
    def end_recording(session_id: str, spec: EndRecording, request: Request, response: Response):
        session, replayed = request.app.state.preparation.end_recording(session_id, spec.model_dump())
        response.status_code = 200 if replayed else 201
        return {"session": session, "replayed": replayed}

    @application.get("/api/v1/config-snapshots", response_model=list[ConfigurationSnapshot])
    def list_snapshots(request: Request) -> list[dict]:
        return request.app.state.preparation.store.list_snapshots()

    @application.get("/api/v1/config-snapshots/{snapshot_id}", response_model=ConfigurationSnapshot)
    def get_snapshot(snapshot_id: str, request: Request) -> dict:
        return request.app.state.preparation.store.get_snapshot(snapshot_id)

    @application.get("/api/v1/mobilecar/execution-recipe")
    def execution_recipe(request: Request) -> dict:
        return request.app.state.recipe.document()

    @application.get("/api/v1/mobilecar/kinematics")
    def mobilecar_kinematics(request: Request) -> dict:
        preparation: PreparationService = request.app.state.preparation
        observation = preparation.validator.observe()
        evidence, _ = preparation.validator.kinematics(observation)
        return {
            "schema_version": "unirobot-mobilecar-kinematics-1",
            "profile_id": preparation.recipe.kinematics["profile_id"],
            "digest": preparation.recipe.kinematics_digest,
            "authority": preparation.recipe.kinematics["authority"],
            "profile": preparation.recipe.kinematics,
            "sources": preparation.recipe.kinematics["sources"],
            "runtime_identity": observation.runtime_identity.model_dump(),
            "consistency": evidence.model_dump(exclude={"profile_id", "digest", "authority", "limitations"}),
            "limitations": preparation.recipe.kinematics["limitations"],
        }

    @application.get("/api/v1/maps", response_model=MapList)
    def list_maps(request: Request):
        return request.app.state.maps.list_maps()

    @application.get("/api/v1/maps/{map_id}/versions/{version}", response_model=MapVersionView)
    def get_map_version(map_id: str, version: str, request: Request, frame: str | None = None):
        return request.app.state.maps.get_version(map_id, version, frame)

    @application.get("/api/v1/maps/{map_id}/versions/{version}/image")
    def get_map_image(map_id: str, version: str, request: Request,
                      sha256: str = Query(pattern=r"^[0-9a-f]{64}$")):
        body, digest = request.app.state.maps.read_image(map_id, version, sha256)
        return Response(body, media_type="image/x-portable-graymap",
                        headers={"ETag": f'"{digest}"', "Cache-Control": "no-store"})

    @application.post("/api/v1/route-drafts", response_model=RouteDraft, status_code=201)
    def create_route_draft(spec: CreateRouteDraft, request: Request):
        return request.app.state.routes.create(spec)

    @application.get("/api/v1/route-drafts/{route_id}", response_model=RouteDraft)
    def get_route_draft(route_id: str, request: Request):
        return request.app.state.routes.get(route_id)

    @application.put("/api/v1/route-drafts/{route_id}", response_model=RouteDraft)
    def save_route_draft(route_id: str, spec: SaveRouteDraft, request: Request):
        return request.app.state.routes.save(route_id, spec)

    @application.post("/api/v1/route-drafts/{route_id}/publish", response_model=PublishResult)
    def publish_route_draft(route_id: str, spec: PublishRouteDraft, request: Request):
        return request.app.state.routes.publish(route_id, spec)

    @application.get("/api/v1/routes/{route_id}/versions", response_model=RouteVersionList)
    def list_route_versions(route_id: str, request: Request):
        return request.app.state.routes.list_versions(route_id)

    @application.get("/api/v1/routes/{route_id}/versions/{version}", response_model=RouteVersion)
    def get_route_version(route_id: str, version: str, request: Request):
        return request.app.state.routes.get_version(route_id, version)

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
