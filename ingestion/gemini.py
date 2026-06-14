import os
import re
from typing import Optional

from .schema import ParsedOrderPayload, BuyerSplit, RawItem

# ---------------------------------------------------------------------------
# Gemini system instruction
# Explicitly covers all 10 Sarvam-supported Indian languages and scripts.
# UPDATED: split grouping only on explicit division requests, never on
#          generic address terms like "anna", "bhaiya", etc.
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """
You are the structural parsing brain of an enterprise Kirana Management System.
Your strict function is to extract semantic data from unstructured user strings.

OPERATIONAL PARAMETERS:

1. Multi-lingual Adaptability:
   Accept inputs in ANY of the following languages and their transliterations:
   - Hindi / Hinglish (Devanagari or Latin script)
   - Kannada (Kannada script or Latin transliteration)
   - Tamil (Tamil script or Latin transliteration)
   - Telugu (Telugu script or Latin transliteration)
   - Marathi (Devanagari script or Latin transliteration)
   - Gujarati (Gujarati script or Latin transliteration)
   - Bengali (Bengali script or Latin transliteration)
   - Punjabi / Gurmukhi (Gurmukhi script or Latin transliteration)
   - Malayalam (Malayalam script or Latin transliteration)
   - Odia (Odia script or Latin transliteration)
   - Pure English
   Map semantic concepts (quantities, units, item names, person names) accurately
   regardless of script, syntax, or phonetic spelling variation.

2. Number Word Normalisation:
   Convert number words in ALL of the above languages to their numeric equivalents.
   Examples (non-exhaustive):
     Hindi:    ek=1, do=2, teen=3, char=4, paanch=5, aadha=0.5
     Kannada:  ondu=1, eradu=2, mooru=3, naalu=4, aidu=5, ardha=0.5
     Tamil:    onru=1, rendu=2, moondru=3, naangu=4, aindhu=5, arai=0.5
     Telugu:   okati=1, rendu=2, mudu=3, nalugu=4, aidu=5
     Marathi:  ek=1, don=2, teen=3, char=4, paach=5
     Gujarati: ek=1, be=2, tran=3, char=4, paanch=5
     Bengali:  ek=1, dui=2, tin=3, char=4, paanch=5, adha=0.5
     Punjabi:  ikk=1, do=2, teen=3, char=4, panj=5, adha=0.5
     Malayalam:onnu=1, randu=2, moonu=3, naalu=4, anchu=5, pakuthi=0.5
     Odia:     gote=1, dui=2, tini=3, chari=4, paan=5, ardha=0.5
   Also accept Indic script digits directly (e.g. ২, ੩, ૪, ೫, ൬, ୭, ௮, ౯).

3. Unit Normalisation:
   Map unit aliases in all supported languages to canonical English units:
   kg / litre / gm / ml / packet / piece / bottle / box / dozen / bundle.

4. Payment Intent Tracking:
   Set payment_intent to 'khata' if any credit/tab phrase is detected, such as:
     Hindi:    "khate me likho", "udhaar karo", "account me daal do"
     Kannada:  "udhaara haaki", "khate ge haaku"
     Tamil:    "kaadanai podu", "kadan vaangu"
     Telugu:   "adharam lo petti", "udhari ga ivvu"
     Marathi:  "khata madhe ghala", "udhaar de"
     Gujarati: "khate nakho", "udhaar aap"
     Bengali:  "khate rakho", "udhaar dao"
     Punjabi:  "khate pa", "udhaar de"
     Malayalam:"khaatayil ezhuthu", "kadam tharuu"
     Odia:     "khatare rakha", "udhara deba"
     English:  "put it on my tab", "credit", "on account"
   Otherwise default to 'cash' or 'upi'.

5. PDF / Statement Detection:
   Set request_pdf to true if the user explicitly requests a written bill, receipt,
   or statement in ANY language (e.g. "pdf bill de do", "hisab bhejo",
   "bill kaagu kodi", "bill sheet thaa", "bill thaanga", "receipt aadarah").

6. Entity Split Grouping (UPDATED — stricter):
   - Only create multiple buyer splits when the user EXPLICITLY requests a division or sharing, using phrases like:
       English:   "split with", "divide", "share with", "X will pay for..."
       Hindi:     "X ke saath split", "X ko dena", "X aur main"
       Kannada:   "X jothe split", "X ge kalsi", "X kodu"
       Tamil:     "X udan split", "X ku kodu"
       Telugu:    "X tho split", "X ki ivvu"
   - Do NOT create splits for generic address terms like "anna" (brother), "bhaiya", "didi", "sir",
     "friend", "brother", "sister" unless there is a clear split instruction.
   - If no explicit split instruction is found, assign ALL items to buyer_name 'default'.
   - If a name appears without any items AND there is no explicit split request,
     discard that split entry entirely – it is just conversational language.

7. Language Detection:
   Set the 'language' field to the 2-letter Sarvam language code of the INPUT:
   hi=Hindi/Hinglish, kn=Kannada, ta=Tamil, te=Telugu, mr=Marathi,
   gu=Gujarati, bn=Bengali, pa=Punjabi, ml=Malayalam, or=Odia, en=English.

8. Mathematical Isolation:
   Perform ZERO arithmetic, price calculations, or valuations.
   Extract structural data tokens only.
"""

