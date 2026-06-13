import os
import json
import httpx
from typing import Tuple, Any
from dotenv import load_dotenv  # <-- ADD THIS

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SYSTEM = """You are a Kirana store order parser for Indian grocery stores.
Input may be Hindi (Devanagari), Hinglish, English, or mixed script.

Strict Schema Required:
{
  "items": [{"name": "string", "qty": "float", "unit": "string"}],
  "split_with": ["string"],
  "payment_mode": "cash" | "upi" | "khata"
}

Rules:
- Convert numerals: ek->1, do->2, teen->3, char->4, paanch->5, aadha->0.5
- Units allowed: kg, litre, packet, piece, gm
- split_with: list of names mentioned, empty if none
- payment_mode default: "khata" if split is mentioned, otherwise "cash"
"""

async def extract_order_from_text(clean_text: str, debug: bool = False) -> Tuple[dict, Any]:
    if not GEMINI_API_KEY:
        return {"items": [{"name": "mock item", "qty": 1.0, "unit": "packet"}], "split_with": [], "payment_mode": "khata"}, {"mock": True}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": clean_text}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.post(url, headers={"Content-Type": "application/json"}, json=payload)
            if r.status_code != 200:
                print(f"❌ Gemini Error: {r.status_code} - {r.text}")
                return {"items": [], "split_with": [], "payment_mode": "cash", "error": True}, {"error": r.text}
            
            # Since responseMimeType is application/json, this text is pure JSON
            raw_text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_text.strip()), {"raw": raw_text}
            
        except Exception as e:
            print(f"❌ Gemini Exception: {e}")
            return {"items": [], "split_with": [], "payment_mode": "cash", "error": True}, {"error": str(e)}