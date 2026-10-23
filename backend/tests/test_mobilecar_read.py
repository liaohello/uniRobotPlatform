"""Read-contract regression tests. Fixtures never represent a real M1 run."""
import copy
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from test_mobilecar import FakeOpener
from unirobot.api import create_app
from unirobot.contracts import AdapterConfig
from unirobot.mobilecar import MobileCarIntegration


@pytest.fixture()
def read_client(tmp_path):
    integration = MobileCarIntegration(AdapterConfig(id="mobilecar", title="synthetic", project_root="unused", base_url="http://synthetic.invalid"))
    identity = {"run_id": "synthetic-run", "backend_generation": 1, "episode_id": "synthetic-episode"}
    resource = {key: integration.pin['expected'][key] for key in ('contract_version', 'model_id', 'model_sha256', 'scene_id')}
    transform = {"position_m": [0, 0, 0], "orientation_xyzw": [0, 0, 0, 1]}
    asset_body = b'synthetic mesh bytes, not a product model'
    digest = hashlib.sha256(asset_body).hexdigest()
    link = {"name": "base_link", "parent_name": None, "joint_name": None, "joint_type": "free", "joint_axis": [0, 0, 1], "local_transform": transform,
            "geoms": [{"name": "base_visual", "geom_type": "mesh", "size_m": [1, 1, 1], "local_transform": transform, "rgba": [1, 1, 1, 1], "mesh_asset_id": "base", "collision": False, "group": 0}]}
    payloads = {
        "/api/v1/health": {**identity, "status": "ok", "interface_profile": "synthetic-profile", "recording_required_for_motion": True},
        "/api/v1/capabilities": {**resource, "backend_kind": "mujoco", "arm_joint_names": ['joint1', 'joint2'], "arm_user_limits_rad": [[-1, 1], [-2, 2]],
            "arm_velocity_limits_rad_s": [1, 1], "gripper_min_width_m": 0, "gripper_max_width_m": .04, "base_linear_limit_m_s": .2, "base_yaw_limit_rad_s": .5,
            "tcp_position_tolerance_m": .01, "tcp_orientation_is_soft": True, "supported_commands": ['STOP', 'ARM_JOINT_TARGET'], "sensor_streams": ['RGB'],
            "camera_parent_body": "link4", "tcp_parent_body": "guide_rod_link", "ground_truth_policy_visible": False, "unexpected_secret": "omit-me"},
        "/api/v1/scene": {**resource, "links": [link], "world_links": [], "mesh_assets": [{"asset_id": "base", "uri": "https://untrusted.invalid/do-not-fetch", "sha256": digest, "media_type": "model/stl"}],
            "camera_ids": ['arm_camera'], "tcp_site": "grasp_tcp", "source": "synthetic"},
        "/api/v1/scene/assets/base": asset_body,
        "/api/v1/snapshot": {**identity, 'contract_version': 'mobilecar-1.0', 'episode_started_backend_monotonic_s': 0, 'backend_monotonic_s': 20, 'sim_time_s': 2,
            'feedback_time_s': 19.99, 'wall_utc': '2026-10-23T00:00:00Z', 'clock_id': 'backend_monotonic', 'control_tick_id': 'tick-1', 'task_phase': 'OBSERVE',
            'base': {'frame_id': 'base_link', 'position_world_sim_m': [1, 2, 0], 'orientation_world_sim_xyzw': [0, 0, 0, 1], 'vx_m_s': .1, 'vy_m_s': 0, 'wz_rad_s': 0,
                'requested_vx_m_s': .2, 'requested_vy_m_s': 0, 'requested_wz_rad_s': .1, 'stopped': False, 'stop_latched': False},
            'arm': {'user_joint_positions_rad': [.1, .2], 'user_joint_targets_rad': [.3, .4], 'model_joint_positions_rad': [.1, .2], 'model_joint_targets_rad': [.3, .4],
                'joint_velocities_rad_s': [0, 0], 'joint_torques_nm': [0, 0], 'joint_margin_rad': [.9, 1.8], 'model_limits_rad': [[-1, 1], [-2, 2]], 'coordinates_status': 'known'},
            'gripper': {'width_m': .01, 'target_width_m': .02, 'model_drive_position_rad': .1, 'model_drive_target_rad': .2, 'unknown_oracle': 'omit-me'},
            'tcp': {'frame_id': 'world_sim', 'position_m': [.1, .2, .3], 'orientation_xyzw': [0, 0, 0, 1], 'position_error_m': None, 'orientation_error_rad': None, 'held': False},
            'sensors': [{'kind': 'RGB', 'available': True, 'fresh': False, 'sample_id': 'sample-1', 'stream_id': 'rgb-1', 'measurement_time_s': 19, 'arrival_time_s': 19.1,
                'clock_id': 'backend_monotonic', 'valid_fraction': None, 'asset_uri': 'sensors/rgb/sample-1.jpg', 'quality': 'stale', 'capture_sim_time_s': 1,
                'capture_backend_monotonic_s': 19, 'capture_control_tick_id': 'tick-0', 'feedback_sample_id': 'feedback-0', 'observation_age_s': 1, 'profile_id': 'synthetic-profile'}],
            'active_session_id': 'native-session', 'active_operator_kind': 'human', 'base_owner_session_id': 'native-session', 'arm_owner_session_id': None, 'safety_latched': True,
            'recording': {'status': 'IDLE', 'episode_id': None, 'command_capture_ready': False, 'recording_segment_id': None, 'queued_events': 0, 'dropped_events': 0, 'error': None},
            'model_joint_positions_rad': {'joint1': .1, 'joint2': .2}, 'diagnostics': {'object_pose_world_sim': {'secret': 'omit-me'}},
            'contact_summary': {'truth': 'omit-me'}, 'plan': {'untrusted_preview': 'omit-me'}, 'unknown_oracle': 'omit-me'},
    }
    opener = FakeOpener(copy.deepcopy(payloads))
    integration._opener = opener
    app = create_app(draft_db_path=tmp_path/'drafts.sqlite3')
    app.state.mobilecar_integration = integration
    with TestClient(app) as client:
        yield client, opener, digest


