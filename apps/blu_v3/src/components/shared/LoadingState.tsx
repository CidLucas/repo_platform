export interface LoadingStateProps {
  message?: string;
}

export default function LoadingState({ message }: LoadingStateProps): LoadingStateProps {
  const display = message ?? "Aguarde enquanto carregamos…";
  return <div style={{ padding: "12px 0", color: "var(--mu)", fontSize: 12 }}>{display}</div>;
}
