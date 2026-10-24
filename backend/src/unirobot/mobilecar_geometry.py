"""Opt-in compiled mesh candidate. No MuJoCo dependency in the gateway."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, StrictInt, StrictStr

from .contracts import utc_now
from .mobilecar import Health, NativeReadError, RuntimeIdentity, SceneIdentity
from .mobilecar_read import (
    Asset, Digest, Geom, Link, MobileCarReadService, ReadEnvelope,
    ReadServiceError, SceneData, ObjectIdentity, scene_objects,
)


def content_digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class CompiledGeom(Geom):
    contype: StrictInt = Field(ge=0)
    conaffinity: StrictInt = Field(ge=0)


class CompiledLink(Link):
    geoms: list[CompiledGeom]


class CompiledAsset(Asset):
    coordinate_space: Literal["mujoco_compiled_mesh"]
    units: Literal["m"]
    mesh_preprocessing_applied: Literal[True]
    source_sha256: Digest
    source_mesh_name: StrictStr


class CompiledSceneData(SceneData):
    links: list[CompiledLink]
    world_links: list[CompiledLink]
    mesh_assets: list[CompiledAsset]


class GeometryProvenance(BaseModel):
    compiler: Literal["MuJoCo"]
    compiler_version: StrictStr
    runtime_identity: RuntimeIdentity
    resource_identity: SceneIdentity
    native_scene_sha256: Digest
    model_inputs_sha256: Digest
    compiled_scene_sha256: Digest
    native_scene_builder_sha256: Digest
    bundle_sha256: Digest
    verification_scope: Literal["static_compilation_matches_live_manifest_not_live_memory_or_contacts"]


class GeometryBinding(BaseModel):
    """Content identity is what the meshes depend on; run/episode identity is an observation."""

    bundle_sha256: Digest
    content_identity_sha256: Digest
    exported_runtime_identity: RuntimeIdentity
    observed_runtime_identity: RuntimeIdentity
    content_matches: Literal[True] = True
    runtime_identity_matches: bool
    association: Literal["content_matches_export_identity", "content_reverified_after_runtime_identity_change"]
    revalidated_at: str


class CompiledSceneRead(ReadEnvelope):
    schema_version: Literal["unirobot-mobilecar-geometry-2"] = "unirobot-mobilecar-geometry-2"
    data_source: Literal["live_native_http_with_verified_compiled_geometry"] = "live_native_http_with_verified_compiled_geometry"
    data: CompiledSceneData
    objects: list[ObjectIdentity]
    geometry_provenance: GeometryProvenance
    geometry_binding: GeometryBinding
    world_pose_semantics: Literal["compiled_initial_layout_not_live_object_state"] = "compiled_initial_layout_not_live_object_state"


def content_identity(provenance: GeometryProvenance) -> str:
    return content_digest({
        "contract_version": provenance.resource_identity.contract_version,
        "model_id": provenance.resource_identity.model_id,
        "model_sha256": provenance.resource_identity.model_sha256,
        "scene_id": provenance.resource_identity.scene_id,
        "native_scene_sha256": provenance.native_scene_sha256,
        "model_inputs_sha256": provenance.model_inputs_sha256,
        "compiled_scene_sha256": provenance.compiled_scene_sha256,
    })


class GeometryBundle:
    """Operator-selected immutable export, integrity checked before use."""
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        bundle = json.loads((self.directory / "bundle.json").read_text())
        claimed = bundle["geometry_provenance"].pop("bundle_sha256")
        if content_digest(bundle) != claimed:
            raise ValueError("Compiled geometry bundle digest mismatch")
        bundle["geometry_provenance"]["bundle_sha256"] = claimed
        self.provenance = GeometryProvenance.model_validate(bundle["geometry_provenance"])
        if content_digest(bundle["scene"]) != self.provenance.compiled_scene_sha256 or content_digest(bundle["model_inputs"]) != self.provenance.model_inputs_sha256:
            raise ValueError("Compiled geometry content digest mismatch")
        self.scene = CompiledSceneData.model_validate(bundle["scene"])
        if SceneIdentity.model_validate(self.scene.model_dump()) != self.provenance.resource_identity:
            raise ValueError("Compiled geometry resource identity mismatch")
        self.assets = {}
        for asset in self.scene.mesh_assets:
            body = (self.directory / "assets" / (asset.asset_id + ".stl")).read_bytes()
            if len(body) > 32 * 1024 * 1024 or hashlib.sha256(body).hexdigest() != asset.sha256:
                raise ValueError("Compiled geometry asset integrity mismatch: " + asset.asset_id)
            self.assets[asset.asset_id] = body
        for link in self.scene.links + self.scene.world_links:
            for geom in link.geoms:
                if geom.geom_type == "mesh" and geom.size_m != [1, 1, 1]:
                    raise ValueError("Compiled mesh must have identity scale")
                if geom.collision != bool(geom.contype or geom.conaffinity):
                    raise ValueError("Collision filter metadata mismatch")
        self.content_identity_sha256 = content_identity(self.provenance)


class CompiledGeometryReadService(MobileCarReadService):
    def __init__(self, integration, bundle: GeometryBundle):
        super().__init__(integration)
        self.bundle = bundle

    def scene(self) -> CompiledSceneRead:
        before = self._read("/api/v1/health", Health)
        try:
            raw = self.integration._read("/api/v1/scene")
        except NativeReadError as exc:
            raise ReadServiceError(f"native_{exc.status}", str(exc), 503 if exc.status in {"offline", "not_configured"} else 502) from exc
        provenance = self.bundle.provenance
        identity_ok = all(raw.get(key) == getattr(provenance.resource_identity, key)
                          for key in ("contract_version", "model_id", "model_sha256", "scene_id"))
        if not identity_ok or content_digest(raw) != provenance.native_scene_sha256:
            raise ReadServiceError("geometry_source_changed",
                                   "Live model or scene content differs from the verified geometry export; rebuild the bundle", 409)
        data = self.bundle.scene.model_copy(deep=True)
        for asset in data.mesh_assets:
            asset.uri = f"/api/v1/mobilecar/scene/assets/{asset.asset_id}?sha256={asset.sha256}"
        finished = self._finish(before, provenance.resource_identity)
        observed = RuntimeIdentity.model_validate(finished["runtime_identity"].model_dump())
        matches = observed == provenance.runtime_identity
        binding = GeometryBinding(
            bundle_sha256=provenance.bundle_sha256,
            content_identity_sha256=self.bundle.content_identity_sha256,
            exported_runtime_identity=provenance.runtime_identity,
            observed_runtime_identity=observed,
            runtime_identity_matches=matches,
            association="content_matches_export_identity" if matches else "content_reverified_after_runtime_identity_change",
            revalidated_at=utc_now(),
        )
        return CompiledSceneRead(**finished, data=data, objects=scene_objects(data),
                                 geometry_provenance=provenance, geometry_binding=binding)

    def asset(self, asset_id: str, expected_sha256: str) -> bytes:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", asset_id) or asset_id not in self.bundle.assets:
            raise ReadServiceError("unknown_asset", "Unknown compiled scene asset", 404)
        asset = next(a for a in self.scene().data.mesh_assets if a.asset_id == asset_id)
        if asset.sha256 != expected_sha256:
            raise ReadServiceError("asset_revision_changed", "Asset digest changed; reload the candidate scene manifest", 409)
        return self.bundle.assets[asset_id]
