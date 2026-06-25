export default function PostBoardingEmptyState({
  onAddConnection,
}: {
  onAddConnection: () => void
}) {
  return (
    <div className="post-boarding-empty-state">
      <h1>Bem-vindo! Vamos começar</h1>
      <p>Conecte seu primeiro sistema para que o Blu possa começar a cuidar do seu escritório.</p>
      <button type="button" onClick={onAddConnection}>Adicionar primeira conexão</button>
    </div>
  )
}
