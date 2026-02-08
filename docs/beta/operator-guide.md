# Operator Guide

## Core operations
- Install or update management plane via `platform/gitops/app-of-apps/root.yaml`
- Verify dependencies with `dev/beta-verify.sh`
- Run platform tests and SDK generation with `make beta-release-checklist`

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
