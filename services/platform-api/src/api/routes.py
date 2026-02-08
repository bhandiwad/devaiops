from __future__ import annotations

from typing import Any, List
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.registry import AdapterRegistry
from auth.rbac import require_permission, require_platform_admin, require_principal, require_tenant_access
from config.loader import ConfigStore
from db.models import (
    AccessRequest,
    Event,
    ExportBundle,
    Incident,
    IncidentTransition,
    Promotion,
    RemediationPR,
    Subscription,
    Tenant,
    UpgradeRun,
)
from aiops.evidence import EvidenceCollector
from aiops.pr_bot import create_remediation_pr
from db.repositories import (
    AuditRepository,
    DriftRunRepository,
    ExportBundleRepository,
    EventRepository,
    IncidentRepository,
    IncidentTransitionRepository,
    MeteringRollupRepository,
    MeteringSampleRepository,
    PolicyDecisionRepository,
    PromotionRepository,
    ProvisioningRunRepository,
    AccessRequestRepository,
    RemediationPRRepository,
    RunbookExecutionRepository,
    SubscriptionRepository,
    TenantRepository,
    TenantStatusHistoryRepository,
    UpgradeRunRepository,
    ArtifactRefRepository,
)
from db.services import AuditService, EventService, PolicyDecisionService, TenantStatusService
from governance.enforcement import evaluate_and_record_policy
from drift.detectors import ArgoCDDriftDetector, PostureDriftDetector, TerraformDriftDetector
from drift.manager import DriftManager
from artifacts.service import ArtifactService
from models.api import (
    AccessRequestCreate,
    AccessRequestResponse,
    AuditEventResponse,
    DRStatusResponse,
    DriftRunResponse,
    DriftSummaryResponse,
    DeploymentStatusResponse,
    EvidenceResponse,
    EventResponse,
    ExportCreateRequest,
    ExportResponse,
    FinopsSummaryResponse,
    IncidentCreateRequest,
    IncidentResponse,
    IncidentTransitionRequest,
    IncidentTransitionResponse,
    MessageResponse,
    MeteringRollupResponse,
    ModulePlanResponse,
    PolicyDecisionResponse,
    PlatformVersionResponse,
    ProductResponse,
    ProductToggleResponse,
    RunbookSummaryResponse,
    PromotionResponse,
    RemediationPRResponse,
    ScaffoldRequest,
    ScaffoldResponse,
    SearchItemResponse,
    SearchResponse,
    OnboardingProgressResponse,
    SubscriptionCreateRequest,
    SubscriptionResponse,
    TenantCreateRequest,
    TenantResponse,
    TenantStatusHistoryResponse,
    TenantStatusResponse,
    UpgradePlanResponse,
    UpgradeRunResponse,
)
from models.identity import PrincipalContext
from metering.collector import MeteringCollector
from modules.engine import ModuleEngine
from promotions.controller import PromotionController
from scaffolding.service import ScaffolderService
from worker import celery_app

router = APIRouter()
INCIDENT_ALLOWED_TRANSITIONS = {
    "NEW": {"EVIDENCE_COLLECTED", "CLOSED"},
    "EVIDENCE_COLLECTED": {"INVESTIGATING", "CLOSED"},
    "INVESTIGATING": {"PR_CREATED", "WAITING_APPROVAL", "RESOLVED", "CLOSED"},
    "PR_CREATED": {"WAITING_APPROVAL", "RESOLVED", "CLOSED"},
    "WAITING_APPROVAL": {"RESOLVED", "CLOSED"},
    "RESOLVED": {"CLOSED"},
    "CLOSED": set(),
}


def get_config_store(request: Request) -> ConfigStore:
    return request.app.state.config_store


def get_adapter_registry(request: Request) -> AdapterRegistry:
    return request.app.state.adapter_registry


async def get_db_session(request: Request):
    async with request.app.state.db.session_factory() as session:
        yield session


async def get_audit_service(session: AsyncSession = Depends(get_db_session)) -> AuditService:
    return AuditService(AuditRepository(session))


async def get_status_service(session: AsyncSession = Depends(get_db_session)) -> TenantStatusService:
    return TenantStatusService(TenantRepository(session), TenantStatusHistoryRepository(session))


async def get_policy_service(session: AsyncSession = Depends(get_db_session)) -> PolicyDecisionService:
    return PolicyDecisionService(PolicyDecisionRepository(session))


async def get_event_service(session: AsyncSession = Depends(get_db_session)) -> EventService:
    return EventService(EventRepository(session))


