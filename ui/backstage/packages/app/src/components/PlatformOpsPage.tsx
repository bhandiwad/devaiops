import React, { useEffect, useState } from 'react';
import { InfoCard, Progress, Button } from '@backstage/core-components';
import { platformFetch } from './common/platformApi';
import { ErrorState } from './common/StatePanels';

export function PlatformOpsPage() {
  const [version, setVersion] = useState<any>(null);
  const [metering, setMetering] = useState<any>(null);
  const [dr, setDr] = useState<any>(null);
  const [plan, setPlan] = useState<any>(null);
  const [error, setError] = useState<Error | null>(null);

  async function loadAll() {
    setError(null);
    const [v, m, d, p] = await Promise.all([
      platformFetch('/platform/version'),
      platformFetch('/platform/metering/summary'),
      platformFetch('/platform/dr/status'),
      platformFetch('/platform/upgrade/plan'),
    ]);
    if (!v.ok || !m.ok || !d.ok || !p.ok) {
      throw new Error(`Failed to load platform ops views: version=${v.status} metering=${m.status} dr=${d.status} plan=${p.status}`);
    }
    setVersion(await v.json());
    setMetering(await m.json());
    setDr(await d.json());
    setPlan(await p.json());
  }

  async function verifyDR() {
    const resp = await platformFetch('/platform/dr/verify', { method: 'POST' });
    if (!resp.ok) {
      throw new Error(`DR verify failed: HTTP ${resp.status}`);
    }
    await loadAll();
  }

  useEffect(() => {
    loadAll().catch(e => setError(e));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) return <ErrorState error={error} />;
  if (!version || !metering || !dr || !plan) return <Progress />;

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <InfoCard title="Platform Version">{JSON.stringify(version)}</InfoCard>
      <InfoCard title="Platform Metering">{JSON.stringify(metering)}</InfoCard>
      <InfoCard title="DR Status">
        <div>{JSON.stringify(dr)}</div>
        <Button onClick={() => verifyDR().catch(e => setError(e))} style={{ marginTop: 12 }}>
          Verify DR
        </Button>
      </InfoCard>
      <InfoCard title="Upgrade Plan">{JSON.stringify(plan)}</InfoCard>
    </div>
  );
}
