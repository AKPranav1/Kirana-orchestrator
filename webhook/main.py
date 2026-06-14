from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import httpx
import os

app = FastAPI()

INGESTION_URL = os.getenv("INGESTION_URL", "http://localhost:8001/process")
DB_ALERTS_URL = os.getenv("DB_ALERTS_URL", "http://localhost:8002/log")
SHOPKEEPER_PHONE = os.getenv("SHOPKEEPER_PHONE", "whatsapp:+919986013436")


@app.post("/webhook")
async def webhook(request: Request):
    form = await request.form()

    body       = form.get("Body", "")
    sender     = form.get("From", "")
    num_media  = int(form.get("NumMedia", 0))
    media_url  = form.get("MediaUrl0", "") if num_media > 0 else ""
    media_type = form.get("MediaContentType0", "") if num_media > 0 else ""
    profile_name = form.get("ProfileName") or form.get("Profile") or ""
    profile_name = profile_name.strip() if profile_name else ""

    if num_media > 0 and "audio" in media_type:
        payload_type, payload = "audio", media_url
    elif num_media > 0 and "image" in media_type:
        payload_type, payload = "image", media_url
    else:
        payload_type, payload = "text", body

    print(f"[WEBHOOK] {sender} → type={payload_type} payload={payload[:80]}...")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(INGESTION_URL, json={
                "payload_type": payload_type,
                "payload": payload,
                "customer_phone": sender,  # FIX: pass sender as customer_phone
            })
            ingestion_resp = r.json()
            print(f"[INGESTION] {ingestion_resp}")
            # If ingestion directly returned a khata balance response, send it back to the user
            if isinstance(ingestion_resp, dict) and ingestion_resp.get("type") == "khata_balance":
                # Send the message back to the customer and short-circuit
                msg = ingestion_resp.get("message") or "Here is your khata balance."
                # POST to DB_ALERTS_URL/log to reuse receipt-sending path but mark as simple text
                await client.post(DB_ALERTS_URL, json={
                    "order": {"customer_phone": sender, "customer_name": ingestion_resp.get("customer_name"), "items": [], "payment_mode": "khata"},
                    "shopkeeper_phone": sender,
                    "profile_name": profile_name,
                    "direct_message": msg,
                })
                # Return early since we've handled the webhook
                twiml = """<?xml version="1.0"?><Response><Message>हमने आपकी खाता जानकारी भेज दी है।</Message></Response>"""
                return PlainTextResponse(twiml, media_type="application/xml")
            else:
                order = ingestion_resp  # normal order flow — pass downstream
    except Exception as e:
        print(f"[INGESTION ERROR] {e}")
        order = {}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Send the receipt to the WhatsApp sender (customer) when available;
            # fall back to the configured SHOPKEEPER_PHONE for safety.
            destination_phone = sender if sender else SHOPKEEPER_PHONE
            await client.post(DB_ALERTS_URL, json={
                "order": order,
                "shopkeeper_phone": destination_phone,
                "profile_name": profile_name,
            })
            print(f"[DB+ALERT] order forwarded to Person 3 (to={destination_phone})")
    except Exception as e:
        print(f"[DB+ALERT ERROR] {e}")

    twiml = """<?xml version="1.0"?><Response><Message>Order received! We'll get that ready for you.</Message></Response>"""
    return PlainTextResponse(twiml, media_type="application/xml")


@app.get("/health")
async def health():
    return {"status": "ok"}
