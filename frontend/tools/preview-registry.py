"""Preview process ownership: register, verify, and stop only what this project started.

Why this exists: an earlier round cleaned scratch previews with a port-name regex and killed two
delivered previews. A port number alone is not ownership. Every stop therefore re-reads the live
process identity — full /proc/<pid>/cmdline, the kernel start tick, the uid, and the exact listener
on the recorded port — and refuses unless all of them match the entry this tool registered.

Nothing here starts a backend, a native instance, or any service other than the recorded frontend
preview, and it never signals a process that is not in the registry.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ('pid', 'port', 'release_id', 'upstream', 'directory', 'cmdline', 'start_ticks', 'uid', 'log_path', 'round')


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_cmdline(pid: int) -> list[str]:
    raw = Path(f'/proc/{pid}/cmdline').read_bytes()
    return [part.decode('utf-8', 'replace') for part in raw.split(b'\0') if part]


def read_start_ticks(pid: int) -> int:
    """Field 22 of /proc/<pid>/stat, immune to the comm field containing spaces or brackets."""
    text = Path(f'/proc/{pid}/stat').read_text()
    after = text.rsplit(')', 1)[1].split()
    return int(after[19])


def process_identity(pid: int) -> dict:
    return {
        'alive': Path(f'/proc/{pid}').is_dir(),
        'cmdline': read_cmdline(pid) if Path(f'/proc/{pid}/cmdline').exists() else [],
        'start_ticks': read_start_ticks(pid) if Path(f'/proc/{pid}/stat').exists() else None,
        'uid': (Path(f'/proc/{pid}').stat().st_uid if Path(f'/proc/{pid}').exists() else None),
    }


def port_owner(pid: int, port: int) -> bool:
    """True when /proc/<pid>/net/tcp lists a listening socket on that exact port."""
    try:
        lines = Path(f'/proc/{pid}/net/tcp').read_text().splitlines()[1:]
    except OSError:
        return False
    suffix = f':{port:04X}'
    for line in lines:
        columns = line.split()
        if len(columns) > 3 and columns[1].upper().endswith(suffix) and columns[3] == '0A':
            return True
    return False


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    value = json.loads(path.read_text() or '[]')
    if not isinstance(value, list):
        raise SystemExit(f'registry is not a list: {path}')
    return value


def save(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + '\n')


def check(entry: dict) -> dict:
    pid = int(entry['pid'])
    live = process_identity(pid)
    reasons = []
    if not live['alive']:
        reasons.append('pid is not running')
    else:
        if live['cmdline'] != entry['cmdline']:
            reasons.append('cmdline differs from the registered command')
        if live['start_ticks'] != entry['start_ticks']:
            reasons.append('process start tick differs (pid was reused)')
        if live['uid'] != entry['uid']:
            reasons.append('process uid differs')
        if not port_owner(pid, int(entry['port'])):
            reasons.append(f'pid does not own the listening port {entry["port"]}')
    return {'pid': pid, 'port': entry['port'], 'release_id': entry.get('release_id'), 'upstream': entry.get('upstream'),
            'round': entry.get('round'), 'owned': not reasons, 'reasons': reasons, 'live': live, 'checked_at_utc': now()}


def cmd_register(args) -> int:
    preview = json.loads(Path(args.preview_json).read_text())
    pid = int(preview['pid'])
    live = process_identity(pid)
    if not live['alive']:
        raise SystemExit(f'refusing to register pid {pid}: not running')
    entry = {
        'pid': pid, 'port': int(preview['port']), 'release_id': preview['release_id'], 'upstream': preview['upstream'],
        'directory': preview['directory'], 'cmdline': preview.get('command', live['cmdline']),
        'start_ticks': live['start_ticks'], 'uid': live['uid'],
        'log_path': str(Path(args.preview_json).parent / 'preview.log'),
        'round': args.round, 'started_at_utc': preview.get('started_at_utc'), 'registered_at_utc': now(),
        'status': 'running', 'stopped_at_utc': None, 'stop_reason': None,
    }
    missing = [field for field in FIELDS if entry.get(field) in (None, '', [])]
    if missing:
        raise SystemExit(f'refusing to register without identity fields: {missing}')
    entries = load(args.registry)
    entries = [item for item in entries if not (item['pid'] == pid)]
    entries.append(entry)
    save(args.registry, entries)
    print(json.dumps({'registered': entry, 'registry': str(args.registry)}, ensure_ascii=False))
    return 0


def cmd_verify(args) -> int:
    entries = load(args.registry)
    rows = [check(entry) for entry in entries]
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    return 0 if all(row['owned'] for row in rows) else 1


def cmd_stop(args) -> int:
    entries = load(args.registry)
    targets = [entry for entry in entries if int(entry['pid']) == args.pid]
    if args.require_running:
        targets = [entry for entry in targets if entry.get('status') == 'running']
    if len(targets) != 1:
        raise SystemExit(f'exactly one registry entry must match pid {args.pid}; found {len(targets)}')
    entry = targets[0]
    verdict = check(entry)
    if args.round and entry.get('round') != args.round:
        raise SystemExit(f'refusing: entry round={entry.get("round")} is not the requested round={args.round}')
    if not verdict['owned']:
        raise SystemExit(f'refusing to stop pid {entry["pid"]}: {verdict["reasons"]}')
    os.kill(entry['pid'], signal.SIGTERM)
    deadline = time.time() + args.timeout
    while time.time() < deadline and Path(f'/proc/{entry["pid"]}').is_dir():
        time.sleep(0.2)
    alive = Path(f'/proc/{entry["pid"]}').is_dir()
    if alive:
        os.kill(entry['pid'], signal.SIGKILL)
    entry['status'] = 'stopped'
    entry['stopped_at_utc'] = now()
    entry['stop_reason'] = 'sigterm' if not alive else 'sigkill after timeout'
    save(args.registry, entries)
    print(json.dumps({'stopped_pid': entry['pid'], 'port': entry['port'], 'verified_identity': verdict['reasons'] or ['match'],
                      'needed_sigkill': alive, 'registry': str(args.registry)}, ensure_ascii=False))
    return 0


def cmd_free_port(args) -> int:
    """Report only. This never stops anything: it lists ports that are neither listening nor claimed."""
    entries = load(args.registry)
    claimed = {int(entry['port']) for entry in entries if entry.get('status') == 'running'}
    report = []
    for port in range(args.start, args.stop + 1):
        listening = False
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', port))
            except OSError:
                listening = True
        report.append({'port': port, 'bindable': not listening, 'claimed_by_registry': port in claimed,
                       'free_for_this_round': not listening and port not in claimed})
    print(json.dumps({'range': [args.start, args.stop], 'ports': report, 'registry': str(args.registry)}, indent=1))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--registry', type=Path, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    register = sub.add_parser('register')
    register.add_argument('--preview-json', type=Path, required=True)
    register.add_argument('--round', required=True)
    register.set_defaults(handler=cmd_register)
    verify = sub.add_parser('verify')
    verify.set_defaults(handler=cmd_verify)
    stop = sub.add_parser('stop')
    stop.add_argument('--pid', type=int, required=True)
    stop.add_argument('--round')
    stop.add_argument('--timeout', type=float, default=5.0)
    stop.add_argument('--allow-stopped', dest='require_running', action='store_false')
    stop.set_defaults(handler=cmd_stop)
    free = sub.add_parser('free-port')
    free.add_argument('--start', type=int, required=True)
    free.add_argument('--stop', type=int, required=True)
    free.set_defaults(handler=cmd_free_port)
    args = parser.parse_args()
    return args.handler(args)


if __name__ == '__main__':
    sys.exit(main())
