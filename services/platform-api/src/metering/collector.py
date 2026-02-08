from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

from adapters.interfaces import ClusterRef
from adapters.registry import AdapterRegistry
from config.loader import ConfigStore
from db.models import MeteringRollup, MeteringSample
from db.repositories import (
    AuditRepository,
    DriftRunRepository,
    ExportBundleRepository,
    MeteringRollupRepository,
    MeteringSampleRepository,
    RunbookExecutionRepository,
)


def _safe_number(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


class MeteringCollector:
    def __init__(
        self,
        config_store: ConfigStore,
        registry: AdapterRegistry,
        sample_repo: MeteringSampleRepository,
        rollup_repo: MeteringRollupRepository,
        audit_repo: AuditRepository,
        drift_repo: DriftRunRepository,
        runbook_repo: RunbookExecutionRepository,
        export_repo: ExportBundleRepository,
    ) -> None:
        self._config_store = config_store
        self._registry = registry
        self._sample_repo = sample_repo
        self._rollup_repo = rollup_repo
        self._audit_repo = audit_repo
        self._drift_repo = drift_repo
        self._runbook_repo = runbook_repo
        self._export_repo = export_repo

    def _collect_k8s(self, tenant_spec: Dict[str, Any]) -> Dict[str, float]:
        services = tenant_spec.get("services") or []
        k8s = self._registry.k8s()
        pod_count = 0
        deploy_count = 0
        cpu_requested = 0.0
        mem_requested = 0.0
        for service in services:
            namespace = service.get("namespace", "default")
            label_selector = service.get("label_selector") or ""
            snapshot = k8s.get_workload_snapshot(
                ClusterRef(cluster_id=tenant_spec["tenant_id"], metadata={}),
                selectors={"namespace": namespace, "label_selector": label_selector},
            )
            for resource in snapshot.resources:
                kind = str(resource.get("kind", "")).lower()
                if kind == "pod":
                    pod_count += 1
                if kind == "deployment":
                    deploy_count += 1
                requests = resource.get("resources", {}).get("requests", {})
                cpu_requested += _safe_number(requests.get("cpu", 0))
                mem_requested += _safe_number(requests.get("memory", 0))
        return {
            "cluster_count": 1.0,
            "pod_count": float(pod_count),
            "deployment_count": float(deploy_count),
            "cpu_requested": cpu_requested,
            "memory_requested": mem_requested,
            "pod_hours_estimate": float(pod_count),  # one-hour sampling window approximation
        }

    async def collect(self, tenant_id: str) -> MeteringSample:
        tenant_spec = self._config_store.get_tenant_spec(tenant_id).model_dump()
        k8s_metrics = self._collect_k8s(tenant_spec)
        audits = await self._audit_repo.list_for_tenant(tenant_id)
        drifts = await self._drift_repo.list_for_tenant(tenant_id)
        runbooks = await self._runbook_repo.list_for_tenant(tenant_id)
        exports = await self._export_repo.list_for_tenant(tenant_id)
        metrics = {
            **k8s_metrics,
            "api_calls": float(len(audits)),
            "drift_runs": float(len(drifts)),
            "runbook_executions": float(len(runbooks)),
            "export_count": float(len(exports)),
            "pr_automation_actions": float(len([e for e in audits if e.action == "incident.create_pr"])),
            "log_query_count": float(len([e for e in audits if "observability" in e.action])),
        }
        sample = MeteringSample(
            sample_id=str(uuid4()),
            tenant_id=tenant_id,
            captured_at=datetime.now(timezone.utc),
            metrics=metrics,
        )
        return await self._sample_repo.create(sample)

    async def rollup(self, tenant_id: str, granularity: str = "daily") -> MeteringRollup | None:
        now = datetime.now(timezone.utc)
        if granularity == "hourly":
            period_start = now - timedelta(hours=1)
        else:
            period_start = now - timedelta(days=1)
        samples = await self._sample_repo.list_for_tenant(tenant_id, captured_from=period_start, captured_to=now)
        if not samples:
            return None
        totals: Dict[str, float] = {}
        for sample in samples:
            for key, value in (sample.metrics or {}).items():
                totals[key] = totals.get(key, 0.0) + _safe_number(value)
        rollup = MeteringRollup(
            rollup_id=str(uuid4()),
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=now,
            granularity=granularity,
            metrics=totals,
        )
        return await self._rollup_repo.create(rollup)
