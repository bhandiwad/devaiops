from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from adapters.interfaces import SecretsAdapter


class VaultSecretsAdapter(SecretsAdapter):
    """Vault secrets adapter with KV and baseline auth/policy management."""

    def __init__(self, platform_config=None) -> None:
        self._vault_addr = os.getenv("VAULT_ADDR")
        self._vault_token = os.getenv("VAULT_TOKEN")
        timeout = float((platform_config.integrations or {}).get("timeout_seconds", 10)) if platform_config else 10.0
        self._timeout = timeout
        if not self._vault_addr or not self._vault_token:
            raise RuntimeError("VAULT_ADDR and VAULT_TOKEN are required")

    def _headers(self) -> Dict[str, str]:
        return {"X-Vault-Token": self._vault_token}

    def _url(self, path: str) -> str:
        return f"{self._vault_addr.rstrip('/')}/v1/{path.lstrip('/')}"

    def _request(self, method: str, path: str, payload: Dict[str, Any] | None = None, allow_404: bool = False) -> httpx.Response:
        response = httpx.request(
            method,
            self._url(path),
            headers=self._headers(),
            json=payload,
            timeout=self._timeout,
        )
        if allow_404 and response.status_code == 404:
            return response
        if response.status_code >= 400:
            raise RuntimeError(f"Vault API failed {response.status_code} on {path}: {response.text}")
        return response

    def ensure_platform_oidc_auth(self, keycloak_config: Dict[str, Any]) -> None:
        # Enable JWT auth if missing.
        auths = self._request("GET", "sys/auth").json()
        if "jwt/" not in auths:
            self._request("POST", "sys/auth/jwt", {"type": "jwt"})
        issuer = keycloak_config.get("issuer_url")
        if not issuer:
            raise RuntimeError("keycloak_config.issuer_url is required")
        self._request(
            "POST",
            "auth/jwt/config",
            {
                "oidc_discovery_url": issuer,
                "bound_issuer": issuer,
                "default_role": "platform-default",
            },
        )

    def ensure_tenant_policies(self, tenant_id: str, role_bindings: Dict[str, Any]) -> None:
        policy_name = role_bindings.get("policy_name") or f"tenant-{tenant_id}"
        capabilities = role_bindings.get("capabilities") or ["read", "list"]
        path_prefix = role_bindings.get("path_prefix") or f"kv/data/tenants/{tenant_id}/*"
        policy_hcl = f'path "{path_prefix}" {{ capabilities = {capabilities} }}'
        self._request("PUT", f"sys/policies/acl/{policy_name}", {"policy": policy_hcl})

    def ensure_workload_auth(self, tenant_id: str, workload_identity: Dict[str, Any], policy_ref: str) -> None:
        auths = self._request("GET", "sys/auth").json()
        if "kubernetes/" not in auths:
            self._request("POST", "sys/auth/kubernetes", {"type": "kubernetes"})
        role_name = workload_identity.get("role_name") or f"{tenant_id}-workload"
        sa_names = workload_identity.get("service_account_names") or ["default"]
        sa_namespaces = workload_identity.get("service_account_namespaces") or [tenant_id]
        payload = {
            "bound_service_account_names": sa_names,
            "bound_service_account_namespaces": sa_namespaces,
            "policies": policy_ref,
            "ttl": workload_identity.get("ttl", "1h"),
        }
        self._request("POST", f"auth/kubernetes/role/{role_name}", payload)

    def audit_configure(self) -> None:
        audit = self._request("GET", "sys/audit", allow_404=True)
        existing = audit.json() if audit.content else {}
        if "file/" in existing:
            return
        # Dev-friendly file sink inside container.
        self._request("PUT", "sys/audit/file", {"type": "file", "options": {"file_path": "/tmp/vault-audit.log"}})

    def read_secret(self, secret_ref: str) -> Dict[str, Any]:
        if not secret_ref.startswith("kv/"):
            raise RuntimeError("Only kv/ paths are supported for Vault KV v2")
        response = self._request("GET", secret_ref)
        payload = response.json() if response.content else {}
        return payload.get("data", {}).get("data", {})

    def write_secret(self, secret_ref: str, payload: Dict[str, Any]) -> None:
        if not secret_ref.startswith("kv/"):
            raise RuntimeError("Only kv/ paths are supported for Vault KV v2")
        self._request("POST", secret_ref, {"data": payload})
