from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings


def test_manual_order_api_and_database_agree(store):
    with TestClient(create_app(Settings(), store=store)) as client:
        body = {"request_id": "manual-0001", "customerName": "Demo", "payment_mode": "khata",
                "items": [{"productId": "rice", "quantity": 1}], "totalAmount": 1}
        a = client.post("/orders", json=body)
        assert a.status_code == 200, a.text
        assert a.json()["order"]["total_amount"] == 60
        assert client.post("/orders", json=body).json()["replayed"]
        assert client.get("/orders").json()["count"] == 1
        assert client.get("/khata/Demo").json()["total_outstanding"] == 60


def test_stock_can_be_set_to_zero(store):
    with TestClient(create_app(Settings(), store=store)) as client:
        response = client.patch("/products/rice/stock", json={"stockQuantity": 0})
        assert response.status_code == 200
        assert response.json()["product"]["stockQuantity"] == 0


def test_invalid_payment_cannot_change_balance(store):
    with TestClient(create_app(Settings(), store=store)) as client:
        for amount in [-10, 0, "NaN"]:
            assert client.post("/khata/tx", json={"request_id": "payment-0001", "customerId": "Demo",
                                                 "type": "payment", "amount": amount}).status_code == 422
        assert store.db.khata.count_documents({}) == 0


def test_production_routes_require_operator_token(store):
    with TestClient(create_app(Settings(environment="production", api_token="a" * 32), store=store)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/products").status_code == 401
        assert client.get("/products", headers={"X-API-Key": "a" * 32}).status_code == 200


def test_browser_can_read_authentication_failures_and_preflight(store):
    with TestClient(create_app(Settings(environment="production", api_token="a" * 32), store=store)) as client:
        denied = client.get("/products", headers={"Origin": "http://localhost:3000"})
        assert denied.status_code == 401
        assert denied.headers["access-control-allow-origin"] == "http://localhost:3000"
        preflight = client.options("/products", headers={"Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "X-API-Key"})
        assert preflight.status_code == 200


def test_dashboard_has_measured_sales_and_empty_analytics(store):
    with TestClient(create_app(Settings(), store=store)) as client:
        assert client.get("/dashboard").json()["todaysRevenue"] == 0
        assert client.get("/analytics").json()["analytics"]["categoryDistribution"] == [{"name": "Other", "value": 100.0}]
        assert client.get("/notifications").json()["notifications"] == []


def test_supplier_delivery_replay_cannot_duplicate_stock(store):
    with TestClient(create_app(Settings(), store=store)) as client:
        supplier = client.post("/suppliers", json={"name": "Demo Supplier"}).json()["supplier"]
        po = client.post("/purchase_orders", json={"supplierId": supplier["id"], "supplierName": "Demo Supplier",
            "items": [{"productId": "rice", "quantity": 2, "costPrice": 40}]}).json()["purchase_order"]
        for _ in range(2):
            assert client.post(f"/purchase_orders/{po['id']}/approve").status_code == 200
        for _ in range(2):
            assert client.post(f"/purchase_orders/{po['id']}/receive").status_code == 200
        assert store.db.products.find_one()["stock_milliunits"] == 102000
        assert store.db.suppliers.find_one()["outstanding_balance"] == 80


def test_unknown_purchase_product_cannot_create_supplier_liability(store):
    with TestClient(create_app(Settings(), store=store)) as client:
        supplier = client.post("/suppliers", json={"name": "Supplier"}).json()["supplier"]
        po = client.post("/purchase_orders", json={"supplierId": supplier["id"],
            "items": [{"productId": "missing", "quantity": 2, "costPrice": 40}]}).json()["purchase_order"]
        assert client.post(f"/purchase_orders/{po['id']}/approve").status_code == 404
        assert store.db.suppliers.find_one()["outstanding_balance"] == 0


def test_invalid_extracted_quantities_are_actionable_not_internal_errors(store, monkeypatch):
    from ingestion.schema import ParsedOrderPayload
    async def invalid(*args, **kwargs):
        return ParsedOrderPayload.model_validate({"payment_intent": "cash", "raw_splits": [
            {"buyer_name": "default", "raw_items": [{"name": "rice", "qty": 0, "unit": "kg"}]}]})
    monkeypatch.setattr("backend.api.ingestion.parse_order_text", invalid)
    with TestClient(create_app(Settings(), store=store)) as client:
        response = client.post("/process", json={"request_id": "extracted-0001", "payload_type": "text", "payload": "rice"})
        assert response.status_code == 422
        assert store.db.orders.count_documents({}) == 0


def test_customer_page_includes_its_own_balance_not_a_different_page(store):
    for index in range(101):
        store.db.customers.insert_one({"store_id": "store_001", "customer_name": f"Customer {index}", "lifetime_spend_paise": index})
        store.db.khata.insert_one({"store_id": "store_001", "customer_name": f"Customer {index}", "total_outstanding_paise": index * 100,
                                  "total_outstanding": index})
    with TestClient(create_app(Settings(), store=store)) as client:
        page = client.get("/customers/leaderboard?limit=1").json()
        assert page["customers"][0]["customer_name"] == "Customer 100"
        assert page["customers"][0]["total_outstanding"] == 100
        assert client.get("/customers/leaderboard?limit=1&offset=1").json()["customers"][0]["customer_name"] == "Customer 99"
