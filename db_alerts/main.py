"""
main.py — Kirana AI | Person 3 | Port 8002
FastAPI service: receives order JSON from Person 1 → MongoDB (pricing + khata + loyalty)
                 → WhatsApp text receipt (always) → Vasooli voice note (if debt > ₹1500)
                 → /forecast endpoint (serialized ML payload)
                 → /dashboard aggregates for React frontend
"""

import os
from datetime import datetime, timezone, time
from pathlib import Path

import joblib
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from mongo_connector import (
    log_order as db_log_order,
    get_khata_balance,
    increment_reminder_count,
    get_db,
)
from alerts import send_receipt_only, send_vasooli_alert, create_text_bill

load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────────
AUDIO_DIR = Path(__file__).parent / "audio_files"
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
    allow_origins=["*"],  # tighten to your Vite origin in production
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
    print(
        "[forecast] ℹ️ model_forecasts.pkl not found — /forecast will return 503 until trained"
    )


# ── Request models ─────────────────────────────────────────────────────────────
class LogRequest(BaseModel):
    order: dict
    shopkeeper_phone: str


# Light FlatOrder model to validate incoming payloads from ingestion
class FlatItem(BaseModel):
    name: str
    qty: float
    unit: str | None = None
    unit_price: float | None = None


class FlatOrder(BaseModel):
    customer_phone: str
    customer_name: str
    store_id: str
    language: str = "hi"
    items: list[FlatItem]
    split_with: list[str] = []
    payment_mode: str = "cash"
    input_type: str | None = None
    raw_input_url: str | None = None
    total_amount: float | None = None


class VasooliRequest(BaseModel):
    customer_name: str
    customer_phone: str
    store_id: str = "store_001"
    language: str = "hi"  # Sarvam language code: hi / kn / en / ta / te


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "service": "db-alerts", "port": 8002}


@app.get("/ping-mongo", tags=["health"])
def ping_mongo():
    """Verify MongoDB Atlas connectivity before the demo."""
    try:
        db = get_db()
        info = db.client.server_info()
        return {"status": "ok", "mongo_version": info.get("version")}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MongoDB unreachable: {e}")


