"""Translate extracted language into uncommitted commands. No prices, ledger or I/O."""
from backend.domain.orders import DomainError, OrderCommand
from .schema import ParsedOrderPayload
from .sku_match import SKUMatcher
from pydantic import ValidationError


def validated_command(**values):
    try:
        return OrderCommand(**values)
    except ValidationError as exc:
        raise DomainError("Extracted order needs correction: check quantities, payment mode and buyer names") from exc


def orders_from_parsed(parsed: ParsedOrderPayload, *, customer_name: str, customer_phone: str,
                       request_id: str, matcher: SKUMatcher, store_id: str = "store_001") -> list[OrderCommand]:
    if not parsed.raw_splits or not any(split.raw_items for split in parsed.raw_splits):
        raise DomainError("No order items found; specify products and quantities")

    def name(split):
        return customer_name if split.buyer_name.casefold() in ("default", "unknown", "") else split.buyer_name

    def items(raw):
        result = []
        for item in raw:
            canonical, unit, score = matcher.match(item.name)
            if score < 85:
                raise DomainError(f"Please specify the catalogue product for {item.name}")
            result.append({"name": canonical, "qty": item.qty, "unit": item.unit or unit})
        return result

    common = {"customer_phone": customer_phone, "store_id": store_id, "payment_mode": parsed.payment_intent,
              "language": parsed.language, "input_type": "text"}
    # Empty participant item lists mean one shared basket, emitted only once.
    if any(not split.raw_items for split in parsed.raw_splits):
        people = list(dict.fromkeys([customer_name, *(name(s) for s in parsed.raw_splits)]))
        basket = items([item for split in parsed.raw_splits for item in split.raw_items])
        return [validated_command(request_id=request_id, customer_name=people[0], split_with=people[1:], items=basket, **common)]
    return [validated_command(request_id=request_id if len(parsed.raw_splits) == 1 else f"{request_id}:{index}",
                         customer_name=name(split), items=items(split.raw_items), **common)
            for index, split in enumerate(parsed.raw_splits)]
