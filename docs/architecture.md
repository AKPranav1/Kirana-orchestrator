# Architecture refinement: first increment

Kirana began as a team hackathon project. This increment makes its existing order workflow independently runnable and gives correctness one owner. The multi-turn assistant is subsequent work.

## Decisions

- Deploy one FastAPI application (`backend.app:app`). Feature routers own HTTP translation; domain modules own validated commands and exact pricing; application services coordinate work; adapters own Mongo and optional delivery.
- Keep the existing dashboard URL paths and legacy Python entry points where practical. The browser submits an order once; it does not coordinate extraction, ledger updates or notifications.
- All prices are computed from explicit catalogue identities and units. Persist integer paise; return rupee values at the compatibility boundary. Reject missing prices, invalid units and non-positive quantities. Allocate residual paise deterministically so shared-basket shares sum to the total.
- Require a Mongo replica set for financial writes. An order, inventory decrement, customer totals, ledger entries, idempotency receipt and notification job commit in one transaction. Reusing a key with different input is a conflict. Never silently fall back to non-transactional writes.
- Reuse a bounded Mongo connection pool per application process. Run blocking database/provider work off the ASGI event loop. Scope application data to the configured store.
- Twilio is optional and delivery runs outside the order transaction. An outbox worker leases jobs with bounded retries. Delivery is at-least-once: a crash after provider acceptance can duplicate a notification, but cannot recreate an order.
- Default to local development, with explicit sample data and no outgoing messages. Production requires an operator API token and explicit allowed origins. This is a single-store operator application, not a public multi-tenant service.

## Boundaries

`backend/domain/`: typed input, money and unit conversion; no network, environment or database calls.

`backend/services/`: pricing/commit orchestration and ledger operations.

`backend/adapters/`: Mongo lifecycle, transaction execution, indexes and notification delivery.

`backend/api/`: order/ledger, catalogue/customer, dashboard, supplier/settings and ingestion routes.

`ingestion/`: existing multilingual normalization, provider extraction and SKU matching. Extraction produces uncommitted order input. It cannot write a ledger.

`db_alerts/` and `webhook/`: compatibility entry points and optional delivery integration; no alternative billing implementation.

## Verification and rollout

Use a fresh database for the sample deployment. Do not point this increment at a teammate's data without a migration/reconciliation review. Preserve legacy order fields for reads, and add exact paise fields to new writes. Unique indexes deliberately refuse ambiguous existing duplicates instead of deleting them.

Regression tests cover grams versus kilograms, negative/unknown input, exact split totals, repeated and conflicting commands, zero stock, rollback and concurrent payments. Mongo integration tests require a disposable replica set. Unit doubles are not evidence of Mongo transaction isolation. Frontend type-check/build and a database-backed workflow smoke test are release checks.

Capacity is unmeasured until the documented benchmark is run. A clean module boundary is not evidence of throughput; report environment, provider stubs, concurrency, failures and latency alongside any measurements.
