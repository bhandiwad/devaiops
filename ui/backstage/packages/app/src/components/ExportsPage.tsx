import React, { useEffect, useState } from 'react';
import { Table, Progress, Button } from '@backstage/core-components';
import { asArray, platformFetch } from './common/platformApi';
import { EmptyState, ErrorState } from './common/StatePanels';

export function ExportsPage() {
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

  async function loadExports(selected: string) {
    if (!selected) return;
    const resp = await platformFetch(`/tenants/${selected}/exports`);
    if (!resp.ok) {
      throw new Error(`Failed to load exports: HTTP ${resp.status}`);
    }
    setRows(asArray(await resp.json()));
  }

  async function createExport() {
    if (!tenantId) return;
    const resp = await platformFetch(`/tenants/${tenantId}/exports`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
    if (!resp.ok) {
      throw new Error(`Failed to create export: HTTP ${resp.status}`);
    }
    await loadExports(tenantId);
  }

  async function downloadExport(exportId: string) {
    const resp = await platformFetch(`/tenants/${tenantId}/exports/${exportId}/download`);
    if (!resp.ok) {
      throw new Error(`Failed to download export: HTTP ${resp.status}`);
    }
    const data = await resp.json();
    const binary = atob(data.content_base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: 'application/zip' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = data.filename || 'export.zip';
    a.click();
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    loadTenants().catch(e => setError(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadExports(tenantId).catch(e => setError(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  if (error) return <ErrorState error={error} />;
  if (!tenants.length) return <EmptyState title="No tenants available" description="Create a tenant from Onboarding before creating exports." />;
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
        <Button onClick={createExport} style={{ marginLeft: 12 }}>
          Create Export
        </Button>
      </div>
      <Table
        title="Exports"
        columns={[
          { title: 'Export ID', field: 'export_id' },
          { title: 'Status', field: 'status' },
          { title: 'Created At', field: 'created_at' },
          {
            title: 'Download',
            field: 'download',
            render: row => (
              <Button onClick={() => downloadExport(row.export_id)} disabled={!row.artifact_ref}>
                Download
              </Button>
            ),
          },
        ]}
        data={rows}
        options={{ paging: false }}
      />
    </>
  );
}
