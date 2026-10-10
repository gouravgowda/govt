"""Deadline calendar: recurring annual application windows -> live status.

Each scheme may carry an optional ``application_window``::

    {"opens": "07-01", "closes": "10-31", "note": "..."}

MM-DD pairs recur every year, so badges never go stale the way fixed dates do.
All date math is pure and injectable (``today`` param) for deterministic tests.

States: ``open`` (closes in N days) / ``upcoming`` (opens in N days) /
``closed`` (reopens on date). Tiers drive badge colour: urgent (<=7d),
soon (<=30d), open, upcoming, closed.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, Optional

_MD_RE = re.compile(r"^(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$")


def parse_md(s: str) -> tuple[int, int]:
    if not isinstance(s, str) or not _MD_RE.match(s):
        raise ValueError(f"bad MM-DD date: {s!r}")
    m, d = int(s[:2]), int(s[3:])
    date(2024, m, d)  # validate real calendar day (2024 is a leap year)
    return m, d


def validate_window(w: dict) -> None:
    if not isinstance(w, dict) or "opens" not in w or "closes" not in w:
        raise ValueError(f"application_window needs opens+closes MM-DD: {w!r}")
    parse_md(w["opens"])
    parse_md(w["closes"])


def _fmt(d: date) -> str:
    return d.strftime("%d %b").lstrip("0")


def deadline_status(window: Optional[dict], today: Optional[date] = None,
                    lang: str = "en") -> Optional[Dict[str, Any]]:
    """Return badge payload, or None when the scheme has no window."""
    if not window:
        return None
    validate_window(window)
    from .i18n import DEADLINE, lang_or_default
    lang = lang_or_default(lang)
    today = today or date.today()
    om, od = parse_md(window["opens"])
    cm, cd = parse_md(window["closes"])
    y = today.year
    note = window.get("note", "")

    def _label(kind: str, **kw) -> str:
        if lang == "en":
            return kw["en"]
        return DEADLINE[kind][lang].format(**kw)

    if (om, od) <= (cm, cd):
        # same-year window, e.g. Jul 1 – Oct 31
        start, end = date(y, om, od), date(y, cm, cd)
        if today < start:
            days = (start - today).days
            return {"state": "upcoming", "tier": "upcoming", "days": days,
                    "label": _label("opens_in", n=days, date=_fmt(start),
                                    en=f"Opens in {days} day{'s' if days != 1 else ''} — {_fmt(start)}"),
                    "date": start.isoformat(), "note": note}
        if today <= end:
            days = (end - today).days
            tier = "urgent" if days <= 7 else ("soon" if days <= 30 else "open")
            if days == 0:
                label = _label("closes_today", en="Closes today")
            else:
                label = _label("closes_in", n=days,
                               en=f"Closes in {days} day{'s' if days != 1 else ''}")
            return {"state": "open", "tier": tier, "days": days, "label": label,
                    "date": end.isoformat(), "note": note}
        nxt = date(y + 1, om, od)
        return {"state": "closed", "tier": "closed", "days": (nxt - today).days,
                "label": _label("closed_reopens", date=_fmt(nxt), en=f"Closed — reopens {_fmt(nxt)}"),
                "date": nxt.isoformat(), "note": note}
    else:
        # wraps new year, e.g. Nov 15 – Feb 28
        if today >= date(y, om, od):
            end = date(y + 1, cm, cd)
        elif today <= date(y, cm, cd):
            end = date(y, cm, cd)
        else:
            start = date(y, om, od)
            days = (start - today).days
            return {"state": "upcoming", "tier": "upcoming", "days": days,
                    "label": _label("opens_in", n=days, date=_fmt(start),
                                    en=f"Opens in {days} day{'s' if days != 1 else ''} — {_fmt(start)}"),
                    "date": start.isoformat(), "note": note}
        days = (end - today).days
        tier = "urgent" if days <= 7 else ("soon" if days <= 30 else "open")
        if days == 0:
            label = _label("closes_today", en="Closes today")
        else:
            label = _label("closes_in", n=days,
                           en=f"Closes in {days} day{'s' if days != 1 else ''}")
        return {"state": "open", "tier": tier, "days": days, "label": label,
                "date": end.isoformat(), "note": note}
