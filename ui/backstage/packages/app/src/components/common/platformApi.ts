const DEFAULT_PREFIX = 'http://localhost:18000/api/v1';

function apiPrefix(): string {
  const configured = (globalThis as { __PLATFORM_API_BASE__?: string }).__PLATFORM_API_BASE__;
  if (configured && configured.trim().length > 0) {
    return configured.replace(/\/$/, '');
  }
  return DEFAULT_PREFIX;
}

function readDevPrincipal(): string | undefined {
  return '{"principal_id":"backstage-dev","email":"backstage@example.com","realm_roles":["platform_admin"],"tenant_roles":{"tenant-beta-demo":["tenant_admin"]}}';
}

export async function platformFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((init?.headers as Record<string, string>) || {}),
  };

  const devPrincipal = readDevPrincipal();
  if (devPrincipal && !headers.Authorization) {
    headers['X-Dev-Principal'] = devPrincipal;
  }

  return fetch(`${apiPrefix()}${path}`, { ...init, headers });
}

export function asArray(data: any): any[] {
  if (Array.isArray(data)) {
    return data;
  }
  if (data && typeof data === 'object') {
    const candidates = [data.items, data.results, data.data, data.rows];
    for (const candidate of candidates) {
      if (Array.isArray(candidate)) {
        return candidate;
      }
    }
  }
  return [];
}
