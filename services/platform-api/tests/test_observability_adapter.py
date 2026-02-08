import httpx
import pytest

from config.models import PlatformConfig
from plugins.observability import LokiPromObservabilityAdapter


def test_observability_injects_tenant_label():
    seen = {"prom": None, "loki": None}

    def handler(request: httpx.Request):
        if request.url.host == "prom":
            seen["prom"] = request.url
            return httpx.Response(200, json={"status": "success", "data": {"result": []}})
        seen["loki"] = request.url
        return httpx.Response(200, json={"status": "success", "data": {"result": []}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    platform_config = PlatformConfig.model_validate(
        {
            "modules": {"module_catalog_path": "config/module_catalog.yaml"},
            "identity": {},
            "adapters": {},
            "rbac": {},
            "observability": {
                "prometheus_base_url": "http://prom",
                "loki_base_url": "http://loki",
                "tenant_label": "tenant_id",
            },
        }
    )
    adapter = LokiPromObservabilityAdapter(platform_config=platform_config, client=client)
    adapter.query_metrics("tenant-a", {"query": "up"})
    adapter.query_logs("tenant-a", {"query": "{app=\"demo\"}"})

    assert seen["prom"] is not None
    assert "tenant_id%3D%22tenant-a%22" in str(seen["prom"])
    assert seen["loki"] is not None
    assert "tenant_id%3D%22tenant-a%22" in str(seen["loki"])


def test_observability_rejects_mismatched_tenant_label():
    platform_config = PlatformConfig.model_validate(
        {
            "modules": {"module_catalog_path": "config/module_catalog.yaml"},
            "identity": {},
            "adapters": {},
            "rbac": {},
            "observability": {
                "prometheus_base_url": "http://prom",
                "loki_base_url": "http://loki",
                "tenant_label": "tenant_id",
            },
        }
    )
    adapter = LokiPromObservabilityAdapter(
        platform_config=platform_config,
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))),
    )
    with pytest.raises(RuntimeError):
        adapter.query_metrics("tenant-a", {"query": "up{tenant_id=\"tenant-b\"}"})
