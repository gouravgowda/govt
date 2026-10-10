import os
import tempfile

db = os.path.join(tempfile.mkdtemp(), "test_users.db")
os.environ["AUTH_DB_PATH"] = db

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)


def signup_token():
    r = c.post("/auth/signup", json={"name": "Test User", "email": "test@example.com", "password": "secret123"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_signup_and_me():
    tok = signup_token()
    r = c.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200 and r.json()["email"] == "test@example.com"


def test_duplicate_signup_rejected():
    r = c.post("/auth/signup", json={"name": "Dup", "email": "dup@example.com", "password": "secret123"})
    assert r.status_code == 200
    r2 = c.post("/auth/signup", json={"name": "Dup", "email": "dup@example.com", "password": "secret123"})
    assert r2.status_code == 409


def test_login_wrong_password():
    c.post("/auth/signup", json={"name": "W", "email": "w@example.com", "password": "secret123"})
    r = c.post("/auth/login", json={"email": "w@example.com", "password": "nope"})
    assert r.status_code == 401
    r2 = c.post("/auth/login", json={"email": "w@example.com", "password": "secret123"})
    assert r2.status_code == 200 and "token" in r2.json()


def test_sessions_require_auth():
    r = c.post("/sessions")
    assert r.status_code == 401


def test_full_chat_with_auth():
    tok = signup_token() if False else c.post(
        "/auth/signup", json={"name": "Chat", "email": "chat@example.com", "password": "secret123"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    sid = c.post("/sessions", headers=h).json()["session_id"]
    for a in ["planning to start a business", "24", "3 lakhs", "not registered yet",
              "manufacturing", "Karnataka", "2 lakh per year", "Female"]:
        r = c.post(f"/sessions/{sid}/messages", headers=h, json={"message": a}).json()
        if r.get("done"):
            break
    assert r.get("done") is True
    assert len(r["results"]["eligible"]) >= 1


def test_cross_user_session_forbidden():
    t1 = c.post("/auth/signup", json={"name": "A", "email": "a@example.com", "password": "secret123"}).json()["token"]
    t2 = c.post("/auth/signup", json={"name": "B", "email": "b@example.com", "password": "secret123"}).json()["token"]
    sid = c.post("/sessions", headers={"Authorization": f"Bearer {t1}"}).json()["session_id"]
    r = c.get(f"/sessions/{sid}/results", headers={"Authorization": f"Bearer {t2}"})
    assert r.status_code == 403


def test_logout_invalidates():
    tok = c.post("/auth/signup", json={"name": "L", "email": "l@example.com", "password": "secret123"}).json()["token"]
    assert c.post("/auth/logout", headers={"Authorization": f"Bearer {tok}"}).status_code == 200
    assert c.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_patch_profile_validates_values():
    tok = c.post("/auth/signup", json={"name": "P", "email": "p@example.com", "password": "secret123"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    sid = c.post("/sessions", headers=h).json()["session_id"]
    bad = c.patch(f"/sessions/{sid}/profile", headers=h, json={"field": "age", "value": "banana"})
    assert bad.status_code == 422
    bad2 = c.patch(f"/sessions/{sid}/profile", headers=h, json={"field": "gender", "value": "<img src=x>"})
    assert bad2.status_code == 422
    ok = c.patch(f"/sessions/{sid}/profile", headers=h, json={"field": "age", "value": 30})
    assert ok.status_code == 200 and ok.json()["profile"]["age"] == 30


def test_retry_reply_not_duplicated():
    tok = c.post("/auth/signup", json={"name": "R", "email": "r@example.com", "password": "secret123"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    sid = c.post("/sessions", headers=h).json()["session_id"]
    r1 = c.post(f"/sessions/{sid}/messages", headers=h, json={"message": "student"}).json()
    assert r1["field"] == "age"
    r2 = c.post(f"/sessions/{sid}/messages", headers=h, json={"message": "banana"}).json()
    assert r2["reply"] == "I didn't catch that."
    assert r2["question"] and r2["question"] != r2["reply"]
