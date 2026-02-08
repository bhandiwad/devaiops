import React, { useEffect, useState } from 'react';
import { Table, Progress } from '@backstage/core-components';
import { asArray, platformFetch } from './common/platformApi';
import { EmptyState, ErrorState } from './common/StatePanels';

export function GovernancePage() {
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
    if (data.length && !tenantId) {
      setTenantId(data[0].tenant_id);
    }
  }

  async function loadDecisions(selected: string) {
    if (!selected) return;
    const resp = await platformFetch(`/tenants/${selected}/policy-decisions`);
    if (!resp.ok) {
      throw new Error(`Failed to load policy decisions: HTTP ${resp.status}`);
    }
    setRows(asArray(await resp.json()));
  }

  useEffect(() => {
    loadTenants().catch(e => setError(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadDecisions(tenantId).catch(e => setError(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  if (error) return <ErrorState error={error} />;
  if (!tenants.length) return <EmptyState title="No tenants available" description="Create a tenant from Onboarding before reviewing policy decisions." />;
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
      </div>
      <Table
        title="Policy Decisions"
        columns={[
          { title: 'Action', field: 'action' },
          { title: 'Allow', field: 'allow' },
          { title: 'Reasons', field: 'reasons' },
          { title: 'Obligations', field: 'obligations' },
          { title: 'Time', field: 'created_at' },
        ]}
        data={rows}
        options={{ paging: false }}
      />
    </>
  );
}
