import asyncio
import httpx
import pytest
from pymongo.errors import AutoReconnect

from backend.domain.orders import DomainError


@pytest.mark.parametrize("failure", ["rejection", "timeout"])
def test_speech_provider_failure_is_sanitized_and_actionable(monkeypatch, failure):
    import ingestion.sarvam as speech
    original = httpx.AsyncClient
    def upstream(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("provider internal detail", request=request)
        return httpx.Response(429, text="private provider body", request=request)
    monkeypatch.setattr(speech, "SARVAM_API_KEY", "test")
    monkeypatch.setattr(speech.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(upstream)))
    with pytest.raises(DomainError) as exc:
        asyncio.run(speech.speech_to_text(b"recording"))
    assert exc.value.status_code in (502, 504)
    assert "private" not in str(exc.value)


def test_worker_database_outage_requests_backoff_instead_of_termination():
    from backend.worker import iteration
    class Disconnected:
        def run_once(self):
            raise AutoReconnect("transient connection failure")
    assert iteration(Disconnected()) == 5
