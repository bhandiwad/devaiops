# Beta Quickstart

## Prerequisites
- Kubernetes cluster for management plane (tested with Docker Desktop k8s at `https://127.0.0.1:6443`)
- `kubectl`, `uv`, and Docker available
- `helm` available for Harbor install
- Platform config in `config/examples/platform_config.yaml` adjusted for your environment

## Install (GitOps path)
```bash
make beta-install
```

## Install (Local k8s all-in-one path)
```bash
kubectl apply -f k8s/local/stack.yaml
kubectl apply -f k8s/local/observability-vault.yaml
helm repo add harbor https://helm.goharbor.io
helm repo update
helm upgrade --install harbor harbor/harbor -n registry -f k8s/local/harbor-values.yaml
```

## Verify
```bash
make beta-verify
```

## Run demo seed
```bash
make beta-demo
```

## Reset demo
```bash
make beta-reset
```

## Verification checklist
- `/api/v1/me` works with Keycloak token (or `DEV_AUTH` in non-prod mode)
- Backstage loads and can list tenants/products/incidents
- Event feed shows new actions after demo seed
- Incident synthetic flow can be created and investigated

## Local k8s endpoints (NodePort)
- Backstage: `http://localhost:30080`
- Platform API: `http://localhost:30081`
- Keycloak: `http://localhost:30082`
- Argo CD: `http://localhost:30083`
- Harbor: `http://localhost:30084`
- Prometheus: `http://localhost:30090`
- Loki: `http://localhost:30100`
- Vault: `http://localhost:30200`
- Grafana: `http://localhost:30300`
