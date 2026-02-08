from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from adapters.interfaces import ClusterAccess
from adapters.registry import AdapterRegistry
from aiops.credentials import resolve_k8s_access
from config.loader import ConfigLoader, ConfigStore
from artifacts.loader import load_artifact_store
from governance.policy_engine import BasePolicyEngine, PolicyContext, load_policy_engine
from modules.engine import ModuleEngine
from models.identity import PrincipalContext


class OnboardingError(Exception):
    pass


@dataclass
class OnboardingResult:
    tenant_id: str
    status: str
    detail: Dict[str, Any]


class OnboardingPipeline:
    def __init__(
        self,
        config_store: ConfigStore,
        registry: AdapterRegistry,
        repo_root: Path,
        policy_engine: BasePolicyEngine | None = None,
    ) -> None:
        self.config_store = config_store
        self.registry = registry
        self.repo_root = repo_root
        self.policy_engine = policy_engine

    def run(self, tenant_id: str, status_callback: Optional[Callable[[str], None]] = None) -> OnboardingResult:
        tenant_spec = self.config_store.get_tenant_spec(tenant_id).model_dump()
        provider_profile = self.config_store.get_provider_profile(tenant_spec["provider_profile_id"]).model_dump()

        if tenant_spec["mode"] == "PROVISIONED":
            if status_callback:
                status_callback("PROVISIONING")
            cluster_access = self.registry.provisioner_default().provision(tenant_spec, provider_profile)
            if status_callback:
                status_callback("BOOTSTRAPPING")
        elif tenant_spec["mode"] == "BYOC":
            if status_callback:
                status_callback("BOOTSTRAPPING")
            cluster_access, _ = resolve_k8s_access(tenant_spec, self.registry, self.repo_root)
        else:
            raise OnboardingError(f"Unsupported tenant mode: {tenant_spec['mode']}")

        capability_report = self.registry.capability_probe_default().probe(cluster_access, provider_profile)

        module_engine = ModuleEngine(
            module_catalog=self.config_store.module_catalog.model_dump(),
            platform_adapters=self.config_store.platform_config.adapters,
        )
        plan = module_engine.plan(tenant_spec, provider_profile, capability_report.__dict__, tenant_id=tenant_id)
        if plan.errors:
            raise OnboardingError("; ".join(plan.errors))

        self.registry.registrar_default().bootstrap(
            cluster_access, tenant_spec, provider_profile, capability_report
        )

        gitops = self.registry.gitops()
        gitops.register_cluster(tenant_id, cluster_access, self.config_store.platform_config.rbac)
        gitops.ensure_tenant_project(tenant_id, {"tenant_id": tenant_id})

        system_principal = PrincipalContext(
            principal_id="system",
            realm_roles=["platform_admin"],
            tenant_roles={tenant_id: ["tenant_admin"]},
        )
        integration_refs: Dict[str, Any] = {}
        for item in plan.items:
            if item.action == "install" and item.app_spec:
                if self.policy_engine:
                    decision = self.policy_engine.evaluate(
                        PolicyContext(
                            action="module.install",
                            principal=system_principal,
                            tenant_id=tenant_id,
                            payload={"module_id": item.module_id},
                            request_meta={},
                        )
                    )
                    if not decision.allow:
                        raise OnboardingError(f"Policy denied module install: {decision.reasons}")
                gitops.apply_application(item.app_spec)
            elif item.action == "integrate" and item.integration_ref:
                if self.policy_engine:
                    decision = self.policy_engine.evaluate(
                        PolicyContext(
                            action="module.integrate",
                            principal=system_principal,
                            tenant_id=tenant_id,
                            payload={"module_id": item.module_id},
                            request_meta={},
                        )
                    )
                    if not decision.allow:
                        raise OnboardingError(f"Policy denied module integrate: {decision.reasons}")
                integration_refs[item.module_id] = item.integration_ref

        return OnboardingResult(tenant_id=tenant_id, status="READY", detail={"integrations": integration_refs})


def build_pipeline() -> OnboardingPipeline:
    loader = ConfigLoader()
    config_store = loader.load_all()
    artifact_store = load_artifact_store(
        config_store.platform_config.model_dump() if hasattr(config_store.platform_config, "model_dump") else {}
    )
    registry = AdapterRegistry(config_store.platform_config, artifact_store=artifact_store)
    policy_engine = load_policy_engine(
        config_store.platform_config.model_dump() if hasattr(config_store.platform_config, "model_dump") else {},
        loader.repo_root,
    )
    return OnboardingPipeline(config_store, registry, loader.repo_root, policy_engine=policy_engine)
