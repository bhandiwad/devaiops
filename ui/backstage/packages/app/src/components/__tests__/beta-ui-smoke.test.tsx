import React from 'react';
import { render, screen } from '@testing-library/react';
import { App } from '../../App';

describe('beta navigation smoke', () => {
  it('renders core IA tabs', () => {
    render(<App />);
    expect(screen.getByText('Search')).toBeInTheDocument();
    expect(screen.getByText('Onboarding')).toBeInTheDocument();
    expect(screen.getByText('Tenants')).toBeInTheDocument();
    expect(screen.getByText('Marketplace')).toBeInTheDocument();
    expect(screen.getByText('Incidents')).toBeInTheDocument();
  });
});
