from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ConfigSources(BaseModel):
    provider_profiles_path: str
    tenant_specs_path: str
    products_path: str | None = None


class DatabaseConfig(BaseModel):
    url: str


class TenantDefaults(BaseModel):
    default_status: str


class WorkerConfig(BaseModel):
    broker_url: str
    result_backend: str | None = None


class PlatformConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    modules: Dict[str, Any]
    identity: Dict[str, Any]
    adapters: Dict[str, Any]
    rbac: Dict[str, Any]
    gitops: Optional[Dict[str, Any]] = None
    git_provider: Optional[Dict[str, Any]] = None
    observability: Optional[Dict[str, Any]] = None
    aiops: Optional[Dict[str, Any]] = None
    artifacts: Optional[Dict[str, Any]] = None
    provisioning: Optional[Dict[str, Any]] = None
    runbooks: Optional[list[Dict[str, Any]]] = None
    policy: Optional[Dict[str, Any]] = None
    drift: Optional[Dict[str, Any]] = None
    rate_limit: Optional[Dict[str, Any]] = None
    idempotency: Optional[Dict[str, Any]] = None
    metering: Optional[Dict[str, Any]] = None
    platform: Optional[Dict[str, Any]] = None
    dr: Optional[Dict[str, Any]] = None
    tracing: Optional[Dict[str, Any]] = None
    integrations: Optional[Dict[str, Any]] = None
    config_repo: Optional[Dict[str, Any]] = None
    config_sources: Optional[ConfigSources] = None
    database: Optional[DatabaseConfig] = None
    tenants: Optional[TenantDefaults] = None
    worker: Optional[WorkerConfig] = None


class ModuleCatalog(BaseModel):
    model_config = ConfigDict(extra="allow")

    modules: List[Dict[str, Any]]


class ProviderProfile(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    capabilities: Dict[str, Any]
    defaults: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None
    auth_modes: Optional[Dict[str, Any]] = None
    module_overrides: Optional[Dict[str, Any]] = None


class TenantSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    tenant_id: str
    mode: str
    provider_profile_id: str
    git: Dict[str, Any]
    display_name: Optional[str] = None
    provisioner_ref: Optional[Dict[str, Any]] = None
    k8s_access_ref: Optional[Dict[str, Any]] = None
    modules: Optional[Dict[str, Any]] = None
    approval_policy: Optional[Dict[str, Any]] = None
    remediation_allowlist: Optional[List[str]] = None
    observability: Optional[Dict[str, Any]] = None
    policies: Optional[Dict[str, Any]] = None


class ProductDescriptor(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    description: str
    required_modules: list[str] = Field(default_factory=list)
    required_capabilities: Dict[str, Any] = Field(default_factory=dict)
    finops_tags: Optional[Dict[str, Any]] = None
    allowed_tenants: Optional[list[str]] = None
