"""Local language support (English / Hindi / Kannada). Deterministic string tables —
no LLM translation, so output is stable and testable. Dynamic scheme data
(names, benefits, documents) stays in English as the official record; everything
the assistant itself says (questions, options, replies, badges, explanations)
is translated. Option chips display the translated label but submit the
canonical English value, so the rules engine is untouched."""

LANGS = ("en", "hi", "kn")


def lang_or_default(lang: str | None) -> str:
    return lang if lang in LANGS else "en"


# ---------- questions per profile field ----------
QUESTIONS = {
    "occupation_stage": {
        "en": "What best describes you?",
        "hi": "आप कौन हैं? (सबसे सही विकल्प चुनें)",
        "kn": "ನೀವು ಯಾರು? (ಹೆಚ್ಚು ಸೂಕ್ತವಾದುದನ್ನು ಆರಿಸಿ)",
    },
    "age": {
        "en": "What is your age (in years)?",
        "hi": "आपकी उम्र कितनी है? (साल में)",
        "kn": "ನಿಮ್ಮ ವಯಸ್ಸು ಎಷ್ಟು? (ವರ್ಷಗಳಲ್ಲಿ)",
    },
    "state": {
        "en": "Which state do you live in?",
        "hi": "आप किस राज्य में रहते हैं?",
        "kn": "ನೀವು ಯಾವ ರಾಜ್ಯದಲ್ಲಿ ವಾಸಿಸುತ್ತಿದ್ದೀರಿ?",
    },
    "gender": {
        "en": "What is your gender? (Only used to unlock women-specific benefits — you can skip.)",
        "hi": "आपका लिंग क्या है? (सिर्फ महिला-विशेष लाभों के लिए — छोड़ सकते हैं)",
        "kn": "ನಿಮ್ಮ ಲಿಂಗ ಯಾವುದು? (ಮಹಿಳಾ-ವಿಶೇಷ ಸೌಲಭ್ಯಗಳಿಗೆ ಮಾತ್ರ — ಬಿಟ್ಟುಬಿಡಬಹುದು)",
    },
    "social_category": {
        "en": "What is your social category? (Only unlocks category benefits — you can skip.)",
        "hi": "आपकी सामाजिक श्रेणी क्या है? (सिर्फ श्रेणी-विशेष लाभों के लिए — छोड़ सकते हैं)",
        "kn": "ನಿಮ್ಮ ಸಾಮಾಜಿಕ ವರ್ಗ ಯಾವುದು? (ವರ್ಗ-ವಿಶೇಷ ಸೌಲಭ್ಯಗಳಿಗೆ ಮಾತ್ರ — ಬಿಟ್ಟುಬಿಡಬಹುದು)",
    },
    "education_level": {
        "en": "What level are you studying at (or your highest education)?",
        "hi": "आप किस स्तर पर पढ़ रहे हैं (या आपकी उच्चतम शिक्षा)?",
        "kn": "ನೀವು ಯಾವ ಮಟ್ಟದಲ್ಲಿ ಓದುತ್ತಿದ್ದೀರಿ (ಅಥವಾ ನಿಮ್ಮ ಅತ್ಯುನ್ನತ ಶಿಕ್ಷಣ)?",
    },
    "sector": {
        "en": "Which sector is your business/idea in?",
        "hi": "आपका व्यवसाय/विचार किस क्षेत्र में है?",
        "kn": "ನಿಮ್ಮ ವ್ಯಾಪಾರ/ಕಲ್ಪನೆ ಯಾವ ಕ್ಷೇತ್ರದಲ್ಲಿದೆ?",
    },
    "funding_need": {
        "en": "How much funding do you need for the business?",
        "hi": "व्यवसाय के लिए कितनी रकम चाहिए?",
        "kn": "ವ್ಯಾಪಾರಕ್ಕೆ ಎಷ್ಟು ಹಣ ಬೇಕು?",
    },
    "income_band": {
        "en": "What is your annual household income band? (Needed for scholarships, pensions and subsidies — you can skip.)",
        "hi": "परिवार की सालाना आय कितनी है? (छात्रवृत्ति, पेंशन और सब्सिडी के लिए — छोड़ सकते हैं)",
        "kn": "ಕುಟುಂಬದ ವಾರ್ಷಿಕ ಆದಾಯ ಎಷ್ಟು? (ವಿದ್ಯಾರ್ಥಿವೇತನ, ಪಿಂಚಣಿ ಮತ್ತು ಸಬ್ಸಿಡಿಗಾಗಿ — ಬಿಟ್ಟುಬಿಡಬಹುದು)",
    },
    "business_registered": {
        "en": "Is your business already registered (e.g. Udyam)?",
        "hi": "क्या आपका व्यवसाय पहले से पंजीकृत है (जैसे Udyam)?",
        "kn": "ನಿಮ್ಮ ವ್ಯಾಪಾರ ಈಗಾಗಲೇ ನೋಂದಾಯಿತವಾಗಿದೆಯೇ (ಉದಾ. Udyam)?",
    },
    "first_time_borrower": {
        "en": "Is this your first business loan?",
        "hi": "क्या यह आपका पहला व्यवसाय ऋण है?",
        "kn": "ಇದು ನಿಮ್ಮ ಮೊದಲ ವ್ಯಾಪಾರ ಸಾಲವೇ?",
    },
}

