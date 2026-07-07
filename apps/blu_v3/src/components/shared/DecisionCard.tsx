import { useState } from 'react'
import { useAppStore } from '../../store/appStore'
import type { ApprovalRequest } from '../../api/approvals'
import { AGENT_COLORS } from '../../utils/constants'
import Checkbox from './Checkbox'
import SmartRenderer from '../chat/SmartRenderer'

// ── Helpers ──────────────────────────────────────────────────────────────────

function agentColor(slug: string) {
  return AGENT_COLORS[slug] ?? '#94a3b8'
}

function agentLabel(slug: string) {
  const labels: Record<string, string> = {
    compras: 'Compras',
    financeiro: 'Financeiro',
    clientes: 'Clientes',
    documentos: 'Documentos',
    estrategia: 'Estratégia',
    agenda: 'Agenda',
    estoque: 'Estoque',
  }
  return labels[slug] ?? slug.charAt(0).toUpperCase() + slug.slice(1)
}

function priorityBadge(priority: ApprovalRequest['priority']): { cls: string; label: string } {
  switch (priority) {
    case 'urgent': return { cls: 'bdg bu', label: 'Urgente' }
    case 'high':   return { cls: 'bdg bu', label: 'Alto' }
    case 'medium': return { cls: 'bdg bw', label: 'Médio' }
    default:       return { cls: 'bdg bw', label: 'Normal' }
  }
}

