#!/usr/bin/env bash
# Start the unified candidate as a persistent loopback service for frontend integration.
# Idempotent guard: refuses to start when the port is taken, so this never replaces another instance.
# Real native access stays GET-only: the launcher writes no command to 8792.
set -euo pipefail
ROOT=$HOME/Desktop/uniRobotPlatform
REL=$ROOT/releases/m1j-20261025T020857Z-platform
GEOM=$ROOT/releases/m1-geometry-20261023T192202Z-cdfc7472e5de/geometry
MAPS=$HOME/Desktop/mobileCar/var/maps
PY=$ROOT/envs/gateway-py314/bin/python
REPORT=$ROOT/var/reports/m1j-20261025T020857Z-platform
TS=$(date -u +%H%M%S)
PORT=18959

[ -z "$(ss -ltnH "sport = :$PORT" 2>/dev/null)" ] || { echo "ABORT: $PORT busy (candidate already live; do not replace it)" >&2; exit 3; }
mkdir -p "$REPORT"
cd "$REL/backend"
PYTHONPATH=$REL/backend/src setsid "$PY" tools/launch_unified_gateway.py --port $PORT \
  --native-url http://127.0.0.1:8792 \
  --geometry-bundle "$GEOM" \
  --map-catalog "$REL/backend/config/maps.catalog.json" \
  --maps-root "$MAPS" \
  --draft-db "$REL/report/unified-live-$TS.sqlite3" \
  --out-manifest "$REPORT/unified-startup-live.json" > "$REPORT/unified-gateway-live.log" 2>&1 < /dev/null &
sleep 6
ss -ltnp "sport = :$PORT" 2>/dev/null
PYTHONPATH=$REL/backend/src "$PY" tools/unified_candidate_check.py --platform-url "http://127.0.0.1:$PORT" \
  --native-url http://127.0.0.1:8792 --bundle-dir "$GEOM" \
  --startup-manifest "$REPORT/unified-startup-live.json" \
  --out "$REPORT/unified-candidate-check-live.json"
