from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.domain.orders import OrderCommand, DomainError
from backend.domain.pricing import price_order


PRODUCTS = [
    {"id": "rice", "name": "Rice", "unit": "kg", "price_paise": 6000},
    {"id": "tea", "name": "Tea", "unit": "kg", "price_paise": 28000},
    {"id": "soap", "name": "Soap", "unit": "piece", "price_paise": 10000},
]


def command(**changes):
    return OrderCommand.model_validate({
        "request_id": "request-0001", "customer_name": "Demo", "payment_mode": "khata",
        "items": [{"name": "Rice", "qty": 500, "unit": "gm"}], **changes,
    })


def test_grams_use_catalogue_base_unit_and_ignore_client_price():
    result = price_order(command(items=[{"name": "Rice", "qty": 500, "unit": "gm", "unit_price": 1}]), PRODUCTS)
    assert result["total_paise"] == 3000
    assert result["items"][0]["stock_milliunits"] == 500


def test_tea_kilogram_has_one_authoritative_price():
    assert price_order(command(items=[{"product_id": "tea", "quantity": 1, "unit": "kg"}]), PRODUCTS)["total_paise"] == 28000


def test_split_residual_paise_are_conserved():
    result = price_order(command(items=[{"name": "Soap", "qty": 1}], split_with=["B", "C"]), PRODUCTS)
    assert result["split_shares_paise"] == {"Demo": 3334, "B": 3333, "C": 3333}
    assert result["total_paise"] == 10000


@pytest.mark.parametrize("item", [
    {"name": "Unknown", "qty": 1}, {"name": "Rice", "qty": 1, "unit": "bottle"},
])
def test_unresolved_product_or_unit_cannot_be_billed(item):
    with pytest.raises(DomainError):
        price_order(command(items=[item]), PRODUCTS)


def test_ambiguous_name_needs_an_explicit_product_identity():
    with pytest.raises(DomainError):
        price_order(command(), PRODUCTS + [{"id": "rice-2", "name": "Rice", "unit": "kg", "price_paise": 7000}])


@pytest.mark.parametrize("qty", [0, -1, "NaN", "Infinity", "0.00001"])
def test_invalid_quantities_are_rejected(qty):
    with pytest.raises((ValidationError, DomainError)):
        price_order(command(items=[{"name": "Rice", "qty": qty}]), PRODUCTS)


def test_discount_applies_once_before_allocating_shared_sale():
    result = price_order(command(items=[{"name": "Rice", "qty": 30}], split_with=["B"]), PRODUCTS)
    assert result["original_total_paise"] == 180000
    assert result["discount_paise"] == 18000
    assert result["split_shares_paise"] == {"Demo": 81000, "B": 81000}


def test_customer_and_store_fields_do_not_change_price():
    assert command().items[0].qty == Decimal("500")
    assert price_order(command(customer_name="Another"), PRODUCTS)["total_paise"] == 3000
