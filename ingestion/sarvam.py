import os
import httpx
import tempfile
import asyncio
from typing import Tuple
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_STT_URL = os.getenv("SARVAM_STT_URL", "https://api.sarvam.ai/speech-to-text")
# Optional tuning knobs
SARVAM_VISION_PREFER_HANDWRITING = os.getenv("SARVAM_VISION_PREFER_HANDWRITING", "1")
SARVAM_VISION_LANGUAGE = os.getenv("SARVAM_VISION_LANGUAGE")

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

def _run_sarvam_vision_sync(image_path: str, api_key: str) -> str:
    """Synchronous helper — minimal, proven-working Sarvam SDK call."""
    client = SarvamAI(api_subscription_key=api_key)
    response = client.document_digitization.digitize(
        file_path=image_path,
        language="hi-IN",
        output_format="md",
    )
    print(f"[SARVAM DEBUG] pages count: {len(getattr(response, 'pages', []))}")
    extracted_text = ""
    for page in getattr(response, "pages", []):
        for block in getattr(page, "blocks", []):
            block_text = getattr(block, "text", "")
            print(f"[SARVAM DEBUG] block text: {block_text!r}")
            extracted_text += block_text + "\n"
    return extracted_text

async def vision_ocr(image_bytes: bytes) -> Tuple[str, dict]:
    """Async wrapper for the Sarvam Vision SDK."""
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("[WARNING] Missing Sarvam API Key. Returning mock data.")
        return "2 kilo aata, ek doodh", {"mock": True}

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        print(f"[SARVAM OCR] Processing image, size={len(image_bytes)} bytes")
        extracted_text = await asyncio.to_thread(_run_sarvam_vision_sync, tmp_path, api_key)
        print(f"[SARVAM SUCCESS] Extracted: {extracted_text[:120]!r}")
        return extracted_text, {"status": "success"}
    except Exception as e:
        print(f"[SARVAM EXCEPTION] {e}")
        return "", {"error": str(e)}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)