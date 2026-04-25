from flask import Flask, request, Response, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from flask_cors import CORS
from dotenv import load_dotenv
import os
import re

from db import save_call
from flow import is_not_interested
from interaction import get_ai_reply, translate_to_english, normalize_english
from summary import summarize
from intent_analysis import calculate_intent
from tts import generate_audio

load_dotenv()

NGROK_URL          = os.getenv("NGROK_URL", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

app = Flask(__name__)
CORS(app)

call_sessions = {}

# ─────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────
def get_session(call_sid):
    if call_sid not in call_sessions:
        call_sessions[call_sid] = {
            "state": "INTEREST",
            "conversation_history": [],
            "lang": "en",
            "slots": {
                "interest": None,
                "goal": None,
                "timeline": None,
                "budget": None,
                "final_question": None
            },
            "silence_count": 0,
            "retry_count": 0
        }
    return call_sessions[call_sid]
def extract_course(text):
    t = text.lower()

    mapping = {
        "ai": ["ai", "artificial intelligence", "machine learning", "deep learning", "ml", "nlp"],
        "data science": ["data science", "data analysis", "analytics", "pandas", "statistics"],
        "full stack": ["full stack", "web development", "frontend", "backend", "javascript", "react", "node", "coding"]
    }

    # TASK 1 & 4 — Find Semantic Keywords & Prioritize First Match
    positions = {}
    for course, keywords in mapping.items():
        for k in keywords:
            # Strict word boundary checking prevents 'ai' from matching 'hair'
            for match in re.finditer(rf'\b{re.escape(k)}\b', t):
                if course not in positions or match.start() < positions[course]:
                    positions[course] = match.start()

    if positions:
        return min(positions, key=positions.get)

    # TASK 2 & 3 — Fallback LLM Intelligence & Handle Partial Input
    try:
        from interaction import _client
        from config import GROQ_MODEL
        
        prompt = f"""Classify this user's desired course into exactly one of: AI, Data Science, Full Stack. 
Return ONLY the exact category name.
If the text is vague, conversational, off-topic, or doesn't mention coding/data/AI (e.g., 'interesting picture download', 'I want to speak to someone', 'maybe next month'), YOU MUST return NONE.
Text: {text}"""
        resp = _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10,
        )
        ans = resp.choices[0].message.content.strip().lower()
        
        if "data science" in ans: return "data science"
        if "full" in ans or "stack" in ans: return "full stack"
        if "ai" in ans or "artificial" in ans: return "ai"
        
    except Exception as e:
        print(f"[Extract Course LLM Error] {e}")

    return None
# ─────────────────────────────────────────────
# SPEAK FUNCTIONS
# ─────────────────────────────────────────────
def speak(response_obj, text, lang, ngrok_url):
    if lang in ("ta", "ml"):
        try:
            filename = generate_audio(text, lang)
            audio_url = f"{ngrok_url}/static/{filename}"
            response_obj.play(audio_url)
            return
        except Exception:
            pass

    response_obj.say(text, voice="Polly.Joanna", language="en-US")


def speak_in_gather(gather_obj, text, lang, ngrok_url):
    if lang in ("ta", "ml"):
        try:
            filename = generate_audio(text, lang)
            audio_url = f"{ngrok_url}/static/{filename}"
            gather_obj.play(audio_url)
            return
        except Exception:
            pass

    gather_obj.say(text, voice="Polly.Joanna", language="en-US")

# ─────────────────────────────────────────────
# SLOT EXTRACTION
# ─────────────────────────────────────────────
def extract_slots(user_text, slots):
    text = user_text.lower()

    if not slots["interest"] and any(x in text for x in ["yes", "interested", "looking"]):
        slots["interest"] = user_text

    if not slots["goal"]:
        course = extract_course(user_text)
        if course:
            slots["goal"] = course

    if not slots["timeline"] and any(x in text for x in ["week", "month", "soon", "later"]):
        slots["timeline"] = user_text

    if not slots["budget"]:
        if re.search(r"\d+", text):
            slots["budget"] = user_text

    return slots


def get_next_missing_slot(slots):
    for key in ["interest", "goal", "timeline", "budget"]:
        if not slots.get(key):
            return key
    return "final_question"

