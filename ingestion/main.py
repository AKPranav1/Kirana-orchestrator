import os
import uuid
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from schema import Order, Item
from utils import normalize_text
from gemini import extract_order_from_text
from sarvam import speech_to_text, vision_ocr
from sku_match import SKUMatcher

app = FastAPI()

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "data", "sku_catalog.json")
matcher = SKUMatcher(CATALOG_PATH)


class ProcessRequest(BaseModel):
    payload_type: str
    payload: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/process")
async def process(req: ProcessRequest):
    payload_type = req.payload_type
    payload = req.payload
    raw_input_url = None
    clean_text = ""
    debug = {"steps": []}

    # fetch media if needed
    if payload_type == "audio":
        raw_input_url = payload
        # fetch bytes
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(payload)
                r.raise_for_status()
                audio_bytes = r.content
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"failed to fetch audio: {e}")

        text, meta = await speech_to_text(audio_bytes)
        debug["stt_meta"] = meta
        clean_text, md = normalize_text(text)
        debug["normalize_md"] = md

    elif payload_type == "image":
        raw_input_url = payload
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(payload)
                r.raise_for_status()
                img_bytes = r.content
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"failed to fetch image: {e}")

        text, meta = await vision_ocr(img_bytes)
        debug["ocr_meta"] = meta
        clean_text, md = normalize_text(text)
        debug["normalize_md"] = md

    else:
        # assume text
        clean_text, md = normalize_text(payload)
        debug["normalize_md"] = md

    # call Gemini
    parsed, raw = await extract_order_from_text(clean_text, debug=bool(os.getenv("DEBUG")))
    debug["gemini_raw"] = raw

    # build Order
    order = Order(
        customer_phone=parsed.get("customer_phone"),
        store_id=parsed.get("store_id"),
        items=[],
        split_with=parsed.get("split_with"),
        payment_mode=parsed.get("payment_mode"),
        input_type=payload_type,
        raw_input_url=raw_input_url,
        error=parsed.get("error", False),
        debug=debug,
    )

    for it in parsed.get("items", []):
        name = it.get("name") or ""
        qty = float(it.get("qty") or 0)
        unit = it.get("unit")
        canon, canon_unit, score = matcher.match(name)
        if canon_unit and not unit:
            unit = canon_unit
        item = Item(name=canon, qty=qty, unit=unit, unit_price=None, match_score=score, original_name=name)
        order.items.append(item)

    return JSONResponse(order.dict())
