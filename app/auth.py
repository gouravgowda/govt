"""Local auth: signup/login with SQLite user store, PBKDF2 password hashing, bearer tokens.

No external dependencies — stdlib only (sqlite3, hashlib, secrets).
DB file defaults to <repo-root>/users.db, overridable via AUTH_DB_PATH.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from pathlib import Path

TOKEN_TTL = int(os.getenv("AUTH_TOKEN_TTL", str(30 * 24 * 3600)))


def db_path() -> Path:
    env = os.getenv("AUTH_DB_PATH", "users.db")
    p = Path(env)
    if not p.is_absolute():
        root = Path(__file__).resolve().parent.parent
        p = root / env
    return p


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(db_path()))
    c.execute(
        "CREATE TABLE IF NOT EXISTS users("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, "
        "email TEXT NOT NULL UNIQUE, salt TEXT NOT NULL, pwdhash TEXT NOT NULL, "
        "created REAL NOT NULL)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS tokens("
        "token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created REAL NOT NULL)"
    )
    return c


def _hash(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt.hex(), h.hex()


def create_user(name: str, email: str, password: str) -> dict:
    email = email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Enter a valid email address.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if not name.strip():
        raise ValueError("Enter your name.")
    salt, h = _hash(password)
    c = _conn()
    try:
        cur = c.execute(
            "INSERT INTO users(name, email, salt, pwdhash, created) VALUES(?,?,?,?,?)",
            (name.strip(), email, salt, h, time.time()),
        )
        c.commit()
        uid = cur.lastrowid
    except sqlite3.IntegrityError:
        c.close()
        raise ValueError("An account with this email already exists. Try logging in.")
    c.close()
    return {"id": uid, "name": name.strip(), "email": email}


def verify_user(email: str, password: str) -> dict | None:
    c = _conn()
    row = c.execute("SELECT id, name, email, salt, pwdhash FROM users WHERE email=?",
                    (email.strip().lower(),)).fetchone()
    c.close()
    if not row:
        return None
    _, _, _, salt, stored = row
    if not hmac.compare_digest(_hash(password, salt)[1], stored):
        return None
    return {"id": row[0], "name": row[1], "email": row[2]}


def issue_token(user_id: int) -> str:
    tok = secrets.token_urlsafe(32)
    c = _conn()
    c.execute("DELETE FROM tokens WHERE created < ?", (time.time() - TOKEN_TTL,))
    c.execute("INSERT INTO tokens(token, user_id, created) VALUES(?,?,?)",
              (tok, user_id, time.time()))
    c.commit()
    c.close()
    return tok


def user_for_token(token: str) -> dict | None:
    if not token:
        return None
    c = _conn()
    row = c.execute(
        "SELECT u.id, u.name, u.email, t.created FROM tokens t JOIN users u ON u.id=t.user_id "
        "WHERE t.token=?", (token,)).fetchone()
    c.close()
    if not row or time.time() - row[3] > TOKEN_TTL:
        return None
    return {"id": row[0], "name": row[1], "email": row[2]}


def revoke_token(token: str) -> None:
    c = _conn()
    c.execute("DELETE FROM tokens WHERE token=?", (token,))
    c.commit()
    c.close()
