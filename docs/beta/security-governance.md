# Security and Governance

## Authentication and RBAC
- Keycloak-based auth in production mode
- `DEV_AUTH` only allowed for non-prod mode
- Permission checks and policy engine enforcement server-side

## Secret handling
- No secrets in Postgres
- Webhook headers are resolved from Vault refs at dispatch time
- Evidence/export pipelines include redaction controls

## Governance controls
- Policy decisions persisted for major actions
- Approval obligations supported (`require_approval`, `require_ticket_id`, `require_2person_rule`)
- PR remediation allowlist and risk gating enforced server-side
