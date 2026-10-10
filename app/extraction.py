"""Free-text -> typed field extraction. Rule-based baseline; LLM bumps confidence when configured."""
from __future__ import annotations

import re
from typing import Any, Optional, Tuple

STATES = ["karnataka", "maharashtra", "tamil nadu", "telangana", "kerala", "delhi",
          "uttar pradesh", "gujarat", "rajasthan", "west bengal", "punjab", "haryana",
          "bihar", "madhya pradesh", "andhra pradesh", "odisha", "assam", "goa", "other"]

CATEGORY_MAP = {"general": "General", "obc": "OBC", "sc": "SC", "st": "ST",
                "ews": "EWS", "prefer not to say": "prefer not to say", "skip": "prefer not to say",
                "बताना नहीं चाहते": "prefer not to say", "ಹೇಳಲು ಇಷ್ಟವಿಲ್ಲ": "prefer not to say"}
GENDER_MAP = {"female": "Female", "woman": "Female", "women": "Female", "girl": "Female",
              "लड़की": "Female", "महिला": "Female", "ಹುಡುಗಿ": "Female", "ಮಹಿಳೆ": "Female",
              "male": "Male", "man": "Male", "लड़का": "Male", "पुरुष": "Male",
              "ಹುಡುಗ": "Male", "ಪುರುಷ": "Male", "other": "Other",
              "prefer not to say": "prefer not to say", "skip": "prefer not to say",
              "बताना नहीं चाहते": "prefer not to say", "ಹೇಳಲು ಇಷ್ಟವಿಲ್ಲ": "prefer not to say"}
# NOTE: order matters — specific/longer keys before their substrings
# ("नया व्यवसाय" before "व्यवसाय", "परास्नातक" before "स्नातक").
STAGE_MAP = {"student": "student", "studying": "student", "college": "student",
             "school": "student", "university": "student", "pupil": "student",
             "छात्र": "student", "ವಿದ್ಯಾರ್ಥಿ": "student",
             "planning": "aspiring entrepreneur", "aspiring": "aspiring entrepreneur",
             "start": "aspiring entrepreneur", "idea": "aspiring entrepreneur",
             "नया व्यवसाय": "aspiring entrepreneur", "शुरू": "aspiring entrepreneur",
             "ಹೊಸ ವ್ಯಾಪಾರ": "aspiring entrepreneur",
             "running": "existing business", "existing": "existing business", "own a": "existing business",
             "shop": "existing business", "business": "existing business",
             "व्यवसाय": "existing business", "व्यापार": "existing business",
             "ವ್ಯಾಪಾರ": "existing business",
             "farm": "farmer", "farmer": "farmer", "किसान": "farmer", "ರೈತ": "farmer",
             "खेती": "farmer",
             "salaried": "salaried", "job": "salaried",
             "employed": "salaried", "employee": "salaried",
             "नौकरी": "salaried",
             "artisan": "artisan", "weaver": "artisan", "carpenter": "artisan", "craft": "artisan",
             "कारीगर": "artisan", "ಕುಶಲಕರ್ಮಿ": "artisan",
             "retired": "retired", "retiree": "retired", "senior citizen": "retired",
             "old age": "retired", "pensioner": "retired",
             "सेवानिवृत्त": "retired", "ನಿವೃತ್ತ": "retired",
             "vendor": "street vendor", "street vendor": "street vendor", "hawker": "street vendor",
             "rehdi": "street vendor", "thela": "street vendor", "cart vendor": "street vendor",
             "रेहड़ी": "street vendor", "ಬೀದಿ ವ್ಯಾಪಾರಿ": "street vendor",
             "homemaker": "homemaker", "housewife": "homemaker", "househusband": "homemaker",
             "stay at home": "homemaker", "गृहिणी": "homemaker", "ಗೃಹಿಣಿ": "homemaker",
             "unemployed": "unemployed", "looking for work": "unemployed",
             "बेरोज़गार": "unemployed", "बेरोजगार": "unemployed", "ನಿರುದ್ಯೋಗಿ": "unemployed",
             "between jobs": "unemployed"}
EDU_MAP = {"school": "school", "class 10": "school", "class 12": "school", "12th": "school",
           "स्कूल": "school", "ಶಾಲೆ": "school",
           "postgraduate": "postgraduate", "postgrad": "postgraduate",
           "परास्नातक": "postgraduate", "ಸ್ನಾತಕೋತ್ತರ": "postgraduate",
           "master": "postgraduate", "phd": "postgraduate",
           "undergraduate": "undergraduate", "undergrad": "undergraduate", "bachelor": "undergraduate",
           "स्नातक": "undergraduate", "ಪದವಿ": "undergraduate",
           "college": "undergraduate", "b.tech": "undergraduate", "btech": "undergraduate", "degree": "undergraduate",
           "diploma": "diploma", "iti": "diploma", "polytechnic": "diploma", "vocational": "diploma",
           "डिप्लोमा": "diploma", "ಡಿಪ್ಲೊಮಾ": "diploma"}