async def get_artifact_service(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> ArtifactService:
    return ArtifactService(request.app.state.artifact_store, ArtifactRefRepository(session))


def get_evidence_collector(request: Request) -> EvidenceCollector:
    return EvidenceCollector(
        request.app.state.config_store,
        request.app.state.adapter_registry,
        request.app.state.repo_root,
    )


def get_investigator(request: Request):
    return request.app.state.investigator_adapter


async def _record_incident_transition(
    session: AsyncSession,
    tenant_id: str,
    incident: Incident,
    to_status: str,
    detail: dict[str, Any] | None = None,
) -> IncidentTransition:
    current = incident.status
    if current != to_status:
        allowed = INCIDENT_ALLOWED_TRANSITIONS.get(current, set())
        if to_status not in allowed:
            raise HTTPException(status_code=409, detail=f"Invalid incident transition: {current} -> {to_status}")
    incident.status = to_status
    await IncidentRepository(session).update(incident)
    transition = IncidentTransition(
        transition_id=str(uuid4()),
        incident_id=incident.incident_id,
        tenant_id=tenant_id,
        from_status=current,
        to_status=to_status,
        detail=detail or {},
    )
    return await IncidentTransitionRepository(session).create(transition)


@router.get("/me")
async def get_me(request: Request, audit: AuditService = Depends(get_audit_service)):
    principal: PrincipalContext = require_principal(request)
    await audit.write_event(
        principal=principal.principal_id,
        action="identity.me.read",
        detail={"email": principal.email},
    )
    return principal.model_dump()


@router.get("/provider-profiles")
async def list_provider_profiles(
    request: Request,
    config_store: ConfigStore = Depends(get_config_store),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.read")
    await audit.write_event(
        principal=principal.principal_id,
        action="config.provider_profiles.read",
    )
    return [profile.model_dump() for profile in config_store.provider_profiles.values()]


@router.get("/modules")
async def list_modules(
    request: Request,
    config_store: ConfigStore = Depends(get_config_store),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.read")
    await audit.write_event(
        principal=principal.principal_id,
        action="config.modules.read",
    )
    return config_store.module_catalog.model_dump()["modules"]


@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(
    request: Request,
    payload: TenantCreateRequest,
    config_store: ConfigStore = Depends(get_config_store),
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
    status_service: TenantStatusService = Depends(get_status_service),
    event_service: EventService = Depends(get_event_service),
):
    principal: PrincipalContext = require_principal(request)
    require_platform_admin(principal)
    await evaluate_and_record_policy(
        request,
        principal,
        action="tenant.create",
        payload={"tenant_id": payload.tenant_id, "mode": payload.mode},
        policy_service=policy_service,
    )

    repo = TenantRepository(session)
    existing = await repo.get(payload.tenant_id)
    if existing:
        raise HTTPException(status_code=409, detail="Tenant already exists")

    if not config_store.platform_config.tenants:
        raise HTTPException(status_code=500, detail="PlatformConfig.tenants.default_status is required")
    default_status = config_store.platform_config.tenants.default_status

    tenant = Tenant(
        tenant_id=payload.tenant_id,
        display_name=payload.display_name,
        mode=payload.mode,
        provider_profile_id=payload.provider_profile_id,
        status=default_status,
        metadata_={},
    )
    await repo.create(tenant)
    await status_service.transition(tenant.tenant_id, default_status)
    await audit.write_event(
        principal=principal.principal_id,
        action="tenant.create",
        tenant_id=tenant.tenant_id,
        resource_type="tenant",
        resource_id=tenant.tenant_id,
        detail={"mode": tenant.mode, "status": tenant.status},
    )
    await event_service.append(
        "TenantCreated",
        {"tenant_id": tenant.tenant_id, "mode": tenant.mode, "status": tenant.status},
        tenant_id=tenant.tenant_id,
    )
    celery_app.send_task(
        "onboard_tenant",
        args=[tenant.tenant_id, principal.principal_id, request.state.correlation_id],
    )
    await audit.write_event(
        principal=principal.principal_id,
        action="tenant.onboarding.enqueued",
        tenant_id=tenant.tenant_id,
        resource_type="tenant",
        resource_id=tenant.tenant_id,
        correlation_id=str(uuid4()),
        detail={"status": "queued"},
    )
    await session.commit()
    return TenantResponse.model_validate(tenant)


@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    request: Request,
    response: Response,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    repo = TenantRepository(session)
    if principal.is_platform_admin():
        tenants = await repo.list()
    else:
        tenant_ids = list(principal.tenant_roles.keys())
        tenants = await repo.list(tenant_ids=tenant_ids)
    total = len(tenants)
    paged = tenants[offset : offset + max(1, min(limit, 200))]
    response.headers["X-Total-Count"] = str(total)
    await audit.write_event(
        principal=principal.principal_id,
        action="tenant.list",
        detail={"count": len(paged), "total": total, "limit": limit, "offset": offset},
    )
    await session.commit()
    return [TenantResponse.model_validate(t) for t in paged]


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    request: Request,
    tenant_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.read", tenant_id)

    repo = TenantRepository(session)
    tenant = await repo.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await audit.write_event(
        principal=principal.principal_id,
        action="tenant.read",
        tenant_id=tenant_id,
        resource_type="tenant",
        resource_id=tenant_id,
    )
    await session.commit()
    return TenantResponse.model_validate(tenant)


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    request: Request,
    tenant_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
):
    principal: PrincipalContext = require_principal(request)
    require_platform_admin(principal)
    await evaluate_and_record_policy(
        request,
        principal,
        action="tenant.decommission",
        tenant_id=tenant_id,
        payload={},
        policy_service=policy_service,
    )

    repo = TenantRepository(session)
    deleted = await repo.delete(tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await audit.write_event(
        principal=principal.principal_id,
        action="tenant.delete",
        tenant_id=tenant_id,
        resource_type="tenant",
        resource_id=tenant_id,
    )
    await session.commit()
    return {"status": "deleted"}


@router.post("/tenants/{tenant_id}/onboard")
async def onboard_tenant(
    request: Request,
    tenant_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.manage", tenant_id)
    await evaluate_and_record_policy(
        request,
        principal,
        action="tenant.onboard",
        tenant_id=tenant_id,
        payload={},
        policy_service=policy_service,
    )

    repo = TenantRepository(session)
    tenant = await repo.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    celery_app.send_task(
        "onboard_tenant",
        args=[tenant_id, principal.principal_id, request.state.correlation_id],
    )
    await audit.write_event(
        principal=principal.principal_id,
        action="tenant.onboarding.enqueued",
        tenant_id=tenant_id,
        resource_type="tenant",
        resource_id=tenant_id,
        correlation_id=str(uuid4()),
        detail={"status": "queued"},
    )
    await session.commit()
    return {"status": "queued"}


@router.get("/tenants/{tenant_id}/status", response_model=TenantStatusResponse)
async def get_tenant_status(
    request: Request,
    tenant_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.read", tenant_id)

    repo = TenantRepository(session)
    tenant = await repo.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    history_repo = TenantStatusHistoryRepository(session)
    history = await history_repo.list_for_tenant(tenant_id)
    await audit.write_event(
        principal=principal.principal_id,
        action="tenant.status.read",
        tenant_id=tenant_id,
        detail={"current": tenant.status},
    )
    await session.commit()
    return TenantStatusResponse(
        tenant_id=tenant_id,
        status=tenant.status,
        history=[TenantStatusHistoryResponse.model_validate(h) for h in history],
    )


@router.get("/tenants/{tenant_id}/onboarding/progress", response_model=OnboardingProgressResponse)
async def get_onboarding_progress(
    request: Request,
    tenant_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.read", tenant_id)
    tenant = await TenantRepository(session).get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    history = await TenantStatusHistoryRepository(session).list_for_tenant(tenant_id)
    recent_audit = await AuditRepository(session).list_for_tenant(tenant_id)
    return OnboardingProgressResponse(
        tenant_id=tenant_id,
        status=tenant.status,
        history=[TenantStatusHistoryResponse.model_validate(h) for h in history[:20]],
        recent_audit=[AuditEventResponse.model_validate(e) for e in recent_audit[:20]],
    )


@router.get("/tenants/{tenant_id}/deployments", response_model=List[DeploymentStatusResponse])
async def list_deployments(
    request: Request,
    tenant_id: str,
    config_store: ConfigStore = Depends(get_config_store),
    session: AsyncSession = Depends(get_db_session),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.read", tenant_id)
    spec = config_store.get_tenant_spec(tenant_id).model_dump()
    services = spec.get("services") or []
    gitops = request.app.state.adapter_registry.gitops()
    rows: list[DeploymentStatusResponse] = []
    for svc in services:
        app_ref = svc.get("gitops_app") or f"{tenant_id}-{svc.get('id')}"
        status = gitops.get_application_status(app_ref)
        rows.append(
            DeploymentStatusResponse(
                tenant_id=tenant_id,
                service_id=svc.get("id"),
                app_ref=app_ref,
                status=status,
            )
        )
    await session.commit()
    return rows


@router.post("/tenants/{tenant_id}/deployments/{service_id}/sync", response_model=MessageResponse)
async def sync_deployment(
    request: Request,
    tenant_id: str,
    service_id: str,
    config_store: ConfigStore = Depends(get_config_store),
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.manage", tenant_id)
    spec = config_store.get_tenant_spec(tenant_id).model_dump()
    service = next((s for s in (spec.get("services") or []) if s.get("id") == service_id), None)
    if not service:
        raise HTTPException(status_code=404, detail="Service deployment not found")
    app_ref = service.get("gitops_app") or f"{tenant_id}-{service_id}"
    request.app.state.adapter_registry.gitops().sync_application(app_ref)
    await audit.write_event(
        principal=principal.principal_id,
        action="deployment.sync",
        tenant_id=tenant_id,
        resource_type="deployment",
        resource_id=service_id,
        detail={"app_ref": app_ref},
    )
    await session.commit()
    return MessageResponse(status="queued", detail={"app_ref": app_ref})


@router.post("/tenants/{tenant_id}/deployments/{service_id}/rollback", response_model=MessageResponse)
async def rollback_deployment(
    request: Request,
    tenant_id: str,
    service_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.manage", tenant_id)
    await audit.write_event(
        principal=principal.principal_id,
        action="deployment.rollback.requested",
        tenant_id=tenant_id,
        resource_type="deployment",
        resource_id=service_id,
        detail={"mode": "gitops_revert_pr"},
    )
    await session.commit()
    return MessageResponse(
        status="manual_action_required",
        detail={
            "message": "Rollback requires reverting manifest revision through GitOps PR.",
            "service_id": service_id,
        },
    )


@router.post("/tenants/{tenant_id}/plan", response_model=ModulePlanResponse)
async def plan_modules(
    request: Request,
    tenant_id: str,
    config_store: ConfigStore = Depends(get_config_store),
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.plan", tenant_id)

    tenant_spec = config_store.get_tenant_spec(tenant_id).model_dump()
    provider_profile = config_store.get_provider_profile(tenant_spec["provider_profile_id"]).model_dump()
    capability_report = {"capabilities": provider_profile.get("capabilities", {})}

    engine = ModuleEngine(
        module_catalog=config_store.module_catalog.model_dump(),
        platform_adapters=config_store.platform_config.adapters,
    )
    plan = engine.plan(tenant_spec, provider_profile, capability_report, tenant_id=tenant_id)
    await audit.write_event(
        principal=principal.principal_id,
        action="tenant.module.plan",
        tenant_id=tenant_id,
        detail={"errors": len(plan.errors)},
    )
    await session.commit()
    return ModulePlanResponse(items=plan.items, errors=plan.errors)


@router.get("/tenants/{tenant_id}/audit", response_model=List[AuditEventResponse])
async def list_audit_events(
    request: Request,
    tenant_id: str,
    response: Response,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "audit.read", tenant_id)

    repo = AuditRepository(session)
    events = await repo.list_for_tenant(tenant_id)
    total = len(events)
    paged = events[offset : offset + max(1, min(limit, 500))]
    response.headers["X-Total-Count"] = str(total)
    await audit.write_event(
        principal=principal.principal_id,
        action="tenant.audit.read",
        tenant_id=tenant_id,
        detail={"count": len(paged), "total": total, "limit": limit, "offset": offset},
    )
    await session.commit()
    return [AuditEventResponse.model_validate(e) for e in paged]


@router.post("/tenants/{tenant_id}/incidents", response_model=IncidentResponse)
async def create_incident(
    request: Request,
    tenant_id: str,
    payload: IncidentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    event_service: EventService = Depends(get_event_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "incident.ingest", tenant_id)

    incident_repo = IncidentRepository(session)
    incident = Incident(
        incident_id=str(uuid4()),
        tenant_id=tenant_id,
        service_id=payload.service_id,
        alert_name=payload.alert_name,
        status="NEW",
        alert_json=payload.alert,
        evidence_json={},
        proposal_json={},
    )
    await incident_repo.create(incident)
    await IncidentTransitionRepository(session).create(
        IncidentTransition(
            transition_id=str(uuid4()),
            incident_id=incident.incident_id,
            tenant_id=tenant_id,
            from_status=None,
            to_status="NEW",
            detail={"source": "ingest"},
        )
    )
    await audit.write_event(
        principal=principal.principal_id,
        action="incident.create",
        tenant_id=tenant_id,
        resource_type="incident",
        resource_id=incident.incident_id,
    )
    await event_service.append(
        "IncidentCreated",
        {"incident_id": incident.incident_id, "alert_name": incident.alert_name, "service_id": incident.service_id},
        tenant_id=tenant_id,
    )
    await session.commit()
    return IncidentResponse.model_validate(incident)


@router.get("/tenants/{tenant_id}/incidents", response_model=List[IncidentResponse])
async def list_incidents(
    request: Request,
    tenant_id: str,
    response: Response,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "incident.read", tenant_id)
    incident_repo = IncidentRepository(session)
    incidents = await incident_repo.list_for_tenant(tenant_id)
    total = len(incidents)
    paged = incidents[offset : offset + max(1, min(limit, 200))]
    response.headers["X-Total-Count"] = str(total)
    await audit.write_event(
        principal=principal.principal_id,
        action="incident.list",
        tenant_id=tenant_id,
        detail={"count": len(paged), "total": total, "limit": limit, "offset": offset},
    )
    await session.commit()
    return [IncidentResponse.model_validate(i) for i in paged]


@router.get("/tenants/{tenant_id}/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    request: Request,
    tenant_id: str,
    incident_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "incident.read", tenant_id)
    incident_repo = IncidentRepository(session)
    incident = await incident_repo.get(incident_id)
    if not incident or incident.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    await audit.write_event(
        principal=principal.principal_id,
        action="incident.read",
        tenant_id=tenant_id,
        resource_type="incident",
        resource_id=incident_id,
    )
    await session.commit()
    return IncidentResponse.model_validate(incident)


@router.post("/tenants/{tenant_id}/incidents/{incident_id}/evidence", response_model=EvidenceResponse)
async def collect_evidence(
    request: Request,
    tenant_id: str,
    incident_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    event_service: EventService = Depends(get_event_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "incident.investigate", tenant_id)

    incident_repo = IncidentRepository(session)
    incident = await incident_repo.get(incident_id)
    if not incident or incident.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Incident not found")

    collector = get_evidence_collector(request)
    result = collector.collect(tenant_id, incident_id, incident.alert_json, incident.service_id)
    incident.evidence_json = result.evidence
    await _record_incident_transition(
        session,
        tenant_id,
        incident,
        "EVIDENCE_COLLECTED",
        detail={"redacted_fields": result.redaction.get("redacted_fields", [])},
    )
    await audit.write_event(
        principal=principal.principal_id,
        action="incident.evidence.collect",
        tenant_id=tenant_id,
        resource_type="incident",
        resource_id=incident_id,
        detail=result.redaction,
    )
    await event_service.append(
        "IncidentUpdated",
        {"incident_id": incident_id, "status": "EVIDENCE_COLLECTED"},
        tenant_id=tenant_id,
    )
    await session.commit()
    return EvidenceResponse(incident_id=incident_id, evidence=result.evidence)


@router.post("/tenants/{tenant_id}/incidents/{incident_id}/investigate", response_model=IncidentResponse)
async def investigate_incident(
    request: Request,
    tenant_id: str,
    incident_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    event_service: EventService = Depends(get_event_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "incident.investigate", tenant_id)

    incident_repo = IncidentRepository(session)
    incident = await incident_repo.get(incident_id)
    if not incident or incident.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Incident not found")

    investigator = get_investigator(request)
    proposal = investigator.investigate(incident.evidence_json or {})
    incident.proposal_json = proposal
    await _record_incident_transition(
        session,
        tenant_id,
        incident,
        "INVESTIGATING",
        detail={"fix_type": proposal.get("fix_type"), "risk_level": proposal.get("risk_level")},
    )
    if getattr(investigator, "last_fallback", False):
        await audit.write_event(
            principal=principal.principal_id,
            action="incident.investigate.fallback",
            tenant_id=tenant_id,
            resource_type="incident",
            resource_id=incident_id,
        )
    await audit.write_event(
        principal=principal.principal_id,
        action="incident.investigate",
        tenant_id=tenant_id,
        resource_type="incident",
        resource_id=incident_id,
        detail={"fix_type": proposal.get("fix_type")},
    )
    await event_service.append(
        "IncidentUpdated",
        {"incident_id": incident_id, "status": "INVESTIGATING", "fix_type": proposal.get("fix_type")},
        tenant_id=tenant_id,
    )
    await session.commit()
    return IncidentResponse.model_validate(incident)


@router.post("/tenants/{tenant_id}/incidents/{incident_id}/create-pr", response_model=RemediationPRResponse)
async def create_remediation_pr_endpoint(
    request: Request,
    tenant_id: str,
    incident_id: str,
    config_store: ConfigStore = Depends(get_config_store),
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
    event_service: EventService = Depends(get_event_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "remediation.create_pr", tenant_id)

    incident_repo = IncidentRepository(session)
    pr_repo = RemediationPRRepository(session)
    incident = await incident_repo.get(incident_id)
    if not incident or incident.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Incident not found")

    proposal = incident.proposal_json or {}
    if not proposal:
        raise HTTPException(status_code=400, detail="Missing remediation proposal")

    decision = await evaluate_and_record_policy(
        request,
        principal,
        action="remediation.create_pr",
        tenant_id=tenant_id,
        payload={
            "fix_type": proposal.get("fix_type"),
            "risk_level": proposal.get("risk_level"),
            "paths": [f"remediations/incident-{incident_id}.md"],
        },
        policy_service=policy_service,
    )

    required_checks = []
    for obligation in decision.get("obligations", []):
        if isinstance(obligation, dict) and obligation.get("type") == "required_checks":
            required_checks.extend(obligation.get("checks") or [])

    result = create_remediation_pr(
        tenant_id,
        incident_id,
        proposal,
        config_store,
        request.app.state.adapter_registry,
        required_checks=required_checks or None,
    )
    pr = RemediationPR(
        pr_id=str(uuid4()),
        tenant_id=tenant_id,
        incident_id=incident_id,
        repo_url=config_store.get_tenant_spec(tenant_id).git["repo_url"],
        pr_url=result.pr_url,
        fix_type=proposal.get("fix_type"),
        risk_level=proposal.get("risk_level"),
        status=result.status,
        proposal_json=proposal,
        metadata_={"pr_number": result.pr_number},
    )
    await pr_repo.create(pr)
    await _record_incident_transition(
        session,
        tenant_id,
        incident,
        "PR_CREATED",
        detail={"pr_url": result.pr_url, "pr_status": result.status},
    )
    await audit.write_event(
        principal=principal.principal_id,
        action="incident.create_pr",
        tenant_id=tenant_id,
        resource_type="remediation_pr",
        resource_id=pr.pr_id,
        detail={"pr_url": result.pr_url},
    )
    await event_service.append(
        "RemediationPRCreated",
        {"incident_id": incident_id, "pr_id": pr.pr_id, "pr_url": pr.pr_url, "status": pr.status},
        tenant_id=tenant_id,
    )
    await session.commit()
    return RemediationPRResponse.model_validate(pr)


@router.get("/tenants/{tenant_id}/policy-decisions", response_model=List[PolicyDecisionResponse])
async def list_policy_decisions(
    request: Request,
    tenant_id: str,
    response: Response,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "policy.read", tenant_id)
    repo = PolicyDecisionRepository(session)
    decisions = await repo.list_for_tenant(tenant_id)
    total = len(decisions)
    paged = decisions[offset : offset + max(1, min(limit, 500))]
    response.headers["X-Total-Count"] = str(total)
    await audit.write_event(
        principal=principal.principal_id,
        action="policy.decisions.read",
        tenant_id=tenant_id,
        detail={"count": len(paged), "total": total, "limit": limit, "offset": offset},
    )
    await session.commit()
    return [PolicyDecisionResponse.model_validate(d) for d in paged]


@router.post("/tenants/{tenant_id}/drift/run")
async def run_drift(
    request: Request,
    tenant_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
    artifact_service: ArtifactService = Depends(get_artifact_service),
    config_store: ConfigStore = Depends(get_config_store),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "drift.run", tenant_id)
    await evaluate_and_record_policy(
        request,
        principal,
        action="drift.run",
        tenant_id=tenant_id,
        payload={},
        policy_service=policy_service,
    )
    registry = get_adapter_registry(request)
    detectors = {
        "terraform": TerraformDriftDetector(config_store, registry),
        "argocd": ArgoCDDriftDetector(config_store, registry),
        "posture": PostureDriftDetector(config_store),
    }
    manager = DriftManager(detectors, DriftRunRepository(session), artifact_service)
    results = await manager.run(tenant_id)
    await audit.write_event(
        principal=principal.principal_id,
        action="drift.run",
        tenant_id=tenant_id,
        detail={"count": len(results)},
    )
    await session.commit()
    return {"status": "completed", "results": [r.__dict__ for r in results]}


@router.get("/tenants/{tenant_id}/drift", response_model=DriftSummaryResponse)
async def get_drift_summary(
    request: Request,
    tenant_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "drift.read", tenant_id)
    repo = DriftRunRepository(session)
    runs = await repo.list_for_tenant(tenant_id)
    latest: dict[str, DriftRunResponse] = {}
    for run in runs:
        if run.detector_type not in latest:
            latest[run.detector_type] = DriftRunResponse.model_validate(run)
    await audit.write_event(
        principal=principal.principal_id,
        action="drift.read",
        tenant_id=tenant_id,
        detail={"detectors": list(latest.keys())},
    )
    await session.commit()
    return DriftSummaryResponse(tenant_id=tenant_id, detectors=latest)


@router.get("/tenants/{tenant_id}/drift/history", response_model=List[DriftRunResponse])
async def get_drift_history(
    request: Request,
    tenant_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "drift.read", tenant_id)
    repo = DriftRunRepository(session)
    runs = await repo.list_for_tenant(tenant_id)
    await audit.write_event(
        principal=principal.principal_id,
        action="drift.history.read",
        tenant_id=tenant_id,
        detail={"count": len(runs)},
    )
    await session.commit()
    return [DriftRunResponse.model_validate(r) for r in runs]


@router.post("/tenants/{tenant_id}/exports", response_model=ExportResponse)
async def create_export(
    request: Request,
    tenant_id: str,
    payload: ExportCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
    artifact_service: ArtifactService = Depends(get_artifact_service),
    event_service: EventService = Depends(get_event_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "export.create", tenant_id)
    await evaluate_and_record_policy(
        request,
        principal,
        action="export.create",
        tenant_id=tenant_id,
        payload={"start_time": payload.start_time, "end_time": payload.end_time},
        policy_service=policy_service,
    )
    export_repo = ExportBundleRepository(session)
    bundle = await export_repo.create(
        ExportBundle(
            export_id=str(uuid4()),
            tenant_id=tenant_id,
            status="QUEUED",
            filters=payload.model_dump(),
        )
    )
    celery_app.send_task(
        "export_tenant_bundle",
        args=[tenant_id, bundle.export_id, request.state.correlation_id],
    )
    await audit.write_event(
        principal=principal.principal_id,
        action="export.create",
        tenant_id=tenant_id,
        detail={"export_id": bundle.export_id},
    )
    await event_service.append(
        "ExportCreated",
        {"export_id": bundle.export_id, "status": bundle.status},
        tenant_id=tenant_id,
    )
    await session.commit()
    return ExportResponse.model_validate(bundle)


@router.get("/tenants/{tenant_id}/exports", response_model=List[ExportResponse])
async def list_exports(
    request: Request,
    tenant_id: str,
    response: Response,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "export.read", tenant_id)
    repo = ExportBundleRepository(session)
    exports = await repo.list_for_tenant(tenant_id)
    total = len(exports)
    paged = exports[offset : offset + max(1, min(limit, 200))]
    response.headers["X-Total-Count"] = str(total)
    await audit.write_event(
        principal=principal.principal_id,
        action="export.list",
        tenant_id=tenant_id,
        detail={"count": len(paged), "total": total, "limit": limit, "offset": offset},
    )
    await session.commit()
    return [ExportResponse.model_validate(e) for e in paged]


@router.get("/tenants/{tenant_id}/exports/{export_id}/download")
async def download_export(
    request: Request,
    tenant_id: str,
    export_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    artifact_service: ArtifactService = Depends(get_artifact_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "export.read", tenant_id)
    repo = ExportBundleRepository(session)
    bundle = await repo.get(export_id)
    if not bundle or bundle.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Export not found")
    if not bundle.artifact_ref:
        raise HTTPException(status_code=404, detail="Export artifact not ready")
    artifact = await ArtifactRefRepository(session).get(bundle.artifact_ref)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    content = await artifact_service.get_bytes(artifact)
    await audit.write_event(
        principal=principal.principal_id,
        action="export.download",
        tenant_id=tenant_id,
        detail={"export_id": export_id},
    )
    await session.commit()
    import base64
    return {
        "filename": f"tenant-export-{tenant_id}.zip",
        "content_base64": base64.b64encode(content).decode("utf-8"),
    }


@router.get("/tenants/{tenant_id}/metering", response_model=List[MeteringRollupResponse])
async def tenant_metering(
    request: Request,
    tenant_id: str,
    from_ts: str | None = None,
    to_ts: str | None = None,
    granularity: str = "daily",
    session: AsyncSession = Depends(get_db_session),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.read", tenant_id)
    from_dt = datetime.fromisoformat(from_ts) if from_ts else None
    to_dt = datetime.fromisoformat(to_ts) if to_ts else None
    rollups = await MeteringRollupRepository(session).list_for_tenant(
        tenant_id,
        granularity=granularity,
        period_from=from_dt,
        period_to=to_dt,
    )
    return [MeteringRollupResponse.model_validate(r) for r in rollups]


@router.post("/tenants/{tenant_id}/metering/collect")
async def collect_tenant_metering(
    request: Request,
    tenant_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.manage", tenant_id)
    collector = MeteringCollector(
        config_store=request.app.state.config_store,
        registry=request.app.state.adapter_registry,
        sample_repo=MeteringSampleRepository(session),
        rollup_repo=MeteringRollupRepository(session),
        audit_repo=AuditRepository(session),
        drift_repo=DriftRunRepository(session),
        runbook_repo=RunbookExecutionRepository(session),
        export_repo=ExportBundleRepository(session),
    )
    sample = await collector.collect(tenant_id)
    await collector.rollup(tenant_id, granularity="hourly")
    await collector.rollup(tenant_id, granularity="daily")
    await session.commit()
    return {"sample_id": sample.sample_id, "status": "collected"}


@router.get("/tenants/{tenant_id}/finops/summary", response_model=FinopsSummaryResponse)
async def tenant_finops_summary(
    request: Request,
    tenant_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.read", tenant_id)
    rollups = await MeteringRollupRepository(session).list_for_tenant(tenant_id, granularity="daily")
    totals: dict[str, float] = {}
    for roll in rollups[:30]:
        for key, value in (roll.metrics or {}).items():
            totals[key] = totals.get(key, 0.0) + float(value or 0)
    return FinopsSummaryResponse(tenant_id=tenant_id, totals=totals)


@router.get("/platform/metering/summary")
async def platform_metering_summary(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    principal: PrincipalContext = require_principal(request)
    require_platform_admin(principal)
    rollups = await MeteringRollupRepository(session).list_all(granularity="daily")
    totals: dict[str, float] = {}
    for roll in rollups:
        for key, value in (roll.metrics or {}).items():
            totals[key] = totals.get(key, 0.0) + float(value or 0)
    return {"totals": totals}


@router.get("/platform/version", response_model=PlatformVersionResponse)
async def platform_version(
    request: Request,
    config_store: ConfigStore = Depends(get_config_store),
):
    principal: PrincipalContext = require_principal(request)
    require_platform_admin(principal)
    platform_cfg = config_store.platform_config.model_dump()
    current = (platform_cfg.get("platform") or {}).get("version", "0.1.0")
    module_versions = {}
    for module in config_store.module_catalog.model_dump().get("modules", []):
        module_versions[module.get("id")] = module.get("version", "0.1.0")
    return PlatformVersionResponse(platform_version=current, api_version=request.app.version, module_versions=module_versions)


@router.get("/platform/upgrade/plan", response_model=UpgradePlanResponse)
async def platform_upgrade_plan(
    request: Request,
    target_version: str | None = None,
    config_store: ConfigStore = Depends(get_config_store),
):
    principal: PrincipalContext = require_principal(request)
    require_platform_admin(principal)
    platform_cfg = config_store.platform_config.model_dump()
    current = (platform_cfg.get("platform") or {}).get("version", "0.1.0")
    target = target_version or current
    required_module_updates = []
    for module in config_store.module_catalog.model_dump().get("modules", []):
        version = module.get("version", "0.1.0")
        if version != target:
            required_module_updates.append({"module_id": module.get("id"), "from": version, "to": target})
    return UpgradePlanResponse(
        target_version=target,
        requires_migrations=(target != current),
        required_module_updates=required_module_updates,
        breaking_changes=[],
    )


@router.post("/platform/upgrade/apply", response_model=UpgradeRunResponse)
async def platform_upgrade_apply(
    request: Request,
    target_version: str,
    session: AsyncSession = Depends(get_db_session),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
):
    principal: PrincipalContext = require_principal(request)
    require_platform_admin(principal)
    await evaluate_and_record_policy(
        request,
        principal,
        action="platform.upgrade.apply",
        payload={"target_version": target_version},
        policy_service=policy_service,
    )
    plan = {
        "target_version": target_version,
        "steps": ["alembic upgrade head", "sync platform-api", "sync platform-worker", "sync modules"],
    }
    run = UpgradeRun(
        run_id=str(uuid4()),
        target_version=target_version,
        status="COMPLETED",
        plan_json=plan,
        result_json={"status": "simulated"},
        correlation_id=request.state.correlation_id,
    )
    repo = UpgradeRunRepository(session)
    await repo.create(run)
    await session.commit()
    return UpgradeRunResponse.model_validate(run)


@router.get("/platform/dr/status", response_model=DRStatusResponse)
async def platform_dr_status(
    request: Request,
    config_store: ConfigStore = Depends(get_config_store),
):
    principal: PrincipalContext = require_principal(request)
    require_platform_admin(principal)
    cfg = config_store.platform_config.model_dump()
    dr = cfg.get("dr") or {}
    artifacts = cfg.get("artifacts") or {}
    return DRStatusResponse(
        enabled=bool(dr.get("enabled", True)),
        backup_mode=dr.get("backup_mode", "logical"),
        artifact_store=artifacts.get("store", "local"),
        export_ready=True,
    )


@router.post("/platform/dr/verify")
async def platform_dr_verify(
    request: Request,
    policy_service: PolicyDecisionService = Depends(get_policy_service),
):
    principal: PrincipalContext = require_principal(request)
    require_platform_admin(principal)
    await evaluate_and_record_policy(
        request,
        principal,
        action="platform.dr.verify",
        payload={"mode": "dry_run"},
        policy_service=policy_service,
    )
    return {"status": "verified", "mode": "dry_run"}


@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    request: Request,
    config_store: ConfigStore = Depends(get_config_store),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "product.read")
    products = []
    for product in config_store.products.values():
        products.append(
            ProductResponse(
                id=product.id,
                name=product.name,
                description=product.description,
                required_modules=product.required_modules,
                required_capabilities=product.required_capabilities,
                finops_tags=product.finops_tags,
                enabled=False,
            )
        )
    return products


@router.get("/runbooks", response_model=List[RunbookSummaryResponse])
async def list_runbooks(
    request: Request,
    config_store: ConfigStore = Depends(get_config_store),
):
    principal: PrincipalContext = require_principal(request)
    require_platform_admin(principal)
    runbooks = []
    for item in (config_store.platform_config.runbooks or []):
        runbooks.append(
            RunbookSummaryResponse(
                id=item.get("id", ""),
                description=item.get("description", ""),
                required_role=item.get("required_role"),
                steps=item.get("steps") or [],
            )
        )
    return runbooks


@router.post("/tenants/{tenant_id}/products/{product_id}/enable", response_model=ProductToggleResponse)
async def enable_product(
    request: Request,
    tenant_id: str,
    product_id: str,
    config_store: ConfigStore = Depends(get_config_store),
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
    event_service: EventService = Depends(get_event_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "product.manage", tenant_id)
    product = config_store.get_product(product_id)
    if product.allowed_tenants and tenant_id not in product.allowed_tenants:
        raise HTTPException(status_code=403, detail="Product not allowed for tenant")
    await evaluate_and_record_policy(
        request,
        principal,
        action="product.enable",
        tenant_id=tenant_id,
        payload={"product_id": product_id, "modules": product.required_modules},
        policy_service=policy_service,
    )
    tenant_repo = TenantRepository(session)
    tenant = await tenant_repo.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    meta = dict(tenant.metadata_ or {})
    enabled = set((meta.get("enabled_products") or []))
    enabled.add(product_id)
    meta["enabled_products"] = sorted(enabled)
    await tenant_repo.update_metadata(tenant_id, meta)

    tenant_spec = config_store.get_tenant_spec(tenant_id).model_dump()
    provider = config_store.get_provider_profile(tenant_spec["provider_profile_id"]).model_dump()
    capability_union = provider.get("capabilities", {})
    for key, expected in product.required_capabilities.items():
        if capability_union.get(key) != expected:
            raise HTTPException(status_code=400, detail=f"Missing required capability: {key}")

    module_map = {m.get("id"): m for m in config_store.module_catalog.model_dump().get("modules", [])}
    gitops = request.app.state.adapter_registry.gitops()
    for module_id in product.required_modules:
        module = module_map.get(module_id)
        if not module:
            continue
        if module.get("type") == "INSTALL":
            app = module.get("install", {}).get("argo_application_template")
            if app:
                gitops.apply_application(app)

    await audit.write_event(
        principal=principal.principal_id,
        action="product.enable",
        tenant_id=tenant_id,
        detail={"product_id": product_id},
    )
    await event_service.append(
        "ProductEnabled",
        {"product_id": product_id, "modules": product.required_modules},
        tenant_id=tenant_id,
    )
    await session.commit()
    return ProductToggleResponse(tenant_id=tenant_id, product_id=product_id, status="enabled", modules=product.required_modules)


@router.post("/tenants/{tenant_id}/products/{product_id}/disable", response_model=ProductToggleResponse)
async def disable_product(
    request: Request,
    tenant_id: str,
    product_id: str,
    config_store: ConfigStore = Depends(get_config_store),
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
    event_service: EventService = Depends(get_event_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "product.manage", tenant_id)
    product = config_store.get_product(product_id)
    await evaluate_and_record_policy(
        request,
        principal,
        action="product.disable",
        tenant_id=tenant_id,
        payload={"product_id": product_id},
        policy_service=policy_service,
    )
    tenant_repo = TenantRepository(session)
    tenant = await tenant_repo.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    meta = dict(tenant.metadata_ or {})
    enabled = set((meta.get("enabled_products") or []))
    enabled.discard(product_id)
    meta["enabled_products"] = sorted(enabled)
    await tenant_repo.update_metadata(tenant_id, meta)
    await audit.write_event(
        principal=principal.principal_id,
        action="product.disable",
        tenant_id=tenant_id,
        detail={"product_id": product_id},
    )
    await event_service.append(
        "ProductDisabled",
        {"product_id": product_id},
        tenant_id=tenant_id,
    )
    await session.commit()
    return ProductToggleResponse(tenant_id=tenant_id, product_id=product_id, status="disabled", modules=product.required_modules)


@router.post("/tenants/{tenant_id}/access/requests", response_model=AccessRequestResponse)
async def create_access_request(
    request: Request,
    tenant_id: str,
    payload: AccessRequestCreate,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
    event_service: EventService = Depends(get_event_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "access.request", tenant_id)
    await evaluate_and_record_policy(
        request,
        principal,
        action="access.request.create",
        tenant_id=tenant_id,
        payload={"requested_role": payload.requested_role, "ticket_id": payload.ticket_id},
        policy_service=policy_service,
    )
    req = AccessRequest(
        request_id=str(uuid4()),
        tenant_id=tenant_id,
        principal=principal.principal_id,
        requested_role=payload.requested_role,
        status="PENDING",
        metadata_={"ticket_id": payload.ticket_id, "justification": payload.justification},
    )
    created = await AccessRequestRepository(session).create(req)
    await audit.write_event(
        principal=principal.principal_id,
        action="access.request.create",
        tenant_id=tenant_id,
        resource_type="access_request",
        resource_id=req.request_id,
    )
    await event_service.append(
        "AccessRequestCreated",
        {"request_id": req.request_id, "requested_role": req.requested_role, "principal": req.principal},
        tenant_id=tenant_id,
    )
    await session.commit()
    return AccessRequestResponse.model_validate(created)


@router.get("/tenants/{tenant_id}/access/requests", response_model=List[AccessRequestResponse])
async def list_access_requests(
    request: Request,
    tenant_id: str,
    response: Response,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "scaffold.create", tenant_id)
    rows = await AccessRequestRepository(session).list_for_tenant(tenant_id)
    total = len(rows)
    paged = rows[offset : offset + max(1, min(limit, 200))]
    response.headers["X-Total-Count"] = str(total)
    return [AccessRequestResponse.model_validate(r) for r in paged]


@router.post("/tenants/{tenant_id}/access/requests/{request_id}/approve", response_model=AccessRequestResponse)
async def approve_access_request(
    request: Request,
    tenant_id: str,
    request_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
    event_service: EventService = Depends(get_event_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "service.promote", tenant_id)
    repo = AccessRequestRepository(session)
    row = await repo.get(request_id)
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Access request not found")
    await evaluate_and_record_policy(
        request,
        principal,
        action="access.request.approve",
        tenant_id=tenant_id,
        payload={"requested_role": row.requested_role, "principal": row.principal},
        policy_service=policy_service,
    )
    row.status = "APPROVED"
    row.approver = principal.principal_id
    row.decided_at = datetime.utcnow()
    await repo.update(row)
    await audit.write_event(
        principal=principal.principal_id,
        action="access.request.approve",
        tenant_id=tenant_id,
        resource_type="access_request",
        resource_id=request_id,
    )
    await event_service.append(
        "AccessRequestApproved",
        {"request_id": request_id, "principal": row.principal, "role": row.requested_role},
        tenant_id=tenant_id,
    )
    await session.commit()
    return AccessRequestResponse.model_validate(row)


@router.post("/tenants/{tenant_id}/access/requests/{request_id}/deny", response_model=AccessRequestResponse)
async def deny_access_request(
    request: Request,
    tenant_id: str,
    request_id: str,
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    event_service: EventService = Depends(get_event_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.manage", tenant_id)
    repo = AccessRequestRepository(session)
    row = await repo.get(request_id)
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Access request not found")
    row.status = "DENIED"
    row.approver = principal.principal_id
    row.decided_at = datetime.utcnow()
    await repo.update(row)
    await audit.write_event(
        principal=principal.principal_id,
        action="access.request.deny",
        tenant_id=tenant_id,
        resource_type="access_request",
        resource_id=request_id,
    )
    await event_service.append(
        "AccessRequestDenied",
        {"request_id": request_id, "principal": row.principal, "role": row.requested_role},
        tenant_id=tenant_id,
    )
    await session.commit()
    return AccessRequestResponse.model_validate(row)


@router.post("/tenants/{tenant_id}/scaffold", response_model=ScaffoldResponse)
async def scaffold_service(
    request: Request,
    tenant_id: str,
    payload: ScaffoldRequest,
    config_store: ConfigStore = Depends(get_config_store),
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.manage", tenant_id)
    await evaluate_and_record_policy(
        request,
        principal,
        action="scaffold.service",
        tenant_id=tenant_id,
        payload={"template_id": payload.template_id, "parameters": payload.parameters},
        policy_service=policy_service,
    )
    scaffolder = ScaffolderService(request.app.state.adapter_registry)
    result = scaffolder.scaffold(tenant_id, payload.template_id, payload.parameters)
    await audit.write_event(
        principal=principal.principal_id,
        action="scaffold.service",
        tenant_id=tenant_id,
        detail={"template_id": payload.template_id, "repo_url": result.repo_url},
    )
    await session.commit()
    return ScaffoldResponse(
        tenant_id=tenant_id,
        service_id=result.service_id,
        repo_url=result.repo_url,
        pr_url=result.pr_url,
        argo_apps=result.argo_apps,
    )


@router.post("/tenants/{tenant_id}/services/{service_id}/promote", response_model=PromotionResponse)
async def promote_service(
    request: Request,
    tenant_id: str,
    service_id: str,
    from_env: str,
    to_env: str,
    image_tag: str = "latest",
    config_store: ConfigStore = Depends(get_config_store),
    session: AsyncSession = Depends(get_db_session),
    audit: AuditService = Depends(get_audit_service),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
    event_service: EventService = Depends(get_event_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.manage", tenant_id)
    decision = await evaluate_and_record_policy(
        request,
        principal,
        action="service.promote",
        tenant_id=tenant_id,
        payload={"service_id": service_id, "from_env": from_env, "to_env": to_env, "risk_level": "high" if to_env == "prod" else "medium"},
        policy_service=policy_service,
    )
    checks: list[str] = []
    for ob in decision.get("obligations", []):
        if isinstance(ob, dict) and ob.get("type") == "required_checks":
            checks.extend(ob.get("checks") or [])

    tenant = config_store.get_tenant_spec(tenant_id)
    controller = PromotionController(request.app.state.adapter_registry)
    result = controller.create_promotion_pr(
        repo_url=tenant.git["repo_url"],
        default_branch=tenant.git.get("default_branch", "main"),
        service_id=service_id,
        from_env=from_env,
        to_env=to_env,
        image_tag=image_tag,
        required_checks=checks or None,
    )
    promotion = Promotion(
        promotion_id=str(uuid4()),
        tenant_id=tenant_id,
        service_id=service_id,
        from_env=from_env,
        to_env=to_env,
        pr_url=result.pr_url,
        status=result.status,
        metadata_={"image_tag": image_tag},
    )
    await PromotionRepository(session).create(promotion)
    await audit.write_event(
        principal=principal.principal_id,
        action="service.promote",
        tenant_id=tenant_id,
        resource_type="promotion",
        resource_id=promotion.promotion_id,
        detail={"pr_url": result.pr_url},
    )
    await event_service.append(
        "PromotionCreated",
        {"promotion_id": promotion.promotion_id, "service_id": service_id, "pr_url": result.pr_url, "status": result.status},
        tenant_id=tenant_id,
    )
    await session.commit()
    return PromotionResponse.model_validate(promotion)


@router.get("/tenants/{tenant_id}/services/{service_id}/promotions", response_model=List[PromotionResponse])
async def list_promotions(
    request: Request,
    tenant_id: str,
    service_id: str,
    response: Response,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.read", tenant_id)
    rows = await PromotionRepository(session).list_for_service(tenant_id, service_id)
    total = len(rows)
    paged = rows[offset : offset + max(1, min(limit, 200))]
    response.headers["X-Total-Count"] = str(total)
    return [PromotionResponse.model_validate(r) for r in paged]


@router.get("/aiops/investigator/health")
async def investigator_health(request: Request):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "incident.investigate")
    investigator = get_investigator(request)
    return investigator.health()


@router.get("/search", response_model=SearchResponse)
async def global_search(
    request: Request,
    q: str,
    limit: int = 25,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
    config_store: ConfigStore = Depends(get_config_store),
):
    principal: PrincipalContext = require_principal(request)
    query = q.strip().lower()
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")

    tenant_repo = TenantRepository(session)
    incident_repo = IncidentRepository(session)
    event_repo = EventRepository(session)
    if principal.is_platform_admin():
        tenants = await tenant_repo.list()
        tenant_ids = [t.tenant_id for t in tenants]
    else:
        tenant_ids = list(principal.tenant_roles.keys())
        tenants = await tenant_repo.list(tenant_ids=tenant_ids)

    items: list[SearchItemResponse] = []
    for tenant in tenants:
        if query in tenant.tenant_id.lower() or query in (tenant.display_name or "").lower():
            items.append(
                SearchItemResponse(
                    kind="tenant",
                    id=tenant.tenant_id,
                    title=tenant.display_name,
                    tenant_id=tenant.tenant_id,
                    status=tenant.status,
                )
            )
    for tenant_id in tenant_ids:
        incidents = await incident_repo.list_for_tenant(tenant_id)
        for incident in incidents:
            if (
                query in incident.incident_id.lower()
                or query in (incident.alert_name or "").lower()
                or query in (incident.service_id or "").lower()
            ):
                items.append(
                    SearchItemResponse(
                        kind="incident",
                        id=incident.incident_id,
                        title=incident.alert_name,
                        tenant_id=tenant_id,
                        status=incident.status,
                        metadata={"service_id": incident.service_id},
                    )
                )
    for tenant_id in tenant_ids:
        events = await event_repo.list(tenant_id=tenant_id)
        for event in events[:100]:
            if query in event.type.lower():
                items.append(
                    SearchItemResponse(
                        kind="event",
                        id=event.event_id,
                        title=event.type,
                        tenant_id=tenant_id,
                        status=event.status,
                    )
                )
    for product in config_store.products.values():
        if query in product.id.lower() or query in product.name.lower() or query in product.description.lower():
            items.append(
                SearchItemResponse(
                    kind="product",
                    id=product.id,
                    title=product.name,
                    metadata={"description": product.description},
                )
            )
    for runbook in (config_store.platform_config.runbooks or []):
        runbook_id = str(runbook.get("id", ""))
        runbook_desc = str(runbook.get("description", ""))
        if query in runbook_id.lower() or query in runbook_desc.lower():
            items.append(
                SearchItemResponse(
                    kind="runbook",
                    id=runbook_id,
                    title=runbook_desc or runbook_id,
                    metadata={"required_role": runbook.get("required_role")},
                )
            )
    total = len(items)
    paged = items[offset : offset + max(1, min(limit, 100))]
    return SearchResponse(query=q, total=total, items=paged)


@router.get("/events", response_model=List[EventResponse])
async def list_events(
    request: Request,
    response: Response,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    principal: PrincipalContext = require_principal(request)
    require_platform_admin(principal)
    rows = await EventRepository(session).list()
    total = len(rows)
    paged = rows[offset : offset + max(1, min(limit, 500))]
    response.headers["X-Total-Count"] = str(total)
    return [EventResponse.model_validate(row) for row in paged]


@router.get("/tenants/{tenant_id}/events", response_model=List[EventResponse])
async def list_tenant_events(
    request: Request,
    tenant_id: str,
    response: Response,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.read", tenant_id)
    rows = await EventRepository(session).list(tenant_id=tenant_id)
    total = len(rows)
    paged = rows[offset : offset + max(1, min(limit, 500))]
    response.headers["X-Total-Count"] = str(total)
    return [EventResponse.model_validate(row) for row in paged]


@router.post("/tenants/{tenant_id}/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    request: Request,
    tenant_id: str,
    payload: SubscriptionCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.manage", tenant_id)
    await evaluate_and_record_policy(
        request,
        principal,
        action="integrations.webhook.subscribe",
        tenant_id=tenant_id,
        payload={"event_types": payload.event_types, "destination_ref": payload.destination_ref},
        policy_service=policy_service,
    )
    created = await SubscriptionRepository(session).create(
        Subscription(
            subscription_id=str(uuid4()),
            tenant_id=tenant_id,
            event_types=payload.event_types,
            destination_ref=payload.destination_ref,
            headers_ref=payload.headers_ref,
            status="ACTIVE",
            metadata_={},
        )
    )
    await session.commit()
    return SubscriptionResponse.model_validate(created)


@router.get("/tenants/{tenant_id}/subscriptions", response_model=List[SubscriptionResponse])
async def list_subscriptions(
    request: Request,
    tenant_id: str,
    response: Response,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.read", tenant_id)
    rows = await SubscriptionRepository(session).list_for_tenant(tenant_id)
    total = len(rows)
    paged = rows[offset : offset + max(1, min(limit, 200))]
    response.headers["X-Total-Count"] = str(total)
    return [SubscriptionResponse.model_validate(row) for row in paged]


@router.delete("/tenants/{tenant_id}/subscriptions/{subscription_id}", response_model=MessageResponse)
async def delete_subscription(
    request: Request,
    tenant_id: str,
    subscription_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "tenant.manage", tenant_id)
    repo = SubscriptionRepository(session)
    row = await repo.get(subscription_id)
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Subscription not found")
    row.status = "DISABLED"
    await repo.update(row)
    await session.commit()
    return MessageResponse(status="deleted", detail={"subscription_id": subscription_id})


@router.post("/tenants/{tenant_id}/incidents/{incident_id}/transition", response_model=IncidentTransitionResponse)
async def transition_incident(
    request: Request,
    tenant_id: str,
    incident_id: str,
    payload: IncidentTransitionRequest,
    session: AsyncSession = Depends(get_db_session),
    event_service: EventService = Depends(get_event_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "incident.investigate", tenant_id)
    incident_repo = IncidentRepository(session)
    incident = await incident_repo.get(incident_id)
    if not incident or incident.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    transition = await _record_incident_transition(
        session,
        tenant_id,
        incident,
        payload.to_status,
        detail=payload.detail,
    )
    await event_service.append(
        "IncidentUpdated",
        {"incident_id": incident_id, "status": payload.to_status},
        tenant_id=tenant_id,
    )
    await session.commit()
    return IncidentTransitionResponse.model_validate(transition)


@router.get("/tenants/{tenant_id}/incidents/{incident_id}/timeline", response_model=List[IncidentTransitionResponse])
async def incident_timeline(
    request: Request,
    tenant_id: str,
    incident_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "incident.read", tenant_id)
    incident = await IncidentRepository(session).get(incident_id)
    if not incident or incident.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    rows = await IncidentTransitionRepository(session).list_for_incident(incident_id)
    return [IncidentTransitionResponse.model_validate(row) for row in rows]


@router.post("/tenants/{tenant_id}/incidents/{incident_id}/notify", response_model=MessageResponse)
async def incident_notify(
    request: Request,
    tenant_id: str,
    incident_id: str,
    payload: dict[str, Any] | None = None,
    session: AsyncSession = Depends(get_db_session),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "incident.investigate", tenant_id)
    incident = await IncidentRepository(session).get(incident_id)
    if not incident or incident.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    body = payload or {}
    await evaluate_and_record_policy(
        request,
        principal,
        action="incident.notify",
        tenant_id=tenant_id,
        payload=body,
        policy_service=policy_service,
    )
    default_channel = ((request.app.state.config_store.platform_config.integrations or {}).get("default_channel")) or "alerts"
    channel = body.get("channel") or default_channel
    msg = body.get("message") or f"Incident {incident_id} ({incident.alert_name}) status={incident.status}"
    ref = request.app.state.adapter_registry.messaging().post_message(
        channel=channel,
        message=msg,
        metadata={"tenant_id": tenant_id, "incident_id": incident_id},
    )
    await AuditService(AuditRepository(session)).write_event(
        principal=principal.principal_id,
        action="incident.notify",
        tenant_id=tenant_id,
        resource_type="incident",
        resource_id=incident_id,
        detail={"channel": channel, "message_id": ref.message_id},
    )
    await session.commit()
    return MessageResponse(status="sent", detail={"channel": channel, "message_id": ref.message_id})


@router.post("/tenants/{tenant_id}/incidents/{incident_id}/create-ticket", response_model=MessageResponse)
async def incident_create_ticket(
    request: Request,
    tenant_id: str,
    incident_id: str,
    payload: dict[str, Any] | None = None,
    session: AsyncSession = Depends(get_db_session),
    policy_service: PolicyDecisionService = Depends(get_policy_service),
):
    principal: PrincipalContext = require_principal(request)
    require_permission(request, principal, "incident.investigate", tenant_id)
    incident = await IncidentRepository(session).get(incident_id)
    if not incident or incident.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    body = payload or {}
    await evaluate_and_record_policy(
        request,
        principal,
        action="incident.create_ticket",
        tenant_id=tenant_id,
        payload=body,
        policy_service=policy_service,
    )
    ticket = request.app.state.adapter_registry.ticketing().create_ticket(
        title=body.get("title") or f"[{tenant_id}] {incident.alert_name}",
        description=body.get("description") or f"Incident {incident_id} status={incident.status}",
        labels=["tenant:" + tenant_id, "incident:" + incident_id],
        metadata={"tenant_id": tenant_id, "incident_id": incident_id},
    )
    await AuditService(AuditRepository(session)).write_event(
        principal=principal.principal_id,
        action="incident.create_ticket",
        tenant_id=tenant_id,
        resource_type="incident",
        resource_id=incident_id,
        detail={"ticket_id": ticket.ticket_id, "ticket_url": ticket.url},
    )
    await session.commit()
    return MessageResponse(
        status="created",
        detail={"ticket_id": ticket.ticket_id, "ticket_url": ticket.url},
    )
