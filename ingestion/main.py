import os
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from ingestion.schema import FinalOrderManifest
from ingestion.utils import normalize_text
from ingestion.gemini import parse_order_text
from ingestion.sarvam import speech_to_text, vision_ocr
from ingestion.sku_match import SKUMatcher
from ingestion.orchestrator import orchestrate_order_processing
from ingestion.pdf_generator import compile_invoice_document

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

app = FastAPI()

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "data", "sku_catalog.json")
matcher = SKUMatcher(CATALOG_PATH)

class ProcessRequest(BaseModel):
    payload_type: str
    payload: str
    customer_phone: str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/process")
async def process(req: ProcessRequest):
    payload_type = req.payload_type
    payload = req.payload
    raw_input_url = None
    clean_text = ""

    # 1. HANDLE MULTIMODAL (Keeps your Twilio/Sarvam Logic!)
    if payload_type == "audio":
        raw_input_url = payload
        try:
            auth = (TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID and TWILIO_TOKEN else None
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(payload, auth=auth)
                r.raise_for_status()
                text, _ = await speech_to_text(r.content)
                clean_text, _ = normalize_text(text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Audio fetch failed: {e}")

    elif payload_type == "image":
        raw_input_url = payload
        try:
            auth = (TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID and TWILIO_TOKEN else None
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(payload, auth=auth)
                r.raise_for_status()
                text, _ = await vision_ocr(r.content)
                clean_text, _ = normalize_text(text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image fetch failed: {e}")

    else:
        clean_text, _ = normalize_text(payload)

    try:
        # 2. RUN BULLETPROOF LLM EXTRACTION
        parsed_structural_json = await parse_order_text(clean_text)
        
        # 3. RUN DETERMINISTIC MATH & SKU MATCHING
        input_meta = {
            "input_type": payload_type, 
            "raw_input_url": raw_input_url,
            "customer_phone": req.customer_phone  # Pass it down!
        }
        final_manifest = orchestrate_order_processing(parsed_structural_json, input_meta, matcher)
        
        # 4. GENERATE PDF IF REQUESTED
        if final_manifest.pdf_requested:
            os.makedirs("shared_billing_dump", exist_ok=True)
            for split in final_manifest.processed_splits:
                pdf_binary = compile_invoice_document(final_manifest, split.buyer_name)
                with open(f"shared_billing_dump/bill_{split.buyer_name}.pdf", "wb") as f:
                    f.write(pdf_binary.read())
        
        return JSONResponse(status_code=200, content=final_manifest.model_dump())
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": True, "details": str(e)})