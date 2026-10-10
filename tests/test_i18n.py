import os
import tempfile

os.environ.setdefault("AUTH_DB_PATH", os.path.join(tempfile.mkdtemp(), "test_i18n.db"))

import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.i18n import LANGS, QUESTIONS, OPTION_LABELS, STR, qoptions
from app.graph import FIELD_TO_QUESTION, QUESTIONS as GQ
from app.deadlines import deadline_status
from app.extraction import extract_field

c = TestClient(app)


def auth():
    tok = c.post("/auth/signup", json={"name": "Lg", "email": f"lg{auth.n}@e.com",
                                       "password": "secret123"}).json()["token"]
    auth.n += 1
    return {"Authorization": f"Bearer {tok}"}
auth.n = 0


def test_no_missing_keys():
    # every intake field has a question in every language
    for q in GQ:
        for lang in LANGS:
            assert QUESTIONS[q["field"]][lang], (q["field"], lang)
    # every chip value has a label in hi/kn
    for field, q in FIELD_TO_QUESTION.items():
        for v in q.get("options") or []:
            vals, labels = qoptions(field, "hi")
            assert len(vals) == len(labels) and len(vals) > 0, field
            vals, labels = qoptions(field, "kn")
            assert len(vals) == len(labels) and len(vals) > 0, field
    # every reply template exists in every language (en composes 3 with DISCLAIMER)
    for key, table in STR.items():
        for lang in LANGS:
            if lang == "en" and key in ("greet", "results_ready", "found", "disc"):
                continue
            assert table[lang] is not None, (key, lang)


def test_hindi_extraction():
    assert extract_field("age", "मैं 24 साल का हूँ")[0] == 24
    assert extract_field("age", "२४")[0] == 24  # devanagari digits
    assert extract_field("gender", "महिला")[0] == "Female"
    assert extract_field("gender", "ಮಹಿಳೆ")[0] == "Female"
    assert extract_field("occupation_stage", "मैं छात्र हूँ")[0] == "student"
    assert extract_field("occupation_stage", "ನಾನು ರೈತ")[0] == "farmer"
    assert extract_field("state", "कर्नाटक")[0] == "Karnataka"
    assert extract_field("income_band", "2 लाख सालाना")[0] == "1 to 2.5 lakh"
    assert extract_field("funding_need", "मुझे 8 लाख चाहिए")[0] == "5 to 10 lakh"
    assert extract_field("funding_need", "ನನಗೆ 3 ಲಕ್ಷ ಬೇಕು")[0] == "50k to 5 lakh"
    assert extract_field("business_registered", "हाँ, पंजीकृत है")[0] is True
    assert extract_field("education_level", "स्नातक")[0] == "undergraduate"


def test_hindi_deadline_labels():
    w = {"opens": "07-01", "closes": "10-31"}
    d = deadline_status(w, date(2026, 10, 10), "hi")
    assert d["label"] == "21 दिनों में बंद" and d["tier"] == "soon"
    d = deadline_status(w, date(2026, 5, 1), "kn")
    assert d["state"] == "upcoming" and "ದಿನಗಳಲ್ಲಿ ತೆರೆಯುತ್ತದೆ" in d["label"]
    d = deadline_status(w, date(2026, 11, 5), "hi")
    assert d["state"] == "closed" and "फिर खुलेगा" in d["label"]


def test_hindi_session_flow():
    h = auth()
    s = c.post("/sessions?lang=hi", headers=h).json()
    assert s["lang"] == "hi" and "नमस्ते" in s["message"]
    assert "उम्र" in s["question"] or "कौन" in s["question"]
    assert s["option_labels"] and s["option_labels"] != s["options"]
    r = c.post(f"/sessions/{s['session_id']}/messages", headers=h,
               json={"message": "मैं छात्र हूँ"}).json()
    assert r["question"] and "उम्र" in r["question"]
    r = c.post(f"/sessions/{s['session_id']}/messages", headers=h,
               json={"message": "19 साल"}).json()
    assert r["question"] and ("राज्य" in r["question"] or "रहते" in r["question"])
    # progress translated
    assert r["progress"].startswith("प्रश्न")


def test_kannada_session_flow():
    h = auth()
    s = c.post("/sessions?lang=kn", headers=h).json()
    assert s["lang"] == "kn" and "ನಮಸ್ತೆ" in s["message"]
    r = c.post(f"/sessions/{s['session_id']}/messages", headers=h,
               json={"message": "ನಾನು ವಿದ್ಯಾರ್ಥಿ"}).json()
    assert r["question"] and "ವಯಸ್ಸು" in r["question"]


def test_hindi_results_translated():
    h = auth()
    sid = c.post("/sessions?lang=hi", headers=h).json()["session_id"]
    r = None
    for a in ["मैं छात्र हूँ", "19 साल", "कर्नाटक", "महिला", "OBC",
              "स्नातक", "1 लाख से कम"]:
        r = c.post(f"/sessions/{sid}/messages", headers=h, json={"message": a}).json()
        if r.get("done"):
            break
    assert r.get("done") is True, r.get("reply")
    assert r["results"]["lang"] == "hi"
    nsp = [e for e in r["results"]["eligible"] if e["id"] == "nsp-scholarship"]
    assert nsp and "योग्य" in nsp[0]["explanation"]
    assert nsp[0]["deadline"] and "बंद" in nsp[0]["deadline"]["label"]
    assert "मार्गदर्शन" in r["results"]["disclaimer"]


def test_bad_lang_falls_back_to_english():
    h = auth()
    s = c.post("/sessions?lang=xx", headers=h).json()
    assert s["lang"] == "en" and "Namaste" in s["message"]
