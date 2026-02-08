import React, { useState } from 'react';
import { Button, Table } from '@backstage/core-components';
import { ErrorState, EmptyState, LoadingState } from './common/StatePanels';
import { platformFetch } from './common/platformApi';

export function OnboardingWizardPage() {
  const [tenantId, setTenantId] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [mode, setMode] = useState('BYOC');
  const [providerProfileId, setProviderProfileId] = useState('generic-k8s-on-vms');
  const [created, setCreated] = useState<any | null>(null);
  const [progress, setProgress] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  async function createTenant() {
    setLoading(true);
    setError(null);
    try {
      const resp = await platformFetch('/tenants', {
        method: 'POST',
        body: JSON.stringify({ tenant_id: tenantId, display_name: displayName || tenantId, mode, provider_profile_id: providerProfileId }),
      });
      if (!resp.ok) {
        throw new Error(`Create tenant failed: HTTP ${resp.status}`);
      }
      const data = await resp.json();
      setCreated(data);
      await loadProgress(data.tenant_id);
    } catch (e: any) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  async function loadProgress(id: string) {
    const resp = await platformFetch(`/tenants/${id}/onboarding/progress`);
    if (!resp.ok) {
      throw new Error(`Progress fetch failed: HTTP ${resp.status}`);
    }
    setProgress(await resp.json());
  }

  async function refreshProgress() {
    if (!created?.tenant_id) return;
    setLoading(true);
    setError(null);
    try {
      await loadProgress(created.tenant_id);
    } catch (e: any) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h3>Tenant Onboarding Wizard</h3>
      <p>Choose onboarding mode, submit tenant creation, then monitor pipeline progress and failures.</p>
      <div style={{ display: 'grid', gap: 8, maxWidth: 640 }}>
        <label>Tenant ID<input value={tenantId} onChange={e => setTenantId(e.target.value)} /></label>
        <label>Display Name<input value={displayName} onChange={e => setDisplayName(e.target.value)} /></label>
        <label>Provider Profile<input value={providerProfileId} onChange={e => setProviderProfileId(e.target.value)} /></label>
        <label>Mode
          <select value={mode} onChange={e => setMode(e.target.value)}>
            <option value="BYOC">BYOC</option>
            <option value="PROVISIONED">PROVISIONED</option>
          </select>
        </label>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button disabled={!tenantId || !providerProfileId || loading} onClick={createTenant}>Create & Start Onboarding</Button>
          <Button disabled={!created || loading} onClick={refreshProgress}>Refresh Progress</Button>
        </div>
      </div>
      {loading && <LoadingState message="Processing onboarding workflow" />}
      {error && <ErrorState error={error} />}
      {!loading && !error && created && !progress && <EmptyState title="Tenant created" description="Progress will appear after first status transition." />}
      {!loading && !error && progress && (
        <div style={{ marginTop: 16 }}>
          <h4>Status: {progress.status}</h4>
          <Table
            title="Status History"
            columns={[
              { title: 'From', field: 'from_status' },
              { title: 'To', field: 'to_status' },
              { title: 'At', field: 'occurred_at' },
            ]}
            data={progress.history || []}
            options={{ paging: true, pageSize: 10 }}
          />
          <Table
            title="Recent Audit Events"
            columns={[
              { title: 'Action', field: 'action' },
              { title: 'Principal', field: 'principal' },
              { title: 'At', field: 'created_at' },
            ]}
            data={progress.recent_audit || []}
            options={{ paging: true, pageSize: 10 }}
          />
        </div>
      )}
    </div>
  );
}