SECTOR_MAP = {"manufacturing": "manufacturing", "manufacture": "manufacturing", "factory": "manufacturing",
              "निर्माण": "manufacturing", "ಉತ್ಪಾದನೆ": "manufacturing",
              "service": "services", "services": "services", "सेवा": "services", "सेवाएँ": "services",
              "ಸೇವೆ": "services", "ಸೇವೆಗಳು": "services",
              "trading": "trading", "trade": "trading",
              "shop": "trading", "दुकान": "trading", "ಅಂಗಡಿ": "trading",
              "agriculture": "agriculture", "farm": "agriculture",
              "कृषि": "agriculture", "खेती": "agriculture", "ಕೃಷಿ": "agriculture",
              "tech": "tech", "software": "tech", "it ": "tech", "startup": "tech",
              "तकनीक": "tech", "ತಂತ್ರಜ್ಞಾನ": "tech",
              "handicraft": "handicraft", "craft": "handicraft", "handloom": "handicraft",
              "हस्तशिल्प": "handicraft", "ಕರಕುಶಲ": "handicraft"}
HI_STATE_MAP = {"कर्नाटक": "Karnataka", "महाराष्ट्र": "Maharashtra", "तमिलनाडु": "Tamil Nadu",
                "तेलंगाना": "Telangana", "केरल": "Kerala", "दिल्ली": "Delhi",
                "उत्तर प्रदेश": "Uttar Pradesh", "यूपी": "Uttar Pradesh", "गुजरात": "Gujarat",
                "राजस्थान": "Rajasthan", "पश्चिम बंगाल": "West Bengal", "बंगाल": "West Bengal",
                "पंजाब": "Punjab", "हरियाणा": "Haryana", "बिहार": "Bihar",
                "मध्य प्रदेश": "Madhya Pradesh", "एमपी": "Madhya Pradesh",
                "आंध्र प्रदेश": "Andhra Pradesh", "ओडिशा": "Odisha", "उड़ीसा": "Odisha",
                "असम": "Assam", "गोवा": "Goa"}
KN_STATE_MAP = {"ಕರ್ನಾಟಕ": "Karnataka", "ಮಹಾರાષ್ಟ್ರ": "Maharashtra", "ತಮಿಳುನಾಡು": "Tamil Nadu",
                "ತೆಲಂಗಾಣ": "Telangana", "ಕೇರಳ": "Kerala", "ದೆಹಲಿ": "Delhi",
                "ಉತ್ತರ ಪ್ರದೇಶ": "Uttar Pradesh", "ಗುಜರಾತ್": "Gujarat",
                "ರಾಜಸ್ಥಾನ": "Rajasthan", "ಪಶ್ಚಿಮ ಬಂಗಾಳ": "West Bengal",
                "ಪಂಜಾಬ್": "Punjab", "ಹರಿಯಾಣ": "Haryana", "ಬಿಹಾರ": "Bihar",
                "ಮಧ್ಯಪ್ರದೇಶ": "Madhya Pradesh", "ಆಂಧ್ರಪ್ರದೇಶ": "Andhra Pradesh",
                "ಒಡಿಶಾ": "Odisha", "ಅಸ್ಸಾಂ": "Assam", "ಗೋವಾ": "Goa"}
YES_WORDS = r"yes|yeah|yep|हाँ|हां|जी|ಹೌದು|ಹೌದ"
NO_WORDS = r"no\b|not\b|n't|never|नहीं|नही|ना\b|ಇಲ್ಲ|ಬೇಡ"


_DIGITS = str.maketrans("०१२३४५६७८९೦೧೨೩೪೫೬೭೮೯", "01234567890123456789")


def _low(t: str) -> str:
    return t.strip().lower().translate(_DIGITS)


# Hindi/Kannada units -> ascii before number parsing ("2 लाख" -> "2 lakh")
_UNIT_WORDS = {
    # NOTE: no bare "रू"/"ರೂ" — they occur inside ordinary words (ज़रूर).
    # Bare numbers are handled by the rupees fallback in the parsers.
    "करोड़": "crore", "करोड": "crore", "लाख": "lakh", "हजार": "thousand",
    "रुपये": "", "रुपए": "",
    "ಲಕ್ಷ": "lakh", "ಕೋಟಿ": "crore", "ಸಾವಿರ": "thousand",
}
_UNIT_RE = re.compile("|".join(sorted(_UNIT_WORDS, key=len, reverse=True)))


def _norm_units(t: str) -> str:
    return _UNIT_RE.sub(lambda m: _UNIT_WORDS[m.group(0)], t)