# ── Core: Receive Order ────────────────────────────────────────────────────────
# ── Core: Receive Order ────────────────────────────────────────────────────────
@app.post("/log", tags=["core"])
async def log_endpoint(req: LogRequest):
    """
    Called by Person 1's webhook router after an order arrives.
    """
    raw_payload = req.order or {}
    if not isinstance(raw_payload, dict):
        print("[/log] ⚠️ Received non-dict payload; coercing to empty dict for safety")
        raw_payload = {}

    clean_order = None

    # ── THE ADAPTER: Convert Person 2's messy nested JSON into Person 3's clean format ──

    # 1. Try strict validation first — flat order sent directly by ingestion
    try:
        candidate = FlatOrder.model_validate(raw_payload)
        clean_order = candidate.model_dump()
        clean_order.setdefault("customer_phone", req.shopkeeper_phone)
    except Exception:
        clean_order = None

    # 2. Fast-path: already-flat dict (has customer_name + items) but didn't
    #    pass strict FlatOrder validation (e.g. missing store_id)
    if clean_order is None and "customer_name" in raw_payload and "items" in raw_payload:
        clean_order = raw_payload
        clean_order.setdefault("customer_phone", req.shopkeeper_phone)
        clean_order.setdefault("language", "hi")
        clean_order.setdefault("payment_mode", "cash")
        clean_order.setdefault("split_with", [])

    # 3. Legacy nested 'processed_splits' format
    if clean_order is None and raw_payload.get("processed_splits"):
        clean_order = {
            "customer_name": "Unknown",
            "customer_phone": raw_payload.get("customer_phone", req.shopkeeper_phone),
            "language": raw_payload.get("language", "hi"),
            "payment_mode": raw_payload.get("payment_mode", "cash"),
            "items": [],
            "split_with": [],
        }

        main_split = raw_payload["processed_splits"][0]
        clean_order["customer_name"] = main_split.get("buyer_name", "Unknown")

        for item in main_split.get("items", []):
            clean_order["items"].append(
                {
                    "name": item.get("item_name", "item"),
                    "qty": item.get("quantity", 1),
                }
            )

        # Extra buyers go into split_with
        for extra_split in raw_payload["processed_splits"][1:]:
            clean_order["split_with"].append(
                extra_split.get("buyer_name", "Unknown")
            )

    # 4. Last resort: nothing usable came through (e.g. ingestion error → {})
    if clean_order is None:
        clean_order = {
            "customer_name": raw_payload.get("customer_name", "Unknown"),
            "customer_phone": raw_payload.get("customer_phone", req.shopkeeper_phone),
            "language": raw_payload.get("language", "hi"),
            "payment_mode": raw_payload.get("payment_mode", "cash"),
            "items": raw_payload.get("items", []),
            "split_with": raw_payload.get("split_with", []),
        }

    print(f"\n[/log] 📥 Adapted Order for DB: {clean_order}")
    print(
        f"[/log]    Mode={clean_order['payment_mode']} | Lang={clean_order['language']}"
    )
    # ───────────────────────────────────────────────────────────────────────────────────

    try:
        # Step 1: MongoDB (critical — must succeed before anything else)
        # PASS 'clean_order', NOT 'req.order'
        order_id, order_doc, highest_debt = db_log_order(
            clean_order, req.shopkeeper_phone
        )

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
                phone_digits = "".join(c for c in customer_phone if c.isdigit())

                if len(phone_digits) >= 10:
                    lang = order_doc.get("language", "hi")
                    name = order_doc["customer_name"]
                    count = increment_reminder_count(name, order_doc["store_id"])

                    print(
                        f"[/log] 🚨 Auto-Vasooli L{count} → {name} | debt=₹{highest_debt}"
                    )
                    send_vasooli_alert(name, customer_phone, highest_debt, count, lang)
                    alert_status = "text_receipt_and_auto_vasooli_sent"
                else:
                    print(
                        f"[/log] ⚠️ Debt ₹{highest_debt} > limit but no valid phone for {order_doc['customer_name']} — Vasooli skipped"
                    )
                    alert_status = "vasooli_skipped_no_phone"

        except Exception as api_err:
            print(f"[/log] ⚠️ DB OK but alert API error: {api_err}")
            alert_status = f"api_failed: {api_err}"

        print(
            f"[/log] ✅ order_id={order_id} | total=₹{order_doc.get('total_amount')} | {alert_status}\n"
        )

        response_order = dict(order_doc)
        response_order["created_at"] = str(response_order.get("created_at", ""))

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "alert_status": alert_status,
                "order_id": order_id,
                "order": response_order,
            },
        )

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
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": f"Valid 10-digit phone required for {req.customer_name}. Cannot send Vasooli.",
            },
        )

    khata_doc = get_khata_balance(req.customer_name, req.store_id)
    if not khata_doc:
        raise HTTPException(
            status_code=404, detail=f"No khata found for {req.customer_name}"
        )

    outstanding = khata_doc.get("total_outstanding", 0)
    if outstanding <= 0:
        return JSONResponse(
            status_code=200,
            content={
                "status": "no_dues",
                "message": f"{req.customer_name} has cleared their balance. 🎉",
            },
        )

    count = increment_reminder_count(req.customer_name, req.store_id)
    print(
        f"[/vasooli] 📤 Manual Level {count} reminder → {req.customer_name} (₹{outstanding})"
    )

    try:
        audio = send_vasooli_alert(
            req.customer_name, req.customer_phone, outstanding, count, req.language
        )
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "escalation_level": count,
                "outstanding": outstanding,
                "audio_file": audio,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Read: Orders ───────────────────────────────────────────────────────────────
@app.get("/orders", tags=["read"])
def list_orders(limit: int = 20):
    """Most recent N orders — used by the React LiveOrders page."""
    db = get_db()
    cursor = db["orders"].find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    docs = []
    for d in cursor:
        # Normalize field names for frontend compatibility: 'order_id' -> 'id'
        d["created_at"] = str(d.get("created_at", ""))
        if "order_id" in d:
            d["id"] = d.pop("order_id")
        docs.append(d)
    return {"count": len(docs), "orders": docs}


