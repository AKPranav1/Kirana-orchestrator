from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import AliasChoices, Field
from pymongo import ReturnDocument

from backend.domain.orders import InputModel
from backend.domain.pricing import paise
from .common import db_for, product_view, public, scope

router = APIRouter(tags=["catalogue and customers"])


class ProductInput(InputModel):
    name: str = Field(min_length=1, max_length=200)
    unit: str = Field(min_length=1, max_length=20)
    unit_price: Decimal = Field(gt=0, le=100000000, decimal_places=2, validation_alias=AliasChoices("unit_price", "unitPrice"))
    stock: Decimal = Field(0, ge=0, le=1000000, decimal_places=3, validation_alias=AliasChoices("stock", "stock_quantity", "stockQuantity"))
    sku: str = Field("", max_length=100)
    category: str = Field("Other", max_length=100)
    costPrice: float = Field(0, ge=0, allow_inf_nan=False)
    supplierId: str = Field("", max_length=100)
    supplierName: str = Field("", max_length=100)


class StockUpdate(InputModel):
    quantity: Decimal = Field(ge=0, le=1000000, decimal_places=3, validation_alias=AliasChoices("stockQuantity", "stock_quantity", "quantity"))


@router.get("/products")
def products(request: Request, limit: int = Query(200, ge=1, le=500)):
    docs = [product_view(d) for d in db_for(request).products.find(scope(request)).limit(limit)]
    return {"count": len(docs), "products": docs}


@router.post("/products")
def create_product(body: ProductInput, request: Request):
    from backend.domain.pricing import UNITS
    if body.unit not in UNITS:
        raise HTTPException(422, "Unsupported catalogue unit")
    doc = {**body.model_dump(mode="json", exclude={"stock", "unit_price"}), **scope(request), "id": f"prod-{uuid4()}",
           "price_paise": paise(body.unit_price), "stock_milliunits": int(body.stock * 1000), "stock_quantity": float(body.stock)}
    db_for(request).products.insert_one(doc.copy())
    return {"status": "success", "product": product_view(doc)}


@router.patch("/products/{product_id}/stock")
def stock(product_id: str, body: StockUpdate, request: Request):
    doc = db_for(request).products.find_one_and_update({**scope(request), "id": product_id},
        {"$set": {"stock_milliunits": int(body.quantity * 1000), "stock_quantity": float(body.quantity)}}, return_document=ReturnDocument.AFTER)
    if doc is None:
        raise HTTPException(404, "Product not found")
    return {"status": "success", "product": product_view(doc)}


class CustomerInput(InputModel):
    customer_name: str = Field(min_length=1, max_length=100, validation_alias=AliasChoices("customer_name", "name"))
    customer_phone: str = Field("", max_length=40, validation_alias=AliasChoices("customer_phone", "phone"))


@router.post("/customers")
def create_customer(body: CustomerInput, request: Request):
    query = {**scope(request), "customer_name": body.customer_name}
    db_for(request).customers.update_one(query, {"$set": {"customer_phone": body.customer_phone},
                "$setOnInsert": {"lifetime_spend": 0, "lifetime_spend_paise": 0, "order_count": 0}}, upsert=True)
    return {"status": "success", "customer": public(db_for(request).customers.find_one(query))}


@router.get("/customers/leaderboard")
def customers(request: Request, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0, le=100000),
              order_by: str = Query("spend", pattern="^(spend|name)$")):
    db = db_for(request)
    ordering = [("customer_name", 1)] if order_by == "name" else [("lifetime_spend_paise", -1), ("customer_name", 1)]
    docs = [public(d) for d in db.customers.find(scope(request)).sort(ordering).skip(offset).limit(limit)]
    balances = {d["customer_name"]: d.get("total_outstanding_paise", 0) for d in db.khata.find(
        {**scope(request), "customer_name": {"$in": [d["customer_name"] for d in docs]}})}
    for doc in docs:
        doc["total_outstanding_paise"] = balances.get(doc["customer_name"], 0)
        doc["total_outstanding"] = doc["total_outstanding_paise"] / 100
    return {"count": len(docs), "customers": docs}


@router.get("/customers/lookup")
def customer_lookup(phone: str, request: Request):
    # Normalized exact identity; never a substring of another customer's phone.
    normalized = "".join(c for c in phone if c.isdigit())
    if not normalized:
        raise HTTPException(422, "A phone number is required")
    doc = db_for(request).customers.find_one({**scope(request), "customer_phone": {"$in": [phone, normalized, "+" + normalized, "whatsapp:+" + normalized]}})
    if doc is None:
        raise HTTPException(404, "Customer not found")
    return {"name": doc["customer_name"], "group_members": doc.get("group_members", [])}