def extract_age(text: str) -> Tuple[Optional[int], float]:
    t = _low(text)
    if re.search(r"prefer not|skip|don'?t want|बताना नहीं|ಹೇಳಲು ಇಷ್ಟವಿಲ್ಲ|ಬಿಟ್ಟು", t):
        return None, 0.0
    m = re.search(r"(\d{1,3})\s*(years? old|yrs?|y\.?o\.?|साल|वर्ष|ವರ್ಷ|ವಯಸ್ಸು)?", t)
    if m:
        try:
            v = int(m.group(1))
            if 5 <= v <= 100:
                return v, 0.95
            return None, 0.3
        except ValueError:
            pass
    return None, 0.2


def extract_state(text: str) -> Tuple[Optional[str], float]:
    t = _low(text)
    v, c = _map_extract(text, {**HI_STATE_MAP, **KN_STATE_MAP})
    if v is not None:
        return v, c
    for s in STATES:
        if s in t:
            return s.title() if s != "other" else "Other", 0.9
    # single-word state guess — low confidence on purpose: caller asks to confirm
    if len(t.split()) == 1 and len(t) > 2 and t.isalpha():
        return text.strip().title(), 0.5
    return None, 0.2


def _map_extract(text: str, mapping: dict) -> Tuple[Optional[str], float]:
    t = _low(text)
    # NOTE: \b is unreliable around Indic scripts (vowel signs are non-word
    # chars), so use explicit lookarounds: a key must not touch any word
    # character — ascii or Indic (Devanagari U+0900–097F, Kannada U+0C80–0CFF).
    # This keeps short keys like "sc"/"st"/"man" from firing inside ordinary
    # words ("certificate", "woman", "परास्नातक").
    edge = "[0-9A-Za-z_" + chr(0x0900) + "-" + chr(0x097F) + chr(0x0C80) + "-" + chr(0x0CFF) + "]"
    for k, v in mapping.items():
        kk = k.strip()
        if re.search(r"(?<!" + edge + r")" + re.escape(kk) + r"(?!" + edge + r")", t):
            return v, 0.9
    return None, 0.2


def extract_income_band(text: str) -> Tuple[Optional[str], float]:
    t = _norm_units(_low(text).replace(",", "").replace("₹", "").replace("rs", ""))
    if re.search(r"prefer not|skip|बताना नहीं|ಹೇಳಲು ಇಷ್ಟವಿಲ್ಲ", t):
        return None, 0.0
    nums = [float(n) for n in re.findall(r"(\d+(?:\.\d+)?)", t)]
    # find explicit lakh numbers (supports k/thousand/crore/lakh + bare rupees)
    lakhs = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(crore|cr|lakh|lacs?|l\b|thousand|k\b)", t):
        try:
            n = float(m.group(1)); unit = (m.group(2) or "").lower()
        except ValueError:
            continue
        if unit.startswith("cr"):
            lakhs.append(n * 100)
        elif unit.startswith("thousand") or unit == "k":
            lakhs.append(n / 100)  # rupees -> lakh
        elif unit.startswith("lakh") or unit.startswith("lac") or unit == "l":
            lakhs.append(n)
        else:
            lakhs.append(n / 100000)  # bare rupees -> lakh
    v = lakhs[0] if lakhs else None
    if v is None and nums:
        # bare number: assume rupees; small bare numbers are ambiguous (could be thousands)
        n = nums[0]
        if n > 20000:
            v = n / 100000
        else:
            return None, 0.25
    if v is not None:
        if v < 1:
            return "under 1 lakh", 0.85
        if v <= 2.5:
            return "1 to 2.5 lakh", 0.85
        if v <= 6:
            return "2.5 to 6 lakh", 0.85
        if v <= 12:
            return "6 to 12 lakh", 0.85
        return "above 12 lakh", 0.85
    for band in ["under 1 lakh", "1 to 2.5 lakh", "2.5 to 6 lakh", "6 to 12 lakh", "above 12 lakh"]:
        if band in t:
            return band, 0.9
    if "below" in t and "lakh" in t:
        return "under 1 lakh", 0.6
    return None, 0.2


