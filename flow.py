# ───────────────────────────────────────────────────────────
# flow.py (FINAL CLEAN VERSION)
# Handles ONLY:
# 1. Exit / not-interested detection
# 2. Optional greeting support (if needed)
# ───────────────────────────────────────────────────────────


# ── Not-interested signals (multilingual) ────────────────────
_NOT_INTERESTED = [
    # English
    "not interested", "no thanks", "no thank you", "dont want",
    "don't want", "not now", "maybe later", "later", "busy", "stop",
    "call later", "not now bro", "i'll think", "i will think",

    # Tamil
    "இல்லை", "வேண்டாம்", "இப்போது வேண்டாம்", "பிறகு பார்க்கலாம்",

    # Malayalam
    "ഇല്ല", "വേണ്ട", "ഇപ്പോൾ വേണ്ട", "പിന്നെ നോക്കാം",
]


def is_not_interested(user_text):
    """
    Detect if user wants to exit the conversation.
    Lightweight keyword-based check (fast).
    """
    if not user_text:
        return False

    text = user_text.lower().strip()

    return any(phrase in text for phrase in _NOT_INTERESTED)


# ── OPTIONAL: Greeting (ONLY used in /voice) ─────────────────
def get_greeting(lang="en"):
    greetings = {
        "en": "Hi! I'm your AI course advisor. Are you looking to explore any courses?",
        "ta": "வணக்கம்! நான் உங்கள் AI கோர்ஸ் ஆலோசகர். நீங்கள் எந்தப் பாடநெறிகளை பார்க்க விரும்புகிறீர்கள்?",
        "ml": "ഹായ്! ഞാൻ നിങ്ങളുടെ AI കോഴ്സ് അഡ്വൈസർ. നിങ്ങൾ ഏതെങ്കിലും കോഴ്സ് അന്വേഷിക്കുന്നുണ്ടോ?",
    }

    return greetings.get(lang, greetings["en"])