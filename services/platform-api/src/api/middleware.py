from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

from db.models import IdempotencyKey
from db.repositories import IdempotencyKeyRepository

REQUEST_COUNTER = Counter(
    "platform_api_requests_total",
    "Platform API request count",
    ["method", "path", "status_code", "tenant_id"],
)
REQUEST_LATENCY = Histogram(
    "platform_api_request_latency_seconds",
    "Platform API request latency",
    ["method", "path", "tenant_id"],
)
RATE_LIMIT_HITS = Counter(
    "platform_api_rate_limit_denied_total",
    "Denied requests by rate limit",
    ["tenant_id"],
)


def _extract_tenant_id(request: Request) -> str:
    path_parts = [part for part in request.url.path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] == "tenants":
        return path_parts[1]
    if len(path_parts) >= 4 and path_parts[0] == "api" and path_parts[1] == "v1" and path_parts[2] == "tenants":
        return path_parts[3]
    return request.headers.get("X-Tenant-Id", "platform")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limits: Dict[str, Any] | None = None):
        super().__init__(app)
        limits = limits or {}
        self._window_seconds = int(limits.get("window_seconds", 60))
        self._max_requests = int(limits.get("max_requests", 120))
        self._buckets: dict[str, list[float]] = {}

    def _sync_config(self, request: Request) -> None:
        try:
            cfg = request.app.state.config_store.platform_config.model_dump()
        except Exception:
            return
        limits = cfg.get("rate_limit") or {}
        self._window_seconds = int(limits.get("window_seconds", self._window_seconds))
        self._max_requests = int(limits.get("max_requests", self._max_requests))

    async def dispatch(self, request: Request, call_next):
        self._sync_config(request)
        principal = getattr(request.state, "principal", None)
        principal_id = getattr(principal, "principal_id", "anonymous")
        tenant_id = _extract_tenant_id(request)
        key = f"{tenant_id}:{principal_id}"
        now = time.time()
        window_start = now - self._window_seconds
        values = [stamp for stamp in self._buckets.get(key, []) if stamp >= window_start]
        if len(values) >= self._max_requests:
            RATE_LIMIT_HITS.labels(tenant_id=tenant_id).inc()
            return JSONResponse(status_code=429, content={"error": {"code": "rate_limit", "message": "Too many requests"}})
        values.append(now)
        self._buckets[key] = values
        return await call_next(request)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, config: Dict[str, Any] | None = None):
        super().__init__(app)
        cfg = config or {}
        self._ttl_seconds = int(cfg.get("ttl_seconds", 3600))
        self._actions = cfg.get(
            "protected_paths",
            [
                "/provision/apply",
                "/provision/destroy",
                "/runbooks/",
                "/exports",
                "/create-pr",
                "/transition",
                "/notify",
                "/create-ticket",
                "/subscriptions",
                "/products/",
                "/promote",
                "/upgrade/apply",
            ],
        )

    def _sync_config(self, request: Request) -> None:
        try:
            cfg = request.app.state.config_store.platform_config.model_dump()
        except Exception:
            return
        idem_cfg = cfg.get("idempotency") or {}
        self._ttl_seconds = int(idem_cfg.get("ttl_seconds", self._ttl_seconds))
        self._actions = idem_cfg.get("protected_paths", self._actions)

    def _protected(self, path: str, method: str) -> bool:
        if method.upper() != "POST":
            return False
        return any(fragment in path for fragment in self._actions)

    async def dispatch(self, request: Request, call_next):
        self._sync_config(request)
        if not self._protected(request.url.path, request.method):
            return await call_next(request)

        idem_key = request.headers.get("Idempotency-Key")
        if not idem_key:
            return JSONResponse(status_code=400, content={"error": {"code": "missing_idempotency_key", "message": "Idempotency-Key required"}})

        body_bytes = await request.body()
        request_hash = hashlib.sha256(
            f"{request.method}:{request.url.path}:".encode("utf-8") + body_bytes
        ).hexdigest()
        tenant_id = _extract_tenant_id(request)
        principal = getattr(getattr(request.state, "principal", None), "principal_id", "anonymous")

        async with request.app.state.db.session_factory() as session:
            repo = IdempotencyKeyRepository(session)
            existing = await repo.get(idem_key)
            now = datetime.now(timezone.utc)
            if existing:
                expires_at = existing.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                is_valid = expires_at > now
            else:
                is_valid = False
            if existing and is_valid:
                if existing.request_hash != request_hash:
                    return JSONResponse(
                        status_code=409,
                        content={"error": {"code": "idempotency_conflict", "message": "Idempotency key reuse with different payload"}},
                    )
                if existing.status == "COMPLETED":
                    return JSONResponse(status_code=200, content=existing.response_json)
                return JSONResponse(status_code=409, content={"error": {"code": "request_in_progress", "message": "Request already in progress"}})

            if not existing:
                await repo.create(
                    IdempotencyKey(
                        idempotency_key=idem_key,
                        tenant_id=tenant_id,
                        principal=principal,
                        action=request.url.path,
                        request_hash=request_hash,
                        response_json={},
                        status="IN_PROGRESS",
                        expires_at=now + timedelta(seconds=self._ttl_seconds),
                    )
                )
            else:
                existing.request_hash = request_hash
                existing.status = "IN_PROGRESS"
                existing.response_json = {}
                existing.expires_at = now + timedelta(seconds=self._ttl_seconds)
                await repo.update(existing)
            await session.commit()

        response = await call_next(request)
        if response.status_code >= 500:
            return response

        payload: Dict[str, Any] = {}
        if isinstance(response, JSONResponse):
            payload = json.loads(response.body.decode("utf-8")) if response.body else {}
        async with request.app.state.db.session_factory() as session:
            repo = IdempotencyKeyRepository(session)
            existing = await repo.get(idem_key)
            if existing:
                existing.status = "COMPLETED"
                existing.response_json = payload
                await repo.update(existing)
                await session.commit()
        return response


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        tenant_id = _extract_tenant_id(request)
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        REQUEST_COUNTER.labels(
            method=request.method,
            path=request.url.path,
            status_code=str(response.status_code),
            tenant_id=tenant_id,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            path=request.url.path,
            tenant_id=tenant_id,
        ).observe(elapsed)
        return response
