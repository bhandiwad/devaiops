from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict
import inspect
import time

from opentelemetry import trace
from prometheus_client import Counter, Histogram

from adapters.loader import load_object
from config.models import PlatformConfig


ADAPTER_CALL_COUNTER = Counter(
    "platform_adapter_calls_total",
    "Adapter calls by adapter and operation",
    ["adapter_type", "operation", "outcome"],
)
ADAPTER_CALL_LATENCY = Histogram(
    "platform_adapter_call_latency_seconds",
    "Adapter call latency",
    ["adapter_type", "operation"],
)


class _InstrumentedAdapterProxy:
    def __init__(self, adapter_type: str, obj: Any) -> None:
        self._adapter_type = adapter_type
        self._obj = obj
        self._tracer = trace.get_tracer("platform-api.adapters")

    def __getattr__(self, item):
        attr = getattr(self._obj, item)
        if not callable(attr):
            return attr

        def wrapped(*args, **kwargs):
            start = time.perf_counter()
            with self._tracer.start_as_current_span(f"adapter.{self._adapter_type}.{item}"):
                try:
                    result = attr(*args, **kwargs)
                    ADAPTER_CALL_COUNTER.labels(
                        adapter_type=self._adapter_type,
                        operation=item,
                        outcome="success",
                    ).inc()
                    return result
                except Exception:
                    ADAPTER_CALL_COUNTER.labels(
                        adapter_type=self._adapter_type,
                        operation=item,
                        outcome="error",
                    ).inc()
                    raise
                finally:
                    ADAPTER_CALL_LATENCY.labels(adapter_type=self._adapter_type, operation=item).observe(
                        time.perf_counter() - start
                    )

        return wrapped


@dataclass
class AdapterRegistry:
    platform_config: PlatformConfig
    artifact_store: Any | None = None
    _instances: Dict[str, Any] = field(default_factory=dict)

    def _get_adapter(self, key: str) -> Any:
        if key in self._instances:
            return self._instances[key]
        adapters = self.platform_config.adapters
        if key not in adapters:
            raise KeyError(f"Adapter '{key}' not configured")
        adapter_path = adapters[key]
        adapter_cls = load_object(adapter_path)
        instance = self._construct(adapter_cls)
        instance = _InstrumentedAdapterProxy(key, instance)
        self._instances[key] = instance
        return instance

    def _construct(self, adapter_cls):
        try:
            signature = inspect.signature(adapter_cls)
        except (TypeError, ValueError):
            return adapter_cls()
        params = signature.parameters
        if "platform_config" in params:
            if "artifact_store" in params:
                return adapter_cls(platform_config=self.platform_config, artifact_store=self.artifact_store)
            return adapter_cls(platform_config=self.platform_config)
        if "config" in params:
            return adapter_cls(config=self.platform_config)
        if "artifact_store" in params:
            return adapter_cls(artifact_store=self.artifact_store)
        return adapter_cls()

    def identity(self):
        return self._get_adapter("identity")

    def provisioner_default(self):
        return self._get_adapter("provisioner_default")

    def capability_probe_default(self):
        return self._get_adapter("capability_probe_default")

    def registrar_default(self):
        return self._get_adapter("registrar_default")

    def gitops(self):
        return self._get_adapter("gitops")

    def secrets(self):
        return self._get_adapter("secrets")

    def registry(self):
        return self._get_adapter("registry")

    def observability(self):
        return self._get_adapter("observability")

    def git_provider(self):
        return self._get_adapter("git_provider")

    def k8s(self):
        return self._get_adapter("k8s")

    def signature_verifier(self):
        return self._get_adapter("signature_verifier")

    def webhook_destination(self):
        return self._get_adapter("webhook_destination")

    def ticketing(self):
        return self._get_adapter("ticketing")

    def messaging(self):
        return self._get_adapter("messaging")
