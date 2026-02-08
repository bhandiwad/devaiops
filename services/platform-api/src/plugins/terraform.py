from __future__ import annotations

from adapters.interfaces import ClusterAccess, ProvisionerAdapter


class TerraformProvisionerAdapter(ProvisionerAdapter):
    """Stub Terraform provisioner adapter."""

    def provision(self, tenant_spec, provider_profile) -> ClusterAccess:
        raise NotImplementedError("TerraformProvisionerAdapter.provision is not implemented")

    def upgrade(self, tenant_id: str, plan) -> ClusterAccess:
        raise NotImplementedError("TerraformProvisionerAdapter.upgrade is not implemented")

    def deprovision(self, tenant_id: str) -> None:
        raise NotImplementedError("TerraformProvisionerAdapter.deprovision is not implemented")
