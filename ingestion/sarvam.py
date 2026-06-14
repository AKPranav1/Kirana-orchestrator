import os
import httpx
from typing import Tuple
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY    = os.getenv("SARVAM_API_KEY")
SARVAM_STT_URL    = os.getenv("SARVAM_STT_URL",    "https://api.sarvam.ai/speech-to-text")
SARVAM_VISION_URL = os.getenv("SARVAM_VISION_URL", "https://api.sarvam.ai/vision/ocr")

# ---------------------------------------------------------------------------
# Sarvam language code → BCP-47 locale used by the STT API
# https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe
# ---------------------------------------------------------------------------
_LANG_TO_LOCALE: dict[str, str] = {
    "unknown": "unknown",
    "hi": "hi-IN",
    "kn": "kn-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "mr": "mr-IN",
    "gu": "gu-IN",
    "bn": "bn-IN",
    "pa": "pa-IN",
    "ml": "ml-IN",
    "or": "od-IN",
    "en": "en-IN",
}

def _locale(lang_code: str) -> str:
    code = (lang_code or "unknown").lower()
    return _LANG_TO_LOCALE.get(code, "unknown")


async def speech_to_text(
    audio_bytes: bytes,
    language_code: str = "unknown",
) -> Tuple[str, dict]:
    """
    Transcribe audio bytes via Sarvam's Speech-to-Text API (saarika:v2.5).

    Args:
        audio_bytes:   Raw audio content (OGG / OPUS / WAV / MP3 / etc.)
        language_code: 2-letter Sarvam language code (hi / kn / ta / te /
                       mr / gu / bn / pa / ml / or / en).
                       Passed to the API so recognition is language-specific
                       rather than relying on potentially slow auto-detection.

    Returns:
        (transcript_string, raw_api_response_dict)
    """
    if not SARVAM_API_KEY:
        # Deterministic mock for local dev — returns Hinglish test phrase
        return (
            "bhaiya 2 kilo aata aur ek doodh ka packet, "
            "Rahul ke saath split karo, khate mein daal do",
            {"mock": True},
        )

    headers = {"api-subscription-key": SARVAM_API_KEY}
    data    = {
        "language_code": _locale(language_code),
        # "saaras:v2" is not a real model — saarika:v2.5 is the default
        # transcription model and transcribes audio in the spoken language,
        # which is what normalize_text() / gemini.py expect downstream.
        "model": "saarika:v2.5",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        files = {"file": ("audio.ogg", audio_bytes, "audio/ogg")}
        r = await client.post(SARVAM_STT_URL, headers=headers, files=files, data=data)
        if r.status_code >= 400:
            # Surface Sarvam's actual error body for debugging
            raise RuntimeError(f"Sarvam STT {r.status_code}: {r.text[:300]}")
        resp = r.json()
        return resp.get("transcript", ""), resp


async def vision_ocr(
    image_bytes: bytes,
    language_code: str = "unknown",
) -> Tuple[str, dict]:
    """
    Extract text from an image via Sarvam's vision/document OCR.

    Args:
        image_bytes:   Raw image content (JPEG / PNG).
        language_code: 2-letter Sarvam language code — hints the OCR engine
                       toward the expected script for better accuracy on
                       low-resolution or handwritten images.

    Returns:
        (extracted_text_string, raw_api_response_dict)

    NOTE: As of current Sarvam docs, image/document OCR ("Sarvam Vision" /
    Document Intelligence) is an async job-based API (create job -> upload
    file -> trigger processing -> poll status -> download result ZIP),
    not a single synchronous POST with a file like this. The endpoint
    `https://api.sarvam.ai/vision/ocr` used below is likely stale and may
    return 404/400 in production. This mock path keeps text/audio orders
    unblocked; if you hit errors here on a real image order, capture the
    response body and we can wire up the correct async flow.
    """
    if not SARVAM_API_KEY:
        return "2 kilo aata, ek doodh", {"mock": True}

    headers = {"api-subscription-key": SARVAM_API_KEY}
    data    = {"language_code": _locale(language_code)}

    async with httpx.AsyncClient(timeout=30) as client:
        files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
        r = await client.post(SARVAM_VISION_URL, headers=headers, files=files, data=data)
        if r.status_code >= 400:
            raise RuntimeError(f"Sarvam Vision OCR {r.status_code}: {r.text[:300]}")
        resp = r.json()
        return resp.get("text", ""), resp
