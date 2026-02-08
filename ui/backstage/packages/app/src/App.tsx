import React from 'react';
import { BrowserRouter, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { TenantConsolePage } from './components/TenantConsolePage';
import { DeploymentsPage } from './components/DeploymentsPage';
import { IncidentsPage } from './components/IncidentsPage';
import { DriftPage } from './components/DriftPage';
import { GovernancePage } from './components/GovernancePage';
import { ExportsPage } from './components/ExportsPage';
import { TenantUsagePage } from './components/TenantUsagePage';
import { PlatformOpsPage } from './components/PlatformOpsPage';
import { MarketplacePage } from './components/MarketplacePage';
import { AccessPage } from './components/AccessPage';
import { ScaffoldPage } from './components/ScaffoldPage';
import { PromotionsPage } from './components/PromotionsPage';
import { SearchPage } from './components/SearchPage';
import { ActivityFeedPage } from './components/ActivityFeedPage';
import { OnboardingWizardPage } from './components/OnboardingWizardPage';
import { SettingsPage } from './components/SettingsPage';
import './app-theme.css';

type NavItem = {
  label: string;
  path: string;
  icon: string;
};

const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/tenants', icon: '◫' },
  { label: 'Search', path: '/search', icon: '⌕' },
  { label: 'Activity', path: '/activity', icon: '◉' },
  { label: 'Onboarding', path: '/onboarding', icon: '⇄' },
  { label: 'Services', path: '/services', icon: '◻' },
  { label: 'Deployments', path: '/deployments', icon: '⇪' },
  { label: 'Incidents', path: '/incidents', icon: '⚑' },
  { label: 'Runbooks', path: '/platform-ops', icon: '⚙' },
  { label: 'Drift', path: '/drift', icon: '∆' },
  { label: 'Marketplace', path: '/marketplace', icon: '◇' },
  { label: 'Governance', path: '/governance', icon: '⛨' },
  { label: 'Access', path: '/access', icon: '◌' },
  { label: 'Promotions', path: '/promotions', icon: '↟' },
  { label: 'Exports', path: '/exports', icon: '⇩' },
  { label: 'Metering', path: '/usage', icon: '◔' },
  { label: 'Settings', path: '/settings', icon: '⋯' },
];

function AppShell() {
  const location = useLocation();
  const currentLabel = navItems.find(item => location.pathname.startsWith(item.path))?.label || 'Dashboard';

  return (
    <div className="shell-root">
      <aside className="shell-sidebar">
        <div className="brand">
          <div className="brand-logo" aria-hidden>
            <span className="loop left" />
            <span className="loop right" />
          </div>
          <div>
            <h1>AIOps</h1>
            <p>Platform</p>
          </div>
        </div>
        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navItems.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <span className="nav-icon" aria-hidden>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-pill">
            <div className="avatar">A</div>
            <div>
              <strong>Account</strong>
              <p>Workspace</p>
            </div>
          </div>
        </div>
      </aside>

      <main className="shell-main">
        <header className="topbar">
          <h2>{currentLabel}</h2>
          <div className="topbar-actions">
            <label className="searchbox" aria-label="Search">
              <span>⌕</span>
              <input placeholder="Search..." />
            </label>
            <button type="button" className="icon-btn" aria-label="Alerts">◌</button>
          </div>
        </header>

        <section className="hero">
          <div>
            <h3>{currentLabel}</h3>
            <p>Unified platform operations</p>
          </div>
        </section>

        <section className="content-card">
          <Routes>
            <Route path="/" element={<div>Select a view.</div>} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/activity" element={<ActivityFeedPage />} />
            <Route path="/onboarding" element={<OnboardingWizardPage />} />
            <Route path="/tenants" element={<TenantConsolePage />} />
            <Route path="/services" element={<ScaffoldPage />} />
            <Route path="/deployments" element={<DeploymentsPage />} />
            <Route path="/incidents" element={<IncidentsPage />} />
            <Route path="/drift" element={<DriftPage />} />
            <Route path="/governance" element={<GovernancePage />} />
            <Route path="/exports" element={<ExportsPage />} />
            <Route path="/usage" element={<TenantUsagePage />} />
            <Route path="/platform-ops" element={<PlatformOpsPage />} />
            <Route path="/marketplace" element={<MarketplacePage />} />
            <Route path="/access" element={<AccessPage />} />
            <Route path="/scaffold" element={<ScaffoldPage />} />
            <Route path="/promotions" element={<PromotionsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </section>
      </main>
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}
