from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.responses import JSONResponse
from starlette.requests import Request

from api.middleware import IdempotencyMiddleware, RateLimitMiddleware
from db.models import Base
from db.session import create_database


def _build_request(app, path: str, method: str, headers: dict[str, str], body: bytes = b"{}") -> Request:
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [(k.lower().encode("utf-8"), v.encode("utf-8")) for k, v in headers.items()],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "app": app,
    }
    return Request(scope, receive=receive)


@pytest.mark.asyncio
async def test_idempotency_replay_returns_stored_response(tmp_path):
    db = create_database(f"sqlite+aiosqlite:///{tmp_path}/idem.db")
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app = SimpleNamespace(
        state=SimpleNamespace(
            db=db,
            config_store=SimpleNamespace(platform_config=SimpleNamespace(model_dump=lambda: {})),
        )
    )
    middleware = IdempotencyMiddleware(app)

    calls = {"count": 0}

    async def call_next(_request):
        calls["count"] += 1
        return JSONResponse({"ok": True, "count": calls["count"]})

    req1 = _build_request(app, "/platform/upgrade/apply", "POST", {"Idempotency-Key": "abc-1"})
    req1.state.principal = SimpleNamespace(principal_id="user-a")
    res1 = await middleware.dispatch(req1, call_next)
    assert res1.status_code == 200
    assert calls["count"] == 1

    req2 = _build_request(app, "/platform/upgrade/apply", "POST", {"Idempotency-Key": "abc-1"})
    req2.state.principal = SimpleNamespace(principal_id="user-a")
    res2 = await middleware.dispatch(req2, call_next)
    assert res2.status_code == 200
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_rate_limit_denies_after_threshold():
    app = SimpleNamespace(state=SimpleNamespace(config_store=SimpleNamespace(platform_config=SimpleNamespace(model_dump=lambda: {}))))
    middleware = RateLimitMiddleware(app, limits={"window_seconds": 60, "max_requests": 1})

    async def call_next(_request):
        return JSONResponse({"ok": True})

    req1 = _build_request(app, "/tenants/t1", "GET", {})
    req1.state.principal = SimpleNamespace(principal_id="u1")
    res1 = await middleware.dispatch(req1, call_next)
    assert res1.status_code == 200

    req2 = _build_request(app, "/tenants/t1", "GET", {})
    req2.state.principal = SimpleNamespace(principal_id="u1")
    res2 = await middleware.dispatch(req2, call_next)
    assert res2.status_code == 429


def test_idempotency_protected_paths_include_beta_side_effects():
    middleware = IdempotencyMiddleware(SimpleNamespace(state=SimpleNamespace()))
    assert middleware._protected("/api/v1/tenants/t1/incidents/i1/transition", "POST") is True
    assert middleware._protected("/api/v1/tenants/t1/incidents/i1/notify", "POST") is True
    assert middleware._protected("/api/v1/tenants/t1/incidents/i1/create-ticket", "POST") is True
    assert middleware._protected("/api/v1/tenants/t1/subscriptions", "POST") is True
