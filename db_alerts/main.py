"""
main.py — Kirana AI | Person 3 | Port 8002
FastAPI service: receives order JSON from Person 1 → MongoDB (pricing + khata + loyalty)
                 → WhatsApp text receipt (always) → Vasooli voice note (if debt > ₹1500)
                 → /forecast endpoint (serialized ML payload)
                 → /dashboard aggregates for React frontend
"""

import os
import datetime
from pathlib import Path

import joblib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from mongo_connector import (
    log_order           as db_log_order,
    get_khata_balance,
    increment_reminder_count,
    get_db,
)
from alerts import send_receipt_only, send_vasooli_alert, create_text_bill

load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────────
AUDIO_DIR         = Path(__file__).parent / "audio_files"
AUDIO_DIR.mkdir(exist_ok=True)

DEBT_WARNING_LIMIT = 1500.0

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Kirana AI — DB & Alerts",
    description=(
        "Person 3: MongoDB persistence + dynamic pricing + "
        "multilingual receipts + escalating Vasooli + ML forecasts"
    ),
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your Vite origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated MP3s so Twilio can download them
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")

# ── Load ML forecasts at startup ───────────────────────────────────────────────
MODEL_FILE = Path(__file__).parent / "model_forecasts.pkl"
_forecasts_payload = None

if MODEL_FILE.exists():
    try:
        _forecasts_payload = joblib.load(MODEL_FILE)
        print(f"[forecast] ✅ Loaded {len(_forecasts_payload)} forecast entries")
    except Exception as e:
        print(f"[forecast] ⚠️ Failed to load forecasts payload: {e}")
else:
    print("[forecast] ℹ️ model_forecasts.pkl not found — /forecast will return 503 until trained")


# ── Request models ─────────────────────────────────────────────────────────────
class LogRequest(BaseModel):
    order:            dict
    shopkeeper_phone: str


class VasooliRequest(BaseModel):
    customer_name:  str
    customer_phone: str
    store_id:       str = "store_001"
    language:       str = "hi"   # Sarvam language code: hi / kn / en / ta / te


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "service": "db-alerts", "port": 8002}


@app.get("/ping-mongo", tags=["health"])
def ping_mongo():
    """Verify MongoDB Atlas connectivity before the demo."""
    try:
        db   = get_db()
        info = db.client.server_info()
        return {"status": "ok", "mongo_version": info.get("version")}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MongoDB unreachable: {e}")


