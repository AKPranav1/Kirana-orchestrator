import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from ingestion.utils import normalize_text
from ingestion.gemini import parse_order_text, _KHATA_PHRASES
from ingestion.sarvam import speech_to_text, vision_ocr
from ingestion.sku_match import SKUMatcher
from ingestion.orchestrator import orchestrate_order_processing
from ingestion.pdf_generator import compile_invoice_document
import asyncio
import re

from ingestion.schema import BuyerSplit, RawItem


async def _fetch_bytes_with_retry(url: str, auth=None, timeout=30, retries=2):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                r = await client.get(url, auth=auth)
                r.raise_for_status()
                return r.content
        except Exception as e:
            last_exc = e
            await asyncio.sleep(0.5 * (attempt + 1))
    raise last_exc


# ── Output schema enforced at /process ───────────────────────────────────────
class FlatItem(BaseModel):
    name: str
    qty: float
    unit: str | None = None
    unit_price: float | None = None


class FlatOrder(BaseModel):
    customer_phone: str
    customer_name: str
    store_id: str
    language: str = "hi"
    items: list[FlatItem]
    split_with: list[str] = []
    payment_mode: str = "cash"
    input_type: str | None = None
    raw_input_url: str | None = None
    total_amount: float | None = None


TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

app = FastAPI(title="Kirana AI — Ingestion", version="1.1.0")

# URL for DB & alerts service (Person 3)
DB_ALERTS_URL = os.getenv("DB_ALERTS_URL", "http://localhost:8002")

# ── Multilingual khata question detection ─────────────────────────────────
# Single-token question words (word-bounded, Latin + Indic scripts)
_KHATA_Q_WORDS = re.compile(
    r"\b(?:"
    # Hindi / Hinglish
    r"kitna|kitne|kittna|kitni|kya|baki|kittana"
    # English
    r"|how\s+much|what\s+is|balance|outstanding"
    # Kannada (Latin + script)
    r"|eshtu|yestu|yastu|iddhe"
    r"|ಎಷ್ಟು|ಯಷ್ಟು"
    # Tamil (Latin + script)
    r"|evvalavu|evalavu|எவ்வளவு"
    # Telugu (Latin + script)
    r"|entha|enta|ఎంత"
    # Malayalam (Latin + script)
    r"|etra|ethra|എത്ര"
    # Marathi
    r"|kitke|kitka|किती|कितके"
    # Gujarati
    r"|ketlu|કેટલું"
    # Bengali
    r"|koto|কত"
    # Punjabi
    r"|kinna|ਕਿੰਨਾ"
    r")\b",
    re.IGNORECASE,
)
# Multi-token question phrases (exact sequence)
_KHATA_Q_PHRASES = re.compile(
    r"kitna\s+hai|kya\s+hai|baki\s+kitna"
    r"|how\s+much|what\s+is"
    r"|eshtu\s+ide|yestu\s+ide|yastu\s+ide|eshtu\s+iddhe"
    r"|evvalavu\s+irukku|evalavu\s+irukku"
    r"|entha\s+undi|enta\s+undi"
    r"|etra\s+undu|ethra\s+undu"
    r"|koto\s+taka",
    re.IGNORECASE,
)

