import json
import re
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

_client = Groq(api_key=GROQ_API_KEY)


def calculate_intent(conversation_history):
    if not conversation_history:
        return _fallback_result("No conversation data available.")

    # ───────────────────────────────────────────────────────
    # We will use the LLM to powerfully analyze the emotion, 
    # enthusiasm, and true intent of the lead based on their answers.
    # ───────────────────────────────────────────────────────
    conv_text = "\n".join([
        f"{item['type'].upper()}: {item.get('english', item.get('answer', item.get('user', '')))}"
        for item in conversation_history
        if item.get("english", item.get("answer", item.get("user", "")))
    ])

    prompt = f"""You are an expert sales psychologist.
Analyze this lead's phone call transcript to determine their true sentiment, emotion, and purchasing intent for our courses.

Transcript:
{conv_text}

Calculate a score from 0 to 100 based on their enthusiasm, urgency, and willingness to learn and invest.
- 70 to 100: High interest, enthusiastic, clear about budget/timeline.
- 40 to 69: Medium interest, hesitant, vague timeline or budget.
- 0 to 39: Low interest, unenthusiastic, negative signals, or just browsing.

Return ONLY JSON:
{{
  "score": (integer 0-100),
  "priority": ("HIGH", "MEDIUM", or "LOW"),
  "reason": "One short sentence explaining their emotional state and intent."
}}
"""
    try:
        resp = _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150,
        )
        content = resp.choices[0].message.content.strip()
        
        # Clean JSON markdown
        if content.startswith("```json"): content = content[7:]
        elif content.startswith("```"): content = content[3:]
        if content.endswith("```"): content = content[:-3]
        
        result = json.loads(content.strip())
        
        score_percent = result.get("score", 50)
        priority = result.get("priority", "MEDIUM").upper()
        reason = result.get("reason", "Analyzed intent from conversation.")
        
        # Override if explicitly negative
        if any("negative_signal" == item.get("type") for item in conversation_history):
            return {
                "score": 10,
                "priority": "LOW",
                "reason": "User explicitly showed negative signals or hung up."
            }

        return {
            "score": score_percent,
            "priority": priority,
            "reason": reason
        }

    except Exception as e:
        print(f"[Intent ERROR] {e}")
        return _fallback_result("Failed to dynamically analyze intent.")


# ───────────────────────────────────────────────────────────
# BUDGET EXTRACTION — handles numeric AND natural language
# ───────────────────────────────────────────────────────────

_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

def _extract_budget_value(text):
    """
    Tries to extract a numeric budget from natural language.

    Examples handled:
      "5000"          → 5000
      "5k"            → 5000
      "five thousand" → 5000
      "around 4k"     → 4000
      "₹3000"         → 3000
      "3 to 5 thousand" → 5000 (takes upper bound)
      "ten thousand"  → 10000

    Returns an integer, or None if no numeric info found.
    """
    if not text:
        return None

    text = text.lower().strip()

    # ── "X thousand" or "X k" patterns ────────────────────
    # e.g. "five thousand", "5 thousand", "5k", "5.5k"
    match = re.search(r"([\d,.]+|[a-z]+)\s*(thousand|k)\b", text)
    if match:
        raw = match.group(1).replace(",", "")
        # try word number first
        if raw in _WORD_NUMBERS:
            return _WORD_NUMBERS[raw] * 1000
        try:
            return int(float(raw) * 1000)
        except ValueError:
            pass

    # ── Plain digits (with optional ₹ / Rs prefix) ────────
    digits = re.sub(r"[^\d]", "", text)
    if digits:
        try:
            val = int(digits)
            # Sanity check: ignore numbers that look like phone/year
            if 100 <= val <= 200000:
                return val
        except ValueError:
            pass

    return None


# ───────────────────────────────────────────────────────────

def _fallback_result(reason):
    print(f"[Intent] Fallback score 50 — {reason}")
    return {
        "score":    50,
        "priority": "MEDIUM",
        "reason":   reason,
    }