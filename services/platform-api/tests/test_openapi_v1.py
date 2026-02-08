from __future__ import annotations

from main import create_app


def test_openapi_contains_v1_paths_and_error_shape():
    app = create_app()
    spec = app.openapi()
    assert "/api/v1/tenants" in spec["paths"]
    assert "/api/v1/events" in spec["paths"]
    assert "/api/v1/tenants/{tenant_id}/subscriptions" in spec["paths"]
    assert "/api/v1/tenants/{tenant_id}/incidents/{incident_id}/timeline" in spec["paths"]
    assert "/api/v1/search" in spec["paths"]
    assert "/api/v1/tenants/{tenant_id}/onboarding/progress" in spec["paths"]
    assert "/api/v1/tenants/{tenant_id}/deployments" in spec["paths"]
