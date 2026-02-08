from __future__ import annotations

from adapters.interfaces import ProjectRef, RegistryAdapter, RobotCredentials


class HarborRegistryAdapter(RegistryAdapter):
    """Stub Harbor registry adapter."""

    def ensure_tenant_project(self, tenant_id: str, project_spec) -> ProjectRef:
        raise NotImplementedError("HarborRegistryAdapter.ensure_tenant_project is not implemented")

    def ensure_role_bindings(self, tenant_id: str, role_bindings) -> None:
        raise NotImplementedError("HarborRegistryAdapter.ensure_role_bindings is not implemented")

    def create_robot_account(self, tenant_id: str, scope) -> RobotCredentials:
        raise NotImplementedError("HarborRegistryAdapter.create_robot_account is not implemented")
