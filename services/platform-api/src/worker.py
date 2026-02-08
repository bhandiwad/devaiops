from __future__ import annotations

import asyncio
import logging
import time
from uuid import uuid4

from celery import Celery
from prometheus_client import Counter, Histogram

from config.loader import ConfigLoader
from artifacts.loader import load_artifact_store
from db.repositories import AuditRepository, TenantRepository, TenantStatusHistoryRepository
from db.services import AuditService, TenantStatusService
from db.session import create_database
from onboarding.pipeline import OnboardingError, build_pipeline
from adapters.registry import AdapterRegistry
from artifacts.service import ArtifactService
from drift.detectors import ArgoCDDriftDetector, PostureDriftDetector, TerraformDriftDetector
from drift.manager import DriftManager
from db.repositories import (
    EventRepository,
    DriftRunRepository,
    ExportBundleRepository,
    ArtifactRefRepository,
    MeteringRollupRepository,
    MeteringSampleRepository,
    ProvisioningRunRepository,
    RunbookExecutionRepository,
    PolicyDecisionRepository,
    IncidentRepository,
    SubscriptionRepository,
)
from exports.bundler import TenantExportBundler
from governance.policy_engine import load_policy_engine
from adapters.errors import AdapterError
from metering.collector import MeteringCollector
from integrations.event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)
JOB_COUNTER = Counter(
    "platform_worker_jobs_total",
    "Worker jobs by type and outcome",
    ["job_type", "outcome"],
)
JOB_LATENCY = Histogram(
    "platform_worker_job_latency_seconds",
    "Worker job latency",
    ["job_type", "outcome"],
)

loader = ConfigLoader()
config_store = loader.load_all()
platform_config = config_store.platform_config
governance_policy_engine = load_policy_engine(
    platform_config.model_dump() if hasattr(platform_config, "model_dump") else {},
    loader.repo_root,
)
artifact_store = load_artifact_store(
    platform_config.model_dump() if hasattr(platform_config, "model_dump") else {}
)

if not platform_config.worker:
    raise RuntimeError("PlatformConfig.worker.broker_url is required")

celery_app = Celery(
    "platform_worker",
    broker=platform_config.worker.broker_url,
    backend=platform_config.worker.result_backend or platform_config.worker.broker_url,
)

drift_cfg = platform_config.drift or {}
schedule_seconds = drift_cfg.get("schedule_seconds")
if schedule_seconds:
    celery_app.conf.beat_schedule = {
        "drift-all-tenants": {
            "task": "run_drift_all",
            "schedule": schedule_seconds,
        }
    }
metering_cfg = platform_config.metering or {}
metering_seconds = metering_cfg.get("schedule_seconds", 1800)
celery_app.conf.beat_schedule = celery_app.conf.beat_schedule or {}
celery_app.conf.beat_schedule["metering-all-tenants"] = {
    "task": "collect_metering_all",
    "schedule": metering_seconds,
}
celery_app.conf.beat_schedule["dispatch-events"] = {
    "task": "dispatch_events",
    "schedule": 30,
}

database = None
if platform_config.database:
    database = create_database(platform_config.database.url)
else:
    raise RuntimeError("PlatformConfig.database.url is required")


def _adapter_registry() -> AdapterRegistry:
    return AdapterRegistry(platform_config, artifact_store=artifact_store)


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def _with_session(fn):
    async with database.session_factory() as session:
        return await fn(session)


async def _transition_status(session, tenant_id: str, to_status: str, error_detail=None):
    tenant_repo = TenantRepository(session)
    history_repo = TenantStatusHistoryRepository(session)
    status_service = TenantStatusService(tenant_repo, history_repo)
    await status_service.transition(tenant_id, to_status, error_detail=error_detail)
    await session.commit()


async def _write_audit(session, principal: str, action: str, tenant_id: str, correlation_id: str, detail=None):
    audit_service = AuditService(AuditRepository(session))
    await audit_service.write_event(
        principal=principal,
        action=action,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        detail=detail or {},
    )
    await session.commit()


async def _update_metadata(session, tenant_id: str, updates: dict) -> None:
    tenant_repo = TenantRepository(session)
    tenant = await tenant_repo.get(tenant_id)
    if not tenant:
        return
    metadata = dict(tenant.metadata_ or {})
    metadata.update(updates)
    await tenant_repo.update_metadata(tenant_id, metadata)
    await session.commit()


