
# Adapter contracts (Codex target)

Adapters must be defined as Python interfaces (ABCs/Protocols) and loaded dynamically.

## 1) IdentityAdapter (Keycloak)
Responsibilities:
- verify JWT
- resolve principal context: tenant memberships + roles
- optional: manage role bindings if platform is authoritative

Methods:
- verify_token(token) -> Principal
- get_context(principal) -> PrincipalContext

## 2) ProvisionerAdapter
Responsibilities:
- Provisioned clusters: create/upgrade/delete and return ClusterAccess.
- BYOC clusters: typically not used.

Methods:
- provision(tenant_spec, provider_profile) -> ClusterAccess
- upgrade(tenant_id, plan) -> ClusterAccess
- deprovision(tenant_id) -> None

## 3) CapabilityProbeAdapter
Responsibilities:
- Validate cluster prerequisites and capability flags against reality.

Methods:
- probe(cluster_access, provider_profile) -> CapabilityReport

## 4) RegistrarAdapter
Responsibilities:
- Bootstrap tenant cluster with minimal resources:
  - namespaces
  - service accounts and RBAC needed for Argo registration and evidence collection
- Ensure minimal required add-ons for selected modules (only if declared and supported)

Methods:
- bootstrap(cluster_access, tenant_spec, provider_profile, capability_report) -> BootstrapResult

## 5) GitOpsAdapter (Argo CD)
Methods:
- register_cluster(tenant_id, cluster_access, rbac_policy) -> ClusterRef
- ensure_tenant_project(tenant_id, project_policy) -> ProjectRef
- apply_application(app_spec) -> AppRef
- get_application_status(app_ref) -> AppStatus
- sync_application(app_ref) -> SyncResult

## 6) SecretsAdapter (Vault)
Methods:
- ensure_platform_oidc_auth(keycloak_config) -> None
- ensure_tenant_policies(tenant_id, role_bindings) -> None
- ensure_workload_auth(tenant_id, workload_identity, policy_ref) -> None
- audit_configure() -> None

## 7) RegistryAdapter (Harbor)
Methods:
- ensure_tenant_project(tenant_id, project_spec) -> ProjectRef
- ensure_role_bindings(tenant_id, role_bindings) -> None
- create_robot_account(tenant_id, scope) -> RobotCredentials

## 8) ObservabilityAdapter
Notes:
- Loki typically needs a gateway/tenant-header strategy for secure multi-tenancy.
- This adapter must enforce tenant scoping.

Methods:
- ensure_tenant_observability(tenant_id, mode, mappings) -> None
- query_logs(tenant_id, query_spec) -> LogResult
- query_metrics(tenant_id, query_spec) -> MetricResult
- list_dashboards(tenant_id) -> DashboardList
- summary(service_ref) -> ObservabilitySummary

## 9) GitProviderAdapter (PR bot dependency)
Responsibilities:
- Create repos from templates
- Create branches, commits, PRs/MRs
- Read PR status, approvals, CI status

Methods:
- scaffold_repo(template_ref, parameters) -> RepoRef
- create_pull_request(repo_ref, branch, title, body, changes) -> PRRef
- get_pull_request_status(pr_ref) -> PRStatus
- add_labels(pr_ref, labels) -> None

## 10) K8sAdapter
Responsibilities:
- Read-only access for evidence collection
- Strictly limited write access only for bootstrap tasks (through Registrar)

Methods:
- get_workload_snapshot(cluster_ref, selectors) -> Snapshot
- get_events(cluster_ref, namespace, since) -> Events
- get_resource(cluster_ref, gvk, name, namespace) -> Resource

## Adapter loading
- Use a plugin registry mapping adapter IDs -> Python import path in PlatformConfig.
- Support multiple implementations per adapter type.
