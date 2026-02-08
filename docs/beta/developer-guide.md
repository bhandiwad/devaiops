# Developer Guide

## API v1
- All supported endpoints are under `/api/v1`
- Use standardized error shape: `error.code`, `error.message`, `error.correlation_id`

## SDK usage
Generate SDKs:
```bash
make sdk
```

Artifacts:
- `sdk/openapi.json`
- `sdk/python/aiops_platform_client`
- `sdk/typescript/src/client.ts`

## Scaffolding and promotions
- Scaffold service via API or `aiopsctl scaffold`
- Promote via PR-only flow and policy obligations
