# M1.2d evidence index

Release: platform `m1e-20261024T090448Z-platform`; native test release `m1e-20261024T090412Z-native`.
All execution was on server `cec-sim`; no MuJoCo physics instance was created.

## Classification

| Class | Artifact | Proves | Does not prove |
|---|---|---|---|
| Platform unit/fixture | `platform/focused-m1e.junit.xml` (93 passed) | P1 lifecycle/TTL, live-current contract and refusals with synthetic native | Real native HTTP |
| Platform full suite | `platform/full-m1e.junit.xml` (97 passed, 3 failed) | Same three historical layout failures, no new regressions | A green full suite in this checkout layout |
| Native unit/integration | `native/reports/native-m1e.junit.xml` (57 passed) | lifecycle serialization barriers, prepared-only TTL, started survival, real app/recorder with mock backend | MuJoCo physics or deployment |
| Pre-fix contrast | `native/prefix-race/*` (2 failed) | The race tests fail on the pre-fix native code | A passing current candidate |
| Cross-HTTP | `native/http/cross-http.json` | Real platform app + real `NativeBindingClient` + real native mock HTTP: validation passed, prepare/readback/start/begin/release, duplicate start/begin, identity/config refusals, recorder files | Production G1 or physical motion |
| Live production candidate | `platform/live-m1e/*` | Real 18949 against unpatched 8792: G1 still refused, list stored empty, 404s; native unchanged | Real G1 prepared/Start |
| Freeze | `platform/source-listing-final.txt`, `native/reports/*`, patch | Platform/native source and dependency identities | Deployment |

## P1 evidence

- Native lifecycle lock: `src/mobilecar/app.py` now serializes RESET, legacy `episodes/start`, `recording/begin`, stop and recorder-failure stop through `Runtime.lifecycle_lock`; order is lifecycle -> backend -> recorder. The barrier tests are `tests/integration/test_lifecycle_race.py`.
- `native/prefix-race/prefix-race.log` shows both new race tests failing against the previous release, so the gate is not tautological.
- Prepared TTL: `tests/integration/test_session_binding.py` proves prepared expires, started survives beyond TTL, duplicate prepare still conflicts while started, and release/RESET invalidate. `expires_scope="prepared"` is explicit in native readback.
- Live current: `tests/test_prepare.py` proves single-session GET is read-only, offline/identity/terminal states never report ready, list is explicitly stored, and repeated GET does not write or rebind.

## Cross-HTTP (test-only mock recipe)

- `native/http/cross-http.json`: test recipe `mobilecar.g1.teleop.mock-testonly`, validation passed/eligible, Session created and started, begin returned RECORDING, initial snapshot hash matched, duplicate begin replayed with no new events, release invalidated, current never ready after release.
- The test platform was stopped; it ran on port 18948 against native mock port 18947. Both were isolated and had no physics.
- This is **protocol integration**, not production G1 validation. The production recipe was not changed and was not used to make the mock pass.

## Live production failure (real)

- Port 18949, production recipe revision 3, native 8792 PID 941842.
- Validation: snapshot `cs-8f5f2d9076327e145b47f7f69900185f49dacf7a`, `failed`, `execution_eligible=false`.
- Blocking: `interface_profile` (configuration); `deployed_config_attestation`, `scene_manifest_attestation`, `runtime_python_version`, `runtime_package_versions`, `session_binding_protocol`, `recording_begin_protocol` (readiness, all unsupported).
- Session create: 409 `validation_incomplete`; list: `{"source":"stored","live":false,"sessions":[]}`; missing session/begin: 404.
- Native after: run `run_9c88e3e36e7648a3852c9f590e43ed5f`, generation 1, episode `episode_43c22f95536f4517be04e4b195d6d354`, `recording=IDLE`, no owners, `safety_latched=true`.

## Source and dependency identity

- Platform backend: 46 non-cache files; listing SHA-256 `4c4bca55…b2`; Python 3.14.6, fastapi 0.161.1, pydantic 2.14.1, uvicorn 0.54.0, PyYAML 6.0.3, pytest 9.1.1.
- Native final test release: source listing SHA-256 `ff27bb5e…b1cb`; native Python 3.10.12 and lock versions exact. Config digest `02351b71…a9af0`; scene digest `5969e260…f1bf2d`; `physics_state_calls=0`.
- Native patch: `native/native-m1e.patch`, SHA-256 `df7e6e96…d7e6`, applies cleanly to `a5cef52`.
- Old source pin `a0109804…911c` matches **a5cef52 base only**. Patched candidate identities are:
  - a5cef52 + patch: `c325a2b3…6efd`
  - drvfix + patch: `dd24d1c8…f7da` (the server test release)
- Base differences (old pin scope) are listed in `native/reports/native-deploy-identity.json`; they include `backend.py`, modelgen source/init, an xacro asset, G4A2 html/js, AGENTS, and (for the patched comparison) three docs. Neither patched candidate may reuse the old pin.

## Ports / processes

- 18949 new platform candidate (production recipe, read-only); 18944 prior M1.2c candidate; 18943 backend consumed by frontend; 18946 latest frontend preview proxy; 18933 older preview; 18941/18942 unchanged; 8792 untouched.
- 18947 native mock and 18948 test platform were used and stopped. 18946 was not used.
