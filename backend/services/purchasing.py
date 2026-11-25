"""Purchase-order transitions commit inventory and supplier effects together."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from pydantic import Field

from backend.domain.orders import DomainError, InputModel
from backend.domain.pricing import paise


class PurchaseItem(InputModel):
    productId: str = Field(min_length=1, max_length=100)
    productName: str = Field("", max_length=200)
    quantity: Decimal = Field(gt=0, le=100000, decimal_places=3)
    costPrice: Decimal = Field(gt=0, le=100000000, decimal_places=2)


class PurchaseInput(InputModel):
    supplierId: str = Field(min_length=1, max_length=100)
    supplierName: str = Field("", max_length=200)
    items: list[PurchaseItem] = Field(min_length=1, max_length=100)


class PurchasingService:
    def __init__(self, store, store_id):
        self.store, self.store_id = store, store_id

    def create(self, body):
        doc = {**body.model_dump(mode="json"), "store_id": self.store_id, "id": f"PO-{uuid4()}",
               "status": "Awaiting Approval", "deliveryProgress": 0, "created_at": datetime.now(timezone.utc)}
        doc["total_paise"] = sum(paise(item.quantity * item.costPrice) for item in body.items)
        doc["totalAmount"] = doc["total_paise"] / 100
        for item, original in zip(doc["items"], body.items):
            item["quantity"], item["costPrice"] = float(original.quantity), float(original.costPrice)
        self.store.db.purchase_orders.insert_one(doc.copy())
        return doc

    def transition(self, po_id, action):
        query = {"store_id": self.store_id, "id": po_id}

        def commit(db, session):
            doc = db.purchase_orders.find_one(query, session=session)
            if doc is None:
                raise DomainError("Purchase order not found", 404)
            if action == "approve":
                if doc["status"] in ("In Transit", "Delivered"):
                    return doc
                if doc["status"] != "Awaiting Approval":
                    raise DomainError("Purchase order cannot be approved", 409)
                for item in doc["items"]:
                    if db.products.find_one({"store_id": self.store_id, "id": item["productId"]}, session=session) is None:
                        raise DomainError("Purchase order product not found; correct the draft before approval", 404)
                supplier = db.suppliers.update_one({"store_id": self.store_id, "id": doc["supplierId"]},
                    {"$inc": {"outstanding_balance_paise": doc["total_paise"], "outstanding_balance": doc["totalAmount"]}}, session=session)
                if supplier.matched_count != 1:
                    raise DomainError("Supplier not found", 404)
                updates = {"status": "In Transit", "deliveryProgress": 10}
            else:
                if doc["status"] == "Delivered":
                    return doc
                if doc["status"] != "In Transit":
                    raise DomainError("Approve the purchase order before receiving it", 409)
                for item in doc["items"]:
                    quantity = Decimal(str(item["quantity"]))
                    product = db.products.update_one({"store_id": self.store_id, "id": item["productId"]},
                        {"$inc": {"stock_milliunits": int(quantity * 1000), "stock_quantity": float(quantity)}}, session=session)
                    if product.matched_count != 1:
                        raise DomainError("Purchase order product not found", 404)
                updates = {"status": "Delivered", "deliveryProgress": 100}
            db.purchase_orders.update_one(query, {"$set": updates}, session=session)
            return {**doc, **updates}

        return self.store.transact(commit)
