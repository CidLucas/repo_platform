// GOAL: Melhorar qualidade do código | BEHAVIOR: B8 Error Boundaries | DECISÃO: extend
interface ErrorFallbackProps {
  error?: Error | null
  onReset?: () => void
}

export default function ErrorFallback({ error: _error, onReset }: ErrorFallbackProps) {
  const handleReset = () => {
    if (onReset) {
      onReset()
    } else {
      window.location.reload()
    }
  }

  return (
    <div
      role="alert"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 16,
        padding: '48px 24px',
        maxWidth: 480,
        margin: '0 auto',
        minHeight: '60vh',
        textAlign: 'center',
        color: 'var(--fg, #DFE3EE)',
      }}
    >
      <div style={{ fontSize: 48, lineHeight: 1 }} aria-hidden="true">⚠️</div>
      <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Algo deu errado</h2>
      <p style={{ fontSize: 14, color: 'var(--mu, #888)', margin: 0, lineHeight: 1.5 }}>
        Ocorreu um erro inesperado. Por favor, tente novamente.
      </p>
      <button
        type="button"
        onClick={handleReset}
        style={{
          marginTop: 8,
          padding: '10px 20px',
          borderRadius: 'var(--r, 8px)',
          background: 'var(--ac, #8C5FDB)',
          color: '#fff',
          fontSize: 14,
          fontWeight: 600,
          cursor: 'pointer',
          border: 'none',
        }}
      >
        Tentar novamente
      </button>
    </div>
  )
}
