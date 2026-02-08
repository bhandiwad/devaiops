# BETA RELEASE

## Included features
- Unified API under `/api/v1` with SDK generation
- Tenant onboarding for BYOC and PROVISIONED flows
- Product marketplace with policy-gated enable/disable
- Incident lifecycle with evidence, investigation, PR-only remediation, timeline
- Event store + subscriptions + outbound webhook dispatch
- Drift, exports, metering, governance, and access request workflows
- Backstage primary UX with search, activity feed, onboarding wizard, deployments/incidents UX

## Environment requirements
- Kubernetes management cluster
- Postgres, Redis, Keycloak, Vault, Argo CD
- Optional but recommended: Harbor, Prometheus, Loki, Grafana
- Python 3.11+ and `uv`

## End-to-end demo steps
1. `make beta-install`
2. `make beta-verify`
3. `make beta-demo`
4. Open Backstage and validate:
   - Search and Activity feed
   - Onboarding progress
   - Marketplace product enablement
   - Incidents timeline and actions
   - Deployments status and sync actions
5. `make beta-release-checklist`

## Known limitations
- See `docs/beta/known-limitations.md`
