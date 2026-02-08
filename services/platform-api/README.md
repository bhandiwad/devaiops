# AIOps Platform API

## Quickstart

### Prereqs
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- Docker (for local Postgres)

### 1) Start Postgres + Redis
```bash
cd /Users/pb/devops_ai/aiops_platform_docs/services/platform-api

# start db

docker compose up -d

# initialize schema
psql "postgresql://platform:platform@localhost:5432/platform" -f /Users/pb/devops_ai/aiops_platform_docs/db/schema.sql
```

### 2) Install deps
```bash
cd /Users/pb/devops_ai/aiops_platform_docs/services/platform-api
uv venv
source .venv/bin/activate
uv pip install -e .[test]
```

### 3) Run the API (dev auth)
```bash
export DEV_AUTH=true
export PLATFORM_CONFIG_PATH="/Users/pb/devops_ai/aiops_platform_docs/config/examples/platform_config.yaml"
export ARGOCD_SERVER="https://argocd.example"
export ARGOCD_TOKEN="changeme"
export GITHUB_TOKEN="changeme"
export PROMETHEUS_BASE_URL="http://prometheus:9090"
export LOKI_BASE_URL="http://loki:3100"

uvicorn src.main:app --reload --port 8000
```

### 3b) Run the API (Keycloak auth)
```bash
export DEV_AUTH=false
export PLATFORM_CONFIG_PATH="/Users/pb/devops_ai/aiops_platform_docs/config/examples/platform_config.yaml"
export ARGOCD_SERVER="https://argocd.example"
export ARGOCD_TOKEN="changeme"
export GITHUB_TOKEN="changeme"
export PROMETHEUS_BASE_URL="http://prometheus:9090"
export LOKI_BASE_URL="http://loki:3100"
export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="changeme"

uvicorn src.main:app --reload --port 8000
```

### 4) Run the worker
```bash
export PLATFORM_CONFIG_PATH="/Users/pb/devops_ai/aiops_platform_docs/config/examples/platform_config.yaml"

celery -A src.worker.celery_app worker --loglevel=INFO
```

### 5) Example request
```bash
curl -H 'X-Dev-Principal: {"principal_id":"dev-user","email":"dev@example.com","realm_roles":["platform_admin"],"tenant_roles":{"tenant-acme":["tenant_admin"]}}' \
  http://localhost:8000/api/v1/me
```

## Kubernetes deployment (local cluster)
From repo root:
```bash
docker build -f services/platform-api/Dockerfile -t local/aiops-platform-api:dev .
docker build -f ui/backstage/Dockerfile -t local/aiops-backstage:dev .

kubectl apply -f k8s/local/stack.yaml
kubectl apply -f k8s/local/observability-vault.yaml

helm repo add harbor https://helm.goharbor.io
helm repo update
helm upgrade --install harbor harbor/harbor -n registry -f k8s/local/harbor-values.yaml
```

NodePort access:
- Backstage: `http://localhost:30080`
- API: `http://localhost:30081`
- Keycloak: `http://localhost:30082`
- Argo CD: `http://localhost:30083`
- Harbor: `http://localhost:30084`

## Config
- Default config path is `config/examples/platform_config.yaml` (override with `PLATFORM_CONFIG_PATH`).
- Module catalog path is read from `PlatformConfig.modules.module_catalog_path`.
- Provider profiles and tenant specs are loaded from `PlatformConfig.config_sources`.
- For local k8s, runtime config is injected via ConfigMap in `k8s/local/stack.yaml`.
- Harbor runtime settings are under `registry.harbor` and consumed by `plugins.harbor:HarborRegistryAdapter`.
- Iteration 7 settings:
  - `rate_limit`: per-tenant/principal request limits
  - `idempotency`: protected POST routes and key TTL
  - `metering`: collection schedule
  - `platform.version`: control-plane version
  - `dr`: backup/verification mode
  - `tracing`: optional OpenTelemetry exporter settings

## Iteration 7 endpoints
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

## Iteration 8 endpoints
- `GET /products`
- `POST /tenants/{tenant_id}/products/{product_id}/enable`
- `POST /tenants/{tenant_id}/products/{product_id}/disable`
- `POST /tenants/{tenant_id}/access/requests`
- `GET /tenants/{tenant_id}/access/requests`
- `POST /tenants/{tenant_id}/access/requests/{request_id}/approve`
- `POST /tenants/{tenant_id}/access/requests/{request_id}/deny`
- `POST /tenants/{tenant_id}/scaffold`
- `POST /tenants/{tenant_id}/services/{service_id}/promote?from_env=&to_env=`
- `GET /tenants/{tenant_id}/services/{service_id}/promotions`

## Iteration 9 endpoints (v1 API)
- `GET /api/v1/events`
- `GET /api/v1/tenants/{tenant_id}/events`
- `POST /api/v1/tenants/{tenant_id}/subscriptions`
- `GET /api/v1/tenants/{tenant_id}/subscriptions`
- `DELETE /api/v1/tenants/{tenant_id}/subscriptions/{subscription_id}`
- `POST /api/v1/tenants/{tenant_id}/incidents/{incident_id}/transition`
- `GET /api/v1/tenants/{tenant_id}/incidents/{incident_id}/timeline`
- `POST /api/v1/tenants/{tenant_id}/incidents/{incident_id}/notify`
- `POST /api/v1/tenants/{tenant_id}/incidents/{incident_id}/create-ticket`

## Beta endpoints (Iteration 10)
- `GET /api/v1/search?q=...`
- `GET /api/v1/tenants/{tenant_id}/onboarding/progress`
- `GET /api/v1/tenants/{tenant_id}/deployments`
- `POST /api/v1/tenants/{tenant_id}/deployments/{service_id}/sync`
- `POST /api/v1/tenants/{tenant_id}/deployments/{service_id}/rollback`
- `GET /api/v1/runbooks`

## SDK generation
```bash
cd /Users/pb/devops_ai/aiops_platform_docs/services/platform-api
make sdk
```
- OpenAPI snapshot: `/Users/pb/devops_ai/aiops_platform_docs/sdk/openapi.json`
- Python SDK: `/Users/pb/devops_ai/aiops_platform_docs/sdk/python`
- TypeScript SDK: `/Users/pb/devops_ai/aiops_platform_docs/sdk/typescript`

## GitOps packaging
- Helm charts: `/Users/pb/devops_ai/aiops_platform_docs/platform/charts/platform-api`, `/Users/pb/devops_ai/aiops_platform_docs/platform/charts/platform-worker`
- Argo app-of-apps: `/Users/pb/devops_ai/aiops_platform_docs/platform/gitops/app-of-apps/root.yaml`
- Env overlays: `/Users/pb/devops_ai/aiops_platform_docs/platform/gitops/environments/dev`, `/Users/pb/devops_ai/aiops_platform_docs/platform/gitops/environments/stage`, `/Users/pb/devops_ai/aiops_platform_docs/platform/gitops/environments/prod`

## Tests
```bash
cd /Users/pb/devops_ai/aiops_platform_docs/services/platform-api
uv run pytest
```

## Adapter implementation status
- Harbor registry adapter: implemented (`ensure_tenant_project`, `ensure_role_bindings`, `create_robot_account`)
- Terraform provisioner adapter: implemented (`provision`, `upgrade`, `deprovision`) and wired to runner
- Vault adapter: implemented baseline auth/policy/audit + KV read/write
- K8s default adapters: implemented capability probe, registrar bootstrap, resource/event/workload reads
