
# Postgres data model (MVP)

## Tables (recommended)
- tenants
- clusters
- services
- deployments (cached status snapshots)
- incidents
- remediation_prs
- access_bindings
- audit_events (append-only)
- provider_profiles (cached from config repo)
- module_descriptors (cached from config repo)

## Design rules
- audit_events is immutable (append-only) and indexed by tenant_id, timestamp, correlation_id
- do not store secrets in Postgres
- store only references/IDs to secret paths, PR links, dashboard IDs, etc.

See db/schema.sql for a starter DDL.
