# Kirana AI

Voice-enabled order extraction and store operations, originally built as a team hackathon project. This repository now uses one FastAPI backend with explicit domain, application and adapter boundaries.

The current refinement focuses on a reproducible order workflow: catalogue-backed pricing, exact shared-basket allocations, transactional inventory/credit updates, replay-safe commands and optional asynchronous receipts. Manual ordering works without speech, LLM or Twilio credentials.

## What works in this increment

- Existing React dashboard for products, customers, sales, credit records and purchasing.
- One backend operation creates a sale, decrements inventory and records any credit.
- Integer-paise pricing with explicit product identities and unit conversion.
- Stable request IDs: retrying a command returns its receipt; changed input conflicts.
- Mongo transactions roll back partial writes. A replica set is required.
- Shared baskets are one sale with allocations that conserve every paise.
- Purchase approval/delivery transitions do not duplicate supplier debt or stock.
- Text/media extraction returns **uncommitted drafts**. Provider failures are explicit.
- Optional signed WhatsApp ingestion reuses persisted extraction on retries.
- Optional outbox delivery is leased and retried separately from order commits.

Multi-turn clarification, conversational confirmation UI and browser voice playback are **not implemented yet**. The API supports recording uploads for transcription; the current browser UI supports manual sales.

## Local setup without your old database or Twilio

Requires Docker Compose, Node.js 22+ and npm.

1. Copy the root environment template to `.env` and `frontend/.env.example` to `frontend/.env.local`.
2. Run the backend and its local Mongo replica set:
   ```sh
   docker compose up --build -d
   docker compose exec api python -m backend.seed
   ```
3. Run the dashboard:
   ```sh
   cd frontend
   npm ci
   npm run dev
   ```

