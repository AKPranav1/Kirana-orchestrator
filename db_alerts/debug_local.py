"""
test_local.py — Person 3 standalone test
Run this BEFORE integrating with Person 1 to verify every piece works.

Usage:
  python test_local.py              → runs all tests
  python test_local.py mongo        → MongoDB only
  python test_local.py elevenlabs   → ElevenLabs audio generation only
  python test_local.py alert        → full alert (ElevenLabs + Twilio)
  python test_local.py full         → full end-to-end (mongo + alert)
"""

import sys
import json
from datetime import datetime

# ── Sample order that mirrors what Person 1 / Person 2 will send ──────────────
SAMPLE_ORDER = {
    "customer_name":  "Rohan",
    "customer_phone": "+919876543210",
    "store_id":       "store_001",
    "items": [
        {"name": "Milk",        "qty": 2, "unit": "litre",  "unit_price": None},
        {"name": "Wheat Flour", "qty": 1, "unit": "kg",     "unit_price": None},
    ],
    "split_with":   ["Rahul"],
    "payment_mode": "khata",
    "input_type":   "text",
    "total_amount": 100.0,
}

SHOPKEEPER_PHONE = "+919999999999"   # ← replace with your own number for demo


# ─────────────────────────────────────────────────────────────────────────────
def test_mongo():
    print("\n" + "="*55)
    print("TEST: MongoDB — log_order + khata split")
    print("="*55)
    from mongo_connector import log_order
    try:
        order_id = log_order(SAMPLE_ORDER, SHOPKEEPER_PHONE)
        print(f"\n✅ PASS — order_id = {order_id}")
        print("   Check MongoDB Atlas → kirana_ai → orders collection")
        print("   Check MongoDB Atlas → kirana_ai → khata  collection")
        return True
    except Exception as e:
        print(f"\n❌ FAIL — {e}")
        return False


def test_elevenlabs_only():
    print("\n" + "="*55)
    print("TEST: ElevenLabs — generate audio")
    print("="*55)
    from alerts import create_text_bill, generate_audio
    try:
        text     = create_text_bill(SAMPLE_ORDER)
        print(f"   Alert text: \"{text}\"")
        filename = generate_audio(text, {"stability": 0.7, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": True})
        print(f"\n✅ PASS — saved to audio_files/{filename}")
        print("   Play the file to verify audio quality.")
        return True
    except Exception as e:
        print(f"\n❌ FAIL — {e}")
        return False


def test_full_alert():
    print("\n" + "="*55)
    print("TEST: Full alert pipeline (ElevenLabs + Twilio)")
    print("="*55)
    print(f"   Sending to: {SHOPKEEPER_PHONE}")
    from alerts import send_receipt_only
    try:
        send_receipt_only(SAMPLE_ORDER, SHOPKEEPER_PHONE)
        print(f"\n✅ PASS — Check WhatsApp on {SHOPKEEPER_PHONE}")
        return True
    except Exception as e:
        print(f"\n❌ FAIL — {e}")
        return False


def test_end_to_end():
    print("\n" + "="*55)
    print("TEST: Full end-to-end (MongoDB + ElevenLabs + Twilio)")
    print("="*55)
    from mongo_connector import log_order
    from alerts import send_receipt_only
    try:
        order_id = log_order(SAMPLE_ORDER, SHOPKEEPER_PHONE)
        print(f"   MongoDB ✅  order_id={order_id}")
        send_receipt_only(SAMPLE_ORDER, SHOPKEEPER_PHONE)
        print(f"   Alert  ✅  WhatsApp (text) sent to {SHOPKEEPER_PHONE}")
        print(f"\n✅ PASS — Full pipeline complete!")
        return True
    except Exception as e:
        print(f"\n❌ FAIL — {e}")
        return False


def test_via_http():
    """Send a POST request to the running FastAPI server (requires server running)."""
    import requests as req
    print("\n" + "="*55)
    print("TEST: HTTP POST to http://localhost:8002/log")
    print("="*55)
    try:
        r = req.post(
            "http://localhost:8002/log",
            json={"order": SAMPLE_ORDER, "shopkeeper_phone": SHOPKEEPER_PHONE},
            timeout=60,
        )
        print(f"   Status: {r.status_code}")
        print(f"   Body:   {r.json()}")
        if r.status_code == 200:
            print("\n✅ PASS")
            return True
        else:
            print("\n❌ FAIL")
            return False
    except Exception as e:
        print(f"\n❌ FAIL — {e}")
        print("   Is the server running? → uvicorn main:app --port 8002 --reload")
        return False


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "mongo":
        test_mongo()
    elif mode == "elevenlabs":
        test_elevenlabs_only()
    elif mode == "alert":
        test_full_alert()
    elif mode == "full":
        test_end_to_end()
    elif mode == "http":
        test_via_http()
    else:
        # Run all in sequence
        results = {
            "MongoDB":     test_mongo(),
            "ElevenLabs":  test_elevenlabs_only(),
            "Full alert":  test_full_alert(),
        }
        print("\n" + "="*55)
        print("SUMMARY")
        print("="*55)
        for name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}  {name}")
