export interface EmptyStateProps {
  icon: string;
  title: string;
  description: string;
  action?: { label: string; onClick: () => void };
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps): EmptyStateProps {
  return (
    <div className="empty">
      <i className="ei">{icon}</i>
      <div className="et">{title}</div>
      <div className="eb">{description}</div>
      {action && (
        <button className="ea" onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  );
}
