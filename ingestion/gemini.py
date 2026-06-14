import os
import re
from typing import Optional

from .schema import ParsedOrderPayload, BuyerSplit, RawItem

# ---------------------------------------------------------------------------
# Gemini system instruction (unchanged, keep full)
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

3. Unit Normalisation:
   Map unit aliases in all supported languages to canonical English units.

4. Payment Intent Tracking:
   Set payment_intent to 'khata' if any credit/tab phrase is detected.

5. PDF / Statement Detection:
   Set request_pdf to true if the user explicitly requests a written bill.

6. Entity Split Grouping (UPDATED — stricter):
   - Only create multiple buyer splits when the user EXPLICITLY requests a division or sharing.
   - Do NOT create splits for generic address terms like "anna", "bhaiya", "didi" unless there is a clear split instruction.
   - If no explicit split instruction is found, assign ALL items to buyer_name 'default'.
   - If a name appears without any items AND there is no explicit split request,
     discard that split entry entirely – it is just conversational language.

7. Language Detection:
   Set the 'language' field to the 2-letter Sarvam language code of the INPUT.

8. Mathematical Isolation:
   Perform ZERO arithmetic, price calculations, or valuations.
   Extract structural data tokens only.
"""

# ---------------------------------------------------------------------------
# Helper: detect split instructions (used in fallback)
# ---------------------------------------------------------------------------
SPLIT_KEYWORDS = {
    "split", "saath", "ke saath", "with", "and", "aur", "mattu", "agum",
    "um", "mariyu", "tho", "ani", "va", "ebong", "o", "te", "ate", "kum",
    "ko", "ke liye", "ko dena", "ko do", "dena", "do"
}

def _is_split_instruction(s: str) -> bool:
    """Return True if the string looks like a split instruction (contains split keyword and no digits)."""
    s_lower = s.lower()
    has_kw = any(kw in s_lower for kw in SPLIT_KEYWORDS)
    has_digit = bool(re.search(r"\d", s_lower))
    return has_kw and not has_digit

def _has_items(payload: ParsedOrderPayload) -> bool:
    return any(len(s.raw_items) > 0 for s in payload.raw_splits)

# ---------------------------------------------------------------------------
# Gemini parsing
# ---------------------------------------------------------------------------
async def _gemini_parse(text_content: str) -> Optional[ParsedOrderPayload]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types
    except ImportError:
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
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Groq fallback
# ---------------------------------------------------------------------------
async def _groq_parse(text_content: str) -> Optional[ParsedOrderPayload]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq
    except ImportError:
        return None

    client = Groq(api_key=api_key)
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION + "\n\nIMPORTANT: Output ONLY a valid JSON object. Do NOT include any extra text, markdown fences, or explanations."},
        {"role": "user", "content": f"Raw Unprocessed Ingestion Line: {text_content}"},
    ]
    try:
        completion = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=messages,
            temperature=0.0,
            max_tokens=4096,
            top_p=1.0,
            stream=False,
            stop=None,
            reasoning_format="hidden",
        )
        raw_output = completion.choices[0].message.content
        if not raw_output:
            return None
        json_text = _extract_json_payload(raw_output)
        if not json_text:
            return None
        return ParsedOrderPayload.model_validate_json(json_text)
    except Exception:
        return None

def _extract_json_payload(text: str) -> Optional[str]:
    text = re.sub(r"<think>.*?(</think>|$)", "", text, flags=re.DOTALL).strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    return match.group(0) if match else (text or None)

# ---------------------------------------------------------------------------
# Heuristic fallback with split filtering
# ---------------------------------------------------------------------------
_KHATA_PHRASES = re.compile(
    r"khata|udhaar|account|tab|credit"
    r"|udhaara|khate\s*ge|kaadanai|kadan|adharam|udhari"
    r"|khata\s*madhe|udhaar\s*de|khate\s*nakho|udhaar\s*aap"
    r"|khate\s*rakho|udhaar\s*dao|khate\s*pa|udhaar\s*de"
    r"|khaatayil|kadam\s*tharuu|khatare\s*rakha|udhara\s*deba",
    flags=re.IGNORECASE,
)
_PDF_PHRASES = re.compile(
    r"pdf|bill|receipt|hisab|statement|document"
    r"|bill\s*kaagu|bill\s*sheet|bill\s*thaanga|receipt\s*aadarah|hisaab",
    flags=re.IGNORECASE,
)
_UNIT_NOISE = re.compile(
    r"\b(kg|kilo|kilos|litre|liter|litres|packet|pack|piece|pc|gm|gram|grams"
    r"|paakit|litar|litaru|litrulu|tukadu|paaket|patket|kilograam"
    r"|kilograamulu|graam|grammu|graamulu|bottle|box|dozen|bundle|ml|milli)\b",
    flags=re.IGNORECASE,
)

def _detect_language(text: str) -> str:
    if re.search(r"[\u0C80-\u0CFF]", text):   return "kn"
    if re.search(r"[\u0B80-\u0BFF]", text):   return "ta"
    if re.search(r"[\u0C00-\u0C7F]", text):   return "te"
    if re.search(r"[\u0980-\u09FF]", text):   return "bn"
    if re.search(r"[\u0A80-\u0AFF]", text):   return "gu"
    if re.search(r"[\u0A00-\u0A7F]", text):   return "pa"
    if re.search(r"[\u0D00-\u0D7F]", text):   return "ml"
    if re.search(r"[\u0B00-\u0B7F]", text):   return "or"
    if re.search(r"[\u0900-\u097F]", text):   return "hi"
    return "hi"

def _heuristic_fallback(text_content: str) -> ParsedOrderPayload:
    from ingestion.utils import normalize_text, split_multilingual

    text = text_content or ""
    lang = _detect_language(text)
    cleaned, _ = normalize_text(text.lower())
    payment_intent = "khata" if _KHATA_PHRASES.search(cleaned) else "cash"
    request_pdf = bool(_PDF_PHRASES.search(cleaned))

    parts = split_multilingual(cleaned)
    items: list[RawItem] = []

    for part in parts:
        # Skip split instructions (no digits, contains split keywords)
        if _is_split_instruction(part):
            continue
        # Skip generic address terms with no digits
        if not re.search(r"\d", part) and part.lower() in {"anna", "bhaiya", "didi", "sir", "madam", "brother", "sister", "friend", "dost", "akka", "tamma", "amma", "appa"}:
            continue

        qty_match = re.search(r"(\d+(?:\.\d+)?)", part)
        if qty_match:
            qty = float(qty_match.group(1))
            name = re.sub(r"(\d+(?:\.\d+)?)", "", part).strip()
        else:
            qty = 1.0
            name = part

        name = _UNIT_NOISE.sub("", name).strip()
        name = re.sub(r"[।،,\.]+", "", name).strip()

        if name and not _is_split_instruction(name):
            items.append(RawItem(name=name, qty=qty))

    if not items:
        items = [RawItem(name=text_content.strip(), qty=1)]

    # Heuristic: detect explicit split-with names like "Abhi ke saath", "with Rahul",
    # and create empty buyer splits for them so the orchestrator can perform an
    # equal split (Pattern A) when one party has items and others are empty.
    extra_names = set()
    try:
        name_before = re.findall(r"([\w\u0900-\u097F\u0C80-\u0CFF]{2,20})\s+(?:ke saath|saath|saath mein)", cleaned, flags=re.IGNORECASE)
        name_after = re.findall(r"(?:split with|with|ke saath split)\s+([\w\u0900-\u097F\u0C80-\u0CFF]{2,20})", cleaned, flags=re.IGNORECASE)
        for nm in set(name_before + name_after):
            n = nm.strip()
            if n and not re.search(r"\d", n) and n.lower() not in {"split", "with", "saath"}:
                extra_names.add(n)
    except Exception:
        pass

    raw_splits = [BuyerSplit(buyer_name="default", raw_items=items)]
    for n in extra_names:
        # append empty split entry for the other party
        raw_splits.append(BuyerSplit(buyer_name=n, raw_items=[]))

    return ParsedOrderPayload(
        payment_intent=payment_intent,
        request_pdf=request_pdf,
        raw_splits=raw_splits,
        language=lang,
    )

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
async def parse_order_text(text_content: str) -> ParsedOrderPayload:
    result = await _gemini_parse(text_content)
    if result is not None and _has_items(result):
        return result
    result = await _groq_parse(text_content)
    if result is not None and _has_items(result):
        return result
    return _heuristic_fallback(text_content)
