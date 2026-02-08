from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from adapters.interfaces import DashboardList, LogResult, MetricResult, ObservabilityAdapter, ObservabilitySummary


@dataclass
class ObservabilityConfig:
    prometheus_base_url: str
    loki_base_url: str
    tenant_label: str


class LokiPromObservabilityAdapter(ObservabilityAdapter):
    """Minimal Loki + Prometheus adapter enforcing tenant scoping."""

    def __init__(self, platform_config=None, client: Optional[httpx.Client] = None) -> None:
        self._config = self._load_config(platform_config)
        self._client = client or httpx.Client(timeout=20.0)

    def _load_config(self, platform_config) -> ObservabilityConfig:
        prometheus_base_url = os.getenv("PROMETHEUS_BASE_URL")
        loki_base_url = os.getenv("LOKI_BASE_URL")
        tenant_label = None
        if platform_config:
            obs_cfg = platform_config.observability or {}
            prometheus_base_url = prometheus_base_url or obs_cfg.get("prometheus_base_url")
            loki_base_url = loki_base_url or obs_cfg.get("loki_base_url")
            tenant_label = obs_cfg.get("tenant_label")
        if not prometheus_base_url or not loki_base_url:
            raise RuntimeError("Observability endpoints missing (PROMETHEUS_BASE_URL / LOKI_BASE_URL)")
        if not tenant_label:
            raise RuntimeError("observability.tenant_label is required")
        return ObservabilityConfig(prometheus_base_url, loki_base_url, tenant_label)

    def _inject_tenant_label(self, query: str, tenant_id: str) -> str:
        label = self._config.tenant_label
        existing = re.search(rf'{label}\s*=\s*"([^"]+)"', query)
        if existing:
            if existing.group(1) != tenant_id:
                raise RuntimeError("Query tenant label does not match tenant_id")
            return query
        if "{" in query and "}" in query:
            return re.sub(r"\{", f"{{{label}=\"{tenant_id}\",", query, count=1)
        return f"{query}{{{label}=\"{tenant_id}\"}}"

    def query_logs(self, tenant_id: str, query_spec: Dict[str, Any]) -> LogResult:
        query = query_spec.get("query")
        if not query:
            raise RuntimeError("query_spec.query is required")
        query = self._inject_tenant_label(query, tenant_id)
        params = {
            "query": query,
            "limit": query_spec.get("limit", 100),
        }
        if query_spec.get("start"):
            params["start"] = query_spec["start"]
        if query_spec.get("end"):
            params["end"] = query_spec["end"]
        response = self._client.get(f"{self._config.loki_base_url}/loki/api/v1/query_range", params=params)
        if response.status_code >= 400:
            raise RuntimeError(f"Loki query error {response.status_code}: {response.text}")
        data = response.json()
        return LogResult(entries=data)

    def query_metrics(self, tenant_id: str, query_spec: Dict[str, Any]) -> MetricResult:
        query = query_spec.get("query")
        if not query:
            raise RuntimeError("query_spec.query is required")
        query = self._inject_tenant_label(query, tenant_id)
        params = {"query": query}
        response = self._client.get(f"{self._config.prometheus_base_url}/api/v1/query", params=params)
        if response.status_code >= 400:
            raise RuntimeError(f"Prometheus query error {response.status_code}: {response.text}")
        data = response.json()
        return MetricResult(series=data)

    def list_dashboards(self, tenant_id: str) -> DashboardList:
        return DashboardList(dashboards=[])

    def summary(self, service_ref: Dict[str, Any]) -> ObservabilitySummary:
        tenant_id = service_ref.get("tenant_id")
        if not tenant_id:
            raise RuntimeError("service_ref.tenant_id is required")
        label_selector = service_ref.get("label_selector")
        if not label_selector:
            raise RuntimeError("service_ref.label_selector is required")
        selector = self._inject_tenant_label(label_selector, tenant_id)
        cpu_query = f"sum(rate(container_cpu_usage_seconds_total{selector}[5m]))"
        mem_query = f"sum(container_memory_working_set_bytes{selector})"
        restarts_query = f"sum(kube_pod_container_status_restarts_total{selector})"
        cpu = self.query_metrics(tenant_id, {"query": cpu_query}).series
        mem = self.query_metrics(tenant_id, {"query": mem_query}).series
        restarts = self.query_metrics(tenant_id, {"query": restarts_query}).series
        return ObservabilitySummary(
            summary={
                "cpu": cpu,
                "memory": mem,
                "restarts": restarts,
            }
        )
