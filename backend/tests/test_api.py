import pytest
from fastapi.testclient import TestClient

from unirobot.api import create_app


@pytest.fixture()
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health_and_platform(client):
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    platform = client.get("/api/v1/platform").json()
    assert platform["tasks"] == 12
    assert platform["coverage"]["verified"] == 6


def test_tasks_and_filters(client):
    tasks = client.get("/api/v1/tasks").json()
    assert len(tasks) == 12
    assert all("adapter" in item and "available" in item for item in tasks)
    only_bimanual = client.get("/api/v1/tasks", params={"robot": "so101_dual"}).json()
    assert len(only_bimanual) == 4
    verified = client.get("/api/v1/tasks", params={"maturity": "verified"}).json()
    assert len(verified) == 8
    nav = client.get("/api/v1/tasks", params={"template": "NAV-POINT"}).json()
    assert len(nav) == 2
    assert client.get("/api/v1/tasks/unknown").status_code == 404


def test_prepare_run_and_conflict(client):
    response = client.post(
        "/api/v1/runs",
        json={"task_id": "mobilecar.g3b.nav_point", "seed": 7, "launch": False},
    )
    assert response.status_code == 201
    run = response.json()
    assert run["state"] == "prepared"
    assert "--seed" not in run["native_command"]
    assert "configs/g3b_server_room_a.yaml" in run["native_command"]

    conflict = client.post(
        "/api/v1/runs", json={"task_id": "mobilecar.g4a1.nearfield_grasp"}
    )
    assert conflict.status_code == 409

    stopped = client.post(f"/api/v1/runs/{run['run_id']}/stop")
    assert stopped.status_code == 200
    assert stopped.json()["state"] == "stopped"

    again = client.post(
        "/api/v1/runs", json={"task_id": "mobilecar.g4a1.nearfield_grasp"}
    )
    assert again.status_code == 201
    client.post(f"/api/v1/runs/{again.json()['run_id']}/stop")


def test_policy_checkpoint_override(client):
    response = client.post(
        "/api/v1/runs",
        json={
            "task_id": "bimanual.p5.act_rollout",
            "seed": 7,
            "overrides": {"checkpoint": "outputs/p5/checkpoints/016000"},
        },
    )
    assert response.status_code == 201
    run = response.json()
    assert "016000" in run["native_command"]
    assert "{checkpoint}" not in run["native_command"]
    client.post(f"/api/v1/runs/{run['run_id']}/stop")


def test_run_validation(client):
    assert (
        client.post("/api/v1/runs", json={"task_id": "missing"}).status_code == 404
    )
    invalid = client.post(
        "/api/v1/runs",
        json={"task_id": "bimanual.p5.act_rollout", "mode": "teleop"},
    )
    assert invalid.status_code == 422
    assert client.get("/api/v1/runs/missing").status_code == 404


def test_console_is_served(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "统一任务台" in page.text