_KHATA_BALANCE_TEMPLATES = {
    "hi": ("नमस्ते {name}। आपका खाता बैलेंस ₹{amt:.2f} है।", "नमस्ते {name}। कोई खाता रिकॉर्ड नहीं मिला।"),
    "kn": ("ನಮಸ್ಕಾರ {name}. ನಿಮ್ಮ ಖಾತೆ ಬ್ಯಾಲೆನ್ಸ್ ₹{amt:.2f}.", "ನಮಸ್ಕಾರ {name}. ಯಾವುದೇ ಖಾತೆ ದಾಖಲೆ ಕಂಡುಬಂದಿಲ್ಲ."),
    "ta": ("வணக்கம் {name}. உங்கள் கணக்கு இருப்பு ₹{amt:.2f}.", "வணக்கம் {name}. கணக்கு பதிவு எதுவும் இல்லை."),
    "te": ("నమస్కారం {name}. మీ ఖాతా బ్యాలెన్స్ ₹{amt:.2f}.", "నమస్కారం {name}. ఖాతా రికార్డు ఏదీ కనుగొనబడలేదు."),
    "ml": ("നമസ്കാരം {name}. നിങ്ങളുടെ അക്കൗണ്ട് ബാലൻസ് ₹{amt:.2f}.", "നമസ്കാരം {name}. അക്കൗണ്ട് റെക്കോർഡ് ഒന്നും കണ്ടെത്തിയില്ല."),
    "mr": ("नमस्कार {name}. तुमचे खाते शिल्लक ₹{amt:.2f} आहे.", "नमस्कार {name}. कोणताही खाते रेकॉर्ड आढळला नाही."),
    "gu": ("નમસ્તે {name}. તમારું ખાતા બૅલેન્સ ₹{amt:.2f} છે.", "નમસ્તે {name}. કોઈ ખાતા રેકોર્ડ મળ્યો નહીં."),
    "bn": ("নমস্কার {name}। আপনার হিসাবের ব্যালেন্স ₹{amt:.2f}।", "নমস্কার {name}। কোনো হিসাবের রেকর্ড পাওয়া যায়নি।"),
    "pa": ("ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ {name}। ਤੁਹਾਡਾ ਖਾਤਾ ਬੈਲੈਂਸ ₹{amt:.2f} ਹੈ।", "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ {name}। ਕੋਈ ਖਾਤਾ ਰਿਕਾਰਡ ਨਹੀਂ ਮਿਲਿਆ।"),
}
_EN_BALANCE   = "Hello {name}. Your khata balance is ₹{amt:.2f}."
_EN_NO_RECORD = "Hello {name}. No khata record found."
_EN_ERROR     = "Error fetching khata — please try again later."

def _build_khata_message(lang: str, name: str, amt: float | None = None) -> str:
    templates = _KHATA_BALANCE_TEMPLATES.get(lang[:2] if lang else "hi", _KHATA_BALANCE_TEMPLATES["hi"])
    if amt is None:
        return f"{_EN_ERROR}"
    if amt >= 0:
        native = templates[0].format(name=name, amt=amt)
        english = _EN_BALANCE.format(name=name, amt=amt)
    else:
        native = templates[1].format(name=name)
        english = _EN_NO_RECORD.format(name=name)
    return f"{native}\n{english}"

def _is_khata_question(text: str) -> bool:
    """Return True if text looks like a khata balance inquiry."""
    return bool(_KHATA_Q_WORDS.search(text) or _KHATA_Q_PHRASES.search(text))

# ── Latin-script Indic keyword map for language detection ─────────────────
_LATIN_INDIC_KEYWORDS = {
    "kn": {"eshtu", "yestu", "yastu", "iddhe", "ide", "illa", "beku", "koḍi", "kodi", "thumba"},
    "ta": {"evvalavu", "evalavu", "illai", "irukku", "kudu", "romba", "enna"},
    "te": {"entha", "enta", "undi", "ledu", "ivvu", "chala", "meeru"},
    "ml": {"etra", "ethra", "undo", "illa", "tharo", "venda", "ingane"},
    "mr": {"kitke", "kitka", "nahi", "dya", "aahe", "kara"},
    "gu": {"ketlu", "nathi", "apo", "chhe"},
    "bn": {"koto", "dao", "ache", "nei"},
    "pa": {"kinna", "nahi", "de", "hai"},
}

