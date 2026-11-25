from datetime import datetime, timedelta, timezone

from backend.adapters.outbox import OutboxWorker


def test_failed_delivery_is_retryable_without_recreating_order(store):
    now = datetime.now(timezone.utc)
    store.db.orders.insert_one({"order_id": "ord-1", "store_id": "store_001"})
    store.db.outbox.insert_one({"_id": "job-1", "order_id": "ord-1", "store_id": "store_001", "status": "pending", "attempts": 0, "available_at": now})
    attempts = []

    def deliver(order):
        attempts.append(order["order_id"])
        if len(attempts) == 1:
            raise RuntimeError("provider down")

    worker = OutboxWorker(store, deliver, clock=lambda: now)
    assert worker.run_once()
    assert store.db.outbox.find_one()["status"] == "pending"
    worker.clock = lambda: now + timedelta(minutes=5)
    assert worker.run_once()
    assert store.db.outbox.find_one()["status"] == "sent"
    assert store.db.orders.count_documents({}) == 1


def test_abandoned_lease_can_be_reclaimed(store):
    now = datetime.now(timezone.utc)
    store.db.orders.insert_one({"order_id": "ord-1", "store_id": "store_001"})
    store.db.outbox.insert_one({"_id": "job-1", "order_id": "ord-1", "store_id": "store_001", "status": "processing", "attempts": 1,
                               "available_at": now - timedelta(minutes=3), "lease_until": now - timedelta(seconds=1)})
    assert OutboxWorker(store, lambda order: None).run_once()
    assert store.db.outbox.find_one()["status"] == "sent"
