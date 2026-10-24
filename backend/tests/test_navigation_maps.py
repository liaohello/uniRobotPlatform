"""Versioned map read and orientated Route Draft/Version persistence."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from native_fixtures import FakeNative
from unirobot.api import create_app
from unirobot.contracts import AdapterConfig
from unirobot.maps import MapStore, MapVersionView, pixel_to_world, world_to_pixel, world_to_cell
from unirobot.mobilecar import MobileCarIntegration
from unirobot.routes import RouteError, RouteService, WaypointInput


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _pgm(pixels: list[int], width: int = 4, height: int = 4) -> bytes:
    return f"P5\n{width} {height}\n255\n".encode() + bytes(pixels)


def _map_fixture(tmp_path: Path, *, yaw: float = 0.0) -> tuple[Path, Path, bytes, dict]:
    root = tmp_path / "maps"
    package = root / "map_test"
    package.mkdir(parents=True)
    pixels = [
        0, 0, 0, 0,
        0, 254, 254, 0,
        0, 254, 128, 0,
        0, 0, 0, 0,
    ]
    image = _pgm(pixels)
    (package / "map.pgm").write_bytes(image)
    metadata = {
        "image": "map.pgm", "mode": "trinary", "resolution": 1.0,
        "origin": [0.0, 0.0, yaw], "negate": 0,
        "occupied_thresh": 0.65, "free_thresh": 0.196,
    }
    yaml_body = yaml.safe_dump(metadata, sort_keys=False).encode()
    (package / "map.yaml").write_bytes(yaml_body)
    manifest = {
        "schema_version": 1,
        "interface_profile": "platform-test-map-1",
        "map_id": "map_test",
        "map_frame": "map",
        "odom_frame": "odom",
        "base_frame": "base_link",
        "resolution_m": 1.0,
        "origin_xy_yaw": [0.0, 0.0, yaw],
        "occupied_thresh": 0.65,
        "free_thresh": 0.196,
        "scene_id": "scene_test",
        "model_sha256": "0" * 64,
        "assets": [
            {"role": "occupancy_yaml", "relative_path": "map.yaml", "sha256": _sha(yaml_body), "bytes": len(yaml_body)},
            {"role": "occupancy_image", "relative_path": "map.pgm", "sha256": _sha(image), "bytes": len(image)},
        ],
        "test_map": True,
    }
    manifest_body = json.dumps(manifest, sort_keys=True).encode()
    (package / "manifest.json").write_bytes(manifest_body)
    catalog = {
        "schema_version": "unirobot-map-catalog-1",
        "maps": [{
            "map_id": "map_test", "version": "v1", "frame": "map", "package": "map_test",
            "manifest_sha256": _sha(manifest_body), "source": "synthetic_contract_only",
            "interface_profile": "platform-test-map-1", "test_only": True,
        }],
    }
    catalog_path = tmp_path / "maps.catalog.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    return catalog_path, root, image, metadata


def _app(tmp_path: Path, catalog: Path, root: Path) -> tuple[TestClient, FakeNative]:
    integration = MobileCarIntegration(AdapterConfig(id="mobilecar", title="unused", project_root="unused",
                                                     base_url="http://fixture.invalid"))
    fake = FakeNative({}, binding=False)
    integration._opener = fake
    app = create_app(
        draft_db_path=tmp_path / "route.sqlite3",
        mobilecar_integration=integration,
        map_catalog_path=catalog,
        maps_root=root,
    )
    return TestClient(app), fake


def _route_body(**overrides):
    body = {
        "name": "Test route",
        "map_ref": {"map_id": "map_test", "version": "v1", "frame": "map"},
        "waypoints": [
            {"id": "wp-a", "order": 1, "x_m": 1.5, "y_m": 2.5, "yaw_rad": 0.0},
            {"id": "wp-b", "order": 2, "x_m": 1.5, "y_m": 1.5, "yaw_rad": -1.0},
        ],
    }
    body.update(overrides)
    return body


def test_map_list_and_fixed_map_read_are_real_and_read_only(tmp_path):
    catalog, root, image, metadata = _map_fixture(tmp_path)
    http, fake = _app(tmp_path, catalog, root)
    with http:
        listing = http.get("/api/v1/maps")
        assert listing.status_code == 200
        value = listing.json()
        assert value["supported"] is True and value["live"] is False
        item = value["maps"][0]
        assert item["map_id"] == "map_test" and item["version"] == "v1"
        assert item["status"] == "available"
        assert item["source"] == "synthetic_contract_only" and item["test_only"] is True
        assert item["origin"] == {"x_m": 0.0, "y_m": 0.0, "yaw_rad": 0.0}
        assert item["width_px"] == 4 and item["height_px"] == 4
        assert item["image"]["sha256"] == _sha(image)
        assert item["assets_verified"] is True
        assert item["coordinate_convention"]["origin"] == "image_lower_left_corner_in_map_frame"
        assert item["coordinate_convention"]["image_row"] == "-Y"
        assert item["compatibility"]["navigation_eligible"] is False
        fixed = http.get("/api/v1/maps/map_test/versions/v1?frame=map")
        assert fixed.status_code == 200 and fixed.json()["map_id"] == "map_test"
        assert http.get("/api/v1/maps/map_test/versions/v2").status_code == 404
        assert http.get("/api/v1/maps/map_test/versions/v1?frame=odom").status_code == 409
        image_response = http.get(f"/api/v1/maps/map_test/versions/v1/image?sha256={_sha(image)}")
        assert image_response.status_code == 200 and image_response.content == image
        assert image_response.headers["content-type"].startswith("image/x-portable-graymap")
        assert http.get(f"/api/v1/maps/map_test/versions/v1/image?sha256={'0' * 64}").status_code == 409
        assert fake.calls == []


def test_rotated_origin_pixel_round_trip_and_cell_center():
    view = MapVersionView.model_validate({
        "map_id": "rot", "version": "v1", "frame": "map", "status": "available",
        "source": "test", "live": False, "test_only": True, "interface_profile": "test",
        "map_frame": "map", "odom_frame": "odom", "base_frame": "base_link",
        "resolution_m": 0.05, "width_px": 10, "height_px": 8,
        "origin": {"x_m": -1.0, "y_m": -2.0, "yaw_rad": 0.5},
        "occupied_thresh": 0.65, "free_thresh": 0.196, "negate": False,
        "image": None, "assets": [], "manifest_sha256": None, "assets_verified": False,
        "scene_id": None, "model_sha256": None, "navigation_profile_sha256": None,
        "sensor_profile_sha256": None, "scan_config_sha256": None, "initial_prior": None,
        "compatibility": {"g1_recipe_scene_match": None, "g1_recipe_model_match": None,
                          "g1_recipe_status": "not_checked", "reasons": [], "unverified": []},
    })
    for point in ((0.1, 0.2), (-0.4, 0.7), (0.0, 0.0)):
        px, py = world_to_pixel(view, *point)
        x, y = pixel_to_world(view, px, py)
        assert abs(x - point[0]) < 1e-12 and abs(y - point[1]) < 1e-12
    row, col = world_to_cell(view, *pixel_to_world(view, 3, 4))
    assert (row, col) == (3, 3)


def test_map_missing_catalog_is_unsupported(tmp_path):
    missing_catalog = tmp_path / "missing.json"
    missing_root = tmp_path / "missing-maps"
    app = create_app(
        draft_db_path=tmp_path / "route.sqlite3",
        mobilecar_integration=MobileCarIntegration(AdapterConfig(
            id="mobilecar", title="unused", project_root="unused", base_url="http://fixture.invalid")),
        map_catalog_path=missing_catalog, maps_root=missing_root,
    )
    with TestClient(app) as http:
        value = http.get("/api/v1/maps").json()
        assert value["supported"] is False and value["maps"] == []
        assert "not configured" in value["reason"]
        assert http.get("/api/v1/maps/map_test/versions/v1").status_code == 404


def test_route_draft_requires_yaw_and_normalizes_explicit_zero(tmp_path):
    catalog, root, _, _ = _map_fixture(tmp_path)
    http, fake = _app(tmp_path, catalog, root)
    with http:
        missing = _route_body()
        missing["waypoints"][0].pop("yaw_rad")
        response = http.post("/api/v1/route-drafts", json=missing)
        assert response.status_code == 422
        assert "yaw_rad" in response.text
        null_yaw = _route_body()
        null_yaw["waypoints"][0]["yaw_rad"] = None
        response = http.post("/api/v1/route-drafts", json=null_yaw)
        assert response.status_code == 422
        assert "yaw_rad" in response.text
        schema = http.get("/openapi.json").json()["components"]["schemas"]["WaypointInput"]
        assert "yaw_rad" in schema["required"]
        assert schema["properties"]["yaw_rad"]["type"] == "number"
        explicit_zero = _route_body()
        explicit_zero["waypoints"][0]["yaw_rad"] = 2.0 * math.pi
        created = http.post("/api/v1/route-drafts", json=explicit_zero)
        assert created.status_code == 201, created.text
        value = created.json()
        assert value["waypoints"][0]["yaw_rad"] == 0.0
        assert value["validation"]["pose_checks_passed"] is True
        assert value["validation"]["navigation_eligible"] is False
        assert value["validation"]["adoption_supported"] is False
        assert value["validation"]["execution_supported"] is False
        assert {"footprint", "path_reachability", "dynamic_execution", "g1_route_adoption"} <= set(
            value["validation"]["unsupported_checks"]
        )
        assert fake.calls == []


@pytest.mark.parametrize("field,value,code", [
    ("x_m", 10.0, "waypoint_out_of_bounds"),
    ("y_m", 10.0, "waypoint_out_of_bounds"),
])
def test_route_rejects_out_of_bounds(tmp_path, field, value, code):
    catalog, root, _, _ = _map_fixture(tmp_path)
    http, _ = _app(tmp_path, catalog, root)
    with http:
        body = _route_body()
        body["waypoints"][0][field] = value
        response = http.post("/api/v1/route-drafts", json=body)
        assert response.status_code == 422 and response.json()["detail"]["code"] == code


def test_route_rejects_occupied_and_unknown_cells(tmp_path):
    catalog, root, _, _ = _map_fixture(tmp_path)
    http, _ = _app(tmp_path, catalog, root)
    with http:
        occupied = _route_body()
        occupied["waypoints"][0].update(x_m=0.5, y_m=3.5)
        response = http.post("/api/v1/route-drafts", json=occupied)
        assert response.status_code == 422 and response.json()["detail"]["code"] == "waypoint_occupied"
        unknown = _route_body()
        unknown["waypoints"][0].update(x_m=2.5, y_m=1.5)
        response = http.post("/api/v1/route-drafts", json=unknown)
        assert response.status_code == 422 and response.json()["detail"]["code"] == "waypoint_unknown"


def test_route_save_conflict_reorder_publish_and_immutability(tmp_path):
    catalog, root, _, _ = _map_fixture(tmp_path)
    http, fake = _app(tmp_path, catalog, root)
    with http:
        created = http.post("/api/v1/route-drafts", json=_route_body()).json()
        route_id = created["route_id"]
        assert created["draft_revision"] == 1
        v1 = http.post(f"/api/v1/route-drafts/{route_id}/publish", json={"base_revision": 1}).json()
        assert v1["reused"] is False
        assert v1["route_version"]["version"] == "v1"
        v1_text = http.get(f"/api/v1/routes/{route_id}/versions/v1").text
        assert http.get(f"/api/v1/routes/{route_id}/versions/latest").status_code == 404

        changed = _route_body()
        changed["waypoints"] = [
            {"id": "wp-b", "order": 1, "x_m": 1.5, "y_m": 1.5, "yaw_rad": 0.25},
            {"id": "wp-a", "order": 2, "x_m": 1.5, "y_m": 2.5, "yaw_rad": 0.0},
        ]
        saved = http.put(f"/api/v1/route-drafts/{route_id}", json={**changed, "base_revision": 1})
        assert saved.status_code == 200 and saved.json()["draft_revision"] == 2
        assert [item["id"] for item in saved.json()["waypoints"]] == ["wp-b", "wp-a"]
        conflict = http.put(f"/api/v1/route-drafts/{route_id}", json={**changed, "base_revision": 1})
        assert conflict.status_code == 409 and conflict.json()["detail"]["code"] == "route_draft_revision_conflict"
        v2 = http.post(f"/api/v1/route-drafts/{route_id}/publish", json={"base_revision": 2}).json()
        assert v2["route_version"]["version"] == "v2"
        assert v2["route_version"]["content_digest"] != v1["route_version"]["content_digest"]
        assert http.get(f"/api/v1/routes/{route_id}/versions/v1").text == v1_text
        assert http.get(f"/api/v1/routes/{route_id}/versions").json()["versions"][0]["version"] == "v2"
        replay = http.post(f"/api/v1/route-drafts/{route_id}/publish", json={"base_revision": 2}).json()
        assert replay["reused"] is True and replay["route_version"]["version"] == "v2"
        assert fake.calls == []


def test_route_wrong_map_or_frame_is_rejected(tmp_path):
    catalog, root, _, _ = _map_fixture(tmp_path)
    http, _ = _app(tmp_path, catalog, root)
    with http:
        wrong_map = _route_body(map_ref={"map_id": "missing", "version": "v1", "frame": "map"})
        assert http.post("/api/v1/route-drafts", json=wrong_map).status_code == 404
        wrong_frame = _route_body(map_ref={"map_id": "map_test", "version": "v1", "frame": "odom"})
        assert http.post("/api/v1/route-drafts", json=wrong_frame).status_code == 409


def test_route_service_rejects_nan_values(tmp_path):
    catalog, root, _, _ = _map_fixture(tmp_path)
    integration = MobileCarIntegration(AdapterConfig(id="mobilecar", title="unused", project_root="unused",
                                                     base_url="http://fixture.invalid"))
    maps = MapStore(catalog, root)
    service = RouteService(tmp_path / "route.sqlite3", maps)
    from unirobot.routes import CreateRouteDraft, MapRef, RouteError
    with pytest.raises(RouteError) as exc:
        service.create(CreateRouteDraft(
            map_ref=MapRef(map_id="map_test", version="v1"),
            waypoints=[WaypointInput(id="wp", order=1, x_m=float("nan"), y_m=2.5, yaw_rad=0.0)],
        ))
    assert exc.value.code == "waypoint_value_not_finite"
