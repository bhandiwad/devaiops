# Operator Guide

## Core operations
- Install or update management plane via `platform/gitops/app-of-apps/root.yaml`
- Verify dependencies with `dev/beta-verify.sh`
- Run platform tests and SDK generation with `make beta-release-checklist`

## Local Kubernetes operations
- Apply base stack: `kubectl apply -f k8s/local/stack.yaml`
- Apply obs + vault: `kubectl apply -f k8s/local/observability-vault.yaml`
- Install Harbor:
  - `helm repo add harbor https://helm.goharbor.io`
  - `helm repo update`
  - `helm upgrade --install harbor harbor/harbor -n registry -f k8s/local/harbor-values.yaml`
- Check readiness:
  - `kubectl get pods -n platform-system`
  - `kubectl get pods -n platform-deps`
  - `kubectl get pods -n keycloak`
  - `kubectl get pods -n vault`
  - `kubectl get pods -n observability`
  - `kubectl get pods -n registry`
  - `kubectl get pods -n argocd`

## Backups and restore
- Use export endpoints for redacted compliance bundles
- Use runbooks in config for DR verification and backup procedures
- Use `POST /api/v1/platform/dr/verify` for dry-run validation

## Drift operations
- Manual drift run: `POST /api/v1/tenants/{tenant_id}/drift/run`
- Read drift status/history from dashboard and API endpoints

## Troubleshooting
- Check `correlation_id` from API error responses
- Use activity feed (`/api/v1/events`) and tenant audit trail for root cause tracking
- Verify policy decisions (`/api/v1/tenants/{tenant_id}/policy-decisions`)
- If product enable fails with `Idempotency-Key required`, resend request with `Idempotency-Key` header.
- If tenant-scoped product actions fail with `TenantSpec not found`, add matching tenant spec YAML under configured `tenant_specs_path`.
