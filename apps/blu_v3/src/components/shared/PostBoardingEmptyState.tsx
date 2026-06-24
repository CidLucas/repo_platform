interface PostBoardingEmptyStateProps {
  onAddConnection: () => void
}

export default function PostBoardingEmptyState({ onAddConnection }: PostBoardingEmptyStateProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 16,
        padding: '48px 24px',
        background: 'rgba(8,18,48,0.55)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: 14,
        textAlign: 'center',
      }}
    >
      <h1
        style={{
          margin: 0,
          fontSize: 22,
          fontWeight: 800,
          color: 'var(--fg)',
          letterSpacing: '-.02em',
        }}
      >
        Bem-vindo! Vamos começar
      </h1>
      <p
        style={{
          margin: 0,
          fontSize: 13,
          color: 'var(--mu, rgba(223,227,238,0.55))',
          lineHeight: 1.5,
          maxWidth: 420,
        }}
      >
        Conecte sua primeira fonte de dados para o Blu começar a entender o seu negócio.
      </p>
      <button
        type="button"
        onClick={onAddConnection}
        style={{
          marginTop: 4,
          padding: '10px 18px',
          fontSize: 13,
          fontWeight: 600,
          color: '#E8EDF8',
          background: 'linear-gradient(135deg, #8C5FDB 0%, #5E3FBE 100%)',
          border: '1px solid rgba(140,95,219,0.55)',
          borderRadius: 8,
          cursor: 'pointer',
          boxShadow: '0 6px 20px rgba(140,95,219,0.25)',
        }}
      >
        Adicionar primeira conexão
      </button>
    </div>
  )
}
