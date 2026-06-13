import os
import httpx
from typing import Tuple, Any

# Lightweight wrappers for Sarvam APIs. If keys missing, return mocked responses.

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_STT_URL = os.getenv("SARVAM_STT_URL", "https://api.sarvam.example/speech-to-text")
SARVAM_VISION_URL = os.getenv("SARVAM_VISION_URL", "https://api.sarvam.example/vision/ocr")


async def speech_to_text(audio_bytes: bytes) -> Tuple[str, dict]:
    if not SARVAM_API_KEY:
        # mock: return a fixed small string for dev
        return "bhaiya 2 kilo aata aur ek doodh ka packet, Rahul ke saath split karo, khate mein daal do", {"mock": True}

    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}"}
    async with httpx.AsyncClient(timeout=30) as client:
        files = {"file": ("audio.ogg", audio_bytes)}
        r = await client.post(SARVAM_STT_URL, headers=headers, files=files)
        r.raise_for_status()
        data = r.json()
        # assume {'text': '...', 'language': 'hi'}
        return data.get("text", ""), data


async def vision_ocr(image_bytes: bytes) -> Tuple[str, dict]:
    if not SARVAM_API_KEY:
        return "2 kilo aata, ek doodh", {"mock": True}

    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}"}
    async with httpx.AsyncClient(timeout=30) as client:
        files = {"file": ("image.jpg", image_bytes)}
        r = await client.post(SARVAM_VISION_URL, headers=headers, files=files)
        r.raise_for_status()
        data = r.json()
        return data.get("text", ""), data
