import React, { useEffect, useState } from 'react';
import { Table, Progress, Button } from '@backstage/core-components';
import { asArray, platformFetch } from './common/platformApi';
import { EmptyState, ErrorState } from './common/StatePanels';

export function TenantUsagePage() {
  const [tenants, setTenants] = useState<any[]>([]);
  const [tenantId, setTenantId] = useState<string>('');
  const [rows, setRows] = useState<any[]>([]);
  const [error, setError] = useState<Error | null>(null);

  async function loadTenants() {
    const resp = await platformFetch('/tenants');
    if (!resp.ok) {
      throw new Error(`Failed to load tenants: HTTP ${resp.status}`);
    }
    const data = asArray(await resp.json());
    setTenants(data);
    if (data.length && !tenantId) setTenantId(data[0].tenant_id);
  }

  async function loadMetering(selected: string) {
    if (!selected) return;
    const resp = await platformFetch(`/tenants/${selected}/metering?granularity=daily`);
    if (!resp.ok) {
      throw new Error(`Failed to load metering: HTTP ${resp.status}`);
    }
    setRows(asArray(await resp.json()));
  }

  async function collectNow() {
    if (!tenantId) return;
    const resp = await platformFetch(`/tenants/${tenantId}/metering/collect`, {
      method: 'POST',
    });
    if (!resp.ok) {
      throw new Error(`Failed to collect metering: HTTP ${resp.status}`);
    }
    await loadMetering(tenantId);
  }

  useEffect(() => {
    loadTenants().catch(e => setError(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadMetering(tenantId).catch(e => setError(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  if (error) return <ErrorState error={error} />;
  if (!tenants.length) return <EmptyState title="No tenants available" description="Create a tenant from Onboarding before collecting usage." />;
  if (!tenantId) return <Progress />;

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <label htmlFor="tenant-id">Tenant:</label>{' '}
        <select id="tenant-id" value={tenantId} onChange={e => setTenantId(e.target.value)}>
          {tenants.map(t => (
            <option key={t.tenant_id} value={t.tenant_id}>
              {t.display_name || t.tenant_id}
            </option>
          ))}
        </select>
        <Button onClick={collectNow} style={{ marginLeft: 12 }}>
          Collect Usage
        </Button>
      </div>
      <Table
        title="Tenant Usage"
        columns={[
          { title: 'Period Start', field: 'period_start' },
          { title: 'Period End', field: 'period_end' },
          { title: 'Granularity', field: 'granularity' },
          { title: 'Metrics', field: 'metrics', render: r => JSON.stringify(r.metrics) },
        ]}
        data={rows}
        options={{ paging: false }}
      />
    </>
  );
}