def _has_items(payload: ParsedOrderPayload) -> bool:
    return any(len(s.raw_items) > 0 for s in payload.raw_splits)

async def parse_order_text(text_content: str) -> ParsedOrderPayload:
    result = await _gemini_parse(text_content)
    if result is not None and _has_items(result):
        return result
    if result is not None:
        print(f"[gemini] returned empty raw_splits, trying groq: {result.model_dump()}", flush=True)

    result = await _groq_parse(text_content)
    if result is not None and _has_items(result):
        return result
    if result is not None:
        print(f"[groq] returned empty raw_splits, using heuristic: {result.model_dump()}", flush=True)

    print(f"[parse] all providers empty for input: {text_content!r}", flush=True)
    return _heuristic_fallback(text_content)

# ---------------------------------------------------------------------------
# Gemini-specific parsing helper
# ---------------------------------------------------------------------------
async def _gemini_parse(text_content: str) -> Optional[ParsedOrderPayload]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types
    except Exception as e:
        print(f"[gemini] genai SDK unavailable ({e})", flush=True)
        return None

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Raw Unprocessed Ingestion Line: {text_content}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=ParsedOrderPayload,
            ),
        )
        return ParsedOrderPayload.model_validate_json(response.text)
    except Exception as e:
        print(f"[gemini] API call failed ({e}) — falling back to Groq / heuristic", flush=True)
        return None


# ---------------------------------------------------------------------------
# Groq (qwen-3-32b) fallback helper
# ---------------------------------------------------------------------------
async def _groq_parse(text_content: str) -> Optional[ParsedOrderPayload]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[groq] GROQ_API_KEY not set, skipping", flush=True)
        return None

    try:
        from groq import Groq
    except ImportError:
        print("[groq] groq library not installed, skipping", flush=True)
        return None

    client = Groq(api_key=api_key)

    messages = [
        {
            "role": "system",
            "content": SYSTEM_INSTRUCTION + "\n\nIMPORTANT: Output ONLY a valid JSON object. Do NOT include any extra text, markdown fences, or explanations.",
        },
        {
            "role": "user",
            "content": f"Raw Unprocessed Ingestion Line: {text_content}",
        },
    ]

    try:
        completion = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=messages,
            temperature=0.0,          # deterministic
            max_tokens=4096,
            top_p=1.0,
            stream=False,
            stop=None,
            reasoning_format="hidden",  # suppress <think>...</think> reasoning trace
        )
        raw_output = completion.choices[0].message.content
        if not raw_output:
            print("[groq] empty response content", flush=True)
            return None

        json_text = _extract_json_payload(raw_output)
        if not json_text:
            print(f"[groq] no JSON object found in response: {raw_output[:200]!r}", flush=True)
            return None

        return ParsedOrderPayload.model_validate_json(json_text)

    except Exception as e:
        print(f"[groq] qwen fallback failed: {e}", flush=True)
        return None


def _extract_json_payload(text: str) -> Optional[str]:
    """
    Cleans an LLM response down to a single JSON object string.

    Handles:
      - <think>...</think> reasoning traces (Qwen reasoning models),
        including unterminated ones if generation got cut off.
      - ```json ... ``` markdown code fences.
      - Any leading/trailing prose around the actual JSON object.
    """
    # Drop <think>...</think> blocks (or anything from an unterminated <think> onward)
    text = re.sub(r"<think>.*?(</think>|$)", "", text, flags=re.DOTALL).strip()

    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()

    # Extract the first {...} JSON object (handles any remaining stray text)
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    return match.group(0) if match else (text or None)

# ---------------------------------------------------------------------------
# Heuristic fallback parser (unchanged)
# Used when both Gemini and Groq are unavailable.
# ---------------------------------------------------------------------------

# Khata / credit trigger phrases across all 10 languages
_KHATA_PHRASES = re.compile(
    r"khata|udhaar|account|tab|credit"          # Hindi / English
    r"|udhaara|khate\s*ge"                       # Kannada
    r"|kaadanai|kadan"                           # Tamil
    r"|adharam|udhari"                           # Telugu
    r"|khata\s*madhe|udhaar\s*de"               # Marathi
    r"|khate\s*nakho|udhaar\s*aap"              # Gujarati
    r"|khate\s*rakho|udhaar\s*dao"              # Bengali
    r"|khate\s*pa|udhaar\s*de"                  # Punjabi
    r"|khaatayil|kadam\s*tharuu"                # Malayalam
    r"|khatare\s*rakha|udhara\s*deba",          # Odia
    flags=re.IGNORECASE,
)

