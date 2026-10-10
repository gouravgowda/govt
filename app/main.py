"""FastAPI layer: sessions, messages, results, profile patch, scheme detail, health."""
from __future__ import annotations

import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from contextlib import asynccontextmanager
from datetime import date

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from . import auth as auth_store
from . import history as history_store
from .compare import build_comparison
from .deadlines import deadline_status
from .engine import evaluate_all
from .i18n import STR, field_label, lang_or_default, qoptions, qtext
from .recheck import diff_statuses, fix_actions, transition_message
from .explanation import explain_match, explain_near_miss
from .extraction import extract_field, try_llm_extract
from .graph import FIELD_TO_QUESTION, is_done, next_field, progress_text
from .ranking import rank
from .schemes import load_schemes
from .models import (MessageRequest, MessageResponse, CreateSessionResponse,
                     ProfilePatchRequest, SignupRequest, LoginRequest, AuthResponse)

DISCLAIMER = ("I give guidance, not guarantees — final eligibility is decided by the scheme authority. "
              "I never ask for Aadhaar, PAN or bank details.")
STALENESS_DAYS = int(os.getenv("STALENESS_DAYS", "180"))

SCHEMES: List[dict] = []
SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSION_TTL = int(os.getenv("SESSION_TTL_SECONDS", "3600"))


def get_schemes() -> List[dict]:
    global SCHEMES
    if not SCHEMES:
        SCHEMES = load_schemes()
    return SCHEMES


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_schemes()
    yield


