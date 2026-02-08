
# Module catalog

A ModuleDescriptor defines:
- name, version
- type: INSTALL or INTEGRATE
- scope: management-plane, tenant-plane, or both
- requirements: required capabilities and required adapters
- manifests: how to install (Argo app spec) OR how to integrate (adapter config requirements)
- outputs: what resources/URLs/credentials it provides to the Platform API

## Examples (conceptual modules)
- gitops.argocd (INSTALL or INTEGRATE)
- secrets.vault (INSTALL or INTEGRATE)
- registry.harbor (INSTALL or INTEGRATE)
- obs.stack (INSTALL) OR obs.external (INTEGRATE)
- aiops.core (INSTALL; evidence collector + investigator + pr-bot)
- ui.backstage (INSTALL)

## Required module behavior
- Must declare capability requirements.
- Must declare whether it is optional or mandatory per tenant.
- Must declare how tenant scoping is enforced (labels, headers, org IDs, separate instances).

See schemas/module_descriptor.schema.json