@app.get("/orders/{order_id}/receipt", tags=["read"])
def get_receipt(order_id: str):
    db = get_db()
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
    db = get_db()
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
    db = get_db()
    today = datetime.now(timezone.utc).date()
    day_start = datetime.combine(today, time.min).replace(tzinfo=timezone.utc)

    todays_orders = list(
        db["orders"].find({"created_at": {"$gte": day_start}}, {"total_amount": 1})
    )
    todays_revenue = sum(o.get("total_amount", 0) for o in todays_orders)
    todays_orders_count = len(todays_orders)

    outstanding_khata = sum(
        k.get("total_outstanding", 0)
        for k in db["khata"].find({}, {"total_outstanding": 1})
    )

    collections = db.list_collection_names()

    low_stock_count = (
        db["products"].count_documents({"stock_quantity": {"$lt": 5}})
        if "products" in collections
        else 0
    )

    pending_deliveries = (
        db["purchase_orders"].count_documents({"status": "In Transit"})
        if "purchase_orders" in collections
        else 0
    )

    pending_supplier_pay = (
        sum(
            s.get("outstanding_balance", 0)
            for s in db["suppliers"].find({}, {"outstanding_balance": 1})
        )
        if "suppliers" in collections
        else 0
    )

    return {
        "todaysRevenue": round(todays_revenue, 2),
        "todaysOrdersCount": todays_orders_count,
        "outstandingKhata": round(outstanding_khata, 2),
        "lowStockItemsCount": low_stock_count,
        "pendingDeliveriesCount": pending_deliveries,
        "pendingSupplierPay": round(pending_supplier_pay, 2),
        "storeHealthScore": 94,
    }


# ── Read: Flattened Khata Transactions (new) ───────────────────────────────────
@app.get("/khata", tags=["read"])
def list_khata_transactions(store_id: str = "store_001"):
    """Return a flattened list of khata transactions across all customers for the dashboard/client.
    Each khata document stores an `entries` array — this endpoint normalizes them to individual
    transaction objects so the frontend can display a chronological ledger stream.
    """
    db = get_db()
    txns = []
    cursor = db["khata"].find(
        {"store_id": store_id}, {"_id": 0, "customer_name": 1, "entries": 1}
    )
    for doc in cursor:
        customer_name = doc.get("customer_name")
        for idx, e in enumerate(doc.get("entries", [])):
            txns.append(
                {
                    "id": f"{customer_name}-{e.get('order_id')}-{idx}",
                    "customerId": customer_name,  # note: customerName used as id here for compatibility
                    "customerName": customer_name,
                    "type": "credit",
                    "amount": e.get("amount", 0),
                    "date": e.get("date"),
                    "description": f"Order {e.get('order_id')}",
                }
            )
    # sort by date descending
    try:
        txns.sort(key=lambda x: x.get("date") or "", reverse=True)
    except Exception:
        pass
    return {"count": len(txns), "transactions": txns}


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


# --- Products CRUD (minimal) -------------------------------------------------
@app.get("/products", tags=["read"])
def list_products():
    db = get_db()
    cursor = db["products"].find({}, {"_id": 0})
    prods = []
    for p in cursor:
        # normalize timestamps
        if "created_at" in p:
            p["created_at"] = str(p.get("created_at", ""))
        prods.append(p)
    return {"count": len(prods), "products": prods}


@app.post("/products", tags=["write"])
def create_product(product: dict):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    product_doc = dict(product)
    product_doc.setdefault("id", f"prod-{uuid.uuid4()}")
    product_doc.setdefault("created_at", now)
    product_doc.setdefault("stock_quantity", product_doc.get("stock_quantity", 0))
    product_doc.setdefault("status", "In Stock" if product_doc.get("stock_quantity", 0) > 0 else "Out of Stock")
    db["products"].insert_one(product_doc)
    return {"status": "success", "product": product_doc}


