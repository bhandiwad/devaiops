
# Terraform and hypervisor portability (including HPE VM Essentials)

## Core stance
The platform never directly depends on a hypervisor.
It depends on a Kubernetes API endpoint and GitOps.

Hypervisor integration happens via ProvisionerAdapter implementations.

## Recommended approach: ProvisionerAdapter(Terraform runner)
- Use Terraform modules to provision VMs/network/storage on any substrate.
- Optionally use Ansible or cloud-init to bootstrap Kubernetes on provisioned VMs.
- Output a standard ClusterAccess object (kube endpoint + credentials + metadata).

## HPE VM Essentials integration patterns
- Pattern A (recommended): Terraform provisions VM Essentials resources, then bootstraps K8s. Platform consumes kube access.
- Pattern B (later): HypervisorAdapter for deep VM lifecycle operations in UI. Avoid for MVP to reduce coupling.

## Determinism requirement
Provisioner outputs must be sufficient to:
- register cluster in Argo
- create least-privilege service account
- run capability probe and bootstrap modules
