from flask import request, jsonify
from datetime import datetime
from pymongo import MongoClient
from twilio.rest import Client

from config import (
    MONGO_URI,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_FROM_NUMBER,
    NGROK_URL
)

# ─── MongoDB ───────────────────────────────────────────────
client = MongoClient(MONGO_URI)
db = client["voice_ai"]
leads_col = db["pending_leads"]

# ───────────────────────────────────────────────────────────
# DEBUG: PRINT CONFIG (VERY IMPORTANT)
# ───────────────────────────────────────────────────────────
print("\n=== CONFIG CHECK ===")
print("TWILIO_ACCOUNT_SID:", TWILIO_ACCOUNT_SID)
print("TWILIO_AUTH_TOKEN:", "SET" if TWILIO_AUTH_TOKEN else "MISSING")
print("TWILIO_FROM_NUMBER:", TWILIO_FROM_NUMBER)
print("NGROK_URL:", NGROK_URL)
print("====================\n")


# ───────────────────────────────────────────────────────────
# CALL FUNCTION
# ───────────────────────────────────────────────────────────
def _make_twilio_call(phone, lang):
    try:
        # 🚨 HARD CHECK (prevents silent failure)
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER]):
            return None, "Twilio config missing in .env"

        if not NGROK_URL:
            return None, "NGROK_URL missing"

        webhook_url = f"{NGROK_URL}/voice?lang={lang}"

        print(f"[CALL] Trying → {phone}")
        print(f"[CALL] Webhook → {webhook_url}")

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        call = client.calls.create(
            to=phone,
            from_=TWILIO_FROM_NUMBER,
            url=webhook_url
        )

        print(f"[SUCCESS] Call triggered → SID={call.sid}")
        return call.sid, None

    except Exception as e:
        print(f"[ERROR] Twilio failed → {e}")
        return None, str(e)


# ───────────────────────────────────────────────────────────
# MAIN ROUTE: /register
# ───────────────────────────────────────────────────────────
def register_lead():
    data = request.get_json(silent=True) or {}

    phone = (data.get("phone") or "").strip()
    lang  = (data.get("lang") or "en").strip().lower()
    name  = (data.get("name") or "").strip()

    print(f"\n[REGISTER] phone={phone} lang={lang} name={name}")

    if not phone:
        return jsonify({"error": "phone required"}), 400

    if lang not in ["en", "ta", "ml"]:
        lang = "en"

    # ─── SAVE USER ─────────────────────────────────────────
    existing = leads_col.find_one({"phone": phone})

    if existing:
        lead_id = str(existing["_id"])
        print(f"[REGISTER] Existing lead → {lead_id}")
    else:
        result = leads_col.insert_one({
            "phone": phone,
            "lang": lang,
            "name": name,
            "created_at": datetime.utcnow()
        })
        lead_id = str(result.inserted_id)
        print(f"[REGISTER] New lead → {lead_id}")

    # ─── 🔥 FORCE CALL ─────────────────────────────────────
    sid, err = _make_twilio_call(phone, lang)

    if err:
        print(f"[REGISTER] Call FAILED → {err}")
        return jsonify({
            "status": "call_failed",
            "error": err
        }), 500

    print(f"[REGISTER] Call SUCCESS → {sid}")

    return jsonify({
        "status": "call_initiated",
        "call_sid": sid,
        "lead_id": lead_id
    }), 200


# ───────────────────────────────────────────────────────────
# OPTIONAL: TEST ROUTE (VERY USEFUL)
# ───────────────────────────────────────────────────────────
def test_call():
    data = request.get_json(silent=True) or {}

    phone = (data.get("phone") or "").strip()
    lang  = (data.get("lang") or "en").strip().lower()

    print(f"\n[TEST] Triggering manual call → {phone}")

    sid, err = _make_twilio_call(phone, lang)

    if err:
        return jsonify({"error": err}), 500

    return jsonify({"status": "ok", "call_sid": sid}), 200