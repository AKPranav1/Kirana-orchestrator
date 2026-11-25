from contextlib import contextmanager
from copy import deepcopy
from threading import RLock

import mongomock
import pytest


class TestStore:
    """Mongo-shaped unit double. Real Mongo isolation is tested separately."""
    __test__ = False

    def __init__(self):
        self.db = mongomock.MongoClient().kirana
        self.lock = RLock()

    def transact(self, callback):
        with self.lock:
            # A failing callback must roll back the in-memory fixture too.
            before = {n: deepcopy(list(self.db[n].find())) for n in self.db.list_collection_names()}
            try:
                return callback(self.db, None)
            except Exception:
                for n in self.db.list_collection_names():
                    self.db[n].delete_many({})
                for n, rows in before.items():
                    if rows:
                        self.db[n].insert_many(rows)
                raise

    def close(self):
        self.db.client.close()

    def ready(self):
        return True


@pytest.fixture
def store():
    result = TestStore()
    result.db.products.insert_one({"id": "rice", "store_id": "store_001", "name": "Rice", "unit": "kg",
                                   "price_paise": 6000, "stock_milliunits": 100000, "stock_quantity": 100})
    return result