def test_scene_ids_and_hashed_same_origin_assets(read_client):
    client, upstream, digest = read_client
    scene = client.get('/api/v1/mobilecar/scene')
    assert scene.status_code == 200
    value = scene.json()
    assert value['session_ready'] is False and value['platform_session_id'] is None
    assert value['read_only'] is True and value['deployed_content_verified'] is False
    assert value['interface_profile'] == 'synthetic-profile'
    assert value['data_source'] == 'live_native_http'
    assert value['objects'][0]['object_id'] == 'body:base_link'
    assert value['objects'][1]['object_id'] == 'geom:base_link/base_visual'
    assert value['world_pose_semantics'] == 'compiled_initial_layout_not_live_object_state'
    uri = value['data']['mesh_assets'][0]['uri']
    assert uri == f'/api/v1/mobilecar/scene/assets/base?sha256={digest}'
    asset = client.get(uri)
    assert asset.status_code == 200 and asset.content == upstream.payloads['/api/v1/scene/assets/base']
    assert asset.headers['etag'] == f'"{digest}"'
    assert scene.headers['cache-control'] == asset.headers['cache-control'] == 'no-store'
    assert all(method == 'GET' for method, _ in upstream.calls)


def test_snapshot_separates_actual_target_preserves_source_clock_and_drops_oracle(read_client):
    client, upstream, _ = read_client
    before = copy.deepcopy(upstream.payloads)
    response = client.get('/api/v1/mobilecar/snapshot')
    assert response.status_code == 200
    value = response.json(); data = value['data']
    assert data['actual']['arm']['user_joint_positions_rad'] == [.1, .2]
    assert data['target']['user_joint_positions_rad'] == [.3, .4]
    assert 'user_joint_targets_rad' not in data['actual']['arm']
    assert data['target']['command_id'] is None and data['preview'] is None
    assert data['target']['tcp'] is None
    assert data['target']['base_velocity'] == {'frame_id': 'base_link', 'vx_m_s': .2, 'vy_m_s': 0, 'wz_rad_s': .1}
    assert data['actual']['base']['position_world_sim_m'] == [1, 2, 0]
    assert data['time']['feedback_time_s'] == 19.99 and data['time']['sim_time_s'] == 2
    assert data['authority']['base_owner_session_id'] == 'native-session'
    assert data['authority']['authorizes_caller'] is False and data['authority']['lease_status'] == 'not_exposed'
    assert data['sensor_media_status'] == 'not_exposed'
    assert data['sensors'][0]['native_asset_uri'] == 'sensors/rgb/sample-1.jpg'
    assert data['sensors'][0]['frame_id'] is None and data['sensors'][0]['fresh'] is False
    assert 'omit-me' not in response.text and 'diagnostics' not in data and 'contact_summary' not in data
    assert upstream.payloads == before
    assert upstream.calls == [('GET', p) for p in ['/api/v1/health', '/api/v1/capabilities', '/api/v1/snapshot', '/api/v1/health']]


