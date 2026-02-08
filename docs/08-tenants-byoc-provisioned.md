
# Tenants: BYOC and PROVISIONED

## 1) TenantSpec
TenantSpec is the only tenant input to Platform API:
- tenant_id
- mode: BYOC | PROVISIONED
- provider_profile_id
- git repo info
- module selection
- remediation allowlist and approval policy
- observability mode
- provisioning_ref (only for PROVISIONED)

## 2) BYOC minimum requirements
- Kubernetes API reachable
- Platform can create (or is provided) a least-privilege service account and kube credentials
- Optional: ability to install tenant base add-ons (if tenant chooses)

## 3) PROVISIONED requirements
- ProvisionerAdapter must be configured (Terraform runner default)
- Provisioner must output ClusterAccess in the standard schema

Both modes then use the same pipeline: probe → bootstrap → register → apply tenant base modules.
