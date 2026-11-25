from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Query, Request
from pydantic import Field

from backend.domain.orders import InputModel
from backend.services.purchasing import PurchaseInput, PurchasingService
from .common import db_for, public, scope

router = APIRouter(tags=["store operations"])


class SupplierInput(InputModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field("Other", max_length=100)
    contactName: str = Field("", max_length=100)
    phone: str = Field("", max_length=40)
    avgDeliveryDays: int = Field(0, ge=0, le=365)


@router.get("/suppliers")
def suppliers(request: Request, limit: int = Query(100, ge=1, le=500)):
    docs = [public(d) for d in db_for(request).suppliers.find(scope(request)).limit(limit)]
    return {"count": len(docs), "suppliers": docs}


@router.post("/suppliers")
def create_supplier(body: SupplierInput, request: Request):
    doc = {**body.model_dump(), **scope(request), "id": f"sup-{uuid4()}", "outstanding_balance": 0,
           "outstanding_balance_paise": 0, "created_at": datetime.now(timezone.utc)}
    db_for(request).suppliers.insert_one(doc.copy())
    return {"status": "success", "supplier": public(doc)}


@router.get("/purchase_orders")
def purchase_orders(request: Request, limit: int = Query(100, ge=1, le=500)):
    docs = [public(d) for d in db_for(request).purchase_orders.find(scope(request)).sort("created_at", -1).limit(limit)]
    return {"count": len(docs), "purchase_orders": docs}


def purchasing(request):
    return PurchasingService(request.app.state.store, request.app.state.settings.store_id)


@router.post("/purchase_orders")
def create_po(body: PurchaseInput, request: Request):
    return {"status": "success", "purchase_order": public(purchasing(request).create(body))}


@router.post("/purchase_orders/{po_id}/approve")
def approve(po_id: str, request: Request):
    return {"status": "success", "purchase_order": public(purchasing(request).transition(po_id, "approve"))}


@router.post("/purchase_orders/{po_id}/receive")
def receive(po_id: str, request: Request):
    return {"status": "success", "purchase_order": public(purchasing(request).transition(po_id, "receive"))}


class StoreSettings(InputModel):
    storeName: str = Field("Kirana AI", max_length=200)
    ownerName: str = Field("Store Owner", max_length=100)
    phone: str = Field("", max_length=40)
    whatsappEnabled: bool = False
    storeStatus: str = Field("Online", pattern="^(Online|Offline)$")
    autoExtractWhatsapp: bool = False
    lowStockThreshold: int = Field(5, ge=0, le=100000)


@router.get("/settings")
def settings(request: Request):
    return {"settings": public(db_for(request).settings.find_one(scope(request)))}


@router.post("/settings")
def save_settings(body: StoreSettings, request: Request):
    doc = {**body.model_dump(), **scope(request)}
    db_for(request).settings.update_one(scope(request), {"$set": doc}, upsert=True)
    return {"status": "success", "settings": doc}
