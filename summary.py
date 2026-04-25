import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

_client = Groq(api_key=GROQ_API_KEY)


def summarize(conversation_history, slots=None):
    """
    Fast + structured + sales-ready summary
    """

    if slots is None:
        slots = {}

    raw = {
        "interest": slots.get("interest"),
        "goal": slots.get("goal"),
        "timeline": slots.get("timeline"),
        "budget": slots.get("budget"),
        "language": None,
    }

    # ── Extract structured data from history (Fallback) ──
    for item in conversation_history:
        t = item.get("type", "").lower()
        a = item.get("english", item.get("answer", item.get("user", "")))

        if not a:
            continue

        if t in raw and not raw[t]:
            raw[t] = a

    # ── Detect not interested ──
    not_interested = (
        raw["interest"] and
        any(x in raw["interest"].lower() for x in ["no", "not interested"])
    )

    # ── Build compact transcript ──
    conv_text = "\n".join([
        f"{item['type'].upper()}: {item.get('english', item.get('answer', item.get('user', '')))}"
        for item in conversation_history
        if item.get("english", item.get("answer", item.get("user", "")))
    ])

    llm_summary = _generate_llm_summary_fast(conv_text, not_interested)

    final_q = next(
        (item.get("english", item.get("answer", item.get("user", ""))) for item in conversation_history if item["type"] == "FINAL_QUESTIONS"),
        None
    )

    course = clean_slot(raw["goal"], "interest")
    budget = clean_slot(raw["budget"], "budget")
    timeline = raw["timeline"]

    course_str = course if (course and course.lower() != "skipped") else "not specified"
    budget_str = budget if (budget and budget.lower() != "skipped") else "not specified"
    timeline_str = timeline if (timeline and timeline.lower() != "skipped") else "not specified"

    final_summary_sentence = f"Interested in {course_str}, planning to start {timeline_str}, budget around {budget_str}."

    return {
        "preferred_course": course or "Not mentioned",
        "budget": budget or "Not mentioned",
        "timeline": timeline or "Not mentioned",
        "language_preference": raw["language"] or "English",

        "call_overview": final_summary_sentence,
        "buying_signals": llm_summary["buying_signals"],
        "recommended_action": llm_summary["recommended_action"],
        "availability": llm_summary["availability"],
        "final_query": final_q or "None",

        "not_interested": not_interested,
        "completed_flow": raw["budget"] is not None,
    }


# ───────────────────────────────
# FAST LLM SUMMARY
# ───────────────────────────────

def _generate_llm_summary_fast(conv_text, not_interested):

    if not conv_text.strip():
        return _fallback_summary(not_interested)

    prompt = f"""
You are an expert sales analyst summarizing a lead phone call.

Transcript:
{conv_text}

Return ONLY valid JSON. Absolutely NO debris text, NO markdown formatting outside the JSON, and NO introductions.

{{
"overview": "Write a detailed summary of MINIMUM 2 lines. Ensure you explicitly mention the inferred timeline, budget, course of interest, and summarize the final question asked by the user along with the AI's reply to it.",
"buying_signals": "Extract specific indicators of purchasing intent from the user such as urgency to start, price sensitivity, exact career goals, or any hesitations. If none, state 'No explicit buying signals'.",
"recommended_action": "Specific next action for the sales team.",
"availability": "When they aim to start or be contacted."
}}
"""

    try:
        response = _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150
        )

        content = response.choices[0].message.content.strip()

        # Clean potential markdown from JSON output
        if content.startswith("```json"): content = content[7:]
        elif content.startswith("```"): content = content[3:]
        if content.endswith("```"): content = content[:-3]
        content = content.strip()

        try:
            return json.loads(content)
        except:
            print("[Summary ERROR FIXED]")
            return _fallback_summary(not_interested)

    except Exception as e:
        print("[Summary ERROR]", e)
        return _fallback_summary(not_interested)


def _fallback_summary(not_interested):
    return {
        "overview": "User interaction completed",
        "buying_signals": "None" if not not_interested else "Not interested",
        "recommended_action": "Follow up later" if not not_interested else "Do not contact",
        "availability": "Not discussed"
    }
def clean_slot(value, field):
    if not value or value == "skipped":
        return value

    v = value.lower()

    # Interest correction
    if field == "interest":
        if "web" in v or "frontend" in v or "backend" in v:
            return "Full Stack Development"
        if "ai" in v or "machine learning" in v:
            return "Artificial Intelligence"
        if "data" in v:
            return "Data Science"
        if v == "skipped" or v == "":
            return None
        return value.title() # Return their raw input capitalized if not standard course

    # Budget cleanup
    if field == "budget":
        return value.title()

    return value