set -uo pipefail
R=${R:?}; RP=$HOME/Desktop/uniRobotPlatform; MC=$HOME/Desktop/mobileCar
REL=$RP/releases/$R; PL=$REL/backend; V=$RP/var/reports/$R; PY=$RP/envs/gateway-py314/bin/python
BUNDLE=$RP/releases/m1-geometry-20261023T192202Z-cdfc7472e5de/geometry
TS=$(date -u +%H%M%S); UDB=$REL/report/unified-$TS.sqlite3; mkdir -p $V $REL/report
[ -z "$(ss -ltnH sport = :18959 2>/dev/null)" ] || { echo "ABORT: 18959 busy"; exit 3; }
cd $PL || exit 1
PYTHONPATH=$PL/src UNIROBOT_REPO_ROOT=$REL nohup $PY tools/launch_unified_gateway.py --port 18959 \
  --native-url http://127.0.0.1:8792 --geometry-bundle $BUNDLE --map-catalog $PL/config/maps.catalog.json \
  --maps-root $MC/var/maps --draft-db $UDB --out-manifest $V/unified-startup.json </dev/null > $V/unified-gateway.log 2>&1 &
sleep 12
PYTHONPATH=$PL/src $PY tools/unified_candidate_check.py --platform-url http://127.0.0.1:18959 --native-url http://127.0.0.1:8792 \
  --bundle-dir $BUNDLE --startup-manifest $V/unified-startup.json --out $V/unified-candidate-check.json > $V/unified-check.log 2>&1
echo "unified check exit=$?"; tail -4 $V/unified-check.log
pid=$(ss -ltnp sport = :18959 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1); [ -n "$pid" ] && kill $pid 2>/dev/null; sleep 2
[ -z "$(ss -ltnH sport = :18959 2>/dev/null)" ] && echo "18959 released"
$PY - <<'PY'
import json,os,glob
v=os.environ.get("V")
PY
true
