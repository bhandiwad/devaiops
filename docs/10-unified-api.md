
# Unified Platform API

## Principles
- Backstage and aiopsctl call Platform API only.
- Platform API enforces RBAC and writes audit events.
- Platform API uses adapters and module descriptors; handler code never calls vendor SDKs directly.

## Core resources
- ProviderProfile
- ModuleDescriptor
- Tenant
- Cluster
- Service
- Deployment
- Incident
- RemediationPR
- AccessBinding
- AuditEvent

## Endpoint skeleton (minimum)
Identity:
- GET /me

Config:
- GET /provider-profiles
- GET /modules
- (Optional) POST /provider-profiles (admin)
- (Optional) POST /modules (admin)

Tenants:
- POST /tenants
- GET /tenants
- GET /tenants/{tenant_id}
- POST /tenants/{tenant_id}/upgrade
- DELETE /tenants/{tenant_id}

Services & Deployments:
- POST /tenants/{tenant_id}/services
- GET /tenants/{tenant_id}/services
- GET /tenants/{tenant_id}/services/{service_id}
- GET /tenants/{tenant_id}/services/{service_id}/deployments
- POST /tenants/{tenant_id}/services/{service_id}/rollback

Observability:
- GET /tenants/{tenant_id}/services/{service_id}/observability/summary
- POST /tenants/{tenant_id}/logs/query
- POST /tenants/{tenant_id}/metrics/query
- GET /tenants/{tenant_id}/dashboards

Secrets (metadata-first):
- GET /tenants/{tenant_id}/secrets
- GET /tenants/{tenant_id}/secrets/{secret_id}/metadata

Incidents & AIOps:
- POST /tenants/{tenant_id}/incidents (alert ingest)
- GET /tenants/{tenant_id}/incidents/{incident_id}
- POST /tenants/{tenant_id}/incidents/{incident_id}/evidence
- POST /tenants/{tenant_id}/incidents/{incident_id}/investigate
- POST /tenants/{tenant_id}/incidents/{incident_id}/create-pr

Access & Audit:
- POST /tenants/{tenant_id}/access/bindings
- GET /tenants/{tenant_id}/access/bindings
- GET /tenants/{tenant_id}/audit
