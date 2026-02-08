
# Backstage as primary UI shell

## 1) Backstage’s role
Backstage provides the user-facing shell:
- Tenant Console
- Services / Deployments
- Incidents + AIOps PRs
- Observability
- Secrets metadata + workflows
- Access (RBAC bindings)
- Audit

Backstage must call Platform API only.

## 2) UX swap option
Backstage is a client. To change UX later:
- build a new React SPA calling Platform API
- keep aiopsctl unchanged
- optionally keep Backstage for catalog/scaffolding

## 3) Plugin boundaries
Plugins should be thin:
- fetch data from Platform API
- render UI states
- initiate actions via Platform API
No secrets or direct tool credentials in browser.
