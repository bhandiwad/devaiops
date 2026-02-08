from __future__ import annotations

from provisioning.terraform_runner import TerraformRunnerProvisionerAdapter


class TerraformProvisionerAdapter(TerraformRunnerProvisionerAdapter):
    """Provisioner adapter entrypoint that reuses the Terraform runner implementation."""
