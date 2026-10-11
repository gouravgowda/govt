import os

# ensure the disabled path: no key file in repo, no inline key
os.environ.pop("FIREBASE_KEY_JSON", None)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from app import firebase_auth as fb
from app.main import app

c = TestClient(app)


def test_disabled_without_key():
    assert not Path("firebase-key.json").exists()
    assert not Path("/etc/secrets/firebase-key.json").exists()
    assert fb.enabled() is False
    st = fb.status()
    assert st["firebase"] is False and st.get("reason")
    with pytest.raises(ValueError):
        fb.verify_token("anything")


def test_auth_config_public_and_reports_local():
    r = c.get("/auth/config")
    assert r.status_code == 200
    body = r.json()
    assert body["firebase"] is False and body["config"] is None


def test_local_flow_unaffected():
    tok = c.post("/auth/signup", json={"name": "Fb", "email": "fb@example.com",
                                       "password": "secret123"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert c.get("/auth/me", headers=h).status_code == 200
    # history endpoints work on the sqlite backend
    assert c.get("/history", headers=h).json()["backend"] == "sqlite"
    assert c.get("/history/9999", headers=h).status_code == 404


def test_web_config_shape():
    cfg = fb.FIREBASE_WEB_CONFIG
    assert cfg["projectId"] == "govt-11bb5"
    for k in ("apiKey", "authDomain", "storageBucket", "messagingSenderId", "appId"):
        assert cfg[k], k
