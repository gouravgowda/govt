import os
import tempfile

os.environ.setdefault("AUTH_DB_PATH", os.path.join(tempfile.mkdtemp(), "test_compare.db"))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.compare import build_comparison, fmt_inr
from app.engine import evaluate_all
from app.schemes import load_schemes

c = TestClient(app)
SCHEMES = load_schemes()


def auth():
    tok = c.post("/auth/signup", json={"name": "Cp", "email": f"cp{auth.n}@e.com",
                                       "password": "secret123"}).json()["token"]
    auth.n += 1
    return {"Authorization": f"Bearer {tok}"}
auth.n = 0


def test_fmt_inr():
    assert fmt_inr(10000000) == "₹1 Cr"
    assert fmt_inr(500000) == "₹5 L"
    assert fmt_inr(50000) == "₹50k"
    assert fmt_inr(0) == "—"


def test_build_comparison_unit():
    prof = {"age": 24, "occupation_stage": "aspiring entrepreneur", "sector": "manufacturing",
            "funding_need": "50k to 5 lakh", "business_registered": False}
    out = build_comparison(SCHEMES, evaluate_all(SCHEMES, prof), ["pmegp", "mudra-kishor"])
    assert [col["id"] for col in out["columns"]] == ["pmegp", "mudra-kishor"]
    assert len(out["rows"]) == 8
    assert out["callouts"]["highest_benefit"] == "pmegp"  # 50L > 5L proxy
    assert out["callouts"]["fewest_documents"] in ("pmegp", "mudra-kishor")
    assert all(col["status"] for col in out["columns"])
    assert all(col["url"] and col["last_verified"] for col in out["columns"])


def test_compare_validation():
    prof = {"age": 30}
    for bad in ([], ["pmegp"], ["a", "b", "c", "d"]):
        try:
            build_comparison(SCHEMES, evaluate_all(SCHEMES, prof), bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"should reject {bad}")
    try:
        build_comparison(SCHEMES, evaluate_all(SCHEMES, prof), ["pmegp", "nope"])
    except LookupError:
        pass
    else:
        raise AssertionError("should reject unknown id")
    # dedupe preserves order
    out = build_comparison(SCHEMES, evaluate_all(SCHEMES, prof), ["pmegp", "pmegp", "mudra-kishor"])
    assert [col["id"] for col in out["columns"]] == ["pmegp", "mudra-kishor"]


def test_compare_endpoint():
    h = auth()
    sid = c.post("/sessions", headers=h).json()["session_id"]
    for a in ["planning to start a business", "24", "3 lakhs", "not registered yet",
              "manufacturing", "Karnataka", "2 lakh per year", "Female"]:
        r = c.post(f"/sessions/{sid}/messages", headers=h, json={"message": a}).json()
        if r.get("done"):
            break
    assert r.get("done") is True
    ok = c.get(f"/sessions/{sid}/compare?ids=pmegp,mudra-kishor", headers=h)
    assert ok.status_code == 200
    body = ok.json()
    assert len(body["columns"]) == 2 and body["callouts"]["highest_benefit"] == "pmegp"
    assert c.get(f"/sessions/{sid}/compare?ids=pmegp", headers=h).status_code == 422
    assert c.get(f"/sessions/{sid}/compare?ids=a,b,c,d", headers=h).status_code == 422
    assert c.get(f"/sessions/{sid}/compare?ids=pmegp,nope", headers=h).status_code == 404
    assert c.get(f"/sessions/{sid}/compare?ids=pmegp,mudra-kishor").status_code == 401
