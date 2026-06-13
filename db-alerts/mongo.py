"""
mongo.py — Kirana AI | Person 3
Handles: orders collection write + dynamic pricing + khata split-bill logic
         + group discount engine + customer lifetime value tracking
"""

import os
import uuid
from datetime import datetime, timezone
from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection
from dotenv import load_dotenv

load_dotenv()

MONGO_URI    = os.getenv("MONGO_URI")
DB_NAME      = os.getenv("MONGO_DB_NAME", "kirana_ai")
STORE_ID     = os.getenv("STORE_ID", "store_001")

# ──────────────────────────────────────────────
# Dataset: Store price catalog (HackPrix demo set)
# ──────────────────────────────────────────────
STORE_PRICES = {
    # Staples
    "Wheat Flour": 50.0,
    "Milk": 32.0,
    "Rice": 60.0,
    "Sugar": 45.0,
    "Cooking Oil": 120.0,
    # Specific Demo Items
    "Lamb": 600.0,
    "Raw Mango": 40.0,
    "Prawns": 450.0,
    "Kashmiri Chili Powder": 80.0,
    "Mustard Oil": 150.0,
}

# Threshold for automatic "Wholesale / Group Discount" trigger
WHOLESALE_THRESHOLD = 1500.0
WHOLESALE_DISCOUNT_RATE = 0.10  # 10%


# ──────────────────────────────────────────────
# Internal helper: get a live DB handle
# ──────────────────────────────────────────────
def _get_db():
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI is not set in your .env file!")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Trigger a real connection check immediately
    client.admin.command("ping")
    return client[DB_NAME]


# ──────────────────────────────────────────────
# STEP A1: Dynamic price enrichment
# ──────────────────────────────────────────────
def _enrich_items_with_prices(items: list) -> tuple[list, float]:
    """
    Loops through incoming items, attaches unit_price + line_total
    from STORE_PRICES, and returns (enriched_items, calculated_total).
    """
    enriched_items = []
    calculated_total = 0.0

    for item in items:
        item_name = item.get("name", "")
        qty = float(item.get("qty", 1))

        # Look up the price (default to 0 if we don't sell it)
        unit_price = STORE_PRICES.get(item_name, 0.0)
        line_total = unit_price * qty

        item["unit_price"] = unit_price
        item["line_total"] = line_total
        enriched_items.append(item)

        calculated_total += line_total

    return enriched_items, calculated_total


# ──────────────────────────────────────────────
# STEP A2: Wholesale / Group Discount engine
# ──────────────────────────────────────────────
def _apply_group_discount(calculated_total: float) -> tuple[float, float, float]:
    """
    If the order total crosses WHOLESALE_THRESHOLD, apply a flat
    discount rate automatically (P2 spec: Volume spike → discount pricing).

    Returns (final_total, discount_applied, original_total).
    """
    if calculated_total >= WHOLESALE_THRESHOLD:
        discount_applied = round(calculated_total * WHOLESALE_DISCOUNT_RATE, 2)
        final_total = round(calculated_total - discount_applied, 2)
        print(
            f"[MongoDB] 🎯 VOLUME SPIKE DETECTED! Total ₹{calculated_total} "
            f"≥ ₹{WHOLESALE_THRESHOLD} → Applying "
            f"{int(WHOLESALE_DISCOUNT_RATE * 100)}% discount (-₹{discount_applied})"
        )
        return final_total, discount_applied, calculated_total

    return round(calculated_total, 2), 0.0, round(calculated_total, 2)


# ──────────────────────────────────────────────
# STEP B: Write to `orders` collection
# ──────────────────────────────────────────────
def _write_order(orders_col: Collection, order: dict, shopkeeper_phone: str):
    order_id = str(uuid.uuid4())
    now      = datetime.now(timezone.utc)

    # --- DYNAMIC PRICE ENRICHMENT -----------------------------------
    enriched_items, raw_total = _enrich_items_with_prices(order.get("items", []))

    # --- GROUP / WHOLESALE DISCOUNT ----------------------------------
    final_total, discount_applied, original_total = _apply_group_discount(raw_total)
    # ------------------------------------------------------------------

    order_doc = {
        "order_id":         order_id,
        "customer_name":    order.get("customer_name", "Unknown"),
        "customer_phone":   order.get("customer_phone", ""),
        "store_id":         order.get("store_id", STORE_ID),
        "items":            enriched_items,          # items now carry unit_price/line_total
        "split_with":       order.get("split_with", []),
        "payment_mode":     order.get("payment_mode", "cash"),
        "input_type":       order.get("input_type", "text"),
        "raw_input_url":    order.get("raw_input_url"),
        "original_total":   original_total,          # pre-discount total
        "discount_applied": discount_applied,        # ₹ value discounted
        "total_amount":     final_total,              # final payable total
        "shopkeeper_phone": shopkeeper_phone,
        "created_at":       now,
        "status":           "pending",
    }

    orders_col.insert_one(order_doc)
    print(
        f"[MongoDB] ✅ Order written → order_id={order_id} "
        f"total=₹{final_total} (discount=₹{discount_applied})"
    )
    return order_id, order_doc


