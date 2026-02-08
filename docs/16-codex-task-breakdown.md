
# Codex task breakdown (modular-first)

## EPIC 0: Scaffolding
- Repo structure
- CI linting for configs and schemas

## EPIC 1: Config system
- Config loader (git or fs)
- Schema validation and error reporting
- Hot reload + impact analysis

## EPIC 2: Adapter framework
- Python interfaces (ABCs/Protocols)
- Plugin loader (import paths from config)
- Adapter registry and dependency injection

## EPIC 3: Identity + RBAC
- Keycloak JWT validation
- /me endpoint and tenant role parsing
- RBAC middleware and permission checks
- Audit event emission

## EPIC 4: Tenant pipeline (BYOC + PROVISIONED)
- TenantSpec ingestion + validation
- Capability probe step (pluggable)
- Bootstrap step (RegistrarAdapter)
- Argo registration + tenant project isolation
- Tenant base GitOps application creation

## EPIC 5: Module engine
- Parse ModuleCatalog and ModuleDescriptors
- For each enabled module:
  - validate requirements/capabilities
  - INSTALL: generate Argo app spec + apply
  - INTEGRATE: validate adapter config presence

## EPIC 6: Integrations via adapters
- GitOpsAdapter (Argo) integration
- SecretsAdapter (Vault) integration + OIDC
- RegistryAdapter (Harbor) integration
- ObservabilityAdapter (Grafana/Loki/Prometheus) integration with tenant scoping
- GitProviderAdapter integration

## EPIC 7: AIOps PR autopilot
- EvidencePack collector (tenant scoped)
- Investigator (strict JSON output)
- PR bot using GitProviderAdapter
- Gating hooks + status tracking

## EPIC 8: Backstage (primary UI)
- Backstage app config (Keycloak auth)
- Plugins: Tenant Console, Services, Incidents, Access, Audit, Observability, Secrets
- All plugins call Platform API only

## EPIC 9: Unified CLI aiopsctl
- Keycloak device login
- Command groups mirror API resources
- RBAC respected

## EPIC 10: Postgres storage layer
- Implement DDL
- Repositories/DAOs
- Append-only audit event writer