function dcClass(priority: ApprovalRequest['priority']) {
  return priority === 'urgent' || priority === 'high' ? 'urg' : 'warn'
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

// ── Routine Activation Card (nested) ───────────────────────────────────────────

function RoutineActivationCard({
  approval,
  onApprove,
  onReject,
}: {
  approval: ApprovalRequest
  onApprove: () => void
  onReject: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const payload = approval.payload ?? {}
  const steps = (payload.steps as { label?: string; type?: string; skill_slug?: string; function?: string; action?: string }[] | undefined) ?? []
  const routineName = (payload.routine_name as string | undefined) ?? approval.title

  return (
    <div className={`dc warn${expanded ? ' expanded' : ''}`}>
      <div className="dc-row" onClick={() => setExpanded(!expanded)}>
        <div className="ag">
          <div className="agd" style={{ background: '#818cf8' }} />
          <span>Rotina</span>
        </div>
        <span className="bdg bw" style={{ fontSize: 9, background: 'rgba(129,140,248,.12)', color: '#818cf8' }}>✦ IA</span>
        <span className="dc-row-summary">{routineName}</span>
        <span className="dt">{new Date(approval.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>
        <span className="dc-chev">{expanded ? '▼' : '▶'}</span>
      </div>
      <div className="dc-expand">
        {steps.length > 0 && (
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 10, color: 'var(--mu)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
              {steps.length} passo{steps.length !== 1 ? 's' : ''}
            </div>
            {steps.map((step, i) => {
              const stepDone = Boolean((step as { done?: boolean }).done)
              const stepLabel = step.label ?? step.skill_slug ?? step.function ?? step.action ?? 'Passo'
              return (
                <div key={i} style={{ marginBottom: 6 }}>
                  <Checkbox
                    checked={stepDone}
                    disabled
                    onChange={() => {}}
                    label={stepLabel}
                  />
                  {step.type && <div style={{ fontSize: 10, color: 'var(--mu)', marginTop: 1, marginLeft: 28 }}>{step.type}</div>}
                </div>
              )
            })}
          </div>
        )}
        <div className="dc-act">
          <button className="btn bp" onClick={(e) => { e.stopPropagation(); onApprove() }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Ativar</button>
          <button className="btn bs" onClick={(e) => { e.stopPropagation(); onReject() }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg> Rejeitar</button>
        </div>
      </div>
    </div>
  )
}

// ── Main Decision Card ─────────────────────────────────────────────────────────

export interface DecisionCardProps {
  approval: ApprovalRequest
  onApprove: () => void
  onReject: () => void
  onSnooze: () => void
}

export default function DecisionCard({
  approval,
  onApprove,
  onReject,
  onSnooze,
}: DecisionCardProps) {
  const { toggleDc, expandedId, addToast, goWithTab, openChatWith, setPendingDocId } = useAppStore()

  if (approval.action_type === 'routine_activation') {
    return (
      <RoutineActivationCard
        approval={approval}
        onApprove={() => { onApprove(); addToast('ok', 'Rotina ativada', approval.title) }}
        onReject={() => { onReject(); addToast('no', 'Rejeitado', 'Rotina não ativada.') }}
      />
    )
  }

  const isExpanded = expandedId === approval.id
  const badge = priorityBadge(approval.priority)
  const cls = ['dc', dcClass(approval.priority), isExpanded ? 'expanded' : ''].filter(Boolean).join(' ')

  const artifactType = (approval.metadata?.artifact_type as string) ?? ''
  const artifactId = (approval.metadata?.artifact_id as string) ?? ''
  const artifactUrl = (approval.metadata?.artifact_url as string) ?? ''

  function handleApprove() {
    onApprove()
    addToast('ok', 'Aprovado', approval.title)
  }
  function handleReject() {
    onReject()
    if (artifactType === 'document' && artifactId) {
      setPendingDocId(artifactId)
      goWithTab('estrategia', 'Estratégia', 'documentos')
      addToast('no', 'Rejeitado', 'Abrindo documento para edição.')
    } else {
      const ctx = [approval.title, approval.body].filter(Boolean).join('\n')
      openChatWith(`Rejeitei: ${ctx}\n\nO que fazemos?`)
      addToast('no', 'Rejeitado', 'Blu anotou.')
    }
  }
  function handleSnooze() {
    onSnooze()
    addToast('sn', 'Adiado', 'Lembrete em 2 horas.')
  }

  return (
    <div className={cls} id={approval.id}>
      <div className="dc-row" onClick={() => toggleDc(approval.id)}>
        <div className="ag">
          <div className="agd" style={{ background: agentColor(approval.agent_slug) }} />
          {agentLabel(approval.agent_slug)}
        </div>
        <span className={badge.cls}>{badge.label}</span>
        <span className="dc-row-summary">{approval.title}</span>
        <span className="dt">{formatTime(approval.created_at)}</span>
        <span className="dc-chev">{isExpanded ? '▼' : '▶'}</span>
      </div>
      <div className="dc-expand">
        {approval.body && (
          <div className="db">
            <SmartRenderer content={approval.body} />
          </div>
        )}
        {artifactType === 'document' && artifactId && (
          <button
            className="btn bg"
            style={{ marginBottom: 8, fontSize: 11 }}
            onClick={(e) => { e.stopPropagation(); setPendingDocId(artifactId); goWithTab('estrategia', 'Estratégia', 'documentos') }}
          >
            Ver documento →
          </button>
        )}
        {artifactType === 'report' && artifactUrl && (
          <a
            href={artifactUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn bg"
            style={{ marginBottom: 8, fontSize: 11, display: 'inline-block' }}
          >
            Ver relatório →
          </a>
        )}
        <div className="dc-act">
          <button className="btn bp" onClick={(e) => { e.stopPropagation(); handleApprove() }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Aprovar</button>
          <button className="btn bg" onClick={(e) => { e.stopPropagation(); handleSnooze() }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 2 16 8 22 8"/><line x1="4" y1="18" x2="4" y2="22"/><line x1="8" y1="18" x2="8" y2="22"/><polyline points="9 22 5 12 19 12 15 22"/></svg> Depois</button>
          <button className="btn bs" onClick={(e) => { e.stopPropagation(); handleReject() }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg> Rejeitar</button>
        </div>
      </div>
    </div>
  )
}
