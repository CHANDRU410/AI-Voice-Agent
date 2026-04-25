import json
import re
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

_client = Groq(api_key=GROQ_API_KEY)

# ─────────────────────────────────────────────────────────────
# CLEANUP — strips LLM preamble garbage
# ─────────────────────────────────────────────────────────────
def _cleanup(text):
    text = re.compile(
        r'^(here is( the)? (translation|response):?|translated text:?|'
        r'tanglish:?|in tanglish:?|output:?|sure[,!.]?\s*|okay[,!.]?\s*|'
        r'alright[,!.]?\s*)\s*',
        re.IGNORECASE
    ).sub('', text)
    return text.strip().strip('"').strip("'")


# ─────────────────────────────────────────────────────────────
# NORMALIZE ENGLISH
# ─────────────────────────────────────────────────────────────
def normalize_english(text):
    """Clean grammar, remove filler words, and output clean short English."""
    if not text.strip():
        return text

    prompt = f"""You are an expert system.
Transform this messy speech into clean, short English.
Fix grammar and remove filler words (uh, um, ah).
Output ONLY the final English text, nothing else.
Text: {text}"""

    try:
        resp = _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=80
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Normalize Error] {e}")
        return text


# ─────────────────────────────────────────────────────────────
# TRANSLATE USER INPUT → ENGLISH  (for slot extraction + history)
# ─────────────────────────────────────────────────────────────
def translate_to_english(text, lang):
    """
    Translate Tamil or Malayalam user speech to English.
    Used so slots and conversation history are always stored in English.
    """
    if lang == "en" or not text.strip():
        return text

    lang_name = "Tamil" if lang == "ta" else "Malayalam"

    prompt = f"""You are a strict translation engine.
Translate the following {lang_name} text to English.
Rules:
- Output ONLY the plain English translation.
- No explanations, no preamble, no extra words.
Text: {text}"""

    try:
        resp = _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=80
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Translate→EN Error] {e}")
        return text


