# Beta Quickstart

## Prerequisites
- Kubernetes cluster for management plane
- `kubectl`, `uv`, and Docker available
- Platform config in `config/examples/platform_config.yaml` adjusted for your environment

## Install
```bash
make beta-install
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
