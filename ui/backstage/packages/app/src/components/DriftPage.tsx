import React, { useEffect, useState } from 'react';
import { Table, Progress, Button } from '@backstage/core-components';
import { platformFetch } from './common/platformApi';
import { EmptyState, ErrorState } from './common/StatePanels';

export function DriftPage() {
  const [tenants, setTenants] = useState<any[]>([]);
  const [tenantId, setTenantId] = useState<string>('');
  const [summaryRows, setSummaryRows] = useState<any[]>([]);
  const [error, setError] = useState<Error | null>(null);

  async function loadTenants() {
    const resp = await platformFetch('/tenants');
    if (!resp.ok) {
      throw new Error(`Failed to load tenants: HTTP ${resp.status}`);
    }
    const data = await resp.json();
    setTenants(data);
    if (data.length && !tenantId) {
      setTenantId(data[0].tenant_id);
    }
  }

  async function loadSummary(selected: string) {
    if (!selected) return;
    const resp = await platformFetch(`/tenants/${selected}/drift`);
    if (!resp.ok) {
      throw new Error(`Failed to load drift summary: HTTP ${resp.status}`);
    }
    const data = await resp.json();
    const rows = Object.keys(data.detectors || {}).map(key => ({
      detector: key,
      status: data.detectors[key].status,
      summary: JSON.stringify(data.detectors[key].summary || {}),
    }));
    setSummaryRows(rows);
  }

  async function runDrift() {
    if (!tenantId) return;
    const resp = await platformFetch(`/tenants/${tenantId}/drift/run`, {
      method: 'POST',
    });
    if (!resp.ok) {
      throw new Error(`Failed to run drift: HTTP ${resp.status}`);
    }
    await loadSummary(tenantId);
  }

  useEffect(() => {
    loadTenants().catch(e => setError(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadSummary(tenantId).catch(e => setError(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  if (error) return <ErrorState error={error} />;
  if (!tenants.length) return <EmptyState title="No tenants available" description="Create a tenant from Onboarding before running drift checks." />;
  if (!tenantId) return <Progress />;

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <label htmlFor="tenant-select">Tenant:</label>{' '}
        <select
          id="tenant-select"
          value={tenantId}
          onChange={e => setTenantId(e.target.value)}
        >
          {tenants.map(t => (
            <option key={t.tenant_id} value={t.tenant_id}>
              {t.display_name || t.tenant_id}
            </option>
          ))}
        </select>
        <Button onClick={runDrift} style={{ marginLeft: 12 }}>
          Run Drift
        </Button>
      </div>
      <Table
        title="Drift Summary"
        columns={[
          { title: 'Detector', field: 'detector' },
          { title: 'Status', field: 'status' },
          { title: 'Summary', field: 'summary' },
        ]}
        data={summaryRows}
        options={{ paging: false }}
      />
    </>
  );
}
