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

async def speech_to_text(audio_bytes: bytes) -> Tuple[str, dict]:
    if not SARVAM_API_KEY:
        return "bhaiya 2 kilo aata aur ek doodh ka packet, Rahul ke saath split karo, khate mein daal do", {"mock": True}

    headers = {"api-subscription-key": SARVAM_API_KEY}
    async with httpx.AsyncClient(timeout=30) as client:
        files = {"file": ("audio.ogg", audio_bytes)}
        r = await client.post(SARVAM_STT_URL, headers=headers, files=files)
        r.raise_for_status()
        data = r.json()
        return data.get("transcript", ""), data

def _run_sarvam_vision_sync(image_path: str, api_key: str, handwritten: bool = False, language: str | None = None) -> dict:
    """Synchronous helper to run the official Sarvam SDK.

    Returns a dict with keys: text (string), raw (string repr), confidence (float|None)
    """
    client = SarvamAI(api_subscription_key=api_key)

    kwargs = {"output_format": "md"}
    if language:
        kwargs["language"] = language

    # Try to request a handwriting/document-specific path if requested.
    response = None
    try:
        if handwritten:
            # SDKs vary; attempt a handwritten/document_type kwarg and fall back gracefully
            try:
                response = client.document_digitization.digitize(file_path=image_path, document_type="handwritten", **kwargs)
            except TypeError:
                # SDK doesn't accept document_type; call generic digitize
                response = client.document_digitization.digitize(file_path=image_path, **kwargs)
        else:
            response = client.document_digitization.digitize(file_path=image_path, **kwargs)
    except Exception:
        # Re-raise to allow caller to handle/log
        raise

    # Parse the text blocks from the SDK response
    extracted_text = ""
    confs = []
    for page in getattr(response, "pages", []):
        for block in getattr(page, "blocks", []):
            # Some SDKs return text and optional confidence on blocks
            extracted_text += getattr(block, "text", "") + "\n"
            if hasattr(block, "confidence"):
                try:
                    confs.append(float(getattr(block, "confidence")))
                except Exception:
                    pass

    avg_conf = sum(confs) / len(confs) if confs else None
    # Keep a safe, small string representation of the raw response for debugging
    raw_summary = str(response)[:4000]
    return {"text": extracted_text, "raw": raw_summary, "confidence": avg_conf}

async def vision_ocr(image_bytes: bytes) -> Tuple[str, dict]:
    """Async wrapper for the Sarvam Vision SDK."""
    SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
    if not SARVAM_API_KEY:
        print("[WARNING] Missing Sarvam API Key. Returning mock data.")
        return "2 kilo aata, ek doodh", {"mock": True}

    # The SDK strictly requires a file path, so we save the Twilio bytes temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_img:
        temp_img.write(image_bytes)
        temp_img_path = temp_img.name

    try:
        print("[SARVAM OCR] Processing image via SDK...")

        prefer_hand = SARVAM_VISION_PREFER_HANDWRITING == "1"
        lang = SARVAM_VISION_LANGUAGE if SARVAM_VISION_LANGUAGE else None

        # Try handwriting-first (if configured), falling back to generic digitize
        result = None
        used_model = "document"
        if prefer_hand:
            try:
                result = await asyncio.to_thread(_run_sarvam_vision_sync, temp_img_path, SARVAM_API_KEY, True, lang)
                used_model = "handwritten"
            except Exception as e:
                # If handwriting-specific call fails at SDK level, attempt generic digitize
                print(f"[SARVAM HANDWRITING TRY FAILED] {e}; falling back to generic digitize")

        if result is None or not result.get("text", "").strip():
            # Either we didn't try handwriting or it produced empty text — call generic
            try:
                result = await asyncio.to_thread(_run_sarvam_vision_sync, temp_img_path, SARVAM_API_KEY, False, lang)
                used_model = "document"
            except Exception as e:
                print(f"[SARVAM EXCEPTION] {e}")
                return "", {"error": str(e)}

        extracted_text = result.get("text", "")
        meta = {"status": "success", "model": used_model, "confidence": result.get("confidence"), "raw": result.get("raw")}
        print(f"[SARVAM SUCCESS] Extracted: {extracted_text[:50]}... (model={used_model})")
        return extracted_text, meta

    except Exception as e:
        print(f"[SARVAM EXCEPTION] {e}")
        return "", {"error": str(e)}

    finally:
        # Prevent server storage from filling up with hackathon test images
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
