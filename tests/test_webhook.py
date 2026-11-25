import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings


def test_webhook_is_explicitly_unavailable_without_configuration(store, monkeypatch):
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    with TestClient(create_app(Settings(), store=store)) as client:
        assert client.post("/webhook", data={"MessageSid": "SM123456789"}).status_code == 503


def test_signed_webhook_replay_reuses_extraction_and_order(store, monkeypatch):
    from twilio.request_validator import RequestValidator
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("TWILIO_WEBHOOK_URL", "http://testserver/webhook")
    calls = []
    async def extract(body, request):
        calls.append(body.payload)
        return {"drafts": [{"request_id": body.request_id, "customer_name": "Demo", "payment_mode": "cash",
                            "items": [{"product_id": "rice", "qty": 1}]}]}
    monkeypatch.setattr("backend.api.webhook.process", extract)
    form = {"MessageSid": "SM123456789", "From": "whatsapp:+919999999999", "Body": "1 kg rice"}
    signature = RequestValidator("test-token").compute_signature("http://testserver/webhook", form)
    with TestClient(create_app(Settings(), store=store)) as client:
        assert client.post("/webhook", data=form).status_code == 403
        for _ in range(2):
            response = client.post("/webhook", data=form, headers={"X-Twilio-Signature": signature})
            assert response.status_code == 200, response.text
    assert calls == ["1 kg rice"]
    assert store.db.orders.count_documents({}) == 1