# ──────────────────────────────────────────────
# STEP C: Khata split-bill math
# ──────────────────────────────────────────────
def _update_khata(khata_col: Collection, order_doc: dict) -> None:
    split_with    = order_doc.get("split_with", [])
    total_amount  = order_doc.get("total_amount", 0.0)
    store_id      = order_doc.get("store_id", STORE_ID)
    order_id      = order_doc["order_id"]

    if not split_with or total_amount <= 0:
        print("[MongoDB] ℹ️  No split requested — skipping khata update.")
        return

    # e.g. split_with=["Rahul"] → 2 people → each owes 50
    num_parties    = len(split_with) + 1          # include the orderer
    per_person     = round(total_amount / num_parties, 2)
    now            = datetime.now(timezone.utc)

    print(f"[MongoDB] 💸 Split: ₹{total_amount} ÷ {num_parties} = ₹{per_person} each")

    for person in split_with:
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
                    "customer_name": person,
                    "customer_phone": "",
                    "store_id": store_id,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        print(
            f"[MongoDB] ✅ Khata updated → {person} "
            f"outstanding=₹{result['total_outstanding']}"
        )


# ──────────────────────────────────────────────
# STEP D: Customer Lifetime Value (Loyalty Feature)
# ──────────────────────────────────────────────
def _update_customer_lifetime_value(customers_col: Collection, order_doc: dict) -> None:
    """
    Tracks total spend + order count per customer in the `customers` collection.
    Powers a "Top Loyal Customers" leaderboard on the dashboard.
    """
    customer_name = order_doc.get("customer_name", "Unknown")
    store_id      = order_doc.get("store_id", STORE_ID)
    total_amount  = order_doc.get("total_amount", 0.0)
    now           = datetime.now(timezone.utc)

    if total_amount <= 0:
        return

    result = customers_col.find_one_and_update(
        {"customer_name": customer_name, "store_id": store_id},
        {
            "$inc": {
                "lifetime_spend": total_amount,
                "order_count": 1,
            },
            "$set": {"last_order_at": now},
            "$setOnInsert": {
                "customer_name": customer_name,
                "store_id": store_id,
                "customer_phone": order_doc.get("customer_phone", ""),
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    print(
        f"[MongoDB] 🏆 Loyalty updated → {customer_name} "
        f"lifetime_spend=₹{result['lifetime_spend']} "
        f"order_count={result['order_count']}"
    )


# ──────────────────────────────────────────────
# PUBLIC ENTRY POINT (called from main.py)
# ──────────────────────────────────────────────
def log_order(order: dict, shopkeeper_phone: str):
    """
    Writes order to MongoDB `orders` (with price enrichment + discount),
    updates `khata` if split_with present, and updates `customers`
    lifetime-value tracking.

    Returns (order_id, order_doc) — order_doc is needed by main.py
    to build the text receipt and emotion-aware voice alert.
    """
    db          = _get_db()
    orders_col  = db["orders"]
    khata_col   = db["khata"]
    customers_col = db["customers"]

    order_id, order_doc = _write_order(orders_col, order, shopkeeper_phone)
    _update_khata(khata_col, order_doc)
    _update_customer_lifetime_value(customers_col, order_doc)

    return order_id, order_doc


# ──────────────────────────────────────────────
# PUBLIC: Fetch a customer's khata for Vasooli alerts
# ──────────────────────────────────────────────
def get_khata_balance(customer_name: str, store_id: str = STORE_ID):
    """
    Returns the khata document for a customer, or None if not found.
    Used by the automated debt-collection ("Vasooli") voice note feature.
    """
    db = _get_db()
    return db["khata"].find_one(
        {"customer_name": customer_name, "store_id": store_id},
        {"_id": 0},
    )