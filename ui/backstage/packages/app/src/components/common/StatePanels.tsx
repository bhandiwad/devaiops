import React from 'react';

export function LoadingState(props: { message?: string }) {
  return (
    <div style={{ padding: 16 }}>
      <div style={{ marginTop: 8 }}>{props.message || 'Loading...'}</div>
    </div>
  );
}

export function EmptyState(props: { title: string; action?: React.ReactNode; description?: string }) {
  return (
    <div style={{ border: '1px solid #d0d7de', borderRadius: 8, padding: 16, background: '#f8fafc' }}>
      <h4 style={{ margin: 0 }}>{props.title}</h4>
      {props.description ? <p style={{ marginTop: 8, marginBottom: 0 }}>{props.description}</p> : null}
      <div style={{ marginTop: 8 }}>{props.action}</div>
    </div>
  );
}

export function ErrorState(props: { error: Error; retry?: () => void }) {
  return (
    <div style={{ border: '1px solid #fecaca', borderRadius: 8, padding: 16, background: '#fff1f2' }}>
      <h4 style={{ margin: 0 }}>Error</h4>
      <p style={{ marginTop: 8, marginBottom: 0 }}>{props.error?.message || 'Unexpected error'}</p>
      {props.retry ? (
        <button type="button" onClick={props.retry} style={{ marginTop: 10 }}>
          Retry
        </button>
      ) : null}
    </div>
  );
}
