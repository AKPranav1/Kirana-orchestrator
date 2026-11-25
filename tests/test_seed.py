from backend.seed import seed


def test_seeding_twice_preserves_existing_stock_and_creates_no_financial_history(store):
    seed(store)
    store.db.products.update_one({"id": "rice"}, {"$set": {"stock_milliunits": 1234}})
    seed(store)
    assert store.db.products.find_one({"id": "rice"})["stock_milliunits"] == 1234
    assert store.db.products.count_documents({}) == 27
    assert store.db.orders.count_documents({}) == 0
    assert store.db.khata.count_documents({}) == 0