def test_capabilities_do_not_enable_platform_control(read_client):
    client, _, _ = read_client
    response = client.get('/api/v1/mobilecar/capabilities')
    assert response.status_code == 200
    value = response.json()
    assert value['data']['arm_joint_names'] == ['joint1', 'joint2']
    assert value['platform_commands_available'] is value['platform_recording_available'] is value['platform_replay_available'] is False
    assert 'unexpected_secret' not in value['data']


@pytest.mark.parametrize('path', ['scene', 'capabilities', 'snapshot'])
def test_offline_is_explicit_and_does_not_return_cached_success(read_client, path):
    client, upstream, _ = read_client
    assert client.get('/api/v1/mobilecar/'+path).status_code == 200
    upstream.fail_path = '/api/v1/health'
    response = client.get('/api/v1/mobilecar/'+path)
    assert response.status_code == 503
    assert response.json()['detail']['code'] == 'native_offline'
    assert 'data' not in response.json()


@pytest.mark.parametrize('mutation', ['wrong_frame', 'nonfinite', 'wrong_length', 'bool_number', 'wrong_version', 'missing_state'])
def test_malformed_external_state_is_rejected(read_client, mutation):
    client, upstream, _ = read_client
    value = upstream.payloads['/api/v1/snapshot']
    if mutation == 'wrong_frame': value['tcp']['frame_id'] = 'unmapped_frame'
    elif mutation == 'nonfinite': value['arm']['user_joint_positions_rad'][0] = float('nan')
    elif mutation == 'wrong_length': value['arm']['user_joint_positions_rad'] = [0]
    elif mutation == 'bool_number': value['tcp']['position_m'][0] = True
    elif mutation == 'wrong_version': value['contract_version'] = 'different-2'
    else: del value['base']
    response = client.get('/api/v1/mobilecar/snapshot')
    assert response.status_code == 502
    assert response.json()['detail']['code'] == 'native_incompatible'
    assert 'omit-me' not in response.text


def test_snapshot_runtime_mismatch_is_conflict(read_client):
    client, upstream, _ = read_client
    upstream.payloads['/api/v1/snapshot']['episode_id'] = 'after-reset'
    response = client.get('/api/v1/mobilecar/snapshot')
    assert response.status_code == 409 and response.json()['detail']['code'] == 'native_identity_changed'


def test_health_identity_change_during_scene_read_is_conflict(read_client):
    client, upstream, _ = read_client
    original = upstream.open
    def open_with_reset(request, *, timeout):
        if request.full_url.endswith('/api/v1/scene'):
            upstream.payloads['/api/v1/health']['backend_generation'] = 2
        return original(request, timeout=timeout)
    upstream.open = open_with_reset
    response = client.get('/api/v1/mobilecar/scene')
    assert response.status_code == 409 and response.json()['detail']['code'] == 'native_identity_changed'


def test_asset_allowlist_revision_and_integrity(read_client):
    client, upstream, digest = read_client
    response = client.get(f'/api/v1/mobilecar/scene/assets/absent?sha256={digest}')
    assert response.status_code == 404
    assert all(path != '/api/v1/scene/assets/absent' for _, path in upstream.calls)
    assert client.get('/api/v1/mobilecar/scene/assets/base?sha256='+'0'*64).status_code == 409
    upstream.payloads['/api/v1/scene/assets/base'] = b'changed bytes'
    response = client.get(f'/api/v1/mobilecar/scene/assets/base?sha256={digest}')
    assert response.status_code == 502 and response.json()['detail']['code'] == 'asset_integrity_failed'
    assert client.get('/api/v1/mobilecar/scene/assets/base').status_code == 422


def test_invalid_scene_references_are_not_exposed(read_client):
    client, upstream, _ = read_client
    upstream.payloads['/api/v1/scene']['links'][0]['geoms'][0]['mesh_asset_id'] = 'missing'
    assert client.get('/api/v1/mobilecar/scene').status_code == 502


def test_resource_mismatch_is_observable_not_session_readiness(read_client):
    client, upstream, _ = read_client
    upstream.payloads['/api/v1/capabilities']['model_sha256'] = '0'*64
    response = client.get('/api/v1/mobilecar/capabilities')
    assert response.status_code == 200 and response.json()['resource_matches_pin'] is False
    assert response.json()['session_ready'] is False


def test_openapi_exposes_typed_read_contract(read_client):
    client, _, _ = read_client
    spec = client.get('/openapi.json').json()
    schema = spec['paths']['/api/v1/mobilecar/snapshot']['get']['responses']['200']['content']['application/json']['schema']
    assert schema['$ref'].endswith('/SnapshotRead')
    assert spec['components']['schemas']['SnapshotData']['properties']['preview']['type'] == 'null'
