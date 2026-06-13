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


async def _fetch_bytes_with_retry(url: str, auth=None, timeout=30, retries=2):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(url, auth=auth)
                r.raise_for_status()
                return r.content
        except Exception as e:
            last_exc = e
            await asyncio.sleep(0.5 * (attempt + 1))
    raise last_exc


# ------------------ Flat Order Model (enforced at /process output) ------------------
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


TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

app = FastAPI(title="Kirana AI — Ingestion", version="1.0.0")

# Allow CORS for local frontend during development
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


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ingestion", "port": 8001}


@app.post("/process")
async def process(req: ProcessRequest):
    payload_type = req.payload_type
    payload = req.payload
    raw_input_url = None
    clean_text = ""

    # ── 1. MULTIMODAL INGESTION ────────────────────────────────────
    if payload_type == "audio":
        raw_input_url = payload
        try:
            auth = (TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID and TWILIO_TOKEN else None
            data = await _fetch_bytes_with_retry(payload, auth=auth, timeout=30)
            text, _ = await speech_to_text(data)
            clean_text, _ = normalize_text(text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Audio fetch failed: {e}")

    elif payload_type == "image":
        raw_input_url = payload
        try:
            auth = (TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID and TWILIO_TOKEN else None
            data = await _fetch_bytes_with_retry(payload, auth=auth, timeout=30)
            text, _ = await vision_ocr(data)
            clean_text, _ = normalize_text(text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image fetch failed: {e}")

    else:
        clean_text, _ = normalize_text(payload)

    # ── 2. LLM EXTRACTION + SKU MATCHING ──────────────────────────
    try:
        parsed = await parse_order_text(clean_text)

        input_meta = {
            "input_type": payload_type,
            "raw_input_url": raw_input_url,
            "customer_phone": req.customer_phone,
        }
        final_manifest = orchestrate_order_processing(parsed, input_meta, matcher)

        # ── 3. PDF (optional) ──────────────────────────────────────
        if final_manifest.pdf_requested:
            os.makedirs("shared_billing_dump", exist_ok=True)
            for split in final_manifest.processed_splits:
                pdf_binary = compile_invoice_document(final_manifest, split.buyer_name)
                with open(
                    f"shared_billing_dump/bill_{split.buyer_name}.pdf", "wb"
                ) as f:
                    f.write(pdf_binary.read())

        # ── 4. Translate FinalOrderManifest → flat order dict ──────
        # Person 3's mongo_connector expects flat dict with "items" key.
        # FinalOrderManifest uses "processed_splits" — this bridges the gap.
        first_split = (
            final_manifest.processed_splits[0]
            if final_manifest.processed_splits
            else None
        )
        other_splits = (
            final_manifest.processed_splits[1:]
            if len(final_manifest.processed_splits) > 1
            else []
        )

        flat_order = {
            "customer_phone": final_manifest.customer_phone,
            "customer_name": first_split.buyer_name if first_split else "Unknown",
            "store_id": "store_001",
            "language": final_manifest.language,
            "items": [
                {
                    "name": item.item_name,
                    "qty": item.quantity,
                    "unit": item.unit,
                    "unit_price": None,  # Person 3 enriches from STORE_PRICES
                }
                for item in (first_split.items if first_split else [])
            ],
            "split_with": [s.buyer_name for s in other_splits],
            "payment_mode": final_manifest.payment_mode,
            "input_type": final_manifest.input_type,
            "raw_input_url": final_manifest.raw_input_url,
            "total_amount": None,  # Person 3 computes after price enrichment
        }

        print(f"[INGESTION] returning flat_order with {len(flat_order['items'])} items")
        # Validate output against FlatOrder model before returning
        try:
            validated = FlatOrder(
                customer_phone=flat_order.get("customer_phone", "unknown"),
                customer_name=flat_order.get("customer_name", "Unknown"),
                store_id=flat_order.get("store_id", "store_001"),
                language=flat_order.get("language", "hi"),
                items=flat_order.get("items", []),
                split_with=flat_order.get("split_with", []),
                payment_mode=flat_order.get("payment_mode", "cash"),
                input_type=flat_order.get("input_type"),
                raw_input_url=flat_order.get("raw_input_url"),
                total_amount=flat_order.get("total_amount"),
            )
            return JSONResponse(status_code=200, content=validated.model_dump())
        except Exception as e:
            print(f"[INGESTION] ⚠️ Validation failed for flat_order: {e}")
            # Return unvalidated payload for backward compatibility but log warning
            return JSONResponse(status_code=200, content=flat_order)

    except Exception as e:
        print(f"[INGESTION ERROR] {e}")
        return JSONResponse(status_code=500, content={"error": True, "details": str(e)})
