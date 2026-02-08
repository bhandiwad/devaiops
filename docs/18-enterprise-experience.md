# Iteration 8: Enterprise Experience, Dev Portal, Marketplace

## Added capabilities
- Backstage catalog and TechDocs wiring for platform entities and docs.
- Golden-path service scaffolding through Platform API (`/tenants/{tenant_id}/scaffold`).
- PR-based environment promotions (`/tenants/{tenant_id}/services/{service_id}/promote`).
- Product marketplace with config-driven ProductDescriptors and tenant enable/disable flows.
- Self-service access request workflow with approval/deny endpoints and policy obligations.
- aiopsctl commands for scaffold, promotion, products, and access workflows.

## Data model additions
- `promotions`
- `access_requests`

## Config additions
- Product descriptors under `config/products/*.yaml`.
- `config_sources.products_path` in PlatformConfig.

## API additions
- `GET /products`
- `POST /tenants/{tenant_id}/products/{product_id}/enable`
- `POST /tenants/{tenant_id}/products/{product_id}/disable`
- `POST /tenants/{tenant_id}/access/requests`
- `GET /tenants/{tenant_id}/access/requests`
- `POST /tenants/{tenant_id}/access/requests/{request_id}/approve`
- `POST /tenants/{tenant_id}/access/requests/{request_id}/deny`
- `POST /tenants/{tenant_id}/scaffold`
- `POST /tenants/{tenant_id}/services/{service_id}/promote`
- `GET /tenants/{tenant_id}/services/{service_id}/promotions`

## Backstage additions
- Marketplace page
- Access page
- Scaffold page
- Promotions page
- Catalog + TechDocs configuration
- Scaffolder template definitions in `ui/backstage/templates/`

## Notes
- Backstage remains a thin client; policy, RBAC, and audit enforcement remain server-side.
- Promotion and remediation stay PR-only.
