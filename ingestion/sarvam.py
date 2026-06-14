import os
import httpx
import tempfile
import asyncio
from typing import Tuple
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_STT_URL = os.getenv("SARVAM_STT_URL", "https://api.sarvam.ai/speech-to-text")

# ---------------------------------------------------------------------------
# Sarvam language code → BCP-47 locale used by the STT API
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


# ---------------------------------------------------------------------------
# STT — unchanged
# ---------------------------------------------------------------------------
async def speech_to_text(
    audio_bytes: bytes,
    language_code: str = "unknown",
) -> Tuple[str, dict]:
    if not SARVAM_API_KEY:
        return (
            "bhaiya 2 kilo aata aur ek doodh ka packet, "
            "Rahul ke saath split karo, khate mein daal do",
            {"mock": True},
        )

    headers = {"api-subscription-key": SARVAM_API_KEY}
    data = {
        "language_code": _locale(language_code),
        "model": "saarika:v2.5",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        files = {"file": ("audio.ogg", audio_bytes, "audio/ogg")}
        r = await client.post(SARVAM_STT_URL, headers=headers, files=files, data=data)
        if r.status_code >= 400:
            raise RuntimeError(f"Sarvam STT {r.status_code}: {r.text[:300]}")
        resp = r.json()
        return resp.get("transcript", ""), resp


# ---------------------------------------------------------------------------
# OCR — Google Cloud Vision
# ---------------------------------------------------------------------------
def _run_gcv_ocr_sync(image_bytes: bytes) -> str:
    import base64, json, urllib.request

    # Always use REST if no service account credentials
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("Set GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS in .env")

        b64 = base64.b64encode(image_bytes).decode()
        payload = json.dumps({
            "requests": [{
                "image": {"content": b64},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
            }]
        }).encode()

        url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())

        try:
            text = result["responses"][0]["fullTextAnnotation"]["text"]
        except (KeyError, IndexError):
            text = ""
        print(f"[GCV OCR] REST extracted {len(text)} chars")
        return text

    # SDK path (only if service account is available)
    from google.cloud import vision
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)
    if response.error.message:
        raise RuntimeError(f"GCV error: {response.error.message}")
    text = response.full_text_annotation.text or ""
    print(f"[GCV OCR] SDK extracted {len(text)} chars")
    return text

async def vision_ocr(image_bytes: bytes) -> Tuple[str, dict]:
    """Async wrapper for GCV OCR. Falls back to mock if no credentials."""
    has_sdk_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    has_api_key   = os.getenv("GOOGLE_API_KEY")

    if not has_sdk_creds and not has_api_key:
        print("[WARNING] No GCV credentials. Returning mock OCR data.")
        return "2 kilo aata, ek doodh", {"mock": True}

    try:
        print(f"[GCV OCR] Processing image, size={len(image_bytes)} bytes")
        extracted_text = await asyncio.to_thread(_run_gcv_ocr_sync, image_bytes)
        print(f"[GCV OCR] Extracted: {extracted_text[:120]!r}")
        return extracted_text, {"status": "success", "engine": "gcv"}
    except Exception as e:
        print(f"[GCV OCR] Exception: {e}")
        return "", {"error": str(e), "engine": "gcv"}