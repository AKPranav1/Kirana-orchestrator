import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from ingestion.utils import normalize_text
from ingestion.gemini import parse_order_text
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
    # Optional: caller can hint the user's language so Sarvam STT / OCR
    # uses the right model.  If omitted, Sarvam auto-detects (for audio/image)
    # or gemini.py infers from script (for text).
    language_hint: str = "unknown"


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ingestion", "port": 8001}


@app.post("/process")
async def process(req: ProcessRequest):
    payload_type  = req.payload_type
    payload       = req.payload
    language_hint = req.language_hint or "hi"
    raw_input_url = None
    clean_text    = ""

    # ── 1. MULTIMODAL INGESTION ───────────────────────────────────────────
    if payload_type == "audio":
        raw_input_url = payload
        try:
            auth = (TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID and TWILIO_TOKEN else None
            data = await _fetch_bytes_with_retry(payload, auth=auth, timeout=30)
            # Pass language_hint so Sarvam uses the correct locale model
            text, _ = await speech_to_text(data, language_code=language_hint)
            clean_text, _ = normalize_text(text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Audio fetch failed: {e}")

    elif payload_type == "image":
        raw_input_url = payload
        try:
            auth = (TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID and TWILIO_TOKEN else None
            data = await _fetch_bytes_with_retry(payload, auth=auth, timeout=30)
            # Pass language_hint so Sarvam uses the correct locale OCR model
            text, _ = await vision_ocr(data, language_code=language_hint)
            clean_text, _ = normalize_text(text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image fetch failed: {e}")

    else:
        # Text: normalize handles all Indic scripts natively
        clean_text, _ = normalize_text(payload)

    # ── 2. LLM EXTRACTION + SKU MATCHING ─────────────────────────────────
    try:
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

        # Post-process: split any combined raw_items like
        # "bhaiya, 1kg chawal for me, 1kg atta for Abyud" that LLM returned
        # as a single RawItem into multiple RawItems and assign them to the
        # correct buyer split when "for <name>" is present.
        try:
            # Build a map of buyer_name -> BuyerSplit for easy appends
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
                        # detect "for <name>" or "for me" inside item_text
                        buyer_match = re.search(r"for\s+([\w\u0900-\u097F\-]+)", item_text, flags=re.IGNORECASE)
                        if buyer_match:
                            buyer_token = buyer_match.group(1).strip()
                            if buyer_token.lower() in ("me", "my", "mujhe", "mera", "main"):
                                target_buyer = split.buyer_name
                            else:
                                target_buyer = buyer_token
                            # strip the "for <name>" from item_text
                            item_text = re.sub(r"for\s+[\w\u0900-\u097F\-]+", "", item_text, flags=re.IGNORECASE).strip()
                        else:
                            target_buyer = split.buyer_name

                        # ensure a split exists for the target buyer
                        # normalize buyer token (strip punctuation)
                        target_buyer = re.sub(r"[^\w\u0900-\u097F\-]", "", target_buyer).strip()
                        if target_buyer:
                            # title-case ASCII names to match DB conventions (best-effort)
                            try:
                                if all(ord(c) < 128 for c in target_buyer):
                                    target_buyer = target_buyer.title()
                            except Exception:
                                pass

                        if target_buyer not in split_map:
                            # create a new empty split for this buyer
                            parsed.raw_splits.append(BuyerSplit(buyer_name=target_buyer, raw_items=[]))
                            split_map[target_buyer] = parsed.raw_splits[-1]
                            # ensure new_raw_splits has an entry
                            new_raw_splits[target_buyer] = []

                        # Strip polite/noise tokens (please, bro, bhai etc.) before normalization
                        try:
                            noisy = re.compile(r"\b(please|pls|bro|bhai|bhaiya|brother|sister|pls\.|please\.|bhaiya,)\b", flags=re.IGNORECASE)
                            item_text_clean = noisy.sub("", item_text).strip()
                        except Exception:
                            item_text_clean = item_text.strip()

                        # Normalize item text (multilingual) so SKU matcher has a clean input
                        try:
                            cleaned_item_text, _ = normalize_text(item_text_clean)
                            cleaned_item_text = cleaned_item_text.strip()
                        except Exception:
                            cleaned_item_text = item_text_clean.strip()

                        try:
                            print(f"[INGESTION] append RawItem -> buyer={target_buyer} name={cleaned_item_text!r} qty={qty} unit={unit}", flush=True)
                        except Exception:
                            pass

                        new_raw_splits[target_buyer].append(RawItem(name=cleaned_item_text, qty=qty, unit=unit))

                    if not found:
                        # Attempt to extract a single qty/unit/item from the raw text
                        single_m = qty_item_re.search(text)
                        if single_m:
                            qty = float(single_m.group(1))
                            unit = (single_m.group(2) or "").lower() or None
                            item_text = single_m.group(3).strip()

                            # remove polite/noise tokens
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
                            # No quantity pattern — clean noise and keep original
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

            # Rebuild parsed.raw_splits from new_raw_splits preserving order
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
        # do a more permissive split directly on clean_text to extract segments like
        # "1kg rice Abhi" or "1kg rice for me" and assign per-segment items.
        try:
            if len(parsed.raw_splits) == 1 and len(parsed.raw_splits[0].raw_items) == 1:
                lone = parsed.raw_splits[0].raw_items[0].name or ""
                # quick check: multiple quantity mentions in the raw text
                if len(re.findall(r"\d+(?:\.\d+)?", lone)) >= 2 or len(re.findall(r"\d+(?:\.\d+)?", clean_text)) >= 2:
                    segments = re.findall(r"(\d+(?:\.\d+)?\s*(?:kg|gm|g|litre|l|packet|pc|piece)?\s*[^,]+)(?:,|$)", clean_text, flags=re.IGNORECASE)
                    if not segments:
                        segments = re.findall(r"(\d+(?:\.\d+)?\s*(?:kg|gm|g|litre|l|packet|pc|piece)?\s*[^,]+)(?:,|$)", lone, flags=re.IGNORECASE)
                    if segments and len(segments) > 1:
                        # rebuild splits
                        newmap = {}
                        for seg in segments:
                            seg = seg.strip().rstrip(',')
                            m = re.match(r"(?P<qty>\d+(?:\.\d+)?)(?:\s*(?P<unit>kg|gm|g|litre|l|packet|pc|piece))?\s+(?P<rest>.+)$", seg, flags=re.IGNORECASE)
                            if not m:
                                continue
                            qty = float(m.group('qty'))
                            unit = (m.group('unit') or "").lower() or None
                            rest = m.group('rest').strip()
                            # prefer explicit 'for NAME'
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
                            # Strip polite/noise tokens from permissive-segment item_text
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

                            try:
                                print(f"[INGESTION] permissive append -> buyer={buyer} name={cleaned_item_text!r} qty={qty} unit={unit}", flush=True)
                            except Exception:
                                pass

                            newmap[buyer].append(RawItem(name=cleaned_item_text, qty=qty, unit=unit))

                        # Build new parsed.raw_splits preserving original order where possible
                        rebuilt = []
                        seen = set()
                        # ensure primary existing split first
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
                with open(
                    f"shared_billing_dump/bill_{split.buyer_name}.pdf", "wb"
                ) as f:
                    f.write(pdf_binary.read())

        # ── 4. Translate FinalOrderManifest → flat order dict(s) ─────────
        # If this is a per-person split (each processed_split has its own items),
        # return a batch of flat orders (one per person). Otherwise return a
        # single flat order representing the first split (primary customer's bill).
        per_person_splits = [s for s in final_manifest.processed_splits if len(s.items) > 0]
        if len(per_person_splits) > 1 and all(len(s.items) > 0 for s in per_person_splits):
            batch_orders = []
            for s in per_person_splits:
                batch_orders.append(
                    {
                        "customer_phone": final_manifest.customer_phone,
                        "customer_name": s.buyer_name,
                        "store_id": "store_001",
                        "language": final_manifest.language or language_hint,
                        "items": [
                            {
                                "name": item.item_name,
                                "qty": item.quantity,
                                "unit": item.unit,
                                "unit_price": None,
                            }
                            for item in s.items
                        ],
                        "split_with": [],
                        "payment_mode": final_manifest.payment_mode,
                        "input_type": final_manifest.input_type,
                        "raw_input_url": final_manifest.raw_input_url,
                        "total_amount": s.order_total,
                    }
                )
            return JSONResponse(status_code=200, content={"batch_orders": batch_orders})

        # Fallback: single flat order for the primary customer
        first_split  = (
            final_manifest.processed_splits[0]
            if final_manifest.processed_splits else None
        )
        other_splits = (
            final_manifest.processed_splits[1:]
            if len(final_manifest.processed_splits) > 1 else []
        )

        # Build flat_order. Ensure split_with is populated even if orchestrator
        # returned a single processed_split (fallback to parsed raw_splits names).
        other_splits = (
            final_manifest.processed_splits[1:]
            if len(final_manifest.processed_splits) > 1 else []
        )

        split_with_names = [s.buyer_name for s in other_splits]
        # Fallback: if orchestrator returned only one split but parsed hinted at extra parties,
        # derive names from parsed.raw_splits (excluding 'default' which maps to primary later).
        if not split_with_names:
            try:
                parsed_names = [s.buyer_name for s in parsed.raw_splits if s.buyer_name and s.buyer_name.lower() != "default"]
                # remove duplicates and any name equal to first_split (if present)
                parsed_names = [n for i, n in enumerate(dict.fromkeys(parsed_names))]
                # exclude primary/first split name if present
                if first_split:
                    parsed_names = [n for n in parsed_names if n.lower() != first_split.buyer_name.lower()]
                split_with_names = parsed_names
            except Exception:
                split_with_names = []

        flat_order = {
            "customer_phone": final_manifest.customer_phone,
            "customer_name":  first_split.buyer_name if first_split else "Unknown",
            "store_id":       "store_001",
            # Use the language Gemini detected; fall back to hint if not set
            "language":       final_manifest.language or language_hint,
            "items": [
                {
                    "name":       item.item_name,
                    "qty":        item.quantity,
                    "unit":       item.unit,
                    "unit_price": None,   # Person 3 enriches from STORE_PRICES
                }
                for item in (first_split.items if first_split else [])
            ],
            "split_with":    split_with_names,
            "payment_mode":  final_manifest.payment_mode,
            "input_type":    final_manifest.input_type,
            "raw_input_url": final_manifest.raw_input_url,
            "total_amount":  None,        # Person 3 computes after price enrichment
        }

        # Heuristics: do NOT mutate item quantities when splitting. Keep the
        # original requested quantities (e.g. 1kg rice) and let downstream
        # services compute monetary splits. We will, however, apply a
        # conservative single-quantity heuristic to drop hallucinated extra items.
        try:
            numeric_count = len(re.findall(r"\d+(?:\.\d+)?", clean_text))
            if numeric_count <= 1 and len(flat_order["items"]) > 1:
                print(f"[INGESTION] single-quantity heuristic: keeping first of {len(flat_order['items'])} items", flush=True)
                flat_order["items"] = [flat_order["items"][0]]
        except Exception:
            pass

        print(f"[INGESTION] returning flat_order with {len(flat_order['items'])} items "
              f"| lang={flat_order['language']}")
        print(f"[INGESTION] flat_order={flat_order}", flush=True)

        # Validate output against FlatOrder model before returning
        try:
            validated = FlatOrder(
                customer_phone = flat_order.get("customer_phone", "unknown"),
                customer_name  = flat_order.get("customer_name", "Unknown"),
                store_id       = flat_order.get("store_id", "store_001"),
                language       = flat_order.get("language", "hi"),
                items          = flat_order.get("items", []),
                split_with     = flat_order.get("split_with", []),
                payment_mode   = flat_order.get("payment_mode", "cash"),
                input_type     = flat_order.get("input_type"),
                raw_input_url  = flat_order.get("raw_input_url"),
                total_amount   = flat_order.get("total_amount"),
            )
            return JSONResponse(status_code=200, content=validated.model_dump())
        except Exception as e:
            print(f"[INGESTION] ⚠️ Validation failed for flat_order: {e}")
            return JSONResponse(status_code=200, content=flat_order)

    except Exception as e:
        print(f"[INGESTION ERROR] {e}")
        return JSONResponse(
            status_code=500, content={"error": True, "details": str(e)}
        )
