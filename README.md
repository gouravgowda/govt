# SchemeSetu — Government Scheme-Matching Assistant

India has hundreds of central and state government schemes — for entrepreneurs, students, farmers, women, seniors — but most eligible people never apply because they can't tell whether they qualify or can't parse the eligibility language on official portals.

**SchemeSetu** is a conversational web app that asks **5–8 simple questions**, checks the answers against a **deterministic, auditable rules engine**, and returns a **ranked list of schemes the person qualifies for** — each with a plain-language reason, required documents, and an official apply link. It also flags **near-misses** (schemes you *almost* qualify for) with the exact gap and how to close it, then lets you **re-check in one tap** after fixing it.

- 🎯 Rule-backed matches — every decision traces to named criteria and your answers
- 🔶 Near-miss gaps with one-tap fixes ("I registered my business" → re-check → eligible)
- 📅 Application-window badges ("Closes in 21 days")
- ⚖️ Side-by-side comparison of 2–3 schemes
- 🌐 English, Hindi (हिंदी) and Kannada (ಕನ್ನಡ) — questions, answers, results
- 📚 57 schemes across 13 states and counting; the landing-page coverage grid builds itself from the dataset

> **Guidance only.** Final eligibility is decided by the scheme authority. The app never asks for Aadhaar, PAN, or bank details, and every result links to its official source with a last-verified date.

---

## Contents

