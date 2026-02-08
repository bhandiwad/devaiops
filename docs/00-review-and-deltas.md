
# Review of previous draft (accuracy, novelty, completeness)

This pack incorporates the earlier modularity considerations and fixes gaps:

## Accuracy fixes / clarifications
- Some components (notably Loki) do not provide strong built-in per-tenant authorization. This design treats tenancy enforcement as an ObservabilityAdapter responsibility (often implemented via a gateway enforcing tenant headers/labels).
- Not all Kubernetes clusters support OIDC to Kubernetes out-of-the-box. This design treats Kubernetes SSO/RBAC mapping as optional capability, not assumed.
- Harbor/Grafana/Argo/Vault SSO capabilities vary by version and deployment. This design supports both direct OIDC and “auth-proxy” patterns, configured via profiles.

## Novelty added
- A formal **Module Catalog**: modules can be installed or integrated (external), with explicit requirements and capability checks.
- A formal **Capability Probe**: provider profiles plus runtime validation to avoid brittle vendor branching.
- Explicit **BYOC vs PROVISIONED** convergence: both paths flow through Registrar → GitOps bootstrap.
- Explicit **Auth Integration Modes**: direct OIDC vs proxy OIDC without changing clients.

## Completeness added
- Git provider abstraction for PR bot (GitHub/GitLab/Gitea/Forgejo/etc) via GitProviderAdapter.
- Config system with precedence + schema validation + config repo patterns.
- Postgres DDL skeleton and event/audit model.
- Security boundaries and minimum viable trust model.
- Codex task breakdown aligned to adapters + modules + plugin loader.

This is a build-ready documentation pack: it specifies contracts, schemas, boundaries, and tasks without assuming a specific infrastructure vendor, K8s distro, network, or storage.
