from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from adapters.interfaces import SecretsAdapter


class VaultSecretsAdapter(SecretsAdapter):
    """Stub Vault secrets adapter."""

    def ensure_platform_oidc_auth(self, keycloak_config) -> None:
        raise NotImplementedError("VaultSecretsAdapter.ensure_platform_oidc_auth is not implemented")

    def ensure_tenant_policies(self, tenant_id: str, role_bindings) -> None:
        raise NotImplementedError("VaultSecretsAdapter.ensure_tenant_policies is not implemented")

    def ensure_workload_auth(self, tenant_id: str, workload_identity, policy_ref: str) -> None:
        raise NotImplementedError("VaultSecretsAdapter.ensure_workload_auth is not implemented")

    def audit_configure(self) -> None:
        raise NotImplementedError("VaultSecretsAdapter.audit_configure is not implemented")

    def read_secret(self, secret_ref: str) -> Dict[str, Any]:
        vault_addr = os.getenv("VAULT_ADDR")
        vault_token = os.getenv("VAULT_TOKEN")
        if not vault_addr or not vault_token:
            raise RuntimeError("VAULT_ADDR and VAULT_TOKEN are required to read secrets")
        if not secret_ref.startswith("kv/"):
            raise RuntimeError("Only kv/ paths are supported for Vault KV v2")
        url = f"{vault_addr.rstrip('/')}/v1/{secret_ref}"
        response = httpx.get(url, headers={"X-Vault-Token": vault_token}, timeout=10.0)
        if response.status_code >= 400:
            raise RuntimeError(f"Vault read failed {response.status_code}: {response.text}")
        payload = response.json()
        return payload.get("data", {}).get("data", {})