@celery_app.task(name="onboard_tenant", bind=True, max_retries=5)
def onboard_tenant(self, tenant_id: str, principal_id: str | None = None, correlation_id: str | None = None):
    started = time.perf_counter()
    correlation_id = correlation_id or str(uuid4())
    principal = principal_id or "system"

    async def _run(session):
        await _write_audit(session, principal, "tenant.onboard.started", tenant_id, correlation_id)

    _run_async(_with_session(_run))

    pipeline = build_pipeline()
    try:
        def _status_update(status: str) -> None:
            _run_async(_with_session(lambda s: _transition_status(s, tenant_id, status)))

        result = pipeline.run(tenant_id, status_callback=_status_update)
        if result.detail.get("integrations"):
            _run_async(
                _with_session(lambda s: _update_metadata(s, tenant_id, {"integrations": result.detail["integrations"]}))
            )
        _run_async(_with_session(lambda s: _transition_status(s, tenant_id, result.status)))
        _run_async(
            _with_session(
                lambda s: _write_audit(
                    s,
                    principal,
                    "tenant.onboard.completed",
                    tenant_id,
                    correlation_id,
                    detail=result.detail,
                )
            )
        )
        JOB_COUNTER.labels(job_type="onboard_tenant", outcome="success").inc()
        JOB_LATENCY.labels(job_type="onboard_tenant", outcome="success").observe(time.perf_counter() - started)
        return {"status": result.status, "detail": result.detail}
    except AdapterError as exc:
        if exc.retryable and self.request.retries < self.max_retries:
            JOB_COUNTER.labels(job_type="onboard_tenant", outcome="retry").inc()
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        _run_async(
            _with_session(
                lambda s: _transition_status(
                    s,
                    tenant_id,
                    "FAILED_RETRYABLE" if exc.retryable else "ERROR",
                    error_detail={"message": str(exc), "code": exc.code},
                )
            )
        )
        JOB_COUNTER.labels(job_type="onboard_tenant", outcome="error").inc()
        JOB_LATENCY.labels(job_type="onboard_tenant", outcome="error").observe(time.perf_counter() - started)
        raise
    except OnboardingError as exc:
        _run_async(
            _with_session(
                lambda s: _transition_status(
                    s,
                    tenant_id,
                    "ERROR",
                    error_detail={"message": str(exc)},
                )
            )
        )
        _run_async(
            _with_session(
                lambda s: _write_audit(
                    s,
                    principal,
                    "tenant.onboard.failed",
                    tenant_id,
                    correlation_id,
                    detail={"error": str(exc)},
                )
            )
        )
        JOB_COUNTER.labels(job_type="onboard_tenant", outcome="error").inc()
        JOB_LATENCY.labels(job_type="onboard_tenant", outcome="error").observe(time.perf_counter() - started)
        raise


@celery_app.task(name="decommission_tenant", bind=True, max_retries=5)
def decommission_tenant(self, tenant_id: str, principal_id: str | None = None, correlation_id: str | None = None):
    started = time.perf_counter()
    correlation_id = correlation_id or str(uuid4())
    principal = principal_id or "system"

    async def _run(session):
        await _transition_status(session, tenant_id, "DECOMMISSIONING")
        await _write_audit(session, principal, "tenant.decommission.started", tenant_id, correlation_id)

    _run_async(_with_session(_run))
    _run_async(
        _with_session(
            lambda s: _write_audit(
                s,
                principal,
                "tenant.decommission.completed",
                tenant_id,
                correlation_id,
                detail={"status": "pending_cleanup"},
            )
        )
    )
    JOB_COUNTER.labels(job_type="decommission_tenant", outcome="success").inc()
    JOB_LATENCY.labels(job_type="decommission_tenant", outcome="success").observe(time.perf_counter() - started)
    return {"status": "DECOMMISSIONING"}


@celery_app.task(name="run_drift", bind=True, max_retries=5)
def run_drift(self, tenant_id: str, correlation_id: str | None = None):
    started = time.perf_counter()
    registry = _adapter_registry()

    async def _run(session):
        artifact_service = ArtifactService(artifact_store, ArtifactRefRepository(session))
        detectors = {
            "terraform": TerraformDriftDetector(config_store, registry),
            "argocd": ArgoCDDriftDetector(config_store, registry),
            "posture": PostureDriftDetector(config_store),
        }
        manager = DriftManager(detectors, DriftRunRepository(session), artifact_service)
        await manager.run(tenant_id)
        await session.commit()

    try:
        _run_async(_with_session(_run))
        JOB_COUNTER.labels(job_type="run_drift", outcome="success").inc()
        JOB_LATENCY.labels(job_type="run_drift", outcome="success").observe(time.perf_counter() - started)
    except AdapterError as exc:
        if exc.retryable and self.request.retries < self.max_retries:
            JOB_COUNTER.labels(job_type="run_drift", outcome="retry").inc()
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        JOB_COUNTER.labels(job_type="run_drift", outcome="error").inc()
        JOB_LATENCY.labels(job_type="run_drift", outcome="error").observe(time.perf_counter() - started)
        raise


