"""Optional signed WhatsApp adapter; no loopback HTTP between services."""
from datetime import datetime, timezone
import hashlib
import json
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pymongo.errors import DuplicateKeyError
from starlette.concurrency import run_in_threadpool

from backend.domain.orders import DomainError, OrderCommand
from .ingestion import ProcessInput, process
from .orders import submit

router = APIRouter(tags=["optional WhatsApp"])


@router.post("/webhook")
async def webhook(request: Request):
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if not token:
        raise HTTPException(503, "WhatsApp adapter is not configured; use the browser or API")
    try:
        from twilio.request_validator import RequestValidator
    except ImportError as exc:
        raise HTTPException(503, "Install optional provider dependencies to enable WhatsApp") from exc
    form = await request.form()
    url = os.getenv("TWILIO_WEBHOOK_URL") or str(request.url)
    if not RequestValidator(token).validate(url, form, request.headers.get("X-Twilio-Signature", "")):
        raise HTTPException(403, "Invalid Twilio signature")
    sid, sender = str(form.get("MessageSid", "")), str(form.get("From", ""))
    if not 8 <= len(sid) <= 100 or not sender:
        raise HTTPException(422, "MessageSid and sender are required")
    settings = request.app.state.settings
    db = request.app.state.store.db
    key = hashlib.sha256(f"{settings.store_id}:{sid}".encode()).hexdigest()
    fingerprint = hashlib.sha256(json.dumps(sorted((k, str(v)) for k, v in form.multi_items())).encode()).hexdigest()
    event = await run_in_threadpool(db.webhook_events.find_one, {"_id": key})
    if event and event["fingerprint"] != fingerprint:
        raise DomainError("Message ID was reused with different input", 409)
    if event is None:
        content_type = str(form.get("MediaContentType0", ""))
        media = str(form.get("MediaUrl0", ""))
        kind = "audio" if content_type.startswith("audio/") else "image" if content_type.startswith("image/") else "text"
        phone = "".join(c for c in sender if c.isdigit())
        customer = await run_in_threadpool(db.customers.find_one, {"store_id": settings.store_id,
            "customer_phone": {"$in": [sender, phone, "+" + phone]}})
        name = customer["customer_name"] if customer else "Customer +" + phone
        extracted = await process(ProcessInput(request_id=sid, payload_type=kind, payload=media if kind != "text" else str(form.get("Body", "")),
                                              customer_name=name, customer_phone=sender), request)
        event = {"_id": key, "store_id": settings.store_id, "fingerprint": fingerprint, "drafts": extracted["drafts"],
                 "created_at": datetime.now(timezone.utc)}
        try:
            await run_in_threadpool(db.webhook_events.insert_one, event.copy())
        except DuplicateKeyError:
            event = await run_in_threadpool(db.webhook_events.find_one, {"_id": key})
            if event["fingerprint"] != fingerprint:
                raise DomainError("Message ID conflict", 409)
    # Reuse the persisted extraction on retries, even if provider output changes.
    # Each independent buyer order has its own transaction and stable request ID.
    for draft in event["drafts"]:
        command = OrderCommand.model_validate({**draft, "input_type": "whatsapp"})
        await run_in_threadpool(submit, request, command)
    return Response('<?xml version="1.0"?><Response/>', media_type="application/xml")
