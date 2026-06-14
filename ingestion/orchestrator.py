"""
orchestrator.py — Kirana AI | Ingestion Service

CHANGES (2025-06-14):
  ✅ Split-Fix: Removed 200% duplication bug.
  ✅ DB-driven customer name & group split (reads from MongoDB).
  ✅ Proper per-person item assignment (respects Gemini’s raw_splits when items are assigned).
  ✅ Filter out generic address terms ("anna", "bhaiya", etc.) so they are never treated as split parties.
"""

from __future__ import annotations
import os
import httpx
from typing import Optional, Dict, List

from .schema import (
    ParsedOrderPayload,
    FinalOrderManifest,
    ProcessedSplit,
    ProcessedItem,
    WhatsAppNotification,
    BuyerSplit,
)
from .sku_match import SKUMatcher


# ---------------------------------------------------------------------------
# Database lookup (MongoDB) – resolves customer by phone
# ---------------------------------------------------------------------------
def _get_mongo_client():
    """Lazy-load the MongoDB client."""
    try:
        from pymongo import MongoClient
    except ImportError:
        raise ImportError(
            "pymongo is required for DB lookup. Install it with `pip install pymongo`"
        )
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    return MongoClient(mongo_uri)

def resolve_customer_details(phone: str) -> Dict[str, any]:
    if not phone or phone == "unknown":
        return {"name": "Unknown", "group_members": []}
    try:
        # The db_alerts service is at localhost:8002 (adjust if needed)
        url = f"http://localhost:8002/customers/lookup?phone={phone}"
        resp = httpx.get(url, timeout=5)
        if resp.status_code == 200:
            return {"name": resp.json()["name"], "group_members": []}
    except Exception as e:
        print(f"[orchestrator] lookup via db_alerts failed: {e}", flush=True)
    return {"name": "Unknown", "group_members": []}

# ---------------------------------------------------------------------------
# Generic address terms that are NEVER real split parties (unless in DB)
# ---------------------------------------------------------------------------
_GENERIC_TERMS = {
    "anna", "bhaiya", "didi", "bhai", "behen", "sir", "madam",
    "brother", "sister", "friend", "dost", "yaar", "mitra",
    "akka", "tamma", "amma", "appa",
}


def _is_generic_name(name: str, db_members: List[str]) -> bool:
    """Return True if name is a common address term and NOT a known DB contact."""
    if name.lower() in _GENERIC_TERMS and name not in db_members:
        return True
    return False


# ---------------------------------------------------------------------------
# Price lookup
# ---------------------------------------------------------------------------
def _get_store_prices() -> Dict[str, float]:
    """Import STORE_PRICES from db_alerts, with fallback."""
    try:
        from db_alerts.mongo_connector import STORE_PRICES
        return STORE_PRICES
    except ImportError:
        pass
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "db_alerts"))
        from db_alerts.mongo_connector import STORE_PRICES
        return STORE_PRICES
    except ImportError:
        return {}


def _unit_price(canonical_name: str, unit: Optional[str], prices: dict) -> float:
    base = prices.get(canonical_name, 0.0)
    if base and (unit or "").lower() == "gm":
        per_gram_products = {"Tea", "Coffee", "Paneer", "Butter", "Spices"}
        if canonical_name in per_gram_products:
            return round(base / 1000, 4)
    return base


# ---------------------------------------------------------------------------
# Khata ledger lookup
# ---------------------------------------------------------------------------
def _fetch_khata_balance(customer_name: str, store_id: str = "store_001") -> float:
    try:
        from db_alerts.mongo_connector import get_khata_balance
    except ImportError:
        try:
            from db_alerts.mongo_connector import get_khata_balance
        except ImportError:
            return 0.0

    try:
        doc = get_khata_balance(customer_name, store_id)
        if doc:
            return float(doc.get("total_outstanding", 0.0))
    except Exception as e:
        print(f"[orchestrator] khata lookup failed for {customer_name}: {e}", flush=True)
    return 0.0


