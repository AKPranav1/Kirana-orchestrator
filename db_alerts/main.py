"""
main.py — Kirana AI | Person 3 | Port 8002
FastAPI service: receives order JSON from Person 1 → logs to MongoDB
(with dynamic pricing + auto discount) → fires emotion-aware
ElevenLabs/Twilio alert + text receipt → tracks loyalty
+ exposes Vasooli (debt collection) endpoint
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import joblib
from pathlib import Path
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from mongo_connector import log_order as db_log_order, get_khata_balance
from alerts import send_alert, send_vasooli_alert, create_text_bill

load_dotenv()

# ── Audio directory (MP3s served from here) ────────────────────────────────────
AUDIO_DIR = Path(__file__).parent / "audio_files"
AUDIO_DIR.mkdir(exist_ok=True)

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Kirana AI — DB & Alerts",
    description="Person 3 service: MongoDB persistence + dynamic pricing + ElevenLabs + Twilio WhatsApp alert",
    version="2.0.0",
)

# Mount audio_files/ as a static endpoint so Twilio can fetch the MP3s
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")

# CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Forecasts payload (produced by ML training script)
MODEL_FILE = Path(__file__).parent / "model_forecasts.pkl"
_forecasts_payload = None
if MODEL_FILE.exists():
    try:
        _forecasts_payload = joblib.load(MODEL_FILE)
        print(f"[forecast] Loaded forecasts payload with {len(_forecasts_payload)} entries")
    except Exception as e:
        print(f"[forecast] Failed to load forecasts payload: {e}")


# ── Request models ─────────────────────────────────────────────────────────────
class LogRequest(BaseModel):
    order:            dict
    shopkeeper_phone: str


class VasooliRequest(BaseModel):
    customer_name:  str
    customer_phone: str
    store_id:       str = "store_001"


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
def health_check():
    """Quick ping — confirms the service is alive."""
    return {
        "status":  "ok",
        "service": "db-alerts",
        "port":    8002,
    }


@app.get("/ping-mongo", tags=["health"])
def ping_mongo():
    """Verify that MongoDB Atlas is reachable."""
    from mongo import _get_db
    try:
        db   = _get_db()
        info = db.client.server_info()
        return {"status": "ok", "mongo_version": info.get("version")}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MongoDB unreachable: {e}")


@app.post("/log", tags=["core"])
async def log_endpoint(req: LogRequest):
    """
    Main endpoint called by Person 1.
    Sequence:
      1. DB Logic (prices, discount, khata, loyalty)
      2. ElevenLabs + Twilio (emotion-aware + receipt)
    """
    print("\n" + "="*60)
    print(f"[/log] 📥 Incoming order: {req.order}")
    print(f"[/log]    Shopkeeper phone: {req.shopkeeper_phone}")
    print("="*60)

    try:
        # ── Step 1-4: MongoDB (pricing, discount, khata, loyalty) ──
        # This MUST succeed to record the order.
        order_id, order_doc = db_log_order(req.order, req.shopkeeper_phone)

        # ── Step 5-6: ElevenLabs + Twilio (emotion-aware + receipt) ─
        # 🛡️ SAFETY FIX 2: The API Domino Effect Preventer
        # If Twilio or ElevenLabs goes down, we catch it here so the database
        # still saves the order and Person 1 still gets a 200 OK response.
        alert_status = "success"
        try:
            send_alert(order_doc, req.shopkeeper_phone)
        except Exception as api_error:
            print(f"[/log] ⚠️ DB saved, but Alert failed: {api_error}")
            alert_status = f"failed_to_send_alert: {api_error}"

        print(f"[/log] ✅ Done — order_id={order_id} total=₹{order_doc.get('total_amount')}\n")

        # Serialize datetime for JSON response
        response_order = dict(order_doc)
        response_order["created_at"] = str(response_order.get("created_at", ""))

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "alert_status": alert_status,  # Let the frontend know if audio failed
                "order_id": order_id,
                "order": response_order,
            },
        )

    except Exception as e:
        print(f"[/log] ❌ CRITICAL ERROR: {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/khata/{customer_name}", tags=["read"])
def get_khata(customer_name: str, store_id: str = "store_001"):
    """Fetch outstanding Khata balance for a customer."""
    doc = get_khata_balance(customer_name, store_id)
    if not doc:
        raise HTTPException(404, detail=f"No khata found for {customer_name}")
    doc["last_updated"] = str(doc.get("last_updated", ""))
    for e in doc.get("entries", []):
        e["date"] = str(e.get("date", ""))
    return doc


@app.get("/orders", tags=["read"])
def list_orders(limit: int = 10):
    """Fetch the last N orders."""
    from mongo import _get_db
    db     = _get_db()
    cursor = db["orders"].find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    docs   = []
    for d in cursor:
        d["created_at"] = str(d.get("created_at", ""))
        docs.append(d)
    return {"count": len(docs), "orders": docs}


@app.get("/orders/{order_id}/receipt", tags=["read"])
def get_receipt(order_id: str):
    """Returns the formatted text receipt for a given order."""
    from mongo import _get_db
    db  = _get_db()
    doc = db["orders"].find_one({"order_id": order_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, detail=f"No order found with id {order_id}")
    return {"order_id": order_id, "receipt": create_text_bill(doc)}


@app.get("/customers/leaderboard", tags=["read"])
def get_loyalty_leaderboard(limit: int = 10, store_id: str = "store_001"):
    """"Top Loyal Customers" leaderboard, sorted by lifetime_spend."""
    from mongo import _get_db
    db     = _get_db()
    cursor = (
        db["customers"]
        .find({"store_id": store_id}, {"_id": 0})
        .sort("lifetime_spend", -1)
        .limit(limit)
    )
    docs = []
    for d in cursor:
        d["last_order_at"] = str(d.get("last_order_at", ""))
        docs.append(d)
    return {"count": len(docs), "customers": docs}


@app.get("/forecast", tags=["ml"])
def get_forecast(limit: int = 50):
    """
    Return per-SKU forecasts produced by offline ML training.
    The ML training script serializes a ready-to-serve list into db_alerts/model_forecasts.pkl
    which this endpoint loads at startup.
    """
    global _forecasts_payload
    if _forecasts_payload is None:
        raise HTTPException(status_code=503, detail="Forecasts not available (model not trained)")
    try:
        return _forecasts_payload[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard", tags=["read"])
def dashboard_metrics():
    """Derived aggregates used by the frontend dashboard."""
    from mongo import _get_db
    import datetime

    db = _get_db()
    today = datetime.datetime.utcnow().date()
    start_of_day = datetime.datetime.combine(today, datetime.time.min)

    # Sum today's orders revenue
    cursor = db["orders"].find({"created_at": {"$gte": start_of_day}}, {"total_amount": 1})
    todays_revenue = sum(o.get("total_amount", 0) for o in cursor)
    todays_orders_count = db["orders"].count_documents({"created_at": {"$gte": start_of_day}})

    outstanding_khata = 0.0
    for k in db["khata"].find({}, {"total_outstanding": 1}):
        outstanding_khata += k.get("total_outstanding", 0)

    return {
        "todaysRevenue": round(todays_revenue, 2),
        "todaysOrdersCount": int(todays_orders_count),
        "outstandingKhata": round(outstanding_khata, 2),
        "lowStockItemsCount": 0,
        "pendingDeliveriesCount": 0,
        "pendingSupplierPay": 0,
        "storeHealthScore": 94,
    }


@app.post("/vasooli", tags=["core"])
async def vasooli_endpoint(req: VasooliRequest):
    """Automated debt collection voice note triggered by shopkeeper."""
    print("\n" + "="*60)
    print(f"[/vasooli] 📥 Collection request for: {req.customer_name}")
    print("="*60)

    # 🛡️ SAFETY FIX 1: The "Missing Phone Number" crash preventer
    # Stops Twilio from crashing if the AI didn't catch the customer's phone number
    if not req.customer_phone or len(req.customer_phone) < 10:
        print("[/vasooli] ❌ ERROR: Invalid or missing customer phone number.")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": f"Cannot send Vasooli alert: valid phone number required for {req.customer_name}."
            }
        )

    khata_doc = get_khata_balance(req.customer_name, req.store_id)

    if not khata_doc:
        raise HTTPException(404, detail=f"No khata found for {req.customer_name}")

    outstanding = khata_doc.get("total_outstanding", 0)

    if outstanding <= 0:
        return JSONResponse(
            status_code=200,
            content={
                "status": "no_dues",
                "message": f"{req.customer_name} has no outstanding balance. 🎉",
                "outstanding": outstanding,
            },
        )

    try:
        audio_filename = send_vasooli_alert(req.customer_name, req.customer_phone, outstanding)

        print(f"[/vasooli] ✅ Reminder sent to {req.customer_name} (₹{outstanding})\n")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "customer_name": req.customer_name,
                "outstanding": outstanding,
                "audio_file": audio_filename,
            },
        )
    except Exception as e:
        print(f"[/vasooli] ❌ ERROR: {e}\n")
        raise HTTPException(status_code=500, detail=str(e))
