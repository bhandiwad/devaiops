from __future__ import annotations

from aiops.pr_bot import create_remediation_pr
from config.models import ModuleCatalog, PlatformConfig, ProviderProfile, TenantSpec
from config.loader import ConfigStore
from adapters.interfaces import PRChecks, PRRef, RepoRef


class StubGitProvider:
    def create_pull_request(self, repo_ref: RepoRef, branch: str, title: str, body: str, changes):
        return PRRef(pr_url="https://example/pr/1", metadata={"number": 1, "repo_url": repo_ref.repo_url})

    def add_labels(self, pr_ref: PRRef, labels):
        return None

    def get_pull_request_checks(self, pr_ref: PRRef) -> PRChecks:
        return PRChecks(status="pending", checks=[{"context": "ci/lint", "state": "success"}])


class StubRegistry:
    def git_provider(self):
        return StubGitProvider()


def test_required_checks_mark_pending():
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
        "fix_type": "RESOURCE_TUNE",
        "risk_level": "low",
        "validation_steps": [],
        "rollback_plan": "",
    }
    result = create_remediation_pr("tenant-a", "inc-1", proposal, store, StubRegistry(), required_checks=["ci/lint", "ci/test"])
    assert result.status == "pending_checks"
