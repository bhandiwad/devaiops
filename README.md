
# Modular AIOps DevOps Platform (Cluster-per-Tenant)

This repo is a *Codex-ready documentation pack* for building a modular DevOps-as-a-Service platform where **each tenant gets its own Kubernetes cluster** and the user experience is delivered primarily through **Backstage** (custom plugins), with a **unified Platform API** and a **unified CLI** named **aiopsctl**.

The platform is designed to integrate with:
- Any Kubernetes distribution (managed or self-managed, upstream or vendor)
- Any infrastructure substrate / hypervisor (including HPE VM Essentials) via pluggable provisioners

## Core capabilities
- Cluster-per-tenant onboarding (BYOC or provisioned)
- GitOps execution via Argo CD
- Secrets via HashiCorp Vault
- Registry via Harbor
- Observability via Prometheus + Grafana + Loki (centralized or per-tenant)
- AI-assisted investigations + PR-based remediation (no direct prod mutations)
- Keycloak SSO everywhere + unified RBAC propagated to integrated systems
- Full modularity via external configuration + adapter plugins + capability flags

## Design invariants (non-negotiable)
1. **No assumptions about Kubernetes distro** (CNI/CSI/Ingress/LB/DNS are not assumed).
2. **All behavior is config-driven**; configs live outside code.
3. **Adapters isolate vendor/tool differences**; core logic does not import vendor specifics.
4. **Safe AIOps**: AI proposes PRs only; GitOps applies changes.
5. **Unified control plane**: Backstage and aiopsctl call the Platform API only.

## Contents
- docs/: architecture + modularity + adapters + RBAC/SSO + runbooks + task breakdown
- schemas/: JSON schemas for configs and AI artifacts
- config/examples/: sample configs (no secrets)
- db/: Postgres DDL and data model notes

## Licensing note (important)
You said you're ok with HashiCorp Vault and Terraform. Be aware:
- HashiCorp changed Terraform/Vault licensing to BSL (Business Source License). BSL is typically free to use, but it is not OSI “open source”.
- If you ever need OSI-only alternatives later, swap adapters (e.g., OpenTofu/OpenBao) without changing platform core.
