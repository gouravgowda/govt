import os
import tempfile

os.environ.setdefault("AUTH_DB_PATH", os.path.join(tempfile.mkdtemp(), "test_recheck.db"))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.recheck import diff_statuses, fix_actions, transition_message
from app.engine import evaluate_all
from app.schemes import load_schemes

c = TestClient(app)
SCHEMES = load_schemes()
BY_ID = {s["id"]: s for s in SCHEMES}


def auth():
    tok = c.post("/auth/signup", json={"name": "Rc", "email": f"rc{auth.n}@e.com",
                                       "password": "secret123"}).json()["token"]
    auth.n += 1
    return {"Authorization": f"Bearer {tok}"}
auth.n = 0


def run_to_done(h, answers):
    sid = c.post("/sessions", headers=h).json()["session_id"]
    r = None
    for a in answers:
        r = c.post(f"/sessions/{sid}/messages", headers=h, json={"message": a}).json()
        if r.get("done"):
            break
    assert r.get("done") is True, r
    return sid, r


def test_diff_detects_upgrade():
    prof = {"age": 24, "occupation_stage": "aspiring entrepreneur", "sector": "tech",
            "funding_need": "5 to 10 lakh", "business_registered": False}
    old = evaluate_all(SCHEMES, prof)
    new = evaluate_all(SCHEMES, {**prof, "business_registered": True})
    t = diff_statuses(old, new)
    seed = [x for x in t if x["scheme_id"] == "startup-seed-fund"]
    assert seed and seed[0]["old"] == "near_miss" and seed[0]["new"] == "eligible"
    assert "moved to Eligible" in transition_message(seed)
    assert transition_message([]) == "Re-checked — no scheme changed status."


def test_fix_actions_shapes():
    seed_failed = [cr for cr in
                   next(e for e in evaluate_all(SCHEMES, {"age": 24, "occupation_stage": "aspiring entrepreneur",
                                                          "sector": "tech", "funding_need": "5 to 10 lakh",
                                                          "business_registered": False})
                        if e["scheme_id"] == "startup-seed-fund")["criteria"]
                   if cr["status"] == "not_met" and cr["required"]]
    acts = fix_actions(BY_ID["startup-seed-fund"], seed_failed)
    assert acts and acts[0]["field"] == "business_registered" and acts[0]["value"] is True
    # funding band gap -> options action
    stand_failed = [cr for cr in
                    next(e for e in evaluate_all(SCHEMES, {"age": 30, "occupation_stage": "aspiring entrepreneur",
                                                           "sector": "services", "funding_need": "50k to 5 lakh",
                                                           "gender": "Female", "business_registered": False})
                         if e["scheme_id"] == "standup-india")["criteria"]
                    if cr["status"] == "not_met" and cr["required"]]
    acts2 = fix_actions(BY_ID["standup-india"], stand_failed)
    assert any("options" in a for a in acts2)
    # non-actionable gaps yield nothing
    assert fix_actions({}, [{"field": "age", "status": "not_met", "required": True,
                             "actionable": False, "expected": [18, 70],
                             "label": "Age", "operator": "between"}]) == []


def test_conversational_update_upgrades_scheme():
    h = auth()
    sid, r = run_to_done(h, ["planning to start a tech business", "24", "7 lakhs",
                             "not registered yet", "tech", "Karnataka",
                             "5 lakh per year", "Male"])
    assert any(n["id"] == "startup-seed-fund" for n in r["results"]["near_miss"])
    assert any("actions" in n and n["actions"] for n in r["results"]["near_miss"])
    r2 = c.post(f"/sessions/{sid}/messages", headers=h,
                json={"message": "I got my DPIIT certificate, business is registered now"}).json()
    assert r2["done"] is True
    assert any(t["scheme_id"] == "startup-seed-fund" and t["new"] == "eligible"
               for t in (r2["transitions"] or [])), r2["reply"]
    assert "moved to Eligible" in r2["reply"]


def test_recheck_keyword_and_unknown_update():
    h = auth()
    sid, r = run_to_done(h, ["student", "19", "Karnataka", "Female", "OBC",
                             "undergraduate", "under 1 lakh"])
    r2 = c.post(f"/sessions/{sid}/messages", headers=h, json={"message": "recheck"}).json()
    assert r2["done"] is True and r2["transitions"] == []
    r3 = c.post(f"/sessions/{sid}/messages", headers=h, json={"message": "banana hammock"}).json()
    assert r3["done"] is True and "couldn't tell what changed" in r3["reply"]


def test_patch_returns_transitions():
    h = auth()
    sid, r = run_to_done(h, ["planning a services business", "30", "7 lakhs",
                             "not registered", "services", "Delhi",
                             "5 lakh per year", "Female"])
    p = c.patch(f"/sessions/{sid}/profile", headers=h,
                json={"field": "business_registered", "value": True}).json()
    assert any(t["scheme_id"] == "startup-seed-fund" and t["new"] == "eligible"
               for t in p["transitions"])
    assert any(e["id"] == "startup-seed-fund" for e in p["results"]["eligible"])
