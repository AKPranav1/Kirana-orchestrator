"""One exact pricing authority; client totals and client prices are never trusted."""
from decimal import Decimal, ROUND_HALF_UP

from .orders import DomainError, OrderCommand

UNITS = {
    "kg": ("kg", Decimal(1)), "kilo": ("kg", Decimal(1)),
    "g": ("kg", Decimal(".001")), "gm": ("kg", Decimal(".001")), "gram": ("kg", Decimal(".001")),
    "litre": ("litre", Decimal(1)), "liter": ("litre", Decimal(1)), "l": ("litre", Decimal(1)),
    "ml": ("litre", Decimal(".001")),
    "packet": ("packet", Decimal(1)), "pack": ("packet", Decimal(1)),
    "piece": ("piece", Decimal(1)), "pc": ("piece", Decimal(1)),
    "bottle": ("bottle", Decimal(1)),
}


def paise(value) -> int:
    number = Decimal(str(value))
    if not number.is_finite():
        raise DomainError("Money must be finite")
    return int((number * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def rupees(value: int) -> float:
    return float(Decimal(value) / 100)


def price_order(command: OrderCommand, products: list[dict]) -> dict:
    lines = []
    for item in command.items:
        matches = [p for p in products if (p["id"] == item.product_id if item.product_id else p["name"].casefold() == item.name.casefold())]
        if len(matches) != 1:
            raise DomainError(f"Choose an exact catalogue product for {item.product_id or item.name}")
        product = matches[0]
        base = UNITS.get(str(product.get("unit", "")).casefold())
        requested = UNITS.get(item.unit or str(product.get("unit", "")).casefold())
        if base is None or requested is None or base[0] != requested[0]:
            raise DomainError(f"Incompatible or missing unit for {product['name']}")
        quantity = item.qty * requested[1] / base[1]
        milliunits = quantity * 1000
        if milliunits != milliunits.to_integral_value():
            raise DomainError("Quantity is smaller than the supported stock precision")
        price = product.get("price_paise")
        if not isinstance(price, int) or isinstance(price, bool) or price <= 0:
            raise DomainError(f"Missing valid catalogue price for {product['name']}")
        subtotal = int((quantity * price).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        if subtotal <= 0:
            raise DomainError("Order line is below one paise")
        lines.append({"product_id": product["id"], "name": product["name"], "qty": float(quantity),
                      "unit": product["unit"], "unit_price": rupees(price), "price_paise": price,
                      "stock_milliunits": int(milliunits), "line_total_paise": subtotal, "line_total": rupees(subtotal)})
    original = sum(line["line_total_paise"] for line in lines)
    discount = int((Decimal(original) / 10).quantize(Decimal(1), rounding=ROUND_HALF_UP)) if original >= 150000 else 0
    total = original - discount
    people = [command.customer_name, *command.split_with]
    quotient, residual = divmod(total, len(people))
    shares = {name: quotient + (index < residual) for index, name in enumerate(people)}
    return {"items": lines, "original_total_paise": original, "discount_paise": discount,
            "total_paise": total, "split_shares_paise": shares}
