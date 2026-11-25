"""Single application composition root: uvicorn backend.app:app."""
from contextlib import asynccontextmanager
import hmac
import logging
import time
import httpx
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from starlette.concurrency import run_in_threadpool

from backend.adapters.mongo import MongoStore
from backend.config import Settings
from backend.domain.orders import DomainError

logger = logging.getLogger("kirana.requests")


def create_app(settings: Settings | None = None, *, store=None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application):
        owned = store is None
        application.state.store = store if store is not None else MongoStore(settings)
        try:
            if owned:
                await run_in_threadpool(application.state.store.initialize)
            yield
        finally:
            if owned:
                application.state.store.close()

    application = FastAPI(title="Kirana AI", version="2.0.0", lifespan=lifespan)
    application.state.settings = settings

    @application.middleware("http")
    async def request_boundary(request: Request, call_next):
        request_id, started = uuid4().hex, time.monotonic()
        if request.method != "OPTIONS" and request.url.path not in ("/health", "/webhook") and settings.api_token:
            if not hmac.compare_digest(request.headers.get("X-API-Key", ""), settings.api_token):
                return JSONResponse({"detail": "Operator authentication required"}, status_code=401)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("request id=%s method=%s path=%s status=%s duration_ms=%.1f", request_id, request.method,
                    request.scope.get("route").path if request.scope.get("route") else "unmatched", response.status_code,
                    (time.monotonic() - started) * 1000)
        return response

    @application.exception_handler(DomainError)
    async def domain_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)

    @application.exception_handler(PyMongoError)
    async def database_error(request, exc):
        logger.error("database operation failed type=%s", type(exc).__name__)
        return JSONResponse({"detail": "Database temporarily unavailable; retry with the same request ID"}, status_code=503)

    @application.exception_handler(httpx.HTTPError)
    async def upstream_error(request, exc):
        status = 504 if isinstance(exc, httpx.TimeoutException) else 502
        return JSONResponse({"detail": "Media provider unavailable; retry or use manual entry"}, status_code=status)

    @application.get("/health", tags=["operations"])
    def health():
        return {"status": "ok", "service": "kirana"}

    @application.get("/ready", tags=["operations"])
    def ready(request: Request):
        request.app.state.store.ready()
        return {"status": "ready"}

    from backend.api import catalogue, dashboard, ingestion, operations, orders, webhook
    application.include_router(catalogue.router)
    application.include_router(orders.router)
    application.include_router(dashboard.router)
    application.include_router(operations.router)
    application.include_router(ingestion.router)
    application.include_router(webhook.router)
    # CORS must wrap early authentication/error responses too.
    application.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins,
                               allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type", "X-API-Key", "Idempotency-Key"])
    return application


app = create_app()
