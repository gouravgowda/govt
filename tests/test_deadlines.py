import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from app.deadlines import deadline_status, validate_window

W = {"opens": "07-01", "closes": "10-31", "note": "typical"}


def test_open_window_counts_down():
    # Oct 10 -> Oct 31 = 21 days -> "soon" tier
    d = deadline_status(W, date(2026, 10, 10))
    assert d["state"] == "open" and d["tier"] == "soon" and d["days"] == 21
    assert d["label"] == "Closes in 21 days"


def test_open_boundaries():
    assert deadline_status(W, date(2026, 7, 1))["state"] == "open"
    assert deadline_status(W, date(2026, 10, 31))["label"] == "Closes today"
    assert deadline_status(W, date(2026, 10, 30))["tier"] == "urgent"
    assert deadline_status(W, date(2026, 8, 1))["tier"] == "open"


def test_upcoming():
    d = deadline_status(W, date(2026, 5, 1))
    assert d["state"] == "upcoming" and d["tier"] == "upcoming"
    assert d["label"].startswith("Opens in 61 days")


def test_closed_reopens_next_year():
    d = deadline_status(W, date(2026, 11, 5))
    assert d["state"] == "closed" and d["date"] == "2027-07-01"
    assert d["label"] == "Closed — reopens 1 Jul"


def test_wrap_window():
    w = {"opens": "11-15", "closes": "02-28"}
    assert deadline_status(w, date(2026, 12, 20))["state"] == "open"
    assert deadline_status(w, date(2027, 1, 10))["state"] == "open"
    up = deadline_status(w, date(2027, 5, 1))
    assert up["state"] == "upcoming" and up["date"] == "2027-11-15"


def test_none_when_no_window():
    assert deadline_status(None) is None
    assert deadline_status({}) is None


def test_bad_windows_rejected():
    for bad in [{"opens": "7-1", "closes": "10-31"}, {"opens": "13-01", "closes": "10-31"},
                {"opens": "02-30", "closes": "10-31"}, {"opens": "07-01"}]:
        with pytest.raises(ValueError):
            validate_window(bad)


def test_results_carry_deadline_badges():
    from app.main import build_results
    r = build_results({"age": 19, "state": "Karnataka", "occupation_stage": "student",
                       "education_level": "undergraduate", "income_band": "under 1 lakh",
                       "gender": "Female", "social_category": "OBC"})
    nsp = [e for e in r["eligible"] if e["id"] == "nsp-scholarship"]
    assert nsp and nsp[0]["deadline"] and nsp[0]["deadline"]["state"] in ("open", "upcoming", "closed")
    # schemes without windows carry explicit null
    kis = [e for e in r["eligible"] if e["id"] == "pmjjby"]
    assert kis and kis[0]["deadline"] is None