def determine_next_state(slots, current_state):
    if current_state == "FINAL_QUESTIONS":
        return "END"
        
    missing = get_next_missing_slot(slots)
    
    state_mapping = {
        "interest": "INTEREST",
        "goal": "GOAL",
        "timeline": "TIMELINE",
        "budget": "BUDGET",
        "final_question": "FINAL_QUESTIONS"
    }
    
    return state_mapping.get(missing, "END")

TA_FLOW = {
    "INTEREST": "நீங்கள் ஆன்லைனில் கோர்ஸ் படிக்க ஆர்வமாக உள்ளீர்களா?",
    "GOAL": "உங்களுக்கு எந்த வகை கோர்ஸில் ஆர்வம் இருக்கிறது? உதாரணமாக AI, Data Science அல்லது Full Stack?",
    "TIMELINE": "நீங்கள் எப்போது தொடங்க திட்டமிடுகிறீர்கள்?",
    "BUDGET": "உங்கள் பட்ஜெட் சுமார் எவ்வளவு?",
    "FINAL_QUESTIONS": "உங்களுக்கு ஏதேனும் கேள்விகள் உள்ளதா?",
    "END": "சரி, எங்கள் குழு விரைவில் உங்களை தொடர்பு கொள்ளும். நன்றி!"
}

ML_FLOW = {
    "INTEREST": "നിങ്ങൾക്ക് കോഴ്സ് പഠിക്കാൻ താല്പര്യമുണ്ടോ?",
    "GOAL": "നിങ്ങൾക്ക് ഏത് കോഴ്സിലാണ് താൽപ്പര്യം?",
    "TIMELINE": "നിങ്ങൾ എപ്പോൾ തുടങ്ങാൻ പദ്ധതിയിടുന്നു?",
    "BUDGET": "നിങ്ങളുടെ ബജറ്റ് ഏകദേശം എത്രയാണ്?",
    "FINAL_QUESTIONS": "നിങ്ങൾക്ക് എന്തെങ്കിലും സംശയങ്ങൾ ഉണ്ടോ?",
    "END": "ശരി, ഞങ്ങളുടെ ടീം ഉടൻ നിങ്ങളെ ബന്ധപ്പെടും. നന്ദി!"
}
def get_course_details(course):
    course = str(course).lower()
    
    if "ai" in course or "artificial intelligence" in course:
        return "Our AI course covers Python, Machine Learning, Deep Learning, and NLP. It usually takes 3 to 6 months and costs around ₹10,000 to ₹25,000. It prepares you with job-ready AI skills."
        
    elif "data science" in course or "data" in course:
        return "Our Data Science course covers Python, Pandas, Visualization, and ML. It usually takes 3 to 5 months and costs around ₹8,000 to ₹20,000."
        
    elif "full stack" in course or "web" in course:
        return "Our Full Stack course covers HTML, CSS, JS, React, and Backend. It usually takes 4 to 6 months and costs around ₹12,000 to ₹30,000."
        
    return "We offer courses in AI, Data Science, and Full Stack Development. They take 3 to 6 months and cost between ₹8,000 and ₹30,000."
# ─────────────────────────────────────────────
# CALL TRIGGER
# ─────────────────────────────────────────────
@app.route("/call", methods=["POST"])
def trigger_call():
    data = request.get_json(silent=True) or {}

    phone = (data.get("phone") or "").strip()
    lang  = (data.get("lang") or "en").strip().lower()

    if not phone:
        return jsonify({"error": "phone required"}), 400

    webhook_url = f"{NGROK_URL}/voice?lang={lang}"

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    call = client.calls.create(
        to=phone,
        from_=TWILIO_FROM_NUMBER,
        url=webhook_url
    )

    sess = get_session(call.sid)
    sess["name"] = (data.get("name") or "").strip()
    sess["details"] = (data.get("details") or "").strip()
    sess["phone"] = phone

    return jsonify({"status": "call_initiated", "call_sid": call.sid})

