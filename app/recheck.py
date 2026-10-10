"""Near-miss re-check loop: diff old vs new evaluations and propose one-click fixes.

``diff_statuses`` compares two ``evaluate_all`` outputs and reports every scheme
whose status changed. ``fix_actions`` turns a near-miss's actionable gaps into
concrete UI actions (exact value flips or option lists) so "I fixed it" is one
tap, never a re-typed essay. Both are pure functions — easy to test.
"""
from __future__ import annotations

from typing import Any, Dict, List

STATUS_LABEL = {
    "eligible": "Eligible",
    "near_miss": "Almost eligible",
    "possibly_eligible": "Needs info",
    "not_eligible": "Not eligible",
}


def diff_statuses(old_evals: List[dict], new_evals: List[dict]) -> List[Dict[str, Any]]:
    new_by_id = {e["scheme_id"]: e for e in new_evals}
    out = []
    for old in old_evals:
        new = new_by_id.get(old["scheme_id"])
        if not new or new["status"] == old["status"]:
            continue
        out.append({"scheme_id": old["scheme_id"],
                    "scheme_name": new.get("scheme_name", old["scheme_id"]),
                    "old": old["status"], "new": new["status"]})
    return out


def transition_message(transitions: List[Dict[str, Any]], lang: str = "en") -> str:
    from .i18n import STATUS, STR, lang_or_default
    lang = lang_or_default(lang)
    if not transitions:
        return STR["no_change"][lang]
    bits = []
    for t in transitions:
        if t["new"] == "eligible":
            bits.append(STR["moved_eligible"][lang].format(name=t["scheme_name"]))
        elif t["old"] == "not_eligible" and t["new"] == "near_miss":
            bits.append(STR["moved_almost"][lang].format(name=t["scheme_name"]))
        else:
            old = STATUS[t["old"]][lang] if lang != "en" and t["old"] in STATUS else STATUS_LABEL.get(t["old"], t["old"])
            new = STATUS[t["new"]][lang] if lang != "en" and t["new"] in STATUS else STATUS_LABEL.get(t["new"], t["new"])
            bits.append(STR["moved_other"][lang].format(name=t["scheme_name"], old=old, new=new))
    return " ".join(bits)


def fix_actions(scheme: dict, failed: List[dict]) -> List[Dict[str, Any]]:
    """One-click fix proposals for actionable gaps.

    Action shapes: {label, field, value} (exact flip) or
    {label, field, options} (pick one) or {label, field} (free-text update).
    Non-actionable gaps yield no action — reported honestly, not framed as fixable.
    """
    actions = []
    for c in failed:
        if not c.get("actionable"):
            continue
        field, exp, label = c["field"], c.get("expected"), c.get("label") or c["field"]
        if isinstance(exp, bool):
            want = "registered/new" if exp else "new/unregistered"
            actions.append({"label": f"Done: marked {label} ({want})",
                            "field": field, "value": exp})
        elif isinstance(exp, list) and c.get("operator") == "in" and len(exp) <= 6:
            actions.append({"label": f"Change {label}", "field": field,
                            "options": [str(v) for v in exp]})
        else:
            actions.append({"label": f"Update {label}", "field": field})
    return actions
