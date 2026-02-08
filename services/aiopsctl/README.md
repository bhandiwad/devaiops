# aiopsctl

Thin API-only CLI.

## Install
```bash
cd /Users/pb/devops_ai/aiops_platform_docs/services/aiopsctl
uv sync
```

## Usage
```bash
export AIOPS_API_BASE=http://localhost:8000
export AIOPS_TOKEN=<token>

aiopsctl scaffold <tenant_id> python-fastapi <service_name> <owner>
aiopsctl promote <tenant_id> <service_id> dev stage
aiopsctl products list
aiopsctl products enable <tenant_id> <product_id>
aiopsctl access request <tenant_id> tenant_operator
```
