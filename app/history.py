"""Persisted results history (SQLite, same file as the auth store)."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path


def _db_path() -> Path:
    env = os.getenv("AUTH_DB_PATH", "users.db")
    p = Path(env)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent / env
    return p


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_db_path()))
    c.execute(
        "CREATE TABLE IF NOT EXISTS history("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
        "created REAL NOT NULL, profile TEXT NOT NULL, results TEXT NOT NULL)"
    )
    return c


def save(user_id: int, profile: dict, results: dict) -> int:
    c = _conn()
    cur = c.execute(
        "INSERT INTO history(user_id, created, profile, results) VALUES(?,?,?,?)",
        (user_id, time.time(), json.dumps(profile), json.dumps(results)),
    )
    c.commit()
    hid = cur.lastrowid
    c.close()
    return hid


def list_for(user_id: int, limit: int = 20) -> list[dict]:
    c = _conn()
    rows = c.execute(
        "SELECT id, created, results FROM history WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    c.close()
    out = []
    for hid, created, results in rows:
        r = json.loads(results)
        out.append({"id": hid, "created": created,
                    "n_eligible": len(r.get("eligible", [])),
                    "n_near": len(r.get("near_miss", [])),
                    "n_poss": len(r.get("possibly_eligible", []))})
    return out


def get(user_id: int, hid: int) -> dict | None:
    c = _conn()
    row = c.execute("SELECT results FROM history WHERE id=? AND user_id=?",
                    (hid, user_id)).fetchone()
    c.close()
    return json.loads(row[0]) if row else None
