from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    AccessRequest,
    ArtifactRef,
    AuditEvent,
    DriftRun,
    IdempotencyKey,
    ExportBundle,
    Incident,
    IncidentTransition,
    MeteringRollup,
    MeteringSample,
    Event,
    Subscription,
    PolicyDecision,
    ProvisioningRun,
    Promotion,
    RemediationPR,
    RunbookExecution,
    Tenant,
    TenantStatusHistory,
    DeploymentProvenance,
    UpgradeRun,
)


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, tenant: Tenant) -> Tenant:
        self.session.add(tenant)
        await self.session.flush()
        await self.session.refresh(tenant)
        return tenant

    async def list(self, tenant_ids: Optional[Iterable[str]] = None) -> List[Tenant]:
        stmt = select(Tenant)
        if tenant_ids is not None:
            stmt = stmt.where(Tenant.tenant_id.in_(list(tenant_ids)))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, tenant_id: str) -> Optional[Tenant]:
        result = await self.session.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
        return result.scalars().first()

    async def delete(self, tenant_id: str) -> bool:
        result = await self.session.execute(delete(Tenant).where(Tenant.tenant_id == tenant_id))
        return result.rowcount > 0

    async def update_status(self, tenant_id: str, status: str) -> Optional[Tenant]:
        tenant = await self.get(tenant_id)
        if not tenant:
            return None
        tenant.status = status
        await self.session.flush()
        await self.session.refresh(tenant)
        return tenant

    async def update_metadata(self, tenant_id: str, metadata: dict) -> Optional[Tenant]:
        tenant = await self.get(tenant_id)
        if not tenant:
            return None
        tenant.metadata_ = metadata
        await self.session.flush()
        await self.session.refresh(tenant)
        return tenant


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, event: AuditEvent) -> AuditEvent:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def list_for_tenant(self, tenant_id: str) -> List[AuditEvent]:
        stmt = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id).order_by(AuditEvent.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class TenantStatusHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, history: TenantStatusHistory) -> TenantStatusHistory:
        self.session.add(history)
        await self.session.flush()
        await self.session.refresh(history)
        return history

    async def list_for_tenant(self, tenant_id: str) -> List[TenantStatusHistory]:
        stmt = select(TenantStatusHistory).where(TenantStatusHistory.tenant_id == tenant_id).order_by(
            TenantStatusHistory.occurred_at.desc()
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, incident: Incident) -> Incident:
        self.session.add(incident)
        await self.session.flush()
        await self.session.refresh(incident)
        return incident

    async def list_for_tenant(self, tenant_id: str) -> List[Incident]:
        result = await self.session.execute(select(Incident).where(Incident.tenant_id == tenant_id))
        return list(result.scalars().all())

    async def get(self, incident_id: str) -> Incident | None:
        result = await self.session.execute(select(Incident).where(Incident.incident_id == incident_id))
        return result.scalars().first()

    async def update(self, incident: Incident) -> Incident:
        await self.session.flush()
        await self.session.refresh(incident)
        return incident


class RemediationPRRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, pr: RemediationPR) -> RemediationPR:
        self.session.add(pr)
        await self.session.flush()
        await self.session.refresh(pr)
        return pr

    async def list_for_tenant(self, tenant_id: str) -> List[RemediationPR]:
        result = await self.session.execute(select(RemediationPR).where(RemediationPR.tenant_id == tenant_id))
        return list(result.scalars().all())


class ArtifactRefRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, artifact: ArtifactRef) -> ArtifactRef:
        self.session.add(artifact)
        await self.session.flush()
        await self.session.refresh(artifact)
        return artifact

    async def get(self, artifact_id: str) -> ArtifactRef | None:
        result = await self.session.execute(select(ArtifactRef).where(ArtifactRef.artifact_id == artifact_id))
        return result.scalars().first()


class ProvisioningRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, run: ProvisioningRun) -> ProvisioningRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def list_for_tenant(self, tenant_id: str) -> List[ProvisioningRun]:
        result = await self.session.execute(select(ProvisioningRun).where(ProvisioningRun.tenant_id == tenant_id))
        return list(result.scalars().all())

    async def get(self, run_id: str) -> ProvisioningRun | None:
        result = await self.session.execute(select(ProvisioningRun).where(ProvisioningRun.run_id == run_id))
        return result.scalars().first()

    async def update(self, run: ProvisioningRun) -> ProvisioningRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run


class RunbookExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, execution: RunbookExecution) -> RunbookExecution:
        self.session.add(execution)
        await self.session.flush()
        await self.session.refresh(execution)
        return execution

    async def list_for_tenant(self, tenant_id: str) -> List[RunbookExecution]:
        result = await self.session.execute(select(RunbookExecution).where(RunbookExecution.tenant_id == tenant_id))
        return list(result.scalars().all())

    async def get(self, exec_id: str) -> RunbookExecution | None:
        result = await self.session.execute(select(RunbookExecution).where(RunbookExecution.exec_id == exec_id))
        return result.scalars().first()

    async def update(self, execution: RunbookExecution) -> RunbookExecution:
        await self.session.flush()
        await self.session.refresh(execution)
        return execution


class PolicyDecisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, decision: PolicyDecision) -> PolicyDecision:
        self.session.add(decision)
        await self.session.flush()
        await self.session.refresh(decision)
        return decision

    async def list_for_tenant(self, tenant_id: str) -> List[PolicyDecision]:
        result = await self.session.execute(
            select(PolicyDecision).where(PolicyDecision.tenant_id == tenant_id).order_by(PolicyDecision.created_at.desc())
        )
        return list(result.scalars().all())


class DriftRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, run: DriftRun) -> DriftRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def list_for_tenant(self, tenant_id: str) -> List[DriftRun]:
        result = await self.session.execute(
            select(DriftRun).where(DriftRun.tenant_id == tenant_id).order_by(DriftRun.started_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, run_id: str) -> DriftRun | None:
        result = await self.session.execute(select(DriftRun).where(DriftRun.run_id == run_id))
        return result.scalars().first()

    async def update(self, run: DriftRun) -> DriftRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run


class ExportBundleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, bundle: ExportBundle) -> ExportBundle:
        self.session.add(bundle)
        await self.session.flush()
        await self.session.refresh(bundle)
        return bundle

    async def list_for_tenant(self, tenant_id: str) -> List[ExportBundle]:
        result = await self.session.execute(select(ExportBundle).where(ExportBundle.tenant_id == tenant_id))
        return list(result.scalars().all())

    async def get(self, export_id: str) -> ExportBundle | None:
        result = await self.session.execute(select(ExportBundle).where(ExportBundle.export_id == export_id))
        return result.scalars().first()

    async def update(self, bundle: ExportBundle) -> ExportBundle:
        await self.session.flush()
        await self.session.refresh(bundle)
        return bundle


class DeploymentProvenanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, provenance: DeploymentProvenance) -> DeploymentProvenance:
        self.session.add(provenance)
        await self.session.flush()
        await self.session.refresh(provenance)
        return provenance

    async def list_for_tenant(self, tenant_id: str) -> List[DeploymentProvenance]:
        result = await self.session.execute(select(DeploymentProvenance).where(DeploymentProvenance.tenant_id == tenant_id))
        return list(result.scalars().all())


class IdempotencyKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, key: IdempotencyKey) -> IdempotencyKey:
        self.session.add(key)
        await self.session.flush()
        await self.session.refresh(key)
        return key

    async def get(self, idempotency_key: str) -> IdempotencyKey | None:
        result = await self.session.execute(
            select(IdempotencyKey).where(IdempotencyKey.idempotency_key == idempotency_key)
        )
        return result.scalars().first()

    async def update(self, key: IdempotencyKey) -> IdempotencyKey:
        await self.session.flush()
        await self.session.refresh(key)
        return key


class UpgradeRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, run: UpgradeRun) -> UpgradeRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def list(self) -> List[UpgradeRun]:
        result = await self.session.execute(select(UpgradeRun).order_by(UpgradeRun.started_at.desc()))
        return list(result.scalars().all())

    async def get(self, run_id: str) -> UpgradeRun | None:
        result = await self.session.execute(select(UpgradeRun).where(UpgradeRun.run_id == run_id))
        return result.scalars().first()

    async def update(self, run: UpgradeRun) -> UpgradeRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run


class MeteringSampleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, sample: MeteringSample) -> MeteringSample:
        self.session.add(sample)
        await self.session.flush()
        await self.session.refresh(sample)
        return sample

    async def list_for_tenant(
        self,
        tenant_id: str,
        captured_from: datetime | None = None,
        captured_to: datetime | None = None,
    ) -> List[MeteringSample]:
        stmt = select(MeteringSample).where(MeteringSample.tenant_id == tenant_id)
        if captured_from:
            stmt = stmt.where(MeteringSample.captured_at >= captured_from)
        if captured_to:
            stmt = stmt.where(MeteringSample.captured_at <= captured_to)
        result = await self.session.execute(stmt.order_by(MeteringSample.captured_at.desc()))
        return list(result.scalars().all())


class MeteringRollupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, rollup: MeteringRollup) -> MeteringRollup:
        self.session.add(rollup)
        await self.session.flush()
        await self.session.refresh(rollup)
        return rollup

    async def list_for_tenant(
        self,
        tenant_id: str,
        granularity: str | None = None,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
    ) -> List[MeteringRollup]:
        stmt = select(MeteringRollup).where(MeteringRollup.tenant_id == tenant_id)
        if granularity:
            stmt = stmt.where(MeteringRollup.granularity == granularity)
        if period_from:
            stmt = stmt.where(MeteringRollup.period_start >= period_from)
        if period_to:
            stmt = stmt.where(MeteringRollup.period_end <= period_to)
        result = await self.session.execute(stmt.order_by(MeteringRollup.period_start.desc()))
        return list(result.scalars().all())

    async def list_all(self, granularity: str | None = None) -> List[MeteringRollup]:
        stmt = select(MeteringRollup)
        if granularity:
            stmt = stmt.where(MeteringRollup.granularity == granularity)
        result = await self.session.execute(stmt.order_by(MeteringRollup.period_start.desc()))
        return list(result.scalars().all())


class PromotionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, promotion: Promotion) -> Promotion:
        self.session.add(promotion)
        await self.session.flush()
        await self.session.refresh(promotion)
        return promotion

    async def list_for_service(self, tenant_id: str, service_id: str) -> List[Promotion]:
        result = await self.session.execute(
            select(Promotion)
            .where(Promotion.tenant_id == tenant_id, Promotion.service_id == service_id)
            .order_by(Promotion.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, promotion: Promotion) -> Promotion:
        await self.session.flush()
        await self.session.refresh(promotion)
        return promotion


class AccessRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, req: AccessRequest) -> AccessRequest:
        self.session.add(req)
        await self.session.flush()
        await self.session.refresh(req)
        return req

    async def list_for_tenant(self, tenant_id: str) -> List[AccessRequest]:
        result = await self.session.execute(
            select(AccessRequest).where(AccessRequest.tenant_id == tenant_id).order_by(AccessRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, request_id: str) -> AccessRequest | None:
        result = await self.session.execute(select(AccessRequest).where(AccessRequest.request_id == request_id))
        return result.scalars().first()

    async def update(self, req: AccessRequest) -> AccessRequest:
        await self.session.flush()
        await self.session.refresh(req)
        return req


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, event: Event) -> Event:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def list(self, tenant_id: str | None = None) -> List[Event]:
        stmt = select(Event)
        if tenant_id:
            stmt = stmt.where(Event.tenant_id == tenant_id)
        result = await self.session.execute(stmt.order_by(Event.created_at.desc()))
        return list(result.scalars().all())

    async def list_pending(self, limit: int = 100) -> List[Event]:
        result = await self.session.execute(
            select(Event).where(Event.status == "PENDING").order_by(Event.created_at.asc()).limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, event: Event) -> Event:
        await self.session.flush()
        await self.session.refresh(event)
        return event


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, subscription: Subscription) -> Subscription:
        self.session.add(subscription)
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def list_for_tenant(self, tenant_id: str) -> List[Subscription]:
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.tenant_id == tenant_id, Subscription.status == "ACTIVE")
            .order_by(Subscription.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_global(self) -> List[Subscription]:
        result = await self.session.execute(
            select(Subscription).where(Subscription.tenant_id.is_(None), Subscription.status == "ACTIVE")
        )
        return list(result.scalars().all())

    async def get(self, subscription_id: str) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription).where(Subscription.subscription_id == subscription_id)
        )
        return result.scalars().first()

    async def update(self, subscription: Subscription) -> Subscription:
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription


class IncidentTransitionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, transition: IncidentTransition) -> IncidentTransition:
        self.session.add(transition)
        await self.session.flush()
        await self.session.refresh(transition)
        return transition

    async def list_for_incident(self, incident_id: str) -> List[IncidentTransition]:
        result = await self.session.execute(
            select(IncidentTransition)
            .where(IncidentTransition.incident_id == incident_id)
            .order_by(IncidentTransition.created_at.desc())
        )
        return list(result.scalars().all())