# ─────────────────────────────────────────────
# VOICE ENTRY
# ─────────────────────────────────────────────
@app.route("/voice", methods=["POST"])
def voice():
    call_sid = request.values.get("CallSid")
    lang     = request.args.get("lang", "en")

    session = get_session(call_sid)
    session["lang"] = lang

    response = VoiceResponse()

    gather = response.gather(
        input="speech",
        action=f"{NGROK_URL}/process?lang={lang}",
        speechTimeout="auto",
        timeout=6,
        actionOnEmptyResult=True
    )

    greeting = "Hi! I'm your AI course advisor. Are you interested in learning a course through our platform?"
    if lang == "ta":
        greeting = "வணக்கம்! நான் உங்க ஏ.ஐ கோர்ஸ் அட்வைசர் பேசுறேன். நீங்க ஏதாவது கோர்ஸ் படிக்கணுமா?"
    elif lang == "ml":
        greeting = "ഹായ്! ഞാൻ നിങ്ങളുടെ AI കോഴ്സ് അഡ്വൈസർ ആണ്. നിങ്ങൾക്ക് ഏതെങ്കിലും കോഴ്സ് പഠിക്കണോ?"

    speak_in_gather(
        gather,
        greeting,
        lang,
        NGROK_URL
    )

    return Response(str(response), mimetype="text/xml")

