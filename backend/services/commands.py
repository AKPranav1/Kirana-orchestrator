"""Stable command fingerprints and receipts, shared by financial writes."""
import hashlib
import json
from decimal import Decimal

from backend.domain.orders import DomainError


def canonical(value):
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, list):
        return [canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    return value


def identity(command, operation: str, store_id: str) -> tuple[str, str]:
    if command.store_id != store_id:
        raise DomainError("This backend serves a different store", 403)
    fingerprint = hashlib.sha256(json.dumps(canonical(command.model_dump()), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    key = hashlib.sha256(f"{store_id}:{operation}:{command.request_id}".encode()).hexdigest()
    return key, fingerprint


def replay(db, key: str, fingerprint: str, session):
    receipt = db.receipts.find_one({"_id": key}, session=session)
    if receipt is None:
        return None
    if receipt["fingerprint"] != fingerprint:
        raise DomainError("Idempotency key was already used with different input", 409)
    return {**receipt["result"], "replayed": True}
