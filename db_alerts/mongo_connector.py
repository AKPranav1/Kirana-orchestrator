"""
mongo_connector.py — Kirana AI | Person 3
Handles: orders collection write + dynamic pricing + khata split-bill logic
         + group discount engine + customer lifetime value tracking

FIXES APPLIED:
  [Fix 5] "DEFAULT" bug: customer_name fallback uses last-4 digits of phone
  [Fix 3] _update_khata only fires on payment_mode="khata" (prevents false khata writes)
  [Critical] Split fix: primary customer is INCLUDED in khata parties, not just split_with
  [Fix 4] reminder_count field seeded in khata for escalating Vasooli tracking
  New fn : increment_reminder_count() — called by /log (auto) and /vasooli (manual)
  log_order() now returns (order_id, order_doc, highest_debt) — 3-tuple
"""

import os
import uuid
from datetime import datetime, timezone
from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME   = os.getenv("MONGO_DB_NAME", "kirana_ai")
STORE_ID  = os.getenv("STORE_ID", "store_001")

STORE_PRICES = {
    "Wheat Flour":           50.0,
    "Milk":                  32.0,
    "Rice":                  60.0,
    "Sugar":                 45.0,
    "Cooking Oil":          120.0,
    "Salt":                  20.0,
    "Tea":                   80.0,
    "Instant Noodles":       15.0,
    "Soap":                  35.0,
    "Lamb":                 600.0,
    "Raw Mango":             40.0,
    "Prawns":               450.0,
    "Kashmiri Chili Powder": 80.0,
    "Mustard Oil":          150.0,
}

WHOLESALE_THRESHOLD     = 1500.0
WHOLESALE_DISCOUNT_RATE = 0.10


# ── DB connection ──────────────────────────────────────────────────────────────
def _get_db():
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI is not set in your .env file!")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[DB_NAME]


# Public alias so main.py can do: from mongo_connector import get_db
def get_db():
    return _get_db()


# ── Fix 5: Resolve "Unknown" / "Default" customer names ──────────────────────
def _resolve_customer_name(order: dict) -> str:
    """
    If Person 2's AI failed to catch the customer's name, fall back to the
    last 4 digits of their phone number rather than the useless string "Unknown".
    """
    name  = (order.get("customer_name") or "").strip()
    phone = order.get("customer_phone", "")

    if name and name.lower() not in ("unknown", "default", "customer", ""):
        return name

    # Fallback: last 4 digits of customer phone
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) >= 4:
        return f"Customer {digits[-4:]}"

    return "Walk-in"


# ── Pricing ────────────────────────────────────────────────────────────────────
def _enrich_items_with_prices(items: list) -> tuple[list, float]:
    enriched_items   = []
    calculated_total = 0.0

    for item in items:
        qty        = float(item.get("qty", 1))
        unit_price = STORE_PRICES.get(item.get("name", ""), 0.0)
        line_total = unit_price * qty
        item["unit_price"] = unit_price
        item["line_total"] = line_total
        enriched_items.append(item)
        calculated_total  += line_total

    return enriched_items, calculated_total


def _apply_group_discount(calculated_total: float) -> tuple[float, float, float]:
    """Returns (final_total, discount_applied, original_total)."""
    if calculated_total >= WHOLESALE_THRESHOLD:
        discount_applied = round(calculated_total * WHOLESALE_DISCOUNT_RATE, 2)
        final_total      = round(calculated_total - discount_applied, 2)
        print(
            f"[MongoDB] 🎯 Bulk discount: ₹{calculated_total} → ₹{final_total} "
            f"(saved ₹{discount_applied})"
        )
        return final_total, discount_applied, round(calculated_total, 2)
    return round(calculated_total, 2), 0.0, round(calculated_total, 2)


# ── Write Order ────────────────────────────────────────────────────────────────
def _write_order(
    orders_col: Collection, order: dict, shopkeeper_phone: str
) -> tuple[str, dict]:
    order_id = str(uuid.uuid4())
    now      = datetime.now(timezone.utc)

    enriched_items, raw_total                     = _enrich_items_with_prices(order.get("items", []))
    final_total, discount_applied, original_total = _apply_group_discount(raw_total)

    order_doc = {
        "order_id":         order_id,
        "customer_name":    _resolve_customer_name(order),         # Fix 5
        "customer_phone":   order.get("customer_phone", ""),
        "store_id":         order.get("store_id", STORE_ID),
        "language":         order.get("language", "hi"),           # Sarvam code: hi/kn/en/ta/te…
        "items":            enriched_items,
        "split_with":       order.get("split_with", []),
        "payment_mode":     order.get("payment_mode", "cash"),
        "input_type":       order.get("input_type", "text"),
        "raw_input_url":    order.get("raw_input_url"),
        "original_total":   original_total,
        "discount_applied": discount_applied,
        "total_amount":     final_total,
        "shopkeeper_phone": shopkeeper_phone,
        "created_at":       now,
        "status":           "pending",
    }

    orders_col.insert_one(order_doc)
    order_doc.pop("_id", None)  # Remove ObjectId so dict stays JSON-serializable

    print(
        f"[MongoDB] ✅ Order {order_id} | "
        f"₹{final_total} (disc=₹{discount_applied}) | {order_doc['customer_name']}"
    )
    return order_id, order_doc