# ---------- option labels: canonical value -> display label ----------
OPTION_LABELS = {
    "occupation_stage": {
        "student": {"hi": "छात्र", "kn": "ವಿದ್ಯಾರ್ಥಿ"},
        "aspiring entrepreneur": {"hi": "नया व्यवसाय शुरू करना", "kn": "ಹೊಸ ವ್ಯಾಪಾರ ಆರಂಭ"},
        "existing business": {"hi": "चलता व्यवसाय", "kn": "ಚಾಲ್ತಿಯಲ್ಲಿರುವ ವ್ಯಾಪಾರ"},
        "farmer": {"hi": "किसान", "kn": "ರೈತ"},
        "salaried": {"hi": "नौकरीपेशा", "kn": "ಸಂಬಳದಾರ"},
        "artisan": {"hi": "कारीगर", "kn": "ಕುಶಲಕರ್ಮಿ"},
        "street vendor": {"hi": "रेहड़ी-पटरी विक्रेता", "kn": "ಬೀದಿ ವ್ಯಾಪಾರಿ"},
        "retired": {"hi": "सेवानिवृत्त", "kn": "ನಿವೃತ್ತ"},
        "homemaker": {"hi": "गृहिणी/गृहस्थ", "kn": "ಗೃಹಿಣಿ"},
        "unemployed": {"hi": "बेरोज़गार", "kn": "ನಿರುದ್ಯೋಗಿ"},
        "other": {"hi": "अन्य", "kn": "ಇತರೆ"},
    },
    "gender": {
        "Female": {"hi": "महिला", "kn": "ಮಹಿಳೆ"},
        "Male": {"hi": "पुरुष", "kn": "ಪುರುಷ"},
        "Other": {"hi": "अन्य", "kn": "ಇತರೆ"},
        "prefer not to say": {"hi": "बताना नहीं चाहते", "kn": "ಹೇಳಲು ಇಷ್ಟವಿಲ್ಲ"},
    },
    "social_category": {
        "General": {"hi": "सामान्य", "kn": "ಸಾಮಾನ್ಯ"},
        "OBC": {"hi": "OBC", "kn": "OBC"},
        "SC": {"hi": "SC", "kn": "SC"},
        "ST": {"hi": "ST", "kn": "ST"},
        "EWS": {"hi": "EWS", "kn": "EWS"},
        "prefer not to say": {"hi": "बताना नहीं चाहते", "kn": "ಹೇಳಲು ಇಷ್ಟವಿಲ್ಲ"},
    },
    "state": {
        "Karnataka": {"hi": "कर्नाटक", "kn": "ಕರ್ನಾಟಕ"},
        "Maharashtra": {"hi": "महाराष्ट्र", "kn": "ಮಹಾರಾಷ್ಟ್ರ"},
        "Tamil Nadu": {"hi": "तमिलनाडु", "kn": "ತಮಿಳುನಾಡು"},
        "Delhi": {"hi": "दिल्ली", "kn": "ದೆಹಲಿ"},
        "Other": {"hi": "अन्य", "kn": "ಇತರೆ"},
    },
    "education_level": {
        "school": {"hi": "स्कूल", "kn": "ಶಾಲೆ"},
        "undergraduate": {"hi": "स्नातक", "kn": "ಪದವಿ"},
        "postgraduate": {"hi": "परास्नातक", "kn": "ಸ್ನಾತಕೋತ್ತರ"},
        "diploma": {"hi": "डिप्लोमा", "kn": "ಡಿಪ್ಲೊಮಾ"},
        "other": {"hi": "अन्य", "kn": "ಇತರೆ"},
    },
    "sector": {
        "manufacturing": {"hi": "विनिर्माण", "kn": "ಉತ್ಪಾದನೆ"},
        "services": {"hi": "सेवाएँ", "kn": "ಸೇವೆಗಳು"},
        "trading": {"hi": "व्यापार", "kn": "ವ್ಯಾಪಾರ"},
        "agriculture": {"hi": "कृषि", "kn": "ಕೃಷಿ"},
        "tech": {"hi": "तकनीक", "kn": "ತಂತ್ರಜ್ಞಾನ"},
        "handicraft": {"hi": "हस्तशिल्प", "kn": "ಕರಕುಶಲ"},
        "other": {"hi": "अन्य", "kn": "ಇತರೆ"},
    },
    "income_band": {
        "under 1 lakh": {"hi": "1 लाख से कम", "kn": "1 ಲಕ್ಷಕ್ಕಿಂತ ಕಡಿಮೆ"},
        "1 to 2.5 lakh": {"hi": "1 से 2.5 लाख", "kn": "1 ರಿಂದ 2.5 ಲಕ್ಷ"},
        "2.5 to 6 lakh": {"hi": "2.5 से 6 लाख", "kn": "2.5 ರಿಂದ 6 ಲಕ್ಷ"},
        "6 to 12 lakh": {"hi": "6 से 12 लाख", "kn": "6 ರಿಂದ 12 ಲಕ್ಷ"},
        "above 12 lakh": {"hi": "12 लाख से ज़्यादा", "kn": "12 ಲಕ್ಷಕ್ಕಿಂತ ಹೆಚ್ಚು"},
    },
    "funding_need": {
        "under 50k": {"hi": "50 हज़ार से कम", "kn": "50 ಸಾವಿರಕ್ಕಿಂತ ಕಡಿಮೆ"},
        "50k to 5 lakh": {"hi": "50 हज़ार से 5 लाख", "kn": "50 ಸಾವಿರದಿಂದ 5 ಲಕ್ಷ"},
        "5 to 10 lakh": {"hi": "5 से 10 लाख", "kn": "5 ರಿಂದ 10 ಲಕ್ಷ"},
        "10 to 50 lakh": {"hi": "10 से 50 लाख", "kn": "10 ರಿಂದ 50 ಲಕ್ಷ"},
        "50 lakh to 1 crore": {"hi": "50 लाख से 1 करोड़", "kn": "50 ಲಕ್ಷದಿಂದ 1 ಕೋಟಿ"},
        "above 1 crore": {"hi": "1 करोड़ से ज़्यादा", "kn": "1 ಕೋಟಿಗಿಂತ ಹೆಚ್ಚು"},
    },
}

