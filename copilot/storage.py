from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "copilot_history.sqlite3"


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            kind TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    con.commit()
    return con


def save_snapshot(kind: str, payload: dict[str, Any]) -> int:
    con = _connect()
    cur = con.execute(
        "INSERT INTO snapshots (created_at, kind, payload) VALUES (?, ?, ?)",
        (datetime.now(UTC).isoformat(), kind, json.dumps(payload, default=str)),
    )
    con.commit()
    row_id = int(cur.lastrowid)
    con.close()
    return row_id


def latest_snapshots(kind: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
    con = _connect()
    if kind:
        rows = con.execute(
            "SELECT id, created_at, kind, payload FROM snapshots WHERE kind=? ORDER BY id DESC LIMIT ?",
            (kind, limit),
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT id, created_at, kind, payload FROM snapshots ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    con.close()
    return [
        {"id": row[0], "created_at": row[1], "kind": row[2], "payload": json.loads(row[3])}
        for row in rows
    ]
