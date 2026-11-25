"""Receipt rendering uses committed values and allocations; it never reprices."""
from decimal import Decimal


def money(paise):
    return f"{Decimal(paise) / 100:.2f}"


def create_text_bill(order: dict) -> str:
    lines = ["Kirana AI receipt", f"Customer: {order.get('customer_name', 'Walk-in')}"]
    for item in order.get("items", []):
        lines.append(f"{item['name']} x {item['qty']} {item.get('unit', '')}: ₹{money(item['line_total_paise'])}")
    if order.get("discount_paise"):
        lines.append(f"Discount: ₹{money(order['discount_paise'])}")
    lines.append(f"Total: ₹{money(order['total_paise'])}")
    for name, share in order.get("split_shares_paise", {}).items():
        lines.append(f"{name}: ₹{money(share)}")
    return "\n".join(lines)