# ── Core: Receive Order ────────────────────────────────────────────────────────
@app.post("/log", tags=["core"])
async def log_endpoint(req: LogRequest):
    """
    Called by Person 1's webhook router after an order arrives.

    Sequence:
      1. MongoDB: price enrichment + khata split + loyalty update  (must succeed)
      2. Twilio:  text receipt → shopkeeper                        (always)
      3. Twilio:  Vasooli voice note → customer                    (only if khata debt > ₹1500)

    DB write failure  → 500  (Person 1 must know)
    Alert failure     → 200 with alert_status describing the error (DB is safe, don't cascade)
    """
    print(
        f"\n[/log] 📥 {req.order.get('customer_name')} | "
        f"₹{req.order.get('total_amount')} | mode={req.order.get('payment_mode')}"
    )

    try:
        # Step 1: MongoDB (critical — must succeed before anything else)
        order_id, order_doc, highest_debt = db_log_order(req.order, req.shopkeeper_phone)

        alert_status = "success"

        try:
            # Step 2: Text receipt to shopkeeper (no audio for normal orders)
            send_receipt_only(order_doc, req.shopkeeper_phone)

            # Step 3: Auto-Vasooli if khata debt crossed the warning limit
            if (
                order_doc.get("payment_mode", "").lower() == "khata"
                and highest_debt > DEBT_WARNING_LIMIT
            ):
                customer_phone = order_doc.get("customer_phone", "")
                phone_digits   = "".join(c for c in customer_phone if c.isdigit())

                if len(phone_digits) >= 10:
                    lang  = order_doc.get("language", "hi")
                    name  = order_doc["customer_name"]
                    count = increment_reminder_count(name, order_doc["store_id"])

                    print(
                        f"[/log] 🚨 Auto-Vasooli L{count} → {name} | debt=₹{highest_debt}"
                    )
                    send_vasooli_alert(name, customer_phone, highest_debt, count, lang)
                    alert_status = "text_receipt_and_auto_vasooli_sent"
                else:
                    print(
                        f"[/log] ⚠️ Debt ₹{highest_debt} > limit but no valid phone "
                        f"for {order_doc['customer_name']} — Vasooli skipped"
                    )
                    alert_status = "vasooli_skipped_no_phone"

        except Exception as api_err:
            # Alert APIs failing must not block the 200 response to Person 1
            print(f"[/log] ⚠️ DB OK but alert API error: {api_err}")
            alert_status = f"api_failed: {api_err}"

        print(
            f"[/log] ✅ order_id={order_id} | "
            f"total=₹{order_doc.get('total_amount')} | {alert_status}\n"
        )

        response_order = dict(order_doc)
        response_order["created_at"] = str(response_order.get("created_at", ""))

        return JSONResponse(status_code=200, content={
            "status":       "success",
            "alert_status": alert_status,
            "order_id":     order_id,
            "order":        response_order,
        })

    except Exception as e:
        print(f"[/log] ❌ CRITICAL DB ERROR: {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


# ── Core: Manual Vasooli ───────────────────────────────────────────────────────
@app.post("/vasooli", tags=["core"])
async def vasooli_endpoint(req: VasooliRequest):
    """
    Manual debt-collection voice note triggered from the shopkeeper dashboard.
    Each call increments reminder_count → progressively firmer tone.
    """
    phone_digits = "".join(c for c in req.customer_phone if c.isdigit())
    if len(phone_digits) < 10:
        return JSONResponse(status_code=400, content={
            "status":  "error",
            "message": f"Valid 10-digit phone required for {req.customer_name}. Cannot send Vasooli.",
        })

    khata_doc = get_khata_balance(req.customer_name, req.store_id)
    if not khata_doc:
        raise HTTPException(status_code=404, detail=f"No khata found for {req.customer_name}")

    outstanding = khata_doc.get("total_outstanding", 0)
    if outstanding <= 0:
        return JSONResponse(status_code=200, content={
            "status":  "no_dues",
            "message": f"{req.customer_name} has cleared their balance. 🎉",
        })

    count = increment_reminder_count(req.customer_name, req.store_id)
    print(f"[/vasooli] 📤 Manual Level {count} reminder → {req.customer_name} (₹{outstanding})")

    try:
        audio = send_vasooli_alert(
            req.customer_name, req.customer_phone, outstanding, count, req.language
        )
        return JSONResponse(status_code=200, content={
            "status":           "success",
            "escalation_level": count,
            "outstanding":      outstanding,
            "audio_file":       audio,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Read: Orders ───────────────────────────────────────────────────────────────
@app.get("/orders", tags=["read"])
def list_orders(limit: int = 20):
    """Most recent N orders — used by the React LiveOrders page."""
    db     = get_db()
    cursor = db["orders"].find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    docs   = []
    for d in cursor:
        d["created_at"] = str(d.get("created_at", ""))
        docs.append(d)
    return {"count": len(docs), "orders": docs}


@app.get("/orders/{order_id}/receipt", tags=["read"])
def get_receipt(order_id: str):
    db  = get_db()
    doc = db["orders"].find_one({"order_id": order_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return {"order_id": order_id, "receipt": create_text_bill(doc)}


# ── Read: Khata ────────────────────────────────────────────────────────────────
@app.get("/khata/{customer_name}", tags=["read"])
def get_khata(customer_name: str, store_id: str = "store_001"):
    """Full khata ledger for a customer — used by the React KhataLedger page."""
    doc = get_khata_balance(customer_name, store_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"No khata for {customer_name}")
    doc["last_updated"] = str(doc.get("last_updated", ""))
    if "last_reminded_at" in doc:
        doc["last_reminded_at"] = str(doc["last_reminded_at"])
    for e in doc.get("entries", []):
        e["date"] = str(e.get("date", ""))
    return doc


# ── Read: Customers ────────────────────────────────────────────────────────────
@app.get("/customers/leaderboard", tags=["read"])
def get_loyalty_leaderboard(limit: int = 10, store_id: str = "store_001"):
    """Top customers by lifetime spend — used by the React Customers page."""
    db     = get_db()
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


# ── Read: Dashboard Aggregates ─────────────────────────────────────────────────
@app.get("/dashboard", tags=["read"])
def dashboard_metrics():
    """
    Derived aggregates for the React Dashboard page.
    Uses get_db() (the public alias) — no internal _get_db import needed.
    """
    db      = get_db()
    today   = datetime.datetime.utcnow().date()
    day_start = datetime.datetime.combine(today, datetime.time.min)

    todays_orders = list(
        db["orders"].find({"created_at": {"$gte": day_start}}, {"total_amount": 1})
    )
    todays_revenue      = sum(o.get("total_amount", 0) for o in todays_orders)
    todays_orders_count = len(todays_orders)

    outstanding_khata = sum(
        k.get("total_outstanding", 0)
        for k in db["khata"].find({}, {"total_outstanding": 1})
    )

    low_stock_count = db["products"].count_documents({"stock_quantity": {"$lt": 5}}) \
        if "products" in db.list_collection_names() else 0

    pending_deliveries = db["purchase_orders"].count_documents({"status": "In Transit"}) \
        if "purchase_orders" in db.list_collection_names() else 0

    pending_supplier_pay = sum(
        s.get("outstanding_balance", 0)
        for s in db["suppliers"].find({}, {"outstanding_balance": 1})
    ) if "suppliers" in db.list_collection_names() else 0

    return {
        "todaysRevenue":         round(todays_revenue, 2),
        "todaysOrdersCount":     todays_orders_count,
        "outstandingKhata":      round(outstanding_khata, 2),
        "lowStockItemsCount":    low_stock_count,
        "pendingDeliveriesCount": pending_deliveries,
        "pendingSupplierPay":    round(pending_supplier_pay, 2),
        "storeHealthScore":      94,
    }


# ── ML: Forecasts ──────────────────────────────────────────────────────────────
@app.get("/forecast", tags=["ml"])
def get_forecast(limit: int = 50):
    """
    Returns per-SKU forecasts produced by the offline ML training script.
    Run ML/generate_data.py then ML/train_xgboost.py to regenerate model_forecasts.pkl.
    Returns 503 if the model file hasn't been generated yet.
    """
    if _forecasts_payload is None:
        raise HTTPException(
            status_code=503,
            detail="Forecasts not available. Run the ML training script first to generate model_forecasts.pkl.",
        )
    return _forecasts_payload[:limit]