# ---------- assistant replies ----------
STR = {
    "greet": {
        "en": None,  # composed in main.py with DISCLAIMER (kept byte-identical)
        "hi": "नमस्ते! मैं आपको योग्य सरकारी योजनाएँ खोजने में मदद करता हूँ। यह मार्गदर्शन है, गारंटी नहीं — अंतिम निर्णय योजना प्राधिकरण का होगा।",
        "kn": "ನಮಸ್ತೆ! ನಿಮಗೆ ಅರ್ಹ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಲು ನಾನು ಸಹಾಯ ಮಾಡುತ್ತೇನೆ. ಇದು ಮಾರ್ಗದರ್ಶನ ಮಾತ್ರ, ಖಾತರಿಯಲ್ಲ — ಅಂತಿಮ ನಿರ್ಧಾರ ಯೋಜನಾ ಪ್ರಾಧಿಕಾರದ್ದು.",
    },
    "ack": {"en": "Got it.", "hi": "समझ गया।", "kn": "ಅರ್ಥವಾಯಿತು."},
    "skipped": {"en": "Skipped.", "hi": "छोड़ दिया।", "kn": "ಬಿಟ್ಟುಬಿಡಲಾಗಿದೆ."},
    "retry": {"en": "I didn't catch that.", "hi": "मैं समझ नहीं पाया।", "kn": "ನನಗೆ ಅರ್ಥವಾಗಲಿಲ್ಲ."},
    "confirm": {
        "en": "Just to confirm — did you mean '{value}' for {field}? (Yes/No)",
        "hi": "पुष्टि करें — क्या आपका मतलब {field} के लिए '{value}' था? (हाँ/नहीं)",
        "kn": "ದೃಢೀಕರಿಸಿ — ನೀವು {field} ಗಾಗಿ '{value}' ಎಂದಿದ್ದೀರಾ? (ಹೌದು/ಇಲ್ಲ)",
    },
    "noproblem": {"en": "No problem — ", "hi": "कोई बात नहीं — ", "kn": "ಪರವಾಗಿಲ್ಲ — "},
    "updated_note": {
        "en": " (Updated your earlier answer.)",
        "hi": " (पहले का जवाब बदला।)",
        "kn": " (ಹಿಂದಿನ ಉತ್ತರ ಬದಲಾಯಿಸಲಾಗಿದೆ.)",
    },
    "results_ready": {
        "en": None,  # composed with DISCLAIMER in main.py
        "hi": "धन्यवाद! ये रहे आपके परिणाम। अंतिम निर्णय योजना प्राधिकरण का होगा।",
        "kn": "ಧನ್ಯವಾದ! ಇಲ್ಲಿವೆ ನಿಮ್ಮ ಫಲಿತಾಂಶಗಳು. ಅಂತಿಮ ನಿರ್ಧಾರ ಯೋಜನಾ ಪ್ರಾಧಿಕಾರದ್ದು.",
    },
    "disc": {
        "en": None,  # DISCLAIMER + official-source line in main.py
        "hi": "मार्गदर्शन मात्र — आधिकारिक स्रोत ही मान्य।",
        "kn": "ಮಾರ್ಗದರ್ಶನ ಮಾತ್ರ — ಅಧಿಕೃತ ಮೂಲವೇ ಅಂತಿಮ.",
    },
    "found": {
        "en": None,  # composed with DISCLAIMER in main.py
        "hi": "धन्यवाद! आपको {n} योजना(ओं) के लिए योग्य पाया। अंतिम निर्णय योजना प्राधिकरण का होगा।",
        "kn": "ಧನ್ಯವಾದ! ನೀವು {n} ಯೋಜನೆಗಳಿಗೆ ಅರ್ಹರಾಗಿದ್ದೀರಿ. ಅಂತಿಮ ನಿರ್ಧಾರ ಯೋಜನಾ ಪ್ರಾಧಿಕಾರದ್ದು.",
    },
    "rechecked_same": {
        "en": "Re-checked against your saved answers. No scheme changed status.",
        "hi": "सहेजे जवाबों से फिर जाँचा — कोई योजना नहीं बदली।",
        "kn": "ಉಳಿಸಿದ ಉತ್ತರಗಳಿಂದ ಮತ್ತೆ ಪರಿಶೀಲಿಸಲಾಗಿದೆ — ಯಾವುದೇ ಬದಲಾವಣೆ ಇಲ್ಲ.",
    },
    "couldnt_tell": {
        "en": "I couldn't tell what changed. Reply like “my funding need is 8 lakhs” or “I registered my business” — or tap a fix button on a near-miss card.",
        "hi": "समझ नहीं आया क्या बदला। ऐसे लिखें: “मुझे 8 लाख चाहिए” या “मेरा व्यवसाय पंजीकृत है” — या near-miss कार्ड पर बटन दबाएँ।",
        "kn": "ಏನು ಬದಲಾಗಿದೆ ಎಂದು ತಿಳಿಯಲಿಲ್ಲ. ಹೀಗೆ ಬರೆಯಿರಿ: “ನನಗೆ 8 ಲಕ್ಷ ಬೇಕು” ಅಥವಾ “ನನ್ನ ವ್ಯಾಪಾರ ನೋಂದಾಯಿತವಾಗಿದೆ” — ಅಥವಾ near-miss ಕಾರ್ಡ್‌ನ ಬಟನ್ ಒತ್ತಿ.",
    },
    "updated": {
        "en": "Updated {updates}. ",
        "hi": "{updates} बदला। ",
        "kn": "{updates} ಬದಲಾಯಿಸಲಾಗಿದೆ. ",
    },
    "noted_same": {
        "en": "Noted — values unchanged. ",
        "hi": "नोट किया — मान नहीं बदले। ",
        "kn": "ಗಮನಿಸಲಾಗಿದೆ — ಮೌಲ್ಯಗಳು ಬದಲಾಗಿಲ್ಲ. ",
    },
    "no_change": {
        "en": "Re-checked — no scheme changed status.",
        "hi": "फिर जाँचा — कोई योजना नहीं बदली।",
        "kn": "ಮತ್ತೆ ಪರಿಶೀಲಿಸಲಾಗಿದೆ — ಯಾವುದೇ ಬದಲಾವಣೆ ಇಲ್ಲ.",
    },
    "moved_eligible": {
        "en": "🎉 {name} moved to Eligible!",
        "hi": "🎉 {name} अब योग्य!",
        "kn": "🎉 {name} ಈಗ ಅರ್ಹ!",
    },
    "moved_almost": {
        "en": "👍 {name} moved up to Almost eligible — check its remaining gap.",
        "hi": "👍 {name} अब लगभग योग्य — बचा अंतर देखें।",
        "kn": "👍 {name} ಈಗ ಬಹುತೇಕ ಅರ್ಹ — ಉಳಿದ ಅಂತರ ನೋಡಿ.",
    },
    "moved_other": {
        "en": "{name}: {old} → {new}.",
        "hi": "{name}: {old} → {new}।",
        "kn": "{name}: {old} → {new}.",
    },
    "refuse_guarantee": {
        "en": "I can't guarantee approval or bypass rules — I only give guidance. Let's continue: ",
        "hi": "मैं मंज़ूरी की गारंटी नहीं दे सकता — सिर्फ मार्गदर्शन। आगे बढ़ें: ",
        "kn": "ನಾನು ಅನುಮೋದನೆಯ ಖಾತರಿ ನೀಡಲಾರೆ — ಮಾರ್ಗದರ್ಶನ ಮಾತ್ರ. ಮುಂದುವರಿಯೋಣ: ",
    },
    "progress": {
        "en": "Question {n} of {total}",
        "hi": "प्रश्न {n} / {total}",
        "kn": "ಪ್ರಶ್ನೆ {n} / {total}",
    },
    "yes_no": {"en": ["Yes", "No"], "hi": ["हाँ", "नहीं"], "kn": ["ಹೌದು", "ಇಲ್ಲ"]},
}

