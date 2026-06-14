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
                "customer_phone": sender,
                "customer_name": "",  # Will be populated from profile_name if available
            })
            ingestion_resp = r.json()
            print(f"[INGESTION] {ingestion_resp}")
            
            # Case 1: Khata balance inquiry response
            if isinstance(ingestion_resp, dict) and ingestion_resp.get("type") == "khata_balance":
                msg = ingestion_resp.get("message") or "Here is your khata balance."
                await client.post(DB_ALERTS_URL, json={
                    "order": {"customer_phone": sender, "customer_name": ingestion_resp.get("customer_name"), "items": [], "payment_mode": "khata"},
                    "shopkeeper_phone": sender,
                    "profile_name": profile_name,
                    "direct_message": msg,
                })
                twiml = """<?xml version="1.0"?><Response><Message>हमने आपकी खाता जानकारी भेज दी है।</Message></Response>"""
                return PlainTextResponse(twiml, media_type="application/xml")
            
            # Case 2: Batch orders (multiple people splitting)
            elif isinstance(ingestion_resp, dict) and "batch_orders" in ingestion_resp:
                batch_orders = ingestion_resp["batch_orders"]
                print(f"[WEBHOOK] Processing {len(batch_orders)} batch orders...")
                
                # Send EACH order individually to Person 3
                for single_order in batch_orders:
                    # Ensure phone number is properly formatted
                    customer_phone = single_order.get("customer_phone", sender)
                    if not customer_phone.startswith("whatsapp:"):
                        customer_phone = f"whatsapp:{customer_phone}"
                    
                    await client.post(DB_ALERTS_URL, json={
                        "order": single_order,
                        "shopkeeper_phone": customer_phone,  # Send receipt to the customer
                        "profile_name": profile_name,
                    })
                    print(f"[DB+ALERT] Batch order sent for {single_order.get('customer_name')} (to={customer_phone})")
                
                twiml = """<?xml version="1.0"?><Response><Message>Order split confirmed! Receipts sent.</Message></Response>"""
                return PlainTextResponse(twiml, media_type="application/xml")
            
            # Case 3: Single order
            else:
                order = ingestion_resp
                async with httpx.AsyncClient(timeout=30) as client2:
                    destination_phone = sender if sender else SHOPKEEPER_PHONE
                    await client2.post(DB_ALERTS_URL, json={
                        "order": order,
                        "shopkeeper_phone": destination_phone,
                        "profile_name": profile_name,
                    })
                    print(f"[DB+ALERT] Single order forwarded to Person 3 (to={destination_phone})")
                
                twiml = """<?xml version="1.0"?><Response><Message>Order received! We'll get that ready for you.</Message></Response>"""
                return PlainTextResponse(twiml, media_type="application/xml")
                
    except Exception as e:
        print(f"[WEBHOOK ERROR] {e}")
        twiml = """<?xml version="1.0"?><Response><Message>Sorry, we couldn't process your order. Please try again.</Message></Response>"""
        return PlainTextResponse(twiml, media_type="application/xml")


@app.get("/health")
async def health():
    return {"status": "ok"}