#!/usr/bin/env bash
set -euo pipefail

API_BASE="${AIOPS_API_BASE:-http://localhost:8000}"
TOKEN="${AIOPS_TOKEN:-}"
DEV_PRINCIPAL='{"principal_id":"beta-verify","email":"beta@example.com","realm_roles":["platform_admin"],"tenant_roles":{}}'

function req() {
  local url="$1"
  if [[ -n "${TOKEN}" ]]; then
    curl -fsS -H "Authorization: Bearer ${TOKEN}" "${url}" >/dev/null
  else
    curl -fsS -H "X-Dev-Principal: ${DEV_PRINCIPAL}" "${url}" >/dev/null
  fi
}

echo "[beta-verify] checking API"
req "${API_BASE}/healthz"
req "${API_BASE}/api/v1/me"
req "${API_BASE}/api/v1/tenants?limit=1"
req "${API_BASE}/api/v1/products"
req "${API_BASE}/api/v1/events?limit=1"

echo "[beta-verify] API checks passed"

echo "[beta-verify] checking key platform dependencies (best effort via kubectl)"
kubectl get pods -A | grep -E 'argocd|keycloak|vault|harbor|grafana|loki|prometheus|platform-api|platform-worker' || true

echo "[beta-verify] done"