# ---------- field labels (confirm prompts, update notes) ----------
FIELD_LABELS = {
    "age": {"hi": "उम्र", "kn": "ವಯಸ್ಸು"},
    "state": {"hi": "राज्य", "kn": "ರಾಜ್ಯ"},
    "social_category": {"hi": "श्रेणी", "kn": "ವರ್ಗ"},
    "gender": {"hi": "लिंग", "kn": "ಲಿಂಗ"},
    "occupation_stage": {"hi": "पहचान", "kn": "ಗುರುತು"},
    "sector": {"hi": "क्षेत्र", "kn": "ಕ್ಷೇತ್ರ"},
    "education_level": {"hi": "शिक्षा", "kn": "ಶಿಕ್ಷಣ"},
    "income_band": {"hi": "आय", "kn": "ಆದಾಯ"},
    "funding_need": {"hi": "रकम", "kn": "ಮೊತ್ತ"},
    "business_registered": {"hi": "पंजीकरण", "kn": "ನೋಂದಣಿ"},
    "first_time_borrower": {"hi": "पहला ऋण", "kn": "ಮೊದಲ ಸಾಲ"},
}

# ---------- eligibility status labels ----------
STATUS = {
    "eligible": {"hi": "योग्य", "kn": "ಅರ್ಹ"},
    "near_miss": {"hi": "लगभग योग्य", "kn": "ಬಹುತೇಕ ಅರ್ಹ"},
    "possibly_eligible": {"hi": "जानकारी चाहिए", "kn": "ಮಾಹಿತಿ ಬೇಕು"},
    "not_eligible": {"hi": "योग्य नहीं", "kn": "ಅರ್ಹರಲ್ಲ"},
}

