from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import httpx
import os

app = FastAPI()

INGESTION_URL = os.getenv("INGESTION_URL", "http://localhost:8001/process")
DB_ALERTS_URL = os.getenv("DB_ALERTS_URL", "http://localhost:8002/log")
SHOPKEEPER_PHONE = os.getenv("SHOPKEEPER_PHONE", "whatsapp:+919986013436")


@app.on_event("startup")
async def startup_check():
    # Basic validation of configured endpoints to help developers catch misconfiguration early
    if not INGESTION_URL:
        raise RuntimeError("INGESTION_URL not configured")
    if not DB_ALERTS_URL:
        raise RuntimeError("DB_ALERTS_URL not configured")


@app.post("/webhook")
async def webhook(request: Request):
    form = await request.form()

    body = form.get("Body", "")
    sender = form.get("From", "")
    num_media = int(form.get("NumMedia", 0))
    media_url = form.get("MediaUrl0", "") if num_media > 0 else ""
    media_type = form.get("MediaContentType0", "") if num_media > 0 else ""

    if num_media > 0 and "audio" in media_type:
        payload_type, payload = "audio", media_url
    elif num_media > 0 and "image" in media_type:
        payload_type, payload = "image", media_url
    else:
        payload_type, payload = "text", body

    print(f"[WEBHOOK] {sender} → type={payload_type} payload={payload[:80]}...")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                INGESTION_URL,
                json={
                    "payload_type": payload_type,
                    "payload": payload,
                    "customer_phone": sender,  # FIX: pass sender as customer_phone
                },
            )
            try:
                r.raise_for_status()
                order = r.json()
            except Exception as ex:
                # Log and continue with empty order to avoid breaking webhook flow
                print(
                    f"[INGESTION ERROR] invalid response from ingestion: {ex} | status={getattr(r, 'status_code', None)} | text={getattr(r, 'text', '')[:200]}"
                )
                order = {}
            print(f"[INGESTION] {order}")
    except Exception as e:
        print(f"[INGESTION ERROR] {e}")
        order = {}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(
                DB_ALERTS_URL,
                json={"order": order, "shopkeeper_phone": SHOPKEEPER_PHONE},
            )
            print(f"[DB+ALERT] order forwarded to Person 3")
    except Exception as e:
        print(f"[DB+ALERT ERROR] {e}")

    twiml = """<?xml version="1.0"?><Response><Message>Order received! We'll get that ready for you.</Message></Response>"""
    return PlainTextResponse(twiml, media_type="application/xml")


@app.get("/health")
async def health():
    return {"status": "ok"}
