"""Firebase backend (Auth token verification + Firestore users/history).

Primary when a service-account key is available, silent fallback to the local
SQLite store otherwise — so localhost, tests, and offline demos keep working
with zero config. Key search order:
  1. /etc/secrets/firebase-key.json  (Render Secret Files mount)
  2. ./firebase-key.json             (local dev copy — git-ignored, never commit)
  3. FIREBASE_KEY_JSON env var       (inline JSON, last resort)

Firestore layout:
  users/{uid}                  {name, email, createdAt, lastSeenAt}
  users/{uid}/history/{auto}   {created, profile, results}
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

FIREBASE_WEB_CONFIG = {
    "apiKey": "AIzaSyCUhNiQkOd6KxhhNakieZRDhHOKLOjOEEU",
    "authDomain": "govt-11bb5.firebaseapp.com",
    "projectId": "govt-11bb5",
    "storageBucket": "govt-11bb5.firebasestorage.app",
    "messagingSenderId": "567957734207",
    "appId": "1:567957734207:web:134c93b13fc5b7ac75898a",
}

_db = None
_auth = None
_init_error = ""


def _find_key() -> Optional[Path | str]:
    for cand in ("/etc/secrets/firebase-key.json", "firebase-key.json"):
        p = Path(cand)
        if p.is_file():
            return p
    inline = os.getenv("FIREBASE_KEY_JSON", "").strip()
    return inline or None


def init_firebase() -> bool:
    """Initialize once. Returns True when Firebase is usable."""
    global _db, _auth, _init_error
    if _db is not None:
        return True
    try:
        import firebase_admin  # type: ignore
        from firebase_admin import auth as _fauth, credentials, firestore  # type: ignore
    except ImportError as e:
        _init_error = f"firebase-admin not installed: {e}"
        return False
    key = _find_key()
    if not key:
        _init_error = "no service-account key found (secret file, firebase-key.json, or FIREBASE_KEY_JSON)"
        return False
    try:
        if isinstance(key, Path):
            cred = credentials.Certificate(str(key))
        else:
            cred = credentials.Certificate(json.loads(key))
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(cred)
        _auth = _fauth
        _db = firestore.client()
        return True
    except Exception as e:
        _init_error = f"init failed: {e}"
        _db, _auth = None, None
        return False


def enabled() -> bool:
    return init_firebase()


def status() -> Dict[str, Any]:
    ok = init_firebase()
    return {"firebase": ok, **({} if ok else {"reason": _init_error})}


def verify_token(token: str) -> Dict[str, Any]:
    """Verify a Firebase ID token. Raises ValueError when invalid/unavailable."""
    if not init_firebase():
        raise ValueError("firebase backend not configured")
    try:
        d = _auth.verify_id_token(token)
    except Exception as e:
        raise ValueError(f"bad firebase token: {e}")
    return {"id": d["uid"], "email": d.get("email", ""), "name": d.get("name", "")}


_user_cache: Dict[str, float] = {}


def ensure_user(uid: str, email: str = "", name: str = "") -> None:
    """Create/update users/{uid} (cached 10 min to avoid a read per request)."""
    if not init_firebase():
        return
    if _user_cache.get(uid, 0) > time.time() - 600:
        return
    ref = _db.collection("users").document(uid)
    snap = ref.get()
    now = time.time()
    if snap.exists:
        ref.update({"lastSeenAt": now, **({"email": email} if email else {}),
                    **({"name": name} if name else {})})
    else:
        ref.set({"email": email, "name": name or (email.split("@")[0] if email else "there"),
                 "createdAt": now, "lastSeenAt": now})
    _user_cache[uid] = now


def save_history(uid: str, profile: dict, results: dict) -> str:
    doc = _db.collection("users").document(uid).collection("history").document()
    doc.set({"created": time.time(), "profile": profile, "results": results})
    return doc.id


def list_history(uid: str, limit: int = 20) -> List[dict]:
    q = (_db.collection("users").document(uid).collection("history")
         .order_by("created", direction="DESCENDING").limit(limit).stream())
    out = []
    for d in q:
        r = d.to_dict().get("results", {}) if d.to_dict() else {}
        out.append({"id": d.id, "created": d.to_dict().get("created", 0),
                    "n_eligible": len(r.get("eligible", [])),
                    "n_near": len(r.get("near_miss", [])),
                    "n_poss": len(r.get("possibly_eligible", []))})
    return out


def get_history(uid: str, hid: str) -> Optional[dict]:
    d = _db.collection("users").document(uid).collection("history").document(str(hid)).get()
    if not d.exists:
        return None
    return (d.to_dict() or {}).get("results")
