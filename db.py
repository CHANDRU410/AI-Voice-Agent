from pymongo import MongoClient
from datetime import datetime
from config import MONGO_URI

# Safe connection (won’t crash app immediately)
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

db = client["voice_ai"]
calls_collection = db["calls"]

print("MongoDB client initialized (lazy connection)")


# ─── Save ──────────────────────────────────────────────────
def save_call(call_sid, session, summary, intent, payload=None):
    try:
        data = {
            "call_sid": call_sid,
            "name": session.get("name", "Unknown"),
            "phone": session.get("phone", "Unknown"),
            "details": session.get("details", ""),
            "language": session["lang"],
            "conversation": session["conversation_history"],

            "preferred_course": summary.get("preferred_course"),
            "timeline": summary.get("timeline"),
            "budget": summary.get("budget"),
            "summary": summary.get("call_overview"),
            "buying_signals": summary.get("buying_signals"),
            "recommended_action": summary.get("recommended_action"),

            "priority": intent.get("priority"),
            "score": intent.get("score"),

            "timestamp": datetime.utcnow()
        }

        if payload:
            data.update({
                "interest": payload.get("interest"),
                "goal": payload.get("goal"),
                "timeline": payload.get("timeline"),
                "budget": payload.get("budget"),
                "final_question": payload.get("final_question")
            })

        result = calls_collection.insert_one(data)
        print("[MongoDB] Call saved — ID:", result.inserted_id)

    except Exception as e:
        print(f"[MongoDB ERROR] {e}")


# ─── Fetch ─────────────────────────────────────────────────
def get_all_calls():
    try:
        return list(calls_collection.find().sort("timestamp", -1))
    except Exception as e:
        print("[MongoDB ERROR]", e)
        return []


def get_call(call_sid):
    try:
        return calls_collection.find_one({"call_sid": call_sid})
    except Exception as e:
        print("[MongoDB ERROR]", e)
        return None


def get_high_intent_calls():
    try:
        return list(calls_collection.find({"priority": "HIGH"}))
    except:
        return []


def get_medium_intent_calls():
    try:
        return list(calls_collection.find({"priority": "MEDIUM"}))
    except:
        return []


def get_low_intent_calls():
    try:
        return list(calls_collection.find({"priority": "LOW"}))
    except:
        return []