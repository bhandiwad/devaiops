
# Design principles

## 1) Interfaces over implementations
The platform must not depend on a specific:
- Kubernetes distribution
- CNI/CSI/Ingress/LB/DNS implementation
- Hypervisor or cloud provider
- Git provider

All external systems are accessed through adapters with stable interfaces.

## 2) Configuration outside code
Everything operational must be driven by external configuration:
- enabled modules
- provider profiles (capabilities and defaults)
- tenant specs
- RBAC mappings
- integration endpoints and auth modes
- module overrides

No environment-specific constants may be hardcoded.

## 3) Capability-driven behavior
Never branch by vendor name (“OpenShift”, “RKE2”, etc).
Branch only by explicit capabilities declared/validated:
- supports_network_policy
- supports_loadbalancer_service
- supports_ingress
- supports_rwx_storage
- supports_psa
- supports_k8s_oidc
- supports_volume_snapshots
…and others as needed.

## 4) Safe AIOps (PR-only)
AI never executes changes directly in production.
All fixes are proposed as Git PRs targeting tenant repos.
GitOps applies merged changes.

## 5) Unified control plane
Backstage (UI) and aiopsctl (CLI) call Platform API only.
The Platform API is the single authorization + audit chokepoint.

## 6) Two-phase execution model
- Phase A (optional): provisioning via ProvisionerAdapter (Terraform runner, etc.)
- Phase B: registration + bootstrap + operations via Kubernetes/GitOps adapters

BYOC and PROVISIONED converge into the same Phase B pipeline.