@app.patch("/products/{product_id}/stock", tags=["write"])
def update_product_stock(product_id: str, payload: dict):
    db = get_db()
    qty = payload.get("stockQuantity") or payload.get("stock_quantity")
    if qty is None:
        raise HTTPException(status_code=400, detail="stockQuantity required")
    status = "Out of Stock" if qty == 0 else "Low Stock" if qty < 5 else "In Stock"
    from pymongo import ReturnDocument
    doc = db["products"].find_one_and_update(
        {"id": product_id},
        {"$set": {"stock_quantity": int(qty), "status": status}},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    doc.pop("_id", None)
    return {"status": "success", "product": doc}


# --- Customers create (leaderboard read already exists) ---------------------
@app.post("/customers", tags=["write"])
def create_customer(customer: dict):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    customer_doc = dict(customer)
    customer_doc.setdefault("customer_name", customer_doc.get("name") or customer_doc.get("customer_name") or "Walk-in")
    customer_doc.setdefault("lifetime_spend", 0)
    customer_doc.setdefault("order_count", 0)
    customer_doc.setdefault("last_order_at", None)
    customer_doc.setdefault("created_at", now)
    db["customers"].insert_one(customer_doc)
    customer_doc.pop("_id", None)
    return {"status": "success", "customer": customer_doc}


# --- Khata transaction (ad-hoc) --------------------------------------------
@app.post("/khata/tx", tags=["write"])
def post_khata_tx(tx: dict):
    """Payload: { customerId, type: 'credit'|'payment', amount, description }
    customerId is treated as customer_name for compatibility with current stores.
    """
    db = get_db()
    name = tx.get("customerId") or tx.get("customerName") or tx.get("customer_name")
    if not name:
        raise HTTPException(status_code=400, detail="customerId required")
    ttype = tx.get("type", "credit")
    amount = float(tx.get("amount", 0))
    now = datetime.now(timezone.utc)

    entry = {"order_id": f"tx-{uuid.uuid4()}", "amount": amount, "date": now.isoformat(), "settled": ttype == "payment", "description": tx.get("description", "")}

    if ttype == "credit":
        from pymongo import ReturnDocument
        res = db["khata"].find_one_and_update(
                {"customer_name": name},
                {"$push": {"entries": entry}, "$inc": {"total_outstanding": amount}, "$set": {"last_updated": now}, "$setOnInsert": {"customer_name": name, "store_id": "store_001", "reminder_count": 0}},
                upsert=True,
                return_document=True,
        )
    else:
        # payment reduces outstanding
        res = db["khata"].find_one_and_update(
            {"customer_name": name},
            {"$push": {"entries": entry}, "$inc": {"total_outstanding": -amount}, "$set": {"last_updated": now}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    transaction = {"id": entry["order_id"], "customerId": name, "customerName": name, "type": ttype, "amount": amount, "date": entry["date"], "description": entry["description"]}
    return {"status": "success", "transaction": transaction}


# --- Suppliers & Purchase Orders -------------------------------------------
@app.get("/suppliers", tags=["read"])
def list_suppliers():
    db = get_db()
    docs = list(db["suppliers"].find({}, {"_id": 0}))
    return {"count": len(docs), "suppliers": docs}


@app.post("/suppliers", tags=["write"])
def create_supplier(supplier: dict):
    db = get_db()
    doc = dict(supplier)
    doc.setdefault("id", f"sup-{uuid.uuid4()}")
    doc.setdefault("outstanding_balance", 0)
    doc.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    db["suppliers"].insert_one(doc)
    doc.pop("_id", None)
    return {"status": "success", "supplier": doc}


@app.get("/purchase_orders", tags=["read"])
def list_purchase_orders():
    db = get_db()
    docs = list(db["purchase_orders"].find({}, {"_id": 0}).sort("created_at", -1))
    return {"count": len(docs), "purchase_orders": docs}


@app.post("/purchase_orders", tags=["write"])
def create_purchase_order(po: dict):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    doc = dict(po)
    doc.setdefault("id", f"PO-{uuid.uuid4()}")
    doc.setdefault("status", "Awaiting Approval")
    doc.setdefault("created_at", now)
    doc.setdefault("deliveryProgress", 0)
    db["purchase_orders"].insert_one(doc)
    doc.pop("_id", None)
    return {"status": "success", "purchase_order": doc}


@app.post("/purchase_orders/{po_id}/approve", tags=["write"])
def approve_po(po_id: str):
    db = get_db()
    from pymongo import ReturnDocument
    res = db["purchase_orders"].find_one_and_update({"id": po_id}, {"$set": {"status": "In Transit", "estimatedDelivery": "Est. in 2 days", "deliveryProgress": 10}}, return_document=ReturnDocument.AFTER)
    if not res:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    # bump supplier outstanding if totalAmount present
    try:
        sup_id = res.get("supplierId")
        amt = res.get("totalAmount") or res.get("total_amount") or 0
        if sup_id:
            db["suppliers"].update_one({"id": sup_id}, {"$inc": {"outstanding_balance": amt}})
    except Exception:
        pass
    res.pop("_id", None)
    return {"status": "success", "purchase_order": res}


@app.post("/purchase_orders/{po_id}/receive", tags=["write"])
def receive_po(po_id: str):
    db = get_db()
    from pymongo import ReturnDocument
    res = db["purchase_orders"].find_one_and_update({"id": po_id}, {"$set": {"status": "Delivered", "deliveryProgress": 100}}, return_document=ReturnDocument.AFTER)
    if not res:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    # credit product stock
    try:
        products_col = db["products"]
        for item in res.get("items", []):
            pid = item.get("productId") or item.get("product_id") or item.get("id")
            qty = int(item.get("quantity", 0))
            if not pid:
                continue
            products_col.update_one({"id": pid}, {"$inc": {"stock_quantity": qty}, "$set": {"status": "In Stock"}})
    except Exception:
        pass
    res.pop("_id", None)
    return {"status": "success", "purchase_order": res}


# --- Notifications ---------------------------------------------------------
@app.get("/notifications", tags=["read"])
def list_notifications():
    db = get_db()
    docs = list(db["notifications"].find({}, {"_id": 0}).sort("created_at", -1))
    return {"count": len(docs), "notifications": docs}


@app.post("/notifications/mark-read", tags=["write"])
def mark_notifications_read():
    db = get_db()
    db["notifications"].update_many({}, {"$set": {"isRead": True}})
    return {"status": "success"}


# --- Settings --------------------------------------------------------------
@app.get("/settings", tags=["read"])
def get_settings(store_id: str = "store_001"):
    db = get_db()
    doc = db["settings"].find_one({"store_id": store_id}, {"_id": 0})
    if not doc:
        return {"settings": None}
    return {"settings": doc}


@app.post("/settings", tags=["write"])
def save_settings(settings: dict):
    db = get_db()
    store_id = settings.get("store_id", "store_001")
    settings["store_id"] = store_id
    db["settings"].update_one({"store_id": store_id}, {"$set": settings}, upsert=True)
    return {"status": "success", "settings": settings}


# --- Analytics (simple aggregates) -----------------------------------------
@app.get("/analytics", tags=["read"])
def get_analytics():
    db = get_db()
    # Simple khata ageing buckets
    ageing_buckets = [
        {"range": "0-7 days", "amount": 0},
        {"range": "8-15 days", "amount": 0},
        {"range": "16-30 days", "amount": 0},
        {"range": ">30 days", "amount": 0},
    ]
    try:
        import dateutil.parser as dparser
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        for doc in db["khata"].find({}, {"entries": 1}):
            for e in doc.get("entries", []):
                try:
                    d = dparser.parse(e.get("date"))
                    age = (now - d).days
                    amt = float(e.get("amount", 0))
                    if age <= 7:
                        ageing_buckets[0]["amount"] += amt
                    elif age <= 15:
                        ageing_buckets[1]["amount"] += amt
                    elif age <= 30:
                        ageing_buckets[2]["amount"] += amt
                    else:
                        ageing_buckets[3]["amount"] += amt
                except Exception:
                    continue
    except Exception:
        pass

    analytics = {"khata_ageing": ageing_buckets}
    return {"analytics": analytics}

@app.get("/customers/lookup")
def lookup_customer(phone: str):
    db = get_db()
    # _update_customer_lifetime_value() writes "customer_phone" / "customer_name",
    # so query those field names. Also tolerate "phone" / "name" in case a
    # customer was manually created via POST /customers with those keys.
    doc = db["customers"].find_one(
        {"$or": [{"customer_phone": phone}, {"phone": phone}]},
        {"_id": 0, "customer_name": 1, "name": 1},
    )
    if doc:
        name = doc.get("customer_name") or doc.get("name")
        if name:
            return {"name": name}
    raise HTTPException(status_code=404, detail="Customer not found")