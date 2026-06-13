Kirana AI — Ingestion Service (Person 2)

This microservice implements the `/process` endpoint used by Person 1's FastAPI router. It accepts a POST with JSON `{payload_type, payload}` where payload_type is one of `text|audio|image` and payload is either raw text or a media URL (Twilio Media URL).

Behavior summary:
- Converts audio via Sarvam Saaras STT (if SARVAM_API_KEY provided) or uses a deterministic mock.
- Converts image via Sarvam Vision OCR (if SARVAM_API_KEY provided) or mock.
- Normalizes Hinglish/Hindi numerals and units into a canonical text string.
- Calls Gemini (if GEMINI_API_KEY provided) to extract structured JSON; otherwise uses a heuristic mock.
- Fuzzy-matches item names against `data/sku_catalog.json` using rapidfuzz.
- Returns an Order JSON matching the agreed schema (unit_price is always null here).

Env vars
- SARVAM_API_KEY (optional for dev)
- GEMINI_API_KEY (optional for dev)
- GEMINI_URL (optional)
- DEBUG (set to any value to include debug fields in response)

Run (dev)
1. python -m pip install -r requirements.txt
2. uvicorn main:app --reload --port 8001

Example request (text):
curl -X POST "http://localhost:8001/process" -H "Content-Type: application/json" -d '{"payload_type":"text","payload":"2 kilo aata aur ek doodh ke packet, Rahul ke saath split karna hai, khate mein daal do"}'
