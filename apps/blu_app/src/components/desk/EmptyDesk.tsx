import { ArrowRight } from 'lucide-react'

interface EmptyDeskProps {
  agentName?: string
  onViewHistory?: () => void
}

/**
 * Shown when no pending decisions exist in the desk surface.
 * Warm sand background — calming, not anxious.
 */
export function EmptyDesk({ agentName, onViewHistory }: EmptyDeskProps) {
  const headline = agentName
    ? `${agentName} está monitorando.`
    : 'Nada urgente agora.'
  const sub = agentName
    ? `Quando houver algo para decidir em ${agentName}, vai aparecer aqui.`
    : 'Quando houver itens para decidir, eles aparecerão aqui.'

  return (
    <div className="bg-sand/10 border border-sand/20 rounded-md p-6 text-center">
      <div className="w-8 h-8 rounded-full bg-ok/20 flex items-center justify-center mx-auto mb-3">
        <span className="text-ok text-body-sm">✓</span>
      </div>
      <p className="text-body-sm font-medium text-sand-dark mb-1">{headline}</p>
      <p className="text-caption text-gray-400 mb-4">{sub}</p>
      {onViewHistory && (
        <button
          onClick={onViewHistory}
          className="inline-flex items-center gap-1.5 text-caption text-gray-400
            hover:text-white hover:underline transition-colors cursor-pointer"
        >
          Ver histórico
          <ArrowRight size={13} />
        </button>
      )}
    </div>
  )
}