def extract_funding_need(text: str) -> Tuple[Optional[str], float]:
    t = _norm_units(_low(text).replace(",", "").replace("₹", "").replace("rs", ""))
    if re.search(r"prefer not|skip|बताना नहीं|ಹೇಳಲು ಇಷ್ಟವಿಲ್ಲ", t):
        return None, 0.0
    lakhs: list[float] = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(crore|cr|lakh|l\b|thousand|k\b)", t):
        try:
            n = float(m.group(1)); unit = m.group(2)
        except ValueError:
            continue
        if unit.startswith("cr"):
            lakhs.append(n * 100)
        elif unit.startswith("thousand") or unit == "k":
            lakhs.append(n / 100)
        else:
            lakhs.append(n)
    v = lakhs[0] if lakhs else None
    if v is None:
        for band in ["under 50k", "50k to 5 lakh", "5 to 10 lakh", "10 to 50 lakh",
                     "50 lakh to 1 crore", "above 1 crore"]:
            if band in t:
                return band, 0.9
        return None, 0.2
    if v < 0.5:
        return "under 50k", 0.85
    if v <= 5:
        return "50k to 5 lakh", 0.85
    if v <= 10:
        return "5 to 10 lakh", 0.85
    if v <= 50:
        return "10 to 50 lakh", 0.85
    if v <= 100:
        return "50 lakh to 1 crore", 0.85
    return "above 1 crore", 0.85


def extract_bool(text: str) -> Tuple[Optional[bool], float]:
    t = _low(text)
    if re.search(r"\byes\b|yeah|yep|registered|udyam|already|have\b", t) and not re.search(r"not|no\b|n't", t):
        return True, 0.85
    if re.search(r"\bno\b|not yet|new\b|unregistered|first|haven'?t|nope", t):
        # "new" implies not registered; "first" implies first-time borrower — caller disambiguates
        return False if "borrow" not in t and "loan" not in t else True, 0.6
        # keep simple: below we specialise per field
    if re.search(r"\bno\b|not\b|n't|never", t):
        return False, 0.85
    return None, 0.2


def extract_field(field: str, text: str) -> Tuple[Any, float]:
    """Returns (value, confidence 0..1). Low confidence (<0.55) => caller should confirm."""
    if field == "age":
        return extract_age(text)
    if field == "state":
        return extract_state(text)
    if field == "social_category":
        return _map_extract(text, CATEGORY_MAP)
    if field == "gender":
        return _map_extract(text, GENDER_MAP)
    if field == "occupation_stage":
        if text.strip().lower() in ("other", "अन्य", "ಇತರೆ"):
            return "other", 0.9  # explicit chip tap — no confirmation loop
        v, c = _map_extract(text, STAGE_MAP)
        if v is None and text.strip():
            return "other", 0.4  # guess — caller confirms below threshold
        return v, c
    if field == "sector":
        if text.strip().lower() in ("other", "अन्य", "ಇತರೆ"):
            return "other", 0.9
        v, c = _map_extract(text, SECTOR_MAP)
        if v is None and text.strip():
            return "other", 0.4
        return v, c
    if field == "education_level":
        return _map_extract(text, EDU_MAP)
    if field == "income_band":
        return extract_income_band(text)
    if field == "funding_need":
        return extract_funding_need(text)
    if field == "business_registered":
        t = _low(text)
        if re.search(r"prefer not|skip|बताना नहीं|ಹೇಳಲು ಇಷ್ಟವಿಲ್ಲ", t):
            return None, 0.0
        if re.search(r"yes|registered|udyam|dpiit|incorporat|certificate|recognised|recognized|have|already|got.*(udyam|dpiit|certificate)|हाँ|हां|जी\b|ಹೌದು", t) and not re.search(r"not|no\b|नहीं|नही|ना\b|ಇಲ್ಲ|ಬೇಡ", t):
            return True, 0.85
        if re.search(r"no\b|not|new\b|unregistered|not yet|नहीं|नही|ना\b|ಇಲ್ಲ|ಬೇಡ", t):
            return False, 0.85
        return None, 0.2
    if field == "first_time_borrower":
        t = _low(text)
        if re.search(r"prefer not|skip|बताना नहीं|ಹೇಳಲು ಇಷ್ಟವಿಲ್ಲ", t):
            return None, 0.0
        if re.search(r"first|yes|never.*loan|no.*loan|new borrower|पहल|ಮೊದಲ|हाँ|हां|ಹೌದು", t):
            return True, 0.7
        if re.search(r"no\b|taken|existing loan|before|नहीं|नही|ಇಲ್ಲ", t):
            return False, 0.7
        return None, 0.2
    return None, 0.0


def try_llm_extract(field: str, text: str) -> Tuple[Any, float] | None:
    """Optional LLM pass. Returns None when LLM unavailable so caller uses rules."""
    import os
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(base_url=os.getenv("LLM_BASE_URL") or None, timeout=15)
        prompt = (f"Extract the value for field '{field}' from this user reply: {text!r}. "
                  f"Reply with ONLY the value or the word UNKNOWN. No explanation.")
        r = client.chat.completions.create(model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                                           messages=[{"role": "user", "content": prompt}],
                                           max_tokens=40, temperature=0)
        out = (r.choices[0].message.content or "").strip()
        if out.upper() == "UNKNOWN" or not out:
            return None
        v, c = extract_field(field, out)
        if v is not None:
            return v, min(0.95, c + 0.1)
        return out, 0.6
    except Exception:
        return None
