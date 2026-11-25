"""Durable at-least-once delivery with expiring leases and bounded retries."""
from datetime import datetime, timedelta, timezone
import logging
from uuid import uuid4

from pymongo import ReturnDocument

logger = logging.getLogger("kirana.delivery")


class OutboxWorker:
    def __init__(self, store, deliver, *, store_id="store_001", clock=None):
        self.store, self.deliver, self.store_id = store, deliver, store_id
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def run_once(self):
        now, token = self.clock(), uuid4().hex
        jobs = self.store.db.outbox
        jobs.update_many({"store_id": self.store_id, "status": "processing", "attempts": {"$gte": 5}, "lease_until": {"$lte": now}},
                         {"$set": {"status": "failed", "last_error": "LeaseExpired"}})
        job = jobs.find_one_and_update({"store_id": self.store_id, "attempts": {"$lt": 5}, "$or": [
            {"status": "pending", "available_at": {"$lte": now}}, {"status": "processing", "lease_until": {"$lte": now}}]},
            {"$set": {"status": "processing", "lease_token": token, "lease_until": now + timedelta(minutes=3)}, "$inc": {"attempts": 1}},
            sort=[("available_at", 1)], return_document=ReturnDocument.AFTER)
        if job is None:
            return False
        lease = {"_id": job["_id"], "lease_token": token, "status": "processing"}
        try:
            order = self.store.db.orders.find_one({"store_id": self.store_id, "order_id": job["order_id"]})
            if order is None:
                raise RuntimeError("OrderMissing")
            self.deliver(order)
            jobs.update_one(lease, {"$set": {"status": "sent", "sent_at": self.clock()}, "$unset": {"lease_token": "", "lease_until": ""}})
        except Exception as exc:
            # Provider bodies may contain PII/credentials. Store the class only.
            logger.warning("delivery failed job=%s type=%s", job["_id"], type(exc).__name__)
            jobs.update_one(lease, {"$set": {"status": "failed" if job["attempts"] >= 5 else "pending", "last_error": type(exc).__name__,
                "available_at": self.clock() + timedelta(seconds=min(300, 2 ** job["attempts"]))}, "$unset": {"lease_token": "", "lease_until": ""}})
        return True
