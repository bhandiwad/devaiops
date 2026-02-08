from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class TenantCreateRequest(BaseModel):
    tenant_id: str
    display_name: str
    mode: str
    provider_profile_id: str


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    tenant_id: str
    display_name: str
    mode: str
    provider_profile_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] | None = Field(default=None, alias="metadata_")


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    tenant_id: Optional[str] = None
    principal: str
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    correlation_id: Optional[str] = None
    detail: Dict[str, Any]
    created_at: datetime


class TenantStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    history_id: str
    tenant_id: str
    from_status: Optional[str] = None
    to_status: str
    error_detail: Dict[str, Any]
    occurred_at: datetime


class TenantStatusResponse(BaseModel):
    tenant_id: str
    status: str
    history: list[TenantStatusHistoryResponse]


class ModulePlanItemResponse(BaseModel):
    module_id: str
    module_type: str
    action: str
    app_spec: Optional[Dict[str, Any]] = None
    integration_ref: Optional[Dict[str, Any]] = None
    errors: list[str]


class ModulePlanResponse(BaseModel):
    items: list[ModulePlanItemResponse]
    errors: list[str]


class IncidentCreateRequest(BaseModel):
    alert_name: str
    service_id: Optional[str] = None
    alert: Dict[str, Any] = Field(default_factory=dict)


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    incident_id: str
    tenant_id: str
    service_id: Optional[str] = None
    alert_name: str
    status: str
    alert_json: Dict[str, Any] = Field(default_factory=dict)
    evidence_json: Dict[str, Any] = Field(default_factory=dict)
    proposal_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class EvidenceResponse(BaseModel):
    incident_id: str
    evidence: Dict[str, Any]


class RemediationPRResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pr_id: str
    incident_id: Optional[str] = None
    tenant_id: str
    repo_url: str
    pr_url: str
    fix_type: str
    risk_level: str
    status: str
    proposal_json: Dict[str, Any]


class PolicyDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision_id: str
    tenant_id: Optional[str] = None
    action: str
    allow: bool
    reasons: list[Any]
    obligations: list[Any]
    principal: Dict[str, Any]
    correlation_id: Optional[str] = None
    created_at: datetime


class DriftRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    tenant_id: str
    detector_type: str
    status: str
    summary: Dict[str, Any]
    artifact_ref: Optional[str] = None
    correlation_id: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None


class DriftSummaryResponse(BaseModel):
    tenant_id: str
    detectors: Dict[str, DriftRunResponse]


class ExportCreateRequest(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    export_id: str
    tenant_id: str
    status: str
    artifact_ref: Optional[str] = None
    filters: Dict[str, Any]
    created_at: datetime
    finished_at: Optional[datetime] = None


class MeteringSampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sample_id: str
    tenant_id: str
    captured_at: datetime
    metrics: Dict[str, Any]


class MeteringRollupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rollup_id: str
    tenant_id: str
    period_start: datetime
    period_end: datetime
    granularity: str
    metrics: Dict[str, Any]


class FinopsSummaryResponse(BaseModel):
    tenant_id: str
    totals: Dict[str, float]


class PlatformVersionResponse(BaseModel):
    platform_version: str
    api_version: str
    module_versions: Dict[str, str]


class UpgradePlanResponse(BaseModel):
    target_version: str
    requires_migrations: bool
    required_module_updates: list[Dict[str, Any]]
    breaking_changes: list[str]


class UpgradeRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    target_version: str
    status: str
    plan_json: Dict[str, Any]
    result_json: Dict[str, Any]
    correlation_id: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None


class DRStatusResponse(BaseModel):
    enabled: bool
    backup_mode: str
    artifact_store: str
    export_ready: bool


class ScaffoldRequest(BaseModel):
    template_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ScaffoldResponse(BaseModel):
    tenant_id: str
    service_id: str
    repo_url: str
    pr_url: Optional[str] = None
    argo_apps: list[str] = Field(default_factory=list)


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    required_modules: list[str]
    required_capabilities: Dict[str, Any]
    finops_tags: Optional[Dict[str, Any]] = None
    enabled: bool = False


class ProductToggleResponse(BaseModel):
    tenant_id: str
    product_id: str
    status: str
    modules: list[str]


class PromotionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    promotion_id: str
    tenant_id: str
    service_id: str
    from_env: str
    to_env: str
    pr_url: Optional[str] = None
    status: str
    metadata: Dict[str, Any] | None = Field(default=None, alias="metadata_")
    created_at: datetime


class AccessRequestCreate(BaseModel):
    requested_role: str
    ticket_id: Optional[str] = None
    justification: Optional[str] = None


class AccessRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: str
    tenant_id: str
    principal: str
    requested_role: str
    status: str
    approver: Optional[str] = None
    metadata: Dict[str, Any] | None = Field(default=None, alias="metadata_")
    created_at: datetime
    decided_at: Optional[datetime] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    correlation_id: Optional[str] = None
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class MessageResponse(BaseModel):
    status: str
    detail: Dict[str, Any] = Field(default_factory=dict)


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    tenant_id: Optional[str] = None
    type: str
    payload: Dict[str, Any]
    status: str
    created_at: datetime
    dispatched_at: Optional[datetime] = None


class SubscriptionCreateRequest(BaseModel):
    event_types: list[str] = Field(default_factory=list)
    destination_ref: str
    headers_ref: Optional[str] = None


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subscription_id: str
    tenant_id: Optional[str] = None
    event_types: list[str]
    destination_ref: str
    headers_ref: Optional[str] = None
    status: str
    metadata: Dict[str, Any] | None = Field(default=None, alias="metadata_")
    created_at: datetime


class IncidentTransitionRequest(BaseModel):
    to_status: str
    detail: Dict[str, Any] = Field(default_factory=dict)


class IncidentTransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transition_id: str
    incident_id: str
    tenant_id: str
    from_status: Optional[str] = None
    to_status: str
    detail: Dict[str, Any]
    created_at: datetime


class SearchItemResponse(BaseModel):
    kind: str
    id: str
    title: str
    tenant_id: Optional[str] = None
    status: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    total: int
    items: list[SearchItemResponse]


class OnboardingProgressResponse(BaseModel):
    tenant_id: str
    status: str
    history: list[TenantStatusHistoryResponse]
    recent_audit: list[AuditEventResponse]


class RunbookSummaryResponse(BaseModel):
    id: str
    description: str
    required_role: Optional[str] = None
    steps: list[Dict[str, Any]] = Field(default_factory=list)


class DeploymentStatusResponse(BaseModel):
    tenant_id: str
    service_id: str
    app_ref: str
    status: Dict[str, Any] = Field(default_factory=dict)