Open [the dashboard](http://localhost:3000) or [the API reference](http://localhost:8000/docs). Create a sale using the fictional catalogue and Demo Customer. Notifications are disabled.

Seeding can be repeated: it inserts missing sample records and does not reset existing stock or balances. The 27 sample products and prices are illustrative, not live commercial data.

The Compose configuration binds both published ports to loopback and uses a single-node replica set. It is a development setup, not a production deployment.

### Python development

Requires Python 3.11+. Run all commands from the repository root.

```sh
python -m venv .venv
# Activate .venv for your shell.
python -m pip install -r requirements-dev.txt
docker compose up -d mongo
python -m backend.seed
uvicorn backend.app:app --host 127.0.0.1 --port 8000 --limit-concurrency 64
```

The root `MONGO_URI` can also point at your own Atlas replica set. No teammate credentials or database export are required. Existing hackathon data needs explicit migration/reconciliation before this version will accept it; use a fresh database for the sample deployment.

The old `db_alerts.main:app`, `ingestion.main:app` and `webhook.main:app` imports alias the same application. Do not run three separate backends.

## Architecture

- `backend/app.py`: configuration, lifecycle, authentication, error handling and router composition.
- `backend/domain/`: validated commands, exact pricing, units, allocations and receipt rendering. No I/O.
- `backend/services/`: orders, ledger operations and purchasing transitions.
- `backend/adapters/`: pooled Mongo lifecycle, transactions, bounded media fetches and leased outbox delivery.
- `backend/api/`: feature routers and compatibility response shapes.
- `ingestion/`: existing Indic-language normalization, model extraction and SKU matching; no financial writes.
- `frontend/src/services/`: shared transport and backend contracts.

Read [architecture decisions and limits](docs/architecture.md) before extending these boundaries.

[Verification results](docs/verification.md) include the database-backed checks, browser smoke test and a narrowly scoped local service benchmark.

### Write contract

`POST /orders` requires a stable `request_id`, customer, payment mode and catalogue items. The server ignores client prices/totals and computes the committed result itself.

```json
{
  "request_id": "example-sale-0001",
  "customer_name": "Demo Customer",
  "payment_mode": "khata",
  "items": [{"product_id": "rice", "qty": 500, "unit": "gm"}]
}
```

With the sample catalogue this charges ₹30, not 500 times the kilogram price. Repeating the same request creates no second order, stock decrement or credit entry. Preserve the request ID when retrying an uncertain network response. A different intended sale needs a new ID.

`POST /khata/tx` uses the same command/receipt pattern. Payments exceeding the outstanding balance are rejected. `POST /process` returns drafts; it does not save them. The old `POST /log` accepts `{"order": <canonical command>}` and delegates to the same order service.

## Optional AI and messaging

Install `requirements-providers.txt` in the Python environment to enable the existing provider adapters, then configure the relevant root environment variables. No provider calls are needed for manual sales or the core tests.

For Docker, set `INSTALL_PROVIDERS=true` in root `.env` and rebuild with `docker compose up --build -d`. Root environment values are supplied to the container; the internal Mongo hostname is intentionally overridden by Compose.

- Gemini/Groq: structured extraction. Credentials and provider availability are required.
- Sarvam: transcription. `POST /transcribe` accepts a recording upload of at most 10 MB.
- Google Vision: image extraction.
- Twilio: incoming `/webhook` requires a valid signature and MessageSid. Configure `TWILIO_WEBHOOK_URL` to the exact external URL when behind a proxy.
- Outgoing receipts: explicitly set `NOTIFICATIONS_ENABLED=true`, configure Twilio and run `python -m backend.worker`.

API and worker must use the same store/database/configuration. Delivery has up to five attempts with expiring leases. It is **at-least-once**: a provider-accepted send followed by a worker crash can duplicate a notification. This cannot recreate a sale. Inspect failed jobs in the database outbox.

With provider dependencies installed in the Docker image, `docker compose run --rm api python -m backend.worker` runs the optional worker using the same configuration.

WhatsApp ingestion retains automatic order submission after extraction; each independent buyer order is atomic, while a multi-buyer batch may partially complete and finish on retry. Conversation-based confirmation is future work. Shared baskets are emitted only once.

`KIRANA_DEMO_MODE=true` explicitly permits deterministic sample speech/OCR and heuristic text extraction during local development. It is never a measured provider result and is prohibited in production mode. Provider failure otherwise returns an actionable error.

The legacy voice debt-reminder adapter remains in `db_alerts/alerts.py`; automatic escalation and the old manual reminder endpoint are not connected to the new financial commit path. They need a separately reviewed scheduling/consent integration.

## Checks

```sh
python -m pytest -q
cd frontend
npm test
npm run lint
npm run build
```

Unit/API tests use an in-memory Mongo-shaped double. Real transaction tests opt in via `KIRANA_TEST_MONGO_URI`, create uniquely named disposable databases and delete only those databases:

```sh
KIRANA_TEST_MONGO_URI='mongodb://localhost:27017/?replicaSet=rs0&directConnection=true' python -m pytest tests/integration -q
```

PowerShell: set `$env:KIRANA_TEST_MONGO_URI` first, then run pytest. CI runs both the backend tests against a real replica set and the frontend checks. Integration coverage includes concurrent replay, rollback and concurrent payment protection.

## Deployment and limits

Production mode requires `KIRANA_ENV=production`, a 32+ character `KIRANA_API_TOKEN`, explicit `ALLOWED_ORIGINS`, demo mode disabled, TLS and an authenticated Mongo deployment. The dashboard asks for the operator key when the backend requires it; it is kept in session storage, never bundled into the JavaScript.

This is a single-store operator application. It does not provide individual user roles, multi-tenant isolation, production backups or a public anonymous demo deployment. Enforce request/upload limits at your reverse proxy. Monetary command receipts currently have no expiry so late retries cannot silently create another sale; retention/migration requires a deliberate policy.

Read endpoints are bounded, and financial command execution has an overall deadline. The default connection pool and concurrency settings are engineering limits, **not a throughput benchmark**. No production-scale capacity claim is made. The bundled forecast artifact is an offline hackathon snapshot, not a live evaluation of the current store's inventory.

The original team implementation and contributions remain in Git history. The refinement preserves that provenance while replacing overlapping billing/write paths.
