from __future__ import annotations

from main import create_app


def test_beta_smoke_routes_present():
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/api/v1/search" in paths
    assert "/api/v1/events" in paths
    assert "/api/v1/tenants/{tenant_id}/onboarding/progress" in paths
    assert "/api/v1/tenants/{tenant_id}/deployments" in paths
    assert "/api/v1/tenants/{tenant_id}/incidents/{incident_id}/timeline" in paths
