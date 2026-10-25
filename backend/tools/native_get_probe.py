"""The only native/history probe entry allowed in this project's verification tools.

It issues GET requests and nothing else: there is no method, body or data parameter to
pass, so a verification run cannot accidentally become a write probe. Every request is
appended to a JSONL log so the delivered read-only execution record is auditable.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

METHOD = "GET"
TIMEOUT_S = 20.0


class NonGetRequest(RuntimeError):
    """Unreachable by construction; kept so the invariant is explicit and testable."""


class GetProbe:
    def __init__(self, log_path: Path | None = None) -> None:
        self.log_path = log_path
        self.entries: list[dict[str, Any]] = []
        if log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("", encoding="utf-8")

    def get(self, url: str, *, binary: bool = False) -> tuple[int, bytes, dict[str, str]]:
        if not url.lower().startswith(("http://", "https://")):
            raise ValueError(f"refusing non-http url: {url}")
        request = urllib.request.Request(url, method=METHOD)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                status, body, headers = response.status, response.read(), dict(response.headers)
        except urllib.error.HTTPError as exc:
            status, body, headers = exc.code, exc.read(), dict(exc.headers)
        self._record(url, status, len(body), binary)
        return status, body, headers

    def json(self, url: str) -> tuple[int, Any]:
        status, body, _ = self.get(url)
        try:
            return status, json.loads(body)
        except json.JSONDecodeError:
            return status, body.decode("utf-8", "replace")

    def _record(self, url: str, status: int, size: int, binary: bool) -> None:
        entry = {"method": METHOD, "url": url, "status": status, "bytes": size, "binary": binary}
        self.entries.append(entry)
        if self.log_path is not None:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")

    def summary(self) -> dict[str, Any]:
        methods = sorted({item["method"] for item in self.entries})
        return {"requests": len(self.entries), "methods": methods, "non_get": [item for item in self.entries
                                                                               if item["method"] != METHOD]}

    def write_summary(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"probe": "native_get_probe", "only_method": METHOD, **self.summary(),
                                    "requests": self.entries}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
