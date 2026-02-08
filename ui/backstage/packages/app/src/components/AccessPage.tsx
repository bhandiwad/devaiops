import React, { useEffect, useState } from 'react';
import { Button, Table } from '@backstage/core-components';
import { asArray, platformFetch } from './common/platformApi';
import { EmptyState, ErrorState } from './common/StatePanels';

export function AccessPage() {
  const [tenantId, setTenantId] = useState('');
  const [tenants, setTenants] = useState<any[]>([]);
  const [rows, setRows] = useState<any[]>([]);
  const [error, setError] = useState<Error | null>(null);

  async function load() {
    const t = await platformFetch('/tenants');
    if (!t.ok) {
      throw new Error(`Failed to load tenants: HTTP ${t.status}`);
    }
    const tenantsData = asArray(await t.json());
    setTenants(tenantsData);
    if (tenantsData.length && !tenantId) setTenantId(tenantsData[0].tenant_id);
  }

  async function loadRequests(selected: string) {
    if (!selected) return;
    const r = await platformFetch(`/tenants/${selected}/access/requests`);
    if (!r.ok) {
      throw new Error(`Failed to load access requests: HTTP ${r.status}`);
    }
    setRows(asArray(await r.json()));
  }

  async function createRequest(role: string) {
    if (!tenantId) return;
    const resp = await platformFetch(`/tenants/${tenantId}/access/requests`, {
      method: 'POST',
      body: JSON.stringify({ requested_role: role, justification: 'Self-service request' }),
    });
    if (!resp.ok) {
      throw new Error(`Failed to create access request: HTTP ${resp.status}`);
    }
    await loadRequests(tenantId);
  }

  async function decide(requestId: string, action: 'approve' | 'deny') {
    const resp = await platformFetch(`/tenants/${tenantId}/access/requests/${requestId}/${action}`, { method: 'POST' });
    if (!resp.ok) {
      throw new Error(`Failed to ${action} access request: HTTP ${resp.status}`);
    }
    await loadRequests(tenantId);
  }

  useEffect(() => {
    load().catch(e => setError(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadRequests(tenantId).catch(e => setError(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  if (error) return <ErrorState error={error} />;
  if (!tenants.length) return <EmptyState title="No tenants available" description="Create a tenant from Onboarding before managing access requests." />;

  return (
    <>
      <div style={{ marginBottom: 12 }}>
        <label htmlFor="tenant">Tenant:</label>{' '}
        <select id="tenant" value={tenantId} onChange={e => setTenantId(e.target.value)}>
          {tenants.map(t => (
            <option key={t.tenant_id} value={t.tenant_id}>{t.display_name || t.tenant_id}</option>
          ))}
        </select>
        <Button style={{ marginLeft: 10 }} onClick={() => createRequest('tenant_operator')}>Request Operator</Button>
        <Button style={{ marginLeft: 10 }} onClick={() => createRequest('tenant_admin')}>Request Admin</Button>
      </div>
      <Table
        title="Access Requests"
        columns={[
          { title: 'Principal', field: 'principal' },
          { title: 'Role', field: 'requested_role' },
          { title: 'Status', field: 'status' },
          { title: 'Created', field: 'created_at' },
          {
            title: 'Actions',
            field: 'actions',
            render: r => (
              <>
                <Button onClick={() => decide(r.request_id, 'approve')}>Approve</Button>
                <Button onClick={() => decide(r.request_id, 'deny')} style={{ marginLeft: 8 }}>Deny</Button>
              </>
            ),
          },
        ]}
        data={rows}
        options={{ paging: false }}
      />
    </>
  );
}