# PDF / receipt request phrases
_PDF_PHRASES = re.compile(
    r"pdf|bill|receipt|hisab|statement|document"
    r"|bill\s*kaagu|bill\s*sheet|bill\s*thaanga"
    r"|receipt\s*aadarah|hisaab",
    flags=re.IGNORECASE,
)

# Unit words that should be stripped from the item name after extraction
_UNIT_NOISE = re.compile(
    r"\b(kg|kilo|kilos|litre|liter|litres|packet|pack|piece|pc|gm|gram|grams"
    r"|paakit|litar|litaru|litrulu|tukadu|paaket|patket|kilograam"
    r"|kilograamulu|graam|grammu|graamulu|bottle|box|dozen|bundle|ml|milli)\b",
    flags=re.IGNORECASE,
)

# Language detection: look for script ranges
def _detect_language(text: str) -> str:
    """Heuristic script → Sarvam language code mapping."""
    if re.search(r"[\u0C80-\u0CFF]", text):   return "kn"   # Kannada
    if re.search(r"[\u0B80-\u0BFF]", text):   return "ta"   # Tamil
    if re.search(r"[\u0C00-\u0C7F]", text):   return "te"   # Telugu
    if re.search(r"[\u0980-\u09FF]", text):   return "bn"   # Bengali
    if re.search(r"[\u0A80-\u0AFF]", text):   return "gu"   # Gujarati
    if re.search(r"[\u0A00-\u0A7F]", text):   return "pa"   # Punjabi/Gurmukhi
    if re.search(r"[\u0D00-\u0D7F]", text):   return "ml"   # Malayalam
    if re.search(r"[\u0B00-\u0B7F]", text):   return "or"   # Odia
    if re.search(r"[\u0900-\u097F]", text):   return "hi"   # Devanagari → Hindi/Marathi
    return "hi"   # default: Hindi/Hinglish


def _heuristic_fallback(text_content: str) -> ParsedOrderPayload:
    """
    Lightweight rule-based parser used when Gemini is unavailable.
    Works for simple quantity + item strings in any of the 10 supported languages.
    NOT a replacement for the LLM — complex sentences will parse partially.
    """

    _ADDRESS_TERMS = {
        "anna", "bhaiya", "bhai", "didi", "behen", "sir", "madam",
        "brother", "sister", "friend", "dost", "mitra", "akka", "tamma", "amma", "appa",
    }
    
    print("[gemini] GEMINI_API_KEY missing — using multilingual heuristic fallback", flush=True)

    try:
        from ingestion.utils import normalize_text, split_multilingual
    except ImportError:
        from .utils import normalize_text, split_multilingual

    text = text_content or ""
    lang = _detect_language(text)

    # Normalise: Indic digits → ASCII, number words → digits, units → canonical
    cleaned, _ = normalize_text(text.lower())

    payment_intent = "khata" if _KHATA_PHRASES.search(cleaned) else "cash"
    request_pdf = bool(_PDF_PHRASES.search(cleaned))

    # Split on multilingual item delimiters
    parts = split_multilingual(cleaned)

    items: list[RawItem] = []
    for part in parts:
        # Skip instruction-only fragments (no digits)
        if not re.search(r"\d", part) and any(
            skip in part
            for skip in ("put", "please", "send", "on", "for", "khata",
                         "udhaar", "udhaara", "kaadanai", "adharam",
                         "khaatayil", "khatare", "pdf", "bill", "receipt")
        ):
            continue

        qty_match = re.search(r"(\d+(?:\.\d+)?)", part)
        if qty_match:
            qty = float(qty_match.group(1))
            name = re.sub(r"(\d+(?:\.\d+)?)", "", part).strip()
        else:
            qty = 1.0
            name = part

        # Remove unit tokens from item name
        name = _UNIT_NOISE.sub("", name).strip()
        # Remove stray punctuation
        name = re.sub(r"[।،,\.]+", "", name).strip()

        if name and name.lower() not in _ADDRESS_TERMS:
            items.append(RawItem(name=name, qty=qty))

    if not items:
        # Last-resort: treat the whole string as one unknown item
        items = [RawItem(name=text_content.strip(), qty=1)]

    return ParsedOrderPayload(
        payment_intent=payment_intent,
        request_pdf=request_pdf,
        raw_splits=[BuyerSplit(buyer_name="default", raw_items=items)],
        language=lang,
    )
