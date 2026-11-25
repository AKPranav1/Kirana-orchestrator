"""Run optional receipt delivery separately: python -m backend.worker."""
import logging
import time
from pymongo.errors import PyMongoError

from backend.adapters.mongo import MongoStore
from backend.adapters.outbox import OutboxWorker
from backend.config import Settings


def iteration(worker):
    try:
        return 0 if worker.run_once() else 1
    except PyMongoError as exc:
        logging.getLogger("kirana.delivery").warning("database unavailable type=%s", type(exc).__name__)
        return 5


def main():
    settings = Settings.from_env()
    if not settings.notifications_enabled:
        raise SystemExit("Set NOTIFICATIONS_ENABLED=true and Twilio credentials to run delivery")
    from db_alerts.alerts import send_receipt_only
    store = MongoStore(settings)
    try:
        store.initialize()
        worker = OutboxWorker(store, lambda order: send_receipt_only(order, order["customer_phone"]), store_id=settings.store_id)
        while True:
            delay = iteration(worker)
            if delay:
                time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        store.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
