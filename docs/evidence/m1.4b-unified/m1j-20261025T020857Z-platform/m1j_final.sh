set -uo pipefail
R=${R:?}; RP=$HOME/Desktop/uniRobotPlatform; MC=$HOME/Desktop/mobileCar
REL=$RP/releases/$R; PL=$REL/backend; V=$RP/var/reports/$R; PY=$RP/envs/gateway-py314/bin/python
cd $PL || exit 1
echo "== identity over m1h assembled release =="
$PY tools/release_identity.py build --root $MC/releases/m1h-20261024T152235Z-native --spec $PL/config/release-identity.native-m1h.json --platform-root $PL --out $V/release-identity.m1h.json >/dev/null 2>&1; echo "exit=$?"
echo "== identity over plain drvfix release (expected to fail) =="
$PY tools/release_identity.py build --root $MC/releases/drvfix-20261019T044549Z-0a80415b2577 --spec $PL/config/release-identity.native-m1h.json --platform-root $PL --out $V/release-identity.drvfix.json >/dev/null 2>&1; echo "exit=$? (2 = required paths missing)"
$PY tools/release_identity.py verify --root $MC/releases/m1h-20261024T152235Z-native --manifest $V/release-identity.m1h.json --out $V/release-identity.verify.json >/dev/null 2>&1; echo "verify exit=$?"
$PY - <<'PY'
import json, os
v = os.path.expanduser("~/Desktop/uniRobotPlatform/var/reports/") + os.environ["R"]
a = json.load(open(f"{v}/release-identity.m1h.json")); d = json.load(open(f"{v}/release-identity.drvfix.json")); z = json.load(open(f"{v}/release-identity.verify.json"))
print("m1h: complete=%s required=%d hashed=%d digest=%s unlisted=%d" % (a["complete"], a["required_count"], a["hashed_count"], a["release_digest"][:16], len(a["unlisted_under_watched_roots"])))
print("m1h groups:", {k: (x["required"], x["hashed"], len(x["missing"])) for k, x in a["groups"].items()})
print("drvfix: complete=%s missing=%s digest_published=%s" % (d["complete"], sorted({i["path"] for i in d["missing_required"]}), "release_digest" in d))
print("verify recomputed match:", z["match"], z["recorded_count"], z["recomputed_release_digest"][:16])
PY
echo "== full platform suite =="
UNIROBOT_REPO_ROOT=$REL $PY -m pytest -q 2>&1 | tail -5
