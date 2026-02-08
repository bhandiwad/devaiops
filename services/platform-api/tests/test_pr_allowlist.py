import pytest

from aiops.pr_bot import create_remediation_pr
from config.models import ModuleCatalog, PlatformConfig, ProviderProfile, TenantSpec
from config.loader import ConfigStore


class StubRegistry:
    def git_provider(self):
        raise AssertionError("Should not be called for disallowed fix type")


def test_pr_allowlist_enforced():
    platform_config = PlatformConfig.model_validate(
        {
            "modules": {"module_catalog_path": "config/module_catalog.yaml"},
            "identity": {},
            "adapters": {},
            "rbac": {},
        }
    )
    store = ConfigStore(
        platform_config=platform_config,
        module_catalog=ModuleCatalog.model_validate({"modules": []}),
        provider_profiles={"generic": ProviderProfile.model_validate({"id": "generic", "capabilities": {}})},
        tenant_specs={
            "tenant-a": TenantSpec.model_validate(
                {
                    "tenant_id": "tenant-a",
                    "mode": "BYOC",
                    "provider_profile_id": "generic",
                    "git": {"repo_url": "https://github.com/org/repo", "default_branch": "main"},
                    "remediation_allowlist": ["RESOURCE_TUNE"],
                    "approval_policy": {"low": "auto", "medium": "manual", "high": "manual"},
                }
            )
        },
    )
    proposal = {
        "summary": "",
        "likely_root_cause": "",
        "confidence": 0.5,
        "fix_type": "IMAGE_TAG_FIX",
        "risk_level": "low",
        "validation_steps": [],
        "rollback_plan": "",
    }
    with pytest.raises(RuntimeError):
        create_remediation_pr("tenant-a", "inc-1", proposal, store, StubRegistry())
