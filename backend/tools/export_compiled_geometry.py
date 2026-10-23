"""Server-only static mesh export. Never creates MjData or advances physics.

Run in the deployed native MuJoCo environment, with that release's src on
PYTHONPATH. Inputs and live native are read-only; output must be a new directory.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct
import urllib.request
import xml.etree.ElementTree as ET

import mujoco
import numpy as np


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(body):
    return hashlib.sha256(body).hexdigest()


def compiled_stl(model, mesh_id):
    """Preserve compiled vertices and local face indices, with no further scale."""
    start, count = int(model.mesh_vertadr[mesh_id]), int(model.mesh_vertnum[mesh_id])
    vertices = model.mesh_vert[start:start + count]
    start, count = int(model.mesh_faceadr[mesh_id]), int(model.mesh_facenum[mesh_id])
    faces = model.mesh_face[start:start + count]
    triangles = vertices[faces]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals[lengths > 0] /= lengths[lengths > 0, None]
    facets = np.zeros(count, dtype=np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")]))
    facets["normal"], facets["vertices"] = normals, triangles
    return b"uniRobot MuJoCo compiled mesh; metres".ljust(80, b"\0") + struct.pack("<I", count) + facets.tobytes()


def model_inputs(model_path, native_root):
    """This mobileCar model uses relative includes and assets.xml file meshes.

    Reject other file-backed asset types rather than publish partial provenance.
    """
    paths, mesh_files = set(), {}

    def xml(path):
        path = path.resolve()
        path.relative_to(native_root)
        if path in paths:
            return
        paths.add(path)
        root = ET.parse(path).getroot()
        for node in root.iter():
            filename = node.get("file")
            if filename is None:
                continue
            if node.tag == "include":
                xml(model_path.parent / filename)
            elif node.tag == "mesh":
                asset = (model_path.parent / filename).resolve()
                asset.relative_to(native_root)
                paths.add(asset)
                mesh_files[node.attrib["name"]] = asset
            else:
                raise ValueError("Unsupported file-backed model input: " + node.tag)
        compiler = root.find("compiler")
        if compiler is not None and any(compiler.get(k) for k in ("assetdir", "meshdir", "texturedir")):
            raise ValueError("This exporter requires the native model's explicit relative asset paths")

    xml(model_path)
    entries = [{"path": str(p.relative_to(native_root)), "sha256": digest(p.read_bytes()), "size_bytes": p.stat().st_size} for p in sorted(paths)]
    return entries, mesh_files


def get_json(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def export(model_path, native_root, native_url, output):
    from mobilecar.sensors.scene import build_scene_manifest
    import mobilecar.sensors.scene as native_scene

    native_root, model_path = native_root.resolve(), model_path.resolve()
    before = get_json(native_url + "/api/v1/health")
    raw = get_json(native_url + "/api/v1/scene")
    inputs, mesh_files = model_inputs(model_path, native_root)
    if digest(model_path.read_bytes()) != raw["model_sha256"]:
        raise ValueError("Root model differs from the live native manifest")
    model = mujoco.MjModel.from_xml_path(str(model_path))
    baseline = json.loads(build_scene_manifest(model, model_path, model_id=raw["model_id"], scene_id=raw["scene_id"]).model_dump_json())
    if baseline != raw:
        raise ValueError("Offline compiled manifest differs from live native; refusing geometry publication")
    scene = copy.deepcopy(raw)
    bodies = {model.body(i).name or f"body_{i}": i for i in range(model.nbody)}
    bodies["world_static"] = 0
    for link in scene["links"] + scene["world_links"]:
        body_id = bodies[link["name"]]
        start, count = int(model.body_geomadr[body_id]), int(model.body_geomnum[body_id])
        geoms = {model.geom(i).name or f"geom_{i}": i for i in range(start, start + count)}
        for geom in link["geoms"]:
            i = geoms[geom["name"]]
            geom.update(group=int(model.geom_group[i]), contype=int(model.geom_contype[i]), conaffinity=int(model.geom_conaffinity[i]))
            geom["collision"] = bool(geom["contype"] or geom["conaffinity"])
            if geom["geom_type"] == "mesh":
                geom["size_m"] = [1.0, 1.0, 1.0]
    assets = {a["asset_id"]: a for a in scene["mesh_assets"]}
    output.mkdir(parents=True, exist_ok=False)
    (output / "assets").mkdir()
    mesh_report = []
    for i in range(model.nmesh):
        name = model.mesh(i).name
        asset_id = name.removesuffix("_mesh") or name
        asset = assets[asset_id]
        if digest(mesh_files[name].read_bytes()) != asset["sha256"]:
            raise ValueError("Raw mesh changed during compile: " + name)
        body = compiled_stl(model, i)
        (output / "assets" / (asset_id + ".stl")).write_bytes(body)
        asset.update(source_sha256=asset["sha256"], source_mesh_name=name, sha256=digest(body),
                     coordinate_space="mujoco_compiled_mesh", units="m", mesh_preprocessing_applied=True)
        mesh_report.append({"asset_id": asset_id, "vertices": int(model.mesh_vertnum[i]), "triangles": int(model.mesh_facenum[i]), "sha256": digest(body), "size_bytes": len(body)})
    after = get_json(native_url + "/api/v1/health")
    identity_keys = ("run_id", "backend_generation", "episode_id", "interface_profile", "recording_required_for_motion")
    if any(before[k] != after[k] for k in identity_keys) or raw != get_json(native_url + "/api/v1/scene"):
        raise ValueError("Live native changed during export")
    if inputs != model_inputs(model_path, native_root)[0]:
        raise ValueError("Model input files changed during export")
    provenance = {
        "compiler": "MuJoCo", "compiler_version": mujoco.__version__,
        "runtime_identity": {k: before[k] for k in ("run_id", "backend_generation", "episode_id")},
        "resource_identity": {k: raw[k] for k in ("contract_version", "model_id", "model_sha256", "scene_id")},
        "native_scene_sha256": digest(canonical(raw)), "model_inputs_sha256": digest(canonical(inputs)),
        "compiled_scene_sha256": digest(canonical(scene)), "native_scene_builder_sha256": digest(Path(native_scene.__file__).read_bytes()),
        "verification_scope": "static_compilation_matches_live_manifest_not_live_memory_or_contacts",
    }
    bundle = {"scene": scene, "geometry_provenance": provenance, "model_inputs": inputs, "mesh_report": mesh_report}
    provenance["bundle_sha256"] = digest(canonical(bundle))
    (output / "bundle.json").write_text(json.dumps(bundle, indent=2) + "\n")
    print(json.dumps({"bundle_sha256": provenance["bundle_sha256"], "meshes": len(assets), "model_inputs": len(inputs), "compiler_version": mujoco.__version__}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, required=True)
    parser.add_argument("--native-url", default="http://127.0.0.1:8792")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export(args.model, args.native_root, args.native_url.rstrip("/"), args.output)
