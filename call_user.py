"""
call_user.py — Trigger a single outbound Twilio call to a lead.

Usage:
    python call_user.py                         # calls default number in .env
    python call_user.py +918248229715           # calls a specific number
    python call_user.py +918248229715 ta        # calls in Tamil
"""

import sys
from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, NGROK_URL


def make_call(to_number, lang="en"):
    """
    Initiate an outbound call via Twilio.

    Args:
        to_number: Phone number to call in E.164 format, e.g. +918248229715
        lang:      Language code to pass to the voice agent ("en", "ta", "ml")

    Returns:
        Twilio Call SID if successful, None on failure.
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER]):
        print("[CallUser] Error: Twilio credentials missing in .env file")
        print("  Required: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER")
        return None

    if not to_number:
        print("[CallUser] Error: No phone number provided")
        return None

    webhook_url = f"{NGROK_URL}/voice?lang={lang}"

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        call = client.calls.create(
            to=to_number,
            from_=TWILIO_FROM_NUMBER,
            url=webhook_url,
            method="POST"
        )

        print(f"[CallUser] Call initiated successfully")
        print(f"  To      : {to_number}")
        print(f"  Language: {lang}")
        print(f"  Webhook : {webhook_url}")
        print(f"  Call SID: {call.sid}")

        return call.sid

    except Exception as e:
        print(f"[CallUser] Failed to initiate call: {e}")
        return None


if __name__ == "__main__":
    # CLI usage: python call_user.py [phone_number] [lang]
    to   = sys.argv[1] if len(sys.argv) > 1 else "+918248229715"
    lang = sys.argv[2] if len(sys.argv) > 2 else "en"

    make_call(to, lang)