# ── Khata Split (Critical Fix + Fix 3) ───────────────────────────────────────
def _update_khata(khata_col: Collection, order_doc: dict) -> float:
    """
    CRITICAL FIX: The primary customer is NOW included in the debt distribution,
    not just the people in split_with. Everyone who owes money gets a separate
    ledger entry.

    Fix 3: Only runs when payment_mode == "khata". Cash/UPI orders skip entirely.

    Returns the highest total_outstanding seen across all updated khata entries,
    so main.py can decide whether to auto-trigger a Vasooli voice note.
    """
    total_amount = order_doc.get("total_amount", 0.0)
    payment_mode = order_doc.get("payment_mode", "").lower()
    split_with   = order_doc.get("split_with", [])
    store_id     = order_doc.get("store_id", STORE_ID)
    order_id     = order_doc["order_id"]
    primary_cust = order_doc["customer_name"]

    # Fix 3: Skip entirely for non-credit orders
    if total_amount <= 0 or payment_mode != "khata":
        print("[MongoDB] ℹ️  Not a khata order — skipping khata update.")
        return 0.0

    # Critical Fix: primary customer is always in the debt distribution
    parties = list(dict.fromkeys([primary_cust] + split_with))  # preserve order, no dups
    num_parties = len(parties)
    per_person  = round(total_amount / num_parties, 2)
    now         = datetime.now(timezone.utc)

    print(f"[MongoDB] 💸 Khata split: ₹{total_amount} ÷ {num_parties} = ₹{per_person} each | parties: {parties}")

    highest_debt = 0.0
    for person in parties:
        khata_entry = {
            "order_id": order_id,
            "amount":   per_person,
            "date":     now.isoformat(),
            "settled":  False,
        }
        result = khata_col.find_one_and_update(
            {"customer_name": person, "store_id": store_id},
            {
                "$push": {"entries": khata_entry},
                "$inc":  {"total_outstanding": per_person},
                "$set":  {"last_updated": now},
                "$setOnInsert": {
                    "customer_name":  person,
                    "customer_phone": order_doc.get("customer_phone", ""),
                    "store_id":       store_id,
                    "reminder_count": 0,   # Fix 4: seed for escalating Vasooli
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        current_debt = result.get("total_outstanding", 0.0)
        print(f"[MongoDB] ✅ Khata → {person}: outstanding=₹{current_debt}")
        if current_debt > highest_debt:
            highest_debt = current_debt

    return highest_debt


# ── Customer Lifetime Value ───────────────────────────────────────────────────
def _update_customer_lifetime_value(
    customers_col: Collection, order_doc: dict
) -> None:
    name         = order_doc.get("customer_name", "Walk-in")
    store_id     = order_doc.get("store_id", STORE_ID)
    total_amount = order_doc.get("total_amount", 0.0)

    if total_amount <= 0:
        return

    result = customers_col.find_one_and_update(
        {"customer_name": name, "store_id": store_id},
        {
            "$inc": {"lifetime_spend": total_amount, "order_count": 1},
            "$set": {"last_order_at": datetime.now(timezone.utc)},
            "$setOnInsert": {
                "customer_name":  name,
                "store_id":       store_id,
                "customer_phone": order_doc.get("customer_phone", ""),
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    print(
        f"[MongoDB] 🏆 Loyalty: {name} | "
        f"lifetime=₹{result['lifetime_spend']} | orders={result['order_count']}"
    )


# ── Public Entry Points ────────────────────────────────────────────────────────
def log_order(order: dict, shopkeeper_phone: str) -> tuple[str, dict, float]:
    """
    Main entry point called by main.py.
    Returns (order_id, order_doc, highest_debt).
    highest_debt = max total_outstanding across all khata entries touched by this order.
    """
    db            = _get_db()
    orders_col    = db["orders"]
    khata_col     = db["khata"]
    customers_col = db["customers"]

    order_id, order_doc = _write_order(orders_col, order, shopkeeper_phone)
    highest_debt        = _update_khata(khata_col, order_doc)
    _update_customer_lifetime_value(customers_col, order_doc)

    return order_id, order_doc, highest_debt


def get_khata_balance(customer_name: str, store_id: str = STORE_ID) -> dict | None:
    db = _get_db()
    return db["khata"].find_one(
        {"customer_name": customer_name, "store_id": store_id},
        {"_id": 0},
    )


def increment_reminder_count(customer_name: str, store_id: str = STORE_ID) -> int:
    """
    Fix 4: Increments reminder_count in the khata document.
    Returns new count, capped at 3 (max escalation level — no need to go beyond stern).
    Called both automatically from /log and manually from /vasooli.
    """
    db     = _get_db()
    result = db["khata"].find_one_and_update(
        {"customer_name": customer_name, "store_id": store_id},
        {
            "$inc": {"reminder_count": 1},
            "$set": {"last_reminded_at": datetime.now(timezone.utc)},
        },
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        return 1  # No doc found — treat as first reminder, don't crash
    return min(result.get("reminder_count", 1), 3)  # Hard cap at 3