app = FastAPI(title="Government Scheme-Matching Assistant", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _new_session(owner_email: str = "", lang: str = "en") -> str:
    now = time.time()
    for k in [k for k, v in SESSIONS.items() if now - v["created"] > SESSION_TTL]:
        SESSIONS.pop(k, None)
    sid = f"s_{uuid.uuid4().hex[:12]}"
    SESSIONS[sid] = {"profile": {}, "asked": [], "pending_confirm": None,
                     "created": time.time(), "turns": 0, "owner": owner_email,
                     "lang": lang_or_default(lang)}
    return sid


def _lang(session: Dict[str, Any]) -> str:
    return lang_or_default(session.get("lang", "en"))


def _ask_turn(session: Dict[str, Any], q: dict, reply: str) -> "MessageResponse":
    """Build a question turn in the session's language. Chips show translated
    labels but submit canonical English values (engine untouched)."""
    L = _lang(session)
    vals, labels = qoptions(q["field"], L)
    return MessageResponse(reply=reply, question=qtext(q["field"], L),
                           progress=progress_text(session["profile"], L),
                           field=q["field"], options=vals or None,
                           option_labels=labels or None)


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        return ""
    return authorization.split(None, 1)[1].strip()


def current_user(authorization: str | None = Header(default=None)) -> Dict[str, Any]:
    user = auth_store.user_for_token(_bearer(authorization or ""))
    if not user:
        raise HTTPException(401, "Login required — sign up or log in first.")
    return user


def _get_session(sid: str, user: Dict[str, Any] | None = None) -> Dict[str, Any]:
    s = SESSIONS.get(sid)
    if not s:
        raise HTTPException(404, "unknown session — start a new one via POST /sessions")
    if time.time() - s["created"] > SESSION_TTL:
        SESSIONS.pop(sid, None)
        raise HTTPException(410, "session expired — start a new one via POST /sessions")
    if user and s.get("owner") and s["owner"] != user["email"]:
        raise HTTPException(403, "this session belongs to another account")
    return s


def _first_question(session: Dict[str, Any]):
    q = next_field(session["profile"], get_schemes(), session["asked"])
    return q


def _stale_warning(scheme: dict) -> str | None:
    try:
        lv = date.fromisoformat(scheme.get("last_verified", ""))
        if (date.today() - lv).days > STALENESS_DAYS:
            return f"Note: record last verified {lv} — rules may have changed; check the official link."
    except Exception:
        return "Note: verification date unclear — check the official link."
    return None


def build_results(profile: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
    lang = lang_or_default(lang)
    schemes = get_schemes()
    evals = evaluate_all(schemes, profile)
    ranked = rank(evals, schemes, profile)
    by_id = {s["id"]: s for s in schemes}
    eligible, near, poss = [], [], []
    for ev in ranked:
        s = by_id[ev["scheme_id"]]
        stale = _stale_warning(s)
        if ev["status"] == "eligible":
            eligible.append({
                "id": s["id"], "name": s["name"], "benefit": s["benefit_summary"],
                "explanation": explain_match(s, ev, profile, lang),
                "documents": s.get("documents", []), "channel": s.get("channel", ""),
                "url": s["url"], "last_verified": s["last_verified"], "source": s["source"],
                "score": ev["score"], "rank_reason": ev.get("rank_reason"),
                "stale_warning": stale, "deadline": deadline_status(s.get("application_window"), lang=lang),
            })
        elif ev["status"] == "near_miss":
            failed = [c for c in ev["criteria"] if c["status"] == "not_met" and c.get("required")]
            alt = [e["scheme_name"] for e in ranked if e["status"] == "eligible"][:1]
            near.append({
                "id": s["id"], "name": s["name"], "benefit": s["benefit_summary"],
                "failed": [{"field": c["field"], "label": c.get("label"), "gap": c.get("gap"),
                            "actionable": c.get("actionable"), "fix": c.get("fix_hint")} for c in failed],
                "guidance": explain_near_miss(s, ev, profile, alt, lang),
                "url": s["url"], "last_verified": s["last_verified"], "source": s["source"],
                "score": ev["score"], "stale_warning": stale,
                "deadline": deadline_status(s.get("application_window"), lang=lang),
                "actions": fix_actions(s, failed),
            })
        elif ev["status"] == "possibly_eligible":
            missing = [c["field"] for c in ev["criteria"] if c["status"] == "unknown" and c.get("required")]
            poss.append({"id": s["id"], "name": s["name"], "benefit": s["benefit_summary"],
                         "missing_fields": missing, "url": s["url"],
                         "last_verified": s["last_verified"], "source": s["source"]})
    disc = DISCLAIMER + " Official source prevails." if lang == "en" else STR["disc"][lang]
    return {"eligible": eligible, "near_miss": near, "possibly_eligible": poss,
            "profile": profile, "disclaimer": disc, "lang": lang}


def _handle_offtopic(text: str) -> bool:
    t = text.strip().lower()
    triggers = ["guarantee", "approve my", "bypass", "jailbreak", "ignore previous",
                "you are now", "system prompt", "aadhaar", "pan number"]
    return any(k in t for k in triggers)


_ALLOWED_VALUES: Dict[str, set] = {
    "gender": {"female", "male", "other", "prefer not to say"},
    "social_category": {"general", "obc", "sc", "st", "ews", "prefer not to say"},
    "occupation_stage": {"student", "aspiring entrepreneur", "existing business", "farmer",
                         "salaried", "artisan", "street vendor", "retired", "homemaker", "unemployed", "other"},
    "education_level": {"school", "undergraduate", "postgraduate", "diploma", "other"},
    "sector": {"manufacturing", "services", "trading", "agriculture", "tech", "handicraft", "other"},
    "income_band": {"under 1 lakh", "1 to 2.5 lakh", "2.5 to 6 lakh", "6 to 12 lakh", "above 12 lakh"},
    "funding_need": {"under 50k", "50k to 5 lakh", "5 to 10 lakh", "10 to 50 lakh",
                     "50 lakh to 1 crore", "above 1 crore"},
}


def _valid_field_value(field: str, value: Any) -> bool:
    """API-boundary guard: profile fields must hold engine-compatible values."""
    if value is None:
        return True
    if field == "age":
        return isinstance(value, int) and not isinstance(value, bool) and 5 <= value <= 100
    if field in ("business_registered", "first_time_borrower"):
        return isinstance(value, bool)
    if field == "state":
        return isinstance(value, str) and 0 < len(value.strip()) <= 60
    allowed = _ALLOWED_VALUES.get(field)
    return bool(allowed) and isinstance(value, str) and value.strip().lower() in allowed


@app.post("/auth/signup", response_model=AuthResponse)
def signup(req: SignupRequest):
    try:
        user = auth_store.create_user(req.name, req.email, req.password)
    except ValueError as e:
        raise HTTPException(409 if "already exists" in str(e) else 422, str(e))
    return AuthResponse(token=auth_store.issue_token(user["id"]), name=user["name"], email=user["email"])


@app.post("/auth/login", response_model=AuthResponse)
def login(req: LoginRequest):
    user = auth_store.verify_user(req.email, req.password)
    if not user:
        raise HTTPException(401, "Wrong email or password.")
    return AuthResponse(token=auth_store.issue_token(user["id"]), name=user["name"], email=user["email"])


@app.get("/auth/me")
def me(user: Dict[str, Any] = Depends(current_user)):
    return {"name": user["name"], "email": user["email"]}


@app.post("/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    auth_store.revoke_token(_bearer(authorization or ""))
    return {"status": "logged out"}


@app.post("/sessions", response_model=CreateSessionResponse)
def create_session(lang: str = "en", user: Dict[str, Any] = Depends(current_user)):
    L = lang_or_default(lang)
    sid = _new_session(user["email"], L)
    s = SESSIONS[sid]
    q = _first_question(s)
    if L == "en":
        greet = f"Namaste! I help you find government schemes you may qualify for. {DISCLAIMER}"
    else:
        greet = STR["greet"][L]
    vals, labels = qoptions(q["field"], L) if q else ([], [])
    return CreateSessionResponse(
        session_id=sid,
        message=greet,
        question=qtext(q["field"], L) if q else None,
        progress=progress_text(s["profile"], L) if q else None,
        field=q["field"] if q else None,
        options=vals or None,
        option_labels=labels or None,
        lang=L,
    )


CONFIRM_YES = {"yes", "correct", "right", "confirm", "yeah", "yep",
                 "हाँ", "हां", "जी", "हौದು", "ಹೌದು"}
CONFIRM_NO = {"no", "wrong", "incorrect", "नहीं", "नही", "ना", "ಇಲ್ಲ", "ಬೇಡ"}


def _process_reply(session: Dict[str, Any], text: str, lang: str = "en") -> Dict[str, Any]:
    L = lang_or_default(lang)
    # prompt-injection: treat free text strictly as data (PRD 12)
    if _handle_offtopic(text):
        t = text.strip().lower()
        if "guarantee" in t or "approve" in t or "bypass" in t:
            return {"reply": STR["refuse_guarantee"][L], "redirect": True}
        # injection-looking text still goes through extraction as data; fall through
    # pending confirmation?
    pc = session.get("pending_confirm")
    if pc:
        t = text.strip().lower()
        if t in CONFIRM_YES:
            session["profile"][pc["field"]] = pc["value"]
            session["asked"].append(pc["field"])
            session["pending_confirm"] = None
            return {"confirmed": True}
        if t in CONFIRM_NO:
            session["pending_confirm"] = None
            return {"reply": STR["noproblem"][L] + qtext(pc["field"], L),
                    "field": pc["field"], "confirm_no": True}
        # otherwise treat as new answer to same field
        session["pending_confirm"] = None
    # which field are we answering?
    q = next_field(session["profile"], get_schemes(), session["asked"])
    if not q:
        return {"done_early": True}
    field = q["field"]
    llm_hit = try_llm_extract(field, text)
    value, conf = llm_hit if llm_hit else extract_field(field, text)
    if value is not None and not _valid_field_value(field, value):
        value, conf = None, 0.0
    # contradiction: latest wins (PRD 12) — just overwrite; note it
    had_old = session["profile"].get(field)
    if value is None:
        if conf == 0.0 and ("prefer not" in text.lower() or "बताना नहीं" in text or "ಹೇಳಲು ಇಷ್ಟವಿಲ್ಲ" in text):
            session["profile"][field] = None
            session["asked"].append(field)
            return {"skipped": True, "field": field}
        return {"reply": STR["retry"][L], "question": True,
                "field": field, "retry": True}
    if conf < 0.55:
        session["pending_confirm"] = {"field": field, "value": value}
        return {"reply": STR["confirm"][L].format(value=value, field=field_label(field, L)),
                "field": field, "confirming": True}
    session["profile"][field] = value
    session["asked"].append(field)
    note = STR["updated_note"][L] if had_old is not None and had_old != value else ""
    return {"stored": True, "field": field, "value": value, "note": note}


UPDATE_FIELD_ORDER = ["age", "state", "social_category", "gender", "occupation_stage",
                      "sector", "education_level", "income_band", "funding_need",
                      "business_registered", "first_time_borrower"]
# enums/numbers first: on confidence ties they beat the bool catch-alls
RECHECK_KEYWORDS = ("recheck", "re-check", "check again", "refresh", "re-evaluate", "reevaluate")


def _handle_update(session: Dict[str, Any], text: str) -> MessageResponse:
    """Done-mode: user reports a changed circumstance → update profile, re-run
    the engine, and report exactly which schemes changed status."""
    L = _lang(session)
    t = text.strip().lower()
    if t in RECHECK_KEYWORDS or (t.startswith("recheck") and len(t.split()) <= 3):
        return MessageResponse(reply=STR["rechecked_same"][L],
                               done=True, results=build_results(session["profile"], L), transitions=[])
    scored = []
    for f in UPDATE_FIELD_ORDER:
        llm_hit = try_llm_extract(f, text)
        v, c = llm_hit if llm_hit else extract_field(f, text)
        if v is None or not _valid_field_value(f, v):
            continue
        scored.append([f, v, c])
    # income-vs-funding disambiguation: bare "8 lakhs" fits both parsers —
    # surrounding words decide, otherwise income (earlier order) wins ties
    inc = next((s for s in scored if s[0] == "income_band"), None)
    fun = next((s for s in scored if s[0] == "funding_need"), None)
    if inc and fun:
        if re.search(r"fund|loan|need|require|borrow|project|cost|capital", t):
            scored.remove(inc)
        elif re.search(r"income|salary|earn|family|household|per year|p\.a|wage", t):
            scored.remove(fun)
        else:
            scored.remove(fun)
    # a message may carry several updates ("25-year-old student") — apply every
    # high-confidence one; fall back to the single best above threshold
    strong = [s for s in scored if s[2] >= 0.8]
    picked = strong or (sorted(scored, key=lambda s: -s[2])[:1] if scored else [])
    picked = [p for p in picked if p[2] >= 0.55]
    if not picked:
        return MessageResponse(
            reply=STR["couldnt_tell"][L],
            done=True, results=build_results(session["profile"], L), transitions=[])
    old_evals = evaluate_all(get_schemes(), session["profile"])
    notes = []
    for f, v, _c in picked:
        if session["profile"].get(f) != v:
            notes.append(f"{field_label(f, L)} → '{v}'")
        session["profile"][f] = v
        if f not in session.get("asked", []):
            session["asked"].append(f)
    new_evals = evaluate_all(get_schemes(), session["profile"])
    trans = diff_statuses(old_evals, new_evals)
    results = build_results(session["profile"], L)
    if notes:
        changed_note = STR["updated"][L].format(updates=", ".join(notes))
    else:
        changed_note = STR["noted_same"][L]
    return MessageResponse(reply=changed_note + transition_message(trans, L),
                           done=True, results=results, transitions=trans)


@app.post("/sessions/{sid}/messages", response_model=MessageResponse)
def post_message(sid: str, req: MessageRequest, user: Dict[str, Any] = Depends(current_user)):
    session = _get_session(sid, user)

    def _finish(results: Dict[str, Any], ack: str = "") -> MessageResponse:
        session["done"] = True
        try:
            history_store.save(user["id"], results.get("profile", {}), results)
        except Exception:
            pass
        n_e = len(results["eligible"])
        L = _lang(session)
        if L == "en":
            core = f"Thanks! I found {n_e} scheme(s) you qualify for. " + DISCLAIMER
        else:
            core = STR["found"][L].format(n=n_e)
        return MessageResponse(reply=(ack + " " + core).strip(), done=True, results=results)

    text = req.message.strip()
    if not text:
        raise HTTPException(422, "empty message")
    if len(text) > 2000:
        raise HTTPException(422, "message too long")
    # done-mode: results already delivered — every new message is a re-check update
    if session.get("done"):
        session["pending_confirm"] = None
        return _handle_update(session, text)
    # allow "skip"
    if text.strip().lower() in ("skip", "prefer not to say", "don't know", "dont know",
                                   "छोड़ें", "छोड़ो", "बताना नहीं चाहते", "पता नहीं",
                                   "ಬಿಟ್ಟುಬಿಡಿ", "ಬಿಡಿ", "ಹೇಳಲು ಇಷ್ಟವಿಲ್ಲ", "ಗೊತ್ತಿಲ್ಲ"):
        session["pending_confirm"] = None
        q0 = next_field(session["profile"], get_schemes(), session["asked"])
        if q0:
            session["asked"].append(q0["field"])
            session["profile"][q0["field"]] = None
        nxt = next_field(session["profile"], get_schemes(), session["asked"])
        if nxt is None or is_done(session["profile"]):
            return _finish(build_results(session["profile"], _lang(session)))
        return _ask_turn(session, nxt, STR["skipped"][_lang(session)])
    out = _process_reply(session, text, _lang(session))
    if out.get("redirect"):
        q = next_field(session["profile"], get_schemes(), session["asked"])
        if q is None:
            return _finish(build_results(session["profile"], _lang(session)), out["reply"].strip())
        return _ask_turn(session, q, out["reply"].strip())
    if out.get("confirming"):
        L = _lang(session)
        return MessageResponse(reply=out["reply"], field=out["field"],
                               options=["Yes", "No"], option_labels=STR["yes_no"][L],
                               progress=progress_text(session["profile"], L))
    if out.get("confirm_no"):
        q = next_field(session["profile"], get_schemes(), session["asked"])
        return _ask_turn(session, {"field": out["field"], **q} if q else {"field": out["field"]}, out["reply"])
    if out.get("retry"):
        q = next_field(session["profile"], get_schemes(), session["asked"])
        return _ask_turn(session, q or {"field": out["field"]}, out["reply"])
    # stored / skipped / confirmed → next question or results
    nxt = next_field(session["profile"], get_schemes(), session["asked"])
    L = _lang(session)
    ack = (out.get("note") or "").strip() or (STR["ack"][L] if out.get("stored") or out.get("confirmed") or out.get("skipped") else "")
    if nxt is None or is_done(session["profile"]):
        return _finish(build_results(session["profile"], L), ack)
    # v1 asks at most 8 — the question text travels in `question`; keep `reply` a pure acknowledgement
    return _ask_turn(session, nxt, ack)


@app.get("/history")
def history_list(user: Dict[str, Any] = Depends(current_user)):
    return {"items": history_store.list_for(user["id"])}


@app.get("/history/{hid}")
def history_get(hid: int, user: Dict[str, Any] = Depends(current_user)):
    r = history_store.get(user["id"], hid)
    if not r:
        raise HTTPException(404, "no such saved result")
    return r


@app.get("/sessions/{sid}/results")
def get_results(sid: str, user: Dict[str, Any] = Depends(current_user)):
    session = _get_session(sid, user)
    return build_results(session["profile"], _lang(session))


@app.get("/sessions/{sid}/compare")
def compare_schemes(sid: str, ids: str = "", user: Dict[str, Any] = Depends(current_user)):
    """Side-by-side comparison of 2–3 schemes: ?ids=pmegp,mudra-kishor,standup-india"""
    session = _get_session(sid, user)
    picked = [i.strip() for i in (ids or "").split(",") if i.strip()]
    try:
        return build_comparison(get_schemes(),
                                evaluate_all(get_schemes(), session["profile"]), picked,
                                _lang(session))
    except ValueError as e:
        raise HTTPException(422, str(e))
    except LookupError as e:
        raise HTTPException(404, str(e))


@app.patch("/sessions/{sid}/profile")
def patch_profile(sid: str, req: ProfilePatchRequest, user: Dict[str, Any] = Depends(current_user)):
    session = _get_session(sid, user)
    if req.field not in FIELD_TO_QUESTION:
        raise HTTPException(422, f"unknown field {req.field}")
    if not _valid_field_value(req.field, req.value):
        raise HTTPException(422, f"invalid value for {req.field}")
    old_evals = evaluate_all(get_schemes(), session["profile"])
    session["profile"][req.field] = req.value
    if req.field in session.get("asked", []):
        pass
    else:
        session["asked"].append(req.field)
    new_evals = evaluate_all(get_schemes(), session["profile"])
    return {"profile": session["profile"], "results": build_results(session["profile"], _lang(session)),
            "transitions": diff_statuses(old_evals, new_evals)}


def _scheme_tag(s: dict) -> str:
    for c in s.get("criteria", []):
        if c["field"] == "state" and c.get("operator") == "equals" and isinstance(c.get("value"), str):
            return c["value"].upper()
    return "CENTRAL"


@app.get("/schemes")
def list_schemes():
    """Public coverage list powering the landing page grid (no auth needed)."""
    return [{"id": s["id"], "name": s["name"], "tag": _scheme_tag(s),
             "url": s.get("url", ""), "benefit": s.get("benefit_summary", "")}
            for s in get_schemes()]


@app.get("/schemes/{scheme_id}")
def scheme_detail(scheme_id: str, lang: str = "en"):
    for s in get_schemes():
        if s["id"] == scheme_id:
            d = dict(s)
            d["stale_warning"] = _stale_warning(s)
            d["deadline"] = deadline_status(s.get("application_window"), lang=lang)
            return d
    raise HTTPException(404, "scheme not in curated dataset — try MyScheme.gov.in for others.")


@app.get("/health")
def health():
    return {"status": "ok", "schemes": len(get_schemes())}


# ---- serve demo UI ----
ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
if STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    idx = ROOT / "static" / "landing.html"
    if idx.exists():
        return idx.read_text(encoding="utf-8")
    return "<h1>Scheme-Matching Assistant API</h1><p>See /docs</p>"


@app.get("/login", response_class=HTMLResponse)
def login_page():
    p = ROOT / "static" / "login.html"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return "<h1>Login</h1><p>See /docs</p>"


@app.get("/chat", response_class=HTMLResponse)
def chat_page():
    p = ROOT / "static" / "chat.html"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return "<h1>Chat</h1><p>See /docs</p>"
