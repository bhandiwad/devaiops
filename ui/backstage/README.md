# Backstage UI (AIOps Platform)

## Dev
```bash
cd /Users/pb/devops_ai/aiops_platform_docs/ui/backstage

# install deps
npm install

# start
npm start
```

## Config
- Auth provider: Keycloak
- Platform API proxy: `/platform-api` (see `app-config.yaml`)
- UI is a thin client and calls Platform API only.

## Iteration 7 pages
- `Usage`: tenant metering and FinOps visibility.
- `Platform Ops`: platform version, upgrade plan/apply view, DR status/verify, platform metering summary.

## Iteration 8 pages
- `Marketplace`: product catalog and enable/disable workflows.
- `Access`: self-service role request and approval flow.
- `Scaffold`: golden-path service generation via Platform API.
- `Promotions`: PR-based GitOps environment promotions.

## Beta pages (Iteration 10)
- `Search`: global search across tenants, incidents, events, products, and runbooks.
- `Activity`: platform event feed (`/api/v1/events`).
- `Onboarding`: tenant onboarding wizard with progress and recent audit.
- `Deployments`: tenant deployment status, sync action, rollback guidance.
- `Incidents`: timeline-first workflow with evidence/investigation/PR actions.
- `Settings`: platform settings and operator pointers.

## Catalog and docs
- Catalog entities are loaded from `catalog-info.yaml` and `ui/backstage/catalog/platform-resources.yaml`.
- TechDocs is configured in `ui/backstage/app-config.yaml`.
- Scaffolder template definitions are under `ui/backstage/templates/`.
