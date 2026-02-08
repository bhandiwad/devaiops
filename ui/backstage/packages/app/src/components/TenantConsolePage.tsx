import React, { useEffect, useState } from 'react';
import { Button, Table } from '@backstage/core-components';
import { EmptyState, ErrorState, LoadingState } from './common/StatePanels';
import { asArray, platformFetch } from './common/platformApi';

export function TenantConsolePage() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const resp = await platformFetch('/tenants?limit=200');
      if (!resp.ok) throw new Error(`Failed to fetch tenants: HTTP ${resp.status}`);
      setRows(asArray(await resp.json()));
    } catch (e: any) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) return <LoadingState message="Loading tenant inventory" />;
  if (error) return <ErrorState error={error} />;
  if (rows.length === 0) return <EmptyState title="No tenants found" description="Use Onboarding to create your first tenant." action={<Button onClick={load}>Refresh</Button>} />;

  return (
    <div>
      <Button onClick={load}>Refresh</Button>
      <Table
        title="Tenants"
        columns={[
          { title: 'Tenant ID', field: 'tenant_id' },
          { title: 'Display Name', field: 'display_name' },
          { title: 'Mode', field: 'mode' },
          { title: 'Status', field: 'status' },
        ]}
        data={rows}
        options={{ paging: true, pageSize: 25 }}
      />
    </div>
  );
}
