"""Thin federated adapters.

Each source project keeps its own interpreter, MuJoCo version and stepping
loop. The gateway only probes health, presents tasks and, when explicitly
allowed, starts a native command in that project's working directory.
"""

from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request
from typing import Any

from .contracts import (
    AdapterConfig,
    AdapterState,
    AdapterStatus,
    RunSpec,
    TaskDescriptor,
    utc_now,
)
from .settings import ALLOW_LAUNCH, BACKEND_ROOT, PROBE_TIMEOUT_S, REPO_ROOT

_CACHE_TTL_S = 3.0
_LOG_DIR = BACKEND_ROOT / "var" / "runs"


class LaunchError(RuntimeError):
    pass


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class Adapter:
    def __init__(self, config: AdapterConfig) -> None:
        self.config = config
        self.project_root = (REPO_ROOT / config.project_root).resolve()
        self._lock = threading.Lock()
        self._cached: AdapterStatus | None = None
        self._cached_at = 0.0

    @property
    def id(self) -> str:
        return self.config.id

    def _url(self, path: str) -> str | None:
        if not self.config.base_url:
            return None
        return self.config.base_url.rstrip("/") + "/" + path.lstrip("/")

    def console_url(self, path: str | None = None) -> str | None:
        if not self.config.base_url:
            return None
        target = path or self.config.console_path
        return self.config.base_url.rstrip("/") + "/" + target.lstrip("/")

    def probe(self, *, force: bool = False) -> AdapterStatus:
        with self._lock:
            now = time.monotonic()
            if (
                not force
                and self._cached is not None
                and now - self._cached_at < _CACHE_TTL_S
            ):
                return self._cached
            status = self._probe()
            self._cached = status
            self._cached_at = now
            return status

    def _probe(self) -> AdapterStatus:
        url = self._url(self.config.health_path)
        if url is None:
            return AdapterStatus(
                adapter_id=self.id,
                state=AdapterState.NOT_CONFIGURED,
                detail="no base_url configured",
            )
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        token = os.environ.get(self.config.auth_env) if self.config.auth_env else None
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=PROBE_TIMEOUT_S) as response:
                body = response.read(64 * 1024)
                latency = (time.perf_counter() - started) * 1000
                payload: dict[str, Any] = {}
                if body:
                    try:
                        parsed = json.loads(body.decode("utf-8"))
                        if isinstance(parsed, dict):
                            payload = parsed
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        pass
                version = (
                    payload.get("version")
                    or payload.get("interface_profile")
                    or payload.get("contract_version")
                    or payload.get("mode")
                )
                return AdapterStatus(
                    adapter_id=self.id,
                    state=AdapterState.ONLINE,
                    base_url=self.config.base_url,
                    latency_ms=round(latency, 1),
                    version=str(version) if version is not None else None,
                    detail=(
                        payload.get("status")
                        or payload.get("mode")
                        or "health ok"
                    ),
                )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            latency = (time.perf_counter() - started) * 1000
            return AdapterStatus(
                adapter_id=self.id,
                state=AdapterState.OFFLINE,
                base_url=self.config.base_url,
                latency_ms=round(latency, 1),
                detail=str(getattr(exc, "reason", exc))[:200],
            )

    def render_command(self, task: TaskDescriptor, spec: RunSpec, run_id: str) -> str:
        values = _SafeDict(
            seed=spec.seed if spec.seed is not None else 1000,
            run_id=run_id,
            checkpoint="{checkpoint}",
            episodes=1,
        )
        values.update(spec.overrides)
        return task.native_launch.format_map(values)

    def launch_task(
        self,
        task: TaskDescriptor,
        spec: RunSpec,
        run_id: str,
        command: str,
    ) -> subprocess.Popen[str]:
        if not ALLOW_LAUNCH:
            raise LaunchError(
                "launch disabled; set UNIROBOT_ALLOW_LAUNCH=1 on the runtime host"
            )
        if "{" in command:
            raise LaunchError(
                f"unresolved placeholder in native command: {command}"
            )
        argv = shlex.split(command, posix=os.name != "nt")
        if not argv:
            raise LaunchError("empty native command")
        env = os.environ.copy()
        if self.config.launch:
            env.update(self.config.launch.env)
        env.setdefault("PYTHONPATH", str(self.project_root / "src"))
        if (self.project_root / "src").is_dir():
            env["PYTHONPATH"] = os.pathsep.join(
                [str(self.project_root / "src"), env.get("PYTHONPATH", "")]
            ).strip(os.pathsep)
        else:
            env["PYTHONPATH"] = os.pathsep.join(
                [str(self.project_root), env.get("PYTHONPATH", "")]
            ).strip(os.pathsep)

        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = _LOG_DIR / f"{run_id}.log"
        log = log_path.open("a", encoding="utf-8")
        log.write(f"# {utc_now()} {task.id}\n# cwd={self.project_root}\n# {command}\n")
        log.flush()
        kwargs: dict[str, Any] = {
            "cwd": str(self.project_root),
            "env": env,
            "stdout": log,
            "stderr": subprocess.STDOUT,
            "text": True,
        }
        if os.name == "posix":
            kwargs["start_new_session"] = True
        else:  # pragma: no cover - Windows runtime host
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        return subprocess.Popen(argv, **kwargs)

    def stop_process(self, process: subprocess.Popen[str], timeout_s: float = 5.0) -> None:
        if process.poll() is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGTERM)
            else:  # pragma: no cover
                process.terminate()
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            try:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:  # pragma: no cover
                    process.kill()
            except ProcessLookupError:
                pass


def build_adapters(configs: list[AdapterConfig]) -> dict[str, Adapter]:
    return {config.id: Adapter(config) for config in configs}
