import os
from dotenv import load_dotenv

load_dotenv()

# ─── Twilio (still used for /voice /process webhook handling) ──
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

# ─── Exotel (used for OUTBOUND calls — calls any Indian number free) ──
# Sign up free at https://app.exotel.com/signup
# After signup go to: Settings → API → copy SID, Key, Token
# ExoPhone: the virtual number assigned to your account (e.g. 08088919888)
EXOTEL_SID         = os.getenv("EXOTEL_SID", "")
EXOTEL_API_KEY     = os.getenv("EXOTEL_API_KEY", "")
EXOTEL_API_TOKEN   = os.getenv("EXOTEL_API_TOKEN", "")
EXOTEL_FROM_NUMBER = os.getenv("EXOTEL_FROM_NUMBER", "")   # your ExoPhone number
EXOTEL_SUBDOMAIN   = os.getenv("EXOTEL_SUBDOMAIN", "api.exotel.com")  # or your region subdomain

# ─── Groq ──────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY is not set in your .env file")

# ─── MongoDB ───────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "")
if not MONGO_URI:
    raise EnvironmentError("MONGO_URI is not set in your .env file")

# ─── App ───────────────────────────────────────────────────
NGROK_URL   = os.getenv("NGROK_URL", "")
FLASK_PORT  = int(os.getenv("FLASK_PORT", 5000))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

# ─── Groq model ────────────────────────────────────────────
GROQ_MODEL = "llama-3.1-8b-instant"