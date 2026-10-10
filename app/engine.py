"""Deterministic rules engine. The LLM NEVER writes eligibility outcomes."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

INCOME_ORDER = ["under 1 lakh", "1 to 2.5 lakh", "2.5 to 6 lakh", "6 to 12 lakh", "above 12 lakh"]
FUNDING_ORDER = ["under 50k", "50k to 5 lakh", "5 to 10 lakh", "10 to 50 lakh",
                 "50 lakh to 1 crore", "above 1 crore"]
# numeric proxy (upper bound INR) for gap messages
FUNDING_VALUE = {
    "under 50k": 50_000,
    "50k to 5 lakh": 500_000,
    "5 to 10 lakh": 1_000_000,
    "10 to 50 lakh": 5_000_000,
    "50 lakh to 1 crore": 10_000_000,
    "above 1 crore": 20_000_000,
}
INCOME_VALUE = {
    "under 1 lakh": 100_000,
    "1 to 2.5 lakh": 250_000,
    "2.5 to 6 lakh": 600_000,
    "6 to 12 lakh": 1_200_000,
    "above 12 lakh": 2_000_000,
}


def _norm(s: Any) -> Any:
    if isinstance(s, str):
        return s.strip().lower()
    return s


def _eq(a: Any, b: Any) -> bool:
    if isinstance(a, str) and isinstance(b, str):
        return a.strip().lower() == b.strip().lower()
    return a == b


def _in(a: Any, vals: list) -> bool:
    if isinstance(a, str):
        return any(_eq(a, v) for v in vals)
    return a in vals


def eval_criterion(operator: str, actual: Any, expected: Any) -> bool:
    op = operator.lower()
    if op == "equals":
        return _eq(actual, expected)
    if op == "in":
        return _in(actual, expected if isinstance(expected, list) else [expected])
    if op == "not_in":
        return not _in(actual, expected if isinstance(expected, list) else [expected])
    if op == "lte":
        return _compare(actual, expected) <= 0
    if op == "gte":
        return _compare(actual, expected) >= 0
    if op == "between":
        lo, hi = expected
        return _compare(actual, lo) >= 0 and _compare(actual, hi) <= 0
    raise ValueError(f"unknown operator {operator}")


def _compare(actual: Any, expected: Any) -> int:
    """Return -1/0/1 comparing band-aware values, else numeric/string compare."""
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return (actual > expected) - (actual < expected)
    # band-aware: funding / income bands compared by order
    if isinstance(actual, str) and isinstance(expected, str):
        al, el = actual.strip().lower(), expected.strip().lower()
        for order in (FUNDING_ORDER, INCOME_ORDER):
            ol = [o.lower() for o in order]
            if al in ol and el in ol:
                ai, ei = ol.index(al), ol.index(el)
                return (ai > ei) - (ai < ei)
        # numeric-looking strings
        try:
            af, ef = float(actual), float(expected)
            return (af > ef) - (af < ef)
        except ValueError:
            pass
        return (al > el) - (al < el)
    # mixed numeric
    try:
        af, ef = float(actual), float(expected)  # type: ignore
        return (af > ef) - (af < ef)
    except (ValueError, TypeError):
        return -1 if str(actual) < str(expected) else (1 if str(actual) > str(expected) else 0)


def gap_text(field: str, actual: Any, expected: Any, operator: str) -> str:
    try:
        if field == "age" and isinstance(actual, (int, float)):
            bound = expected[1] if operator == "between" and isinstance(expected, list) else expected
            if isinstance(bound, (int, float)):
                diff = abs(int(actual) - int(bound))
                direction = "above the limit" if actual > bound else "below the minimum"
                return f"age {actual} is {diff} year(s) {direction} ({expected})"
            if isinstance(expected, list):
                return f"age {actual} is outside the {expected[0]}–{expected[1]} range"
        if field == "funding_need":
            allowed = expected if isinstance(expected, list) else [expected]
            return f"need '{actual}' vs allowed: {' / '.join(str(x) for x in allowed)}"
        return f"got '{actual}', needs '{expected}' ({operator})"
    except Exception:
        return f"got '{actual}', needs '{expected}'"


def evaluate_criterion(criterion: dict, profile: Dict[str, Any]) -> Tuple[str, Any, str]:
    """Returns (status, actual, gap)."""
    field = criterion["field"]
    actual = profile.get(field)
    if actual is None or (isinstance(actual, str) and actual.strip().lower() in ("", "prefer not to say", "unknown", "skip")):
        # "prefer not to say" => unknown per PRD
        return "unknown", actual, ""
    # conditional applicability: criterion may carry {"when": {"field": ..., "in": [...]}} — not in v1 schema,
    # reserved for future; currently everything applies.
    try:
        ok = eval_criterion(criterion["operator"], actual, criterion["value"])
    except Exception:
        return "unknown", actual, ""
    if ok:
        return "met", actual, ""
    return "not_met", actual, gap_text(field, actual, criterion.get("value"), criterion.get("operator", ""))


def evaluate_scheme(scheme: dict, profile: Dict[str, Any]) -> dict:
    crit_results = []
    failed_required = 0
    unknown_required = 0
    failed_all = []
    for c in scheme.get("criteria", []):
        status, actual, gap = evaluate_criterion(c, profile)
        cr = {
            "field": c["field"],
            "status": status,
            "expected": c.get("value"),
            "actual": actual,
            "operator": c.get("operator", ""),
            "required": c.get("required", True),
            "actionable": c.get("actionable", False),
            "fix_hint": c.get("fix_hint"),
            "gap": gap,
            "label": c.get("label") or c["field"],
        }
        crit_results.append(cr)
        if c.get("required", True):
            if status == "not_met":
                failed_required += 1
                failed_all.append(cr)
            elif status == "unknown":
                unknown_required += 1
    # scheme-level outcome per PRD 6.2
    if failed_required == 0 and unknown_required == 0:
        status = "eligible"
    elif failed_required == 0 and unknown_required > 0:
        status = "possibly_eligible"
    elif 1 <= failed_required <= 2 and all(f.get("actionable") for f in failed_all):
        status = "near_miss"
    else:
        status = "not_eligible"
    return {
        "scheme_id": scheme["id"],
        "scheme_name": scheme["name"],
        "status": status,
        "criteria": crit_results,
        "failed_required": failed_required,
        "unknown_required": unknown_required,
        "score": 0.0,
    }


def evaluate_all(schemes: List[dict], profile: Dict[str, Any]) -> List[dict]:
    return [evaluate_scheme(s, profile) for s in schemes]
