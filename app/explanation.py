"""Explanation layer: LLM-constrained-to-engine-output, with offline templated fallback.

Contract: explanations may ONLY mention facts present in the engine's structured
output (criteria, statuses, user values). Faithfulness tests enforce this.
`lang` selects the template language (en/hi/kn); values stay canonical English
because they are data. The LLM path is English-only — other languages always
use the deterministic template.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List


def templated_match_explanation(scheme: dict, evaluation: dict, lang: str = "en") -> str:
    from .i18n import EXPLAIN, field_label, lang_or_default
    lang = lang_or_default(lang)
    met = [c for c in evaluation.get("criteria", []) if c["status"] == "met"]
    if lang == "en":
        if not met:
            return f"{scheme['name']}: all required checks passed on the information given."
        bits = []
        for c in met[:3]:
            bits.append(f"{c.get('label') or c['field']}: {c.get('actual')!r} satisfies {c.get('expected')!r}")
        return f"Why you qualify for {scheme['name']}: " + "; ".join(bits) + "."
    if not met:
        return EXPLAIN["match_all"][lang].format(name=scheme["name"])
    bits = []
    for c in met[:3]:
        bits.append(EXPLAIN["match_bit"][lang].format(
            label=field_label(c["field"], lang), actual=c.get("actual"), expected=c.get("expected")))
    return EXPLAIN["match"][lang].format(name=scheme["name"], bits="; ".join(bits))


def templated_nearmiss_explanation(scheme: dict, evaluation: dict, lang: str = "en") -> str:
    from .i18n import EXPLAIN, field_label, lang_or_default
    lang = lang_or_default(lang)
    failed = [c for c in evaluation.get("criteria", []) if c["status"] == "not_met" and c.get("required")]
    if lang == "en":
        if not failed:
            return f"{scheme['name']}: needs one more detail to decide."
        parts = []
        for c in failed:
            gap = c.get("gap") or f"{c['field']} mismatch"
            hint = c.get("fix_hint") or ("Actionable — see fix." if c.get("actionable") else "Not changeable.")
            parts.append(f"{c.get('label') or c['field']} — {gap}. {hint}")
        return f"Gap for {scheme['name']}: " + " | ".join(parts)
    if not failed:
        return EXPLAIN["match_all"][lang].format(name=scheme["name"])
    parts = []
    for c in failed:
        gap = c.get("gap") or f"{c['field']} mismatch"
        hint = c.get("fix_hint") or ""
        bit = f"{field_label(c['field'], lang)} — {gap}"
        if hint:
            bit += f". {hint}"
        parts.append(bit)
    return EXPLAIN["near"][lang].format(name=scheme["name"], bits=" | ".join(parts))


def llm_explain(kind: str, scheme: dict, evaluation: dict, profile: Dict[str, Any]) -> str | None:
    """Constrained LLM call. Returns None when unavailable so caller falls back."""
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(base_url=os.getenv("LLM_BASE_URL") or None, timeout=15)
        allowed = {
            "scheme": scheme["name"],
            "criteria": [
                {"field": c["field"], "status": c["status"], "expected": c["expected"],
                 "actual": c["actual"], "label": c.get("label")}
                for c in evaluation.get("criteria", [])
            ],
        }
        sys = ("You explain government-scheme eligibility. Mention ONLY facts from the JSON given. "
               "No new numbers, no guarantees, no approval promises. Plain grade-8 language, ≤80 words.")
        user = f"{kind} explanation. Data: {allowed}"
        r = client.chat.completions.create(model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                                           messages=[{"role": "system", "content": sys},
                                                     {"role": "user", "content": user}],
                                           max_tokens=180, temperature=0.2)
        return (r.choices[0].message.content or "").strip() or None
    except Exception:
        return None


def explain_match(scheme: dict, evaluation: dict, profile: Dict[str, Any], lang: str = "en") -> str:
    from .i18n import lang_or_default
    if lang_or_default(lang) != "en":
        return templated_match_explanation(scheme, evaluation, lang)
    return llm_explain("match", scheme, evaluation, profile) or templated_match_explanation(scheme, evaluation)


def explain_near_miss(scheme: dict, evaluation: dict, profile: Dict[str, Any],
                      alternatives: List[str] | None = None, lang: str = "en") -> str:
    from .i18n import lang_or_default
    if lang_or_default(lang) != "en":
        return templated_nearmiss_explanation(scheme, evaluation, lang)
    base = llm_explain("near-miss", scheme, evaluation, profile) or templated_nearmiss_explanation(scheme, evaluation)
    if alternatives:
        base += f" Alternative you do qualify for: {alternatives[0]}."
    return base
