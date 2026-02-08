from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class Principal(BaseModel):
    subject: str
    email: str | None = None
    raw_claims: Dict[str, Any] = Field(default_factory=dict)


class PrincipalContext(BaseModel):
    principal_id: str
    email: str | None = None
    realm_roles: List[str] = Field(default_factory=list)
    tenant_roles: Dict[str, List[str]] = Field(default_factory=dict)

    def is_platform_admin(self) -> bool:
        return "platform_admin" in self.realm_roles

    def has_tenant_role(self, tenant_id: str, roles: List[str] | None = None) -> bool:
        if self.is_platform_admin():
            return True
        if tenant_id not in self.tenant_roles:
            return False
        if not roles:
            return True
        tenant_role_set = set(self.tenant_roles.get(tenant_id, []))
        return bool(tenant_role_set.intersection(set(roles)))
