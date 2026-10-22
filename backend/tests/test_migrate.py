from unirobot.migrate import audit


def test_manifest_sources_exist():
    report = audit()
    assert report["manifest_version"] == "0.1"
    assert len(report["modules"]) == 15
    missing = [item["id"] for item in report["modules"] if not item["source_exists"]]
    assert missing == []
    assert report["counts"].get("blocked", 0) == 0


def test_manifest_keeps_environments_isolated():
    report = audit()
    assert len(report["environments"]) == 4
    assert all(env["isolated"] for env in report["environments"])
    versions = {env["mujoco"] for env in report["environments"]}
    assert {"3.1.6", "3.11.0", "3.14.0"} <= versions
    assert report["do_not_migrate"]
