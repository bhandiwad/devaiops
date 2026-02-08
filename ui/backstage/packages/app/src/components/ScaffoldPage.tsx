import React, { useEffect, useState } from 'react';
import { Button, Progress, Table } from '@backstage/core-components';
import { asArray, platformFetch } from './common/platformApi';
import { EmptyState, ErrorState } from './common/StatePanels';

export function ScaffoldPage() {
  const [tenantId, setTenantId] = useState('');
  const [tenants, setTenants] = useState<any[]>([]);
  const [outputs, setOutputs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  async function loadTenants() {
    setLoading(true);
    setError(null);
    const t = await platformFetch('/tenants');
    if (!t.ok) throw new Error(`Failed to load tenants: HTTP ${t.status}`);
    const tenantsData = asArray(await t.json());
    setTenants(tenantsData);
    if (tenantsData.length && !tenantId) setTenantId(tenantsData[0].tenant_id);
    setLoading(false);
  }

  async function scaffold(templateId: string) {
    if (!tenantId) return;
    setError(null);
    const serviceName = `${templateId.replace(/[^a-z0-9]/g, '-')}-${Date.now().toString().slice(-5)}`;
    const resp = await platformFetch(`/tenants/${tenantId}/scaffold`, {
      method: 'POST',
      body: JSON.stringify({
        template_id: templateId,
        parameters: {
          service_name: serviceName,
          owner: 'platform-team',
          service_description: `Generated ${templateId}`,
        },
      }),
    });
    if (!resp.ok) {
      throw new Error(`Scaffold failed: HTTP ${resp.status}`);
    }
    const data = await resp.json();
    setOutputs([data, ...outputs]);
  }

  useEffect(() => {
    loadTenants().catch(e => {
      setError(e);
      setLoading(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <Progress />;
  if (error) return <ErrorState error={error} />;
  if (!tenants.length) return <EmptyState title="No tenants available" description="Create a tenant from the Onboarding page before scaffolding services." />;

  return (
    <>
      <div style={{ marginBottom: 12 }}>
        <label htmlFor="tenant">Tenant:</label>{' '}
        <select id="tenant" value={tenantId} onChange={e => setTenantId(e.target.value)}>
          {tenants.map(t => (
            <option key={t.tenant_id} value={t.tenant_id}>{t.display_name || t.tenant_id}</option>
          ))}
        </select>
        <Button style={{ marginLeft: 8 }} onClick={() => scaffold('python-fastapi')}>FastAPI</Button>
        <Button style={{ marginLeft: 8 }} onClick={() => scaffold('python-worker')}>Worker</Button>
        <Button style={{ marginLeft: 8 }} onClick={() => scaffold('react-frontend')}>React</Button>
      </div>
      <Table
        title="Scaffold Results"
        columns={[
          { title: 'Service', field: 'service_id' },
          { title: 'Repo', field: 'repo_url' },
          { title: 'PR', field: 'pr_url' },
        ]}
        data={outputs}
        options={{ paging: false }}
      />
    </>
  );
}
