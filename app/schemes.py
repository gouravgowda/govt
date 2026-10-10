"""Scheme store: load + validate versioned JSON dataset."""
from __future__ import annotations

import json, os
from pathlib import Path
from typing import List

REQUIRED_KEYS = ["id", "name", "body", "benefit_summary", "criteria", "url", "last_verified", "source"]
VALID_OPERATORS = {"equals", "in", "not_in", "lte", "gte", "between"}


def default_data_path() -> Path:
    env = os.getenv("DATA_PATH", "data/schemes.json")
    p = Path(env)
    if not p.is_absolute():
        # resolve relative to repo root (parent of app/)
        root = Path(__file__).resolve().parent.parent
        p = root / env
    return p


def validate_scheme(s: dict) -> List[str]:
    errs = []
    for k in REQUIRED_KEYS:
        if not s.get(k):
            errs.append(f"{s.get('id', '?')}: missing '{k}' (source URL + verified date are mandatory)")
    for c in s.get("criteria", []):
        if c.get("operator") not in VALID_OPERATORS:
            errs.append(f"{s.get('id')}: bad operator {c.get('operator')}")
        if "field" not in c or "value" not in c:
            errs.append(f"{s.get('id')}: criterion needs field+value: {c}")
    if "application_window" in s:
        try:
            from .deadlines import validate_window
            validate_window(s["application_window"])
        except ValueError as e:
            errs.append(f"{s.get('id')}: {e}")
    return errs


def load_schemes(path: str | Path | None = None) -> List[dict]:
    if path:
        files = [Path(path)]
    else:
        base = default_data_path()
        # base file plus any schemes_*.json extensions, merged in sorted order
        files = [base] + sorted(base.parent.glob("schemes_*.json"))
    schemes: List[dict] = []
    for p in files:
        data = json.loads(p.read_text(encoding="utf-8"))
        batch = data if isinstance(data, list) else data.get("schemes", [])
        schemes.extend(batch)
    errs: List[str] = []
    seen = set()
    for s in schemes:
        errs.extend(validate_scheme(s))
        if s.get("id") in seen:
            errs.append(f"duplicate scheme id: {s.get('id')}")
        seen.add(s.get("id"))
    if errs:
        raise ValueError("scheme validation failed:\n" + "\n".join(errs))
    return schemes
