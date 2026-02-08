from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx
import jwt
from jwt import algorithms

from adapters.interfaces import IdentityAdapter
from models.identity import Principal, PrincipalContext


@dataclass
class JWKSCache:
    keys: Dict[str, Any]
    fetched_at: float


class KeycloakIdentityAdapter(IdentityAdapter):
    """Keycloak Identity adapter using JWKS validation."""

    def __init__(self, platform_config=None, client: Optional[httpx.Client] = None) -> None:
        if not platform_config:
            raise RuntimeError("PlatformConfig is required for KeycloakIdentityAdapter")
        self._identity = platform_config.identity or {}
        self._claims = self._identity.get("claims", {})
        self._oidc = self._identity.get("oidc", {})
        self._issuer = self._oidc.get("issuer_url")
        self._audience = self._oidc.get("audience")
        self._jwks_cache_seconds = self._identity.get("jwks_cache_seconds")
        if not self._issuer or not self._audience or not self._jwks_cache_seconds:
            raise RuntimeError("identity.oidc.issuer_url, identity.oidc.audience, and identity.jwks_cache_seconds required")
        self._client = client or httpx.Client(timeout=10.0)
        self._jwks_cache: Optional[JWKSCache] = None

    def _jwks_url(self) -> str:
        if self._oidc.get("jwks_url"):
            return self._oidc["jwks_url"]
        return f"{self._issuer.rstrip('/')}/protocol/openid-connect/certs"

    def _get_jwks(self) -> Dict[str, Any]:
        if self._jwks_cache and (time.time() - self._jwks_cache.fetched_at) < self._jwks_cache_seconds:
            return self._jwks_cache.keys
        response = self._client.get(self._jwks_url())
        if response.status_code >= 400:
            raise RuntimeError(f"Failed to fetch JWKS: {response.status_code}")
        keys = response.json()
        self._jwks_cache = JWKSCache(keys=keys, fetched_at=time.time())
        return keys

    def _get_claim(self, claims: Dict[str, Any], path: str) -> Any:
        current = claims
        for part in path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def verify_token(self, token: str) -> Principal:
        jwks = self._get_jwks()
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key:
            raise RuntimeError("Signing key not found in JWKS")
        signing_key = algorithms.RSAAlgorithm.from_jwk(key)
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=self._audience,
            issuer=self._issuer,
        )
        subject_claim = self._claims.get("subject_claim", "sub")
        email_claim = self._claims.get("email_claim", "email")
        return Principal(
            subject=str(self._get_claim(claims, subject_claim) or claims.get("sub")),
            email=self._get_claim(claims, email_claim),
            raw_claims=claims,
        )

    def get_context(self, principal: Principal) -> PrincipalContext:
        claims = principal.raw_claims
        tenant_roles_claim = self._claims.get("tenant_roles_claim", "tenant_roles")
        realm_roles_claim = self._claims.get("realm_roles_claim", "realm_access.roles")
        tenant_roles = self._get_claim(claims, tenant_roles_claim) or {}
        realm_roles = self._get_claim(claims, realm_roles_claim) or []
        return PrincipalContext(
            principal_id=principal.subject,
            email=principal.email,
            realm_roles=list(realm_roles) if isinstance(realm_roles, list) else [],
            tenant_roles=tenant_roles if isinstance(tenant_roles, dict) else {},
        )
