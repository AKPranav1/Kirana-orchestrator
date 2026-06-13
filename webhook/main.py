from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import httpx
import os

app = FastAPI()

INGESTION_URL = os.getenv("INGESTION_URL", "http://localhost:8001/process")
DB_ALERTS_URL = os.getenv("DB_ALERTS_URL", "http://localhost:8002/log")
SHOPKEEPER_PHONE = os.getenv("SHOPKEEPER_PHONE", "whatsapp:+91XXXXXXXXXX")

@app.post("/webhook")
async def webhook(request: Request):
    form = await request.form()

    media_type = form.get("MediaContentType0", "")
    media_url  = form.get("MediaUrl0", "")
    body       = form.get("Body", "")
    sender     = form.get("From", "")

    if "audio" in media_type:
        payload_type, payload = "audio", media_url
    elif "image" in media_type:
        payload_type, payload = "image", media_url
    else:
        payload_type, payload = "text", body

    print(f"[WEBHOOK] {sender} → type={payload_type} payload={payload[:80]}")

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(INGESTION_URL, json={
            "payload_type": payload_type,
            "payload": payload
        })
        order = r.json()
        print(f"[INGESTION] {order}")

    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(DB_ALERTS_URL, json={
            "order": order,
            "shopkeeper_phone": SHOPKEEPER_PHONE
        })

    twiml = """<?xml version="1.0"?><Response><Message>Order received! We'll get that ready for you.</Message></Response>"""
    return PlainTextResponse(twiml, media_type="application/xml")


@app.get("/health")
async def health():
    return {"status": "ok"}