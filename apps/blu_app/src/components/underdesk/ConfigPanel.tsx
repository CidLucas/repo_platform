import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface ConfigSectionProps {
  title: string
  children: ReactNode
  accentColor?: string
  className?: string
}

function ConfigSection({ title, children, accentColor, className }: ConfigSectionProps) {
  return (
    <div className={cn('py-3 px-4 border-b border-border last:border-0', className)}>
      <p className="text-section-label mb-2" style={accentColor ? { color: accentColor } : undefined}>{title}</p>
      {children}
    </div>
  )
}

interface ConfigRowProps {
  label: string
  description?: string
  control: ReactNode
}

function ConfigRow({ label, description, control }: ConfigRowProps) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <div className="flex-1 min-w-0">
        <p className="text-body-sm text-gray-200">{label}</p>
        {description && (
          <p className="text-caption text-gray-500">{description}</p>
        )}
      </div>
      <div className="shrink-0">{control}</div>
    </div>
  )
}

interface ConfigPanelProps {
  agentSlug?: string
  accentColor?: string
  className?: string
}

/**
 * General config panel inside UnderDesk.
 * Extendable — each room adds room-specific sections via composition.
 */
export function ConfigPanel({ accentColor, className }: ConfigPanelProps) {
  return (
    <div className={cn('divide-y divide-border', className)}>
      <ConfigSection title="Notificações" accentColor={accentColor}>
        <ConfigRow
          label="Alertas urgentes"
          description="Receba alertas quando houver decisões urgentes"
          control={
            <span className="text-caption text-gray-500 italic">
              Em breve
            </span>
          }
        />
      </ConfigSection>
      <ConfigSection title="Agente" accentColor={accentColor}>
        <ConfigRow
          label="Relatórios automáticos"
          description="Gere relatórios semanais automaticamente"
          control={
            <span className="text-caption text-gray-500 italic">
              Em breve
            </span>
          }
        />
      </ConfigSection>
    </div>
  )
}

// Expose sub-components for composition
ConfigPanel.Section = ConfigSection
ConfigPanel.Row = ConfigRow
