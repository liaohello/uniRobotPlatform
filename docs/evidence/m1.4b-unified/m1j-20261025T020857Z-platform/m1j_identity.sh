set -uo pipefail
R=${R:?release name required}
RP=$HOME/Desktop/uniRobotPlatform; MC=$HOME/Desktop/mobileCar
REL=$RP/releases/$R; PL=$REL/backend; V=$RP/var/reports/$R; PY=$RP/envs/gateway-py314/bin/python
mkdir -p "$V"
cd "$PL" || exit 1
UNIROBOT_REPO_ROOT=$REL $PY -m pytest tests/test_release_identity.py tests/test_stop_end.py tests/test_prepare.py tests/test_drafts.py -q 2>&1 | tail -2
echo "=== identity over the m1h assembled release ==="
$PY tools/release_identity.py build --root $MC/releases/m1h-20261024T152235Z-native --spec $PL/config/release-identity.native-m1h.json --platform-root $PL --out $V/release-identity.m1h.json > $V/identity-m1h.log 2>&1; echo "build exit=$?"
tail -c 240 $V/identity-m1h.log; echo
echo "=== same spec over the plain drvfix release (must fail) ==="
$PY tools/release_identity.py build --root $MC/releases/drvfix-20261019T044549Z-0a80415b2577 --spec $PL/config/release-identity.native-m1h.json --platform-root $PL --out $V/release-identity.drvfix.json > $V/identity-drvfix.log 2>&1; echo "build exit=$?"
V=$V $PY - <<'PY'
import json, os
v = os.environ["V"]
a = json.load(open(f"{v}/release-identity.m1h.json")); b = json.load(open(f"{v}/release-identity.drvfix.json"))
print("m1h complete:", a["complete"], "| required:", a["required_count"], "| hashed:", a["hashed_count"])
print("m1h release digest:", a.get("release_digest"))
print("m1h groups (required, hashed, missing):", {k: (x["required"], x["hashed"], len(x["missing"])) for k, x in a["groups"].items()})
print("m1h unlisted under watched roots:", len(a["unlisted_under_watched_roots"]), a["unlisted_under_watched_roots"][:5])
print("drvfix complete:", b["complete"], "| missing count:", len(b["missing_required"]))
print("drvfix missing sample:", sorted({i["path"] for i in b["missing_required"]})[:5])
print("drvfix published a digest?", "release_digest" in b)
PY
