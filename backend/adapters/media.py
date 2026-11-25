"""Bounded Twilio media fetches; never send credentials to arbitrary URLs."""
import os
from urllib.parse import urlparse

import httpx

from backend.domain.orders import DomainError

MAX_MEDIA_BYTES = 10 * 1024 * 1024


def approved_url(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    try:
        port = parsed.port
    except ValueError as exc:
        raise DomainError("Malformed media URL") from exc
    if parsed.scheme != "https" or parsed.username or parsed.password or port not in (None, 443):
        raise DomainError("Only HTTPS Twilio media URLs are accepted")
    if host != "api.twilio.com" and not host.endswith(".twiliocdn.com"):
        raise DomainError("Media host is not an approved Twilio media source")
    return host


async def fetch_media(url):
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
        for _ in range(4):
            host = approved_url(url)
            sid, token = os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")
            auth = (sid, token) if host == "api.twilio.com" and sid and token else None
            async with client.stream("GET", url, auth=auth) as response:
                if response.is_redirect:
                    url = str(response.url.join(response.headers["location"]))
                    continue
                response.raise_for_status()
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_MEDIA_BYTES:
                        raise DomainError("Recording or image exceeds the 10 MB limit", 413)
                    chunks.append(chunk)
                return b"".join(chunks), response.headers.get("content-type", "").split(";")[0]
    raise DomainError("Media redirect limit exceeded")
