
# Architecture (cluster-per-tenant)

## 1) Planes

### 1.1 Management plane (platform cluster)
Runs:
- Keycloak (SSO / identity provider)
- Backstage (primary UI shell)
- Platform API (FastAPI) + Platform Worker (async jobs)
- Postgres (platform state + audit/event index)
- Argo CD (GitOps controller)
- Vault (secrets)
- Harbor (registry)
- Observability stack (Prometheus/Grafana/Loki) OR ObservabilityAdapter integration to external systems
- AIOps services: evidence collector, investigator, PR bot
- Optional: auth gateway components for tools that lack tenant-aware auth (e.g., Loki gateway)

### 1.2 Tenant plane (one Kubernetes cluster per tenant)
Runs:
- Tenant workloads
- Optional “tenant base” add-ons (installed via GitOps):
  - log shipper
  - metrics exporters/agent
  - vault agent injector (if used)
  - policy components (optional, capability-dependent)

No Backstage/UI services run in tenant clusters by default.

## 2) Trust boundaries
- Tenants are isolated by *separate clusters*.
- The management plane holds tenant credentials in a secure store and enforces RBAC.
- AI components do not get broad cluster-admin; they work from evidence packs and Git PRs.

## 3) Control surfaces
- Backstage → Platform API
- aiopsctl → Platform API
- Platform API → adapters → external systems (Argo/Vault/Harbor/Observability/K8s/Git)

## 4) Core flows

### 4.1 Tenant onboarding (BYOC)
Input: TenantSpec(mode=BYOC) + ProviderProfile
Steps:
1) Validate cluster access and capabilities (CapabilityProbe)
2) Bootstrap minimal resources (RegistrarAdapter)
3) Register cluster in Argo CD (GitOpsAdapter)
4) Apply tenant base modules via GitOps (ModuleCatalog)
5) Configure Vault policies and auth mappings (SecretsAdapter)
6) Configure Harbor project and RBAC (RegistryAdapter)
7) Configure Observability tenancy integration (ObservabilityAdapter)
8) Mark tenant READY

### 4.2 Tenant onboarding (PROVISIONED)
Same as BYOC except step 0:
0) Provision cluster via ProvisionerAdapter (Terraform runner or other)
Then proceed with steps 1..8 identically.

### 4.3 Service onboarding
1) Backstage template invokes Platform API to scaffold service (GitProviderAdapter)
2) Platform API creates/updates GitOps application targeting tenant cluster
3) Deployments occur via GitOps; status is aggregated by Platform API

### 4.4 Alert → investigation → PR remediation
1) Alert ingested with tenant labels (tenant_id, cluster_id, namespace, service)
2) EvidencePack collected (K8sAdapter + ObservabilityAdapter + GitOpsAdapter)
3) Investigator generates structured proposal (AiRemediationProposal)
4) PR bot creates PR (GitProviderAdapter) to allowed paths/types only
5) PR gated by CI + policy checks + approvals based on risk
6) Merge triggers Argo CD sync; verification runs; incident closed with audit trail
