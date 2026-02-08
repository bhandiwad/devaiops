import pytest
from fastapi import HTTPException

from auth.policy import PolicyConfig, PolicyEngine
from auth.rbac import is_dev_auth_enabled, require_platform_admin, require_tenant_access
from models.identity import PrincipalContext


def test_platform_admin_allows_cross_tenant():
    principal = PrincipalContext(
        principal_id="admin",
        realm_roles=["platform_admin"],
        tenant_roles={},
    )
    require_platform_admin(principal)
    require_tenant_access(principal, "tenant-1")


def test_tenant_access_requires_membership():
    principal = PrincipalContext(
        principal_id="user",
        realm_roles=[],
        tenant_roles={"tenant-1": ["tenant_viewer"]},
    )
    require_tenant_access(principal, "tenant-1")
    with pytest.raises(HTTPException):
        require_tenant_access(principal, "tenant-2")


def test_policy_engine_permissions():
    engine = PolicyEngine(
        PolicyConfig(
            permissions={"tenant.read": ["tenant_viewer", "platform_admin"]},
            deny_by_default=True,
        )
    )
    viewer = PrincipalContext(
        principal_id="viewer",
        realm_roles=[],
        tenant_roles={"tenant-1": ["tenant_viewer"]},
    )
    assert engine.has_permission(viewer, "tenant.read", "tenant-1") is True
    assert engine.has_permission(viewer, "tenant.read", "tenant-2") is False


def test_dev_auth_rejected_in_prod(monkeypatch):
    monkeypatch.setenv("DEV_AUTH", "true")
    monkeypatch.setenv("PLATFORM_ENV", "prod")
    monkeypatch.delenv("NON_PROD_MODE", raising=False)
    assert is_dev_auth_enabled() is False


def test_dev_auth_allowed_in_non_prod(monkeypatch):
    monkeypatch.setenv("DEV_AUTH", "true")
    monkeypatch.setenv("PLATFORM_ENV", "dev")
    assert is_dev_auth_enabled() is True