# ─────────────────────────────────────────────
# MAIN PROCESS
# ─────────────────────────────────────────────
@app.route("/process", methods=["POST"])
def process():
    call_sid = request.values.get("CallSid")
    lang = request.args.get("lang", "en")

    session = call_sessions.get(call_sid)
    if not session:
        return Response("", mimetype="text/xml")

    def clean_text(text):
        return text.strip().replace("  ", " ")

    user_text = clean_text(request.values.get("SpeechResult", ""))
    print(f"\n[USER] {user_text}")

    if not user_text or len(user_text.strip()) < 2:
        vr = VoiceResponse()
        gather = Gather(
            input="speech",
            action=f"{NGROK_URL}/process?lang={lang}",
            method="POST",
            timeout=6,
            speechTimeout="auto",
            language={"en": "en-IN", "ta": "ta-IN", "ml": "ml-IN"}.get(lang, "en-IN"),
            speechModel="phone_call",
            enhanced=True
        )
        speak_in_gather(gather, "Sorry, I didn't get that. Could you please repeat?", lang, NGROK_URL)
        vr.append(gather)
        return Response(str(vr), mimetype="text/xml")

    # ── Translate ──────────────────────────────────────────
    english_text = clean_text(translate_to_english(user_text, lang))
    print(f"[ENGLISH] {english_text}")

    # ── Exit check ─────────────────────────────────────────
    negative = is_not_interested(user_text)

    if negative:
        session["conversation_history"].append({
            "type": "negative_signal",
            "user": user_text,
            "english": english_text
        })


    required_slots = ["interest", "goal", "timeline", "budget", "final_question"]

    questions = {
        "interest": "Are you interested in learning a course through our platform?",
        "goal": "Got it. What specific course or skill do you want to learn?",
        "timeline": "Sounds good. When are you planning to start?",
        "budget": "Perfect. What is your budget range for the course?",
        "final_question": "Awesome. Before we wrap up, do you have any questions?"
    }

    state_to_slot = {
        "INTEREST": "interest",
        "GOAL": "goal",
        "TIMELINE": "timeline",
        "BUDGET": "budget",
        "FINAL_QUESTIONS": "final_question"
    }

    current_state = session["state"]
    target_slot = state_to_slot.get(current_state)
    def is_question(text):
        t = text.lower()
        return (
            "?" in text or
            any(x in t for x in ["what", "how", "why", "which", "can you", "do you", "is there"])
        )
    # ── OUT-OF-ORDER SLOT DETECTION ────────────────────────
    text = english_text.lower()
    slot_detected = False

    # Timeline detection
    if any(x in text for x in ["day", "week", "month", "tomorrow", "soon"]) and len(text.split()) <= 5:
        session["slots"]["timeline"] = english_text
        slot_detected = True

    # Budget detection
    if any(char.isdigit() for char in text) or any(x in text for x in ["k", "thousand"]):
        session["slots"]["budget"] = english_text
        slot_detected = True

    # Course detection (reuse existing extract_course function)
    detected = extract_course(english_text)
    if detected:
        session["slots"]["goal"] = detected
        slot_detected = True

    # ── SLOT CAPTURE (STRICT VALIDATION) ───────────────────
    if target_slot == "interest" and not session["slots"].get("interest"):
        # We already know they didn't say explicit "no" because `negative` check handled it.
        # So we can assume any normal answer here is affirmative or a question.
        if any(x in english_text.lower() for x in ["yes", "yeah", "interested", "looking", "want", "maybe", "thinking"]):
            session["slots"]["interest"] = english_text
            session["retry_count"] = 0
            print(f"[FIXED INTEREST FLAG]")
        elif not slot_detected:
            session["retry_count"] = session.get("retry_count", 0) + 1
            if session["retry_count"] >= 2:
                session["slots"]["interest"] = "skipped"
                session["retry_count"] = 0

    elif target_slot == "goal" and not session["slots"].get("goal"):
        detected = extract_course(english_text)

        if detected:
            session["slots"]["goal"] = detected
            session["raw_interest"] = user_text # save raw text just in case
            session["retry_count"] = 0
            print(f"[FIXED COURSE] → {detected}")
        elif not slot_detected:
            session["retry_count"] = session.get("retry_count", 0) + 1
            print(f"[COURSE NOT CLEAR] (Retry: {session['retry_count']})")
            if session["retry_count"] >= 2:
                # Store whatever they said and move on
                session["slots"]["goal"] = clean_text(english_text)
                session["raw_interest"] = user_text
                session["retry_count"] = 0
            
    elif target_slot and not session["slots"].get(target_slot):
        clean = clean_text(english_text)
        
        # Always accept numbers as valid (budget) & Number words
        if any(char.isdigit() for char in clean.lower()):
            is_valid = True
        elif any(x in clean.lower() for x in ["thousand", "hundred", "lakh"]):
            is_valid = True
        else:
            is_valid = not (len(clean) < 3 or not is_valid_answer(clean, target_slot))
            
        is_garbage = not is_valid
        
        if target_slot == "final_question":
            if any(x in clean.lower() for x in ["can i ask", "i have a question", "can i ask something"]):
                vr = VoiceResponse()
                gather = Gather(
                    input="speech",
                    action=f"{NGROK_URL}/process?lang={lang}",
                    method="POST",
                    timeout=8,
                    speechTimeout="auto",
                    language={"en": "en-IN", "ta": "ta-IN", "ml": "ml-IN"}.get(lang, "en-IN"),
                    speechModel="phone_call",  
                    enhanced=True  
                )
                speak_in_gather(gather, "Of course, go ahead. What would you like to know?", lang, NGROK_URL)
                vr.append(gather)
                return Response(str(vr), mimetype="text/xml")

        if not is_garbage:
            if target_slot == "budget":
                numbers = re.findall(r'\d+', clean)
                if numbers:
                    parsed_nums = []
                    for n in numbers:
                        val = int(n)
                        # Auto-convert shorthand thousands (e.g., '15' -> 15000)
                        if 0 < val < 100:
                            val *= 1000
                        parsed_nums.append(str(val))
                    
                    if len(parsed_nums) > 1:
                        clean = f"₹{parsed_nums[0]} - ₹{parsed_nums[-1]}"
                    else:
                        clean = f"₹{parsed_nums[0]}"
                    
            session["slots"][target_slot] = clean
            session["retry_count"] = 0
            print(f"[SLOT SAVED] {target_slot} → {clean}")
        elif not slot_detected:
            session["retry_count"] = session.get("retry_count", 0) + 1
            print(f"[REJECTED GARBAGE] {clean} (Retry: {session['retry_count']})")
            if session["retry_count"] >= 2:
                session["slots"][target_slot] = "skipped"
                session["retry_count"] = 0

    # ── FIND NEXT MISSING SLOT ─────────────────────────────
    missing_slot = None
    for s in required_slots:
        if session["slots"].get(s) in [None, ""]:
            missing_slot = s
            break

    if slot_detected:
        session["retry_count"] = 0

    # ── FORCE STATE (NO SKIPPING) ──────────────────────────
    state_map = {
        "interest": "INTEREST",
        "goal": "GOAL",
        "timeline": "TIMELINE",
        "budget": "BUDGET",
        "final_question": "FINAL_QUESTIONS"
    }

    for s in ["interest", "goal", "timeline", "budget", "final_question"]:
        if session["slots"].get(s) in [None, ""]:
            session["state"] = state_map[s]
            break
    else:
        session["state"] = "END"

    # session["state"] = state_map.get(missing_slot, "END")

    print("CURRENT STATE:", session["state"])
    print(f"[SLOTS] {session['slots']}")

    vr = VoiceResponse()

    # ── ASK NEXT QUESTION ──────────────────────────────────
    if missing_slot:
        base_question = questions[missing_slot]

        if lang == "ta":
            reply = TA_FLOW[session["state"]]
        elif lang == "ml":
            reply = ML_FLOW[session["state"]]
        else:
            if session.get("retry_count", 0) == 1:
                reply = "I didn't quite catch that. " + base_question
            elif negative:
                reply = "No worries, just to understand better, " + base_question
            else:
                try:
                    reply = get_ai_reply(
                        user_text_english=english_text,
                        lang=lang,
                        state=session["state"],
                        conversation_history=session["conversation_history"],
                        missing_slot=missing_slot,
                        forced_question=base_question
                    )
                except Exception as e:
                    print(f"[Fallback Base Question] {e}")
                    reply = base_question

        # ✅ ALWAYS GATHER (THIS FIXES CALL CUT)
        gather = Gather(
            input="speech",
            action=f"{NGROK_URL}/process?lang={lang}",
            method="POST",
            timeout=8,
            speechTimeout="auto",
            language={"en": "en-IN", "ta": "ta-IN", "ml": "ml-IN"}.get(lang, "en-IN"),
            speechModel="phone_call",  
            enhanced=True  
        )
        session["conversation_history"].append({
            "type": current_state,
            "user": english_text,
            "ai": reply
        })
        speak_in_gather(gather, reply, lang, NGROK_URL)
        vr.append(gather)

    else:
        # ── FINAL STEP ─────────────────────────────────────
        
        final_q = session["slots"].get("final_question", "").lower()
        
        if final_q in ["ok", "fine", "no", "nothing", "skipped", "none", "no questions", "i'm good"]:
            if lang == "ta":
                final_reply = TA_FLOW["END"]
            elif lang == "ml":
                final_reply = ML_FLOW["END"]
            else:
                final_reply = "Got it. Let me quickly summarize. Thank you, our team will definitely contact you soon. Goodbye!"
        else:
            ai_reply = ""
            try:
                if lang == "ta":
                    ai_reply = TA_FLOW["END"]
                elif lang == "ml":
                    ai_reply = ML_FLOW["END"]
                else:
                    ai_reply = get_ai_reply(final_q, lang, "END", session["conversation_history"], None)
            except:
                pass
            
            if lang in ["ta", "ml"]:
                final_reply = ai_reply
            else:
                ans = ai_reply if ai_reply else "Got it. Let me quickly summarize."
                final_reply = f"{ans} Thank you, our team will definitely contact you soon. Goodbye!"
                
        # ✅ STORE FINAL TURN
        session["conversation_history"].append({
            "type": current_state,
            "user": english_text,
            "ai": final_reply
        })

        for key in session["slots"]:
            if session["slots"][key] is None:
                session["slots"][key] = "skipped"

        session["final_summary_data"] = {
            "interest": session["slots"].get("interest"),
            "goal": session["slots"].get("goal"),
            "timeline": session["slots"].get("timeline"),
            "budget": session["slots"].get("budget"),
            "final_question": session["slots"].get("final_question")
        }

        summary = summarize(session["conversation_history"], slots=session["slots"])
        intent = calculate_intent(session["conversation_history"])



        payload = session["final_summary_data"]

        save_call(call_sid, session, summary, intent, payload=payload)

        speak(vr, final_reply, lang, NGROK_URL)
        vr.hangup()

    # ── Continue ─

    return Response(str(vr), mimetype="text/xml")
def is_valid_answer(text, slot):
    t = text.lower()

    # Reject garbage patterns
    if len(t.split()) > 25:
        return False  # too long = hallucination

    if any(x in t for x in [
        "i had a", "today i", "story", "life", "death",
        "meeting", "office", "breakfast"
    ]):
        return False

    # Slot-specific validation
    if slot == "timeline":
        return any(x in t for x in ["day", "week", "month", "soon", "tomorrow", "now", "later", "not sure", "don"])

    if slot == "budget":
        return any(char.isdigit() for char in t) or any(x in t for x in ["k", "thousand", "hundred", "free", "not sure", "don"])

    if slot == "goal":
        return len(t.split()) < 30 # Just accept anything that's not too long

    return True

if __name__ == "__main__":
    app.run(debug=True)