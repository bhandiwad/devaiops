# Known Limitations and Roadmap

## Current beta limitations
- Some external integrations remain generic webhook adapters (ticketing/messaging)
- Deployment rollback is guided GitOps revert workflow (not direct in-cluster mutation)
- UI test suite is smoke-level, not full e2e browser coverage
- OpenAPI is stable for v1 but legacy non-v1 routes are still mounted for compatibility

## Near-term roadmap
- Expand runbook execution UX and typed input forms
- Add richer deployment diff views and revision history
- Add production-grade inbound webhook handlers for common systems
- Add publish pipeline for SDK packages

## Bug reporting
- Include `correlation_id`, endpoint path, tenant id, and reproduction steps
