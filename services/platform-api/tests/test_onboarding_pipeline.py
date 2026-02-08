from pathlib import Path

import pytest

from adapters.interfaces import (
    AppRef,
    BootstrapResult,
    CapabilityReport,
    ClusterAccess,
    ClusterRef,
    ProjectRef,
)
from config.loader import ConfigStore
from config.models import ModuleCatalog, PlatformConfig, ProviderProfile, TenantSpec
from onboarding.pipeline import OnboardingError, OnboardingPipeline


class StubProvisioner:
    def provision(self, tenant_spec, provider_profile):
        return ClusterAccess(kubeconfig="dummy")


class StubCapabilityProbe:
    def __init__(self, capabilities):
        self._capabilities = capabilities

    def probe(self, cluster_access, provider_profile):
        return CapabilityReport(capabilities=self._capabilities)


class StubRegistrar:
    def bootstrap(self, cluster_access, tenant_spec, provider_profile, capability_report):
        return BootstrapResult(status="ok")


class StubGitOps:
    def register_cluster(self, tenant_id, cluster_access, rbac_policy):
        return ClusterRef(cluster_id="cluster-1")

    def ensure_tenant_project(self, tenant_id, project_policy):
        return ProjectRef(project_id="project-1")

    def apply_application(self, app_spec):
        return AppRef(app_id=app_spec["metadata"]["name"])


class StubRegistry:
    def __init__(self, capabilities):
        self._capabilities = capabilities

    def provisioner_default(self):
        return StubProvisioner()

    def capability_probe_default(self):
        return StubCapabilityProbe(self._capabilities)

    def registrar_default(self):
        return StubRegistrar()

    def gitops(self):
        return StubGitOps()


@pytest.fixture()
def kubeconfig_file(tmp_path: Path):
    path = tmp_path / "kubeconfig"
    path.write_text("dummy")
    return path


def _config_store(kubeconfig_path: Path, capability_required=True, adapters=None):
    if adapters is None:
        adapters = {"gitops": "x", "observability": "y", "k8s": "z"}
    platform_config = PlatformConfig.model_validate(
        {
            "modules": {"module_catalog_path": "config/module_catalog.yaml"},
            "identity": {},
            "adapters": adapters,
            "rbac": {},
        }
    )
    module_catalog = ModuleCatalog.model_validate(
        {
            "modules": [
                {
                    "id": "obs.stack",
                    "type": "INSTALL",
                    "scope": "tenant",
                    "requirements": {
                        "adapters": ["gitops"],
                        "capabilities": {"supports_ingress": True} if capability_required else {},
                        "optional": False,
                    },
                    "install": {
                        "values_overrides": {},
                        "argo_application_template": {"metadata": {"name": "obs"}, "spec": {"source": {"helm": {}}}},
                    },
                }
            ]
        }
    )
    provider_profile = ProviderProfile.model_validate(
        {
            "id": "generic",
            "capabilities": {"supports_ingress": True},
        }
    )
    tenant_spec = TenantSpec.model_validate(
        {
            "tenant_id": "tenant-a",
            "mode": "BYOC",
            "provider_profile_id": "generic",
            "k8s_access_ref": {"type": "kubeconfig_file", "reference": str(kubeconfig_path)},
            "git": {"repo_url": "ssh://git.example/acme", "default_branch": "main"},
            "modules": {"enabled": ["obs.stack"]},
        }
    )
    return ConfigStore(
        platform_config=platform_config,
        module_catalog=module_catalog,
        provider_profiles={"generic": provider_profile},
        tenant_specs={"tenant-a": tenant_spec},
    )


def test_onboarding_pipeline_happy_path(kubeconfig_file: Path):
    import os
    os.environ["DEV_AUTH"] = "true"
    config_store = _config_store(kubeconfig_file)
    registry = StubRegistry({"supports_ingress": True})
    pipeline = OnboardingPipeline(config_store, registry, Path("/"))
    result = pipeline.run("tenant-a")
    assert result.status == "READY"


def test_onboarding_pipeline_missing_capability(kubeconfig_file: Path):
    import os
    os.environ["DEV_AUTH"] = "true"
    config_store = _config_store(kubeconfig_file, capability_required=True)
    registry = StubRegistry({"supports_ingress": False})
    pipeline = OnboardingPipeline(config_store, registry, Path("/"))
    with pytest.raises(OnboardingError):
        pipeline.run("tenant-a")


def test_onboarding_pipeline_missing_adapter(kubeconfig_file: Path):
    import os
    os.environ["DEV_AUTH"] = "true"
    config_store = _config_store(kubeconfig_file, adapters={})
    registry = StubRegistry({"supports_ingress": True})
    pipeline = OnboardingPipeline(config_store, registry, Path("/"))
    with pytest.raises(OnboardingError):
        pipeline.run("tenant-a")
