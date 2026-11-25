# Extraction boundary

Run the consolidated backend from the repository root: `uvicorn backend.app:app --port 8000`.

`POST /process` accepts a request_id, payload_type (text/audio/image), payload and customer details. It returns `{drafts, committed: false, demo_mode}`. Text is interpreted by the configured extraction provider; audio/image URLs must be approved HTTPS Twilio media sources.

Extraction does not price an order, contact a second localhost service, fetch a credit balance or write financial data. Review the returned canonical draft and submit it to `POST /orders` with the same request ID to commit. The server prices against the current catalogue.

`POST /transcribe` accepts multipart audio uploads directly, allowing testing without Twilio. Sample results require explicit local demo mode. See the root README for setup and limitations.
