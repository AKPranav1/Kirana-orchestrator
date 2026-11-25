"""Order, inventory, ledger and delivery intent share a single commit boundary."""
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument

from backend.domain.orders import DomainError, OrderCommand
from backend.domain.pricing import price_order, rupees
from .commands import identity, replay


class OrderService:
    def __init__(self, store, *, store_id="store_001", notifications_enabled=False):
        self.store = store
        self.store_id = store_id
        self.notifications_enabled = notifications_enabled

    def submit(self, command: OrderCommand) -> dict:
        key, fingerprint = identity(command, "order", self.store_id)

        def commit(db, session):
            previous = replay(db, key, fingerprint, session)
            if previous:
                return previous
            products = list(db.products.find({"store_id": self.store_id}, session=session))
            priced = price_order(command, products)
            now = datetime.now(timezone.utc)
            order_id = f"ord-{key[:32]}"
            for line in priced["items"]:
                updated = db.products.update_one(
                    {"store_id": self.store_id, "id": line["product_id"], "stock_milliunits": {"$gte": line["stock_milliunits"]}},
                    {"$inc": {"stock_milliunits": -line["stock_milliunits"], "stock_quantity": -line["qty"]}}, session=session)
                if updated.modified_count != 1:
                    raise DomainError(f"Insufficient stock for {line['name']}", 409)
            doc = {**priced, "order_id": order_id, "store_id": self.store_id, "customer_name": command.customer_name,
                   "customer_phone": command.customer_phone, "payment_mode": command.payment_mode,
                   "language": command.language, "input_type": command.input_type, "split_with": command.split_with,
                   "total_amount": rupees(priced["total_paise"]), "original_total": rupees(priced["original_total_paise"]),
                   "discount_applied": rupees(priced["discount_paise"]), "status": "Processed", "created_at": now}
            db.orders.insert_one({"_id": order_id, **doc}, session=session)
            for name, share in priced["split_shares_paise"].items():
                if command.payment_mode == "khata":
                    balance = db.khata.find_one_and_update({"store_id": self.store_id, "customer_name": name},
                        {"$inc": {"total_outstanding_paise": share, "total_outstanding": rupees(share)},
                         "$set": {"last_updated": now}, "$setOnInsert": {"reminder_count": 0}}, upsert=True,
                         return_document=ReturnDocument.AFTER, session=session)
                    db.ledger_entries.insert_one({"_id": f"{order_id}:{name}", "order_id": order_id, "store_id": self.store_id,
                        "customer_name": name, "amount_paise": share, "amount": rupees(share), "type": "credit",
                        "settled": False, "date": now.isoformat(), "description": "Order purchase",
                        "balance_after_paise": balance["total_outstanding_paise"]}, session=session)
                db.customers.update_one({"store_id": self.store_id, "customer_name": name},
                    {"$inc": {"lifetime_spend_paise": share, "lifetime_spend": rupees(share), "order_count": 1},
                     "$set": {"last_order_at": now}, "$setOnInsert": {"customer_phone": command.customer_phone if name == command.customer_name else ""}},
                    upsert=True, session=session)
            status = "disabled"
            if self.notifications_enabled and command.customer_phone:
                db.outbox.insert_one({"_id": order_id, "kind": "receipt", "order_id": order_id, "store_id": self.store_id,
                                      "status": "pending", "attempts": 0, "available_at": now, "created_at": now}, session=session)
                status = "queued"
            # Store a JSON-compatible receipt so retries return the same public shape.
            doc["created_at"] = now.isoformat()
            result = {"status": "success", "order_id": order_id, "order": doc, "alert_status": status, "replayed": False}
            db.receipts.insert_one({"_id": key, "fingerprint": fingerprint, "result": result, "created_at": now}, session=session)
            return result

        try:
            return self.store.transact(commit)
        except DuplicateKeyError:
            result = replay(self.store.db, key, fingerprint, None)
            if result:
                return result
            raise DomainError("Concurrent update; retry with the same request ID", 409)
