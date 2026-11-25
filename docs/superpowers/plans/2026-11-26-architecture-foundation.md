# Kirana Architecture Foundation Implementation Plan

> Execute natively in this checkout under the user's explicit authorization to refactor and commit directly. Review the completed change independently before pushing.

**Goal:** Make the existing order workflow consistent, independently runnable and testable without Twilio.

**Architecture:** One FastAPI composition root, thin feature routers, pure validated pricing, transactional Mongo application services and optional outbox delivery. Preserve useful dashboard paths while making order writes pass through one service.

**Tech Stack:** Python 3.11+, FastAPI/Pydantic, PyMongo, Mongo replica set, existing React/TypeScript/Vite frontend.

**Spec:** `docs/architecture.md`

## Global Constraints

- Preserve team history and contribution attribution; implement independently.
- Require transaction-capable Mongo for financial writes; no unsafe fallback.
- Keep external messaging disabled by default and provider mocks explicit.
- Architecture foundation first; multi-turn conversation and browser recording are subsequent work.

## Review Focus

- Shared basket: one sale, exact allocations and no full-basket charge per person.
- Retry/conflicting input: one order and ledger effect, or a conflict.
- Provider outage: committed money survives; no delivery inside a transaction.
- Inventory zero/unit mismatch: accept zero updates, reject insufficient stock or incompatible units.
- Interrupted/multi-worker execution: transaction rollback and durable leased delivery, tested separately from unit doubles.

## Tasks

### 1. Protect and centralize pricing and contracts

Files: `tests/test_pricing.py`, `backend/domain/orders.py`, `backend/domain/pricing.py`, `backend/data/catalogue.json`.

Interface: `price_order(command: OrderCommand, products: list[dict]) -> dict` returns enriched lines, integer totals and exact split shares. `OrderCommand` accepts normalized legacy/manual inputs and a stable request ID. Invalid input raises a domain error before a write.

- [x] Write literal regression cases for 500g rice = 3000 paise, 1kg tea = 28000 paise, incompatible/unknown products and three-way residual allocation.
- [x] Run `python -m pytest tests/test_pricing.py -q` and observe missing behavior.
- [x] Implement validated commands and the pure pricing boundary.
- [x] Run the pricing cases and commit after the dependent integration work is verified.

### 2. Give writes a transaction and retry boundary

Files: `tests/test_orders.py`, `tests/integration/test_mongo.py`, `backend/adapters/mongo.py`, `backend/services/orders.py`, `backend/services/ledger.py`, `backend/adapters/outbox.py`.

Interfaces: `OrderService.submit(command) -> dict`; `LedgerService.apply(command) -> dict`; `MongoStore.transact(callback)` supplies a session-bound unit of work. Outbox jobs use stable IDs and leases.

- [x] Add failing tests for replay/conflict, exact shares, insufficient stock, invalid/over payments and notification-disabled commits.
- [x] Implement one transaction for order, stock, ledger, customer totals, receipt and optional outbox. Use database uniqueness and conditional writes for concurrency.
- [x] Add a real replica-set test proving rollback and concurrent replay; distinguish integration availability from pass/fail.
- [x] Run unit and integration suites before claiming persistence correctness.

### 3. Compose the application and retain dashboard contracts

Files: `tests/test_api.py`, `backend/app.py`, `backend/config.py`, `backend/api/*.py`, `db_alerts/main.py`, `db_alerts/mongo_connector.py`, `ingestion/main.py`, `ingestion/orchestrator.py`, `webhook/main.py`, frontend API services and order modal.

Interfaces: `create_app(settings, store=None) -> FastAPI`; `POST /orders` and legacy `POST /log` call the same order service; `POST /process` remains extraction-only. Existing read/CRUD paths remain usable with normalized frontend response fields.

- [x] Write API contract tests for manual orders, stock zero, customer lookup, optional delivery, health/readiness and production authentication.
- [x] Extract feature routers, remove hardcoded internal HTTP calls/duplicate routes and make frontend ordering one backend operation.
- [x] Keep shared-basket extraction as one basket plus participants. Provider failure must be explicit outside demo mode.
- [x] Run full pytest, frontend type-check and build; resolve failures.

### 4. Make setup and verification reproducible

Files: root environment/dependency files, `compose.yaml`, Dockerfile, `backend/seed.py`, `backend/worker.py`, CI, README and `docs/architecture.md`.

- [x] Provide a fresh replica-set setup and idempotent sample seed without old credentials/data.
- [x] Verify seeding twice, an order/credit/read round trip, rollback and retries against disposable Mongo.
- [x] Document real limitations and deferred features; remove unsupported performance claims.
- [x] Request independent read-only review, fix important findings, run final checks and commit the verified refactor for publication in the existing repository.
