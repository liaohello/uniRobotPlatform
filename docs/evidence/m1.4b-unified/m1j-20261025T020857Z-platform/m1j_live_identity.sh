#!/usr/bin/env bash
# Read-only capture of the live unified candidate identity on the platform server.
# No native write request is made; only GET to the platform itself and local process inspection.
set -uo pipefail
PORT=18959
ROOT=$HOME/Desktop/uniRobotPlatform
REL=$ROOT/releases/m1j-20261025T020857Z-platform
OUT=$ROOT/var/reports/m1j-20261025T020857Z-platform/live-candidate-identity.json

pid=$(ss -ltnp "sport = :$PORT" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1)
if [ -z "$pid" ]; then echo "ABORT: nothing listening on $PORT" >&2; exit 2; fi

cmdline=$(tr '\0' ' ' < "/proc/$pid/cmdline")
cwd=$(readlink "/proc/$pid/cwd")
envline=$(tr '\0' '\n' < "/proc/$pid/environ" | grep -E '^(UNIROBOT|PYTHONPATH)=' | paste -sd';' -)
started=$(ps -o lstart= -p "$pid")
scene=$(curl -s --max-time 5 "http://127.0.0.1:$PORT/api/v1/mobilecar/scene" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("schema_version"))')
maps=$(curl -s --max-time 5 "http://127.0.0.1:$PORT/api/v1/maps" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(len(d.get("maps",d if isinstance(d,list) else [])))')
openapi=$(curl -s --max-time 5 "http://127.0.0.1:$PORT/openapi.json" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["info"]["version"],len(d["paths"]))')
db=$(printf '%s' "$cmdline" | grep -oP '(?<=--draft-db )\S+')
db_exists=$([ -f "$db" ] && echo true || echo false)

python3 - "$pid" "$PORT" "$cmdline" "$cwd" "$envline" "$started" "$scene" "$maps" "$openapi" "$db" "$db_exists" "$REL" > "$OUT" <<'PY'
import json, sys
pid, port, cmdline, cwd, env, started, scene, maps, openapi, db, db_exists, rel = sys.argv[1:13]
print(json.dumps({
  "candidate_release": rel,
  "listen_port": int(port),
  "pid": int(pid),
  "process_started": started.strip(),
  "working_directory": cwd,
  "unirobot_or_pythonpath_env": env,
  "command_line": cmdline.strip(),
  "draft_db_path": db,
  "draft_db_exists": db_exists == "true",
  "read_only_probe_results": {
    "scene_schema_version": scene,
    "map_count": int(maps),
    "openapi": openapi,
  },
  "note": "captured with ss/proc/curl GET only; no native write request, no process restart",
}, ensure_ascii=False, indent=2))
PY
echo "written: $OUT"
cat "$OUT"
