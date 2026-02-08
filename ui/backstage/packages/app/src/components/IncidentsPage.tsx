import React, { useEffect, useMemo, useState } from 'react';
import { Button, Table } from '@backstage/core-components';
import { asArray, platformFetch } from './common/platformApi';
import { EmptyState, ErrorState, LoadingState } from './common/StatePanels';

export function IncidentsPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [selected, setSelected] = useState<any | null>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [health, setHealth] = useState<string>('unknown');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const resp = await platformFetch('/tenants?limit=200');
      if (!resp.ok) throw new Error(`Failed loading tenants: HTTP ${resp.status}`);
      const tenants = asArray(await resp.json());
      const incidents: any[] = [];
      for (const tenant of tenants) {
        const incResp = await platformFetch(`/tenants/${tenant.tenant_id}/incidents?limit=200`);
        if (!incResp.ok) continue;
        const data = asArray(await incResp.json());
        data.forEach((item: any) => incidents.push({ ...item, tenant_id: tenant.tenant_id }));
      }
      setRows(incidents);
    } catch (e: any) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  async function checkHealth() {
    const resp = await platformFetch('/aiops/investigator/health');
    if (!resp.ok) {
      setHealth('unavailable');
      return;
    }
    const data = await resp.json();
    const mode = data.mode ? ` (${data.mode})` : '';
    setHealth((data.status || 'unknown') + mode);
  }

  async function loadTimeline(tenantId: string, incidentId: string) {
    const resp = await platformFetch(`/tenants/${tenantId}/incidents/${incidentId}/timeline`);
    if (!resp.ok) {
      setTimeline([]);
      return;
    }
    setTimeline(asArray(await resp.json()));
  }

  async function runAction(action: 'evidence' | 'investigate' | 'create-pr' | 'close') {
    if (!selected) return;
    setLoading(true);
    setError(null);
    try {
      if (action === 'close') {
        await platformFetch(`/tenants/${selected.tenant_id}/incidents/${selected.incident_id}/transition`, {
          method: 'POST',
          body: JSON.stringify({ to_status: 'CLOSED', detail: { source: 'ui' } }),
        });
      } else {
        await platformFetch(`/tenants/${selected.tenant_id}/incidents/${selected.incident_id}/${action}`, {
          method: 'POST',
        });
      }
      await refresh();
      await loadTimeline(selected.tenant_id, selected.incident_id);
    } catch (e: any) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh().catch(e => setError(e));
    checkHealth().catch(() => setHealth('unavailable'));
  }, []);

  useEffect(() => {
    if (selected) {
      loadTimeline(selected.tenant_id, selected.incident_id);
    } else {
      setTimeline([]);
    }
  }, [selected?.incident_id]);

  const summary = useMemo(() => {
    const byStatus: Record<string, number> = {};
    rows.forEach(r => {
      byStatus[r.status] = (byStatus[r.status] || 0) + 1;
    });
    return byStatus;
  }, [rows]);

  if (loading && rows.length === 0) return <LoadingState message="Loading incidents and timelines" />;
  if (error && rows.length === 0) return <ErrorState error={error} />;

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <Button onClick={refresh}>Refresh</Button>
        <Button onClick={checkHealth}>Investigator: {health}</Button>
        <span style={{ marginLeft: 8 }}>Status totals: {Object.entries(summary).map(([k, v]) => `${k}=${v}`).join(', ') || 'none'}</span>
      </div>

      {rows.length === 0 ? (
        <EmptyState title="No incidents" description="Ingest an incident to start evidence collection and investigation." />
      ) : (
        <Table
          title="Incidents"
          columns={[
            { title: 'Incident', field: 'incident_id' },
            { title: 'Tenant', field: 'tenant_id' },
            { title: 'Status', field: 'status' },
            { title: 'Alert', field: 'alert_name' },
          ]}
          data={rows}
          options={{ paging: true, pageSize: 20 }}
          onRowClick={(_event, row) => setSelected(row)}
        />
      )}

      {selected && (
        <div style={{ marginTop: 16 }}>
          <h4>Incident Workflow: {selected.incident_id}</h4>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <Button onClick={() => runAction('evidence')}>Collect Evidence</Button>
            <Button onClick={() => runAction('investigate')}>Investigate</Button>
            <Button onClick={() => runAction('create-pr')}>Create PR</Button>
            <Button onClick={() => runAction('close')}>Close</Button>
          </div>
          <Table
            title="Incident Timeline"
            columns={[
              { title: 'From', field: 'from_status' },
              { title: 'To', field: 'to_status' },
              { title: 'At', field: 'created_at' },
            ]}
            data={timeline}
            options={{ paging: true, pageSize: 10 }}
          />
        </div>
      )}
      {error && <ErrorState error={error} />}
    </div>
  );
}
