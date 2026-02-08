# Beta Gaps (Iteration 10)

This file tracks remaining gaps against the Beta exit criteria and assigns an owning workstream.

## Critical Gaps

| ID | Gap | Exit Criteria Impact | Owner |
|---|---|---|---|
| BG-001 | Backstage IA is fragmented and missing a coherent navigation model with global search + activity feed | UX #2 | UI |
| BG-002 | No tenant onboarding wizard with guided BYOC/PROVISIONED flow and progress/error guidance | W1, UX #2 | UI + API |
| BG-003 | `/api/v1` has no platform search endpoint for tenant/service/incident/runbook discoverability | UX #2, W5 | API |
| BG-004 | List endpoints are mostly unpaginated; large-tenant performance can degrade | Hardening #4, Perf | API |
| BG-005 | Missing beta install/verify/demo/reset operator scripts and docs | Install #3 | PlatformOps + Docs |
| BG-006 | No dedicated `/docs/beta/` pack and no top-level beta release guide | Docs #5 | Docs |
| BG-007 | Module catalog naming does not fully reflect required stack product naming (`obs.prom-grafana-loki`, `ui.backstage`) | Functional completeness #2 | PlatformOps |
| BG-008 | Event activity is not consistently surfaced in UI pages | W5, UX #2 | UI |
| BG-009 | Incident UX lacks timeline-first view with evidence/PR references and guided next actions | W4, UX #2 | UI |
| BG-010 | Idempotency coverage does not explicitly include all new v1 side-effect actions (subscriptions/notify/ticket/incident transition) | Hardening #4 | API |

## Medium Gaps

| ID | Gap | Exit Criteria Impact | Owner |
|---|---|---|---|
| BG-011 | No synthetic incident generator for repeatable demo validation | W4, Demo #3 | PlatformOps + Tests |
| BG-012 | No beta release checklist automation target combining smoke checks and docs gates | Quality #D | Tests + PlatformOps |
| BG-013 | Missing UI smoke tests for onboarding wizard + marketplace + incident investigate/create-pr path | Quality #D | Tests |
| BG-014 | Backstage pages have inconsistent loading/empty/error patterns | UX #2 | UI |
| BG-015 | Event-driven audit/activity is not exposed as a unified feed per tenant + platform | W5, UX #2 | UI + API |

## Low Gaps

| ID | Gap | Exit Criteria Impact | Owner |
|---|---|---|---|
| BG-016 | No explicit beta roadmap/known-limits section | Docs #5 | Docs |
| BG-017 | No single-page pilot “go/no-go” checklist for operators | Install/Docs | Docs |

## Planned Closure in this iteration

- Close BG-001..BG-010 as implementation blockers.
- Close BG-011..BG-015 with practical smoke-level coverage and scripts.
- Close BG-016..BG-017 in `/docs/beta/` and `BETA_RELEASE.md`.
