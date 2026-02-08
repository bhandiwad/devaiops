export class AIOpsClient {
  constructor(private readonly baseUrl: string, private readonly token?: string) {}

  private async request(method: string, path: string, payload?: unknown): Promise<unknown> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;
    const res = await fetch(`${this.baseUrl.replace(/\/$/, '')}${path}`, {
      method,
      headers,
      body: payload ? JSON.stringify(payload) : undefined,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text().then((t) => (t ? JSON.parse(t) : null));
  }

  async delete_api_v1_tenants_tenant_id(payload?: unknown): Promise<unknown> {
    return this.request('DELETE', '/api/v1/tenants/{tenant_id}', payload);
  }

  async delete_api_v1_tenants_tenant_id_subscriptions_subscription_id(payload?: unknown): Promise<unknown> {
    return this.request('DELETE', '/api/v1/tenants/{tenant_id}/subscriptions/{subscription_id}', payload);
  }

  async get_api_v1_aiops_investigator_health(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/aiops/investigator/health', payload);
  }

  async get_api_v1_events(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/events', payload);
  }

  async get_api_v1_me(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/me', payload);
  }

  async get_api_v1_modules(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/modules', payload);
  }

  async get_api_v1_platform_dr_status(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/platform/dr/status', payload);
  }

  async get_api_v1_platform_metering_summary(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/platform/metering/summary', payload);
  }

  async get_api_v1_platform_upgrade_plan(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/platform/upgrade/plan', payload);
  }

  async get_api_v1_platform_version(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/platform/version', payload);
  }

  async get_api_v1_products(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/products', payload);
  }

  async get_api_v1_provider_profiles(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/provider-profiles', payload);
  }

  async get_api_v1_runbooks(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/runbooks', payload);
  }

  async get_api_v1_search(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/search', payload);
  }

  async get_api_v1_tenants(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants', payload);
  }

  async get_api_v1_tenants_tenant_id(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}', payload);
  }

  async get_api_v1_tenants_tenant_id_access_requests(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/access/requests', payload);
  }

  async get_api_v1_tenants_tenant_id_audit(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/audit', payload);
  }

  async get_api_v1_tenants_tenant_id_deployments(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/deployments', payload);
  }

  async get_api_v1_tenants_tenant_id_drift(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/drift', payload);
  }

  async get_api_v1_tenants_tenant_id_drift_history(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/drift/history', payload);
  }

  async get_api_v1_tenants_tenant_id_events(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/events', payload);
  }

  async get_api_v1_tenants_tenant_id_exports(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/exports', payload);
  }

  async get_api_v1_tenants_tenant_id_exports_export_id_download(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/exports/{export_id}/download', payload);
  }

  async get_api_v1_tenants_tenant_id_finops_summary(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/finops/summary', payload);
  }

  async get_api_v1_tenants_tenant_id_incidents(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/incidents', payload);
  }

  async get_api_v1_tenants_tenant_id_incidents_incident_id(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}', payload);
  }

  async get_api_v1_tenants_tenant_id_incidents_incident_id_timeline(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/timeline', payload);
  }

  async get_api_v1_tenants_tenant_id_metering(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/metering', payload);
  }

  async get_api_v1_tenants_tenant_id_onboarding_progress(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/onboarding/progress', payload);
  }

  async get_api_v1_tenants_tenant_id_policy_decisions(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/policy-decisions', payload);
  }

  async get_api_v1_tenants_tenant_id_services_service_id_promotions(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/services/{service_id}/promotions', payload);
  }

  async get_api_v1_tenants_tenant_id_status(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/status', payload);
  }

  async get_api_v1_tenants_tenant_id_subscriptions(payload?: unknown): Promise<unknown> {
    return this.request('GET', '/api/v1/tenants/{tenant_id}/subscriptions', payload);
  }

  async post_api_v1_platform_dr_verify(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/platform/dr/verify', payload);
  }

  async post_api_v1_platform_upgrade_apply(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/platform/upgrade/apply', payload);
  }

  async post_api_v1_tenants(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants', payload);
  }

  async post_api_v1_tenants_tenant_id_access_requests(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/access/requests', payload);
  }

  async post_api_v1_tenants_tenant_id_access_requests_request_id_approve(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/access/requests/{request_id}/approve', payload);
  }

  async post_api_v1_tenants_tenant_id_access_requests_request_id_deny(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/access/requests/{request_id}/deny', payload);
  }

  async post_api_v1_tenants_tenant_id_deployments_service_id_rollback(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/deployments/{service_id}/rollback', payload);
  }

  async post_api_v1_tenants_tenant_id_deployments_service_id_sync(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/deployments/{service_id}/sync', payload);
  }

  async post_api_v1_tenants_tenant_id_drift_run(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/drift/run', payload);
  }

  async post_api_v1_tenants_tenant_id_exports(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/exports', payload);
  }

  async post_api_v1_tenants_tenant_id_incidents(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/incidents', payload);
  }

  async post_api_v1_tenants_tenant_id_incidents_incident_id_create_pr(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/create-pr', payload);
  }

  async post_api_v1_tenants_tenant_id_incidents_incident_id_create_ticket(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/create-ticket', payload);
  }

  async post_api_v1_tenants_tenant_id_incidents_incident_id_evidence(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/evidence', payload);
  }

  async post_api_v1_tenants_tenant_id_incidents_incident_id_investigate(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/investigate', payload);
  }

  async post_api_v1_tenants_tenant_id_incidents_incident_id_notify(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/notify', payload);
  }

  async post_api_v1_tenants_tenant_id_incidents_incident_id_transition(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/incidents/{incident_id}/transition', payload);
  }

  async post_api_v1_tenants_tenant_id_metering_collect(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/metering/collect', payload);
  }

  async post_api_v1_tenants_tenant_id_onboard(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/onboard', payload);
  }

  async post_api_v1_tenants_tenant_id_plan(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/plan', payload);
  }

  async post_api_v1_tenants_tenant_id_products_product_id_disable(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/products/{product_id}/disable', payload);
  }

  async post_api_v1_tenants_tenant_id_products_product_id_enable(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/products/{product_id}/enable', payload);
  }

  async post_api_v1_tenants_tenant_id_scaffold(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/scaffold', payload);
  }

  async post_api_v1_tenants_tenant_id_services_service_id_promote(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/services/{service_id}/promote', payload);
  }

  async post_api_v1_tenants_tenant_id_subscriptions(payload?: unknown): Promise<unknown> {
    return this.request('POST', '/api/v1/tenants/{tenant_id}/subscriptions', payload);
  }

}