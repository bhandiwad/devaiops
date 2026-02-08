from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from db.models import AuditEvent, Event, PolicyDecision, TenantStatusHistory
from db.repositories import AuditRepository, EventRepository, PolicyDecisionRepository, TenantRepository, TenantStatusHistoryRepository


@dataclass
class AuditService:
    repository: AuditRepository

    async def write_event(
        self,
        principal: str,
        action: str,
        tenant_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=str(uuid4()),
            tenant_id=tenant_id,
            principal=principal,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            correlation_id=correlation_id,
            detail=detail or {},
        )
        return await self.repository.create(event)


@dataclass
class TenantStatusService:
    tenant_repo: TenantRepository
    history_repo: TenantStatusHistoryRepository

    async def transition(
        self,
        tenant_id: str,
        to_status: str,
        error_detail: Optional[Dict[str, Any]] = None,
        from_status_override: Optional[str] = None,
    ) -> TenantStatusHistory:
        tenant = await self.tenant_repo.get(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant not found: {tenant_id}")
        from_status = from_status_override if from_status_override is not None else tenant.status
        await self.tenant_repo.update_status(tenant_id, to_status)
        history = TenantStatusHistory(
            history_id=str(uuid4()),
            tenant_id=tenant_id,
            from_status=from_status,
            to_status=to_status,
            error_detail=error_detail or {},
        )
        return await self.history_repo.create(history)


@dataclass
class PolicyDecisionService:
    repository: PolicyDecisionRepository

    async def record(
        self,
        tenant_id: Optional[str],
        action: str,
        allow: bool,
        reasons: list[str],
        obligations: list[str],
        principal: dict,
        correlation_id: Optional[str] = None,
    ) -> PolicyDecision:
        decision = PolicyDecision(
            decision_id=str(uuid4()),
            tenant_id=tenant_id,
            action=action,
            allow=allow,
            reasons=reasons,
            obligations=obligations,
            principal=principal,
            correlation_id=correlation_id,
        )
        return await self.repository.create(decision)


@dataclass
class EventService:
    repository: EventRepository

    async def append(
        self,
        event_type: str,
        payload: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> Event:
        event = Event(
            event_id=str(uuid4()),
            tenant_id=tenant_id,
            type=event_type,
            payload=payload,
            status="PENDING",
        )
        return await self.repository.create(event)

    async def mark_dispatched(self, event: Event, status: str = "DISPATCHED") -> Event:
        event.status = status
        event.dispatched_at = datetime.utcnow()
        return await self.repository.update(event)
