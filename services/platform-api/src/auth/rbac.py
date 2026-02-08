from __future__ import annotations

import json
import os
from typing import Callable
from uuid import uuid4

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from adapters.registry import AdapterRegistry
from auth.policy import PolicyEngine
from models.identity import Principal, PrincipalContext


def is_dev_auth_enabled() -> bool:
    if os.getenv("DEV_AUTH", "false").lower() != "true":
        return False
    platform_env = os.getenv("PLATFORM_ENV", "dev").lower()
    non_prod = os.getenv("NON_PROD_MODE", "false").lower() == "true" or platform_env in {
        "dev",
        "stage",
        "staging",
        "test",
        "local",
    }
    return non_prod


def parse_dev_principal(header_value: str) -> PrincipalContext:
    try:
        payload = json.loads(header_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid X-Dev-Principal JSON") from exc
    return PrincipalContext.model_validate(payload)


def extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return auth_header.split(" ", 1)[1].strip()


def resolve_principal_context(request: Request, registry: AdapterRegistry) -> PrincipalContext:
    if is_dev_auth_enabled():
        dev_header = request.headers.get("X-Dev-Principal")
        if not dev_header:
            raise HTTPException(status_code=401, detail="Missing X-Dev-Principal header")
        return parse_dev_principal(dev_header)

    token = extract_bearer_token(request)
    identity_adapter = registry.identity()
    principal: Principal = identity_adapter.verify_token(token)
    return identity_adapter.get_context(principal)


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, registry_provider: Callable[[], AdapterRegistry]):
        super().__init__(app)
        self._registry_provider = registry_provider

    async def dispatch(self, request: Request, call_next):
        request.state.correlation_id = request.headers.get("X-Correlation-Id") or str(uuid4())
        try:
            registry = self._registry_provider()
            request.state.principal = resolve_principal_context(request, registry)
            request.state.auth_error = None
        except HTTPException as exc:
            request.state.principal = None
            request.state.auth_error = exc
        return await call_next(request)


def require_principal(request: Request) -> PrincipalContext:
    if getattr(request.state, "principal", None):
        return request.state.principal
    auth_error = getattr(request.state, "auth_error", None)
    if auth_error:
        raise auth_error
    raise HTTPException(status_code=401, detail="Unauthorized")


def require_platform_admin(principal: PrincipalContext) -> None:
    if not principal.is_platform_admin():
        raise HTTPException(status_code=403, detail="Platform admin role required")


def require_tenant_access(principal: PrincipalContext, tenant_id: str) -> None:
    if not principal.has_tenant_role(tenant_id):
        raise HTTPException(status_code=403, detail="Tenant access required")


def require_permission(request: Request, principal: PrincipalContext, permission: str, tenant_id: str | None = None) -> None:
    engine: PolicyEngine = request.app.state.policy_engine
    if not engine.has_permission(principal, permission, tenant_id):
        raise HTTPException(status_code=403, detail="Permission denied")
