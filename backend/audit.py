"""Append-only writer for output/audit_trail.json.

The file is one JSON array. We never truncate or rewrite history: each call
re-reads the array under a file lock, appends, and swaps the file in atomically.
If the existing file cannot be parsed we raise instead of overwriting it.
"""
from __future__ import annotations

import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .models import AuditEntry

ROOT = Path(__file__).resolve().parent.parent
MAX_TEXT = 6000


def audit_path() -> Path:
    return Path(os.environ.get("AUDIT_TRAIL_PATH", ROOT / "output" / "audit_trail.json"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def clip(value, limit: int = MAX_TEXT):
    """Truncate long strings (recursively) so the audit file stays readable and small."""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + f"...[truncated {len(value) - limit} chars]"
    if isinstance(value, dict):
        return {k: clip(v, limit) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clip(v, limit) for v in value]
    return value


def append_entry(entry: AuditEntry) -> None:
    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists() and path.stat().st_size > 0:
            try:
                rows = json.loads(path.read_text())
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{path} is not valid JSON; refusing to overwrite it") from exc
            if not isinstance(rows, list):
                raise RuntimeError(f"{path} must contain a JSON array")
        else:
            rows = []
        rows.append(json.loads(entry.model_dump_json()))
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
