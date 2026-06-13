"""
main.py — Kirana AI | Person 3 | Port 8002
FastAPI service: receives order JSON from Person 1 → MongoDB (pricing + khata + loyalty)
                 → WhatsApp text receipt (always) → Vasooli voice note (if debt > ₹1500)

FIXES APPLIED:
  [Bug Fix] All imports now use mongo_connector (previously some used "mongo" — crashed on import)
  [Fix 2]  /log sends TEXT receipt by default; audio is not generated for normal orders
  [Fix 3]  Auto-Vasooli triggered if payment_mode="khata" AND highest_debt > ₹1500
  [Safety] Phone validation guard before Vasooli — no crash if customer phone missing
  [Safety] Alert failures are caught separately so DB write always returns 200 to Person 1
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# ── Fix: all DB imports from mongo_connector (not "mongo") ────────────────────
from mongo_connector import (
    log_order            as db_log_order,
    get_khata_balance,
    increment_reminder_count,
    get_db,              # public alias for _get_db, used in read endpoints
)
from alerts import send_receipt_only, send_vasooli_alert, create_text_bill

load_dotenv()

AUDIO_DIR = Path(__file__).parent / "audio_files"
AUDIO_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="Kirana AI — DB & Alerts",
    description=(
        "Person 3: MongoDB persistence + dynamic pricing + "
        "multilingual receipts + escalating Vasooli"
    ),
    version="3.0.0",
)

# Serve generated MP3s so Twilio can download them
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")

DEBT_WARNING_LIMIT = 1500.0  # Fix 3: auto-Vasooli threshold


# ── Request models ─────────────────────────────────────────────────────────────
class LogRequest(BaseModel):
    order:            dict
    shopkeeper_phone: str


class VasooliRequest(BaseModel):
    customer_name:  str
    customer_phone: str
    store_id:       str = "store_001"
    language:       str = "hi"   # Sarvam code: hi / kn / en / ta / te …


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
        raise HTTPException(503, detail=f"MongoDB unreachable: {e}")


# ── Core: Receive Order ────────────────────────────────────────────────────────
@app.post("/log", tags=["core"])
async def log_endpoint(req: LogRequest):
    """
    Called by Person 1's FastAPI router after order is confirmed.

    Sequence:
      1. MongoDB: price enrichment + khata split + loyalty update
      2. Twilio:  text receipt → shopkeeper (always)
      3. Twilio:  Vasooli voice note → customer (only if khata debt > ₹1500)

    DB write failure  → 500 (critical, Person 1 must know)
    Alert failure     → 200 with alert_status="api_failed:..." (DB is safe, don't cascade)
    """
    print(
        f"\n[/log] 📥 {req.order.get('customer_name')} | "
        f"₹{req.order.get('total_amount')} | mode={req.order.get('payment_mode')}"
    )

    try:
        # ── Step 1: MongoDB (must succeed) ─────────────────────────────────────
        order_id, order_doc, highest_debt = db_log_order(req.order, req.shopkeeper_phone)

        alert_status = "success"

        try:
            # ── Step 2: Text receipt to shopkeeper (Fix 2: always text, no audio) ──
            send_receipt_only(order_doc, req.shopkeeper_phone)

            # ── Step 3: Auto-Vasooli if khata debt crossed ₹1500 (Fix 3) ──────────
            if (
                order_doc.get("payment_mode", "").lower() == "khata"
                and highest_debt > DEBT_WARNING_LIMIT
            ):
                customer_phone = order_doc.get("customer_phone", "")
                phone_digits   = "".join(c for c in customer_phone if c.isdigit())

                # Safety guard: only trigger if we have a real 10-digit phone
                if len(phone_digits) >= 10:
                    lang  = order_doc.get("language", "hi")
                    name  = order_doc["customer_name"]
                    count = increment_reminder_count(name, order_doc["store_id"])

                    print(
                        f"[/log] 🚨 Auto-Vasooli L{count} → {name} | "
                        f"debt=₹{highest_debt}"
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
            # DB saved — don't let Twilio/ElevenLabs failures cascade to Person 1
            print(f"[/log] ⚠️ DB OK but alert API error: {api_err}")
            alert_status = f"api_failed: {api_err}"

        print(
            f"[/log] ✅ Done | order_id={order_id} | "
            f"total=₹{order_doc.get('total_amount')} | {alert_status}\n"
        )

        # Serialize datetime for JSON
        response_order = dict(order_doc)
        response_order["created_at"] = str(response_order.get("created_at", ""))

        return JSONResponse(200, {
            "status":       "success",
            "alert_status": alert_status,
            "order_id":     order_id,
            "order":        response_order,
        })

    except Exception as e:
        print(f"[/log] ❌ CRITICAL DB ERROR: {e}\n")
        raise HTTPException(500, detail=str(e))


# ── Core: Manual Vasooli ───────────────────────────────────────────────────────
@app.post("/vasooli", tags=["core"])
async def vasooli_endpoint(req: VasooliRequest):
    """
    Manual debt-collection voice note, triggered from Person 4's shopkeeper dashboard.
    Each call increments reminder_count → progressively angrier ElevenLabs voice.
    """
    # Safety guard (Fix 5 companion): crash-proof phone check
    phone_digits = "".join(c for c in req.customer_phone if c.isdigit())
    if not req.customer_phone or len(phone_digits) < 10:
        return JSONResponse(400, {
            "status":  "error",
            "message": f"Valid 10-digit phone required for {req.customer_name}. Cannot send Vasooli.",
        })

    khata_doc = get_khata_balance(req.customer_name, req.store_id)
    if not khata_doc:
        raise HTTPException(404, detail=f"No khata found for {req.customer_name}")

    outstanding = khata_doc.get("total_outstanding", 0)
    if outstanding <= 0:
        return JSONResponse(200, {
            "status":  "no_dues",
            "message": f"{req.customer_name} has cleared their balance. 🎉",
        })

    count = increment_reminder_count(req.customer_name, req.store_id)
    print(f"[/vasooli] 📤 Manual Level {count} reminder → {req.customer_name} (₹{outstanding})")

    try:
        audio = send_vasooli_alert(
            req.customer_name, req.customer_phone, outstanding, count, req.language
        )
        return JSONResponse(200, {
            "status":           "success",
            "escalation_level": count,
            "outstanding":      outstanding,
            "audio_file":       audio,
        })
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── Read Endpoints (for Person 4's Dashboard) ──────────────────────────────────
@app.get("/khata/{customer_name}", tags=["read"])
def get_khata(customer_name: str, store_id: str = "store_001"):
    """Fetch outstanding Khata balance and full ledger for a customer."""
    doc = get_khata_balance(customer_name, store_id)
    if not doc:
        raise HTTPException(404, detail=f"No khata for {customer_name}")
    # Serialize datetime fields
    doc["last_updated"] = str(doc.get("last_updated", ""))
    if "last_reminded_at" in doc:
        doc["last_reminded_at"] = str(doc["last_reminded_at"])
    for e in doc.get("entries", []):
        e["date"] = str(e.get("date", ""))
    return doc


@app.get("/orders", tags=["read"])
def list_orders(limit: int = 10):
    """Fetch the N most recent orders (default 10). Useful for dashboard live feed."""
    db     = get_db()
    cursor = db["orders"].find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    docs   = []
    for d in cursor:
        d["created_at"] = str(d.get("created_at", ""))
        docs.append(d)
    return {"count": len(docs), "orders": docs}


@app.get("/orders/{order_id}/receipt", tags=["read"])
def get_receipt(order_id: str):
    """Returns the formatted text receipt for a given order_id."""
    db  = get_db()
    doc = db["orders"].find_one({"order_id": order_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, detail=f"Order {order_id} not found")
    return {"order_id": order_id, "receipt": create_text_bill(doc)}


@app.get("/customers/leaderboard", tags=["read"])
def get_loyalty_leaderboard(limit: int = 10, store_id: str = "store_001"):
    """"Top Loyal Customers" leaderboard sorted by lifetime_spend."""
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