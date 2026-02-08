from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from adapters.interfaces import AppRef, ClusterRef
from adapters.registry import AdapterRegistry
from aiops.credentials import resolve_k8s_access
from aiops.redaction import redact_payload
from config.loader import ConfigLoader, ConfigStore
from config.validator import SchemaValidator


@dataclass
class EvidenceResult:
    evidence: Dict[str, Any]
    redaction: Dict[str, int]


class EvidenceCollector:
    def __init__(self, config_store: ConfigStore, registry: AdapterRegistry, repo_root: Path) -> None:
        self.config_store = config_store
        self.registry = registry
        self.repo_root = repo_root
        self.validator = SchemaValidator(repo_root / "schemas")

    def _cluster_ref(self, tenant_spec: Dict[str, Any]) -> ClusterRef:
        _, cluster_ref = resolve_k8s_access(tenant_spec, self.registry, self.repo_root)
        return cluster_ref

    def _service_ref(self, tenant_spec: Dict[str, Any], service_id: str | None) -> Dict[str, Any]:
        services = tenant_spec.get("services", [])
        if service_id:
            for svc in services:
                if svc.get("id") == service_id:
                    return svc
        return {}

    def collect(self, tenant_id: str, incident_id: str, alert: Dict[str, Any], service_id: str | None = None) -> EvidenceResult:
        tenant_spec = self.config_store.get_tenant_spec(tenant_id).model_dump()
        cluster_ref = self._cluster_ref(tenant_spec)
        service_ref = self._service_ref(tenant_spec, service_id)
        namespace = service_ref.get("namespace", "default")
        label_selector = service_ref.get("label_selector") or alert.get("label_selector")

        k8s_adapter = self.registry.k8s()
        snapshot = k8s_adapter.get_workload_snapshot(cluster_ref, {"namespace": namespace, "label_selector": label_selector})
        events = k8s_adapter.get_events(cluster_ref, namespace, since=alert.get("since"))

        obs_adapter = self.registry.observability()
        logs = obs_adapter.query_logs(tenant_id, {"query": alert.get("log_query", "{tenant_id=\"%s\"}" % tenant_id)})
        metrics = obs_adapter.query_metrics(tenant_id, {"query": alert.get("metric_query", "up")})

        gitops = {}
        if service_ref.get("gitops_app"):
            gitops_adapter = self.registry.gitops()
            app_status = gitops_adapter.get_application_status(
                app_ref=AppRef(app_id=service_ref.get("gitops_app"))
            )
            gitops = app_status.detail

        evidence = {
            "incident_id": incident_id,
            "tenant_id": tenant_id,
            "alert": alert,
            "k8s": {
                "events": events.entries,
                "snapshot": snapshot.resources,
            },
            "metrics": metrics.series,
            "logs": logs.entries,
            "gitops": gitops,
        }

        redacted, redaction_info = redact_payload(evidence)
        redacted["redaction"] = redaction_info
        self.validator.validate("evidence_pack.schema.json", redacted, self.repo_root / "schemas" / "evidence_pack.schema.json")
        return EvidenceResult(evidence=redacted, redaction=redaction_info)


def build_collector() -> EvidenceCollector:
    loader = ConfigLoader()
    store = loader.load_all()
    registry = AdapterRegistry(store.platform_config)
    return EvidenceCollector(store, registry, loader.repo_root)
