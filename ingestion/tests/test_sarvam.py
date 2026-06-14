import os
import sys
from pathlib import Path
import pytest

# ensure repository root is on path (mirrors other tests in this package)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import ingestion.sarvam as sarvam_module
from ingestion.sarvam import speech_to_text, vision_ocr


def test_speech_to_text_and_vision_mock():
    import asyncio

    # Ensure module-level flag reflects no API key (module captures env at import)
    os.environ.pop("SARVAM_API_KEY", None)
    sarvam_module.SARVAM_API_KEY = None
    async def _run():
        text, meta = await speech_to_text(b"fake-audio-bytes")
        assert isinstance(text, str) and meta.get("mock") is True

        vtext, vmeta = await vision_ocr(b"fake-image-bytes")
        assert isinstance(vtext, str)
        assert vmeta.get("mock") is True

    asyncio.run(_run())
