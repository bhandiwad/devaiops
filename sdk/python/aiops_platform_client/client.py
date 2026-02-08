from __future__ import annotations

from typing import Any
import requests


class AIOpsClient:
    def __init__(self, base_url: str, token: str | None = None, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        resp = requests.request(method, f"{self.base_url}{path}", headers=headers, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json() if resp.text else None

    def delete_api_v1_tenants_tenant_id(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('DELETE', '/api/v1/tenants/{tenant_id}', payload=payload)

    def delete_api_v1_tenants_tenant_id_subscriptions_subscription_id(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('DELETE', '/api/v1/tenants/{tenant_id}/subscriptions/{subscription_id}', payload=payload)

    def get_api_v1_aiops_investigator_health(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/aiops/investigator/health', payload=payload)

    def get_api_v1_events(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/events', payload=payload)

    def get_api_v1_me(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/me', payload=payload)

    def get_api_v1_modules(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/modules', payload=payload)

    def get_api_v1_platform_dr_status(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/platform/dr/status', payload=payload)

    def get_api_v1_platform_metering_summary(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/platform/metering/summary', payload=payload)

    def get_api_v1_platform_upgrade_plan(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/platform/upgrade/plan', payload=payload)

    def get_api_v1_platform_version(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/platform/version', payload=payload)

    def get_api_v1_products(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/products', payload=payload)

    def get_api_v1_provider_profiles(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/provider-profiles', payload=payload)

    def get_api_v1_runbooks(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/runbooks', payload=payload)

    def get_api_v1_search(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/search', payload=payload)

    def get_api_v1_tenants(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants', payload=payload)

    def get_api_v1_tenants_tenant_id(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}', payload=payload)

    def get_api_v1_tenants_tenant_id_access_requests(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/access/requests', payload=payload)

    def get_api_v1_tenants_tenant_id_audit(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/audit', payload=payload)

    def get_api_v1_tenants_tenant_id_deployments(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/deployments', payload=payload)

    def get_api_v1_tenants_tenant_id_drift(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/drift', payload=payload)

    def get_api_v1_tenants_tenant_id_drift_history(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/drift/history', payload=payload)

    def get_api_v1_tenants_tenant_id_events(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/events', payload=payload)

    def get_api_v1_tenants_tenant_id_exports(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/exports', payload=payload)

    def get_api_v1_tenants_tenant_id_exports_export_id_download(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/exports/{export_id}/download', payload=payload)

    def get_api_v1_tenants_tenant_id_finops_summary(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/finops/summary', payload=payload)

    def get_api_v1_tenants_tenant_id_incidents(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/incidents', payload=payload)

    def get_api_v1_tenants_tenant_id_incidents_incident_id(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}', payload=payload)

    def get_api_v1_tenants_tenant_id_incidents_incident_id_timeline(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/timeline', payload=payload)

    def get_api_v1_tenants_tenant_id_metering(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/metering', payload=payload)

    def get_api_v1_tenants_tenant_id_onboarding_progress(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/onboarding/progress', payload=payload)

    def get_api_v1_tenants_tenant_id_policy_decisions(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/policy-decisions', payload=payload)

    def get_api_v1_tenants_tenant_id_services_service_id_promotions(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/services/{service_id}/promotions', payload=payload)

    def get_api_v1_tenants_tenant_id_status(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/status', payload=payload)

    def get_api_v1_tenants_tenant_id_subscriptions(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('GET', '/api/v1/tenants/{tenant_id}/subscriptions', payload=payload)

    def post_api_v1_platform_dr_verify(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/platform/dr/verify', payload=payload)

    def post_api_v1_platform_upgrade_apply(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/platform/upgrade/apply', payload=payload)

    def post_api_v1_tenants(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants', payload=payload)

    def post_api_v1_tenants_tenant_id_access_requests(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/access/requests', payload=payload)

    def post_api_v1_tenants_tenant_id_access_requests_request_id_approve(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/access/requests/{request_id}/approve', payload=payload)

    def post_api_v1_tenants_tenant_id_access_requests_request_id_deny(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/access/requests/{request_id}/deny', payload=payload)

    def post_api_v1_tenants_tenant_id_deployments_service_id_rollback(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/deployments/{service_id}/rollback', payload=payload)

    def post_api_v1_tenants_tenant_id_deployments_service_id_sync(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/deployments/{service_id}/sync', payload=payload)

    def post_api_v1_tenants_tenant_id_drift_run(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/drift/run', payload=payload)

    def post_api_v1_tenants_tenant_id_exports(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/exports', payload=payload)

    def post_api_v1_tenants_tenant_id_incidents(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/incidents', payload=payload)

    def post_api_v1_tenants_tenant_id_incidents_incident_id_create_pr(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/create-pr', payload=payload)

    def post_api_v1_tenants_tenant_id_incidents_incident_id_create_ticket(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/create-ticket', payload=payload)

    def post_api_v1_tenants_tenant_id_incidents_incident_id_evidence(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/evidence', payload=payload)

    def post_api_v1_tenants_tenant_id_incidents_incident_id_investigate(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/investigate', payload=payload)

    def post_api_v1_tenants_tenant_id_incidents_incident_id_notify(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/notify', payload=payload)

    def post_api_v1_tenants_tenant_id_incidents_incident_id_transition(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/transition', payload=payload)

    def post_api_v1_tenants_tenant_id_metering_collect(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/metering/collect', payload=payload)

    def post_api_v1_tenants_tenant_id_onboard(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/onboard', payload=payload)

    def post_api_v1_tenants_tenant_id_plan(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/plan', payload=payload)

    def post_api_v1_tenants_tenant_id_products_product_id_disable(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/products/{product_id}/disable', payload=payload)

    def post_api_v1_tenants_tenant_id_products_product_id_enable(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/products/{product_id}/enable', payload=payload)

    def post_api_v1_tenants_tenant_id_scaffold(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/scaffold', payload=payload)

    def post_api_v1_tenants_tenant_id_services_service_id_promote(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/services/{service_id}/promote', payload=payload)

    def post_api_v1_tenants_tenant_id_subscriptions(self, payload: dict[str, Any] | None = None) -> Any:
        return self._request('POST', '/api/v1/tenants/{tenant_id}/subscriptions', payload=payload)
