"""Synthetic API regression for the compiled-geometry candidate.

Distinct from server native mesh verification. The content identity of the
export is what lets the candidate keep serving after an Episode change; any
model or scene content change must still be refused.
"""
import copy
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from test_mobilecar_read import read_client
from unirobot.api import create_app
from unirobot.mobilecar_geometry import GeometryBundle, content_digest


def make_bundle(tmp_path, upstream):
    scene = copy.deepcopy(upstream.payloads['/api/v1/scene'])
    body = b'compiled fixture bytes'
    sha = hashlib.sha256(body).hexdigest()
    asset = scene['mesh_assets'][0]
    asset.update(source_sha256=asset['sha256'], source_mesh_name='base_mesh', sha256=sha,
                 coordinate_space='mujoco_compiled_mesh', units='m', mesh_preprocessing_applied=True)
    scene['links'][0]['geoms'][0].update(group=3, contype=2, conaffinity=1, collision=True)
    health = upstream.payloads['/api/v1/health']
    provenance = dict(compiler='MuJoCo', compiler_version='synthetic',
        runtime_identity={k: health[k] for k in ('run_id', 'backend_generation', 'episode_id')},
        resource_identity={k: scene[k] for k in ('contract_version', 'model_id', 'model_sha256', 'scene_id')},
        native_scene_sha256=content_digest(upstream.payloads['/api/v1/scene']),
        model_inputs_sha256=content_digest([]), compiled_scene_sha256=content_digest(scene),
        native_scene_builder_sha256='0'*64, verification_scope='static_compilation_matches_live_manifest_not_live_memory_or_contacts')
    bundle = dict(scene=scene, geometry_provenance=provenance, model_inputs=[], mesh_report=[])
    provenance['bundle_sha256'] = content_digest(bundle)
    directory = tmp_path/'compiled'; directory.mkdir(); (directory/'assets').mkdir()
    (directory/'bundle.json').write_text(json.dumps(bundle))
    (directory/'assets/base.stl').write_bytes(body)
    return directory, sha, body


def test_candidate_wire_assets_and_other_resources_stay_read_v1(read_client, tmp_path):
    old, upstream, _ = read_client
    directory, sha, body = make_bundle(tmp_path, upstream)
    app = create_app(draft_db_path=tmp_path/'candidate.sqlite3', compiled_geometry_path=directory,
                     mobilecar_integration=old.app.state.mobilecar_integration)
    with TestClient(app) as client:
        response = client.get('/api/v1/mobilecar/scene'); assert response.status_code == 200
        value = response.json()
        assert value['schema_version'] == 'unirobot-mobilecar-geometry-2'
        assert value['data_source'] == 'live_native_http_with_verified_compiled_geometry'
        assert value['session_ready'] is False and value['read_only'] is True
        assert value['platform_session_id'] is None
        assert value['objects'] == old.get('/api/v1/mobilecar/scene').json()['objects']
        geom = value['data']['links'][0]['geoms'][0]
        assert (geom['group'], geom['contype'], geom['conaffinity'], geom['collision']) == (3, 2, 1, True)
        asset = value['data']['mesh_assets'][0]
        assert asset['coordinate_space'] == 'mujoco_compiled_mesh' and asset['units'] == 'm'
        binding = value['geometry_binding']
        assert binding['content_matches'] is True and binding['runtime_identity_matches'] is True
        assert binding['association'] == 'content_matches_export_identity'
        assert binding['exported_runtime_identity'] == binding['observed_runtime_identity']
        assert len(binding['content_identity_sha256']) == 64
        assert client.get(asset['uri']).content == body
        assert client.get('/api/v1/mobilecar/scene/assets/base?sha256='+'0'*64).status_code == 409
        assert client.get('/api/v1/mobilecar/scene/assets/unknown?sha256='+sha).status_code == 404
        for resource in ('capabilities', 'snapshot'):
            assert client.get('/api/v1/mobilecar/'+resource).json()['schema_version'] == 'unirobot-mobilecar-read-1'
        for mutation in ('scene', 'model', 'offline'):
            raw = copy.deepcopy(upstream.payloads)
            if mutation == 'scene': upstream.payloads['/api/v1/scene']['source'] = 'changed'
            elif mutation == 'model': upstream.payloads['/api/v1/scene']['model_sha256'] = '1'*64
            else: upstream.fail_path = '/api/v1/health'
            for path in ('/api/v1/mobilecar/scene', asset['uri']):
                error = client.get(path)
                assert error.status_code == (503 if mutation == 'offline' else 409)
                assert error.json()['detail']['code'] == ('native_offline' if mutation == 'offline' else 'geometry_source_changed')
            upstream.payloads = raw; upstream.fail_path = None
    assert all(method == 'GET' for method, _ in upstream.calls)
    assert not any('/scene/assets/' in path for _, path in upstream.calls)  # no raw asset fallback


def test_episode_change_keeps_verified_content_and_reports_the_new_identity(read_client, tmp_path):
    old, upstream, _ = read_client
    directory, sha, body = make_bundle(tmp_path, upstream)
    app = create_app(draft_db_path=tmp_path/'candidate.sqlite3', compiled_geometry_path=directory,
                     mobilecar_integration=old.app.state.mobilecar_integration)
    exported = upstream.payloads['/api/v1/health']['episode_id']
    with TestClient(app) as client:
        upstream.payloads['/api/v1/health']['episode_id'] = 'after-reset'
        upstream.payloads['/api/v1/snapshot']['episode_id'] = 'after-reset'
        response = client.get('/api/v1/mobilecar/scene')
        assert response.status_code == 200, response.text
        binding = response.json()['geometry_binding']
        assert binding['runtime_identity_matches'] is False
        assert binding['association'] == 'content_reverified_after_runtime_identity_change'
        assert binding['exported_runtime_identity']['episode_id'] == exported
        assert binding['observed_runtime_identity']['episode_id'] == 'after-reset'
        assert response.json()['runtime_identity']['episode_id'] == 'after-reset'
        assert response.json()['geometry_provenance']['runtime_identity']['episode_id'] == exported
        assert client.get(f"/api/v1/mobilecar/scene/assets/base?sha256={sha}").content == body
    assert all(method == 'GET' for method, _ in upstream.calls)


@pytest.mark.parametrize('corruption', ['bundle', 'asset'])
def test_candidate_corrupt_bundle_fails_at_startup(read_client, tmp_path, corruption):
    _, upstream, _ = read_client
    directory, _, _ = make_bundle(tmp_path, upstream)
    if corruption == 'bundle':
        path = directory/'bundle.json'; value = json.loads(path.read_text()); value['scene']['tcp_site'] = 'tampered'; path.write_text(json.dumps(value))
    else: (directory/'assets/base.stl').write_bytes(b'tampered')
    with pytest.raises(ValueError, match='digest mismatch|integrity mismatch'):
        GeometryBundle(directory)
