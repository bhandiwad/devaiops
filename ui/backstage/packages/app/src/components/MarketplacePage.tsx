import React, { useEffect, useMemo, useState } from 'react';
import { Button, Table } from '@backstage/core-components';
import { asArray, platformFetch } from './common/platformApi';
import { EmptyState, ErrorState, LoadingState } from './common/StatePanels';

export function MarketplacePage() {
  const [products, setProducts] = useState<any[]>([]);
  const [tenants, setTenants] = useState<any[]>([]);
  const [selectedTenant, setSelectedTenant] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [p, t] = await Promise.all([
        platformFetch('/products'),
        platformFetch('/tenants?limit=200'),
      ]);
      if (!p.ok || !t.ok) {
        throw new Error(`Failed loading marketplace data: products=${p.status}, tenants=${t.status}`);
      }
      const pdata = asArray(await p.json());
      const tdata = asArray(await t.json());
      setProducts(pdata);
      setTenants(tdata);
      if (!selectedTenant && tdata.length > 0) {
        setSelectedTenant(tdata[0].tenant_id);
      }
    } catch (e: any) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  async function toggleProduct(productId: string, action: 'enable' | 'disable') {
    if (!selectedTenant) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await platformFetch(`/tenants/${selectedTenant}/products/${productId}/${action}`, { method: 'POST' });
      if (!resp.ok) {
        throw new Error(`${action} failed: HTTP ${resp.status}`);
      }
      await load();
    } catch (e: any) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const productRows = useMemo(() => {
    return products.map(p => ({
      ...p,
      capabilities: Object.keys(p.required_capabilities || {}).join(', ') || 'none',
    }));
  }, [products]);

  if (loading && products.length === 0) return <LoadingState message="Loading product marketplace" />;
  if (error && products.length === 0) return <ErrorState error={error} />;
  if (products.length === 0) return <EmptyState title="No products available" description="Add ProductDescriptor files to config/products." action={<Button onClick={load}>Refresh</Button>} />;

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <select value={selectedTenant} onChange={e => setSelectedTenant(e.target.value)} disabled={tenants.length === 0}>
          {tenants.map(t => <option key={t.tenant_id} value={t.tenant_id}>{t.tenant_id}</option>)}
        </select>
        <Button onClick={load}>Refresh</Button>
      </div>
      {tenants.length === 0 && (
        <EmptyState title="No tenants available" description="Onboard a tenant to enable or disable marketplace products." />
      )}
      <Table
        title="Marketplace"
        columns={[
          { title: 'Product', field: 'name' },
          { title: 'ID', field: 'id' },
          { title: 'Modules', render: row => (row.required_modules || []).join(', ') },
          { title: 'Capabilities', field: 'capabilities' },
          { title: 'Actions', render: row => (
            <div style={{ display: 'flex', gap: 4 }}>
              <Button onClick={() => toggleProduct(row.id, 'enable')}>Enable</Button>
              <Button onClick={() => toggleProduct(row.id, 'disable')}>Disable</Button>
            </div>
          ) },
        ]}
        data={productRows}
        options={{ paging: true, pageSize: 20 }}
        onRowClick={(_event, row) => setSelectedProduct(row)}
      />
      {selectedProduct && (
        <div style={{ marginTop: 16 }}>
          <h4>{selectedProduct.name}</h4>
          <p>{selectedProduct.description}</p>
          <p>Required modules: {(selectedProduct.required_modules || []).join(', ') || 'none'}</p>
          <p>FinOps tags: {JSON.stringify(selectedProduct.finops_tags || {})}</p>
          <p>Approvals and policy gates are enforced by server-side PolicyEngine.</p>
        </div>
      )}
      {error && <ErrorState error={error} />}
    </div>
  );
}