# ---------- deadline badge labels ----------
DEADLINE = {
    "closes_today": {"hi": "आज बंद", "kn": "ಇಂದು ಮುಚ್ಚುತ್ತದೆ"},
    "closes_in": {"hi": "{n} दिनों में बंद", "kn": "{n} ದಿನಗಳಲ್ಲಿ ಮುಚ್ಚುತ್ತದೆ"},
    "opens_in": {"hi": "{n} दिनों में खुलेगा", "kn": "{n} ದಿನಗಳಲ್ಲಿ ತೆರೆಯುತ್ತದೆ"},
    "closed_reopens": {"hi": "बंद — {date} को फिर खुलेगा", "kn": "ಮುಚ್ಚಿದೆ — {date} ರಂದು ಮತ್ತೆ ತೆರೆಯುತ್ತದೆ"},
}

# ---------- explanation templates (values stay canonical English = data) ----------
EXPLAIN = {
    "match": {
        "hi": "आप {name} के लिए योग्य हैं: {bits}।",
        "kn": "ನೀವು {name} ಗೆ ಅರ್ಹರಾಗಿದ್ದೀರಿ: {bits}।",
    },
    "match_bit": {"hi": "{label}: {actual} शर्त {expected} को पूरा करता है", "kn": "{label}: {actual} ಷರತ್ತು {expected} ಅನ್ನು ಪೂರೈಸುತ್ತದೆ"},
    "match_all": {
        "hi": "{name}: दी गई जानकारी पर सभी ज़रूरी जाँचें पास।",
        "kn": "{name}: ನೀಡಿದ ಮಾಹಿತಿಯ ಮೇಲೆ ಎಲ್ಲಾ ಅಗತ್ಯ ಪರಿಶೀಲನೆಗಳು ಪಾಸ್.",
    },
    "near": {
        "hi": "{name} में अंतर: {bits}",
        "kn": "{name} ನಲ್ಲಿ ಅಂತರ: {bits}",
    },
    "effort": {
        "Very easy": {"hi": "बहुत आसान", "kn": "ತುಂಬಾ ಸುಲಭ"},
        "Easy": {"hi": "आसान", "kn": "ಸುಲಭ"},
        "Moderate": {"hi": "मध्यम", "kn": "ಮಧ್ಯಮ"},
        "Involved": {"hi": "मेहनत वाला", "kn": "ಶ್ರಮದ"},
        "Heavy": {"hi": "कठिन", "kn": "ಕಠಿಣ"},
    },
    "rows": {
        "status": {"hi": "स्थिति", "kn": "ಸ್ಥಿತಿ"},
        "benefit": {"hi": "लाभ", "kn": "ಪ್ರಯೋಜನ"},
        "deadline": {"hi": "आवेदन की अंतिम तिथि", "kn": "ಅರ್ಜಿ ಕೊನೆಯ ದಿನಾಂಕ"},
        "documents": {"hi": "ज़रूरी दस्तावेज़", "kn": "ಅಗತ್ಯ ದಾಖಲೆಗಳು"},
        "effort": {"hi": "आवेदन में मेहनत", "kn": "ಅರ್ಜಿ ಶ್ರಮ"},
        "requirements": {"hi": "मुख्य शर्तें", "kn": "ಮುಖ್ಯ ಷರತ್ತುಗಳು"},
        "channel": {"hi": "आवेदन कैसे करें", "kn": "ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು ಹೇಗೆ"},
        "source": {"hi": "आधिकारिक स्रोत", "kn": "ಅಧಿಕೃತ ಮೂಲ"},
    },
}


def qtext(field: str, lang: str) -> str:
    return QUESTIONS.get(field, {}).get(lang_or_default(lang), QUESTIONS.get(field, {}).get("en", field))


def qoptions(field: str, lang: str):
    """Return (canonical_values, display_labels) for a field's chips."""
    from .graph import FIELD_TO_QUESTION
    values = FIELD_TO_QUESTION.get(field, {}).get("options") or []
    lang = lang_or_default(lang)
    if lang == "en":
        return list(values), list(values)
    table = OPTION_LABELS.get(field, {})
    return list(values), [table.get(v, {}).get(lang, v) for v in values]


def field_label(field: str, lang: str) -> str:
    lang = lang_or_default(lang)
    if lang == "en":
        return field.replace("_", " ")
    return FIELD_LABELS.get(field, {}).get(lang, field)


def status_label(status: str, lang: str) -> str:
    lang = lang_or_default(lang)
    if lang == "en":
        return status
    return STATUS.get(status, {}).get(lang, status)
