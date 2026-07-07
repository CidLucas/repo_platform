import type { RoutineStep, CatalogStep } from '../../api/routines'
import Checkbox from './Checkbox'

interface Props {
  name: string
  description?: string | null
  triggerType: string
  triggerConfig: Record<string, unknown>
  steps: (RoutineStep | CatalogStep)[]
  createdByAi?: boolean
  submitting?: boolean
  onEdit: () => void
  onSubmit: () => void
}

const TRIGGER_LABELS: Record<string, string> = {
  manual: 'Manual — executado sob demanda',
  schedule: 'Agenda',
  cron: 'Agenda',
  event: 'Evento',
  document: 'Documento concluído',
  numeric: 'Métrica',
}

const STEP_TYPE_LABELS: Record<string, string> = {
  function: 'Função',
  skill: 'Agente IA',
  artifact: 'Saída',
}

function stepLabel(step: RoutineStep | CatalogStep): string {
  if ('type' in step && step.type) return STEP_TYPE_LABELS[step.type] ?? step.type
  if ('agent' in step && step.agent) return step.agent
  return 'Passo'
}

function stepTitle(step: RoutineStep | CatalogStep): string {
  if (step.label) return step.label
  if ('skill_slug' in step && step.skill_slug) return step.skill_slug
  if ('function' in step && step.function) return step.function
  if ('artifact_type' in step && step.artifact_type) return step.artifact_type
  if ('action' in step && step.action) return step.action
  return 'Ação'
}

function triggerSummary(type: string, cfg: Record<string, unknown>): string {
  if (type === 'cron' || type === 'schedule') {
    const expr = cfg.expression as string | undefined
    if (!expr) return 'Agenda configurada'
    return `Agenda: ${expr}`
  }
  if (type === 'event') return `Evento: ${cfg.event_type ?? 'configurado'}`
  if (type === 'numeric') return `Métrica: ${cfg.metric ?? ''} ≥ ${cfg.threshold ?? ''}`
  return TRIGGER_LABELS[type] ?? type
}

export default function RoutinePreviewCard({
  name, description, triggerType, triggerConfig, steps, createdByAi,
  submitting, onEdit, onSubmit,
}: Props) {
  return (
    <div
      style={{
        background: 'var(--glass)',
        border: '1px solid var(--accent, #6366f1)',
        borderRadius: 'var(--r)',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--gb)', display: 'flex', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 700 }}>{name}</span>
            {createdByAi && (
              <span style={{ fontSize: 9.5, color: '#818cf8', background: 'rgba(129,140,248,.12)', borderRadius: 4, padding: '1px 5px' }}>
                ✦ IA
              </span>
            )}
          </div>
          {description && <div style={{ fontSize: 11, color: 'var(--mu)', marginTop: 3 }}>{description}</div>}
        </div>
        <span style={{ fontSize: 10, color: 'var(--mu)', background: 'rgba(0,0,0,.2)', borderRadius: 4, padding: '2px 6px', whiteSpace: 'nowrap', marginTop: 2 }}>
          Rascunho
        </span>
      </div>

      {/* Trigger */}
      <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--gb)', display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 10, color: 'var(--mu)', minWidth: 54 }}>Gatilho</span>
        <span style={{ fontSize: 11.5 }}>⚡ {triggerSummary(triggerType, triggerConfig)}</span>
      </div>

      {/* Steps */}
      <div style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 0 }}>
        <div style={{ fontSize: 10.5, color: 'var(--mu)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
          {steps.length} passo{steps.length !== 1 ? 's' : ''}
        </div>
        {steps.map((step, i) => (
          <div key={i} style={{ display: 'flex', gap: 0, alignItems: 'flex-start' }}>
            {/* Timeline */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginRight: 10, paddingTop: 2 }}>
              <Checkbox
                checked={Boolean((step as { done?: boolean }).done)}
                disabled
                onChange={() => {}}
              />
              {i < steps.length - 1 && (
                <div style={{ width: 1, flex: 1, minHeight: 14, background: 'var(--gb)', margin: '2px 0' }} />
              )}
            </div>
            {/* Content */}
            <div style={{ flex: 1, paddingBottom: i < steps.length - 1 ? 10 : 0 }}>
              <div style={{ fontSize: 10, color: 'var(--accent, #6366f1)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                {stepLabel(step)}
              </div>
              <div style={{ fontSize: 12, marginTop: 1 }}>{stepTitle(step)}</div>
              {'task_template' in step && step.task_template && (
                <div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 3, lineHeight: 1.4 }}>
                  {(step.task_template as string).slice(0, 120)}{(step.task_template as string).length > 120 ? '…' : ''}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div style={{ padding: '10px 14px', borderTop: '1px solid var(--gb)', display: 'flex', gap: 8 }}>
        <button
          className="btn bs"
          style={{ fontSize: 11, padding: '5px 12px' }}
          onClick={onEdit}
          disabled={submitting}
        >
          Editar
        </button>
        <button
          className="btn bp"
          style={{ fontSize: 11, padding: '5px 14px', marginLeft: 'auto' }}
          onClick={onSubmit}
          disabled={submitting}
        >
          {submitting ? 'Enviando…' : 'Enviar para aprovação do dono →'}
        </button>
      </div>
    </div>
  )
}