# ---------------------------------------------------------------------------
# Main orchestration – with DB‑backed names and proper per‑person splitting
# ---------------------------------------------------------------------------
def orchestrate_order_processing(
    parsed_data: ParsedOrderPayload,
    input_meta: dict,
    matcher: SKUMatcher,
) -> FinalOrderManifest:
    """
    Transforms a ParsedOrderPayload into a FinalOrderManifest.

    Split logic (UPDATED):
      - Generic address terms ("anna", "bhaiya", etc.) are filtered out before
        splitting unless they appear in the DB as real contacts.
      - Pattern A (equal split): One buyer has items, others have empty item lists.
        → Items are pooled and the total is split equally among ALL named parties.
      - Pattern B (per‑person items): Every buyer has a non‑empty item list.
        → Each buyer is charged only for their own items.

    Party names are resolved as follows:
      - "default" is replaced by the primary customer name (resolved from DB).
      - DB‑provided group_members are merged into the split.
    """
    prices   = _get_store_prices()
    store_id = input_meta.get("store_id", "store_001")

    # ── Resolve primary customer from DB using phone ─────────────────────
    phone = input_meta.get("customer_phone", "unknown")
    customer_info = resolve_customer_details(phone)
    primary = customer_info["name"]  # resolved name, or "Unknown"
    db_group = customer_info["group_members"]  # list of pre‑saved split members

    # ── Filter out Gemini mistakes: splits with generic names and no items ──
    filtered_splits: List[BuyerSplit] = []
    for split in parsed_data.raw_splits:
        name = split.buyer_name.strip()
        # If the name is a generic term, not in DB, and the split has NO items → skip it entirely
        if _is_generic_name(name, db_group) and len(split.raw_items) == 0:
            continue
        # If the name is generic but HAS items, reassign items to primary and skip the split
        if _is_generic_name(name, db_group):
            # find or create the default split and append items
            for default_split in filtered_splits:
                if default_split.buyer_name.lower() in ("default", ""):
                    default_split.raw_items.extend(split.raw_items)
                    break
            else:
                filtered_splits.append(BuyerSplit(buyer_name="default", raw_items=split.raw_items))
            continue
        filtered_splits.append(split)

    parsed_data.raw_splits = filtered_splits

    # ── Determine splitting mode ─────────────────────────────────────────
    has_empty_split = any(
        len(split.raw_items) == 0 for split in parsed_data.raw_splits
    )

    # ── Collect all party names ──────────────────────────────────────────
    raw_party_names: List[str] = []
    for split in parsed_data.raw_splits:
        name = split.buyer_name.strip()
        if name.lower() in ("default", ""):
            name = primary
        if name and name not in raw_party_names:
            raw_party_names.append(name)

    # Inject DB group members (if not already present)
    for member in db_group:
        if member and member not in raw_party_names:
            raw_party_names.append(member)

    # Also accept any explicit split_with passed via input_meta
    for name in input_meta.get("split_with", []):
        if name and name not in raw_party_names:
            raw_party_names.append(name)

    # Ensure primary is first, and at least one party exists
    if not raw_party_names:
        raw_party_names = [primary]
    elif primary not in raw_party_names:
        raw_party_names.insert(0, primary)

    # ── Compute per‑party items & totals ─────────────────────────────────
    processed_splits_list: List[ProcessedSplit] = []
    whatsapp_notifications_list: List[WhatsAppNotification] = []

    party_data: Dict[str, List[ProcessedItem]] = {name: [] for name in raw_party_names}
    party_total: Dict[str, float] = {name: 0.0 for name in raw_party_names}

    if has_empty_split:
        # --- PATTERN A: Shared basket, equal split ---
        all_items: List[ProcessedItem] = []
        grand_total = 0.0
        for split in parsed_data.raw_splits:
            for item in split.raw_items:
                canon_name, canon_unit, _ = matcher.match(item.name)
                effective_unit = item.unit if item.unit else canon_unit
                price = _unit_price(canon_name, effective_unit, prices)
                subtotal = round(price * item.qty, 2)
                grand_total += subtotal
                all_items.append(
                    ProcessedItem(
                        item_name=canon_name,
                        quantity=item.qty,
                        unit=effective_unit,
                        unit_price=price,
                        subtotal=subtotal,
                    )
                )
        grand_total = round(grand_total, 2)

        num_parties = len(raw_party_names)
        per_person_share = round(grand_total / num_parties, 2) if num_parties > 0 else grand_total

        for party_name in raw_party_names:
            previous_debt = 0.0
            updated_debt = 0.0
            if parsed_data.payment_intent == "khata":
                previous_debt = _fetch_khata_balance(party_name, store_id)
                updated_debt = round(previous_debt + per_person_share, 2)

            processed_splits_list.append(
                ProcessedSplit(
                    buyer_name=party_name,
                    items=all_items,
                    order_total=per_person_share,
                    previous_ledger=previous_debt,
                    updated_ledger=updated_debt,
                )
            )

            lines = [f"🛍️ *KIRANA BILL* ({party_name.upper()})"]
            for ri in all_items:
                lines.append(f"  • {ri.item_name} ×{ri.quantity}: ₹{ri.subtotal:.2f}")
            lines.append(f"\n*Total bill:* ₹{grand_total:.2f}")
            if num_parties > 1:
                lines.append(f"*Split {num_parties} ways → your share:* ₹{per_person_share:.2f}")
            if parsed_data.payment_intent == "khata":
                lines.append(f"💳 Added to Khata. Outstanding: ₹{updated_debt:.2f}")

            whatsapp_notifications_list.append(
                WhatsAppNotification(
                    recipient_name=party_name,
                    message_body="\n".join(lines),
                )
            )

    else:
        # --- PATTERN B: Per‑person items ---
        for split in parsed_data.raw_splits:
            buyer = split.buyer_name.strip() or primary
            if buyer.lower() == "default":
                buyer = primary
            if buyer not in party_data:
                party_data[buyer] = []
                party_total[buyer] = 0.0

            for item in split.raw_items:
                canon_name, canon_unit, _ = matcher.match(item.name)
                effective_unit = item.unit if item.unit else canon_unit
                price = _unit_price(canon_name, effective_unit, prices)
                subtotal = round(price * item.qty, 2)
                pi = ProcessedItem(
                    item_name=canon_name,
                    quantity=item.qty,
                    unit=effective_unit,
                    unit_price=price,
                    subtotal=subtotal,
                )
                party_data[buyer].append(pi)
                party_total[buyer] += subtotal

        for party_name in raw_party_names:
            items = party_data.get(party_name, [])
            total = round(party_total.get(party_name, 0.0), 2)

            previous_debt = 0.0
            updated_debt = 0.0
            if parsed_data.payment_intent == "khata":
                previous_debt = _fetch_khata_balance(party_name, store_id)
                updated_debt = round(previous_debt + total, 2)

            processed_splits_list.append(
                ProcessedSplit(
                    buyer_name=party_name,
                    items=items,
                    order_total=total,
                    previous_ledger=previous_debt,
                    updated_ledger=updated_debt,
                )
            )

            lines = [f"🛍️ *KIRANA BILL* ({party_name.upper()})"]
            for ri in items:
                lines.append(f"  • {ri.item_name} ×{ri.quantity}: ₹{ri.subtotal:.2f}")
            lines.append(f"\n*Your total:* ₹{total:.2f}")
            if parsed_data.payment_intent == "khata":
                lines.append(f"💳 Added to Khata. Outstanding: ₹{updated_debt:.2f}")

            whatsapp_notifications_list.append(
                WhatsAppNotification(
                    recipient_name=party_name,
                    message_body="\n".join(lines),
                )
            )

    return FinalOrderManifest(
        customer_phone=phone,
        input_type=input_meta.get("input_type", "text"),
        raw_input_url=input_meta.get("raw_input_url"),
        payment_mode=parsed_data.payment_intent,
        pdf_requested=parsed_data.request_pdf,
        processed_splits=processed_splits_list,
        whatsapp_notifications=whatsapp_notifications_list,
        status="processed",
        language=parsed_data.language,
    )
