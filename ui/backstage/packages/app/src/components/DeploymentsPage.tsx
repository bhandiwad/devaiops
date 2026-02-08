import React, { useEffect, useState } from 'react';
import { Button, Table } from '@backstage/core-components';
import { asArray, platformFetch } from './common/platformApi';
import { EmptyState, ErrorState, LoadingState } from './common/StatePanels';

export function DeploymentsPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [tenants, setTenants] = useState<any[]>([]);
  const [selectedTenant, setSelectedTenant] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  async function loadTenants() {
    const resp = await platformFetch('/tenants?limit=200');
    if (!resp.ok) throw new Error(`Failed loading tenants: HTTP ${resp.status}`);
    const data = asArray(await resp.json());
    setTenants(data);
    if (!selectedTenant && data.length > 0) {
      setSelectedTenant(data[0].tenant_id);
    }
  }

  async function loadDeployments(tenantId: string) {
    const resp = await platformFetch(`/tenants/${tenantId}/deployments`);
    if (!resp.ok) throw new Error(`Failed loading deployments: HTTP ${resp.status}`);
    setRows(asArray(await resp.json()));
  }

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      await loadTenants();
      const tenant = selectedTenant || (tenants[0]?.tenant_id || '');
      if (tenant) {
        await loadDeployments(tenant);
      }
    } catch (e: any) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  async function runAction(serviceId: string, action: 'sync' | 'rollback') {
    if (!selectedTenant) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await platformFetch(`/tenants/${selectedTenant}/deployments/${serviceId}/${action}`, { method: 'POST' });
      if (!resp.ok) throw new Error(`${action} failed: HTTP ${resp.status}`);
      await loadDeployments(selectedTenant);
    } catch (e: any) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh().catch(e => setError(e));
  }, []);

  useEffect(() => {
    if (selectedTenant) {
      loadDeployments(selectedTenant).catch(err => setError(err));
    } else {
      setRows([]);
    }
  }, [selectedTenant]);

  if (loading && rows.length === 0) return <LoadingState message="Loading deployment health" />;
  if (error && rows.length === 0) return <ErrorState error={error} />;

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <select value={selectedTenant} onChange={e => setSelectedTenant(e.target.value)}>
          {tenants.map(t => <option key={t.tenant_id} value={t.tenant_id}>{t.tenant_id}</option>)}
        </select>
        <Button onClick={refresh}>Refresh</Button>
      </div>
      {rows.length === 0 ? (
        <EmptyState title="No deployments discovered" description="Add service definitions in TenantSpec to track deployment status." />
      ) : (
        <Table
          title="Deployments"
          columns={[
            { title: 'Service', field: 'service_id' },
            { title: 'Argo App', field: 'app_ref' },
            { title: 'Sync', render: row => row.status?.sync || 'unknown' },
            { title: 'Health', render: row => row.status?.health || 'unknown' },
            { title: 'Actions', render: row => (
              <div style={{ display: 'flex', gap: 4 }}>
                <Button onClick={() => runAction(row.service_id, 'sync')}>Sync</Button>
                <Button onClick={() => runAction(row.service_id, 'rollback')}>Rollback</Button>
              </div>
            ) },
          ]}
          data={rows}
          options={{ paging: true, pageSize: 20 }}
        />
      )}
      {error && <ErrorState error={error} />}
    </div>
  );
}
