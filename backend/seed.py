"""Idempotent fictional sample data. Never resets stock or financial records."""
import json
from pathlib import Path

from backend.adapters.mongo import MongoStore
from backend.config import Settings


def seed(store, store_id="store_001"):
    rows = json.loads((Path(__file__).parent / "data/catalogue.json").read_text(encoding="utf-8"))
    for row in rows:
        quantity = 10000 if row["unit"] == "gm" else 100
        doc = {**row, "store_id": store_id, "stock_milliunits": quantity * 1000, "stock_quantity": quantity}
        store.db.products.update_one({"store_id": store_id, "id": row["id"]}, {"$setOnInsert": doc}, upsert=True)
    store.db.customers.update_one({"store_id": store_id, "customer_name": "Demo Customer"},
        {"$setOnInsert": {"customer_phone": "", "lifetime_spend_paise": 0, "lifetime_spend": 0, "order_count": 0}}, upsert=True)
    store.db.suppliers.update_one({"store_id": store_id, "id": "sup-demo"},
        {"$setOnInsert": {"name": "Sample Supplier", "phone": "", "category": "Sample catalogue", "contactName": "",
                         "avgDeliveryDays": 2, "outstanding_balance_paise": 0, "outstanding_balance": 0}}, upsert=True)
    return len(rows)


def main():
    settings = Settings.from_env()
    store = MongoStore(settings)
    try:
        store.initialize()
        print(f"Seeded {seed(store, settings.store_id)} fictional products; existing records were preserved.")
    finally:
        store.close()


if __name__ == "__main__":
    main()
