from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.responses import JSONResponse
from starlette.requests import Request

from api.middleware import REQUEST_COUNTER, RequestMetricsMiddleware


def _request(app, path: str = "/tenants/t1"):
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "app": app,
    }
    return Request(scope, receive=receive)


@pytest.mark.asyncio
async def test_request_metrics_increment():
    app = SimpleNamespace(state=SimpleNamespace())
    middleware = RequestMetricsMiddleware(app)

    async def call_next(_request):
        return JSONResponse({"ok": True}, status_code=200)

    before = REQUEST_COUNTER.labels(method="GET", path="/tenants/t1", status_code="200", tenant_id="t1")._value.get()
    req = _request(app, "/tenants/t1")
    await middleware.dispatch(req, call_next)
    after = REQUEST_COUNTER.labels(method="GET", path="/tenants/t1", status_code="200", tenant_id="t1")._value.get()
    assert after == before + 1
