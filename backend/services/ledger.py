"""Validated, scoped credit/payment operations with durable replay receipts."""
from datetime import datetime, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from backend.domain.orders import DomainError, LedgerCommand
from backend.domain.pricing import paise, rupees
from .commands import identity, replay


class LedgerService:
    def __init__(self, store, *, store_id="store_001"):
        self.store, self.store_id = store, store_id

    def apply(self, command: LedgerCommand) -> dict:
        key, fingerprint = identity(command, "ledger", self.store_id)
        amount = paise(command.amount)

        def commit(db, session):
            previous = replay(db, key, fingerprint, session)
            if previous:
                return previous
            scope = {"store_id": self.store_id, "customer_name": command.customer_name}
            now = datetime.now(timezone.utc)
            if command.type == "payment":
                query = {**scope, "total_outstanding_paise": {"$gte": amount}}
                change = -amount
            else:
                query, change = scope, amount
            doc = db.khata.find_one_and_update(query, {"$inc": {"total_outstanding_paise": change, "total_outstanding": rupees(change)},
                    "$set": {"last_updated": now}, "$setOnInsert": {"reminder_count": 0}},
                    upsert=command.type == "credit", return_document=ReturnDocument.AFTER, session=session)
            if doc is None:
                raise DomainError("Payment exceeds the current outstanding balance", 409)
            entry = {"id": f"tx-{key[:32]}", "customerId": command.customer_name, "customerName": command.customer_name,
                     "type": command.type, "amount": rupees(amount), "date": now.isoformat(), "description": command.description}
            db.ledger_entries.insert_one({"_id": entry["id"], "order_id": entry["id"], **scope, **entry,
                                          "amount_paise": amount, "settled": command.type == "payment",
                                          "balance_after_paise": doc["total_outstanding_paise"]}, session=session)
            result = {"status": "success", "transaction": entry, "newBalance": rupees(doc["total_outstanding_paise"]), "replayed": False}
            db.receipts.insert_one({"_id": key, "fingerprint": fingerprint, "result": result, "created_at": now}, session=session)
            return result

        try:
            return self.store.transact(commit)
        except DuplicateKeyError:
            result = replay(self.store.db, key, fingerprint, None)
            if result:
                return result
            raise DomainError("Concurrent update; retry with the same request ID", 409)
