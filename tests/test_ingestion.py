from pathlib import Path

import pytest

from backend.domain.orders import DomainError
from ingestion.orchestrator import orders_from_parsed
from ingestion.schema import ParsedOrderPayload
from ingestion.sku_match import SKUMatcher


def test_shared_basket_is_emitted_once_without_authoritative_prices():
    matcher = SKUMatcher(str(Path(__file__).parents[1] / "ingestion/data/sku_catalog.json"))
    parsed = ParsedOrderPayload.model_validate({"payment_intent": "khata", "raw_splits": [
        {"buyer_name": "default", "raw_items": [{"name": "rice", "qty": 2, "unit": "kg"}]},
        {"buyer_name": "B", "raw_items": []}, {"buyer_name": "C", "raw_items": []}]})
    result = orders_from_parsed(parsed, customer_name="Demo", customer_phone="", request_id="extract-0001", matcher=matcher)
    assert len(result) == 1
    assert result[0].items[0].qty == 2
    assert result[0].split_with == ["B", "C"]


def test_missing_providers_fail_explicitly_outside_demo(monkeypatch):
    import asyncio
    from ingestion.gemini import parse_order_text
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(DomainError):
        asyncio.run(parse_order_text("1 kg rice", allow_demo=False))


def test_speech_does_not_invent_a_transcript_without_credentials(monkeypatch):
    import asyncio
    import ingestion.sarvam as speech
    monkeypatch.setattr(speech, "SARVAM_API_KEY", None)
    with pytest.raises(DomainError):
        asyncio.run(speech.speech_to_text(b"fake audio"))
