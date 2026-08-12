"""Reads back the backend's own log file (see app/core/logging.py) so
errors/activity are visible from the dashboard without shell access."""

from __future__ import annotations

import json
from collections import deque

from fastapi import APIRouter, Query

from app.core.logging import LOG_FILE

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/tail")
async def tail_logs(lines: int = Query(200, ge=1, le=2000), level: str | None = None) -> list[dict]:
    if not LOG_FILE.exists():
        return []

    with LOG_FILE.open(encoding="utf-8", errors="replace") as f:
        recent = deque(f, maxlen=lines * 3 if level else lines)  # overscan a bit when filtering

    entries = []
    for raw_line in recent:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError:
            entry = {"level": "info", "event": raw_line, "timestamp": None}
        if level and entry.get("level", "").lower() != level.lower():
            continue
        entries.append(entry)

    return entries[-lines:]
