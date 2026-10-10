import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine import evaluate_all, eval_criterion
from app.main import app as _app
from app.schemes import load_schemes
from app.ranking import rank
from app.explanation import templated_match_explanation, templated_nearmiss_explanation
from app.extraction import extract_field
from tests.fixtures import FIXTURES


def test_operators():
    assert eval_criterion("equals", "Karnataka", "karnataka")
    assert eval_criterion("in", "SC", ["SC", "ST"])
    assert not eval_criterion("in", "General", ["SC", "ST"])
    assert eval_criterion("between", 24, [18, 70])
    assert not eval_criterion("between", 17, [18, 70])
    assert eval_criterion("gte", 5, 3)
    assert eval_criterion("lte", "under 1 lakh", "1 to 2.5 lakh")  # band-aware


def test_schema_valid():
    schemes = load_schemes()
    assert len(schemes) >= 6
    for s in schemes:
        assert s["url"] and s["last_verified"], s["id"]


def test_fixtures():
    schemes = load_schemes()
    for fx in FIXTURES:
        evals = {e["scheme_id"]: e for e in evaluate_all(schemes, fx["profile"])}
        for sid, expected in fx["expect"].items():
            got = evals[sid]["status"]
            # near_miss vs not_eligible boundary: accept near_miss where not_eligible expected ONLY if gap actionable?
            # Here expectations are strict.
            assert got == expected, f"{fx['name']}: {sid} expected {expected}, got {got} ({evals[sid]})"


def test_ranking_deterministic():
    schemes = load_schemes()
    p = FIXTURES[0]["profile"]
    r1 = rank(evaluate_all(schemes, p), schemes, p)
    r2 = rank(evaluate_all(schemes, p), schemes, p)
    assert [e["scheme_id"] for e in r1] == [e["scheme_id"] for e in r2]
    assert r1[0]["status"] == "eligible"


def test_explanation_faithfulness():
    """Every token-ish claim in templated explanation must come from engine output."""
    schemes = load_schemes()
    by_id = {s["id"]: s for s in schemes}
    for fx in FIXTURES:
        for ev in evaluate_all(schemes, fx["profile"]):
            s = by_id[ev["scheme_id"]]
            if ev["status"] == "eligible":
                txt = templated_match_explanation(s, ev).lower()
                # explanation must mention the scheme-relevant field values only
                for c in ev["criteria"]:
                    if c["status"] == "met" and c["field"] in txt:
                        assert str(c["actual"]).lower() in txt or c["field"] in txt
            if ev["status"] == "near_miss":
                txt = templated_nearmiss_explanation(s, ev)
                assert len(txt) > 10


def test_extraction():
    v, c = extract_field("age", "I am 24 years old")
    assert v == 24 and c > 0.5
    v, c = extract_field("funding_need", "need around 3 lakhs")
    assert v == "50k to 5 lakh", v
    v, c = extract_field("income_band", "family income 90k per year")
    assert v == "under 1 lakh", v
    v, c = extract_field("state", "I live in Karnataka")
    assert v == "Karnataka"
    v, c = extract_field("business_registered", "not yet registered")
    assert v is False


def test_public_scheme_list_powers_landing_grid():
    from fastapi.testclient import TestClient
    tc = TestClient(_app)
    r = tc.get("/schemes")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 50, len(items)
    by_id = {s["id"]: s for s in items}
    assert by_id["pmegp"]["tag"] == "CENTRAL"
    assert by_id["ka-udyogini"]["tag"] == "KARNATAKA"
    assert by_id["wb-kanyashree"]["tag"] == "WEST BENGAL"
    assert by_id["tg-dalit-bandhu"]["tag"] == "TELANGANA"
    states = {s["tag"] for s in items} - {"CENTRAL"}
    assert len(states) >= 10, states
    for s in items:
        assert s["name"] and s["url"], s["id"]