# ─────────────────────────────────────────────────────────────
# LOAD COURSES
# ─────────────────────────────────────────────────────────────
def _load_courses():
    try:
        with open("courses.json", "r", encoding="utf-8") as f:
            return json.load(f).get("courses", [])
    except Exception as e:
        print(f"[Interaction] courses.json error: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# WHAT TO COLLECT AT EACH STATE
# ─────────────────────────────────────────────────────────────
_NEXT_GOAL = {
    "INTEREST":        "which specific course or skill area they want to learn",
    "GOAL":            "when they are planning to start the course",
    "TIMELINE":        "their approximate budget for the course",
    "BUDGET":          None,
    "FINAL_QUESTIONS": "if they have any questions before we close",
    "END":             None,
}

# ─────────────────────────────────────────────────────────────
# LANGUAGE CONFIG
# ─────────────────────────────────────────────────────────────
_LANG_CONFIG = {
    "en": {
        "name": "English",
        "instruction": (
            "Reply in natural spoken English. Max 2 short sentences. "
            "Sound warm and human — like a helpful colleague on the phone."
        ),
    },
    "ta": {
        "name": "Tamil",
        "instruction": (
            "Reply ONLY in Tamil script (தமிழ் எழுத்து). "
            "Do NOT write in English letters (no Tanglish/transliteration). "
            "Use natural spoken Tamil — short, warm, conversational. "
            "Max 2 sentences. Sound like a friendly advisor from Tamil Nadu."
        ),
    },
    "ml": {
        "name": "Malayalam",
        "instruction": (
            "Reply ONLY in Malayalam script (മലയാളം). "
            "Do NOT write in English letters. "
            "Use natural spoken Malayalam — short, warm, conversational. "
            "Max 2 sentences. Sound like a friendly advisor from Kerala."
        ),
    },
}

# ─────────────────────────────────────────────────────────────
# STATIC FALLBACKS (used when Groq fails)
# ─────────────────────────────────────────────────────────────
_FALLBACKS = {
    "which specific course or skill area they want to learn": {
        "en": "Got it! Which course are you interested in — AI, Data Science, or Full Stack?",
        "ta": "சரி! நீங்கள் AI, Data Science, அல்லது Full Stack — எந்த கோர்ஸ் படிக்கணும்னு நினைக்கிறீர்கள்?",
        "ml": "ശരി! AI, Data Science, അതോ Full Stack — ഏത് കോഴ്സ് പഠിക്കണമെന്ന് നിങ്ങൾ ആഗ്രഹിക്കുന്നു?",
    },
    "when they are planning to start the course": {
        "en": "Sounds good! When are you planning to start?",
        "ta": "நல்லது! நீங்கள் எப்போது ஆரம்பிக்க திட்டமிடுகிறீர்கள்?",
        "ml": "നല്ലതാണ്! നിങ്ങൾ എപ്പോൾ തുടങ്ങാൻ ആലോചിക്കുന്നു?",
    },
    "their approximate budget for the course": {
        "en": "Perfect! Do you have a rough budget in mind?",
        "ta": "சரி! தோராயமாக எவ்வளவு பட்ஜெட் வைத்திருக்கிறீர்கள்?",
        "ml": "ശരി! ഏകദേശം എത്ര ബജറ്റ് ആലോചിക்കുന്നുണ്ട്?",
    },
    "if they have any questions before we close": {
        "en": "Before I let you go — do you have any questions for me?",
        "ta": "முடிப்பதற்கு முன், உங்களுக்கு ஏதாவது சந்தேகம் இருக்கிறதா?",
        "ml": "ഞാൻ വിടുന്നതിന് മുമ്പ് — നിങ്ങൾക്ക് എന്തെങ്കിലും ചോദ്യങ്ങൾ ഉണ്ടോ?",
    },
}

_WRAP_UP = {
    "en": "That's all I needed. Our team will reach out to you very soon. Have a great day!",
    "ta": "சரி, இவ்வளவுதான் தேவை. எங்கள் டீம் விரைவில் உங்களை தொடர்பு கொள்ளும். நன்றி!",
    "ml": "ശരി, ഇത്രയും മതി. ഞങ്ങളുടെ ടീം ഉടൻ നിങ്ങളെ ബന്ധപ്പെടും. നന്ദി!",
}

_NOT_INTERESTED_REPLY = {
    "en": "No worries at all! If you change your mind, we're always here. Have a great day!",
    "ta": "பரவாயில்லை! மனசு மாறினால் எங்களை தொடர்பு கொள்ளுங்கள். நல்ல நாள்!",
    "ml": "ഓക്കേ! മനസ്സ് മാറിയാൽ ഞങ്ങളെ ബന്ധപ്പെടൂ. നல്ല ദിവസം!",
}


# ─────────────────────────────────────────────────────────────
# NOT-INTERESTED DETECTION
# ─────────────────────────────────────────────────────────────
_NOT_INTERESTED_PHRASES = [
    # English
    "not interested", "no thanks", "no thank you", "dont want", "don't want",
    "not now", "maybe later", "call later", "busy", "stop",
    # Tamil script
    "வேண்டாம்", "இல்லை", "இப்போது வேண்டாம்", "பிறகு பார்க்கலாம்",
    # Malayalam script
    "വേണ്ട", "ഇല்ல", "ഇപ്പോൾ വേണ്ട", "പിന്നെ നോക്കാം",
]

def is_not_interested(text):
    if not text:
        return False
    t = text.lower()
    return any(re.search(rf"\b{re.escape(p)}\b", t) for p in _NOT_INTERESTED_PHRASES)


# ─────────────────────────────────────────────────────────────
# MAIN AI REPLY FUNCTION
# ─────────────────────────────────────────────────────────────
def get_ai_reply(user_text_english, lang, state, conversation_history, missing_slot=None, forced_question=None):
    """
    Generate a natural, language-correct reply.

    Args:
        user_text_english: User's speech already translated to English
        lang:              "en" | "ta" | "ml"
        state:             Current flow state
        conversation_history: List of {"type", "english"} dicts
        missing_slot:      Which slot still needs to be filled
        forced_question:   Hardcoded question to append (for ANSWER MODE)

    Returns:
        A reply string in the correct language/script.
    """

    # ── Not interested shortcut ──────────────────────────────
    if is_not_interested(user_text_english):
        return _NOT_INTERESTED_REPLY.get(lang, _NOT_INTERESTED_REPLY["en"])



    # ── Course context ───────────────────────────────────────
    courses = _load_courses()
    course_lines = "\n".join([
        f"- {c['name']}: ₹{c['fee']}, {c['duration']}. {c['description']}"
        for c in courses
    ]) if courses else "No course info available."

    # ── Conversation history (English, last 8 turns) ─────────
    history_text = ""
    for item in conversation_history[-8:]:
        t = item.get("type", "").upper()
        a = item.get("english", item.get("user", ""))
        a_ai = item.get("ai", "")
        if a:
            history_text += f"USER ({t}): {a}\n"
        if a_ai:
            history_text += f"AI: {a_ai}\n"

    next_needed = _NEXT_GOAL.get(state)
    cfg = _LANG_CONFIG.get(lang, _LANG_CONFIG["en"])

    if forced_question:
        rules_text = f"""REPLY RULES (CRITICAL FLOW ENFORCEMENT):
- Step 1: If the user asked a question, answer it directly and briefly. If not, acknowledge their input naturally (like 'Got it', 'Perfect').
- Step 2: CRITICAL: You MUST end your response by asking the following question (translated to your assigned language if needed): "{forced_question}"
- NEVER END YOUR TURN WITHOUT ASKING THE QUESTION. Skipping the question breaks the app.
- Do NOT make up your own next step. You MUST ask the provided question."""
    else:
        rules_text = f"""REPLY RULES (WRAP UP):
- You are answering the user's final question before ending the call.
- Answer their question very briefly and politely.
- NEVER ask a follow-up question or offer to tell them more. DO NOT ask any questions whatsoever.
- The call is ending immediately after this, so just provide the answer definitively."""

    # ── Prompt ───────────────────────────────────────────────
    prompt = f"""You are a warm, highly empathetic, and human-like voice sales advisor for Entri, an online education platform.
You are on a PHONE CALL with a potential student.

Available courses:
{course_lines}

Conversation so far (in English):
{history_text if history_text else "(start of call)"}

The user just said (in English): "{user_text_english}"

Current flow stage: {state}
{"Next info to collect: " + next_needed if next_needed else "All info collected — wrap up warmly."}

LANGUAGE INSTRUCTIONS:
{cfg["instruction"]}

{rules_text}
- Output ONLY the reply. No labels, no preamble, no explanation."""

    try:
        resp = _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=180,
            top_p=0.85
        )
        reply = resp.choices[0].message.content.strip()
        reply = _cleanup(reply)
        print(f"[Interaction] AI reply ({lang}): {reply}")
        return reply

    except Exception as e:
        print(f"[Interaction] Groq error: {e}")
        return _fallback(lang, next_needed)


# ─────────────────────────────────────────────────────────────
# FALLBACK
# ─────────────────────────────────────────────────────────────
def _fallback(lang, next_needed):
    if not next_needed:
        return _WRAP_UP.get(lang, _WRAP_UP["en"])
    bucket = _FALLBACKS.get(next_needed, {})
    return bucket.get(lang, bucket.get("en", "Tell me more — I'd love to help you find the right course."))