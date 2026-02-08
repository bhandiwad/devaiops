
# Provider profiles

ProviderProfile describes the environment and integration modes without naming vendors.

## 1) What ProviderProfile contains
- capability flags (declared and/or probed)
- defaults (storage class names, ingress class names, etc.)
- auth integration modes:
  - direct_oidc (tool supports Keycloak OIDC)
  - auth_proxy_oidc (tool fronted by proxy providing OIDC)
- module overrides (chart values, resource presets, security contexts)

## 2) Why this enables “any K8s distro”
Different distros differ mostly in:
- security defaults (PSA/SELinux)
- available ingress/LB
- storage capabilities
- OIDC support
ProviderProfile + capability probing handle these differences without code forks.

## 3) Capability flags (recommended minimum)
- supports_network_policy
- supports_loadbalancer_service
- supports_ingress
- supports_cert_manager
- supports_rwx_storage
- supports_volume_snapshots
- supports_psa
- supports_k8s_oidc
- supports_node_local_dns (optional)
- supports_egress_restrictions (optional)

See schemas/provider_profile.schema.json
