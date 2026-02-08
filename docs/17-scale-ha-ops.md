# Iteration 7: Scale, HA, Upgrades, Metering, Platform Ops

## Highlights
- API hardening with rate limits, idempotency keys, request metrics, and correlation propagation.
- Worker retry/backoff for retryable adapter failures plus worker job metrics.
- Metering subsystem with scheduled collection, rollups, and tenant/platform usage endpoints.
- Platform ops endpoints for version, upgrade plan/apply, and DR status/verify.
- GitOps-first packaging with Helm charts and Argo app-of-apps overlays for dev/stage/prod.

## API additions
- `GET /metrics`
- `POST /tenants/{tenant_id}/metering/collect`
- `GET /tenants/{tenant_id}/metering`
- `GET /tenants/{tenant_id}/finops/summary`
- `GET /platform/metering/summary`
- `GET /platform/version`
- `GET /platform/upgrade/plan`
- `POST /platform/upgrade/apply`
- `GET /platform/dr/status`
- `POST /platform/dr/verify`

## New storage objects
- `idempotency_keys`
- `upgrade_runs`
- `metering_samples`
- `metering_rollups`

## Deployment packaging
- Helm charts:
  - `platform/charts/platform-api`
  - `platform/charts/platform-worker`
- Argo app-of-apps:
  - `platform/gitops/app-of-apps/root.yaml`
- Environment overlays:
  - `platform/gitops/environments/dev`
  - `platform/gitops/environments/stage`
  - `platform/gitops/environments/prod`
- Alerts:
  - `platform/gitops/alerts/platform-alerts.yaml`

## DR runbook intent
- Postgres logical backup and restore verification are represented as platform runbook entries.
- Artifact backup verification is represented as a runbook entry.
- Export bundles remain redacted and secret-free for disaster data portability.
