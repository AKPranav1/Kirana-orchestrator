"""Uncommitted text/media extraction. A separate order command performs the write."""
import asyncio
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Request, UploadFile
from pydantic import Field

from backend.adapters.media import MAX_MEDIA_BYTES, fetch_media
from backend.domain.orders import DomainError, InputModel
from ingestion.gemini import parse_order_text
from ingestion.orchestrator import orders_from_parsed
from ingestion.sarvam import speech_to_text, vision_ocr
from ingestion.sku_match import SKUMatcher
from ingestion.utils import normalize_text

router = APIRouter(tags=["extraction"])
matcher = SKUMatcher(str(Path(__file__).parents[2] / "ingestion/data/sku_catalog.json"))


class ProcessInput(InputModel):
    request_id: str = Field(min_length=8, max_length=120)
    payload_type: Literal["text", "audio", "image"]
    payload: str = Field(min_length=1, max_length=8000)
    customer_name: str = Field("Walk-in", min_length=1, max_length=100)
    customer_phone: str = Field("", max_length=40)
    language_hint: str = Field("unknown", max_length=10)


@router.post("/process")
async def process(body: ProcessInput, request: Request):
    demo = request.app.state.settings.demo_mode
    if body.payload_type == "text":
        text = body.payload
    else:
        content, content_type = await fetch_media(body.payload)
        if body.payload_type == "audio":
            text, _ = await speech_to_text(content, body.language_hint, content_type=content_type, allow_demo=demo)
        else:
            text, _ = await vision_ocr(content, allow_demo=demo)
    text, _ = normalize_text(text)
    if not text.strip():
        raise DomainError("No text recognized; try again or use manual entry")
    try:
        parsed = await asyncio.wait_for(parse_order_text(text, allow_demo=demo), timeout=35)
    except TimeoutError as exc:
        raise DomainError("Extraction timed out; use manual entry or retry", 504) from exc
    commands = orders_from_parsed(parsed, customer_name=body.customer_name, customer_phone=body.customer_phone,
                                 request_id=body.request_id, matcher=matcher, store_id=request.app.state.settings.store_id)
    drafts = [command.model_dump(mode="json") for command in commands]
    return {"drafts": drafts, "committed": False, "demo_mode": demo}


@router.post("/transcribe")
async def transcribe(request: Request, audio: UploadFile = File(...)):
    content = await audio.read(MAX_MEDIA_BYTES + 1)
    await audio.close()
    if not content or len(content) > MAX_MEDIA_BYTES:
        raise DomainError("Upload a recording between 1 byte and 10 MB", 413)
    if audio.content_type not in ("audio/ogg", "audio/webm", "audio/wav", "audio/mpeg", "audio/mp4"):
        raise DomainError("Unsupported recording format")
    text, metadata = await speech_to_text(content, filename=audio.filename or "recording",
        content_type=audio.content_type, allow_demo=request.app.state.settings.demo_mode)
    return {"transcript": text, "demo": bool(metadata.get("mock")), "committed": False}
