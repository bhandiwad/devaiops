# Beta Epics and Execution Plan

## Epic 1: UX IA + Top-notch Backstage Experience (P0)

### Goals
- Coherent IA and navigation for Tenants, Services, Deployments, Products, Incidents, Drift, Runbooks, Metering, Governance, Exports, Settings.
- Global search, activity feed, and onboarding wizard.
- Consistent loading/empty/error states.

### Code changes
- `ui/backstage/packages/app/src/App.tsx`
- `ui/backstage/packages/app/src/components/OnboardingWizardPage.tsx` (new)
- `ui/backstage/packages/app/src/components/SearchPage.tsx` (new)
- `ui/backstage/packages/app/src/components/ActivityFeedPage.tsx` (new)
- `ui/backstage/packages/app/src/components/common/StatePanels.tsx` (new)
- `ui/backstage/packages/app/src/components/IncidentsPage.tsx` (timeline-first UX)
- `ui/backstage/packages/app/src/components/MarketplacePage.tsx` (details + approval states)
- `ui/backstage/packages/app/src/components/DeploymentsPage.tsx` (status/actions)

## Epic 2: API Hardening + Discoverability + Pagination (P0)

### Goals
- Add search endpoint and server-side pagination.
- Extend idempotency coverage and side-effect safety.
- Improve event hooks for feed consistency.

### Code changes
- `services/platform-api/src/api/routes.py`
- `services/platform-api/src/models/api.py`
- `services/platform-api/src/api/middleware.py`
- `services/platform-api/src/config/examples/platform_config.yaml`
- `services/platform-api/tests/test_api_pagination.py` (new)
- `services/platform-api/tests/test_search_endpoint.py` (new)

## Epic 3: Functional Stack Completeness + Config Coherence (P0)

### Goals
- Ensure module catalog and product descriptors reflect required stack names.
- Ensure runbook coverage and event hooks for major flows.

### Code changes
- `config/module_catalog.yaml`
- `config/products/*.yaml`
- `config/examples/provider_profile_generic.yaml`
- `config/examples/tenant_byoc.yaml`
- `config/examples/tenant_provisioned.yaml`

## Epic 4: Beta Packaging + Demo Seed + Reset (P0)

### Goals
- One-command-ish beta install path and verification.
- Demo seed for BYOC/PROVISIONED + synthetic incident.
- Reset workflow for dev/stage.

### Code changes
- `dev/beta-install.sh` (new)
- `dev/beta-verify.sh` (new)
- `dev/beta-demo.sh` (new)
- `dev/beta-reset.sh` (new)
- `dev/synthetic-incident.py` (new)
- `Makefile` (new top-level targets)

## Epic 5: Tests and Release Gates (P1)

### Goals
- Smoke tests for E2E critical flows.
- UI smoke tests for onboarding/marketplace/incidents.
- Beta release checklist automation target.

### Code changes
- `services/platform-api/tests/test_beta_smoke_api.py` (new)
- `ui/backstage/packages/app/src/components/__tests__/beta-ui-smoke.test.tsx` (new)
- `services/platform-api/Makefile` and top-level `Makefile`

## Epic 6: Beta Documentation Pack (P0)

### Goals
- Full `/docs/beta/` docs set and top-level release guide.

### Docs changes
- `docs/beta/quickstart.md` (new)
- `docs/beta/operator-guide.md` (new)
- `docs/beta/tenant-admin-guide.md` (new)
- `docs/beta/developer-guide.md` (new)
- `docs/beta/security-governance.md` (new)
- `docs/beta/known-limitations.md` (new)
- `BETA_RELEASE.md` (new)

## Execution sequence
1. Epic 2 (API search/pagination/idempotency).
2. Epic 1 (UX IA/search/feed/onboarding).
3. Epic 3 (config/module/product coherence).
4. Epic 4 (install/verify/demo/reset).
5. Epic 5 (smoke tests + checklist target).
6. Epic 6 (docs + release guide).
