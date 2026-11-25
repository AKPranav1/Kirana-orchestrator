from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from backend.domain.orders import LedgerCommand, OrderCommand
from backend.services.ledger import LedgerService
from backend.services.orders import OrderService
from .common import db_for, public, scope

router = APIRouter(tags=["orders and ledger"])


def submit(request, command):
    settings = request.app.state.settings
    return OrderService(request.app.state.store, store_id=settings.store_id,
                        notifications_enabled=settings.notifications_enabled).submit(command)


@router.post("/orders")
def create_order(command: OrderCommand, request: Request):
    return submit(request, command)


class LegacyLog(BaseModel):
    order: OrderCommand
    shopkeeper_phone: str = ""
    profile_name: str | None = None


@router.post("/log", deprecated=True)
def log_order(body: LegacyLog, request: Request):
    return submit(request, body.order)


@router.get("/orders")
def orders(request: Request, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0, le=100000)):
    rows = db_for(request).orders.find(scope(request), {"_id": 0}).sort("created_at", -1).skip(offset).limit(limit)
    docs = [public(d) for d in rows]
    return {"count": len(docs), "orders": docs}


@router.get("/orders/{order_id}/receipt")
def receipt(order_id: str, request: Request):
    doc = db_for(request).orders.find_one({**scope(request), "order_id": order_id})
    if doc is None:
        raise HTTPException(404, "Order not found")
    from backend.domain.receipts import create_text_bill
    return {"order_id": order_id, "receipt": create_text_bill(doc)}


@router.get("/khata")
def khata(request: Request, limit: int = Query(100, ge=1, le=500)):
    rows = [public(d) for d in db_for(request).khata.find(scope(request), {"_id": 0}).limit(limit)]
    return {"count": len(rows), "records": rows}


@router.get("/khata/{customer_name}")
def customer_khata(customer_name: str, request: Request, limit: int = Query(100, ge=1, le=500)):
    query = {**scope(request), "customer_name": customer_name}
    doc = db_for(request).khata.find_one(query)
    if doc is None:
        raise HTTPException(404, "No khata record found")
    result = public(doc)
    result["entries"] = [public(d) for d in db_for(request).ledger_entries.find(query).sort("date", -1).limit(limit)]
    return result


@router.post("/khata/tx")
def ledger(command: LedgerCommand, request: Request):
    return LedgerService(request.app.state.store, store_id=request.app.state.settings.store_id).apply(command)
