"""Bounded reads and database aggregations; no synthetic business metrics."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Request

from backend.config import ROOT
from .common import db_for, public, scope

router = APIRouter(tags=["dashboard"])


def total(collection, query, field):
    rows = list(collection.aggregate([{"$match": query}, {"$group": {"_id": None, "value": {"$sum": "$" + field}}}]))
    return rows[0]["value"] if rows else 0


@router.get("/dashboard")
def dashboard(request: Request):
    db, query = db_for(request), scope(request)
    local = datetime.now(ZoneInfo("Asia/Kolkata"))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    today = {**query, "created_at": {"$gte": start.astimezone(timezone.utc), "$lt": (start + timedelta(days=1)).astimezone(timezone.utc)}}
    return {"todaysRevenue": total(db.orders, today, "total_paise") / 100,
            "todaysOrdersCount": db.orders.count_documents(today),
            "outstandingKhata": total(db.khata, query, "total_outstanding_paise") / 100,
            "lowStockItemsCount": db.products.count_documents({**query, "stock_milliunits": {"$lt": 5000}}),
            "pendingDeliveriesCount": db.purchase_orders.count_documents({**query, "status": "In Transit"}),
            "pendingSupplierPay": total(db.suppliers, query, "outstanding_balance_paise") / 100,
            "storeHealthScore": None}


@router.get("/analytics")
def analytics(request: Request, timeframe: str = Query("7d", pattern="^(7d|30d)$")):
    db, query = db_for(request), scope(request)
    start = datetime.now(timezone.utc) - timedelta(days=7 if timeframe == "7d" else 30)
    window = {**query, "created_at": {"$gte": start}}
    trends = list(db.orders.aggregate([{"$match": window}, {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at", "timezone": "+05:30"}}, "revenue": {"$sum": "$total_amount"}}}, {"$sort": {"_id": 1}}]))
    categories = list(db.products.aggregate([{"$match": query}, {"$group": {"_id": "$category", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}, {"$limit": 5}]))
    count = db.products.count_documents(query)
    top = list(db.orders.aggregate([{"$match": window}, {"$unwind": "$items"},
        {"$group": {"_id": "$items.name", "revenue": {"$sum": "$items.line_total"}}}, {"$sort": {"revenue": -1}}, {"$limit": 5}]))
    credit = total(db.ledger_entries, {**query, "type": "credit"}, "amount_paise")
    paid = total(db.ledger_entries, {**query, "type": "payment"}, "amount_paise")
    return {"analytics": {"totalRevenue": total(db.orders, window, "total_paise") / 100,
        "totalOrders": db.orders.count_documents(window), "khataRecoveryRate": round(paid / credit * 100, 2) if credit else 0,
        "topProducts": [{"name": d["_id"], "revenue": d["revenue"]} for d in top],
        "categoryDistribution": [{"name": d["_id"] or "Other", "value": round(d["count"] / count * 100, 1)} for d in categories] if count else [],
        "trendData": [{"date": d["_id"], "revenue": d["revenue"]} for d in trends]}}


@lru_cache(maxsize=1)
def forecasts():
    path = ROOT / "db_alerts" / "model_forecasts.pkl"
    if not path.exists():
        return None
    # Only the repository's trusted offline training artifact is loaded.
    import joblib
    try:
        return joblib.load(path)
    except (ImportError, ValueError, OSError) as exc:
        raise HTTPException(503, "Forecast artifact dependencies unavailable; rebuild with the ML environment") from exc


@router.get("/forecast")
def forecast(limit: int = Query(50, ge=1, le=500)):
    data = forecasts()
    if data is None:
        raise HTTPException(503, "Forecast artifact unavailable; run the offline ML training pipeline")
    return data[:limit]


@router.get("/notifications")
def notifications(request: Request, limit: int = Query(100, ge=1, le=500)):
    docs = [public(d) for d in db_for(request).notifications.find(scope(request)).sort("created_at", -1).limit(limit)]
    return {"count": len(docs), "notifications": docs}


@router.post("/notifications/mark-read")
def read_notifications(request: Request):
    db_for(request).notifications.update_many(scope(request), {"$set": {"isRead": True}})
    return {"status": "success"}