1. [Quickstart](#quickstart)
2. [How it works (user journey)](#how-it-works-user-journey)
3. [Features](#features)
4. [API reference](#api-reference)
5. [Configuration](#configuration)
6. [Architecture & project layout](#architecture--project-layout)
7. [Eligibility model](#eligibility-model)
8. [Scheme coverage](#scheme-coverage)
9. [Adding a scheme (no code change)](#adding-a-scheme-no-code-change)
10. [Testing](#testing)
11. [Privacy & security](#privacy--security)
12. [Roadmap](#roadmap)

---

## Quickstart

Requirements: Python 3.10+.

```powershell
# 1. install
python -m pip install -r requirements.txt

# 2. verify (40 tests)
python -m pytest -q

# 3. run (pick any free port)
python -m uvicorn app.main:app --port 8081
```

Then open:

| Page | URL | What |
|---|---|---|
| Landing | `http://127.0.0.1:8081/` | Hero, how-it-works, live scheme-coverage grid |
| Login / Signup | `http://127.0.0.1:8081/login` | Free account (name + email + password) |
| Assistant | `http://127.0.0.1:8081/chat` | The chat + results (login required) |
| API docs | `http://127.0.0.1:8081/docs` | Interactive Swagger UI |

On macOS/Linux use `python3` and `/` paths — everything else is identical. Copy `.env.example` to `.env` only if you want to override defaults (see [Configuration](#configuration)); the app runs with zero setup out of the box.

---

## How it works (user journey)

1. **Sign up / log in** — email + password or Google (via Firebase), falling back to the built-in local account system when Firebase isn't configured. Chat sessions use bearer tokens (Firebase ID tokens in production).
2. **Pick a language** — EN | हिंदी | ಕನ್ನಡ toggle in the chat header. Questions, option chips, replies, badges and explanations all switch; option chips show translated labels but submit canonical values.
3. **Answer 5–8 questions, one at a time** — the flow adapts to your life stage:
   - *Student* → education level + income (scholarships), never business-loan questions
   - *Senior / farmer / salaried* → short 6-question flow (pensions, PM-KISAN, insurance)
   - *Entrepreneur / artisan / street vendor* → sector, funding need, registration (MUDRA, PMEGP, Stand-Up India…)
   
   Free-text answers are understood ("24 years old", "मैं 24 साल का", "3 lakhs", "कर्नाटक"); uncertain reads are confirmed with a Yes/No check; `skip` works on any non-essential question.
4. **Get ranked results** in three groups:
   - ✅ **Schemes you qualify for** — benefit, 2–3 reason lines, documents, apply channel, deadline badge, official link
   - 🔶 **Almost eligible** — the exact failed check, gap size, how to fix it, plus a one-tap fix button
   - ❓ **Need more info** — what's missing and how to settle it
5. **Close the loop** — tap a fix button or type what changed ("I got my DPIIT certificate") → the engine re-runs and confirms, e.g. `🎉 Startup India Seed Fund moved to Eligible!`
6. **Compare & keep** — select 2–3 schemes for a side-by-side table (benefit, deadline, documents, effort); print or revisit past checks from History.

---

## Features

- **Account system** — signup/login/logout, per-account sessions (cross-account access is rejected), saved result history.
- **Adaptive intake** — most decisive questions first (funding before trivia for entrepreneurs); low-confidence reads confirmed; earlier answers editable; contradictions resolve latest-wins.
- **Deterministic eligibility engine** — pure-Python rules over a versioned JSON dataset; identical profiles always give identical outcomes. Six operators: `equals`, `in`, `not_in`, `lte`, `gte`, `between`.
- **Four outcome statuses** — `eligible`, `near_miss` (1–2 failed checks, all fixable), `possibly_eligible` (nothing failed, something unknown), `not_eligible`. `"prefer not to say"` is treated as unknown, never as a failure.
- **Transparent ranking** — weighted score (match completeness .35, benefit size .25, funding-need fit .20, category fit .10, ease of access .10), tunable via `RANK_WEIGHTS_JSON` with no code change.
- **Deadline calendar** — schemes carry recurring annual windows (`opens`/`closes` as MM-DD, so badges never go stale): open / closing-soon / urgent / upcoming / closed-reopens states.
- **Re-check loop** — natural-language updates or one-tap fix buttons recompute everything and report status transitions.
- **Side-by-side comparison** — 2–3 schemes across status, benefit (₹ L/Cr), deadline, documents, effort, requirement checkmarks, with data-derived callouts (highest benefit, fewest documents, easiest to apply).
- **Trilingual UI** — English/Hindi/Kannada string tables; Hindi/Kannada free-text understanding (Indic digits, लाख/ಲಕ್ಷ units, keywords, yes/no, skip phrases). Scheme records stay in English as the official data.
- **Freshness & honesty** — every record carries a source URL + last-verified date; stale records show warnings; out-of-dataset schemes are declined with a pointer to MyScheme.gov.in, never invented.

---

## API reference

Auth: `Authorization: Bearer <token>` on all `/sessions*` routes. `/schemes*` and `/health` are public.

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/signup` | `{name, email, password}` → `{token, name, email}` (409 on duplicate) |
| POST | `/auth/login` | `{email, password}` → `{token, name, email}` (401 on bad credentials) |
| GET | `/auth/me` | Current account info |
| POST | `/auth/logout` | Revoke the bearer token |
| POST | `/sessions?lang=en\|hi\|kn` | Create session → greeting + first question (+ translated `option_labels`) |
| POST | `/sessions/{id}/messages` | `{"message": "..."}` → next turn, or `done:true` + `results` (+ `transitions` after updates) |
| GET | `/sessions/{id}/results` | Ranked matches + near-misses for the saved profile |
| PATCH | `/sessions/{id}/profile` | `{"field": "...", "value": ...}` → recompute; returns `profile`, `results`, `transitions` |
| GET | `/sessions/{id}/compare?ids=a,b,c` | Side-by-side table for 2–3 scheme ids |
| GET | `/history` · `/history/{hid}` | Saved past result summaries for the account |
| GET | `/schemes` | Public coverage list `{id, name, tag, url, benefit}` (powers the landing grid) |
| GET | `/schemes/{scheme_id}` | Full record + freshness warning + deadline status |
| GET | `/health` | `{"status": "ok", "schemes": N}` |

---

## Configuration

Environment variables (all optional; see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DATA_PATH` | `data/schemes.json` | Base dataset file; `schemes_*.json` siblings auto-merge |
| `SESSION_TTL_SECONDS` | `3600` | Chat session lifetime |
| `STALENESS_DAYS` | `180` | Records older than this show a review warning |
| `RANK_WEIGHTS_JSON` | (built-in weights) | e.g. `{"benefit": 0.4, "ease": 0.2}` to retune ranking |
| `AUTH_DB_PATH` | `users.db` | SQLite account store location |
| `AUTH_BACKEND` | `auto` | `firebase` (require key) · `local` (force SQLite) · `auto` (key present → Firebase) |
| `AUTH_TOKEN_TTL` | 30 days (s) | Bearer token lifetime |

---

## Architecture & project layout

```
app/main.py        FastAPI routes, session store, conversation flow, results builder
app/models.py      Pydantic schemas (profile, scheme, API payloads)
app/engine.py      Deterministic eligibility engine (operators, 4 statuses, gaps)
app/ranking.py     Transparent weighted scoring
app/extraction.py  Free-text → typed values (pattern matching, EN/HI/KN, confidence scores)
app/explanation.py Per-match reasoning rendered from engine output (templated, faithful)
app/graph.py       Adaptive question selection (most-decisive-first, stage-aware)
app/schemes.py     Dataset loader + validator (URL/date mandatory, duplicate ids rejected)
app/deadlines.py   Recurring application-window → open/upcoming/closed badges
app/recheck.py     Status diffs + one-tap fix actions for near-misses
app/compare.py     Side-by-side table builder
app/i18n.py        EN/HI/KN string tables (questions, options, replies, badges)
app/auth.py        PBKDF2 password hashing + SQLite users + bearer tokens (local fallback)
app/firebase_auth.py Firebase ID-token verification + Firestore users/history (primary when a key is present)
app/history.py     Saved result summaries (SQLite fallback; Firestore in production)
app/history.py     Saved result summaries per account
data/schemes.json            Base dataset (13 records)
data/schemes_extended.json   44 more: credit/insurance/pension/scholarship + state schemes
static/landing.html          Landing page (coverage grid renders live from /schemes)
static/login.html            Signup/login form
static/chat.html             Chat + results + compare + history UI (trilingual)
tests/                       40 tests: engine, fixtures, ranking, faithfulness,
                             extraction, auth, deadlines, re-check, compare, i18n
```

Request flow: `chat.html → POST /messages → extract value (+confidence) → update profile → next question (or, when done) → rules engine → ranking → explanations → cards`. The engine is the sole decider; every other module only reads its output.

---

## Eligibility model

Each scheme is a list of criteria: `{field, operator, value, required, actionable, fix_hint, label}`.

- Per-check verdicts: `met` / `not_met` / `unknown` (missing or declined answer) / `na`.
- Scheme verdicts: **eligible** (all required met) · **near_miss** (1–2 required failed, all actionable) · **possibly_eligible** (none failed, some unknown) · **not_eligible** (anything else).
- Profile fields: age, state, social category, gender, occupation/stage, sector, education level, income band, funding need, business registration, first-time borrower.

---

## Scheme coverage

57 schemes, all with official source links and verification dates (landing page renders this list live from `/schemes`):

**Central (29)** — PMEGP · MUDRA Shishu / Kishor / Tarun · Stand-Up India · Startup India Seed Fund · PM Vishwakarma · NSP Post-Matric Scholarship · PM-KISAN · IGNOAPS Old-Age Pension · Atal Pension Yojana · PM Jeevan Jyoti Bima · CGTMSE Credit Guarantee · PM SVANidhi (street vendors) · PMFME food processing · DAY-NRLM Aajeevika (women SHGs) · Kisan Credit Card · PM Fasal Bima (crop insurance) · PM Suraksha Bima (accident cover) · PM-SYM unorganised-workers pension · Central Sector Scholarship · AICTE Pragati (girls in tech) · PM-YASASVI (OBC) · Free Coaching (SC/OBC) · PM Vaya Vandana (seniors) · Rashtriya Vayoshri (BPL senior aids) · Senior Citizens Savings Scheme · Cent Kalyani (women entrepreneurs) · National Apprenticeship (stipend support)

**State (28)** — *Karnataka:* Udyogini, Elevate startup grants, Kaushalya skilling · *Maharashtra:* MAVIM Tejaswini, Lek Ladki, Yuva Karya Prashikshan internships · *Tamil Nadu:* TANSEED, Pudhumai Penn · *Telangana:* Kalyana Lakshmi, Rythu Bharosa, Dalit Bandhu · *Kerala:* Kudumbashree, Vidya Samunnathi · *Delhi:* Merit Scholarship · *Uttar Pradesh:* Kanya Sumangala, Yuva Swarozgar, ODOP · *Gujarat:* Vahli Dikri, Mahila Utkarsh · *Rajasthan:* Anuprati coaching · *West Bengal:* Kanyashree, Lakshmir Bhandar, Student Credit Card · *Bihar:* Mukhyamantri Udyami, Kanya Utthan · *Madhya Pradesh:* Ladli Laxmi, Udyam Kranti · *Odisha:* Mission Shakti

---

## Adding a scheme (no code change)

Append one record to `data/schemes.json` (or a new `data/schemes_<name>.json`, auto-merged):

```json
{
  "id": "example-scheme",
  "name": "Example Scheme",
  "body": "Administering body",
  "benefit_summary": "What the applicant gets",
  "benefit_amount": 500000,
  "ease_score": 3,
  "category_boost": ["female"],
  "criteria": [
    {"field": "age", "operator": "between", "value": [18, 60],
     "required": true, "actionable": false, "label": "Age 18–60"},
    {"field": "business_registered", "operator": "equals", "value": true,
     "required": true, "actionable": true,
     "fix_hint": "Register on Udyam — it takes a day.",
     "label": "Registered unit"}
  ],
  "application_window": {"opens": "07-01", "closes": "10-31",
    "note": "Typical annual window — confirm exact dates on the official portal."},
  "documents": ["Aadhaar", "Project report"],
  "channel": "Where/how to apply",
  "url": "https://official-portal.example/",
  "last_verified": "2026-10-10",
  "source": "official-portal.example + MyScheme.gov.in"
}
```

Rules: `url` + `last_verified` are mandatory (records without them are rejected at startup); mark closable gaps `actionable: true` with a concrete `fix_hint`; then run `pytest` — schema, fixture, and faithfulness tests validate the addition.

---

## Testing

```powershell
python -m pytest -q        # 40 tests, all offline, no keys needed
```

Coverage: rules-engine operators · dataset schema validation · 11 persona fixtures with expected eligible/near-miss/not-eligible outcomes per scheme · ranking determinism · explanation faithfulness (every claim maps to an engine criterion) · free-text extraction (EN/HI/KN) · auth signup/login/token/ownership · deadline open/upcoming/closed/wrap boundaries · re-check transitions + fix actions · compare validation · i18n key completeness (every question/option/reply in all 3 languages) · Hindi + Kannada end-to-end sessions.

---

## Privacy & security

- No Aadhaar, PAN, bank, or document uploads — asked nowhere, stored nowhere.
- **Accounts:** Firebase Auth (email + Google) in production; PBKDF2-hashed (200k rounds, per-user salt) local SQLite accounts as offline fallback. Bearer tokens random 256-bit, revocable, 30-day TTL (local) or 1-hour Firebase ID tokens.
- Sessions live in memory with TTL expiry and per-account ownership checks (403 on cross-account access).
- Income is collected as bands, never exact figures; sensitive fields accept skips.
- Secrets (`.env`, `users.db`, `firebase-key.json`) are git-ignored; the suite runs fully offline.

---

## Roadmap

- More states + schemes (each is one JSON record + tests)
- Document-checklist generator and printable application summary
- Voice input; more regional languages
- Application-window reminders and renewal nudges
- Intermediary (CSC/NGO) multi-profile mode
- Automated change detection on official scheme pages to flag stale records

---

*SchemeSetu is an independent guidance tool — not a government website, and it does not file applications. Results are indicative; the scheme authority's decision is final, and the official source linked on every card always prevails.*
