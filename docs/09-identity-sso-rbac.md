
# Identity, SSO, and RBAC

## 1) Keycloak SSO
Keycloak is the IdP for:
- Backstage
- Platform API
- Argo CD
- Grafana
- Harbor
- Vault (OIDC auth)

Auth integration can be:
- direct OIDC (preferred)
- OIDC via auth proxy (configured per tool)

## 2) Central RBAC model (authoritative)
Platform API is authoritative for authorization and audit.

Roles:
- platform_admin
- tenant_admin
- tenant_operator
- tenant_developer
- tenant_viewer

## 3) Role propagation mappings (managed by Platform API)
- Argo CD: Keycloak groups -> Argo roles + tenant Argo Projects enforce isolation
- Vault: Keycloak groups -> Vault policies scoped to tenant paths
- Grafana: Keycloak groups -> folder permissions + datasource access; tenant scoping for Loki
- Harbor: Keycloak groups -> project role bindings

## 4) Kubernetes RBAC mapping (optional)
If supports_k8s_oidc is true:
- map Keycloak groups to Kubernetes RBAC.
Otherwise:
- rely on platform operations via service accounts; do not assume human SSO into cluster.

## 5) Auditing
All privileged actions must produce an AuditEvent record in Postgres:
- who (principal), what, tenant, resource, before/after refs, correlation id
