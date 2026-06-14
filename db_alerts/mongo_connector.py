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
  [Multilingual] STORE_PRICES now covers all 25 products from ML/products.csv
                 using canonical names that sku_catalog.json resolves to.
"""

import os
import re
import uuid
from datetime import datetime, timezone
from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME   = os.getenv("MONGO_DB_NAME", "kirana_ai")
STORE_ID  = os.getenv("STORE_ID", "store_001")

# ---------------------------------------------------------------------------
# STORE_PRICES — keyed on canonical product names from sku_catalog.json.
# All 25 products from ML/products.csv are covered.
# Prices are representative Indian retail prices (₹).
# ---------------------------------------------------------------------------
STORE_PRICES: dict[str, float] = {
    # ── Staples ──────────────────────────────────────────────────────────────
    "Rice":             60.0,   # per kg
    "Wheat Flour":      50.0,   # per kg
    "Cooking Oil":     120.0,   # per litre
    "Mustard Oil":     150.0,   # per litre
    "Sugar":            45.0,   # per kg
    "Dal":              90.0,   # per kg
    "Salt":             20.0,   # per kg
    "Spices":           80.0,   # per 100gm pack (unit=gm, price per gm scaled below)

    # ── Dairy ─────────────────────────────────────────────────────────────────
    "Milk":             32.0,   # per litre
    "Curd":             50.0,   # per kg
    "Paneer":          320.0,   # per kg  (unit=gm → price handled per-gram)
    "Butter":          560.0,   # per kg  (unit=gm → price handled per-gram)

    # ── Snacks & Beverages ────────────────────────────────────────────────────
    "Instant Noodles":  15.0,   # per packet
    "Bread":            40.0,   # per packet (400gm loaf)
    "Soft drinks":      40.0,   # per bottle (600ml)
    "Chips":            20.0,   # per packet
    "Biscuits":         30.0,   # per packet
    "Tea":             280.0,   # per kg   (unit=gm → price handled per-gram)
    "Coffee":          500.0,   # per kg   (unit=gm → price handled per-gram)
    "Tomato Ketchup":   85.0,   # per bottle

    # ── Personal Care ─────────────────────────────────────────────────────────
    "Soap":             35.0,   # per piece
    "Shampoo":         150.0,   # per bottle
    "Toothpaste":       80.0,   # per piece
    "Toothbrush":       50.0,   # per piece

    # ── Household ─────────────────────────────────────────────────────────────
    "Detergent":        90.0,   # per kg

    # ── Fresh Produce ─────────────────────────────────────────────────────────
    "Onions":           40.0,   # per kg
    "Potatoes":         30.0,   # per kg

    # ── Legacy / alternate canonical names (belt-and-suspenders) ─────────────
    "Lamb":            600.0,
    "Raw Mango":        40.0,
    "Prawns":          450.0,
    "Kashmiri Chili Powder": 80.0,
}

# ---------------------------------------------------------------------------
# Units where pricing is per-gram but catalog unit is "gm"
# We normalise to a per-unit price so the line total is sensible.
# e.g. Tea: ₹280/kg → ₹0.28/gm
# ---------------------------------------------------------------------------
_PER_GRAM_PRODUCTS = {"Tea", "Coffee", "Paneer", "Butter", "Spices"}


def _effective_unit_price(canonical_name: str, unit: str | None) -> float:
    """Return the correct per-unit price accounting for gm vs kg billing."""
    base = STORE_PRICES.get(canonical_name, 0.0)
    if canonical_name in _PER_GRAM_PRODUCTS and (unit or "").lower() == "gm":
        return round(base / 1000, 4)   # ₹/gm
    return base


WHOLESALE_THRESHOLD     = 1500.0
WHOLESALE_DISCOUNT_RATE = 0.10


# ── DB connection ──────────────────────────────────────────────────────────────
def _get_db():
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI is not set in your .env file!")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[DB_NAME]


def get_db():
    return _get_db()


# ── Fix 5: Resolve "Unknown" / "Default" customer names ──────────────────────
def _resolve_customer_name(order: dict) -> str:
    name  = (order.get("customer_name") or "").strip()
    phone = order.get("customer_phone", "")

    if name and name.lower() not in ("unknown", "default", "customer", ""):
        return name

    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) >= 4:
        return f"Customer {digits[-4:]}"

    return "Walk-in"


# ── Pricing ────────────────────────────────────────────────────────────────────
def _enrich_items_with_prices(db, items: list) -> tuple[list, float]:
    enriched_items   = []
    calculated_total = 0.0
    products_col = db["products"] # Access the real inventory

    for item in items:
        item_name  = item.get("name", "")
        qty        = float(item.get("qty", 1))
        
        # 1. TRY MONGODB FIRST (Look for the exact brand name)
        # We use a regex to do a case-insensitive search (e.g., "aashirvaad" matches "Aashirvaad Atta 5kg")
        db_product = products_col.find_one({"name": {"$regex": item_name, "$options": "i"}})
        
        if db_product:
            unit_price = float(db_product.get("unitPrice", 0.0))
            print(f"[Pricing] Found {db_product['name']} in DB: ₹{unit_price}")
        else:
            # 2. FALLBACK TO PYTHON DICTIONARY (Generic items)
            unit_price = STORE_PRICES.get(item_name, 0.0)
            print(f"[Pricing] Brand not found. Using generic price for {item_name}: ₹{unit_price}")

        line_total = unit_price * qty
        item["unit_price"] = unit_price
        item["line_total"] = line_total
        enriched_items.append(item)
        calculated_total += line_total

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

    enriched_items, raw_total = _enrich_items_with_prices(db, order.get("items", []))
    final_total, discount_applied, original_total = _apply_group_discount(raw_total)

    order_doc = {
        "order_id":         order_id,
        "customer_name":    _resolve_customer_name(order),
        "customer_phone":   order.get("customer_phone", ""),
        "store_id":         order.get("store_id", STORE_ID),
        "language":         order.get("language", "hi"),
        "items":            enriched_items,
        "split_with":       order.get("split_with", []),
        "payment_mode":     order.get("payment_mode", "cash"),
        "input_type":       order.get("input_type", "text"),
        "raw_input_url":    order.get("raw_input_url"),
        "original_total":   original_total,
        "discount_applied": discount_applied,
        "total_amount":     final_total,
        # split_shares maps each party -> their share of the final_total (useful for downstream UIs and audits)
        "split_shares": {},
        "shopkeeper_phone": shopkeeper_phone,
        "created_at":       now,
        "status":           "pending",
    }

    orders_col.insert_one(order_doc)
    # Populate split_shares for visibility: include primary + any split_with
    try:
        parties = list(dict.fromkeys([order_doc.get("customer_name")] + (order_doc.get("split_with") or [])))
        if parties:
            per_person = round(order_doc.get("total_amount", 0.0) / len(parties), 2)
            for p in parties:
                order_doc["split_shares"][p] = per_person
            # write this back to the DB document so it's persisted
            orders_col.update_one({"order_id": order_id}, {"$set": {"split_shares": order_doc["split_shares"]}})
    except Exception:
        pass
    order_doc.pop("_id", None)

    print(
        f"[MongoDB] ✅ Order {order_id} | "
        f"₹{final_total} (disc=₹{discount_applied}) | {order_doc['customer_name']}"
    )
    return order_id, order_doc


# ── Khata Split ───────────────────────────────────────────────────────────────
def _update_khata(khata_col: Collection, order_doc: dict) -> float:
    total_amount = order_doc.get("total_amount", 0.0)
    payment_mode = order_doc.get("payment_mode", "").lower()
    split_with   = order_doc.get("split_with", [])
    store_id     = order_doc.get("store_id", STORE_ID)
    order_id     = order_doc["order_id"]
    primary_cust = order_doc["customer_name"]

    if total_amount <= 0 or payment_mode != "khata":
        print("[MongoDB] ℹ️  Not a khata order — skipping khata update.")
        return 0.0

    parties     = list(dict.fromkeys([primary_cust] + split_with))
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
                    "reminder_count": 0,
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

    # If the order had split parties, distribute lifetime spend and order_count
    # proportionally among all parties so loyalty isn't fully credited to the
    # primary customer when the basket was shared.
    split_with = order_doc.get("split_with", []) or []
    parties = list(dict.fromkeys([name] + split_with))
    per_person = round(total_amount / len(parties), 2) if parties else total_amount

    for person in parties:
        try:
            # Case-insensitive match for existing customer name to avoid duplicates
            filter_q = {"customer_name": {"$regex": f'^{re.escape(person)}$', "$options": "i"}, "store_id": store_id}
            set_on_insert = {
                "customer_name": person,
                "store_id": store_id,
                # Only set phone for primary (best-effort)
                "customer_phone": order_doc.get("customer_phone", "") if person == name else "",
            }
            result = customers_col.find_one_and_update(
                filter_q,
                {
                    "$inc": {"lifetime_spend": per_person, "order_count": 1},
                    "$set": {"last_order_at": datetime.now(timezone.utc)},
                    "$setOnInsert": set_on_insert,
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            print(f"[MongoDB] 🏆 Loyalty: {result.get('customer_name', person)} | lifetime=₹{result.get('lifetime_spend', 0)} | orders={result.get('order_count', 0)}")
        except Exception as e:
            print(f"[MongoDB] ⚠️ Failed to update loyalty for {person}: {e}")


def check_inventory_for_upsell(db, items: list) -> dict | None:
    products_col = db["products"]
    for item in items:
        item_name = item.get("name", "")
        db_product = products_col.find_one({"name": {"$regex": item_name, "$options": "i"}})
        
        if db_product and db_product.get("stock_quantity", 0) <= 0:
            category = db_product.get("category")
            substitute = products_col.find_one({
                "category": category, 
                "stock_quantity": {"$gt": 0},
                "name": {"$ne": db_product["name"]}
            })
            if substitute:
                sub_name = substitute["name"]
                orig_name = db_product["name"]
                upsell_text = (
                    f"⚠️ *Stock Alert:* Bhaiya, `{orig_name}` abhi stock mein nahi hai. "
                    f"Par uski jagah `{sub_name}` available hai. \n\n"
                    f"Saath mein 1 packet Maggi daal doon? 🍜\n\n"
                    f"👉 Reply *'YES'* to confirm substitution."
                )
                print(f"[Upsell Engine] Intercepted out-of-stock {orig_name}. Suggesting {sub_name}.")
                return {"status": "upsell_required", "message": upsell_text}
    return None

# ── Public Entry Points ────────────────────────────────────────────────────────
def log_order(order: dict, shopkeeper_phone: str):
    db            = _get_db()
    orders_col    = db["orders"]
    khata_col     = db["khata"]
    customers_col = db["customers"]

    # Pass 'db' as the first argument here!
    order_id, order_doc = _write_order(db, orders_col, order, shopkeeper_phone)
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
        return 1
    return min(result.get("reminder_count", 1), 3)
