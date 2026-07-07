export interface LoadingStateProps {
  message?: string;
  variant?: 'spinner' | 'card' | 'text' | 'row' | 'table' | 'chart';
  rows?: number;
}

export default function LoadingState({
  message,
  variant = 'spinner',
  rows = 3,
}: LoadingStateProps) {
  const display = message ?? 'Aguarde enquanto carregamos…';

  if (variant === 'spinner') {
    return (
      <div style={{ padding: '12px 0', color: 'var(--mu)', fontSize: 12 }}>
        {display}
      </div>
    );
  }

  if (variant === 'card') {
    return <div className="skeleton skeleton-card" />;
  }

  if (variant === 'text') {
    return (
      <div>
        <div className="skeleton skeleton-title" />
        <div className="skeleton skeleton-text" />
        <div className="skeleton skeleton-text" />
        <div className="skeleton skeleton-text" />
      </div>
    );
  }

  if (variant === 'row') {
    const items = Array.from({ length: rows }, (_, i) => i);
    return (
      <div>
        {items.map((i) => (
          <div key={i} className="skeleton skeleton-row" />
        ))}
      </div>
    );
  }

  if (variant === 'table') {
    const bodyRows = Math.max(1, rows - 1);
    return (
      <div>
        <div
          className="skeleton skeleton-row"
          style={{ width: '100%', marginBottom: 8 }}
        />
        {Array.from({ length: bodyRows }, (_, i) => (
          <div
            key={i}
            className="skeleton skeleton-row"
            style={{ width: i % 2 === 0 ? '92%' : '78%' }}
          />
        ))}
      </div>
    );
  }

  // chart variant
  return (
    <div
      className="skeleton"
      style={{
        width: '100%',
        aspectRatio: '16 / 9',
        borderRadius: 'var(--rl)',
      }}
    />
  );
}
