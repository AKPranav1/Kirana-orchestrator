import os
import json
import re
import httpx
from typing import Tuple, Any

# This module wraps the Gemini API call. If GEMINI_API_KEY is missing it uses a mocked parser.

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = os.getenv("GEMINI_URL", "https://api.gemini.example/v1/generate")

SYSTEM = """You are a Kirana store order parser for Indian grocery stores.
Input may be Hindi (Devanagari), Hinglish, English, or mixed script.
You MUST return ONLY a valid JSON object. No explanation. No markdown. No backticks.

Schema:
{
  "items": [{"name": str, "qty": float, "unit": str}],
  "split_with": [],
  "payment_mode": "cash" | "upi" | "khata"
}

Rules:
- Convert: ek→1, do→2, teen→3, char→4, paanch→5, aadha→0.5
- Units: kg, litre, packet, piece, gm only
- split_with: list of names/numbers mentioned, empty list if none
- payment_mode default: "khata" if not mentioned
- Never return null for items. If unclear, best guess.
"""


async def extract_order_from_text(clean_text: str, debug: bool = False) -> Tuple[dict, Any]:
    """Call Gemini to extract JSON. Returns (parsed_dict, raw_response_or_error)
    If GEMINI_API_KEY is absent, run a simple heuristic mock.
    """
    # Mock path for local dev when no API key
    if not GEMINI_API_KEY:
        # very simple heuristic mock: find patterns like "<num> <unit> <name>"
        items = []
        parts = re.split(r"[,;]", clean_text)
        for p in parts:
            m = re.search(r"(\d+(?:\.\d+)?|ek|do|teen|char|chaar|paanch|aadha)\s*(kg|kilo|litre|liter|l|packet|pack|piece|pc|gm|gram)?\s*(.*)", p, flags=re.I)
            if m:
                q = m.group(1).lower()
                qty = _word_to_num(q)
                unit = _normalize_unit(m.group(2) or "")
                name = (m.group(3) or "").strip()
                if name:
                    items.append({"name": name, "qty": qty, "unit": unit})

        if not items:
            # fallback: try to find words that look like items
            items = [{"name": clean_text.strip(), "qty": 1.0, "unit": "packet"}]

        out = {"items": items, "split_with": [], "payment_mode": "khata"}
        return out, {"mock": True}

    # Build prompt
    user_prompt = f"{SYSTEM}\n\nInput: \"{clean_text}\"\n\nReturn JSON:" 

    payload = {"prompt": user_prompt}
    headers = {"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.post(GEMINI_URL, headers=headers, json=payload)
        except Exception as e:
            return {"items": [], "split_with": [], "payment_mode": "khata", "error": True}, {"error": str(e)}

    text = r.text
    # extract first JSON object from output
    j = _extract_first_json(text)
    if j is None:
        # retry once with a stricter instruction appended
        strict_prompt = user_prompt + "\nIf you cannot output valid JSON, return {\"items\":[], \"split_with\":[], \"payment_mode\":\"khata\"}."
        payload = {"prompt": strict_prompt}
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r2 = await client.post(GEMINI_URL, headers=headers, json=payload)
                text2 = r2.text
                j = _extract_first_json(text2)
                if j is None:
                    return {"items": [], "split_with": [], "payment_mode": "khata", "error": True}, {"raw": text2}
                return j, {"raw": text2}
            except Exception as e:
                return {"items": [], "split_with": [], "payment_mode": "khata", "error": True}, {"error": str(e)}

    # Ensure schema compliance: units and numbers
    try:
        _coerce_schema(j)
    except Exception:
        return {"items": [], "split_with": [], "payment_mode": "khata", "error": True}, {"raw": text}

    return j, {"raw": text}


def _extract_first_json(s: str):
    # find first { ... } that can be json decoded
    start = s.find("{")
    if start == -1:
        return None
    sub = s[start:]
    # try progressively shorter suffixes to find a valid JSON
    for end in range(len(sub), 0, -1):
        try:
            candidate = sub[:end]
            parsed = json.loads(candidate)
            return parsed
        except Exception:
            continue
    # last resort: try regex to match balanced braces
    # naive attempt
    m = re.search(r"(\{.*\})", s, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            return None
    return None


def _word_to_num(token: str) -> float:
    token = token.lower()
    if token in ("ek", "1"):
        return 1.0
    if token in ("do", "2"):
        return 2.0
    if token in ("teen", "3"):
        return 3.0
    if token in ("char", "chaar", "4"):
        return 4.0
    if token in ("paanch", "5"):
        return 5.0
    if token == "aadha":
        return 0.5
    try:
        return float(token)
    except Exception:
        return 1.0


def _normalize_unit(u: str) -> str:
    if not u:
        return "packet"
    u = u.lower()
    if u in ("kilo", "kg", "kilos"):
        return "kg"
    if u in ("litre", "liter", "l"):
        return "litre"
    if u in ("packet", "pack"):
        return "packet"
    if u in ("piece", "pc"):
        return "piece"
    if u in ("gram", "gm"):
        return "gm"
    return u


def _coerce_schema(j: dict):
    # ensure keys exist
    if "items" not in j or not isinstance(j["items"], list):
        raise ValueError("invalid items")
    for it in j["items"]:
        # name
        if "name" not in it:
            raise ValueError("item missing name")
        # qty
        q = it.get("qty", 1)
        if isinstance(q, str):
            q = _word_to_num(q)
        it["qty"] = float(q)
        # unit
        it["unit"] = _normalize_unit(it.get("unit", "packet"))
    # split_with
    if "split_with" not in j or not isinstance(j["split_with"], list):
        j["split_with"] = []
    # payment_mode
    pm = j.get("payment_mode")
    if pm not in ("cash", "upi", "khata"):
        j["payment_mode"] = "khata"
