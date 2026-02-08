import React, { useState } from 'react';
import { Button, Table } from '@backstage/core-components';
import { ErrorState, EmptyState, LoadingState } from './common/StatePanels';
import { platformFetch } from './common/platformApi';

export function SearchPage() {
  const [query, setQuery] = useState('');
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  async function runSearch() {
    if (query.trim().length < 2) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const resp = await platformFetch(`/search?q=${encodeURIComponent(query)}&limit=50`);
      if (!resp.ok) {
        throw new Error(`Search failed: HTTP ${resp.status}`);
      }
      const data = await resp.json();
      setRows(data.items || []);
    } catch (e: any) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          aria-label="Global search"
          style={{ flex: 1, padding: 8 }}
          value={query}
          placeholder="Search tenants, incidents, products, runbooks, events"
          onChange={e => setQuery(e.target.value)}
        />
        <Button onClick={runSearch}>Search</Button>
      </div>
      {loading && <LoadingState message="Searching platform data" />}
      {error && <ErrorState error={error} />}
      {!loading && !error && rows.length === 0 && <EmptyState title="No results yet" description="Run a search query to find platform resources." />}
      {!loading && !error && rows.length > 0 && (
        <Table
          title="Search Results"
          columns={[
            { title: 'Type', field: 'kind' },
            { title: 'ID', field: 'id' },
            { title: 'Title', field: 'title' },
            { title: 'Tenant', field: 'tenant_id' },
            { title: 'Status', field: 'status' },
          ]}
          data={rows}
          options={{ paging: true, pageSize: 25 }}
        />
      )}
    </div>
  );
}
