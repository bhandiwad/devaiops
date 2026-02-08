#!/usr/bin/env bash
set -euo pipefail

API_BASE="${AIOPS_API_BASE:-http://localhost:8000}"
TENANT_ID="${BETA_TENANT_ID:-tenant-beta-demo}"
PROVIDER_PROFILE="${BETA_PROVIDER_PROFILE:-generic-k8s-on-vms}"
MODE="${BETA_TENANT_MODE:-BYOC}"
DEV_PRINCIPAL='{"principal_id":"beta-demo","email":"beta@example.com","realm_roles":["platform_admin"],"tenant_roles":{}}'

H=("-H" "Content-Type: application/json")
if [[ -n "${AIOPS_TOKEN:-}" ]]; then
  H+=("-H" "Authorization: Bearer ${AIOPS_TOKEN}")
else
  H+=("-H" "X-Dev-Principal: ${DEV_PRINCIPAL}")
fi

echo "[beta-demo] create tenant"
curl -fsS "${H[@]}" -X POST "${API_BASE}/api/v1/tenants" -d "{\"tenant_id\":\"${TENANT_ID}\",\"display_name\":\"Beta Demo Tenant\",\"mode\":\"${MODE}\",\"provider_profile_id\":\"${PROVIDER_PROFILE}\"}" || true

echo "[beta-demo] enable products"
for product in observability.pack secrets.pack registry.pack gitops.pack aiops.pack; do
  curl -fsS "${H[@]}" -X POST "${API_BASE}/api/v1/tenants/${TENANT_ID}/products/${product}/enable" || true
done

echo "[beta-demo] scaffold example service"
curl -fsS "${H[@]}" -X POST "${API_BASE}/api/v1/tenants/${TENANT_ID}/scaffold" -d '{"template_id":"web-service-python-fastapi","parameters":{"service_name":"payments","owner":"platform-team"}}' || true

echo "[beta-demo] create synthetic incident"
uv run python "$(dirname "$0")/synthetic-incident.py" --tenant "${TENANT_ID}" --service payments --api "${API_BASE}" || true

echo "[beta-demo] done"
