"""Local order-service benchmark; no external providers or production database reuse."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
import platform
import time
from uuid import uuid4

from backend.adapters.mongo import MongoStore
from backend.config import Settings
from backend.domain.orders import OrderCommand
from backend.services.orders import OrderService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uri", required=True, help="Disposable/local Mongo replica set URI")
    parser.add_argument("--orders", type=int, default=50, choices=range(1, 501), metavar="1..500")
    parser.add_argument("--concurrency", type=int, default=5, choices=range(1, 51), metavar="1..50")
    args = parser.parse_args()
    database = "kirana_benchmark_" + uuid4().hex
    store = MongoStore(Settings(mongo_uri=args.uri, database=database))
    try:
        store.initialize()
        store.db.products.insert_one({"id": "rice", "name": "Rice", "store_id": "store_001", "unit": "kg",
            "price_paise": 6000, "stock_milliunits": (args.orders + 1) * 1000, "stock_quantity": args.orders + 1})
        service = OrderService(store)

        def order(index):
            started = time.perf_counter()
            service.submit(OrderCommand(request_id=f"benchmark-{index:06}", customer_name="Benchmark Customer",
                payment_mode="khata", items=[{"product_id": "rice", "qty": 1}]))
            return (time.perf_counter() - started) * 1000

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            durations = sorted(pool.map(order, range(args.orders)))
        elapsed = time.perf_counter() - started
        assert store.db.orders.count_documents({}) == args.orders
        assert store.db.khata.find_one()["total_outstanding_paise"] == args.orders * 6000
        assert store.db.products.find_one()["stock_milliunits"] == 1000
        print(json.dumps({"scope": "order service + real Mongo; one hot product/customer; no HTTP/providers/delivery",
            "python": platform.python_version(), "platform": platform.system(), "mongo": store.client.server_info()["version"],
            "orders": args.orders, "concurrency": args.concurrency, "errors": 0, "elapsed_seconds": round(elapsed, 3),
            "orders_per_second": round(args.orders / elapsed, 2), "p50_ms": round(durations[len(durations)//2], 2),
            "p95_ms": round(durations[math.ceil(len(durations)*.95)-1], 2), "financial_invariants": "passed"}, indent=2))
    finally:
        assert database.startswith("kirana_benchmark_")
        store.client.drop_database(database)
        store.close()


if __name__ == "__main__":
    main()
