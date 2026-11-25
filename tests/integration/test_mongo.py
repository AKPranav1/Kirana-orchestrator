"""Real transaction tests. Opt in with a disposable local replica-set URI."""
from concurrent.futures import ThreadPoolExecutor
import os
from uuid import uuid4

import pytest

from backend.adapters.mongo import MongoStore
from backend.config import Settings
from backend.domain.orders import DomainError, LedgerCommand, OrderCommand
from backend.services.ledger import LedgerService
from backend.services.orders import OrderService

pytestmark = pytest.mark.integration


@pytest.fixture
def mongo():
    uri = os.getenv("KIRANA_TEST_MONGO_URI")
    if not uri:
        pytest.skip("Set KIRANA_TEST_MONGO_URI to a disposable replica set")
    database = "kirana_test_" + uuid4().hex
    store = MongoStore(Settings(mongo_uri=uri, database=database))
    store.initialize()
    store.db.products.insert_one({"store_id": "store_001", "id": "rice", "name": "Rice", "unit": "kg",
                                  "price_paise": 6000, "stock_milliunits": 100000, "stock_quantity": 100})
    try:
        yield store
    finally:
        assert database.startswith("kirana_test_")
        store.client.drop_database(database)
        store.close()


def cmd(**changes):
    return OrderCommand.model_validate({"request_id": "integration-0001", "customer_name": "Demo", "payment_mode": "khata",
                                       "items": [{"product_id": "rice", "qty": 1}], **changes})


def test_real_concurrent_replay_is_one_sale(mongo):
    service = OrderService(mongo)
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: service.submit(cmd()), range(16)))
    assert len({r["order_id"] for r in results}) == 1
    assert mongo.db.orders.count_documents({}) == 1
    assert mongo.db.khata.find_one()["total_outstanding_paise"] == 6000
    assert mongo.db.products.find_one()["stock_milliunits"] == 99000


def test_real_failure_rolls_back_an_earlier_stock_decrement(mongo):
    with pytest.raises(DomainError):
        OrderService(mongo).submit(cmd(items=[{"product_id": "rice", "qty": 1}, {"product_id": "rice", "qty": 100}]))
    assert mongo.db.products.find_one()["stock_milliunits"] == 100000
    assert mongo.db.orders.count_documents({}) == 0
    assert mongo.db.receipts.count_documents({}) == 0


def test_real_concurrent_payments_cannot_overdraw_credit(mongo):
    OrderService(mongo).submit(cmd())

    def pay(index):
        try:
            LedgerService(mongo).apply(LedgerCommand(request_id=f"payment-{index:04}", customer_name="Demo", type="payment", amount=40))
            return "paid"
        except DomainError:
            return "refused"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(pay, range(2)))
    assert sorted(outcomes) == ["paid", "refused"]
    assert mongo.db.khata.find_one()["total_outstanding_paise"] == 2000
