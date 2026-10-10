"""Conversation orchestrator. Stage-aware: a student is never asked about funding
needs; a senior citizen is never asked about business sectors.

Flow: start -> select_question -> ask -> extract -> [confirm?] -> update_profile
      -> check_done -> evaluate -> explain -> present -> followup
Uses LangGraph when installed, else an identical plain-Python state machine.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

QUESTIONS: List[Dict[str, Any]] = [
    {"field": "occupation_stage", "text": "What best describes you?",
     "options": ["student", "aspiring entrepreneur", "existing business", "farmer",
                 "salaried", "artisan", "street vendor", "retired", "homemaker", "other"]},
    {"field": "age", "text": "What is your age (in years)?", "options": None},
    {"field": "state", "text": "Which state do you live in?",
     "options": ["Karnataka", "Maharashtra", "Tamil Nadu", "Delhi", "Other"]},
    {"field": "gender", "text": "What is your gender? (Only used to unlock women-specific benefits — you can skip.)",
     "options": ["Female", "Male", "Other", "prefer not to say"]},
    {"field": "social_category", "text": "What is your social category? (Only unlocks category benefits — you can skip.)",
     "options": ["General", "OBC", "SC", "ST", "EWS", "prefer not to say"]},
    {"field": "education_level", "text": "What level are you studying at (or your highest education)?",
     "options": ["school", "undergraduate", "postgraduate", "diploma", "other"],
     "only_for": ["student"]},
    {"field": "sector", "text": "Which sector is your business/idea in?",
     "options": ["manufacturing", "services", "trading", "agriculture", "tech", "handicraft", "other"],
     "only_for": ["aspiring entrepreneur", "existing business", "artisan"]},
    {"field": "funding_need", "text": "How much funding do you need for the business?",
     "options": ["under 50k", "50k to 5 lakh", "5 to 10 lakh", "10 to 50 lakh",
                 "50 lakh to 1 crore", "above 1 crore"],
     "only_for": ["aspiring entrepreneur", "existing business", "artisan"]},
    {"field": "income_band", "text": "What is your annual household income band? (Needed for scholarships, pensions and subsidies — you can skip.)",
     "options": ["under 1 lakh", "1 to 2.5 lakh", "2.5 to 6 lakh", "6 to 12 lakh", "above 12 lakh"]},
    {"field": "business_registered", "text": "Is your business already registered (e.g. Udyam)?",
     "options": ["Yes", "No"],
     "only_for": ["aspiring entrepreneur", "existing business", "artisan"]},
    {"field": "first_time_borrower", "text": "Is this your first business loan?",
     "options": ["Yes", "No"],
     "only_for": []},  # no scheme keys on this yet — updatable via re-check, not asked by default
]

FIELD_TO_QUESTION = {q["field"]: q for q in QUESTIONS}
MAX_QUESTIONS = 8


def is_relevant(question: Dict[str, Any], profile: Dict[str, Any]) -> bool:
    only = question.get("only_for")
    if only is None:
        return True
    stage = (profile.get("occupation_stage") or "").strip().lower()
    # stage unknown/None (skipped): only ask universal questions
    if not stage:
        return False
    return stage in [s.lower() for s in only]


BUSINESS_STAGES = {"aspiring entrepreneur", "existing business", "artisan"}
# PRD 6.1: ask the most decisive fields first. Business users face a 9-field
# sweep under an 8-question cap, so category (optional almost everywhere for
# entrepreneurs) yields to funding/registration; it stays updatable anytime.
BUSINESS_ORDER = ["occupation_stage", "age", "funding_need", "business_registered",
                  "sector", "state", "income_band", "gender", "social_category",
                  "first_time_borrower"]


def ordered_questions(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_field = {q["field"]: q for q in QUESTIONS}
    stage = (profile.get("occupation_stage") or "").strip().lower()
    if stage in BUSINESS_STAGES:
        fields = BUSINESS_ORDER
    else:
        fields = [q["field"] for q in QUESTIONS]
    return [by_field[f] for f in fields if f in by_field]


def relevant_questions(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    # occupation + age are always asked first; the rest adapt once stage is known
    out = []
    for q in ordered_questions(profile):
        if q["field"] in ("occupation_stage", "age"):
            out.append(q)
        elif profile.get("occupation_stage") is None and q.get("only_for") is not None:
            continue  # can't tailor yet — universal questions only
        elif is_relevant(q, profile):
            out.append(q)
    return out


def next_field(profile: Dict[str, Any], schemes: List[dict] | None = None,
               asked: List[str] | None = None) -> Optional[Dict[str, Any]]:
    asked = asked or []
    for q in ordered_questions(profile):
        f = q["field"]
        if profile.get(f) is not None or f in asked:
            continue
        if f not in ("occupation_stage", "age") and not is_relevant(q, profile):
            continue
        return q
    return None


def questions_answered_count(profile: Dict[str, Any]) -> int:
    return sum(1 for q in QUESTIONS if profile.get(q["field"]) is not None)


def is_done(profile: Dict[str, Any]) -> bool:
    if questions_answered_count(profile) >= MAX_QUESTIONS:
        return True
    if profile.get("occupation_stage") is None or profile.get("age") is None:
        return False
    # done when every relevant question has an answer (skips are tracked
    # via the session's asked-list by the caller — see main.py)
    return next_field(profile, None, []) is None


def progress_text(profile: Dict[str, Any], lang: str = "en") -> str:
    from .i18n import STR, lang_or_default
    lang = lang_or_default(lang)
    total = min(len(relevant_questions(profile)), MAX_QUESTIONS)
    n = min(questions_answered_count(profile) + 1, total if total else MAX_QUESTIONS)
    total = total if total else MAX_QUESTIONS
    if lang == "en":
        return f"Question {n} of {total}"
    return STR["progress"][lang].format(n=n, total=total)


# ---- Optional LangGraph wiring ----
def build_graph(handle_message_fn):
    """Try to build a LangGraph graph; return None when langgraph isn't installed."""
    try:
        from langgraph.graph import StateGraph, END  # type: ignore
    except Exception:
        return None

    def select(state): return {"cursor": "ask"}
    def ask(state): return {}
    workflow = StateGraph(dict)
    workflow.add_node("select_question", select)
    workflow.add_node("ask", ask)
    workflow.set_entry_point("select_question")
    workflow.add_edge("select_question", "ask")
    workflow.add_edge("ask", END)
    return workflow.compile()