@celery_app.task(name="run_drift_all")
def run_drift_all():
    async def _run(session):
        tenant_repo = TenantRepository(session)
        tenants = await tenant_repo.list()
        for tenant in tenants:
            run_drift.delay(tenant.tenant_id)

    _run_async(_with_session(_run))


@celery_app.task(name="export_tenant_bundle", bind=True, max_retries=5)
def export_tenant_bundle(self, tenant_id: str, export_id: str, correlation_id: str | None = None):
    started = time.perf_counter()
    async def _run(session):
        artifact_service = ArtifactService(artifact_store, ArtifactRefRepository(session))
        bundler = TenantExportBundler(
            TenantRepository(session),
            AuditRepository(session),
            PolicyDecisionRepository(session),
            IncidentRepository(session),
            ProvisioningRunRepository(session),
            RunbookExecutionRepository(session),
            DriftRunRepository(session),
            ExportBundleRepository(session),
            artifact_service,
        )
        await bundler.export_existing(export_id, tenant_id)
        await session.commit()

    try:
        _run_async(_with_session(_run))
        JOB_COUNTER.labels(job_type="export_tenant_bundle", outcome="success").inc()
        JOB_LATENCY.labels(job_type="export_tenant_bundle", outcome="success").observe(time.perf_counter() - started)
    except AdapterError as exc:
        if exc.retryable and self.request.retries < self.max_retries:
            JOB_COUNTER.labels(job_type="export_tenant_bundle", outcome="retry").inc()
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        JOB_COUNTER.labels(job_type="export_tenant_bundle", outcome="error").inc()
        JOB_LATENCY.labels(job_type="export_tenant_bundle", outcome="error").observe(time.perf_counter() - started)
        raise


@celery_app.task(name="collect_metering", bind=True, max_retries=5)
def collect_metering(self, tenant_id: str):
    started = time.perf_counter()

    async def _run(session):
        collector = MeteringCollector(
            config_store=config_store,
            registry=_adapter_registry(),
            sample_repo=MeteringSampleRepository(session),
            rollup_repo=MeteringRollupRepository(session),
            audit_repo=AuditRepository(session),
            drift_repo=DriftRunRepository(session),
            runbook_repo=RunbookExecutionRepository(session),
            export_repo=ExportBundleRepository(session),
        )
        await collector.collect(tenant_id)
        await collector.rollup(tenant_id, granularity="hourly")
        await collector.rollup(tenant_id, granularity="daily")
        await session.commit()

    try:
        _run_async(_with_session(_run))
        JOB_COUNTER.labels(job_type="collect_metering", outcome="success").inc()
        JOB_LATENCY.labels(job_type="collect_metering", outcome="success").observe(time.perf_counter() - started)
    except AdapterError as exc:
        if exc.retryable and self.request.retries < self.max_retries:
            JOB_COUNTER.labels(job_type="collect_metering", outcome="retry").inc()
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        JOB_COUNTER.labels(job_type="collect_metering", outcome="error").inc()
        JOB_LATENCY.labels(job_type="collect_metering", outcome="error").observe(time.perf_counter() - started)
        raise


@celery_app.task(name="collect_metering_all")
def collect_metering_all():
    async def _run(session):
        tenant_repo = TenantRepository(session)
        tenants = await tenant_repo.list()
        for tenant in tenants:
            collect_metering.delay(tenant.tenant_id)

    _run_async(_with_session(_run))


@celery_app.task(name="dispatch_events", bind=True, max_retries=5)
def dispatch_events(self):
    started = time.perf_counter()

    async def _run(session):
        dispatcher = EventDispatcher(
            registry=_adapter_registry(),
            event_repo=EventRepository(session),
            subscription_repo=SubscriptionRepository(session),
        )
        await dispatcher.dispatch_pending(limit=100)
        await session.commit()

    try:
        _run_async(_with_session(_run))
        JOB_COUNTER.labels(job_type="dispatch_events", outcome="success").inc()
        JOB_LATENCY.labels(job_type="dispatch_events", outcome="success").observe(time.perf_counter() - started)
    except AdapterError as exc:
        if exc.retryable and self.request.retries < self.max_retries:
            JOB_COUNTER.labels(job_type="dispatch_events", outcome="retry").inc()
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        JOB_COUNTER.labels(job_type="dispatch_events", outcome="error").inc()
        JOB_LATENCY.labels(job_type="dispatch_events", outcome="error").observe(time.perf_counter() - started)
        raise
