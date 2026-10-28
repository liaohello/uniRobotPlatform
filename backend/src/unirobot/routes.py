"""Route Draft/Version resources with no navigation or robot side effects."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, model_validator, StrictStr

from .contracts import Contract, utc_now
from .maps import MapError, MapStore, normalize_yaw

ROUTE_CONTENT_SCHEMA = "unirobot-route-content-1"
ROUTE_VERSION_SCHEMA = "unirobot-route-version-1"
DRAFT_SCHEMA = "unirobot-route-draft-1"


class RouteError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 409,
                 detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code, self.status_code, self.detail = code, status_code, detail or {}


class MapRef(Contract):
    map_id: StrictStr = Field(min_length=1)
    version: StrictStr = Field(min_length=1)
    frame: StrictStr = Field(default="map", min_length=1)


class WaypointInput(Contract):
    id: StrictStr = Field(min_length=1)
    order: int = Field(ge=1)
    x_m: float
    y_m: float
    yaw_rad: float = Field(description="Explicit yaw in radians; missing or null is rejected")

    @model_validator(mode="before")
    @classmethod
    def require_explicit_yaw(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("yaw_rad") is None:
            raise ValueError("yaw_rad is required and must be an explicit finite number")
        return data


class RouteDraftSpec(Contract):
    name: StrictStr = Field(default="", max_length=200)
    map_ref: MapRef
    waypoints: list[WaypointInput]


class CreateRouteDraft(RouteDraftSpec):
    pass


class SaveRouteDraft(RouteDraftSpec):
    base_revision: int = Field(ge=1)


class PublishRouteDraft(Contract):
    base_revision: int = Field(ge=1)


class Waypoint(Contract):
    id: str
    order: int
    x_m: float
    y_m: float
    yaw_rad: float


class RouteCheck(Contract):
    key: str
    status: Literal["passed", "failed", "unsupported", "not_checked"]
    detail: str
    waypoint_id: str | None = None


class RouteValidation(Contract):
    checks: list[RouteCheck]
    pose_checks_passed: bool
    navigation_eligible: Literal[False] = False
    adoption_supported: Literal[False] = False
    execution_supported: Literal[False] = False
    display_supported: Literal[True] = True
    g1_navigation_supported: Literal[False] = False
    arrival_acceptance: Literal["not_checked"] = "not_checked"
    tolerance_source: str = "Task Template goal.position_tolerance / goal.yaw_tolerance_rad; not evaluated by route save"
    unsupported_checks: list[str]
    reasons: list[str]


class RouteDraft(Contract):
    schema_version: Literal["unirobot-route-draft-1"] = DRAFT_SCHEMA
    route_id: str
    draft_revision: int
    name: str
    map_ref: MapRef
    waypoints: list[Waypoint]
    content_digest: str
    validation: RouteValidation
    created_at: str
    updated_at: str


class RouteVersion(Contract):
    schema_version: Literal["unirobot-route-version-1"] = ROUTE_VERSION_SCHEMA
    route_id: str
    version: str
    content_digest: str
    created_at: str
    map_ref: MapRef
    waypoints: list[Waypoint]
    validation: RouteValidation
    navigation_eligible: Literal[False] = False
    adoption_supported: Literal[False] = False
    execution_supported: Literal[False] = False
    display_supported: Literal[True] = True


class RouteVersionSummary(Contract):
    route_id: str
    version: str
    content_digest: str
    created_at: str
    waypoint_count: int
    map_ref: MapRef


class RouteVersionList(Contract):
    route_id: str
    versions: list[RouteVersionSummary]


class PublishResult(Contract):
    route_version: RouteVersion
    reused: bool


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def content_digest(map_ref: MapRef, waypoints: list[Waypoint]) -> str:
    body = {
        "schema_version": ROUTE_CONTENT_SCHEMA,
        "map_ref": map_ref.model_dump(),
        "waypoints": [waypoint.model_dump() for waypoint in waypoints],
    }
    return hashlib.sha256(_canonical(body)).hexdigest()


class RouteService:
    def __init__(self, path: Path, maps: MapStore) -> None:
        self.path = path
        self.maps = maps
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS route_drafts (route_id TEXT PRIMARY KEY, "
                       "revision INTEGER NOT NULL, document TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS route_versions (route_id TEXT NOT NULL, "
                       "version TEXT NOT NULL, content_sha256 TEXT NOT NULL, document TEXT NOT NULL, "
                       "created_at TEXT NOT NULL, PRIMARY KEY(route_id, version))")

    def _validate(self, spec: RouteDraftSpec) -> tuple[list[Waypoint], RouteValidation, MapRef]:
        if not spec.waypoints:
            raise RouteError("route_empty", "a route must contain at least one waypoint", 422)
        ids: set[str] = set()
        orders: list[int] = []
        values: list[Waypoint] = []
        for item in spec.waypoints:
            if item.id in ids:
                raise RouteError("waypoint_id_duplicate", f"duplicate waypoint id: {item.id}", 422)
            ids.add(item.id)
            orders.append(item.order)
            for key, value in (("x_m", item.x_m), ("y_m", item.y_m), ("yaw_rad", item.yaw_rad)):
                if not math.isfinite(float(value)):
                    raise RouteError("waypoint_value_not_finite",
                                     f"waypoint {item.id} {key} must be finite", 422,
                                     {"waypoint_id": item.id, "field": key})
            values.append(Waypoint(
                id=item.id, order=item.order, x_m=float(item.x_m), y_m=float(item.y_m),
                yaw_rad=normalize_yaw(float(item.yaw_rad)),
            ))
        if len(set(orders)) != len(orders) or sorted(orders) != list(range(1, len(orders) + 1)):
            raise RouteError("waypoint_order_invalid", "waypoint order must be unique and contiguous from 1", 422)
        values.sort(key=lambda waypoint: waypoint.order)
        map_ref = spec.map_ref
        view = self.maps.get_version(map_ref.map_id, map_ref.version, map_ref.frame)
        checks: list[RouteCheck] = [
            RouteCheck(key="map_binding", status="passed",
                       detail=f"{map_ref.map_id} {map_ref.version} {map_ref.frame}"),
            RouteCheck(key="map_frame", status="passed", detail=f"frame {map_ref.frame}"),
            RouteCheck(key="waypoint_sequence", status="passed", detail=f"{len(values)} ordered waypoints"),
        ]
        for waypoint in values:
            result = self.maps.classify(map_ref.map_id, map_ref.version, waypoint.x_m, waypoint.y_m)
            if result["classification"] == "outside_map":
                raise RouteError("waypoint_out_of_bounds",
                                 f"waypoint {waypoint.id} is outside the map", 422,
                                 {"waypoint_id": waypoint.id, "classification": result["classification"],
                                  "row": result["row"], "column": result["column"]})
            if result["classification"] == "occupied":
                raise RouteError("waypoint_occupied",
                                 f"waypoint {waypoint.id} is in an occupied cell", 422,
                                 {"waypoint_id": waypoint.id, "classification": result["classification"],
                                  "row": result["row"], "column": result["column"]})
            if result["classification"] == "unknown":
                raise RouteError("waypoint_unknown",
                                 f"waypoint {waypoint.id} is in an unknown cell", 422,
                                 {"waypoint_id": waypoint.id, "classification": result["classification"],
                                  "row": result["row"], "column": result["column"]})
            checks.append(RouteCheck(
                key=f"waypoint_pose:{waypoint.id}", status="passed",
                detail=f"free cell row={result['row']} column={result['column']}",
                waypoint_id=waypoint.id,
            ))
        checks.extend([
            RouteCheck(key="footprint", status="unsupported",
                       detail="no robot footprint binding in this resource slice"),
            RouteCheck(key="path_reachability", status="unsupported",
                       detail="no planner or path validation in this resource slice"),
            RouteCheck(key="dynamic_execution", status="unsupported",
                       detail="no navigation runtime or Session execution in this resource slice"),
            RouteCheck(key="g1_route_adoption", status="unsupported",
                       detail="current G1 has no navigation execution capability; no route adoption"),
            RouteCheck(key="arrival_acceptance", status="not_checked",
                       detail="route save does not evaluate arrival; tolerances come from Task Template"),
        ])
        validation = RouteValidation(
            checks=checks, pose_checks_passed=True,
            unsupported_checks=[check.key for check in checks if check.status == "unsupported"],
            reasons=["route is a resource and display artifact only; it is not navigation-eligible"],
        )
        return values, validation, map_ref

    def _document(self, route_id: str, revision: int, spec: RouteDraftSpec,
                  waypoints: list[Waypoint], validation: RouteValidation, map_ref: MapRef,
                  created_at: str) -> dict:
        now = utc_now()
        return RouteDraft(
            route_id=route_id, draft_revision=revision, name=spec.name, map_ref=map_ref,
            waypoints=waypoints, content_digest=content_digest(map_ref, waypoints),
            validation=validation, created_at=created_at, updated_at=now,
        ).model_dump()

    def create(self, spec: CreateRouteDraft) -> dict:
        waypoints, validation, map_ref = self._validate(spec)
        route_id = "route-" + uuid4().hex
        now = utc_now()
        document = self._document(route_id, 1, spec, waypoints, validation, map_ref, now)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO route_drafts VALUES (?, ?, ?)", (route_id, 1, json.dumps(document)))
        return document

    def get(self, route_id: str) -> dict:
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute("SELECT document FROM route_drafts WHERE route_id=?", (route_id,)).fetchone()
        if row is None:
            raise RouteError("route_draft_not_found", "route draft not found", 404)
        return json.loads(row[0])

    def save(self, route_id: str, spec: SaveRouteDraft) -> dict:
        waypoints, validation, map_ref = self._validate(spec)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT revision, document FROM route_drafts WHERE route_id=?", (route_id,)).fetchone()
            if row is None:
                raise RouteError("route_draft_not_found", "route draft not found", 404)
            revision, existing = row
            if revision != spec.base_revision:
                raise RouteError("route_draft_revision_conflict",
                                 "route draft changed in another host; reload before saving", 409,
                                 {"current_revision": revision})
            existing = json.loads(existing)
            digest = content_digest(map_ref, waypoints)
            if (existing["name"] == spec.name and existing["map_ref"] == map_ref.model_dump()
                    and existing["waypoints"] == [w.model_dump() for w in waypoints]):
                return existing
            document = self._document(route_id, revision + 1, spec, waypoints, validation, map_ref,
                                      existing["created_at"])
            db.execute("UPDATE route_drafts SET revision=?, document=? WHERE route_id=?",
                       (revision + 1, json.dumps(document), route_id))
        return document

    def _latest(self, route_id: str) -> dict | None:
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute("SELECT document FROM route_versions WHERE route_id=? ORDER BY rowid DESC LIMIT 1",
                             (route_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def publish(self, route_id: str, request: PublishRouteDraft) -> PublishResult:
        draft = self.get(route_id)
        if draft["draft_revision"] != request.base_revision:
            raise RouteError("route_draft_revision_conflict",
                             "route draft changed in another host; reload before publishing", 409,
                             {"current_revision": draft["draft_revision"]})
        # Revalidate the accepted draft content, not a client-supplied copy.
        spec = RouteDraftSpec(
            name=draft["name"], map_ref=MapRef.model_validate(draft["map_ref"]),
            waypoints=[WaypointInput.model_validate(item) for item in draft["waypoints"]],
        )
        waypoints, validation, map_ref = self._validate(spec)
        digest = content_digest(map_ref, waypoints)
        latest = self._latest(route_id)
        if latest is not None and latest["content_digest"] == digest:
            return PublishResult(route_version=RouteVersion.model_validate(latest), reused=True)
        now = utc_now()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT version FROM route_versions WHERE route_id=?", (route_id,)).fetchall()
            version = f"v{len(rows) + 1}"
            document = RouteVersion(
                route_id=route_id, version=version, content_digest=digest,
                created_at=now, map_ref=map_ref, waypoints=waypoints, validation=validation,
            ).model_dump()
            db.execute("INSERT INTO route_versions VALUES (?, ?, ?, ?, ?)",
                       (route_id, version, digest, json.dumps(document), now))
        return PublishResult(route_version=RouteVersion.model_validate(document), reused=False)

    def list_versions(self, route_id: str) -> RouteVersionList:
        with closing(sqlite3.connect(self.path)) as db, db:
            rows = db.execute("SELECT document FROM route_versions WHERE route_id=? ORDER BY rowid DESC",
                              (route_id,)).fetchall()
        if not rows:
            raise RouteError("route_version_not_found", "route has no published versions", 404)
        values = [RouteVersion.model_validate(json.loads(row[0])) for row in rows]
        return RouteVersionList(route_id=route_id, versions=[
            RouteVersionSummary(
                route_id=version.route_id, version=version.version,
                content_digest=version.content_digest, created_at=version.created_at,
                waypoint_count=len(version.waypoints), map_ref=version.map_ref,
            ) for version in values
        ])

    def get_version(self, route_id: str, version: str) -> RouteVersion:
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute("SELECT document FROM route_versions WHERE route_id=? AND version=?",
                             (route_id, version)).fetchone()
        if row is None:
            raise RouteError("route_version_not_found", f"route {route_id} version {version} not found", 404)
        return RouteVersion.model_validate(json.loads(row[0]))
