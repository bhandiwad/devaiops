from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from models.identity import PrincipalContext


@dataclass
class PolicyConfig:
    permissions: Dict[str, List[str]]
    deny_by_default: bool = True


class PolicyEngine:
    def __init__(self, config: PolicyConfig) -> None:
        self._config = config

    def _role_list(self, principal: PrincipalContext, tenant_id: Optional[str]) -> List[str]:
        roles = list(principal.realm_roles)
        if tenant_id:
            roles.extend(principal.tenant_roles.get(tenant_id, []))
        return roles

    def has_permission(self, principal: PrincipalContext, permission: str, tenant_id: Optional[str]) -> bool:
        allowed_roles = self._config.permissions.get(permission)
        if allowed_roles is None:
            return not self._config.deny_by_default
        roles = self._role_list(principal, tenant_id)
        return any(role in allowed_roles for role in roles)
