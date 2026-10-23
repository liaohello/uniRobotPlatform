"""Persistent fixed-preset experiment drafts; no native write operations."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import Field, StrictInt, StrictStr

from .contracts import Contract, utc_now
from .mobilecar import MobileCarIntegration


class DraftMetadata(Contract):
    name: StrictStr = Field(default="LanderPi 人工遥操作", min_length=1, max_length=200)
    description: StrictStr = Field(default="", max_length=4000)


class CreateDraft(DraftMetadata):
    preset_id: Literal["mobilecar.g1.teleop"] = "mobilecar.g1.teleop"


class SaveDraft(DraftMetadata):
    base_revision: StrictInt = Field(ge=1)


class ValidateDraft(Contract):
    execution_revision: StrictInt = Field(ge=1)
    fingerprint: StrictStr = Field(pattern=r"^[0-9a-f]{64}$")


class CreateSession(ValidateDraft):
    validated_snapshot_id: StrictStr = Field(min_length=1)
    idempotency_key: StrictStr = Field(min_length=1)


class DraftNotFound(KeyError):
    pass


class DraftConflict(ValueError):
    pass


class DraftStore:
    def __init__(self, path: Path, integration: MobileCarIntegration) -> None:
        self.path = path
        self.integration = integration
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, revision INTEGER NOT NULL, document TEXT NOT NULL)")

    def _execution(self) -> dict:
        pin = self.integration.pin
        return {key: pin[key] for key in ("preset_id", "native_commit", "manifest_sha256", "recipe", "expected")}

    def _fingerprint(self) -> str:
        content = json.dumps(self._execution(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode()).hexdigest()

    def _load(self, db: sqlite3.Connection, draft_id: str) -> dict:
        row = db.execute("SELECT document FROM drafts WHERE id=?", (draft_id,)).fetchone()
        if row is None:
            raise DraftNotFound(draft_id)
        draft = json.loads(row[0])
        if draft["fingerprint"] != self._fingerprint() and draft["validation"]["status"] != "stale":
            draft["validation"]["status"] = "stale"
            draft["validation"]["reason"] = "Fixed preset dependencies changed; create a new draft to adopt the new preset"
            db.execute("UPDATE drafts SET document=? WHERE id=?", (json.dumps(draft), draft_id))
        return draft

    def create(self, request: CreateDraft) -> dict:
        draft = {
            "draft_id": "draft-" + uuid4().hex,
            "draft_revision": 1,
            "execution_revision": 1,
            "fingerprint": self._fingerprint(),
            "preset": self._execution(),
            "name": request.name,
            "description": request.description,
            "validation": {"status": "unvalidated", "result": None},
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO drafts VALUES (?, ?, ?)", (draft["draft_id"], 1, json.dumps(draft)))
        return draft

    def get(self, draft_id: str) -> dict:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            return self._load(db, draft_id)

    def list(self) -> list[dict]:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            ids = [row[0] for row in db.execute("SELECT id FROM drafts ORDER BY rowid DESC")]
            return [self._load(db, draft_id) for draft_id in ids]

    def save(self, draft_id: str, request: SaveDraft) -> dict:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            draft = self._load(db, draft_id)
            if draft["draft_revision"] != request.base_revision:
                raise DraftConflict("Draft changed in another host; reload before saving")
            if draft["name"] == request.name and draft["description"] == request.description:
                return draft
            draft.update(name=request.name, description=request.description,
                         draft_revision=draft["draft_revision"] + 1, updated_at=utc_now())
            # Metadata is excluded from executionRevision/fingerprint and does
            # not invalidate an otherwise applicable execution check result.
            db.execute("UPDATE drafts SET revision=?, document=? WHERE id=?",
                       (draft["draft_revision"], json.dumps(draft), draft_id))
            return draft

    def validate(self, draft_id: str, request: ValidateDraft) -> dict:
        before = self.get(draft_id)
        self._check_execution(before, request)
        preflight = self.integration.check()  # Four GETs only; no Session creation.
        result = {"validation_id": "validation-" + uuid4().hex,
                  "execution_revision": request.execution_revision,
                  "fingerprint": request.fingerprint,
                  "checked_at": preflight["checked_at"],
                  "status": "failed", "checks": preflight["checks"],
                  "validated_snapshot_id": None}
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            current = self._load(db, draft_id)
            # Load again after network I/O so metadata saves are preserved and
            # a response for old execution dependencies cannot revive a check.
            self._check_execution(current, request)
            current["validation"] = {"status": "failed", "result": result}
            db.execute("UPDATE drafts SET document=? WHERE id=?", (json.dumps(current), draft_id))
            return current

    @staticmethod
    def _check_execution(draft: dict, request: ValidateDraft) -> None:
        if (draft["execution_revision"] != request.execution_revision
                or draft["fingerprint"] != request.fingerprint
                or draft["validation"]["status"] == "stale"):
            raise DraftConflict("Execution revision or preset dependencies are stale")
