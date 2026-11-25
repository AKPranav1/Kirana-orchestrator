from decimal import Decimal

import pytest

from backend.domain.orders import DomainError, OrderCommand, LedgerCommand
from backend.services.orders import OrderService
from backend.services.ledger import LedgerService


def order(**changes):
    return OrderCommand.model_validate({"request_id": "order-0001", "customer_name": "Demo", "payment_mode": "khata",
                                       "items": [{"product_id": "rice", "qty": 1}], **changes})


def test_order_replay_does_not_charge_or_decrement_twice(store):
    service = OrderService(store)
    a, b = service.submit(order()), service.submit(order())
    assert a["order"]["order_id"] == b["order"]["order_id"]
    assert b["replayed"] is True
    assert store.db.orders.count_documents({}) == 1
    assert store.db.khata.find_one()["total_outstanding_paise"] == 6000
    assert store.db.products.find_one()["stock_milliunits"] == 99000
    assert store.db.outbox.count_documents({}) == 0


def test_same_key_different_order_is_a_conflict(store):
    service = OrderService(store)
    service.submit(order())
    with pytest.raises(DomainError) as exc:
        service.submit(order(items=[{"product_id": "rice", "qty": 2}]))
    assert exc.value.status_code == 409


def test_one_shared_order_allocates_one_sale(store):
    result = OrderService(store).submit(order(split_with=["B", "C"]))
    assert result["order"]["total_amount"] == 60
    assert store.db.orders.count_documents({}) == 1
    assert sorted(x["total_outstanding_paise"] for x in store.db.khata.find()) == [2000, 2000, 2000]


def test_insufficient_stock_leaves_no_order_or_ledger(store):
    with pytest.raises(DomainError):
        OrderService(store).submit(order(items=[{"product_id": "rice", "qty": 101}]))
    assert store.db.orders.count_documents({}) == 0
    assert store.db.khata.count_documents({}) == 0


def test_cash_order_does_not_create_credit(store):
    OrderService(store).submit(order(payment_mode="cash"))
    assert store.db.khata.count_documents({}) == 0


def test_notification_job_is_optional_and_replayed_once(store):
    service = OrderService(store, notifications_enabled=True)
    cmd = order(customer_phone="+919999999999")
    service.submit(cmd)
    service.submit(cmd)
    assert store.db.outbox.count_documents({}) == 1


def test_payment_replay_and_overpayment_preserve_balance(store):
    OrderService(store).submit(order())
    service = LedgerService(store)
    cmd = LedgerCommand(request_id="payment-0001", customer_name="Demo", type="payment", amount=40)
    service.apply(cmd)
    service.apply(cmd)
    assert store.db.khata.find_one()["total_outstanding_paise"] == 2000
    with pytest.raises(DomainError):
        service.apply(cmd.model_copy(update={"request_id": "payment-0002", "amount": Decimal("30")}))
    assert store.db.khata.find_one()["total_outstanding_paise"] == 2000


def test_store_boundary_cannot_be_overridden(store):
    with pytest.raises(DomainError):
        OrderService(store).submit(order(store_id="another"))


def test_numeric_reserialization_is_the_same_command(store):
    service = OrderService(store)
    service.submit(order(items=[{"product_id": "rice", "qty": 1}]))
    assert service.submit(order(items=[{"product_id": "rice", "qty": 1.0}]))["replayed"]
