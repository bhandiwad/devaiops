import React from 'react';
import { InfoCard } from '@backstage/core-components';

export function SettingsPage() {
  return (
    <InfoCard title="Platform Settings" subheader="Configuration and environment information">
      <p>Settings are managed through external configuration files and policy bundles.</p>
      <p>Use Platform Ops for upgrade, DR verification, and metering summaries.</p>
    </InfoCard>
  );
}
