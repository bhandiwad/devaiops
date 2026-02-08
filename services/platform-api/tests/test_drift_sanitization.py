from __future__ import annotations

from provisioning.terraform_runner import TerraformRunnerProvisionerAdapter
from config.models import PlatformConfig


def test_terraform_plan_sanitization():
    platform_config = PlatformConfig.model_validate(
        {
            "modules": {"module_catalog_path": "config/module_catalog.yaml"},
            "identity": {},
            "adapters": {},
            "rbac": {},
            "provisioning": {"terraform_binary": "terraform", "terraform_work_dir": "/tmp/aiops-terraform"},
        }
    )
    adapter = TerraformRunnerProvisionerAdapter(platform_config=platform_config)
    plan_json = {
        "resource_changes": [
            {"address": "kubernetes_cluster.main", "change": {"actions": ["create"]}},
            {"address": "kubernetes_node_pool.workers", "change": {"actions": ["update"]}},
            {"address": "kubernetes_cluster.main", "change": {"actions": ["delete"]}},
        ]
    }
    summary = adapter._sanitize_plan(plan_json)  # type: ignore[attr-defined]
    assert summary["add"] == 1
    assert summary["change"] == 1
    assert summary["destroy"] == 1
    assert "resource_changes" not in summary
