"""A release identity must fail on missing or changed paths, not silently shrink.

These tests build synthetic release trees; they never touch a real native release.
"""

import importlib.util
import json
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "release_identity.py"
SPEC = json.loads((Path(__file__).resolve().parents[1] / "config" / "release-identity.native-m1h.json").read_text())

spec = importlib.util.spec_from_file_location("release_identity", TOOL)
release_identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_identity)


def fake_release(root: Path, *, with_new_modules: bool = True) -> Path:
    files = {
        "src/mobilecar/app.py": b"patched app",
        "src/mobilecar/config.py": b"config",
        "assets/landerpi/model/robot.xml": b"<mujoco/>",
        "configs/default.yaml": b"profile: base\n",
        "configs/g4a2_server.yaml": b'extends: "default.yaml"\nprofile: g4a2\n',
        "configs/g4a1_server.yaml": b'extends: "default.yaml"\nprofile: g4a1\n',
        "requirements.lock": b"mujoco==3.1.6\n",
        "requirements-test.lock": b"pytest\n",
        "pyproject.toml": b"[project]\n",
        "docs/runtime_api_v1.md": b"documentation is excluded",
        "tests/integration/test_recording_end.py": b"test source is excluded",
        "var/reports/native.log": b"runtime state is excluded",
    }
    if with_new_modules:
        files["src/mobilecar/attestation.py"] = b"attestation module"
        files["src/mobilecar/session_binding.py"] = b"binding module"
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return root


def pin_file(platform_root: Path) -> Path:
    config = platform_root / "config"
    config.mkdir(parents=True, exist_ok=True)
    pin = config / "test-pin.json"
    paths = ["src/mobilecar/app.py", "src/mobilecar/config.py", "assets/landerpi/model/robot.xml",
             "configs/default.yaml", "configs/g4a2_server.yaml", "configs/g4a1_server.yaml",
             "requirements.lock", "requirements-test.lock", "pyproject.toml",
             "docs/runtime_api_v1.md"]
    pin.write_text(json.dumps({"schema_version": 1, "files": [{"path": p} for p in paths]}), encoding="utf-8")
    return pin


def spec_for(pin: Path) -> dict:
    body = json.loads(json.dumps(SPEC))
    body["required_groups"]["baseline_source"]["pin_file"] = str(pin)
    body["required_groups"]["baseline_source"]["ignore_paths"] = ["docs/runtime_api_v1.md"]
    body["watched_roots"] = ["src/mobilecar"]
    return body


def test_new_execution_modules_are_covered(tmp_path):
    root = fake_release(tmp_path / "release")
    pin = pin_file(tmp_path / "platform")
    report, code = release_identity.build(root, spec_for(pin), tmp_path / "platform")
    assert code == 0 and report["complete"] is True, report["missing_required"]
    assert {"src/mobilecar/attestation.py", "src/mobilecar/session_binding.py"} <= set(report["entries"])
    assert report["groups"]["patch_added_modules"]["missing"] == []
    assert report["release_digest"] == release_identity.digest_entries(
        {path: release_identity.sha256_file(root / path) for path, _ in report["entries"].items()})
    assert report["count_invariant"]["aggregate_covers_all_hashed"] is True


def test_missing_required_module_fails_and_names_it(tmp_path):
    root = fake_release(tmp_path / "release", with_new_modules=False)
    pin = pin_file(tmp_path / "platform")
    report, code = release_identity.build(root, spec_for(pin), tmp_path / "platform")
    assert code == 2 and report["complete"] is False
    missing = {item["path"] for item in report["missing_required"]}
    assert {"src/mobilecar/attestation.py", "src/mobilecar/session_binding.py"} <= missing
    # The anti-pattern this tool exists to prevent: no digest may be published over a partial set.
    assert "release_digest" not in report and "entries" not in report


def test_excluded_and_unlisted_paths_are_separate_facts(tmp_path):
    root = fake_release(tmp_path / "release")
    (root / "src/mobilecar/unannounced_module.py").write_text("nobody pinned me", encoding="utf-8")
    pin = pin_file(tmp_path / "platform")
    report, _ = release_identity.build(root, spec_for(pin), tmp_path / "platform")
    assert report["unlisted_under_watched_roots"] == ["src/mobilecar/unannounced_module.py"]
    assert not any(path.startswith(("var/", "tests/", "docs/")) for path in report["entries"])


def test_extends_closure_covers_nested_configs(tmp_path):
    root = fake_release(tmp_path / "release")
    pin = pin_file(tmp_path / "platform")
    report, _ = release_identity.build(root, spec_for(pin), tmp_path / "platform")
    assert set(report["groups"]["execution_configs"]["missing"]) == set()
    hashed = set(report["entries"])
    assert {"configs/default.yaml", "configs/g4a2_server.yaml", "configs/g4a1_server.yaml"} <= hashed


def test_verify_detects_changed_and_removed_content(tmp_path):
    root = fake_release(tmp_path / "release")
    pin = pin_file(tmp_path / "platform")
    report, _ = release_identity.build(root, spec_for(pin), tmp_path / "platform")
    assert release_identity.verify(root, report)[1] == 0
    (root / "src/mobilecar/app.py").write_bytes(b"different bytes")
    result, code = release_identity.verify(root, report)
    assert code == 2 and result["changed_paths"] == ["src/mobilecar/app.py"] and result["match"] is False
    (root / "src/mobilecar/session_binding.py").unlink()
    result, code = release_identity.verify(root, report)
    assert code == 2 and result["removed_paths"] == ["src/mobilecar/session_binding.py"]
