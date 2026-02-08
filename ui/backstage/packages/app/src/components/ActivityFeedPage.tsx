import React, { useEffect, useState } from 'react';
import { ErrorState, EmptyState, LoadingState } from './common/StatePanels';
import { asArray, platformFetch } from './common/platformApi';

export function ActivityFeedPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const resp = await platformFetch('/events?limit=200');
      if (!resp.ok) {
        throw new Error(`Failed to load activity feed: HTTP ${resp.status}`);
      }
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

  if (loading) return <LoadingState message="Loading activity feed" />;
  if (error) return <ErrorState error={error} />;
  if (rows.length === 0) return <EmptyState title="No events yet" description="Platform events will appear here after tenant or service activity." action={<button type="button" onClick={load}>Refresh</button>} />;

  return (
    <div>
      <button type="button" onClick={load} style={{ marginBottom: 12 }}>Refresh</button>
      <h3 style={{ marginTop: 0 }}>Platform Activity</h3>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Type</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Tenant</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Status</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Created</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 200).map((row, idx) => (
              <tr key={`${row.event_id || row.type || 'event'}-${idx}`}>
                <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>{row.type || ''}</td>
                <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>{row.tenant_id || ''}</td>
                <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>{row.status || ''}</td>
                <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>{row.created_at || ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