def detect_lang_hint(text: str) -> str:
    # Unicode script detection first (most reliable)
    if re.search(r'[\u0C80-\u0CFF]', text): return "kn"
    if re.search(r'[\u0B80-\u0BFF]', text): return "ta"
    if re.search(r'[\u0C00-\u0C7F]', text): return "te"
    if re.search(r'[\u0D00-\u0D7F]', text): return "ml"
    if re.search(r'[\u0A00-\u0A7F]', text): return "pa"
    if re.search(r'[\u0980-\u09FF]', text): return "bn"
    if re.search(r'[\u0A80-\u0AFF]', text): return "gu"
    if re.search(r'[\u0900-\u097F]', text): return "hi"
    # Latin-script keyword fallback
    tokens = set(text.lower().split())
    for lang, keywords in _LATIN_INDIC_KEYWORDS.items():
        if tokens & keywords:
            return lang
    return "en"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "data", "sku_catalog.json")
matcher = SKUMatcher(CATALOG_PATH)


class ProcessRequest(BaseModel):
    payload_type: str
    payload: str
    customer_phone: str = "unknown"
    customer_name: str = "unknown"
    language_hint: str = "unknown"


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ingestion", "port": 8001}


@app.post("/process")
async def process(req: ProcessRequest):
    payload_type  = req.payload_type
    payload       = req.payload
    language_hint = req.language_hint if req.language_hint and req.language_hint != "unknown" else detect_lang_hint(payload)
    raw_input_url = None
    clean_text    = ""

    # ── 1. MULTIMODAL INGESTION ───────────────────────────────────────────
    if payload_type == "audio":
        raw_input_url = payload
        try:
            auth = (TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID and TWILIO_TOKEN else None
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(payload, auth=auth, follow_redirects=True)
                r.raise_for_status()
                text, _ = await speech_to_text(r.content)
                clean_text, _ = normalize_text(text)
                input_meta = {"input_type": payload_type, "raw_input_url": raw_input_url, "customer_phone": req.customer_phone}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Audio fetch failed: {e}")

    elif payload_type == "image":
        raw_input_url = payload
        try:
            auth = (TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID and TWILIO_TOKEN else None
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(payload, auth=auth, follow_redirects=True)
                r.raise_for_status()
                text, meta = await vision_ocr(r.content)
                clean_text, _ = normalize_text(text)
                input_meta = {"input_type": payload_type, "raw_input_url": raw_input_url, "customer_phone": req.customer_phone, "sarvam_meta": meta}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image fetch failed: {e}")

    else:
        clean_text, _ = normalize_text(payload)

    if "input_meta" not in locals():
        input_meta = {"input_type": payload_type, "raw_input_url": raw_input_url, "customer_phone": req.customer_phone}

    # ── 2. LLM EXTRACTION + SKU MATCHING ──────────────────────────
    # Early intercept: if the text is a khata/balance question, answer directly
    try:
        # Enhanced khata detection
        is_khata_inquiry = False
        
        # Check for khata phrases
        if _KHATA_PHRASES.search(clean_text):
            is_khata_inquiry = True
        
        # Check for question patterns in multiple languages
        khata_question_patterns = [
            r"खाता.*(?:कितना|हुआ|बाकी|बचा)",
            r"khata.*(?:how much|balance|outstanding)",
            r"(?:मेरा|my|mera)\s*(?:खाता|khata)",
            r"(?:बताओ|batao|tell).*(?:खाता|khata)",
            r"कितना\s+(?:बाकी|है|हुआ)",
            r"balance\s+(?:check|kyA|hai)",
            r"खाते\s+इष्टु",
            r"मेरा\s+खाता",
            r"खाता\s+कितना",
            r"कितना\s+हुआ",
        ]
        for pattern in khata_question_patterns:
            if re.search(pattern, clean_text, re.IGNORECASE):
                is_khata_inquiry = True
                break
        
        # Check for presence of quantity indicators (numbers or product words)
        product_keywords = r"\d+(?:\.\d+)?|kg|kilo|packet|piece|litre|चीनी|नमक|तेल|दूध|आटा|चावल|शक्कर|प्याज|चाय|दाल|मैगी|बिस्किट"
        has_quantity = re.search(product_keywords, clean_text.lower())
        
        # Check if text is very short (likely just a question)
        word_count = len(clean_text.split())
        is_short_question = word_count <= 6 and ("?" in clean_text or "कितना" in clean_text or "khata" in clean_text.lower())
        
        if (is_khata_inquiry or is_short_question) and not has_quantity:
            print(f"[INGESTION] Khata inquiry detected: {clean_text!r}", flush=True)
            import urllib.parse
            
            # Use provided customer_name or lookup by phone
            name = req.customer_name if req.customer_name != "unknown" else None
            if not name:
                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        r = await client.get(f"{DB_ALERTS_URL}/customers/lookup", params={"phone": req.customer_phone})
                        if r.status_code == 200:
                            j = r.json()
                            name = j.get("name")
                except Exception:
                    name = None

            if not name:
                digits = "".join(c for c in (req.customer_phone or "") if c.isdigit())
                if digits and len(digits) >= 4:
                    name = f"Customer {digits[-4:]}"
                else:
                    name = "Unknown"

            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    name_q = urllib.parse.quote(name, safe="")
                    r2 = await client.get(f"{DB_ALERTS_URL}/khata/{name_q}", params={"store_id": "store_001"})
                    if r2.status_code == 200:
                        kh = r2.json()
                        outstanding = kh.get("total_outstanding", 0)
                        message = _build_khata_message(language_hint, name, outstanding)
                        return JSONResponse(status_code=200, content={
                            "type": "khata_balance", 
                            "customer_name": name, 
                            "balance": outstanding, 
                            "message": message
                        })
                    else:
                        message = _build_khata_message(language_hint, name, -1)
                        return JSONResponse(status_code=200, content={
                            "type": "khata_balance", 
                            "customer_name": name, 
                            "balance": 0, 
                            "message": message
                        })
            except Exception as e:
                print(f"Khata lookup failed: {e}")
                message = _build_khata_message(language_hint, name, None)
                return JSONResponse(status_code=200, content={
                    "type": "khata_balance", 
                    "customer_name": name, 
                    "balance": None, 
                    "message": message
                })
        
        # Continue with normal order processing
        parsed = await parse_order_text(clean_text)
        print(f"[INGESTION] parsed_payload={parsed.model_dump()}", flush=True)

        # If the user explicitly mentioned a split (e.g. "Abhi ke saath", "with Rahul")
        # but the LLM didn't produce an empty buyer split for the other party,
        # add an empty BuyerSplit so the orchestrator will perform an equal split.
        try:
            # Collect names that appear either before or after split phrases.
            name_before = re.findall(r"([\w\u0900-\u097F\u0C80-\u0CFF]{2,20})\s+(?:ke saath|saath|saath mein)", clean_text, flags=re.IGNORECASE)
            name_after = re.findall(r"(?:split with|with|ke saath split)\s+([\w\u0900-\u097F\u0C80-\u0CFF]{2,20})", clean_text, flags=re.IGNORECASE)
            name_matches = set(n.strip() for n in (name_before + name_after) if n and n.strip())
            # Filter obvious keyword false-positives
            bad = {"split", "with", "saath", "ke", "mein"}
            for nm in list(name_matches):
                lower = nm.lower()
                if lower in bad or any(kw in lower for kw in ("split", "saath", "with")):
                    name_matches.discard(nm)

            for nm in name_matches:
                n = nm.strip()
                if n and not any(s.buyer_name.lower() == n.lower() for s in parsed.raw_splits):
                    parsed.raw_splits.append(BuyerSplit(buyer_name=n, raw_items=[]))
                    print(f"[INGESTION] added split_with heuristic: {n}", flush=True)
        except Exception:
            pass

        # Post-process: split any combined raw_items
        try:
            split_map = {s.buyer_name: s for s in parsed.raw_splits}
            new_raw_splits = {s.buyer_name: [] for s in parsed.raw_splits}

            qty_item_re = re.compile(r"(\d+(?:\.\d+)?)(?:\s*(kg|gm|g|litre|l|packet|pc|piece)?)\s+([^,]+?)(?=,|$)", flags=re.IGNORECASE)
            for split in list(parsed.raw_splits):
                for ri in split.raw_items:
                    text = ri.name or ""
                    found = False
                    for m in qty_item_re.finditer(text):
                        found = True
                        qty = float(m.group(1))
                        unit = (m.group(2) or "").lower() or None
                        item_text = m.group(3).strip()
                        buyer_match = re.search(r"for\s+([\w\u0900-\u097F\-]+)", item_text, flags=re.IGNORECASE)
                        if buyer_match:
                            buyer_token = buyer_match.group(1).strip()
                            if buyer_token.lower() in ("me", "my", "mujhe", "mera", "main"):
                                target_buyer = split.buyer_name
                            else:
                                target_buyer = buyer_token
                            item_text = re.sub(r"for\s+[\w\u0900-\u097F\-]+", "", item_text, flags=re.IGNORECASE).strip()
                        else:
                            target_buyer = split.buyer_name

                        target_buyer = re.sub(r"[^\w\u0900-\u097F\-]", "", target_buyer).strip()
                        if target_buyer:
                            try:
                                if all(ord(c) < 128 for c in target_buyer):
                                    target_buyer = target_buyer.title()
                            except Exception:
                                pass

                        if target_buyer not in split_map:
                            parsed.raw_splits.append(BuyerSplit(buyer_name=target_buyer, raw_items=[]))
                            split_map[target_buyer] = parsed.raw_splits[-1]
                            new_raw_splits[target_buyer] = []

                        try:
                            noisy = re.compile(r"\b(please|pls|bro|bhai|bhaiya|brother|sister|pls\.|please\.|bhaiya,)\b", flags=re.IGNORECASE)
                            item_text_clean = noisy.sub("", item_text).strip()
                        except Exception:
                            item_text_clean = item_text.strip()

                        try:
                            cleaned_item_text, _ = normalize_text(item_text_clean)
                            cleaned_item_text = cleaned_item_text.strip()
                        except Exception:
                            cleaned_item_text = item_text_clean.strip()

                        new_raw_splits[target_buyer].append(RawItem(name=cleaned_item_text, qty=qty, unit=unit))

                    if not found:
                        single_m = qty_item_re.search(text)
                        if single_m:
                            qty = float(single_m.group(1))
                            unit = (single_m.group(2) or "").lower() or None
                            item_text = single_m.group(3).strip()
                            try:
                                noisy = re.compile(r"\b(please|pls|bro|bhai|bhaiya|brother|sister|pls\.|please\.|bhaiya,)\b", flags=re.IGNORECASE)
                                item_text = noisy.sub("", item_text).strip()
                            except Exception:
                                pass
                            try:
                                cleaned_item_text, _ = normalize_text(item_text)
                                cleaned_item_text = cleaned_item_text.strip()
                            except Exception:
                                cleaned_item_text = item_text.strip()
                            new_raw_splits[split.buyer_name].append(RawItem(name=cleaned_item_text, qty=qty, unit=unit))
                        else:
                            try:
                                noisy = re.compile(r"\b(please|pls|bro|bhai|bhaiya|brother|sister|pls\.|please\.|bhaiya,)\b", flags=re.IGNORECASE)
                                cleaned = noisy.sub("", text).strip()
                            except Exception:
                                cleaned = text.strip()
                            try:
                                cleaned_item_text, _ = normalize_text(cleaned)
                                cleaned_item_text = cleaned_item_text.strip()
                            except Exception:
                                cleaned_item_text = cleaned
                            new_raw_splits[split.buyer_name].append(RawItem(name=cleaned_item_text, qty=ri.qty, unit=ri.unit))

            rebuilt = []
            seen = set()
            for s in parsed.raw_splits:
                name = s.buyer_name
                if name in seen:
                    continue
                seen.add(name)
                items = new_raw_splits.get(name, [])
                rebuilt.append(BuyerSplit(buyer_name=name, raw_items=items))

            parsed.raw_splits = rebuilt
            if rebuilt:
                print(f"[INGESTION] post-processed raw_splits={[ (rs.buyer_name, len(rs.raw_items)) for rs in rebuilt ]}", flush=True)
        except Exception as e:
            print(f"[INGESTION] post-process split failed: {e}", flush=True)

        # If we still have a single RawItem that contains multiple quantity tokens,
        # do a more permissive split directly on clean_text
        try:
            if len(parsed.raw_splits) == 1 and len(parsed.raw_splits[0].raw_items) == 1:
                lone = parsed.raw_splits[0].raw_items[0].name or ""
                if len(re.findall(r"\d+(?:\.\d+)?", lone)) >= 2 or len(re.findall(r"\d+(?:\.\d+)?", clean_text)) >= 2:
                    segments = re.findall(r"(\d+(?:\.\d+)?\s*(?:kg|gm|g|litre|l|packet|pc|piece)?\s*[^,]+)(?:,|$)", clean_text, flags=re.IGNORECASE)
                    if not segments:
                        segments = re.findall(r"(\d+(?:\.\d+)?\s*(?:kg|gm|g|litre|l|packet|pc|piece)?\s*[^,]+)(?:,|$)", lone, flags=re.IGNORECASE)
                    if segments and len(segments) > 1:
                        newmap = {}
                        for seg in segments:
                            seg = seg.strip().rstrip(',')
                            m = re.match(r"(?P<qty>\d+(?:\.\d+)?)(?:\s*(?P<unit>kg|gm|g|litre|l|packet|pc|piece))?\s+(?P<rest>.+)$", seg, flags=re.IGNORECASE)
                            if not m:
                                continue
                            qty = float(m.group('qty'))
                            unit = (m.group('unit') or "").lower() or None
                            rest = m.group('rest').strip()
                            if re.search(r"\bfor\b", rest, flags=re.IGNORECASE):
                                parts = re.split(r"\bfor\b", rest, flags=re.IGNORECASE)
                                item_text = parts[0].strip()
                                buyer_token = parts[1].strip()
                            else:
                                parts = rest.split()
                                if len(parts) >= 2:
                                    buyer_token = parts[-1]
                                    item_text = " ".join(parts[:-1])
                                else:
                                    buyer_token = parsed.raw_splits[0].buyer_name
                                    item_text = rest

                            buyer = buyer_token.strip()
                            if not buyer:
                                buyer = parsed.raw_splits[0].buyer_name
                            if buyer not in newmap:
                                newmap[buyer] = []
                            try:
                                noisy = re.compile(r"\b(please|pls|bro|bhai|bhaiya|brother|sister|pls\.|please\.|bhaiya,)\b", flags=re.IGNORECASE)
                                item_text_clean = noisy.sub("", item_text).strip()
                            except Exception:
                                item_text_clean = item_text.strip()
                            try:
                                cleaned_item_text, _ = normalize_text(item_text_clean)
                                cleaned_item_text = cleaned_item_text.strip()
                            except Exception:
                                cleaned_item_text = item_text_clean.strip()
                            newmap[buyer].append(RawItem(name=cleaned_item_text, qty=qty, unit=unit))

                        rebuilt = []
                        seen = set()
                        for name in [parsed.raw_splits[0].buyer_name] + list(newmap.keys()):
                            if name in seen:
                                continue
                            seen.add(name)
                            items = newmap.get(name, [])
                            rebuilt.append(BuyerSplit(buyer_name=name, raw_items=items))
                        parsed.raw_splits = rebuilt
                        print(f"[INGESTION] permissive-split raw_splits={[ (rs.buyer_name, len(rs.raw_items)) for rs in rebuilt ]}", flush=True)
        except Exception as e:
            print(f"[INGESTION] permissive split failed: {e}", flush=True)

        input_meta = {
            "input_type":    payload_type,
            "raw_input_url": raw_input_url,
            "customer_phone": req.customer_phone,
        }
        final_manifest = orchestrate_order_processing(parsed, input_meta, matcher)
        print(f"[INGESTION] final_manifest.processed_splits={[(s.buyer_name, s.order_total, len(s.items)) for s in final_manifest.processed_splits]}", flush=True)

        # ── 3. PDF (optional) ─────────────────────────────────────────────
        if final_manifest.pdf_requested:
            os.makedirs("shared_billing_dump", exist_ok=True)
            for split in final_manifest.processed_splits:
                pdf_binary = compile_invoice_document(final_manifest, split.buyer_name)
                with open(f"shared_billing_dump/bill_{split.buyer_name}.pdf", "wb") as f:
                    f.write(pdf_binary.read())

        # ── 4. Translate FinalOrderManifest → flat order dict(s) ─────────
        per_person_splits = [s for s in final_manifest.processed_splits if len(s.items) > 0]
        if len(per_person_splits) > 1 and all(len(s.items) > 0 for s in per_person_splits):
            batch_orders = []
            for s in per_person_splits:
                batch_orders.append({
                    "customer_phone": final_manifest.customer_phone,
                    "customer_name": s.buyer_name,
                    "store_id": "store_001",
                    "language": final_manifest.language or language_hint,
                    "items": [{"name": item.item_name, "qty": item.quantity, "unit": item.unit, "unit_price": None} for item in s.items],
                    "split_with": [],
                    "payment_mode": final_manifest.payment_mode,
                    "input_type": final_manifest.input_type,
                    "raw_input_url": final_manifest.raw_input_url,
                    "total_amount": s.order_total,
                })
            return JSONResponse(status_code=200, content={"batch_orders": batch_orders})

        first_split = final_manifest.processed_splits[0] if final_manifest.processed_splits else None
        other_splits = final_manifest.processed_splits[1:] if len(final_manifest.processed_splits) > 1 else []

        split_with_names = [s.buyer_name for s in other_splits]
        if not split_with_names:
            try:
                parsed_names = [s.buyer_name for s in parsed.raw_splits if s.buyer_name and s.buyer_name.lower() != "default"]
                parsed_names = [n for i, n in enumerate(dict.fromkeys(parsed_names))]
                if first_split:
                    parsed_names = [n for n in parsed_names if n.lower() != first_split.buyer_name.lower()]
                split_with_names = parsed_names
            except Exception:
                split_with_names = []

        flat_order = {
            "customer_phone": final_manifest.customer_phone,
            "customer_name": first_split.buyer_name if first_split else "Unknown",
            "store_id": "store_001",
            "language": final_manifest.language or language_hint,
            "items": [{"name": item.item_name, "qty": item.quantity, "unit": item.unit, "unit_price": None} for item in (first_split.items if first_split else [])],
            "split_with": split_with_names,
            "payment_mode": final_manifest.payment_mode,
            "input_type": final_manifest.input_type,
            "raw_input_url": final_manifest.raw_input_url,
            "total_amount": None,
        }

        try:
            numeric_count = len(re.findall(r"\d+(?:\.\d+)?", clean_text))
            if numeric_count == 1 and len(flat_order["items"]) > 1:
                print(f"[INGESTION] single-quantity heuristic: keeping first of {len(flat_order['items'])} items", flush=True)
                flat_order["items"] = [flat_order["items"][0]]
        except Exception:
            pass

        print(f"[INGESTION] returning flat_order with {len(flat_order['items'])} items | lang={flat_order['language']}")
        print(f"[INGESTION] flat_order={flat_order}", flush=True)

        try:
            validated = FlatOrder(**flat_order)
            return JSONResponse(status_code=200, content=validated.model_dump())
        except Exception as e:
            print(f"[INGESTION] ⚠️ Validation failed for flat_order: {e}")
            return JSONResponse(status_code=200, content=flat_order)

    except Exception as e:
        print(f"[INGESTION ERROR] {e}")
        return JSONResponse(status_code=500, content={"error": True, "details": str(e)})