from __future__ import annotations

from typing import Any, Dict

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def configure_tracing(config: Dict[str, Any] | None = None) -> None:
    cfg = config or {}
    tracing_cfg = cfg.get("tracing") or {}
    enabled = tracing_cfg.get("enabled", False)
    if not enabled:
        return
    service_name = tracing_cfg.get("service_name", "platform-api")
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    exporter = tracing_cfg.get("exporter", "stdout")
    if exporter == "otlp":
        endpoint = tracing_cfg.get("otlp_endpoint")
        span_exporter = OTLPSpanExporter(endpoint=endpoint) if endpoint else OTLPSpanExporter()
    else:
        span_exporter = ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(provider)
