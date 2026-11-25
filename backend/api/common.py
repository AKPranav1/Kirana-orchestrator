from fastapi import Request
from fastapi.encoders import jsonable_encoder


def db_for(request: Request):
    return request.app.state.store.db


def scope(request: Request):
    return {"store_id": request.app.state.settings.store_id}


def public(doc):
    if doc is None:
        return None
    return jsonable_encoder({k: v for k, v in doc.items() if k != "_id"})


def product_view(doc):
    result = public(doc)
    result["stockQuantity"] = doc.get("stock_milliunits", 0) / 1000
    result["stock_quantity"] = result["stockQuantity"]
    result["unitPrice"] = doc.get("price_paise", 0) / 100
    result["margin"] = round((result["unitPrice"] - doc.get("costPrice", 0)) / result["unitPrice"] * 100, 2) if result["unitPrice"] else 0
    result["status"] = "Out of Stock" if result["stockQuantity"] == 0 else "Low Stock" if result["stockQuantity"] < 5 else "In Stock"
    return result
