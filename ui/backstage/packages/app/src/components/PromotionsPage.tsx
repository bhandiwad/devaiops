import React, { useEffect, useState } from 'react';
import { Button, Table } from '@backstage/core-components';
import { asArray, platformFetch } from './common/platformApi';
import { EmptyState, ErrorState } from './common/StatePanels';

export function PromotionsPage() {
  const [tenantId, setTenantId] = useState('');
  const [serviceId, setServiceId] = useState('inventory');
  const [tenants, setTenants] = useState<any[]>([]);
  const [rows, setRows] = useState<any[]>([]);
  const [error, setError] = useState<Error | null>(null);

  async function loadTenants() {
    const t = await platformFetch('/tenants');
    if (!t.ok) {
      throw new Error(`Failed to load tenants: HTTP ${t.status}`);
    }
    const data = asArray(await t.json());
    setTenants(data);
    if (data.length && !tenantId) setTenantId(data[0].tenant_id);
  }

  async function loadPromotions() {
    if (!tenantId || !serviceId) return;
    const r = await platformFetch(`/tenants/${tenantId}/services/${serviceId}/promotions`);
    if (!r.ok) {
      throw new Error(`Failed to load promotions: HTTP ${r.status}`);
    }
    setRows(asArray(await r.json()));
  }

  async function promote(fromEnv: string, toEnv: string) {
    if (!tenantId || !serviceId) return;
    const resp = await platformFetch(`/tenants/${tenantId}/services/${serviceId}/promote?from_env=${fromEnv}&to_env=${toEnv}`, { method: 'POST' });
    if (!resp.ok) {
      throw new Error(`Promotion failed: HTTP ${resp.status}`);
    }
    await loadPromotions();
  }

  useEffect(() => {
    loadTenants().catch(e => setError(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadPromotions().catch(e => setError(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId, serviceId]);

  if (error) return <ErrorState error={error} />;
  if (!tenants.length) return <EmptyState title="No tenants available" description="Create a tenant from Onboarding to use promotions." />;

  return (
    <>
      <div style={{ marginBottom: 12 }}>
        <label htmlFor="tenant">Tenant:</label>{' '}
        <select id="tenant" value={tenantId} onChange={e => setTenantId(e.target.value)}>
          {tenants.map(t => (
            <option key={t.tenant_id} value={t.tenant_id}>{t.display_name || t.tenant_id}</option>
          ))}
        </select>
        <label htmlFor="service" style={{ marginLeft: 10 }}>Service:</label>{' '}
        <input id="service" value={serviceId} onChange={e => setServiceId(e.target.value)} />
        <Button style={{ marginLeft: 10 }} onClick={() => promote('dev', 'stage')}>Promote to Stage</Button>
        <Button style={{ marginLeft: 10 }} onClick={() => promote('stage', 'prod')}>Promote to Prod</Button>
      </div>
      <Table
        title="Promotions"
        columns={[
          { title: 'From', field: 'from_env' },
          { title: 'To', field: 'to_env' },
          { title: 'Status', field: 'status' },
          { title: 'PR', field: 'pr_url' },
          { title: 'Created', field: 'created_at' },
        ]}
        data={rows}
        options={{ paging: false }}
      />
    </>
  );
}
