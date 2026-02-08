#!/usr/bin/env bash
set -euo pipefail

API_BASE="${AIOPS_API_BASE:-http://localhost:8000}"
TENANT_ID="${BETA_TENANT_ID:-tenant-beta-demo}"
DEV_PRINCIPAL='{"principal_id":"beta-reset","email":"beta@example.com","realm_roles":["platform_admin"],"tenant_roles":{}}'

H=("-H" "Content-Type: application/json")
if [[ -n "${AIOPS_TOKEN:-}" ]]; then
  H+=("-H" "Authorization: Bearer ${AIOPS_TOKEN}")
else
  H+=("-H" "X-Dev-Principal: ${DEV_PRINCIPAL}")
fi

echo "[beta-reset] deleting demo tenant if it exists"
curl -fsS "${H[@]}" -X DELETE "${API_BASE}/api/v1/tenants/${TENANT_ID}" || true

echo "[beta-reset] cleanup complete"
