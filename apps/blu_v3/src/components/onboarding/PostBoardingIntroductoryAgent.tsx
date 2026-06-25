export default function PostBoardingIntroductoryAgent({
  onDismiss,
}: {
  onDismiss: () => void
}) {
  return (
    <div className="post-boarding-introductory-agent">
      <h2>Olá! Eu sou o Agente blu</h2>
      <p>
        Posso te ajudar a organizar decisões, monitorar sua operação e cuidar
        das rotinas do seu escritório.
      </p>
      <button type="button" onClick={onDismiss}>Começar</button>
    </div>
  )
}
