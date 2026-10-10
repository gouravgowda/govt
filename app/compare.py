"""Side-by-side comparison of 2–3 schemes. Pure builder — all facts come from the
dataset + the engine's evaluations, so the table can never contradict results."""
from __future__ import annotations

from typing import Any, Dict, List

from .deadlines import deadline_status
from .recheck import STATUS_LABEL

EASE_LABEL = {5: "Very easy", 4: "Easy", 3: "Moderate", 2: "Involved", 1: "Heavy"}


def fmt_inr(n: Any) -> str:
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        return "—"
    if n <= 0:
        return "—"
    if n >= 10_000_000:
        v = n / 10_000_000
        return f"₹{v:g} Cr"
    if n >= 100_000:
        v = n / 100_000
        return f"₹{v:g} L"
    if n >= 1_000:
        v = n / 1_000
        return f"₹{v:g}k"
    return f"₹{n}"


def _status_cell(ev: Dict[str, Any], lang: str = "en") -> str:
    from .i18n import STATUS, lang_or_default
    lang = lang_or_default(lang)
    req = [c for c in ev.get("criteria", []) if c.get("required")]
    met = sum(1 for c in req if c["status"] == "met")
    st = ev.get("status", "")
    base = STATUS[st][lang] if lang != "en" and st in STATUS else STATUS_LABEL.get(st, st)
    if st == "eligible":
        return f"{base} ({met}/{len(req)} checks passed)" if req else base
    if st == "near_miss":
        failed = [c for c in req if c["status"] == "not_met"]
        gap = (failed[0].get("gap") or failed[0].get("label") or "") if failed else ""
        return f"{base} — {gap}" if gap else base
    if st == "possibly_eligible":
        missing = [c.get("label") or c["field"] for c in req if c["status"] == "unknown"]
        return f"{base} — needs: {', '.join(missing[:3])}" if missing else base
    failed = [c for c in req if c["status"] == "not_met"]
    gap = (failed[0].get("gap") or "") if failed else ""
    return f"{base} — {gap}" if gap else base


def _req_cell(ev: Dict[str, Any]) -> List[Dict[str, str]]:
    mark = {"met": "✓", "not_met": "✗", "unknown": "?", "na": "–"}
    return [{"label": c.get("label") or c["field"], "mark": mark.get(c["status"], "?")}
            for c in ev.get("criteria", []) if c.get("required")]


def build_comparison(schemes: List[dict], evaluations: List[dict],
                     ids: List[str], lang: str = "en") -> Dict[str, Any]:
    """ids: 2–3 scheme ids, deduped preserving order. Raises ValueError otherwise."""
    from .i18n import EXPLAIN, lang_or_default
    lang = lang_or_default(lang)
    seen, uniq = set(), []
    for i in (ids or []):
        if i not in seen:
            seen.add(i)
            uniq.append(i)
    if len(uniq) < 2:
        raise ValueError("Pick at least 2 schemes to compare.")
    if len(uniq) > 3:
        raise ValueError("Compare at most 3 schemes at a time.")
    by_id = {s["id"]: s for s in schemes}
    ev_by_id = {e["scheme_id"]: e for e in evaluations}
    unknown = [i for i in uniq if i not in by_id]
    if unknown:
        raise LookupError(f"Unknown scheme(s): {', '.join(unknown)}")
    cols = []
    for sid in uniq:
        s = by_id[sid]
        ev = ev_by_id.get(sid, {"scheme_id": sid, "status": "unknown", "criteria": []})
        dl = deadline_status(s.get("application_window"), lang=lang)
        ease = EASE_LABEL.get(s.get("ease_score", 3), "Moderate")
        if lang != "en":
            ease = EXPLAIN["effort"].get(ease, {}).get(lang, ease)
        cols.append({
            "id": sid, "name": s["name"],
            "status": _status_cell(ev, lang),
            "status_key": ev.get("status", "unknown"),
            "benefit": s.get("benefit_summary", ""),
            "benefit_amount": s.get("benefit_amount", 0) or 0,
            "benefit_fmt": fmt_inr(s.get("benefit_amount", 0)),
            "deadline": dl["label"] if dl else "Rolling — no fixed window",
            "documents": s.get("documents", []),
            "effort": ease,
            "ease_score": s.get("ease_score", 3),
            "channel": s.get("channel", ""),
            "requirements": _req_cell(ev),
            "url": s.get("url", ""), "last_verified": s.get("last_verified", ""),
        })
    callouts: Dict[str, Any] = {}
    if any(c["benefit_amount"] for c in cols):
        callouts["highest_benefit"] = max(cols, key=lambda c: c["benefit_amount"])["id"]
    if any(c["documents"] for c in cols):
        callouts["fewest_documents"] = min(cols, key=lambda c: len(c["documents"]))["id"]
    callouts["easiest_apply"] = max(cols, key=lambda c: c["ease_score"])["id"]
    rows = [
        {"key": "status", "label": "Your status" if lang == "en" else EXPLAIN["rows"]["status"][lang]},
        {"key": "benefit", "label": "Benefit" if lang == "en" else EXPLAIN["rows"]["benefit"][lang]},
        {"key": "deadline", "label": "Deadline" if lang == "en" else EXPLAIN["rows"]["deadline"][lang]},
        {"key": "documents", "label": "Documents needed" if lang == "en" else EXPLAIN["rows"]["documents"][lang]},
        {"key": "effort", "label": "Effort to apply" if lang == "en" else EXPLAIN["rows"]["effort"][lang]},
        {"key": "requirements", "label": "Key requirements" if lang == "en" else EXPLAIN["rows"]["requirements"][lang]},
        {"key": "channel", "label": "How to apply" if lang == "en" else EXPLAIN["rows"]["channel"][lang]},
        {"key": "source", "label": "Official source" if lang == "en" else EXPLAIN["rows"]["source"][lang]},
    ]
    disc = {"en": "Guidance only — figures are scheme maxima/summaries; the official source prevails.",
            "hi": "मार्गदर्शन मात्र — आँकड़े योजना की अधिकतम/संक्षिप्त जानकारी हैं; आधिकारिक स्रोत ही मान्य।",
            "kn": "ಮಾರ್ಗದರ್ಶನ ಮಾತ್ರ — ಅಂಕಿಗಳು ಯೋಜನೆಯ ಗರಿಷ್ಠ/ಸಂಕ್ಷಿಪ್ತ ಮಾಹಿತಿ; ಅಧಿಕೃತ ಮೂಲವೇ ಅಂತಿಮ."}
    return {"columns": cols, "rows": rows, "callouts": callouts,
            "disclaimer": disc[lang], "lang": lang}
