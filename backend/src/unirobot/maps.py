"""Read-only, versioned occupancy-map packages without ROS or native Runtime."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field

from .contracts import Contract

MAP_CATALOG_SCHEMA = "unirobot-map-catalog-1"
MAP_VIEW_SCHEMA = "unirobot-map-version-1"
IMAGE_MEDIA_TYPE = "image/x-portable-graymap"


class MapError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 404,
                 detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code, self.status_code, self.detail = code, status_code, detail or {}


class MapOrigin(Contract):
    x_m: float
    y_m: float
    yaw_rad: float


class MapInitialPrior(Contract):
    x_m: float
    y_m: float
    yaw_rad: float
    covariance: list[float]


class MapAssetRef(Contract):
    role: str
    relative_path: str
    sha256: str
    bytes: int
    media_type: str | None = None


class MapCoordinateConvention(Contract):
    frame: str = "map"
    x_axis: str = "+X"
    y_axis: str = "+Y"
    yaw_positive: str = "counterclockwise_from_+X_to_+Y"
    yaw_range: str = "[-pi,pi)"
    origin: str = "image_lower_left_corner_in_map_frame"
    image_column: str = "+X"
    image_row: str = "-Y"
    cell_center: str = "col+0.5,row+0.5"


class MapCompatibility(Contract):
    g1_recipe_scene_match: bool | None
    g1_recipe_model_match: bool | None
    g1_recipe_status: Literal["passed", "failed", "not_checked"]
    current_runtime_status: Literal["not_checked"] = "not_checked"
    navigation_eligible: bool = False
    reasons: list[str]
    unverified: list[str]


class MapVersionView(Contract):
    schema_version: Literal["unirobot-map-version-1"] = MAP_VIEW_SCHEMA
    map_id: str
    version: str
    frame: str
    status: Literal["available", "unsupported", "failed"]
    reason: str | None = None
    source: str
    live: bool
    test_only: bool
    interface_profile: str | None
    map_frame: str | None
    odom_frame: str | None
    base_frame: str | None
    resolution_m: float | None
    width_px: int | None
    height_px: int | None
    origin: MapOrigin | None
    occupied_thresh: float | None
    free_thresh: float | None
    negate: bool | None
    image: MapAssetRef | None
    assets: list[MapAssetRef]
    manifest_sha256: str | None
    assets_verified: bool
    scene_id: str | None
    model_sha256: str | None
    navigation_profile_sha256: str | None
    sensor_profile_sha256: str | None
    scan_config_sha256: str | None
    initial_prior: MapInitialPrior | None
    coordinate_convention: MapCoordinateConvention = Field(default_factory=MapCoordinateConvention)
    compatibility: MapCompatibility


class MapCatalogEntry(Contract):
    map_id: str
    version: str
    frame: str
    package: str
    manifest_sha256: str
    source: str = "g3b_historical_offline"
    interface_profile: str | None = None
    test_only: bool = False


class MapCatalog(Contract):
    schema_version: Literal["unirobot-map-catalog-1"] = MAP_CATALOG_SCHEMA
    maps: list[MapCatalogEntry]


class MapList(Contract):
    schema_version: Literal["unirobot-map-catalog-1"] = MAP_CATALOG_SCHEMA
    source: Literal["local_map_packages"] = "local_map_packages"
    live: Literal[False] = False
    supported: bool
    reason: str | None
    maps: list[MapVersionView]


def _sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_pgm(body: bytes) -> dict[str, Any]:
    """Parse binary P5 PGM; reject truncation, comments and malformed headers."""
    index = 0
    tokens: list[bytes] = []
    length = len(body)
    while len(tokens) < 4:
        while index < length and body[index:index + 1].isspace():
            index += 1
        if index < length and body[index:index + 1] == b"#":
            while index < length and body[index:index + 1] != b"\n":
                index += 1
            continue
        start = index
        while index < length and not body[index:index + 1].isspace() and body[index:index + 1] != b"#":
            index += 1
        if start == index:
            raise ValueError("truncated PGM header")
        tokens.append(body[start:index])
    if tokens[0] != b"P5":
        raise ValueError("only binary P5 PGM is supported")
    width, height, maximum = (int(token) for token in tokens[1:])
    if width <= 0 or height <= 0 or not 0 < maximum <= 255:
        raise ValueError("invalid PGM dimensions or maximum")
    if index >= length or not body[index:index + 1].isspace():
        raise ValueError("PGM header is not terminated")
    index += 1
    pixels = body[index:index + width * height]
    if len(pixels) != width * height:
        raise ValueError("truncated PGM pixels")
    return {"width": width, "height": height, "maximum": maximum, "pixels": pixels}


def normalize_yaw(yaw_rad: float) -> float:
    value = float(yaw_rad)
    if not math.isfinite(value):
        raise ValueError("yaw must be finite")
    normalized = (value + math.pi) % (2.0 * math.pi) - math.pi
    return normalized


def world_to_pixel(map_view: MapVersionView, x_m: float, y_m: float) -> tuple[float, float]:
    if map_view.resolution_m is None or map_view.origin is None or map_view.height_px is None:
        raise ValueError("map metadata is incomplete")
    x, y = float(x_m), float(y_m)
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("map coordinates must be finite")
    dx = x - map_view.origin.x_m
    dy = y - map_view.origin.y_m
    cosine, sine = math.cos(map_view.origin.yaw_rad), math.sin(map_view.origin.yaw_rad)
    local_x = cosine * dx + sine * dy
    local_y = -sine * dx + cosine * dy
    return local_x / map_view.resolution_m, map_view.height_px - local_y / map_view.resolution_m


def pixel_to_world(map_view: MapVersionView, pixel_x: float, pixel_y: float) -> tuple[float, float]:
    if map_view.resolution_m is None or map_view.origin is None or map_view.height_px is None:
        raise ValueError("map metadata is incomplete")
    px, py = float(pixel_x), float(pixel_y)
    if not math.isfinite(px) or not math.isfinite(py):
        raise ValueError("pixel coordinates must be finite")
    local_x = px * map_view.resolution_m
    local_y = (map_view.height_px - py) * map_view.resolution_m
    cosine, sine = math.cos(map_view.origin.yaw_rad), math.sin(map_view.origin.yaw_rad)
    return (
        local_x * cosine - local_y * sine + map_view.origin.x_m,
        local_x * sine + local_y * cosine + map_view.origin.y_m,
    )


def world_to_cell(map_view: MapVersionView, x_m: float, y_m: float) -> tuple[int, int]:
    pixel_x, pixel_y = world_to_pixel(map_view, x_m, y_m)
    if map_view.height_px is None:
        raise ValueError("map metadata is incomplete")
    # Match the G3B/native cell rule: bottom-left origin, image row 0 at top.
    row_from_bottom = math.floor(map_view.height_px - pixel_y)
    return map_view.height_px - 1 - row_from_bottom, math.floor(pixel_x)


def cell_center_to_world(map_view: MapVersionView, row: int, col: int) -> tuple[float, float]:
    if map_view.origin is None or map_view.resolution_m is None or map_view.height_px is None:
        raise ValueError("map metadata is incomplete")
    local_x = (col + 0.5) * map_view.resolution_m
    local_y = (map_view.height_px - (row + 0.5)) * map_view.resolution_m
    cosine, sine = math.cos(map_view.origin.yaw_rad), math.sin(map_view.origin.yaw_rad)
    return (
        local_x * cosine - local_y * sine + map_view.origin.x_m,
        local_x * sine + local_y * cosine + map_view.origin.y_m,
    )


class MapStore:
    """Load declared packages once and expose immutable map/version metadata."""

    def __init__(
        self,
        catalog_path: Path,
        maps_root: Path,
        *,
        reference_scene_id: str | None = None,
        reference_model_sha256: str | None = None,
    ) -> None:
        self.catalog_path = Path(catalog_path)
        self.maps_root = Path(maps_root)
        self.reference_scene_id = reference_scene_id
        self.reference_model_sha256 = reference_model_sha256
        self._cache: dict[tuple[str, str], MapVersionView] = {}
        self._image_cache: dict[tuple[str, str], bytes] = {}

    def _catalog(self) -> MapCatalog | None:
        if not self.catalog_path.is_file():
            return None
        try:
            return MapCatalog.model_validate_json(self.catalog_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise MapError("map_catalog_invalid", f"map catalog is invalid: {exc}", 503) from exc

    def _summary_error(self, entry: MapCatalogEntry, code: str, message: str) -> MapVersionView:
        return MapVersionView(
            map_id=entry.map_id, version=entry.version, frame=entry.frame,
            status="unsupported" if code in {"map_root_missing", "map_package_missing"} else "failed",
            reason=f"{code}: {message}", source=entry.source, live=False,
            test_only=entry.test_only, interface_profile=entry.interface_profile,
            map_frame=None, odom_frame=None, base_frame=None, resolution_m=None,
            width_px=None, height_px=None, origin=None, occupied_thresh=None,
            free_thresh=None, negate=None, image=None, assets=[], manifest_sha256=None,
            assets_verified=False, scene_id=None, model_sha256=None,
            navigation_profile_sha256=None, sensor_profile_sha256=None,
            scan_config_sha256=None, initial_prior=None,
            coordinate_convention=MapCoordinateConvention(),
            compatibility=MapCompatibility(
                g1_recipe_scene_match=None, g1_recipe_model_match=None,
                g1_recipe_status="not_checked",
                reasons=[code], unverified=["map package not loaded"],
            ),
        )

    def _load(self, entry: MapCatalogEntry) -> MapVersionView:
        cached = self._cache.get((entry.map_id, entry.version))
        if cached is not None:
            return cached
        if not self.maps_root.is_dir():
            raise MapError("map_root_missing", f"map root is missing: {self.maps_root}", 404)
        package = (self.maps_root / entry.package).resolve()
        try:
            package.relative_to(self.maps_root.resolve())
        except ValueError as exc:
            raise MapError("map_package_escape", "map package escapes the configured root", 409) from exc
        manifest_path = package / "manifest.json"
        if not manifest_path.is_file():
            raise MapError("map_package_missing", f"map package or manifest is missing: {entry.package}", 404)
        manifest_body = manifest_path.read_bytes()
        manifest_sha = _sha256_bytes(manifest_body)
        if manifest_sha != entry.manifest_sha256:
            raise MapError("map_manifest_digest_mismatch",
                           f"manifest digest {manifest_sha} does not match catalog {entry.manifest_sha256}", 409)
        try:
            manifest = json.loads(manifest_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MapError("map_manifest_invalid", "map manifest is not valid JSON", 503) from exc
        if manifest.get("schema_version") != 1:
            raise MapError("map_manifest_unsupported", "unsupported map manifest schema", 409)
        if manifest.get("map_id") != entry.map_id:
            raise MapError("map_identity_mismatch",
                           f"manifest map_id {manifest.get('map_id')} != catalog {entry.map_id}", 409)
        if manifest.get("map_frame") != entry.frame:
            raise MapError("map_frame_mismatch",
                           f"manifest frame {manifest.get('map_frame')} != catalog {entry.frame}", 409)
        assets: list[MapAssetRef] = []
        asset_bodies: dict[str, bytes] = {}
        for asset in manifest.get("assets", []):
            relative = str(asset.get("relative_path", ""))
            if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
                raise MapError("map_asset_path_invalid", "map asset path is invalid", 409)
            path = (package / relative).resolve()
            try:
                path.relative_to(package)
            except ValueError as exc:
                raise MapError("map_asset_path_invalid", "map asset escapes package", 409) from exc
            if not path.is_file():
                raise MapError("map_asset_missing", f"map asset is missing: {relative}", 404)
            body = path.read_bytes()
            if len(body) != int(asset.get("bytes", -1)) or _sha256_bytes(body) != asset.get("sha256"):
                raise MapError("map_asset_digest_mismatch", f"map asset differs from manifest: {relative}", 409)
            assets.append(MapAssetRef(
                role=str(asset.get("role", "")), relative_path=relative,
                sha256=str(asset.get("sha256")), bytes=len(body),
                media_type=IMAGE_MEDIA_TYPE if asset.get("role") == "occupancy_image" else None,
            ))
            asset_bodies[str(asset.get("role"))] = body
        roles = {asset.role for asset in assets}
        if not {"occupancy_yaml", "occupancy_image"}.issubset(roles):
            raise MapError("map_assets_incomplete", "map package lacks YAML or image", 409)
        try:
            metadata = yaml.safe_load(asset_bodies["occupancy_yaml"].decode("utf-8"))
        except Exception as exc:
            raise MapError("map_yaml_invalid", "map YAML is invalid", 503) from exc
        if not isinstance(metadata, dict):
            raise MapError("map_yaml_invalid", "map YAML must be a mapping", 503)
        image_ref = next(asset for asset in assets if asset.role == "occupancy_image")
        if str(metadata.get("image")) != image_ref.relative_path:
            raise MapError("map_image_reference_mismatch", "YAML image does not name the declared image asset", 409)
        if str(metadata.get("mode", "trinary")) != "trinary":
            raise MapError("map_mode_unsupported", "only trinary occupancy maps are accepted", 409)
        try:
            origin = [float(v) for v in metadata["origin"]]
            resolution = float(metadata["resolution"])
            occupied = float(metadata["occupied_thresh"])
            free = float(metadata["free_thresh"])
            configured_origin = [float(v) for v in manifest["origin_xy_yaw"]]
            configured_resolution = float(manifest["resolution_m"])
            configured_occupied = float(manifest["occupied_thresh"])
            configured_free = float(manifest["free_thresh"])
        except (KeyError, TypeError, ValueError) as exc:
            raise MapError("map_metadata_invalid", "map metadata has missing or invalid numeric fields", 503) from exc
        if len(origin) != 3 or not all(math.isfinite(v) for v in origin) or not all(math.isfinite(v) for v in configured_origin):
            raise MapError("map_origin_invalid", "map origin must contain three finite values", 503)
        if not math.isfinite(resolution) or resolution <= 0 or not math.isclose(resolution, configured_resolution):
            raise MapError("map_resolution_mismatch", "YAML and manifest resolution differ", 409)
        if not math.isclose(occupied, configured_occupied) or not math.isclose(free, configured_free):
            raise MapError("map_threshold_mismatch", "YAML and manifest thresholds differ", 409)
        if any(not math.isclose(a, b) for a, b in zip(origin, configured_origin)):
            raise MapError("map_origin_mismatch", "YAML and manifest origin differ", 409)
        try:
            image = read_pgm(asset_bodies["occupancy_image"])
        except ValueError as exc:
            raise MapError("map_image_invalid", str(exc), 503) from exc
        scene_id = manifest.get("scene_id")
        model_sha = manifest.get("model_sha256")
        g1_scene = (scene_id == self.reference_scene_id) if self.reference_scene_id else None
        g1_model = (model_sha == self.reference_model_sha256) if self.reference_model_sha256 else None
        g1_status = "not_checked" if g1_scene is None or g1_model is None else (
            "passed" if g1_scene and g1_model else "failed"
        )
        reasons: list[str] = []
        if g1_status == "failed":
            reasons.append("map scene/model does not match the current G1 recipe")
        reasons.extend(["navigation runtime is not available", "footprint/path/dynamic checks are unsupported"])
        view = MapVersionView(
            map_id=entry.map_id, version=entry.version, frame=entry.frame,
            status="available", reason=None, source=entry.source, live=False,
            test_only=entry.test_only, interface_profile=manifest.get("interface_profile"),
            map_frame=manifest.get("map_frame"), odom_frame=manifest.get("odom_frame"),
            base_frame=manifest.get("base_frame"), resolution_m=resolution,
            width_px=int(image["width"]), height_px=int(image["height"]),
            origin=MapOrigin(x_m=origin[0], y_m=origin[1], yaw_rad=origin[2]),
            occupied_thresh=occupied, free_thresh=free,
            negate=bool(metadata.get("negate", 0)), image=image_ref, assets=assets,
            manifest_sha256=manifest_sha, assets_verified=True,
            scene_id=scene_id, model_sha256=model_sha,
            navigation_profile_sha256=manifest.get("navigation_profile_sha256"),
            sensor_profile_sha256=manifest.get("sensor_profile_sha256"),
            scan_config_sha256=manifest.get("scan_config_sha256"),
            initial_prior=MapInitialPrior.model_validate(manifest["initial_prior"]) if manifest.get("initial_prior") else None,
            coordinate_convention=MapCoordinateConvention(frame=str(manifest.get("map_frame", "map"))),
            compatibility=MapCompatibility(
                g1_recipe_scene_match=g1_scene, g1_recipe_model_match=g1_model,
                g1_recipe_status=g1_status, reasons=reasons,
                unverified=["posegraph is hash-verified but not parsed", "current runtime compatibility was not read"],
            ),
        )
        self._cache[(entry.map_id, entry.version)] = view
        self._image_cache[(entry.map_id, entry.version)] = asset_bodies["occupancy_image"]
        return view

    def list_maps(self) -> MapList:
        try:
            catalog = self._catalog()
        except MapError as exc:
            return MapList(supported=False, reason=f"{exc.code}: {exc}", maps=[])
        if catalog is None:
            return MapList(supported=False, reason="map catalog is not configured", maps=[])
        values: list[MapVersionView] = []
        for entry in catalog.maps:
            try:
                values.append(self._load(entry))
            except MapError as exc:
                values.append(self._summary_error(entry, exc.code, str(exc)))
        return MapList(supported=True, reason=None, maps=values)

    def get_version(self, map_id: str, version: str, frame: str | None = None) -> MapVersionView:
        catalog = self._catalog()
        if catalog is None:
            raise MapError("map_catalog_missing", "map catalog is not configured", 404)
        entry = next((item for item in catalog.maps if item.map_id == map_id and item.version == version), None)
        if entry is None:
            raise MapError("map_version_not_found", f"map {map_id} version {version} is not declared", 404)
        if frame is not None and frame != entry.frame:
            raise MapError("map_frame_mismatch", f"requested frame {frame} != map frame {entry.frame}", 409)
        return self._load(entry)

    def read_image(self, map_id: str, version: str, expected_sha256: str) -> tuple[bytes, str]:
        view = self.get_version(map_id, version)
        if view.image is None:
            raise MapError("map_image_missing", "map has no image asset", 404)
        if view.image.sha256 != expected_sha256:
            raise MapError("map_asset_revision_changed", "map image digest changed; reload map list", 409)
        body = self._image_cache.get((map_id, version))
        if body is None:
            raise MapError("map_image_missing", "map image is not loaded", 404)
        return body, view.image.sha256

    def classify(self, map_id: str, version: str, x_m: float, y_m: float) -> dict[str, Any]:
        view = self.get_version(map_id, version)
        row, column = world_to_cell(view, x_m, y_m)
        if view.width_px is None or view.height_px is None:
            return {"accepted": False, "classification": "unsupported", "row": row, "column": column}
        if not (0 <= row < view.height_px and 0 <= column < view.width_px):
            return {"accepted": False, "classification": "outside_map", "row": row, "column": column}
        body = self._image_cache.get((map_id, version))
        if body is None:
            raise MapError("map_image_missing", "map image is not loaded", 404)
        image = read_pgm(body)
        gray = int(image["pixels"][row * view.width_px + column])
        probability = gray / float(image["maximum"])
        if view.negate:
            probability = 1.0 - probability
        occupied_probability = 1.0 - probability
        if occupied_probability > float(view.occupied_thresh):
            classification = "occupied"
        elif occupied_probability < float(view.free_thresh):
            classification = "free"
        else:
            classification = "unknown"
        return {
            "accepted": classification == "free", "classification": classification,
            "row": row, "column": column, "gray_value": gray,
            "occupied_probability": occupied_probability, "x_m": float(x_m), "y_m": float(y_m),
        }
