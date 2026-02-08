
# Modularity model

## 1) External configuration layers
1) PlatformConfig: global defaults, enabled modules, adapter bindings, RBAC model
2) ProviderProfile: environment capabilities + defaults + integration auth modes
3) ModuleCatalog: list of modules, install/integrate definitions, requirements
4) TenantSpec: tenant settings, onboarding mode, module selection, allowlists, approval policy

## 2) Adapter plugins
Adapters isolate differences in:
- identity (Keycloak)
- provisioning (Terraform runner, BYOC)
- Kubernetes bootstrap and inventory
- GitOps (Argo CD)
- secrets (Vault)
- registry (Harbor)
- observability (Prometheus/Grafana/Loki or external)
- git provider (PR creation; GitHub/GitLab/Gitea/Forgejo/etc)

## 3) Capability probing
Do not “guess” cluster capabilities.
Use:
- ProviderProfile declared capabilities, and/or
- CapabilityProbeAdapter runtime checks (preferred)

## 4) Module types
Each module is either:
- INSTALL: platform installs it into management/tenant clusters via GitOps
- INTEGRATE: platform integrates with an external pre-existing service using adapter config

This prevents coupling to “we always deploy Grafana ourselves”.

## 5) Degradation strategy
Modules declare required capabilities.
If missing:
- fail fast (if required for correctness), or
- degrade gracefully (skip optional features), per module policy
