# Architecture foundation verification

Verified on 26 November 2026.

## Automated checks

- A fresh Python 3.11 environment installed only `requirements-dev.txt`: 49 tests passed with a disposable MongoDB 8.0.38 replica set enabled.
- Real Mongo tests exercised concurrent order replay, rollback after an earlier stock change and concurrent payment protection.
- Two frontend request-contract tests passed. TypeScript checking and the Vite production build passed.
- A headless Chromium check exercised operator access and the actual manual credit-sale form against a fresh seeded database: one POST produced one order, one ₹60 credit entry and the expected stock decrement.
- Independent read-only review findings were corrected and covered by regressions.

The dependency-free local unit run skips the three real-Mongo cases unless `KIRANA_TEST_MONGO_URI` is supplied. The recorded full run supplied it; these were not counted as skipped passes.

## Small order-service baseline

Command:

```sh
python -m backend.benchmark --uri '<disposable replica-set URI>' --orders 50 --concurrency 5
```

One local Windows run, Python 3.11.0, MongoDB 8.0.38, single-node replica set:

- 50 unique credit orders, five worker threads, one contended product and customer.
- Zero errors; 1.181 seconds elapsed; 42.32 completed orders/second.
- Per-order p50: 20.63 ms. p95: 550.21 ms.
- Exact final order count, outstanding balance and stock invariants passed.

This measures the application order service plus real database transactions on one development machine. It excludes HTTP, speech recognition, language models, OCR, messaging, user think time and production network latency. It is a reproducible smoke benchmark, not a production SLA or forecast of end-to-end throughput. The benchmark creates and removes only its own uniquely named database.

## Practical limits

Docker Compose syntax was parsed, but Docker was not installed on this development machine. Local integration used the official portable Mongo binary instead; CI exercises the Docker replica-set path.

Live AI/provider quality, WhatsApp delivery and paid-provider concurrency were not exercised. Forecast data remains the existing offline hackathon artifact. Multi-turn clarification and a browser voice-conversation UI are outside this increment.
