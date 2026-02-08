from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from adapters.registry import AdapterRegistry
from adapters.interfaces import AppRef
from config.loader import ConfigStore
from provisioning.terraform_runner import TerraformRunnerProvisionerAdapter


@dataclass
class DriftResult:
    detector_type: str
    status: str
    summary: Dict[str, Any]


class DriftDetector:
    def detect(self, tenant_id: str) -> DriftResult:
        raise NotImplementedError


class TerraformDriftDetector(DriftDetector):
    def __init__(self, config_store: ConfigStore, registry: AdapterRegistry) -> None:
        self._config_store = config_store
        self._registry = registry

    def detect(self, tenant_id: str) -> DriftResult:
        tenant_spec = self._config_store.get_tenant_spec(tenant_id).model_dump()
        if tenant_spec.get("mode") != "PROVISIONED":
            return DriftResult(detector_type="terraform", status="skipped", summary={"reason": "not_provisioned"})
        provisioner = self._registry.provisioner_default()
        if not isinstance(provisioner, TerraformRunnerProvisionerAdapter):
            raise RuntimeError("TerraformDriftDetector requires TerraformRunnerProvisionerAdapter")
        summary = provisioner.plan_drift(tenant_spec)
        status = "drift" if summary.get("exit_code") == 2 else "clean"
        return DriftResult(detector_type="terraform", status=status, summary=summary)


class ArgoCDDriftDetector(DriftDetector):
    def __init__(self, config_store: ConfigStore, registry: AdapterRegistry) -> None:
        self._config_store = config_store
        self._registry = registry

    def detect(self, tenant_id: str) -> DriftResult:
        tenant_spec = self._config_store.get_tenant_spec(tenant_id).model_dump()
        gitops = self._registry.gitops()
        services = tenant_spec.get("services") or []
        summary: List[Dict[str, Any]] = []
        drifted = False
        for service in services:
            app_id = service.get("gitops_app")
            if not app_id:
                continue
            status = gitops.get_application_status(app_ref=AppRef(app_id=app_id))
            detail = status.detail or {}
            sync = detail.get("status", {}).get("sync", {}).get("status", "unknown")
            health = detail.get("status", {}).get("health", {}).get("status", "unknown")
            if sync.lower() != "synced":
                drifted = True
            summary.append(
                {
                    "app": app_id,
                    "sync_status": sync,
                    "health_status": health,
                }
            )
        return DriftResult(
            detector_type="argocd",
            status="drift" if drifted else "clean",
            summary={"apps": summary},
        )


class PostureDriftDetector(DriftDetector):
    def __init__(self, config_store: ConfigStore) -> None:
        self._config_store = config_store

    def detect(self, tenant_id: str) -> DriftResult:
        tenant_spec = self._config_store.get_tenant_spec(tenant_id).model_dump()
        required = set((tenant_spec.get("policies") or {}).get("allowed_modules") or [])
        enabled = set((tenant_spec.get("modules") or {}).get("enabled") or [])
        missing = list(required - enabled)
        status = "drift" if missing else "clean"
        return DriftResult(
            detector_type="posture",
            status=status,
            summary={"missing_modules": missing},
        )
