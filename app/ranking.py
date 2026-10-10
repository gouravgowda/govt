"""Transparent ranking. Weights live in config so maintainers can tune without code change."""
from __future__ import annotations

import os, json
from typing import Any, Dict, List

DEFAULT_WEIGHTS = {
    "completeness": 0.35,
    "benefit": 0.25,
    "fit": 0.20,
    "category": 0.10,
    "ease": 0.10,
}

STATUS_BONUS = {"eligible": 1.0, "possibly_eligible": 0.55, "near_miss": 0.35, "not_eligible": 0.0}

FIT_BY_FUNDING = {
    # scheme max loan proxy -> which funding bands fit well (score 1.0), adjacent 0.6, else 0.3
}


def load_weights() -> Dict[str, float]:
    raw = os.getenv("RANK_WEIGHTS_JSON", "")
    if raw:
        try:
            w = json.loads(raw)
            merged = dict(DEFAULT_WEIGHTS)
            merged.update({k: float(v) for k, v in w.items() if k in merged})
            return merged
        except Exception:
            pass
    return dict(DEFAULT_WEIGHTS)


def _completeness(ev: dict) -> float:
    req = [c for c in ev["criteria"] if c.get("required")]
    if not req:
        return 1.0
    met = sum(1 for c in req if c["status"] == "met")
    return met / len(req)


def _benefit_norm(scheme: dict, schemes: List[dict]) -> float:
    mx = max((s.get("benefit_amount", 0) for s in schemes), default=1) or 1
    return (scheme.get("benefit_amount", 0) or 0) / mx


def _fit(scheme: dict, profile: Dict[str, Any]) -> float:
    """Closeness of scheme's loan range to user's funding need. 1.0 if need within range else decay."""
    need = profile.get("funding_need")
    rng = scheme.get("funding_range")  # optional [lo_band, hi_band] labels — rarely set; fallback 0.5
    if not need or not rng:
        return 0.5
    from .engine import FUNDING_ORDER
    order = [o.lower() for o in FUNDING_ORDER]
    try:
        ni = order.index(str(need).strip().lower())
        lo = order.index(str(rng[0]).strip().lower())
        hi = order.index(str(rng[-1]).strip().lower())  # single-band ranges allowed
    except ValueError:
        return 0.5
    if lo <= ni <= hi:
        return 1.0
    dist = min(abs(ni - lo), abs(ni - hi))
    return 0.6 if dist == 1 else 0.3


def _category(scheme: dict, profile: Dict[str, Any]) -> float:
    boosts = [b.lower() for b in (scheme.get("category_boost") or [])]
    if not boosts:
        return 0.3
    vals = [str(profile.get("social_category", "") or "").lower(), str(profile.get("gender", "") or "").lower()]
    return 1.0 if any(v and v in boosts for v in vals) else 0.2


def rank(evaluations: List[dict], schemes: List[dict], profile: Dict[str, Any],
         weights: Dict[str, float] | None = None) -> List[dict]:
    w = weights or load_weights()
    by_id = {s["id"]: s for s in schemes}
    out = []
    for ev in evaluations:
        s = by_id.get(ev["scheme_id"], {})
        comp = _completeness(ev)
        ben = _benefit_norm(s, schemes)
        fit = _fit(s, profile)
        cat = _category(s, profile)
        ease = (s.get("ease_score", 3) or 3) / 5.0
        base = (w["completeness"] * comp + w["benefit"] * ben + w["fit"] * fit
                + w["category"] * cat + w["ease"] * ease)
        score = round(base * STATUS_BONUS.get(ev["status"], 0.0), 4)
        ev2 = dict(ev)
        ev2["score"] = score
        ev2["_breakdown"] = {"completeness": round(comp, 3), "benefit": round(ben, 3),
                             "fit": round(fit, 3), "category": round(cat, 3), "ease": round(ease, 3)}
        # top reason for rank
        parts = sorted([("completeness", comp), ("benefit", ben), ("fit", fit),
                        ("category", cat), ("ease", ease)], key=lambda x: -x[1])
        ev2["rank_reason"] = f"Strongest factor: {parts[0][0]} ({parts[0][1]:.2f})."
        out.append(ev2)
    # eligible first, then possibly, then near_miss, then not_eligible; score desc within group
    order = {"eligible": 0, "possibly_eligible": 1, "near_miss": 2, "not_eligible": 3}
    out.sort(key=lambda e: (order.get(e["status"], 9), -e["score"]))
    return out
