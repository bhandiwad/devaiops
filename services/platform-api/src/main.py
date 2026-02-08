from __future__ import annotations

import logging
import json

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from adapters.registry import AdapterRegistry
from auth.policy import PolicyConfig, PolicyEngine
from governance.policy_engine import load_policy_engine
from artifacts.loader import load_artifact_store
from adapters.loader import load_object
from api.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from api.middleware import IdempotencyMiddleware, RateLimitMiddleware, RequestMetricsMiddleware
from api.routes import router
from auth.rbac import AuthMiddleware
from config.loader import ConfigLoader
from db.session import create_database
from observability.tracing import configure_tracing


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, self.datefmt),
        }
        return json.dumps(payload)


def create_app() -> FastAPI:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    app = FastAPI(title="AIOps Platform API", version="0.1.0")

    @app.on_event("startup")
    async def startup() -> None:
        loader = ConfigLoader()
        config_store = loader.load_all()
        app.state.config_store = config_store
        app.state.repo_root = loader.repo_root
        app.state.artifact_store = load_artifact_store(
            config_store.platform_config.model_dump() if hasattr(config_store.platform_config, "model_dump") else {}
        )
        app.state.adapter_registry = AdapterRegistry(
            config_store.platform_config,
            artifact_store=app.state.artifact_store,
        )
        rbac_cfg = config_store.platform_config.rbac or {}
        permissions = rbac_cfg.get("permissions") or {}
        deny_by_default = (rbac_cfg.get("defaults") or {}).get("deny_by_default", True)
        app.state.policy_engine = PolicyEngine(PolicyConfig(permissions=permissions, deny_by_default=deny_by_default))
        app.state.governance_policy_engine = load_policy_engine(
            config_store.platform_config.model_dump() if hasattr(config_store.platform_config, "model_dump") else {},
            loader.repo_root,
        )
        configure_tracing(
            config_store.platform_config.model_dump() if hasattr(config_store.platform_config, "model_dump") else {}
        )
        aiops_cfg = config_store.platform_config.aiops or {}
        investigator_path = aiops_cfg.get("investigator_adapter")
        if not investigator_path:
            raise RuntimeError("PlatformConfig.aiops.investigator_adapter is required")
        investigator_cls = load_object(investigator_path)
        app.state.investigator_adapter = investigator_cls(platform_config=config_store.platform_config)
        if not config_store.platform_config.database:
            raise RuntimeError("PlatformConfig.database.url is required")
        if not config_store.platform_config.worker:
            raise RuntimeError("PlatformConfig.worker.broker_url is required")
        app.state.db = create_database(config_store.platform_config.database.url)
        logging.getLogger(__name__).info("Platform API startup complete")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    app.add_middleware(AuthMiddleware, registry_provider=lambda: app.state.adapter_registry)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(RequestMetricsMiddleware)

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.add_api_route("/healthz", lambda: {"status": "ok"}, methods=["GET"])
    app.add_api_route("/metrics", lambda: Response(generate_latest(), media_type=CONTENT_TYPE_LATEST), methods=["GET"])
    app.include_router(router, prefix="/api/v1")
    # Backward-compatible legacy paths; clients should migrate to /api/v1.
    app.include_router(router)

    return app


app = create_app()
