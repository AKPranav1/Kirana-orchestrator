"""One bounded client pool per process; transaction-only financial writes."""
from pymongo import ASCENDING, DESCENDING, MongoClient, timeout
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from backend.domain.orders import DomainError


class MongoStore:
    def __init__(self, settings):
        self.operation_timeout = settings.operation_timeout
        self.client = MongoClient(settings.mongo_uri, maxPoolSize=settings.max_pool_size, waitQueueTimeoutMS=5000,
                                  serverSelectionTimeoutMS=5000, connectTimeoutMS=5000, socketTimeoutMS=15000,
                                  tz_aware=True, appname="kirana")
        self.db = self.client[settings.database]

    def initialize(self):
        hello = self.client.admin.command("hello")
        if not hello.get("setName") and hello.get("msg") != "isdbgrid":
            raise RuntimeError("Kirana requires a Mongo replica set for atomic order and ledger writes; see compose.yaml")
        # Mixing old floating balances with new exact counters would lose history.
        for collection, field in [("products", "stock_milliunits"), ("orders", "total_paise"), ("khata", "total_outstanding_paise")]:
            if self.db[collection].find_one({field: {"$exists": False}}, {"_id": 1}) is not None:
                raise RuntimeError("Legacy data needs an explicit migration/reconciliation; use a fresh database for this increment")
        indexes = {
            "products": [("store_id", ASCENDING), ("id", ASCENDING)],
            "customers": [("store_id", ASCENDING), ("customer_name", ASCENDING)],
            "khata": [("store_id", ASCENDING), ("customer_name", ASCENDING)],
        }
        for name, keys in indexes.items():
            self.db[name].create_index(keys, unique=True)
        self.db.orders.create_index([("store_id", ASCENDING), ("created_at", DESCENDING)])
        self.db.ledger_entries.create_index([("store_id", ASCENDING), ("customer_name", ASCENDING), ("date", DESCENDING)])
        self.db.customers.create_index([("store_id", ASCENDING), ("customer_phone", ASCENDING)])
        self.db.outbox.create_index([("status", ASCENDING), ("available_at", ASCENDING)])
        self.db.suppliers.create_index([("store_id", ASCENDING), ("id", ASCENDING)], unique=True)
        self.db.purchase_orders.create_index([("store_id", ASCENDING), ("id", ASCENDING)], unique=True)
        self.db.settings.create_index("store_id", unique=True)

    def transact(self, callback):
        # CSOT bounds the whole callback/retry sequence, not only commit.
        with timeout(self.operation_timeout), self.client.start_session() as session:
            return session.with_transaction(lambda active: callback(self.db, active),
                                            read_concern=ReadConcern("snapshot"), write_concern=WriteConcern("majority"),
                                            max_commit_time_ms=5000)

    def ready(self):
        self.client.admin.command("ping")
        return True

    def close(self):
        self.client.close()
