from backend.domain.receipts import create_text_bill


def test_receipt_displays_persisted_residual_allocation():
    receipt = create_text_bill({"customer_name": "Demo", "items": [], "total_amount": 100, "total_paise": 10000,
        "split_with": ["B", "C"], "split_shares_paise": {"Demo": 3334, "B": 3333, "C": 3333}})
    assert "Demo: ₹33.34" in receipt
    assert "B: ₹33.33" in receipt
    assert "C: ₹33.33" in receipt
